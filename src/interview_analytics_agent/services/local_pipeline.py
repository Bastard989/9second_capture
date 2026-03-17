from __future__ import annotations

import gc
import re
import threading
from typing import Any

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.domain.enums import PipelineStatus
from interview_analytics_agent.processing.enhancer import enhance_text
from interview_analytics_agent.processing.speaker_rules import infer_speakers
from interview_analytics_agent.storage.blob import get_bytes
from interview_analytics_agent.storage import records
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.models import TranscriptSegment
from interview_analytics_agent.storage.repositories import (
    MeetingRepository,
    TranscriptSegmentRepository,
)
from interview_analytics_agent.stt.mock import MockSTTProvider

log = get_project_logger()

_stt_provider = None
_stt_warmup_started = False
_stt_warmup_ready = False
_stt_warmup_error = ""
_stt_warmup_lock = threading.Lock()
_stt_warmup_thread: threading.Thread | None = None
_TRACK_SPEAKERS = {"system", "mic", "mixed"}
_FINAL_PASS_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?…])\s+")
_SPACE_RE = re.compile(r"\s+")


def _status_for_chunk_processing(*, finished_at: object | None) -> PipelineStatus:
    if finished_at is not None:
        return PipelineStatus.done
    return PipelineStatus.processing


def _normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _safe_label(value: str, *, limit: int = 24) -> str:
    raw = "".join(ch if ch.isalnum() else "_" for ch in (value or "").strip())
    compact = "_".join(part for part in raw.split("_") if part)
    return (compact or "UNKNOWN").upper()[:limit]


def _speaker_from_track(
    *,
    source_track: str | None,
    meeting_context: dict[str, Any] | None,
) -> str | None:
    track = str(source_track or "").strip().lower()
    if track not in _TRACK_SPEAKERS:
        return None
    ctx = meeting_context or {}
    roles = ctx.get("source_track_roles") if isinstance(ctx.get("source_track_roles"), dict) else {}
    role = str(roles.get(track) or "").strip().lower()
    candidate_name = str(ctx.get("candidate_name") or "").strip()
    interviewer_name = str(ctx.get("interviewer") or "").strip()
    if role == "candidate":
        suffix = _safe_label(candidate_name) if candidate_name else "UNKNOWN"
        return f"CANDIDATE_{suffix}"
    if role == "interviewer":
        suffix = _safe_label(interviewer_name) if interviewer_name else "UNKNOWN"
        return f"INTERVIEWER_{suffix}"
    return track


def _speaker_locked_for_track(speaker: str | None) -> bool:
    normalized = str(speaker or "").strip().lower()
    if not normalized:
        return False
    if normalized in _TRACK_SPEAKERS:
        return True
    return normalized.startswith("candidate_") or normalized.startswith("interviewer_")


def _language_hint_from_context(meeting_context: dict[str, Any] | None) -> str | None:
    ctx = meeting_context or {}
    profile = str(ctx.get("language_profile") or "").strip().lower()
    locale = str(ctx.get("locale") or "").strip().lower()
    language = str(ctx.get("language") or "").strip().lower()
    raw = profile or language or locale
    if raw.startswith("ru"):
        return "ru"
    if raw.startswith("en"):
        return "en"
    if raw in {"mixed", "auto"}:
        return "auto"
    return None


def _meeting_language_hint(meeting_id: str) -> str | None:
    with db_session() as session:
        mrepo = MeetingRepository(session)
        meeting = mrepo.get(meeting_id)
        if not meeting:
            return None
        return _language_hint_from_context(getattr(meeting, "context", None))


def _extract_missing_tail(*, existing_text: str, backup_text: str) -> str:
    existing_norm = _normalize_text(existing_text)
    backup_norm = _normalize_text(backup_text)
    if not backup_norm:
        return ""
    if not existing_norm:
        return backup_norm
    if backup_norm.startswith(existing_norm):
        return backup_norm[len(existing_norm) :].strip()
    found_idx = backup_norm.rfind(existing_norm)
    if found_idx >= 0:
        return backup_norm[found_idx + len(existing_norm) :].strip()

    existing_tokens = existing_norm.split()
    backup_tokens = backup_norm.split()
    max_overlap = min(len(existing_tokens), len(backup_tokens), 120)
    for token_count in range(max_overlap, 2, -1):
        if existing_tokens[-token_count:] == backup_tokens[:token_count]:
            return " ".join(backup_tokens[token_count:]).strip()

    # Защита от дублей: если тексты в целом про одно и то же, не добавляем
    # весь backup как новый сегмент.
    existing_set = {t for t in existing_tokens if t}
    backup_set = {t for t in backup_tokens if t}
    if existing_set and backup_set:
        shared = len(existing_set & backup_set)
        min_size = min(len(existing_set), len(backup_set))
        if min_size > 0 and shared / float(min_size) >= 0.45:
            return ""

    # Для очень коротких live-частей допустим добавление полного backup.
    if len(existing_tokens) < 8 and len(backup_tokens) > len(existing_tokens) + 4:
        return backup_norm
    return ""


def _split_final_pass_text(transcript: str) -> list[str]:
    compact = _SPACE_RE.sub(" ", (transcript or "").strip())
    if not compact:
        return []

    parts = [part.strip() for part in _FINAL_PASS_SENTENCE_SPLIT_RE.split(compact) if part.strip()]
    if len(parts) <= 1:
        return [compact]
    return parts


def warmup_stt_provider_async() -> None:
    """
    Прогревает модель STT в фоне, чтобы первый запуск транскрибации
    не зависал на ленивой загрузке модели.
    """
    global _stt_warmup_started, _stt_warmup_thread
    with _stt_warmup_lock:
        if _stt_warmup_started:
            return
        _stt_warmup_started = True

    def _worker() -> None:
        global _stt_warmup_ready, _stt_warmup_error
        try:
            _get_stt_provider()
            _stt_warmup_ready = True
            _stt_warmup_error = ""
            log.info("stt_warmup_ready")
        except Exception as e:
            _stt_warmup_ready = False
            _stt_warmup_error = str(e)[:200]
            log.warning(
                "stt_warmup_failed",
                extra={"payload": {"err": str(e)[:200]}},
            )

    thread = threading.Thread(target=_worker, name="stt-warmup", daemon=True)
    _stt_warmup_thread = thread
    thread.start()


def _build_stt_provider():
    s = get_settings()

    if s.stt_provider == "mock":
        return MockSTTProvider()

    if s.stt_provider == "google":
        from interview_analytics_agent.stt.google import GoogleSTTProvider

        return GoogleSTTProvider()

    if s.stt_provider == "salutespeech":
        from interview_analytics_agent.stt.salutespeech import SaluteSpeechProvider

        return SaluteSpeechProvider()

    from interview_analytics_agent.stt.whisper_local import WhisperLocalProvider

    return WhisperLocalProvider(
        model_size=s.whisper_model_size,
        device=s.whisper_device,
        compute_type=s.whisper_compute_type,
        language=s.whisper_language,
        vad_filter=s.whisper_vad_filter,
        beam_size=s.whisper_beam_size,
    )


def _get_stt_provider():
    global _stt_provider, _stt_warmup_ready, _stt_warmup_error
    if _stt_provider is None:
        _stt_provider = _build_stt_provider()
    _stt_warmup_ready = True
    _stt_warmup_error = ""
    return _stt_provider


def shutdown_stt_provider_runtime(*, join_timeout_sec: float = 1.5) -> None:
    """
    Аккуратно очищает in-memory STT runtime при shutdown процесса.
    """
    global _stt_provider, _stt_warmup_started, _stt_warmup_ready, _stt_warmup_error, _stt_warmup_thread
    with _stt_warmup_lock:
        provider = _stt_provider
        warmup_thread = _stt_warmup_thread
        _stt_provider = None
        _stt_warmup_started = False
        _stt_warmup_ready = False
        _stt_warmup_error = ""
        _stt_warmup_thread = None

    if warmup_thread and warmup_thread.is_alive() and warmup_thread is not threading.current_thread():
        warmup_thread.join(timeout=max(0.0, float(join_timeout_sec)))

    if provider is None:
        return

    close_error = None
    close_fn = getattr(provider, "close", None)
    if callable(close_fn):
        try:
            close_fn()
        except Exception as err:  # pragma: no cover - defensive shutdown path
            close_error = err

    model = getattr(provider, "model", None)
    if model is not None:
        for attr in ("close", "unload"):
            cleanup_fn = getattr(model, attr, None)
            if not callable(cleanup_fn):
                continue
            try:
                cleanup_fn()
            except Exception as err:  # pragma: no cover - defensive shutdown path
                close_error = close_error or err
            break
        try:
            setattr(provider, "model", None)
        except Exception:
            pass

    if close_error is not None:
        log.warning(
            "stt_provider_shutdown_cleanup_failed",
            extra={"payload": {"err": str(close_error)[:200]}},
        )

    del provider
    gc.collect()


def reset_stt_provider_runtime(*, restart_warmup: bool = False) -> None:
    """
    Сбрасывает in-memory STT provider, чтобы применить новые runtime-настройки
    (например, смену WHISPER_MODEL_SIZE) без перезапуска процесса.
    """
    global _stt_provider, _stt_warmup_started, _stt_warmup_ready, _stt_warmup_error, _stt_warmup_thread
    with _stt_warmup_lock:
        _stt_provider = None
        _stt_warmup_started = False
        _stt_warmup_ready = False
        _stt_warmup_error = ""
        _stt_warmup_thread = None
    if restart_warmup and bool(getattr(get_settings(), "whisper_warmup_on_start", False)):
        warmup_stt_provider_async()


def stt_runtime_status() -> dict[str, object]:
    """
    Текущее состояние STT runtime для UI-диагностики.
    """
    settings = get_settings()
    provider = str(getattr(settings, "stt_provider", "unknown") or "unknown").strip().lower()
    return {
        "provider": provider,
        "warmup_started": bool(_stt_warmup_started),
        "warmup_ready": bool(_stt_warmup_ready),
        "warmup_error": str(_stt_warmup_error or ""),
        "provider_initialized": _stt_provider is not None,
    }


def verify_stt_provider_connection() -> dict[str, object]:
    settings = get_settings()
    provider_name = str(getattr(settings, "stt_provider", "whisper_local") or "whisper_local").strip().lower()
    try:
        provider = _get_stt_provider()
        verify_fn = getattr(provider, "verify_connection", None)
        if callable(verify_fn):
            message = str(verify_fn() or "").strip()
        elif provider_name == "whisper_local":
            model = str(
                getattr(settings, "whisper_model_size", "")
                or getattr(settings, "stt_model_id", "")
                or "small"
            ).strip()
            message = f"Whisper local готов. Модель {model} загружается без ошибок."
        elif provider_name == "mock":
            message = "Mock STT готов. Это тестовый режим без реального распознавания."
        else:
            message = "STT провайдер инициализирован."
        return {
            "ok": True,
            "provider": provider_name,
            "message": message,
        }
    except Exception as err:
        return {
            "ok": False,
            "provider": provider_name,
            "message": str(err)[:300],
        }


def process_chunk_inline(
    *,
    meeting_id: str,
    chunk_seq: int,
    audio_bytes: bytes | None = None,
    blob_key: str | None = None,
    quality_profile: str = "balanced",
    source_track: str | None = None,
    capture_levels: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """
    Локальная обработка чанка без Redis-очередей.
    """
    if audio_bytes is None:
        if not blob_key:
            raise ValueError("audio_bytes or blob_key required")
        audio_bytes = get_bytes(blob_key)

    stt = _get_stt_provider()
    language_hint = _meeting_language_hint(meeting_id)
    res = stt.transcribe_chunk(
        audio=audio_bytes,
        sample_rate=16000,
        quality_profile=quality_profile,
        source_track=source_track,
        language_hint=language_hint,
        capture_levels=capture_levels,
    )
    text = (res.text or "").strip()
    if not text:
        return []

    with db_session() as session:
        mrepo = MeetingRepository(session)
        srepo = TranscriptSegmentRepository(session)

        m = mrepo.ensure(meeting_id=meeting_id, meeting_context={"source": "inline_pipeline"})
        # Если встречу уже завершили, не возвращаем её обратно в processing.
        m.status = _status_for_chunk_processing(finished_at=m.finished_at)
        mrepo.save(m)

        seg = TranscriptSegment(
            meeting_id=meeting_id,
            seq=chunk_seq,
            speaker=_speaker_from_track(source_track=source_track, meeting_context=m.context) or res.speaker,
            start_ms=None,
            end_ms=None,
            raw_text=text,
            enhanced_text=text,
            confidence=res.confidence,
        )
        srepo.upsert_by_meeting_seq(seg)
        session.flush()

        segs = srepo.list_by_meeting(meeting_id)
        settings = get_settings()
        decisions = infer_speakers(
            [(s.seq, s.raw_text or "", s.enhanced_text or "") for s in segs],
            response_window_sec=settings.speaker_response_window_sec,
        )
        speaker_map = {d.seq: d.speaker for d in decisions if d.speaker is not None}

        for s in segs:
            enh, _meta = enhance_text(s.raw_text or "")
            enh_changed = enh != (s.enhanced_text or "")
            if enh_changed:
                s.enhanced_text = enh

            inferred = speaker_map.get(s.seq)
            speaker_changed = bool(
                inferred
                and inferred != (s.speaker or "")
                and not _speaker_locked_for_track(s.speaker)
            )
            if speaker_changed:
                s.speaker = inferred

    return []


def retranscribe_meeting_high_quality(*, meeting_id: str) -> int:
    """
    Перетранскрибация встречи в финальном (более точном) профиле.

    Используется после Stop/Finish, чтобы улучшить итоговые raw/clean тексты.
    """
    stt = _get_stt_provider()
    updated_segments = 0

    with db_session() as session:
        mrepo = MeetingRepository(session)
        srepo = TranscriptSegmentRepository(session)
        meeting = mrepo.get(meeting_id)
        if not meeting:
            return 0
        language_hint = _language_hint_from_context(meeting.context)

        segs = srepo.list_by_meeting(meeting_id)
        if not segs:
            return 0

        for seg in segs:
            blob_key = f"meetings/{meeting_id}/chunks/{seg.seq}.bin"
            try:
                audio_bytes = get_bytes(blob_key)
            except Exception:
                continue

            current_speaker = (seg.speaker or "").strip().lower()
            source_track = current_speaker if current_speaker in _TRACK_SPEAKERS else None

            try:
                res = stt.transcribe_chunk(
                    audio=audio_bytes,
                    sample_rate=16000,
                    quality_profile="final",
                    source_track=source_track,
                    language_hint=language_hint,
                    capture_levels=None,
                )
            except Exception:
                continue

            next_text = (res.text or "").strip()
            if not next_text:
                continue
            next_enhanced, _meta = enhance_text(next_text)
            next_enhanced = (next_enhanced or next_text).strip()

            changed = False
            if next_text != (seg.raw_text or ""):
                seg.raw_text = next_text
                changed = True
            if next_enhanced != (seg.enhanced_text or ""):
                seg.enhanced_text = next_enhanced
                changed = True
            if res.confidence is not None and res.confidence != seg.confidence:
                seg.confidence = res.confidence
                changed = True
            if res.speaker and current_speaker not in _TRACK_SPEAKERS:
                if res.speaker != seg.speaker:
                    seg.speaker = res.speaker
                    changed = True
            if changed:
                updated_segments += 1

        session.flush()
        segs = srepo.list_by_meeting(meeting_id)
        settings = get_settings()
        decisions = infer_speakers(
            [(s.seq, s.raw_text or "", s.enhanced_text or "") for s in segs],
            response_window_sec=settings.speaker_response_window_sec,
        )
        speaker_map = {d.seq: d.speaker for d in decisions if d.speaker is not None}
        for seg in segs:
            speaker = (seg.speaker or "").strip().lower()
            if speaker in _TRACK_SPEAKERS:
                continue
            inferred = speaker_map.get(seg.seq)
            if inferred and inferred != seg.speaker:
                seg.speaker = inferred

    if updated_segments:
        log.info(
            "meeting_retranscribed_high_quality",
            extra={"payload": {"meeting_id": meeting_id, "updated_segments": updated_segments}},
        )
    return updated_segments


def recover_transcript_from_backup_audio(*, meeting_id: str) -> int:
    """
    Fallback: если live-поток оборвался/потерял часть чанков, добиваем хвост
    из финального аудио-артефакта (backup_audio.*/meeting_audio.mp3/source_upload.*)
    после завершения встречи.
    """
    backup_candidates = (
        "meeting_audio.mp3",
        "backup_audio.mp3",
        "backup_audio.webm",
        "backup_audio.wav",
        "backup_audio.mp4",
        "backup_audio.ogg",
        "backup_audio.m4a",
        "source_upload.mp3",
        "source_upload.wav",
        "source_upload.webm",
        "source_upload.ogg",
        "source_upload.m4a",
        "source_upload.mp4",
    )
    backup_path = None
    for name in backup_candidates:
        if records.exists(meeting_id, name):
            backup_path = records.artifact_path(meeting_id, name)
            break
    if backup_path is None or not backup_path.exists():
        return 0

    try:
        backup_audio = backup_path.read_bytes()
    except Exception:
        return 0
    if not backup_audio:
        return 0

    stt = _get_stt_provider()
    language_hint = _meeting_language_hint(meeting_id)
    try:
        res = stt.transcribe_chunk(
            audio=backup_audio,
            sample_rate=16000,
            quality_profile="final",
            source_track="mixed",
            language_hint=language_hint,
            capture_levels=None,
        )
    except Exception:
        return 0

    backup_text = (res.text or "").strip()
    if not backup_text:
        return 0

    with db_session() as session:
        srepo = TranscriptSegmentRepository(session)
        segs = srepo.list_by_meeting(meeting_id)
        existing_text = "\n".join((seg.raw_text or "").strip() for seg in segs if (seg.raw_text or "").strip())
        missing_tail = _extract_missing_tail(existing_text=existing_text, backup_text=backup_text)
        if not missing_tail:
            return 0

        next_seq = max((seg.seq for seg in segs), default=-1) + 1
        segment = TranscriptSegment(
            meeting_id=meeting_id,
            seq=next_seq,
            speaker="mixed",
            start_ms=None,
            end_ms=None,
            raw_text=missing_tail,
            enhanced_text=missing_tail,
            confidence=res.confidence,
        )
        srepo.upsert_by_meeting_seq(segment)

    log.info(
        "meeting_recovered_from_backup_audio",
        extra={"payload": {"meeting_id": meeting_id, "added_seq": next_seq}},
    )
    return 1


def final_pass_from_backup_audio(*, meeting_id: str) -> int:
    """
    Полный финальный проход по доступному финальному аудио-артефакту
    (backup_audio.*/meeting_audio.mp3/source_upload.*).
    Если артефакт доступен — он становится primary источником итогового transcript.
    """
    backup_candidates = (
        "meeting_audio.mp3",
        "backup_audio.mp3",
        "backup_audio.webm",
        "backup_audio.wav",
        "backup_audio.mp4",
        "backup_audio.ogg",
        "backup_audio.m4a",
        "source_upload.mp3",
        "source_upload.wav",
        "source_upload.webm",
        "source_upload.ogg",
        "source_upload.m4a",
        "source_upload.mp4",
    )
    backup_path = None
    for name in backup_candidates:
        if records.exists(meeting_id, name):
            backup_path = records.artifact_path(meeting_id, name)
            break
    if backup_path is None or not backup_path.exists():
        return 0

    try:
        backup_audio = backup_path.read_bytes()
    except Exception:
        return 0
    if not backup_audio:
        return 0

    stt = _get_stt_provider()
    language_hint = _meeting_language_hint(meeting_id)
    try:
        res = stt.transcribe_chunk(
            audio=backup_audio,
            sample_rate=16000,
            quality_profile="final",
            source_track="mixed",
            language_hint=language_hint,
            capture_levels=None,
        )
    except Exception:
        return 0

    full_text = (res.text or "").strip()
    if not full_text:
        return 0
    parts = _split_final_pass_text(full_text)
    if not parts:
        return 0
    settings = get_settings()
    decisions = infer_speakers(
        [(idx, part, part) for idx, part in enumerate(parts)],
        response_window_sec=settings.speaker_response_window_sec,
    )
    inferred_speakers = {item.seq: item.speaker for item in decisions if item.speaker}

    with db_session() as session:
        srepo = TranscriptSegmentRepository(session)
        # backup-final-pass является primary: пересобираем сегменты целиком.
        session.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).delete()
        for idx, part in enumerate(parts):
            clean_text, _meta = enhance_text(part)
            segment = TranscriptSegment(
                meeting_id=meeting_id,
                seq=idx,
                speaker=str(inferred_speakers.get(idx) or "mixed"),
                start_ms=None,
                end_ms=None,
                raw_text=part,
                enhanced_text=(clean_text or part).strip(),
                confidence=res.confidence,
            )
            srepo.upsert_by_meeting_seq(segment)

    log.info(
        "meeting_final_pass_from_backup_audio",
        extra={"payload": {"meeting_id": meeting_id}},
    )
    return 1
