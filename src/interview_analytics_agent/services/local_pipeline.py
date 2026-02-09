from __future__ import annotations

from typing import Any

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.domain.enums import PipelineStatus
from interview_analytics_agent.processing.enhancer import enhance_text
from interview_analytics_agent.processing.quality import quality_score
from interview_analytics_agent.processing.speaker_rules import infer_speakers
from interview_analytics_agent.storage.blob import get_bytes
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.models import TranscriptSegment
from interview_analytics_agent.storage.repositories import (
    MeetingRepository,
    TranscriptSegmentRepository,
)
from interview_analytics_agent.stt.mock import MockSTTProvider

log = get_project_logger()

_stt_provider = None


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
    global _stt_provider
    if _stt_provider is None:
        _stt_provider = _build_stt_provider()
    return _stt_provider


def process_chunk_inline(
    *,
    meeting_id: str,
    chunk_seq: int,
    audio_bytes: bytes | None = None,
    blob_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Локальная обработка чанка без Redis-очередей.

    Возвращает список payload-ов transcript.update для живого UI.
    """
    if audio_bytes is None:
        if not blob_key:
            raise ValueError("audio_bytes or blob_key required")
        audio_bytes = get_bytes(blob_key)

    stt = _get_stt_provider()
    res = stt.transcribe_chunk(audio=audio_bytes, sample_rate=16000)

    updates: list[dict[str, Any]] = []

    with db_session() as session:
        mrepo = MeetingRepository(session)
        srepo = TranscriptSegmentRepository(session)

        m = mrepo.ensure(meeting_id=meeting_id, meeting_context={"source": "inline_pipeline"})
        m.status = PipelineStatus.processing
        mrepo.save(m)

        seg = TranscriptSegment(
            meeting_id=meeting_id,
            seq=chunk_seq,
            speaker=res.speaker,
            start_ms=None,
            end_ms=None,
            raw_text=res.text or "",
            enhanced_text=res.text or "",
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
            enh, meta = enhance_text(s.raw_text or "")
            enh_changed = enh != (s.enhanced_text or "")
            if enh_changed:
                s.enhanced_text = enh

            inferred = speaker_map.get(s.seq)
            speaker_changed = bool(inferred and inferred != (s.speaker or ""))
            if speaker_changed:
                s.speaker = inferred

            # Для live-UI всегда отдаем update для текущего seq, даже если
            # enh/speaker не изменились, чтобы raw поток показывался сразу.
            if enh_changed or speaker_changed or s.seq == chunk_seq:
                q = quality_score(s.raw_text or "", s.enhanced_text or "")
                updates.append(
                    {
                        "schema_version": "v1",
                        "event_type": "transcript.update",
                        "meeting_id": meeting_id,
                        "seq": s.seq,
                        "speaker": s.speaker,
                        "raw_text": s.raw_text or "",
                        "enhanced_text": s.enhanced_text or "",
                        "confidence": s.confidence,
                        "quality": q,
                        "meta": meta,
                    }
                )

    return updates
