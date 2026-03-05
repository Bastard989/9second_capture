from __future__ import annotations

import csv
import io
import json
import math
import re
import threading
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.common.utils import sha256_hex
from interview_analytics_agent.common.metrics import (
    record_rag_answer_quality,
    record_rag_export_error,
    record_rag_index_latency_ms,
    record_rag_llm_latency_ms,
    record_rag_no_hits,
    record_rag_query_error,
    record_rag_query_latency_ms,
)
from interview_analytics_agent.domain.enums import PipelineStatus
from interview_analytics_agent.processing.aggregation import (
    build_raw_transcript,
)
from interview_analytics_agent.processing.analytics import build_report, report_to_text
from interview_analytics_agent.processing.enhancer import (
    cleanup_transcript_with_llm,
    normalize_transcript_deterministic,
)
from interview_analytics_agent.rag.embeddings import (
    cosine_similarity_dense,
    embed_text_hashing,
    embed_texts_openai_compat,
    hashing_embedding_model_id,
    is_local_openai_compat_base,
)
from interview_analytics_agent.processing.structured import build_structured_rows, structured_to_csv
from interview_analytics_agent.services.audio_artifact_service import (
    CANONICAL_AUDIO_FILENAME,
    materialize_meeting_audio_mp3,
)
from interview_analytics_agent.services.local_pipeline import (
    final_pass_from_backup_audio,
    recover_transcript_from_backup_audio,
    retranscribe_meeting_high_quality,
)
from interview_analytics_agent.storage import records
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import MeetingRepository, TranscriptSegmentRepository

router = APIRouter()
log = get_project_logger()
_TRANSCRIPT_BUILD_LOCKS: dict[str, threading.Lock] = {}
_TRANSCRIPT_BUILD_LOCKS_GUARD = threading.Lock()
LLM_FILES_WORKSPACE_ID = "llm_files_workspace"


class MeetingListItem(BaseModel):
    meeting_id: str
    display_name: str = ""
    record_index: int = 0
    status: str
    created_at: datetime | None
    finished_at: datetime | None
    audio_mp3: bool = False
    artifacts: dict[str, bool] = Field(default_factory=dict)
    rag_index_status: dict[str, str] = Field(default_factory=dict)


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]


TranscriptVariant = Literal["raw", "normalized", "clean"]


class TranscriptGenerateRequest(BaseModel):
    variants: list[TranscriptVariant] = Field(
        default_factory=lambda: ["raw", "normalized", "clean"]
    )
    force_rebuild: bool = False


class TranscriptGenerateItem(BaseModel):
    variant: TranscriptVariant
    filename: str
    chars: int = 0
    generated: bool = False


class TranscriptGenerateResponse(BaseModel):
    ok: bool = True
    meeting_id: str
    items: list[TranscriptGenerateItem] = Field(default_factory=list)


class TranscriptTextResponse(BaseModel):
    ok: bool = True
    meeting_id: str
    variant: TranscriptVariant
    filename: str
    chars: int = 0
    text: str = ""


LLMArtifactMode = Literal["template", "custom", "table"]
LLMArtifactDownloadFormat = Literal["json", "txt", "csv"]


class LLMArtifactGenerateRequest(BaseModel):
    transcript_variant: TranscriptVariant = "clean"
    mode: LLMArtifactMode = "template"
    template_id: str | None = None
    prompt: str | None = None
    input_text: str | None = None
    schema_guide: Any | None = Field(default=None, alias="schema")
    force_rebuild: bool = False


class LLMArtifactFileRef(BaseModel):
    fmt: LLMArtifactDownloadFormat
    filename: str
    bytes: int = 0


class LLMArtifactResponse(BaseModel):
    ok: bool = True
    meeting_id: str
    artifact_id: str
    mode: LLMArtifactMode
    transcript_variant: TranscriptVariant
    template_id: str = ""
    status: str = "ok"
    cached: bool = False
    created_at: str = ""
    transcript_chars: int = 0
    transcript_sha256: str = ""
    result_kind: str = ""
    files: list[LLMArtifactFileRef] = Field(default_factory=list)
    schema_version: str = "v1"


RAGAnswerMode = Literal["none", "llm"]


class RAGIndexRequest(BaseModel):
    transcript_variant: TranscriptVariant = "clean"
    force_rebuild: bool = False
    max_lines_per_chunk: int = Field(default=6, ge=1, le=50)
    overlap_lines: int = Field(default=1, ge=0, le=20)
    max_chars_per_chunk: int = Field(default=1200, ge=100, le=10000)


class RAGIndexResponse(BaseModel):
    ok: bool = True
    meeting_id: str
    transcript_variant: TranscriptVariant
    chunk_count: int = 0
    transcript_chars: int = 0
    transcript_sha256: str = ""
    indexed_at: str = ""
    cached: bool = False
    chunking: dict[str, int] = Field(default_factory=dict)


class RAGIndexJobRequest(BaseModel):
    meeting_ids: list[str] = Field(default_factory=list)
    transcript_variant: TranscriptVariant = "clean"
    force_rebuild: bool = False
    max_lines_per_chunk: int = Field(default=6, ge=1, le=50)
    overlap_lines: int = Field(default=1, ge=0, le=20)
    max_chars_per_chunk: int = Field(default=1200, ge=100, le=10000)


class RAGIndexJobItem(BaseModel):
    meeting_id: str
    status: str = "queued"
    chunk_count: int = 0
    transcript_chars: int = 0
    indexed_at: str = ""
    cached: bool = False
    error: str = ""


class RAGIndexJobStatusResponse(BaseModel):
    ok: bool = True
    job_id: str
    status: str = "queued"
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    transcript_variant: TranscriptVariant = "clean"
    force_rebuild: bool = False
    chunking: dict[str, int] = Field(default_factory=dict)
    total_meetings: int = 0
    completed_meetings: int = 0
    ok_meetings: int = 0
    failed_meetings: int = 0
    progress: float = 0.0
    current_meeting_id: str = ""
    reused_active_job: bool = False
    error: str = ""
    items: list[RAGIndexJobItem] = Field(default_factory=list)


class RAGHit(BaseModel):
    meeting_id: str
    chunk_id: str
    transcript_variant: TranscriptVariant
    score: float = 0.0
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    line_start: int | None = None
    line_end: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    timestamp_start: str = ""
    timestamp_end: str = ""
    speakers: list[str] = Field(default_factory=list)
    text: str = ""
    candidate_name: str = ""
    candidate_id: str = ""
    vacancy: str = ""
    level: str = ""
    interviewer: str = ""


class RAGResultFileRef(BaseModel):
    fmt: Literal["txt", "csv", "json"]
    filename: str
    bytes: int = 0
    download_url: str = ""


class RAGRetrievalMetrics(BaseModel):
    recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    total_relevant_candidates: int = 0


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    transcript_variant: TranscriptVariant = "clean"
    meeting_ids: list[str] = Field(default_factory=list)
    recent_limit: int = Field(default=50, ge=1, le=200)
    top_k: int = Field(default=8, ge=1, le=50)
    auto_index: bool = True
    force_reindex: bool = False
    answer_mode: RAGAnswerMode = "none"
    answer_prompt: str | None = None


class RAGQueryResponse(BaseModel):
    ok: bool = True
    request_id: str = ""
    generated_at: str = ""
    query: str
    transcript_variant: TranscriptVariant
    meeting_ids: list[str] = Field(default_factory=list)
    top_k: int = 0
    retrieval_mode: str = "hybrid_lite"
    index_version: str = ""
    vector_provider: str = ""
    embedding_model: str = ""
    searched_meetings: int = 0
    indexed_meetings: int = 0
    total_chunks_scanned: int = 0
    hits: list[RAGHit] = Field(default_factory=list)
    retrieval_metrics: RAGRetrievalMetrics = Field(default_factory=RAGRetrievalMetrics)
    answer: str = ""
    llm_used: bool = False
    answer_quality: str = "unknown"
    citation_coverage: float = 0.0
    unsupported_claim_rate: float = 0.0
    hallucination_rate: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    files: list[RAGResultFileRef] = Field(default_factory=list)


class ReportRequest(BaseModel):
    source: TranscriptVariant = "clean"


class StructuredRequest(BaseModel):
    source: TranscriptVariant = "clean"


class SeniorBriefRequest(BaseModel):
    source: TranscriptVariant = "clean"


class RenameMeetingRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class CompareMeetingItem(BaseModel):
    meeting_id: str
    created_at: datetime | None = None
    source: TranscriptVariant = "clean"
    candidate_name: str = ""
    candidate_id: str = ""
    vacancy: str = ""
    level: str = ""
    interviewer: str = ""
    overall_score: float = 0.0
    decision_status: str = "insufficient_data"
    decision_confidence: float = 0.0
    transcript_quality: str = "low"
    comparable: bool = False
    summary: str = ""


class CompareMeetingsResponse(BaseModel):
    generated_at: str
    source: TranscriptVariant
    items: list[CompareMeetingItem] = Field(default_factory=list)


class CompareInterviewerItem(BaseModel):
    interviewer: str = ""
    interviews_total: int = 0
    comparable_total: int = 0
    avg_score: float = 0.0
    avg_confidence: float = 0.0
    top_topics: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    decision_breakdown: dict[str, int] = Field(default_factory=dict)
    vacancy_breakdown: dict[str, int] = Field(default_factory=dict)
    level_breakdown: dict[str, int] = Field(default_factory=dict)


class CompareInterviewersResponse(BaseModel):
    generated_at: str
    source: TranscriptVariant
    filters: dict[str, Any] = Field(default_factory=dict)
    items: list[CompareInterviewerItem] = Field(default_factory=list)


def _segments_have_text(segs: list) -> bool:
    for seg in segs:
        if str(getattr(seg, "raw_text", "") or "").strip():
            return True
        if str(getattr(seg, "enhanced_text", "") or "").strip():
            return True
    return False


def _meeting_transcript_lock(meeting_id: str) -> threading.Lock:
    key = str(meeting_id or "").strip() or "__empty__"
    with _TRANSCRIPT_BUILD_LOCKS_GUARD:
        lock = _TRANSCRIPT_BUILD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _TRANSCRIPT_BUILD_LOCKS[key] = lock
        return lock


def _ensure_transcript_segments_ready_impl(meeting_id: str) -> None:
    has_text_segments = False
    meeting_finished = False
    raw_artifact_has_content = False
    with db_session() as session:
        mrepo = MeetingRepository(session)
        meeting = mrepo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        meeting_finished = bool(meeting.finished_at)
        srepo = TranscriptSegmentRepository(session)
        has_text_segments = _segments_have_text(srepo.list_by_meeting(meeting_id))
        if records.exists(meeting_id, "raw.txt"):
            raw_path = records.artifact_path(meeting_id, "raw.txt")
            raw_artifact_has_content = raw_path.exists() and raw_path.stat().st_size > 0
        # После finish первый запрос текста/отчёта должен опираться на финальный аудио-артефакт
        # (MP3/backup), даже если в БД остались live-сегменты.
        need_audio_final_pass = meeting_finished and not raw_artifact_has_content
        if has_text_segments and not need_audio_final_pass:
            return
        if not meeting_finished and not has_text_segments:
            return

    # В record-first режиме финальный текст теперь строится лениво по запросу
    # текста/отчётов, а не на Stop. Сначала стараемся использовать единый audio artifact.
    materialize_meeting_audio_mp3(meeting_id=meeting_id)
    use_audio_final_pass = bool(getattr(get_settings(), "backup_audio_final_pass_enabled", True))
    if use_audio_final_pass:
        used_final_pass = bool(final_pass_from_backup_audio(meeting_id=meeting_id))
        if used_final_pass:
            return

    if has_text_segments:
        # Если live-сегменты уже есть, а final pass по audio не получился
        # (например, нет backup/ffmpeg), используем live fallback без доп. STT.
        return

    retranscribe_meeting_high_quality(meeting_id=meeting_id)
    if bool(getattr(get_settings(), "backup_audio_recovery_enabled", True)):
        recover_transcript_from_backup_audio(meeting_id=meeting_id)


def _ensure_transcript_segments_ready(meeting_id: str) -> None:
    # Защита от параллельного тяжёлого STT final-pass для одного meeting.
    # UI часто делает несколько одновременных запросов raw/clean/report.
    with _meeting_transcript_lock(meeting_id):
        _ensure_transcript_segments_ready_impl(meeting_id)


def _transcript_filename(variant: TranscriptVariant) -> str:
    if variant == "raw":
        return "raw.txt"
    if variant == "normalized":
        return "normalized.txt"
    return "clean.txt"


def _dedupe_transcript_variants(values: list[TranscriptVariant] | None) -> list[TranscriptVariant]:
    requested = list(values or ["raw", "normalized", "clean"])
    seen: set[str] = set()
    ordered: list[TranscriptVariant] = []
    for item in requested:
        value = str(item or "").strip().lower()
        if value not in {"raw", "normalized", "clean"}:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)  # type: ignore[arg-type]
    return ordered or ["raw", "normalized", "clean"]


def _clear_transcript_cache_artifacts(meeting_id: str) -> None:
    for filename in (
        "raw.txt",
        "normalized.txt",
        "clean.txt",
        "clean_llm.txt",
        "clean_llm.meta.json",
    ):
        try:
            path = records.artifact_path(meeting_id, filename)
            path.unlink(missing_ok=True)
        except Exception:
            continue


def _build_normalized_transcript(raw_transcript: str) -> str:
    normalized, _meta = normalize_transcript_deterministic(raw_transcript)
    return (normalized or "").strip()


def _ensure_transcript_variants(
    meeting_id: str,
    *,
    include_normalized: bool = False,
    include_clean: bool = False,
    force_rebuild: bool = False,
) -> dict[str, str]:
    try:
        records.artifact_path(meeting_id, "raw.txt")
        if include_normalized or include_clean:
            records.artifact_path(meeting_id, "normalized.txt")
        if include_clean:
            records.artifact_path(meeting_id, "clean.txt")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")

    if force_rebuild:
        _clear_transcript_cache_artifacts(meeting_id)

    _ensure_transcript_segments_ready(meeting_id)

    with db_session() as session:
        mrepo = MeetingRepository(session)
        meeting = mrepo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        srepo = TranscriptSegmentRepository(session)
        segs = srepo.list_by_meeting(meeting_id)
        raw = build_raw_transcript(segs)
        normalized = ""
        if include_normalized or include_clean:
            normalized = _build_normalized_transcript(raw)
        clean = ""
        if include_clean:
            clean = _maybe_cleanup_clean_transcript_with_cache(
                meeting_id=meeting_id,
                clean_text=normalized,
                segs=segs,
            )
        meeting.raw_transcript = raw
        if include_clean:
            meeting.enhanced_transcript = clean
        elif include_normalized and not str(getattr(meeting, "enhanced_transcript", "") or "").strip():
            # Transitional write for legacy field name; semantically this is a transcript,
            # not an analytics report.
            meeting.enhanced_transcript = normalized
        if meeting.finished_at and meeting.status != PipelineStatus.done:
            meeting.status = PipelineStatus.done
        mrepo.save(meeting)

    records.write_text(meeting_id, "raw.txt", raw)
    if include_normalized or include_clean:
        records.write_text(meeting_id, "normalized.txt", normalized)
    if include_clean:
        records.write_text(meeting_id, "clean.txt", clean)
    return {
        "raw": raw,
        "normalized": normalized,
        "clean": clean,
    }


def _ensure_transcript_text(
    meeting_id: str,
    *,
    variant: TranscriptVariant,
    force_rebuild: bool = False,
) -> str:
    include_normalized = variant in {"normalized", "clean"}
    include_clean = variant == "clean"
    payload = _ensure_transcript_variants(
        meeting_id,
        include_normalized=include_normalized,
        include_clean=include_clean,
        force_rebuild=force_rebuild,
    )
    return str(payload.get(variant) or "")


def _read_transcript_text_artifact(
    meeting_id: str,
    *,
    variant: TranscriptVariant,
) -> str:
    filename = _transcript_filename(variant)
    try:
        path = records.artifact_path(meeting_id, filename)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"transcript_{variant}_not_ready",
        )
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="transcript_read_failed",
        ) from exc


def _ensure_transcripts(meeting_id: str, *, include_clean: bool = True) -> tuple[str, str]:
    payload = _ensure_transcript_variants(
        meeting_id,
        include_normalized=include_clean,
        include_clean=include_clean,
        force_rebuild=False,
    )
    return str(payload.get("raw") or ""), str(payload.get("clean") or "")


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json_canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _safe_artifact_id(artifact_id: str) -> str:
    value = str(artifact_id or "").strip()
    if not value or "/" in value or "\\" in value or ".." in value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_artifact_id")
    return value


def _artifact_file_path(meeting_id: str, artifact_id: str, filename: str):
    aid = _safe_artifact_id(artifact_id)
    rel = f"artifacts/{aid}/{filename}"
    path = records.artifact_path(meeting_id, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_meta_path(meeting_id: str, artifact_id: str):
    return _artifact_file_path(meeting_id, artifact_id, "meta.json")


def _write_artifact_json(meeting_id: str, artifact_id: str, filename: str, payload: Any):
    path = _artifact_file_path(meeting_id, artifact_id, filename)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_artifact_text(meeting_id: str, artifact_id: str, filename: str, text: str):
    path = _artifact_file_path(meeting_id, artifact_id, filename)
    path.write_text(str(text or ""), encoding="utf-8")
    return path


def _write_artifact_bytes(meeting_id: str, artifact_id: str, filename: str, payload: bytes):
    path = _artifact_file_path(meeting_id, artifact_id, filename)
    path.write_bytes(payload)
    return path


def _read_llm_artifact_meta(meeting_id: str, artifact_id: str) -> dict[str, Any]:
    path = _artifact_meta_path(meeting_id, artifact_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="artifact_meta_invalid") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="artifact_meta_invalid")
    return payload


def _artifact_response_from_meta(meta: dict[str, Any], *, cached: bool) -> LLMArtifactResponse:
    files: list[LLMArtifactFileRef] = []
    for item in list(meta.get("files") or []):
        if not isinstance(item, dict):
            continue
        fmt = str(item.get("fmt") or "").strip().lower()
        if fmt not in {"json", "txt", "csv"}:
            continue
        files.append(
            LLMArtifactFileRef(
                fmt=fmt,  # type: ignore[arg-type]
                filename=str(item.get("filename") or ""),
                bytes=int(item.get("bytes") or 0),
            )
        )
    return LLMArtifactResponse(
        meeting_id=str(meta.get("meeting_id") or ""),
        artifact_id=str(meta.get("artifact_id") or ""),
        mode=str(meta.get("mode") or "template"),  # type: ignore[arg-type]
        transcript_variant=str(meta.get("transcript_variant") or "clean"),  # type: ignore[arg-type]
        template_id=str(meta.get("template_id") or ""),
        status=str(meta.get("status") or "ok"),
        cached=bool(cached),
        created_at=str(meta.get("created_at") or ""),
        transcript_chars=int(meta.get("transcript_chars") or 0),
        transcript_sha256=str(meta.get("transcript_sha256") or ""),
        result_kind=str(meta.get("result_kind") or ""),
        files=files,
        schema_version=str(meta.get("schema_version") or "v1"),
    )


def _artifact_result_download_path(meeting_id: str, artifact_id: str, fmt: LLMArtifactDownloadFormat):
    meta = _read_llm_artifact_meta(meeting_id, artifact_id)
    target = None
    for item in list(meta.get("files") or []):
        if isinstance(item, dict) and str(item.get("fmt") or "").strip().lower() == fmt:
            target = str(item.get("filename") or "").strip()
            break
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_format_not_found")
    path = _artifact_file_path(meeting_id, artifact_id, target)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_file_not_found")
    return path


def _build_llm_artifact_orchestrator():
    s = get_settings()
    if not bool(s.llm_enabled):
        return None

    from interview_analytics_agent.llm.mock import MockLLMProvider
    from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider
    from interview_analytics_agent.llm.orchestrator import LLMOrchestrator

    has_api_base = bool((s.openai_api_base or "").strip())
    has_api_key = bool((s.openai_api_key or "").strip())
    if not has_api_base and not has_api_key:
        return LLMOrchestrator(MockLLMProvider())
    return LLMOrchestrator(OpenAICompatProvider())


def _generic_table_json_to_csv(payload: dict[str, Any]) -> bytes:
    columns = [str(c) for c in list(payload.get("columns") or []) if str(c).strip()]
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    if not columns and rows and isinstance(rows[0], dict):
        columns = [str(k) for k in rows[0].keys()]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns or ["value"])
    writer.writeheader()
    if rows and columns:
        for row in rows:
            if isinstance(row, dict):
                writer.writerow({c: row.get(c, "") for c in columns})
            else:
                writer.writerow({columns[0]: str(row)})
    elif rows:
        for row in rows:
            writer.writerow({"value": str(row)})
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _render_template_artifact(*, meeting_id: str, req: LLMArtifactGenerateRequest, transcript_text: str) -> tuple[str, list[dict[str, Any]]]:
    template_id = str(req.template_id or "").strip().lower()
    source = req.transcript_variant
    if template_id in {"", "analysis", "report"}:
        report = build_report(enhanced_transcript=transcript_text, meeting_context={"source": source})
        txt = report_to_text(report)
        json_path = _write_artifact_json(meeting_id, "_tmp_unused", "result.json", report)  # placeholder replaced by caller
        txt_path = _write_artifact_text(meeting_id, "_tmp_unused", "result.txt", txt)
        return "analysis", [
            {"fmt": "json", "filename": json_path.name, "bytes": int(json_path.stat().st_size)},
            {"fmt": "txt", "filename": txt_path.name, "bytes": int(txt_path.stat().st_size)},
        ]
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_template_id")


_FALLBACK_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?…])(?:[\"'\)\]»”’,:;])*\s+")
_FALLBACK_SPACE_RE = re.compile(r"\s+")
_FALLBACK_SPEAKER_LINE_RE = re.compile(r"^([^:\n]{1,64}):\s*(.+)$")
_FALLBACK_CLAUSE_SPLIT_RE = re.compile(r"[,;:]\s+")
_FALLBACK_ATTACHMENT_HEADER_RE = re.compile(
    r"^(?:дополнительные\s+вложения\s+пользователя|additional\s+user\s+attachments)\s*:?\s*$",
    flags=re.IGNORECASE,
)
_FALLBACK_ATTACHMENT_META_LINE_RE = re.compile(r"^-\s+.+\([^)]+\)\s*$")
_FALLBACK_ATTACHMENT_FILE_TAG_RE = re.compile(r"^\[[^\]\n]{1,240}\]\s*$")
_TABLE_COLUMNS_RE = re.compile(r"columns?\s*=\s*\[([^\]]+)\]", flags=re.IGNORECASE)
_TABLE_GENERIC_SPEAKER_LABELS = {
    "mixed",
    "speaker",
    "спикер",
    "system",
    "mic",
    "candidate",
    "interviewer",
    "assistant",
    "user",
}


def _is_attachment_scaffold_line(line: str) -> bool:
    text = str(line or "").strip()
    if not text:
        return True
    if _FALLBACK_ATTACHMENT_HEADER_RE.match(text):
        return True
    if _FALLBACK_ATTACHMENT_META_LINE_RE.match(text):
        return True
    if _FALLBACK_ATTACHMENT_FILE_TAG_RE.match(text):
        return True
    return False


def _split_compact_units(text: str) -> list[str]:
    compact = _FALLBACK_SPACE_RE.sub(" ", str(text or "").strip())
    if not compact:
        return []
    sentence_parts = [part.strip() for part in _FALLBACK_SENTENCE_SPLIT_RE.split(compact) if part.strip()]
    if len(sentence_parts) > 1:
        return sentence_parts
    clause_parts = [part.strip() for part in _FALLBACK_CLAUSE_SPLIT_RE.split(compact) if part.strip()]
    if len(clause_parts) > 1:
        return clause_parts
    if len(compact) <= 320:
        return [compact]

    chunks: list[str] = []
    words = compact.split(" ")
    current: list[str] = []
    current_len = 0
    max_chunk = 260
    for word in words:
        token = str(word or "").strip()
        if not token:
            continue
        added = len(token) + (1 if current else 0)
        if current and current_len + added > max_chunk:
            chunks.append(" ".join(current).strip())
            current = [token]
            current_len = len(token)
        else:
            current.append(token)
            current_len += added
    if current:
        chunks.append(" ".join(current).strip())
    return [part for part in chunks if part]


def _fallback_split_units(transcript: str) -> list[str]:
    lines = [line.strip() for line in (transcript or "").splitlines() if line.strip()]
    units: list[str] = []
    if lines:
        for line in lines:
            if _is_attachment_scaffold_line(line):
                continue
            units.extend(_split_compact_units(line))
        if units:
            return units
    return _split_compact_units(transcript)


def _fallback_clip(text: str, *, limit: int = 220) -> str:
    compact = _FALLBACK_SPACE_RE.sub(" ", str(text or "").strip())
    if len(compact) <= limit:
        return compact
    return compact[: max(24, limit - 1)].rstrip() + "…"


def _infer_meeting_type(transcript: str) -> str:
    text = str(transcript or "").lower()
    if any(token in text for token in ["кандидат", "интервьюер", "собесед", "ваканси", "оценка кандидата"]):
        return "interview"
    if any(token in text for token in ["статус", "стендап", "вчера", "сегодня", "блокер"]):
        return "standup"
    if any(token in text for token in ["план", "спек", "roadmap", "дорожн", "дедлайн"]):
        return "planning"
    if any(token in text for token in ["синк", "sync", "обсудили", "обсуждение", "встреча команды"]):
        return "sync"
    return "other"


def _extract_meeting_fallback(transcript: str) -> dict[str, Any]:
    units = _fallback_split_units(transcript)[:220]
    topics: list[str] = []
    decisions: list[dict[str, str]] = []
    action_items: list[dict[str, str]] = []
    risks: list[str] = []
    blockers: list[str] = []
    open_questions: list[str] = []

    topic_seen: set[str] = set()
    decision_seen: set[str] = set()
    action_seen: set[str] = set()
    risk_seen: set[str] = set()
    blocker_seen: set[str] = set()

    for raw_line in units:
        line = str(raw_line or "").strip()
        if not line:
            continue
        speaker = ""
        text = line
        match = _FALLBACK_SPEAKER_LINE_RE.match(line)
        if match:
            speaker = str(match.group(1) or "").strip()
            text = str(match.group(2) or "").strip()
        if not text:
            continue
        low = text.lower()

        if "?" in text:
            open_questions.append(_fallback_clip(text))

        if any(token in low for token in ["тема", "задач", "план", "спек", "релиз", "проект"]) and len(topic_seen) < 10:
            norm = low[:160]
            if norm not in topic_seen:
                topic_seen.add(norm)
                topics.append(_fallback_clip(text))

        if any(token in low for token in ["решили", "договор", "согласен", "надо переносить", "оставим", "в итоге"]):
            norm = low[:180]
            if norm not in decision_seen:
                decision_seen.add(norm)
                decisions.append(
                    {
                        "text": _fallback_clip(text),
                        "owner": _fallback_clip(speaker, limit=80),
                        "deadline": "",
                    }
                )

        if any(
            token in low
            for token in ["сделать", "сделаю", "нужно", "надо", "проверить", "создам", "напиши", "заведу", "перенос", "доделать"]
        ):
            norm = low[:180]
            if norm not in action_seen:
                action_seen.add(norm)
                action_items.append(
                    {
                        "owner": _fallback_clip(speaker, limit=80),
                        "task": _fallback_clip(text),
                        "due_date": "",
                        "status": "open",
                    }
                )

        if any(token in low for token in ["риск", "проблем", "ошибк", "отстает", "не работает", "уязвим", "атака"]):
            norm = low[:180]
            if norm not in risk_seen:
                risk_seen.add(norm)
                risks.append(_fallback_clip(text))

        if any(token in low for token in ["блокер", "не могу", "не получается", "не знаю, что делать", "нет доступа", "зависим"]):
            norm = low[:180]
            if norm not in blocker_seen:
                blocker_seen.add(norm)
                blockers.append(_fallback_clip(text))

    if not topics:
        topics = [item.get("text", "") for item in decisions[:3] if item.get("text")] or [_fallback_clip(item) for item in units[:5]]

    next_steps = [item.get("task", "") for item in action_items[:10] if item.get("task")]

    return {
        "meeting_type": _infer_meeting_type(transcript),
        "topics": topics[:10],
        "decisions": decisions[:10],
        "action_items": action_items[:20],
        "risks": risks[:12],
        "blockers": blockers[:8],
        "open_questions": open_questions[:12],
        "next_steps": next_steps[:10],
    }


def _prompt_prefers_ru(prompt: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", str(prompt or "")))


def _table_unknown_value(prompt: str) -> str:
    return "Не указан" if _prompt_prefers_ru(prompt) else "Not specified"


def _table_open_status_value(prompt: str) -> str:
    return "В работе" if _prompt_prefers_ru(prompt) else "Open"


def _parse_table_columns_from_prompt(prompt: str) -> list[str]:
    text = str(prompt or "").strip()
    if not text:
        return []
    match = _TABLE_COLUMNS_RE.search(text)
    body = str(match.group(1) or "").strip() if match else ""
    if body:
        cols: list[str] = []
        for raw in body.split(","):
            col = str(raw or "").strip().strip("'\"`")
            if col:
                cols.append(col)
        return cols[:40]

    # Fallback for prompts without columns=[...], e.g.:
    # "...: topic, decision, action_item, owner, due_date, risk, status."
    tail = text
    if ":" in tail:
        tail = tail.split(":", 1)[1]
    tail = str(tail or "").splitlines()[0].strip()
    if not tail or "," not in tail:
        return []

    raw_tokens = [str(item or "").strip().strip("'\"`") for item in tail.split(",")]
    tokens = [token.rstrip(".").strip() for token in raw_tokens if token]
    if not (3 <= len(tokens) <= 20):
        return []
    if not all(re.match(r"^[A-Za-zА-Яа-я0-9_][A-Za-zА-Яа-я0-9_\-/\s]{0,40}$", token) for token in tokens):
        return []
    return tokens[:40]


def _canonical_table_field(value: str) -> str:
    key = re.sub(r"[^a-zа-я0-9]+", "", str(value or "").strip().lower())
    if not key:
        return ""
    if any(token in key for token in ("тема", "topic", "subject")):
        return "topic"
    if any(token in key for token in ("решен", "decision")):
        return "decision"
    if any(token in key for token in ("действ", "action", "task", "nextstep", "actionitem")):
        return "action"
    if any(token in key for token in ("ответств", "owner", "assignee")):
        return "owner"
    if any(token in key for token in ("срок", "duedate", "deadline", "дедлайн")):
        return "due_date"
    if any(token in key for token in ("риск", "risk")):
        return "risk"
    if any(token in key for token in ("статус", "status", "state")):
        return "status"
    return ""


def _extract_explicit_speakers(transcript: str) -> list[str]:
    matches = re.findall(r"(?:^|\n)\s*([^:\n]{1,64}):", str(transcript or ""))
    speakers: list[str] = []
    seen: set[str] = set()
    for raw in matches:
        name = re.sub(r"\s+", " ", str(raw or "").strip())
        low = name.lower()
        if not name or low in _TABLE_GENERIC_SPEAKER_LABELS:
            continue
        if low in seen:
            continue
        seen.add(low)
        speakers.append(name)
    return speakers


def _owner_matches_speakers(owner: str, speakers: list[str]) -> bool:
    value = str(owner or "").strip().lower()
    if not value:
        return False
    for speaker in speakers:
        s = str(speaker or "").strip().lower()
        if not s:
            continue
        if value == s or value.startswith(f"{s} ") or s in value:
            return True
    return False


def _value_explicit_in_transcript(value: str, transcript: str) -> bool:
    candidate = re.sub(r"\s+", " ", str(value or "").strip().lower())
    if not candidate:
        return False
    text = re.sub(r"\s+", " ", str(transcript or "").strip().lower())
    if not text:
        return False
    return candidate in text


def _value_by_canonical(row: dict[str, Any], canonical: str) -> str:
    direct = str(row.get(canonical) or "").strip()
    if direct:
        return direct
    for raw_key, raw_value in row.items():
        if _canonical_table_field(str(raw_key)) == canonical:
            value = str(raw_value or "").strip()
            if value:
                return value
    return ""


def _canonical_rows_from_meeting_fallback(fallback: dict[str, Any]) -> list[dict[str, str]]:
    topics = [str(item).strip() for item in list(fallback.get("topics") or []) if str(item).strip()]
    decisions = [item for item in list(fallback.get("decisions") or []) if isinstance(item, dict)]
    actions = [item for item in list(fallback.get("action_items") or []) if isinstance(item, dict)]
    risks = [str(item).strip() for item in list(fallback.get("risks") or []) if str(item).strip()]
    row_count = max(1, len(topics), len(decisions), len(actions), min(12, len(risks)))
    rows: list[dict[str, str]] = []
    for idx in range(row_count):
        decision_item = decisions[idx] if idx < len(decisions) else {}
        action_item = actions[idx] if idx < len(actions) else {}
        topic = topics[idx] if idx < len(topics) else ""
        decision = str(decision_item.get("text") or "").strip()
        action = str(action_item.get("task") or "").strip()
        owner = str(action_item.get("owner") or decision_item.get("owner") or "").strip()
        due_date = str(action_item.get("due_date") or decision_item.get("deadline") or "").strip()
        risk = risks[idx] if idx < len(risks) else ""
        if not topic:
            topic = decision or action or risk
        rows.append(
            {
                "topic": topic,
                "decision": decision,
                "action": action,
                "owner": owner,
                "due_date": due_date,
                "risk": risk,
                "status": str(action_item.get("status") or "open").strip(),
            }
        )
    return rows[:30]


def _map_canonical_rows_to_columns(
    *,
    canonical_rows: list[dict[str, str]],
    columns: list[str],
    prompt: str,
    transcript_text: str,
) -> list[dict[str, str]]:
    speakers = _extract_explicit_speakers(transcript_text)
    strict_unknown_owner = len(speakers) == 0
    unknown = _table_unknown_value(prompt)
    open_status = _table_open_status_value(prompt)

    rows_out: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    for row in canonical_rows:
        topic = str(row.get("topic") or "").strip()
        decision = str(row.get("decision") or "").strip()
        action = str(row.get("action") or "").strip()
        owner = str(row.get("owner") or "").strip()
        due_date = str(row.get("due_date") or "").strip()
        risk = str(row.get("risk") or "").strip()
        status_value = str(row.get("status") or "").strip()

        if strict_unknown_owner or (owner and not _owner_matches_speakers(owner, speakers)):
            owner = unknown
        elif not owner:
            owner = unknown

        if not due_date or not _value_explicit_in_transcript(due_date, transcript_text):
            due_date = unknown
        if not risk:
            risk = unknown
        if not status_value or status_value.strip().lower() in {"open", "todo", "pending", "draft", "in_progress"}:
            status_value = open_status

        mapped: dict[str, str] = {}
        for col in columns:
            canonical = _canonical_table_field(col)
            if canonical == "topic":
                mapped[col] = topic
            elif canonical == "decision":
                mapped[col] = decision
            elif canonical == "action":
                mapped[col] = action
            elif canonical == "owner":
                mapped[col] = owner
            elif canonical == "due_date":
                mapped[col] = due_date
            elif canonical == "risk":
                mapped[col] = risk
            elif canonical == "status":
                mapped[col] = status_value
            else:
                mapped[col] = str(row.get(col) or "").strip()

        if not any(str(value).strip() for value in mapped.values()):
            continue
        dedupe_key = "|".join(
            [
                topic.lower(),
                decision.lower(),
                action.lower(),
                owner.lower(),
            ]
        ).strip("|")
        if dedupe_key and dedupe_key in seen_keys:
            continue
        if dedupe_key:
            seen_keys.add(dedupe_key)
        rows_out.append(mapped)

    if rows_out:
        return rows_out[:40]
    return [
        {
            col: (
                unknown
                if _canonical_table_field(col) in {"owner", "due_date", "risk"}
                else open_status
                if _canonical_table_field(col) == "status"
                else ""
            )
            for col in columns
        }
    ]


def _normalize_llm_table_payload(
    *,
    payload: Any,
    transcript_text: str,
    user_prompt: str,
) -> dict[str, Any]:
    prompt = str(user_prompt or "").strip()
    requested_columns = _parse_table_columns_from_prompt(prompt)
    data = payload if isinstance(payload, dict) else {}

    columns: list[str] = []
    if requested_columns:
        columns = requested_columns
    elif isinstance(data.get("columns"), list):
        columns = [str(item).strip() for item in list(data.get("columns") or []) if str(item).strip()]

    source_rows = list(data.get("rows") or []) if isinstance(data.get("rows"), list) else []
    if not columns and source_rows and isinstance(source_rows[0], dict):
        columns = [str(k).strip() for k in source_rows[0].keys() if str(k).strip()]
    if not columns:
        if _prompt_prefers_ru(prompt):
            columns = ["Тема", "Решение", "Действие", "Ответственный", "Срок", "Риск", "Статус"]
        else:
            columns = ["Topic", "Decision", "Action", "Owner", "DueDate", "Risk", "Status"]

    canonical_rows: list[dict[str, str]] = []
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        normalized_row = {
            "topic": _value_by_canonical(row, "topic"),
            "decision": _value_by_canonical(row, "decision"),
            "action": _value_by_canonical(row, "action"),
            "owner": _value_by_canonical(row, "owner"),
            "due_date": _value_by_canonical(row, "due_date"),
            "risk": _value_by_canonical(row, "risk"),
            "status": _value_by_canonical(row, "status"),
        }
        if any(
            str(normalized_row.get(key) or "").strip()
            for key in ("topic", "decision", "action", "owner", "due_date", "risk", "status")
        ):
            canonical_rows.append(normalized_row)

    if not canonical_rows:
        canonical_rows = _canonical_rows_from_meeting_fallback(_extract_meeting_fallback(transcript_text))

    rows = _map_canonical_rows_to_columns(
        canonical_rows=canonical_rows,
        columns=columns,
        prompt=prompt,
        transcript_text=transcript_text,
    )

    result: dict[str, Any] = {
        "columns": columns,
        "rows": rows,
        "assumptions": [str(item).strip() for item in list(data.get("assumptions") or []) if str(item).strip()][:12],
        "citations": [str(item).strip() for item in list(data.get("citations") or []) if str(item).strip()][:24],
        "warnings": [str(item).strip() for item in list(data.get("warnings") or []) if str(item).strip()][:12],
    }
    if str(data.get("schema_version") or "").strip():
        result["schema_version"] = str(data.get("schema_version") or "").strip()
    return result


def _custom_json_fallback_payload(
    *,
    meeting_id: str,
    source: TranscriptVariant,
    error_detail: str,
    transcript_text: str,
) -> dict[str, Any]:
    meeting_fallback = _extract_meeting_fallback(transcript_text)
    meeting_type = str(meeting_fallback.get("meeting_type") or "other")
    try:
        report = _load_or_build_report(meeting_id=meeting_id, source=source)
    except Exception:
        report = {}
    highlights = report.get("highlights") if isinstance(report.get("highlights"), dict) else {}
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    skills = [str(item).strip() for item in (highlights.get("strengths") or []) if str(item).strip()]
    concerns = [str(item).strip() for item in (highlights.get("concerns") or []) if str(item).strip()]
    raw_risks = [str(item).strip() for item in (report.get("risk_flags") or []) if str(item).strip()]
    risks = [r.replace("insufficient_interview_evidence", "insufficient_meeting_evidence") for r in raw_risks]
    recommendation = str(report.get("recommendation") or "").strip()
    summary = str(report.get("summary") or "").strip()
    verdict = str(decision.get("status") or "").strip() or "insufficient_data"
    confidence = float(decision.get("confidence") or 0.0)
    if meeting_type != "interview" and verdict == "insufficient_data":
        verdict = "meeting_notes"
        confidence = max(confidence, 0.45)
    evidence: list[str] = []
    if summary:
        evidence.append(summary)
    evidence.extend(concerns[:4])

    raw_recommendations: list[str] = []
    if recommendation and recommendation != "insufficient_data":
        raw_recommendations = [recommendation]
    else:
        raw_recommendations = [str(item).strip() for item in list(meeting_fallback.get("next_steps") or []) if str(item).strip()][:3]

    payload = {
        "schema_version": "v1",
        "meeting_id": meeting_id,
        "source": source,
        "status": "llm_unavailable_fallback",
        "warning": _safe_text(error_detail, limit=240),
        "meeting_type": meeting_type,
        "summary": summary or "LLM unavailable; basic report",
        "topics": list(meeting_fallback.get("topics") or []),
        "decisions": list(meeting_fallback.get("decisions") or []),
        "action_items": list(meeting_fallback.get("action_items") or []),
        "skills": skills,
        "evidence": evidence,
        "risks": list(meeting_fallback.get("risks") or []) or risks,
        "blockers": list(meeting_fallback.get("blockers") or []),
        "open_questions": list(meeting_fallback.get("open_questions") or []),
        "next_steps": list(meeting_fallback.get("next_steps") or []),
        "recommendations": raw_recommendations,
        "итоговый_вердикт": verdict,
        "final_decision": {
            "status": verdict,
            "confidence": confidence,
            "reason": str(decision.get("reason") or "").strip(),
        },
    }
    return payload


def _generate_llm_artifact(meeting_id: str, req: LLMArtifactGenerateRequest) -> tuple[dict[str, Any], bool]:
    direct_input_text = str(req.input_text or "").strip()
    if meeting_id == LLM_FILES_WORKSPACE_ID and not direct_input_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="llm_input_text_required",
        )
    if direct_input_text:
        transcript_text = direct_input_text
        transcript_source = "input_text"
    else:
        transcript_text = _transcript_for_source(meeting_id=meeting_id, source=req.transcript_variant)
        transcript_source = req.transcript_variant
    transcript_sha = sha256_hex(transcript_text.encode("utf-8"))
    s = get_settings()
    fingerprint = {
        "meeting_id": meeting_id,
        "mode": req.mode,
        "template_id": str(req.template_id or ""),
        "prompt": str(req.prompt or ""),
        "schema": req.schema_guide,
        "transcript_variant": req.transcript_variant,
        "transcript_source": transcript_source,
        "transcript_sha256": transcript_sha,
        "llm_enabled": bool(s.llm_enabled),
        "llm_model_id": str(getattr(s, "llm_model_id", "") or ""),
    }
    artifact_id = sha256_hex(_json_canonical_bytes(fingerprint))[:24]

    if not bool(req.force_rebuild):
        try:
            cached_meta = _read_llm_artifact_meta(meeting_id, artifact_id)
            return cached_meta, True
        except HTTPException as exc:
            if exc.status_code != 404:
                raise

    files: list[dict[str, Any]] = []
    result_kind = ""
    template_id = str(req.template_id or "").strip()

    def _save_json_result(payload: Any) -> None:
        path = _write_artifact_json(meeting_id, artifact_id, "result.json", payload)
        files.append({"fmt": "json", "filename": path.name, "bytes": int(path.stat().st_size)})

    def _save_txt_result(text: str) -> None:
        path = _write_artifact_text(meeting_id, artifact_id, "result.txt", text)
        files.append({"fmt": "txt", "filename": path.name, "bytes": int(path.stat().st_size)})

    def _save_csv_result(payload: bytes) -> None:
        path = _write_artifact_bytes(meeting_id, artifact_id, "result.csv", payload)
        files.append({"fmt": "csv", "filename": path.name, "bytes": int(path.stat().st_size)})

    if req.mode == "template":
        tid = template_id.lower()
        if tid in {"", "analysis", "report"}:
            result_kind = "analysis"
            report = build_report(enhanced_transcript=transcript_text, meeting_context={"source": req.transcript_variant})
            _save_json_result(report)
            _save_txt_result(report_to_text(report))
            template_id = "analysis"
        elif tid in {"summary"}:
            result_kind = "summary"
            report = build_report(enhanced_transcript=transcript_text, meeting_context={"source": req.transcript_variant})
            summary_text = str(report.get("summary") or "").strip()
            _save_json_result({"summary": summary_text, "report": report})
            _save_txt_result(summary_text or report_to_text(report))
            template_id = "summary"
        elif tid in {"structured", "structured_table", "table"}:
            result_kind = "table"
            report_file = _report_json_filename(req.transcript_variant)
            report = records.read_json(meeting_id, report_file) if records.exists(meeting_id, report_file) else None
            structured = build_structured_rows(
                meeting_id=meeting_id,
                source=req.transcript_variant,
                transcript=transcript_text,
                report=report,
            )
            _save_json_result(structured)
            _save_csv_result(structured_to_csv(structured))
            template_id = "structured_table"
        elif tid in {"senior_brief", "brief"}:
            result_kind = "text"
            report = _load_or_build_report(meeting_id=meeting_id, source=req.transcript_variant)
            brief = _senior_brief_text(meeting_id=meeting_id, source=req.transcript_variant, report=report)
            _save_txt_result(brief)
            _save_json_result({"text": brief, "template": "senior_brief"})
            template_id = "senior_brief"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_template_id")
    elif req.mode in {"custom", "table"}:
        orch = _build_llm_artifact_orchestrator()
        if orch is None:
            if req.mode == "table":
                result_kind = "table"
                normalized_table = _normalize_llm_table_payload(
                    payload={},
                    transcript_text=transcript_text,
                    user_prompt=str(req.prompt or ""),
                )
                warnings = list(normalized_table.get("warnings") or [])
                warnings.append("llm_unavailable_deterministic_table")
                normalized_table["warnings"] = warnings[:12]
                _save_json_result(normalized_table)
                _save_csv_result(_generic_table_json_to_csv(normalized_table))
            else:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="llm_unavailable")
        else:
            user_prompt = str(req.prompt or "").strip()
            if req.mode == "custom" and not user_prompt:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt_required")
            if req.mode == "table":
                result_kind = "table"
                system = (
                    "Верни ТОЛЬКО валидный JSON с ключами columns, rows, assumptions, citations, warnings. "
                    "rows должен быть массивом объектов. Заполняй только фактами из транскрипта. "
                    "Не выдумывай ответственных, сроки, решения или риски. "
                    "Если ответственный или срок явно не указаны в тексте, верни значение 'Не указан'. "
                    "Если статус не указан явно, используй 'В работе'."
                )
                user = (
                    f"Контекст (source={transcript_source}):\n{transcript_text}\n\n"
                    f"Задача пользователя:\n{user_prompt or 'Сделай структурированную таблицу по интервью.'}\n"
                    f"Желаемая schema (если есть):\n{json.dumps(req.schema_guide, ensure_ascii=False)}"
                )
                table_warn = ""
                try:
                    raw_data = orch.complete_json(system=system, user=user)
                except Exception:
                    raw_data = {}
                    table_warn = "llm_unavailable_deterministic_table"
                data = _normalize_llm_table_payload(
                    payload=raw_data,
                    transcript_text=transcript_text,
                    user_prompt=user_prompt,
                )
                if table_warn:
                    warnings = list(data.get("warnings") or [])
                    warnings.append(table_warn)
                    data["warnings"] = warnings[:12]
                _save_json_result(data)
                _save_csv_result(_generic_table_json_to_csv(data))
            else:
                if req.schema_guide is not None:
                    result_kind = "json"
                    system = (
                        "Верни ТОЛЬКО валидный JSON. Следуй пользовательской схеме и не добавляй текст вне JSON."
                    )
                    user = (
                        f"Контекст (source={transcript_source}):\n{transcript_text}\n\n"
                        f"Запрос:\n{user_prompt}\n\n"
                        f"Schema guide:\n{json.dumps(req.schema_guide, ensure_ascii=False)}"
                    )
                    try:
                        data = orch.complete_json(system=system, user=user)
                    except Exception as exc:
                        detail = _safe_text(exc, limit=220)
                        if not detail.lower().startswith("llm_provider_error:"):
                            detail = f"llm_provider_error:{detail}"
                        data = _custom_json_fallback_payload(
                            meeting_id=meeting_id,
                            source=req.transcript_variant,
                            error_detail=detail,
                            transcript_text=transcript_text,
                        )
                    _save_json_result(data)
                    _save_txt_result(json.dumps(data, ensure_ascii=False, indent=2))
                else:
                    result_kind = "text"
                    system = "Сформируй результат строго на основе предоставленного контекста. Не добавляй выдуманных фактов."
                    user = f"Контекст (source={transcript_source}):\n{transcript_text}\n\nЗапрос:\n{user_prompt}"
                    try:
                        text = orch.complete_text(system=system, user=user).text
                    except Exception as exc:
                        detail = _safe_text(exc, limit=220)
                        if not detail.lower().startswith("llm_provider_error:"):
                            detail = f"llm_provider_error:{detail}"
                        data = _custom_json_fallback_payload(
                            meeting_id=meeting_id,
                            source=req.transcript_variant,
                            error_detail=detail,
                            transcript_text=transcript_text,
                        )
                        _save_json_result(data)
                        _save_txt_result(json.dumps(data, ensure_ascii=False, indent=2))
                        result_kind = "json"
                    else:
                        _save_txt_result(text)
                        _save_json_result({"text": text})
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_mode")

    meta = {
        "schema_version": "v1",
        "artifact_id": artifact_id,
        "meeting_id": meeting_id,
        "mode": req.mode,
        "transcript_variant": req.transcript_variant,
        "transcript_source": transcript_source,
        "template_id": template_id,
        "status": "ok",
        "created_at": _utc_now_iso(),
        "transcript_chars": len(transcript_text),
        "transcript_sha256": transcript_sha,
        "result_kind": result_kind,
        "files": files,
        "request": {
            "prompt": str(req.prompt or ""),
            "schema": req.schema_guide,
            "input_text_chars": len(direct_input_text),
            "force_rebuild": bool(req.force_rebuild),
        },
    }
    _write_artifact_json(meeting_id, artifact_id, "meta.json", meta)
    return meta, False


def _segment_signature(segs: list) -> dict[str, int]:
    return {
        "count": len(segs),
        "max_seq": max((int(getattr(seg, "seq", -1)) for seg in segs), default=-1),
        "raw_chars": sum(len((getattr(seg, "raw_text", "") or "").strip()) for seg in segs),
    }


def _maybe_cleanup_clean_transcript_with_cache(*, meeting_id: str, clean_text: str, segs: list) -> str:
    clean = (clean_text or "").strip()
    if not clean:
        return clean_text
    s = get_settings()
    if not s.llm_enabled or not bool(getattr(s, "llm_transcript_cleanup_enabled", True)):
        return clean_text

    signature = _segment_signature(segs)
    cache_meta_name = "clean_llm.meta.json"
    cache_text_name = "clean_llm.txt"

    try:
        if records.exists(meeting_id, cache_meta_name) and records.exists(meeting_id, cache_text_name):
            meta = records.read_json(meeting_id, cache_meta_name)
            cached_sig = meta.get("segment_signature") if isinstance(meta, dict) else None
            if cached_sig == signature:
                cached_clean = records.read_text(meeting_id, cache_text_name)
                if cached_clean.strip():
                    return cached_clean
    except Exception:
        # cache miss/parse issues -> continue with fresh cleanup
        pass

    cleaned, meta = cleanup_transcript_with_llm(clean)
    cleaned = (cleaned or "").strip()
    if not cleaned:
        return clean_text

    try:
        records.write_text(meeting_id, cache_text_name, cleaned)
        records.write_json(
            meeting_id,
            cache_meta_name,
            {
                "segment_signature": signature,
                "meta": meta,
            },
        )
    except Exception:
        # best-effort cache
        pass
    return cleaned


def _safe_text(value: Any, *, limit: int = 200) -> str:
    return str(value or "").strip()[:limit]


def _extract_compare_meta(context: dict[str, Any] | None) -> dict[str, str]:
    ctx = context or {}
    return {
        "candidate_name": _safe_text(ctx.get("candidate_name"), limit=120),
        "candidate_id": _safe_text(ctx.get("candidate_id"), limit=120),
        "vacancy": _safe_text(ctx.get("vacancy"), limit=160),
        "level": _safe_text(ctx.get("level"), limit=80),
        "interviewer": _safe_text(ctx.get("interviewer"), limit=120),
    }


def _report_json_filename(source: TranscriptVariant) -> str:
    return f"report_{source}.json"


def _report_txt_filename(source: TranscriptVariant) -> str:
    return f"report_{source}.txt"


def _structured_json_filename(source: TranscriptVariant) -> str:
    return f"structured_{source}.json"


def _structured_csv_filename(source: TranscriptVariant) -> str:
    return f"structured_{source}.csv"


def _senior_brief_filename(source: TranscriptVariant) -> str:
    return f"senior_brief_{source}.txt"


def _transcript_for_source(*, meeting_id: str, source: TranscriptVariant) -> str:
    return _read_transcript_text_artifact(meeting_id, variant=source)


_RAG_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-я_+\\-]{2,}", flags=re.UNICODE)
_RAG_SPEAKER_LINE_RE = re.compile(r"^\\s*([^:\\n]{1,80})\\s*:\\s*(.+?)\\s*$")
_RAG_EMBEDDING_CACHE: dict[str, list[float]] = {}
_RAG_EMBEDDING_CACHE_LOCK = threading.RLock()


def _rag_index_relpath(source: TranscriptVariant) -> str:
    return f"artifacts/rag/index_{source}.json"


def _format_ms_timestamp(ms: int | None) -> str:
    if ms is None:
        return ""
    value = max(0, int(ms))
    hours, rem = divmod(value, 3600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _rag_tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _RAG_TOKEN_RE.findall(str(text or ""))]


def _rag_ordered_match_ratio(chunk_tokens: list[str], query_terms: list[str]) -> float:
    if not chunk_tokens or not query_terms:
        return 0.0
    q_idx = 0
    matched = 0
    for tok in chunk_tokens:
        if q_idx >= len(query_terms):
            break
        if tok == query_terms[q_idx]:
            matched += 1
            q_idx += 1
    return float(matched / max(1, len(query_terms)))


def _rag_min_cover_span_ratio(chunk_tokens: list[str], query_terms: list[str]) -> float:
    if not chunk_tokens or not query_terms:
        return 0.0
    needed = set(query_terms)
    if not needed:
        return 0.0
    have: dict[str, int] = {}
    missing = len(needed)
    left = 0
    best_span: int | None = None
    for right, tok in enumerate(chunk_tokens):
        if tok in needed:
            count = int(have.get(tok, 0)) + 1
            have[tok] = count
            if count == 1:
                missing -= 1
        while missing == 0 and left <= right:
            span = right - left + 1
            if best_span is None or span < best_span:
                best_span = span
            lt = chunk_tokens[left]
            if lt in needed:
                count = int(have.get(lt, 0)) - 1
                if count <= 0:
                    have.pop(lt, None)
                    missing += 1
                else:
                    have[lt] = count
            left += 1
    if best_span is None:
        return 0.0
    return float(len(query_terms) / max(len(query_terms), best_span))


def _rag_embedding_batch_size() -> int:
    s = get_settings()
    raw = int(getattr(s, "rag_embedding_batch_size", 24) or 24)
    return max(1, min(raw, 256))


def _rag_embedding_cache_max_items() -> int:
    s = get_settings()
    raw = int(getattr(s, "rag_embedding_cache_max_items", 2048) or 2048)
    return max(0, min(raw, 100_000))


def _rag_embedding_disk_cache_enabled() -> bool:
    s = get_settings()
    return bool(getattr(s, "rag_embedding_disk_cache_enabled", True))


def _rag_embedding_disk_cache_dir() -> Path:
    s = get_settings()
    root = Path((getattr(s, "records_dir", None) or "./data/records").strip()).resolve()
    return root / "_global" / "rag_embeddings_cache"


def _rag_embedding_disk_cache_path(cache_key: str) -> Path:
    key = str(cache_key or "").strip().lower()
    if not key or "/" in key or "\\" in key or ".." in key:
        raise ValueError("invalid_cache_key")
    return _rag_embedding_disk_cache_dir() / key[:2] / f"{key}.json"


def _rag_embedding_disk_cache_read(cache_key: str) -> list[float] | None:
    if not _rag_embedding_disk_cache_enabled():
        return None
    try:
        path = _rag_embedding_disk_cache_path(cache_key)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        payload = raw if isinstance(raw, dict) else {}
        vec = payload.get("vector")
        if not isinstance(vec, list) or not vec:
            return None
        return [float(v or 0.0) for v in vec]
    except Exception:
        return None


def _rag_embedding_disk_cache_write_many(
    *,
    vectors_by_key: dict[str, list[float]],
    vector_cfg: dict[str, Any],
) -> None:
    if not _rag_embedding_disk_cache_enabled() or not vectors_by_key:
        return
    provider = str(vector_cfg.get("provider") or "").strip().lower()
    provider_label = str(vector_cfg.get("provider_label") or provider or "")
    model = str(vector_cfg.get("model") or "")
    try:
        base_dir = _rag_embedding_disk_cache_dir()
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    for key, vec in vectors_by_key.items():
        try:
            path = _rag_embedding_disk_cache_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "rag_embedding_cache_v1",
                        "cached_at": _utc_now_iso(),
                        "provider": provider,
                        "provider_label": provider_label,
                        "model": model,
                        "vector": [float(v or 0.0) for v in list(vec or [])],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
        except Exception:
            continue


def _rag_embedding_cache_key(text: str, *, vector_cfg: dict[str, Any]) -> str:
    provider = str(vector_cfg.get("provider") or "").strip().lower()
    base = str(vector_cfg.get("openai_api_base") or "").rstrip("/")
    payload = {
        "provider": provider,
        "model": str(vector_cfg.get("model") or ""),
        "dim": int(vector_cfg.get("dim") or 0),
        "char_ngrams": bool(vector_cfg.get("char_ngrams", True)),
        "api_base": base if provider == "openai_compat" else "",
        "text_sha256": sha256_hex(str(text or "").encode("utf-8")),
    }
    return sha256_hex(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _rag_vector_config() -> dict[str, Any]:
    s = get_settings()
    enabled = bool(getattr(s, "rag_vector_enabled", True))
    provider_requested = str(getattr(s, "rag_embedding_provider", "auto") or "auto").strip().lower()
    if provider_requested not in {"auto", "hashing", "openai_compat", "ollama"}:
        provider_requested = "auto"
    dim_raw = int(getattr(s, "rag_embedding_dim", 96) or 96)
    dim = max(16, min(dim_raw, 1024))
    char_ngrams = bool(getattr(s, "rag_embedding_char_ngrams", True))
    embedding_model = str(getattr(s, "embedding_model_id", "nomic-embed-text") or "nomic-embed-text").strip()
    embedding_api_base = str(
        getattr(s, "embedding_api_base", "") or getattr(s, "openai_api_base", "") or ""
    ).strip()
    embedding_api_key = str(
        getattr(s, "embedding_api_key", "") or getattr(s, "openai_api_key", "") or ""
    ).strip()
    embedding_timeout_s = max(1.0, float(getattr(s, "rag_embedding_request_timeout_sec", 8.0) or 8.0))
    can_use_openai_compat = bool(embedding_api_base and embedding_model)
    if provider_requested == "hashing":
        resolved_provider = "hashing_local"
    elif provider_requested in {"openai_compat", "ollama"}:
        resolved_provider = "openai_compat" if can_use_openai_compat else "hashing_local"
    else:
        resolved_provider = "openai_compat" if can_use_openai_compat else "hashing_local"
    provider_label = resolved_provider
    if resolved_provider == "openai_compat" and is_local_openai_compat_base(embedding_api_base):
        provider_label = "ollama_openai_compat"
    return {
        "enabled": enabled,
        "requested_provider": provider_requested,
        "provider": resolved_provider,
        "provider_label": provider_label,
        "model": (
            embedding_model
            if resolved_provider == "openai_compat"
            else hashing_embedding_model_id(dim=dim, char_ngrams=char_ngrams)
        ),
        "dim": dim,
        "char_ngrams": char_ngrams,
        "openai_api_base": embedding_api_base if resolved_provider == "openai_compat" else "",
        "openai_api_key": embedding_api_key if resolved_provider == "openai_compat" else "",
        "openai_timeout_s": embedding_timeout_s if resolved_provider == "openai_compat" else 0.0,
    }


def _rag_hashing_fallback_vector_config(vector_cfg: dict[str, Any], *, reason: str = "") -> dict[str, Any]:
    dim = max(16, min(int(vector_cfg.get("dim") or 96), 1024))
    char_ngrams = bool(vector_cfg.get("char_ngrams", True))
    return {
        "enabled": bool(vector_cfg.get("enabled", False)),
        "requested_provider": str(vector_cfg.get("requested_provider") or "hashing"),
        "provider": "hashing_local",
        "provider_label": "hashing_local",
        "model": hashing_embedding_model_id(dim=dim, char_ngrams=char_ngrams),
        "dim": dim,
        "char_ngrams": char_ngrams,
        "openai_api_base": "",
        "openai_api_key": "",
        "openai_timeout_s": 0.0,
        "fallback_reason": str(reason or "").strip(),
    }


def _rag_hybrid_weights(*, vector_enabled: bool) -> tuple[float, float]:
    if not vector_enabled:
        return 1.0, 0.0
    s = get_settings()
    kw = float(getattr(s, "rag_keyword_weight", 0.6) or 0.6)
    vec = float(getattr(s, "rag_vector_weight", 0.4) or 0.4)
    if kw < 0:
        kw = 0.0
    if vec < 0:
        vec = 0.0
    total = kw + vec
    if total <= 0:
        return 0.6, 0.4
    return kw / total, vec / total


def _rag_embed_texts(texts: list[str] | tuple[str, ...], *, vector_cfg: dict[str, Any]) -> list[list[float]]:
    items = [str(text or "") for text in list(texts or [])]
    if not items:
        return []
    if not bool(vector_cfg.get("enabled", False)):
        return [[] for _ in items]

    provider = str(vector_cfg.get("provider") or "").strip().lower()
    cache_keys = [_rag_embedding_cache_key(text, vector_cfg=vector_cfg) for text in items]
    results: list[list[float] | None] = [None] * len(items)
    missing_keys: list[str] = []
    missing_by_key: dict[str, str] = {}

    with _RAG_EMBEDDING_CACHE_LOCK:
        for idx, (text, key) in enumerate(zip(items, cache_keys)):
            cached = _RAG_EMBEDDING_CACHE.get(key)
            if cached is not None:
                results[idx] = list(cached)
                continue
            if key not in missing_by_key:
                missing_by_key[key] = text
                missing_keys.append(key)

    # Disk-backed cache for warm restarts / repeated indexing between process restarts.
    if missing_keys and _rag_embedding_disk_cache_enabled():
        disk_hits_by_key: dict[str, list[float]] = {}
        still_missing: list[str] = []
        for key in missing_keys:
            cached_vec = _rag_embedding_disk_cache_read(key)
            if cached_vec is None:
                still_missing.append(key)
                continue
            disk_hits_by_key[key] = cached_vec
        if disk_hits_by_key:
            cache_limit = _rag_embedding_cache_max_items()
            with _RAG_EMBEDDING_CACHE_LOCK:
                if cache_limit > 0:
                    for key, vec in disk_hits_by_key.items():
                        _RAG_EMBEDDING_CACHE[key] = list(vec)
                    while len(_RAG_EMBEDDING_CACHE) > cache_limit:
                        oldest_key = next(iter(_RAG_EMBEDDING_CACHE), None)
                        if oldest_key is None:
                            break
                        _RAG_EMBEDDING_CACHE.pop(oldest_key, None)
                for idx, key in enumerate(cache_keys):
                    if results[idx] is None and key in disk_hits_by_key:
                        results[idx] = list(disk_hits_by_key[key])
        missing_keys = still_missing

    if missing_keys:
        missing_texts = [missing_by_key[key] for key in missing_keys]
        missing_vectors: list[list[float]] = []
        if provider == "openai_compat":
            batch_size = _rag_embedding_batch_size()
            for start in range(0, len(missing_texts), batch_size):
                batch = missing_texts[start : start + batch_size]
                missing_vectors.extend(
                    embed_texts_openai_compat(
                        batch,
                        api_base=str(vector_cfg.get("openai_api_base") or ""),
                        api_key=str(vector_cfg.get("openai_api_key") or ""),
                        model_id=str(vector_cfg.get("model") or ""),
                        timeout_s=float(vector_cfg.get("openai_timeout_s") or 8.0),
                    )
                )
        else:
            missing_vectors = [
                embed_text_hashing(
                    text,
                    dim=int(vector_cfg.get("dim") or 96),
                    char_ngrams=bool(vector_cfg.get("char_ngrams", True)),
                )
                for text in missing_texts
            ]

        if len(missing_vectors) != len(missing_keys):
            raise RuntimeError(
                f"rag_embeddings_count_mismatch:expected={len(missing_keys)} got={len(missing_vectors)}"
            )

        vector_by_key = {
            key: [float(v or 0.0) for v in list(vec or [])]
            for key, vec in zip(missing_keys, missing_vectors)
        }

        cache_limit = _rag_embedding_cache_max_items()
        with _RAG_EMBEDDING_CACHE_LOCK:
            if cache_limit > 0:
                for key in missing_keys:
                    _RAG_EMBEDDING_CACHE[key] = list(vector_by_key[key])
                while len(_RAG_EMBEDDING_CACHE) > cache_limit:
                    oldest_key = next(iter(_RAG_EMBEDDING_CACHE), None)
                    if oldest_key is None:
                        break
                    _RAG_EMBEDDING_CACHE.pop(oldest_key, None)
            for idx, key in enumerate(cache_keys):
                if results[idx] is None and key in vector_by_key:
                    results[idx] = list(vector_by_key[key])
        _rag_embedding_disk_cache_write_many(vectors_by_key=vector_by_key, vector_cfg=vector_cfg)

    return [list(row or []) for row in results]


def _rag_embed_text(text: str, *, vector_cfg: dict[str, Any]) -> list[float]:
    rows = _rag_embed_texts([text], vector_cfg=vector_cfg)
    return rows[0] if rows else []


def _rag_index_has_compatible_vector_config(index_payload: dict[str, Any], vector_cfg: dict[str, Any]) -> bool:
    current = index_payload.get("vector") if isinstance(index_payload.get("vector"), dict) else {}
    current_enabled = bool(current.get("enabled", False))
    if current_enabled != bool(vector_cfg.get("enabled", False)):
        return False
    if not current_enabled:
        return True
    current_provider = str(current.get("provider") or "")
    target_provider = str(vector_cfg.get("provider") or "")
    if current_provider != target_provider:
        return False
    if current_provider == "openai_compat":
        current_base = str(current.get("openai_api_base") or "").rstrip("/")
        target_base = str(vector_cfg.get("openai_api_base") or "").rstrip("/")
        return (
            str(current.get("model") or "") == str(vector_cfg.get("model") or "")
            and current_base == target_base
        )
    return (
        str(current.get("model") or "") == str(vector_cfg.get("model") or "")
        and int(current.get("dim") or 0) == int(vector_cfg.get("dim") or 0)
        and bool(current.get("char_ngrams", True)) == bool(vector_cfg.get("char_ngrams", True))
    )


def _rag_chunk_embedding(chunk: dict[str, Any], *, vector_cfg: dict[str, Any]) -> list[float]:
    value = chunk.get("embedding")
    if isinstance(value, list) and value:
        try:
            return [float(v or 0.0) for v in value]
        except Exception:
            return []
    if not bool(vector_cfg.get("enabled", False)):
        return []
    try:
        return _rag_embed_text(str(chunk.get("text") or ""), vector_cfg=vector_cfg)
    except Exception:
        if str(vector_cfg.get("provider") or "") == "openai_compat":
            fallback = _rag_hashing_fallback_vector_config(vector_cfg, reason="chunk_embed_fallback")
            return _rag_embed_text(str(chunk.get("text") or ""), vector_cfg=fallback)
        return []


def _rag_indexes_have_vectors(indexes: list[dict[str, Any]]) -> bool:
    for idx in indexes:
        vector = idx.get("vector") if isinstance(idx.get("vector"), dict) else None
        if vector and bool(vector.get("enabled", False)):
            return True
        for chunk in list(idx.get("chunks") or []):
            if isinstance(chunk, dict) and isinstance(chunk.get("embedding"), list) and chunk.get("embedding"):
                return True
    return False


def _rag_primary_index_vector_config(indexes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for idx in indexes:
        vector = idx.get("vector") if isinstance(idx.get("vector"), dict) else None
        if vector and bool(vector.get("enabled", False)):
            return dict(vector)
    return None


def _rag_read_index(meeting_id: str, source: TranscriptVariant) -> dict[str, Any]:
    path = records.artifact_path(meeting_id, _rag_index_relpath(source))
    if not path.exists():
        raise HTTPException(status_code=404, detail="rag_index_not_found")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="rag_index_invalid") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="rag_index_invalid")
    return payload


def _rag_index_status_for_meeting(meeting_id: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for source in ("raw", "normalized", "clean"):
        transcript_filename = _transcript_filename(source)  # type: ignore[arg-type]
        try:
            transcript_path = records.artifact_path(meeting_id, transcript_filename)
            index_path = records.artifact_path(meeting_id, _rag_index_relpath(source))  # type: ignore[arg-type]
        except ValueError:
            statuses[source] = "invalid_meeting_id"
            continue

        transcript_exists = transcript_path.exists()
        index_exists = index_path.exists()
        if not index_exists:
            statuses[source] = "missing"
            continue
        if not transcript_exists:
            statuses[source] = "orphaned"
            continue
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            payload = raw if isinstance(raw, dict) else {}
            index_sha = str(payload.get("transcript_sha256") or "").strip()
            if not index_sha:
                statuses[source] = "invalid"
                continue
            transcript_sha = sha256_hex(transcript_path.read_bytes())
            statuses[source] = "indexed" if transcript_sha == index_sha else "outdated"
        except Exception:
            statuses[source] = "invalid"
    return statuses


def _rag_write_index(meeting_id: str, source: TranscriptVariant, payload: dict[str, Any]) -> None:
    path = records.artifact_path(meeting_id, _rag_index_relpath(source))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rag_segment_line_metadata(meeting_id: str) -> list[dict[str, Any]]:
    with db_session() as session:
        srepo = TranscriptSegmentRepository(session)
        segs = srepo.list_by_meeting(meeting_id)
    rows: list[dict[str, Any]] = []
    for seg in segs:
        raw = str(getattr(seg, "raw_text", "") or "").strip()
        if not raw:
            continue
        rows.append(
            {
                "seq": int(getattr(seg, "seq", 0) or 0),
                "speaker": str(getattr(seg, "speaker", "") or "").strip(),
                "start_ms": int(getattr(seg, "start_ms", 0)) if getattr(seg, "start_ms", None) is not None else None,
                "end_ms": int(getattr(seg, "end_ms", 0)) if getattr(seg, "end_ms", None) is not None else None,
            }
        )
    return rows


def _rag_meeting_meta(meeting_id: str) -> dict[str, Any]:
    display_name = str(records.ensure_meeting_metadata(meeting_id).get("display_name") or meeting_id)
    with db_session() as session:
        repo = MeetingRepository(session)
        meeting = repo.get(meeting_id)
    ctx_meta = _extract_compare_meta(getattr(meeting, "context", None) if meeting else None)
    return {
        "display_name": display_name,
        **ctx_meta,
    }


def _rag_build_line_items(*, transcript_text: str, seg_meta: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = [str(line).strip() for line in str(transcript_text or "").splitlines()]
    lines = [line for line in lines if line]
    items: list[dict[str, Any]] = []
    align_by_index = len(seg_meta) == len(lines) and len(lines) > 0

    for idx, line in enumerate(lines, start=1):
        m = _RAG_SPEAKER_LINE_RE.match(line)
        speaker_from_line = str(m.group(1)).strip() if m else ""
        row: dict[str, Any] = {
            "line_no": idx,
            "text": line,
            "speaker": speaker_from_line,
            "start_ms": None,
            "end_ms": None,
        }
        if align_by_index:
            meta = seg_meta[idx - 1]
            row["speaker"] = str(meta.get("speaker") or row["speaker"] or "").strip()
            row["start_ms"] = meta.get("start_ms")
            row["end_ms"] = meta.get("end_ms")
        items.append(row)
    return items


def _rag_chunk_line_items(
    line_items: list[dict[str, Any]],
    *,
    meeting_id: str,
    source: TranscriptVariant,
    max_lines_per_chunk: int,
    overlap_lines: int,
    max_chars_per_chunk: int,
    meeting_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not line_items:
        return []
    chunks: list[dict[str, Any]] = []
    step = max(1, int(max_lines_per_chunk) - int(overlap_lines))
    chunk_no = 0
    i = 0
    meta = meeting_meta or {}
    while i < len(line_items):
        selected: list[dict[str, Any]] = []
        char_budget = 0
        j = i
        while j < len(line_items) and len(selected) < max_lines_per_chunk:
            line = str(line_items[j].get("text") or "")
            projected = char_budget + (1 if selected else 0) + len(line)
            if selected and projected > max_chars_per_chunk:
                break
            selected.append(line_items[j])
            char_budget = projected
            j += 1
        if not selected:
            selected = [line_items[i]]
            j = i + 1

        chunk_no += 1
        text = "\n".join(str(row.get("text") or "") for row in selected).strip()
        speakers: list[str] = []
        for row in selected:
            sp = str(row.get("speaker") or "").strip()
            if sp and sp not in speakers:
                speakers.append(sp)
        starts = [row.get("start_ms") for row in selected if row.get("start_ms") is not None]
        ends = [row.get("end_ms") for row in selected if row.get("end_ms") is not None]
        start_ms = int(starts[0]) if starts else None
        end_ms = int(ends[-1]) if ends else None
        tokens = _rag_tokenize(text)
        chunks.append(
            {
                "chunk_id": f"c{chunk_no:04d}",
                "meeting_id": meeting_id,
                "transcript_variant": source,
                "text": text,
                "line_start": int(selected[0].get("line_no") or 0) if selected else None,
                "line_end": int(selected[-1].get("line_no") or 0) if selected else None,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "timestamp_start": _format_ms_timestamp(start_ms),
                "timestamp_end": _format_ms_timestamp(end_ms),
                "speakers": speakers,
                "char_count": len(text),
                "token_count": len(tokens),
                "meeting_meta": {
                    "display_name": str(meta.get("display_name") or ""),
                    "candidate_name": str(meta.get("candidate_name") or ""),
                    "candidate_id": str(meta.get("candidate_id") or ""),
                    "vacancy": str(meta.get("vacancy") or ""),
                    "level": str(meta.get("level") or ""),
                    "interviewer": str(meta.get("interviewer") or ""),
                },
            }
        )
        i += step
    return chunks


def _rag_index_response_from_payload(
    payload: dict[str, Any],
    *,
    meeting_id: str,
    source: TranscriptVariant,
    cached: bool,
) -> RAGIndexResponse:
    chunking = payload.get("chunking") if isinstance(payload.get("chunking"), dict) else {}
    return RAGIndexResponse(
        meeting_id=meeting_id,
        transcript_variant=source,
        chunk_count=int(payload.get("chunk_count") or len(list(payload.get("chunks") or []))),
        transcript_chars=int(payload.get("transcript_chars") or 0),
        transcript_sha256=str(payload.get("transcript_sha256") or ""),
        indexed_at=str(payload.get("indexed_at") or ""),
        cached=bool(cached),
        chunking={
            "max_lines_per_chunk": int(chunking.get("max_lines_per_chunk") or 0),
            "overlap_lines": int(chunking.get("overlap_lines") or 0),
            "max_chars_per_chunk": int(chunking.get("max_chars_per_chunk") or 0),
        },
    )


def _ensure_rag_index(
    meeting_id: str,
    *,
    source: TranscriptVariant,
    force_rebuild: bool = False,
    max_lines_per_chunk: int = 6,
    overlap_lines: int = 1,
    max_chars_per_chunk: int = 1200,
) -> tuple[dict[str, Any], bool]:
    started = time.perf_counter()
    try:
        transcript_text = _transcript_for_source(meeting_id=meeting_id, source=source)
        transcript_sha = sha256_hex(transcript_text.encode("utf-8"))
        vector_cfg = _rag_vector_config()
        chunking = {
            "max_lines_per_chunk": int(max_lines_per_chunk),
            "overlap_lines": int(overlap_lines),
            "max_chars_per_chunk": int(max_chars_per_chunk),
        }
        if not force_rebuild:
            try:
                current = _rag_read_index(meeting_id, source)
                same_sha = str(current.get("transcript_sha256") or "") == transcript_sha
                same_chunking = isinstance(current.get("chunking"), dict) and current.get("chunking") == chunking
                same_vector = _rag_index_has_compatible_vector_config(current, vector_cfg)
                if same_sha and same_chunking and same_vector:
                    return current, True
            except HTTPException as exc:
                if exc.status_code != 404:
                    raise

        seg_meta = _rag_segment_line_metadata(meeting_id)
        line_items = _rag_build_line_items(transcript_text=transcript_text, seg_meta=seg_meta)
        meeting_meta = _rag_meeting_meta(meeting_id)
        chunks = _rag_chunk_line_items(
            line_items,
            meeting_id=meeting_id,
            source=source,
            max_lines_per_chunk=max_lines_per_chunk,
            overlap_lines=overlap_lines,
            max_chars_per_chunk=max_chars_per_chunk,
            meeting_meta=meeting_meta,
        )
        active_vector_cfg = dict(vector_cfg)
        if bool(active_vector_cfg.get("enabled", False)):
            try:
                chunk_embeddings = _rag_embed_texts(
                    [str(chunk.get("text") or "") for chunk in chunks],
                    vector_cfg=active_vector_cfg,
                )
                for chunk, emb in zip(chunks, chunk_embeddings):
                    chunk["embedding"] = emb
            except Exception as exc:
                if str(active_vector_cfg.get("provider") or "") == "openai_compat":
                    log.warning(
                        "rag_embeddings_fallback_hashing",
                        extra={
                            "payload": {
                                "meeting_id": meeting_id,
                                "source": source,
                                "provider": str(active_vector_cfg.get("provider_label") or "openai_compat"),
                                "model": str(active_vector_cfg.get("model") or ""),
                                "err": str(exc),
                            }
                        },
                    )
                    active_vector_cfg = _rag_hashing_fallback_vector_config(
                        active_vector_cfg, reason="index_embed_failed"
                    )
                    chunk_embeddings = _rag_embed_texts(
                        [str(chunk.get("text") or "") for chunk in chunks],
                        vector_cfg=active_vector_cfg,
                    )
                    for chunk, emb in zip(chunks, chunk_embeddings):
                        chunk["embedding"] = emb
                else:
                    raise
        payload = {
            "schema_version": "rag_index_v2",
            "meeting_id": meeting_id,
            "transcript_variant": source,
            "transcript_chars": len(transcript_text),
            "transcript_sha256": transcript_sha,
            "chunking": chunking,
            "chunk_count": len(chunks),
            "indexed_at": _utc_now_iso(),
            "meeting_meta": meeting_meta,
            "vector": active_vector_cfg,
            "chunks": chunks,
        }
        _rag_write_index(meeting_id, source, payload)
        return payload, False
    finally:
        record_rag_index_latency_ms(service="api_gateway", elapsed_ms=(time.perf_counter() - started) * 1000.0)


def _safe_meeting_ids(values: list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in list(values or []):
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        try:
            records.artifact_path(value, "noop")
        except ValueError:
            continue
        seen.add(value)
        out.append(value)
    return out


def _rag_select_meeting_ids(*, explicit_ids: list[str], recent_limit: int) -> list[str]:
    ids = _safe_meeting_ids(explicit_ids)
    if ids:
        return ids
    with db_session() as session:
        repo = MeetingRepository(session)
        meetings = repo.list_recent(limit=max(1, min(int(recent_limit), 200)))
    return [str(m.id) for m in meetings if str(getattr(m, "id", "") or "").strip()]


def _rag_clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _rag_relevance_grade(*, chunk_text: str, query_terms: list[str]) -> int:
    if not query_terms:
        return 0
    tokens = _rag_tokenize(chunk_text)
    if not tokens:
        return 0
    token_set = set(tokens)
    matched = sum(1 for t in query_terms if t in token_set)
    coverage = matched / max(1, len(query_terms))
    if coverage >= 0.95:
        return 3
    if coverage >= 0.60:
        return 2
    if coverage >= 0.35:
        return 1
    return 0


def _rag_compute_retrieval_metrics(
    *,
    ranked_rows: list[tuple[float, float, float, dict[str, Any]]],
    query_terms: list[str],
    top_k: int,
) -> RAGRetrievalMetrics:
    if not ranked_rows:
        return RAGRetrievalMetrics()
    grades_all: list[int] = []
    for _score, _kw, _sem, chunk in ranked_rows:
        grades_all.append(_rag_relevance_grade(chunk_text=str(chunk.get("text") or ""), query_terms=query_terms))
    relevant_total = sum(1 for g in grades_all if g > 0)
    if relevant_total <= 0:
        return RAGRetrievalMetrics(total_relevant_candidates=0)

    k = max(1, min(int(top_k), len(ranked_rows)))
    top_grades = grades_all[:k]
    relevant_in_top = sum(1 for g in top_grades if g > 0)
    recall_at_k = relevant_in_top / max(1, relevant_total)

    mrr = 0.0
    for idx, g in enumerate(grades_all, start=1):
        if g > 0:
            mrr = 1.0 / float(idx)
            break

    dcg = 0.0
    for idx, g in enumerate(top_grades, start=1):
        dcg += (2**g - 1) / math.log2(idx + 1)
    ideal = sorted(grades_all, reverse=True)[:k]
    idcg = 0.0
    for idx, g in enumerate(ideal, start=1):
        idcg += (2**g - 1) / math.log2(idx + 1)
    ndcg_at_k = dcg / idcg if idcg > 0 else 0.0

    return RAGRetrievalMetrics(
        recall_at_k=round(_rag_clamp01(recall_at_k), 6),
        mrr=round(_rag_clamp01(mrr), 6),
        ndcg_at_k=round(_rag_clamp01(ndcg_at_k), 6),
        total_relevant_candidates=int(relevant_total),
    )


def _rag_reranker_enabled() -> bool:
    return bool(getattr(get_settings(), "rag_reranker_enabled", True))


def _rag_reranker_top_n() -> int:
    raw = int(getattr(get_settings(), "rag_reranker_top_n", 20) or 20)
    return max(2, min(100, raw))


def _rag_reranker_alpha() -> float:
    raw = float(getattr(get_settings(), "rag_reranker_alpha", 0.35) or 0.35)
    return max(0.0, min(1.0, raw))


def _rag_apply_reranker(
    *,
    ranked_rows: list[tuple[float, float, float, dict[str, Any]]],
    query_text: str,
    query_terms: list[str],
    max_semantic_score: float,
) -> list[tuple[float, float, float, dict[str, Any]]]:
    if not ranked_rows or not _rag_reranker_enabled():
        return ranked_rows
    top_n = min(_rag_reranker_top_n(), len(ranked_rows))
    alpha = _rag_reranker_alpha()
    if top_n <= 1 or alpha <= 0.0:
        return ranked_rows

    head = ranked_rows[:top_n]
    tail = ranked_rows[top_n:]
    q_lower = str(query_text or "").strip().lower()
    reranked: list[tuple[float, float, float, dict[str, Any]]] = []
    for base_score, keyword_score, semantic_score, chunk in head:
        text = str(chunk.get("text") or "")
        lower = text.lower()
        tokens = _rag_tokenize(text)
        token_set = set(tokens)
        coverage = sum(1 for t in query_terms if t in token_set) / max(1, len(query_terms))
        phrase_bonus = 1.0 if q_lower and q_lower in lower else 0.0
        semantic_norm = (float(semantic_score) / max_semantic_score) if max_semantic_score > 0 else 0.0
        rerank_signal = (coverage * 0.65) + (phrase_bonus * 0.25) + (semantic_norm * 0.10)
        final = ((1.0 - alpha) * float(base_score)) + (alpha * rerank_signal)
        reranked.append((final, keyword_score, semantic_score, chunk))
    reranked.sort(key=lambda item: item[0], reverse=True)
    return reranked + tail


def _rag_vector_meta_from_indexes(indexes: list[dict[str, Any]]) -> tuple[str, str, str]:
    # Returns: index_version, vector_provider, embedding_model
    index_version = "rag_index_v2"
    vector_provider = "keyword_only"
    embedding_model = "none"
    if not indexes:
        return index_version, vector_provider, embedding_model

    versions = [str(idx.get("schema_version") or "").strip() for idx in indexes if isinstance(idx, dict)]
    versions = [v for v in versions if v]
    if versions:
        uniq = list(dict.fromkeys(versions))
        index_version = uniq[0] if len(uniq) == 1 else "mixed"

    vector_cfg = _rag_primary_index_vector_config(indexes) if _rag_indexes_have_vectors(indexes) else None
    if vector_cfg:
        vector_provider = str(vector_cfg.get("provider_label") or vector_cfg.get("provider") or "vector").strip() or "vector"
        embedding_model = str(vector_cfg.get("model") or "").strip() or "unknown"
        return index_version, vector_provider, embedding_model

    runtime_cfg = _rag_vector_config()
    if bool(runtime_cfg.get("enabled", False)):
        vector_provider = str(runtime_cfg.get("provider_label") or runtime_cfg.get("provider") or "vector").strip() or "vector"
        embedding_model = str(runtime_cfg.get("model") or "").strip() or "unknown"
    return index_version, vector_provider, embedding_model


def _rag_answer_quality(
    *,
    answer_text: str,
    llm_used: bool,
    hits_count: int,
) -> tuple[str, float, float, float, list[str]]:
    warnings: list[str] = []
    if hits_count <= 0:
        return "no_hits", 0.0, 1.0, 1.0, warnings
    if not llm_used:
        return "retrieval_only", 1.0, 0.0, 0.0, warnings
    answer = str(answer_text or "").strip()
    if not answer:
        warnings.append("answer_empty")
        return "low_confidence", 0.0, 1.0, 1.0, warnings

    cites = re.findall(r"\[(\d+)\]", answer)
    unique_cites = {c for c in cites if str(c).strip().isdigit()}
    has_cites = bool(unique_cites)
    citation_coverage = 1.0 if has_cites else 0.0
    unsupported_claim_rate = 0.0 if has_cites else 1.0
    hallucination_rate = unsupported_claim_rate
    quality = "ok" if has_cites else "low_confidence"
    if not has_cites:
        warnings.append("missing_citations")
    return quality, citation_coverage, unsupported_claim_rate, hallucination_rate, warnings


def _rag_query_output_relpath(request_id: str, filename: str) -> str:
    rid = _safe_artifact_id(request_id)
    return f"artifacts/rag_queries/{rid}/{filename}"


def _rag_query_manifest_relpath(request_id: str) -> str:
    return _rag_query_output_relpath(request_id, "manifest.json")


def _rag_hits_to_csv_bytes(hits: list[RAGHit]) -> bytes:
    output = io.StringIO()
    fieldnames = [
        "rank",
        "score",
        "keyword_score",
        "semantic_score",
        "meeting_id",
        "candidate_name",
        "interviewer",
        "line_start",
        "line_end",
        "timestamp_start",
        "timestamp_end",
        "text",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for idx, hit in enumerate(hits, start=1):
        writer.writerow(
            {
                "rank": idx,
                "score": hit.score,
                "keyword_score": hit.keyword_score,
                "semantic_score": hit.semantic_score,
                "meeting_id": hit.meeting_id,
                "candidate_name": hit.candidate_name,
                "interviewer": hit.interviewer,
                "line_start": hit.line_start if hit.line_start is not None else "",
                "line_end": hit.line_end if hit.line_end is not None else "",
                "timestamp_start": hit.timestamp_start,
                "timestamp_end": hit.timestamp_end,
                "text": hit.text,
            }
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _rag_answer_text_file(*, query: str, answer: str, hits: list[RAGHit]) -> str:
    lines: list[str] = []
    lines.append(f"Query: {str(query or '').strip()}")
    lines.append("")
    lines.append("Answer:")
    lines.append(str(answer or "").strip() or "—")
    lines.append("")
    lines.append("Citations:")
    if not hits:
        lines.append("no_hits")
    else:
        for idx, hit in enumerate(hits, start=1):
            line_span = (
                f"lines={hit.line_start}-{hit.line_end}"
                if hit.line_start is not None and hit.line_end is not None
                else "lines=?-?"
            )
            time_span = f"time={hit.timestamp_start or '?'}..{hit.timestamp_end or '?'}"
            lines.append(f"[{idx}] meeting={hit.meeting_id} chunk={hit.chunk_id} {line_span} {time_span}")
            lines.append(hit.text)
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _rag_store_query_result_files(
    *,
    request_id: str,
    generated_at: str,
    query_resp: RAGQueryResponse,
) -> list[RAGResultFileRef]:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    answer_filename = f"rag_answer_{timestamp}.txt"
    hits_csv_filename = f"rag_hits_topk_{timestamp}.csv"
    hits_json_filename = f"rag_hits_topk_{timestamp}.json"
    files_payload = [
        ("txt", answer_filename, _rag_answer_text_file(query=query_resp.query, answer=query_resp.answer, hits=query_resp.hits).encode("utf-8")),
        ("csv", hits_csv_filename, _rag_hits_to_csv_bytes(query_resp.hits)),
        (
            "json",
            hits_json_filename,
            json.dumps(
                {
                    "query": query_resp.query,
                    "meeting_ids": query_resp.meeting_ids,
                    "top_k": query_resp.top_k,
                    "retrieval_mode": query_resp.retrieval_mode,
                    "hits": [item.model_dump(mode="json") for item in query_resp.hits],
                    "warnings": query_resp.warnings,
                    "llm_used": query_resp.llm_used,
                },
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8"),
        ),
    ]
    out_refs: list[RAGResultFileRef] = []
    for fmt, filename, payload in files_payload:
        rel = _rag_query_output_relpath(request_id, filename)
        path = records.artifact_path(LLM_FILES_WORKSPACE_ID, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        out_refs.append(
            RAGResultFileRef(
                fmt=fmt,  # type: ignore[arg-type]
                filename=filename,
                bytes=int(path.stat().st_size),
                download_url=f"/v1/rag/query/export?request_id={request_id}&fmt={fmt}",
            )
        )

    manifest_rel = _rag_query_manifest_relpath(request_id)
    manifest_path = records.artifact_path(LLM_FILES_WORKSPACE_ID, manifest_rel)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "rag_query_export_v1",
                "request_id": request_id,
                "generated_at": generated_at,
                "files": [item.model_dump(mode="json") for item in out_refs],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out_refs


def _rag_read_query_manifest(request_id: str) -> dict[str, Any]:
    try:
        path = records.artifact_path(LLM_FILES_WORKSPACE_ID, _rag_query_manifest_relpath(request_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_request_id") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="rag_query_export_not_found")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="rag_query_export_manifest_invalid") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="rag_query_export_manifest_invalid")
    return payload


def _rag_query_export_file(
    *,
    request_id: str,
    fmt: Literal["txt", "csv", "json"],
) -> tuple[Path, str]:
    manifest = _rag_read_query_manifest(request_id)
    files = list(manifest.get("files") or [])
    target_name = ""
    for item in files:
        if not isinstance(item, dict):
            continue
        if str(item.get("fmt") or "").strip().lower() == str(fmt).strip().lower():
            target_name = str(item.get("filename") or "").strip()
            break
    if not target_name:
        raise HTTPException(status_code=404, detail="rag_query_export_format_not_found")
    try:
        path = records.artifact_path(LLM_FILES_WORKSPACE_ID, _rag_query_output_relpath(request_id, target_name))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_request_id") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="rag_query_export_not_found")
    return path, target_name

def _rag_rank_hits(
    *,
    query: str,
    indexes: list[dict[str, Any]],
    transcript_variant: TranscriptVariant,
    top_k: int,
) -> tuple[list[RAGHit], int, str, RAGRetrievalMetrics]:
    q_text = str(query or "").strip()
    q_terms_all = _rag_tokenize(q_text)
    if not q_terms_all:
        return [], 0, "keyword_only", RAGRetrievalMetrics()
    q_terms_unique = list(dict.fromkeys(q_terms_all))
    q_term_qtf = Counter(q_terms_all)

    all_chunks: list[dict[str, Any]] = []
    for idx in indexes:
        for chunk in list(idx.get("chunks") or []):
            if isinstance(chunk, dict):
                all_chunks.append(chunk)
    total_chunks = len(all_chunks)
    if total_chunks == 0:
        return [], 0, "keyword_only", RAGRetrievalMetrics()

    indexes_have_vectors = _rag_indexes_have_vectors(indexes)
    runtime_vector_cfg = _rag_vector_config()
    index_vector_cfg = _rag_primary_index_vector_config(indexes) if indexes_have_vectors else None
    if index_vector_cfg:
        # Prefer the provider/model that matches stored chunk embeddings.
        vector_cfg = dict(runtime_vector_cfg)
        vector_cfg["enabled"] = bool(index_vector_cfg.get("enabled", False))
        vector_cfg["provider"] = str(index_vector_cfg.get("provider") or vector_cfg.get("provider") or "")
        vector_cfg["provider_label"] = str(
            index_vector_cfg.get("provider_label") or vector_cfg.get("provider_label") or ""
        )
        vector_cfg["model"] = str(index_vector_cfg.get("model") or vector_cfg.get("model") or "")
        if vector_cfg.get("provider") == "openai_compat":
            vector_cfg["openai_api_base"] = str(
                index_vector_cfg.get("openai_api_base") or vector_cfg.get("openai_api_base") or ""
            )
            vector_cfg["openai_api_key"] = str(vector_cfg.get("openai_api_key") or "")
            vector_cfg["openai_timeout_s"] = float(vector_cfg.get("openai_timeout_s") or 8.0)
        else:
            vector_cfg["dim"] = int(index_vector_cfg.get("dim") or vector_cfg.get("dim") or 96)
            vector_cfg["char_ngrams"] = bool(
                index_vector_cfg.get("char_ngrams")
                if index_vector_cfg.get("char_ngrams") is not None
                else vector_cfg.get("char_ngrams", True)
            )
    else:
        vector_cfg = runtime_vector_cfg

    vector_runtime_enabled = bool(vector_cfg.get("enabled", False))
    query_embedding: list[float] = []
    query_vector_provider = ""
    if vector_runtime_enabled:
        try:
            query_embedding = _rag_embed_text(q_text, vector_cfg=vector_cfg)
            query_vector_provider = str(vector_cfg.get("provider") or "")
        except Exception as exc:
            if str(vector_cfg.get("provider") or "") == "openai_compat" and index_vector_cfg:
                # Stored vectors were built by OpenAI/Ollama provider; hashing fallback would be incompatible.
                log.warning(
                    "rag_query_embeddings_unavailable",
                    extra={
                        "payload": {
                            "provider": str(vector_cfg.get("provider_label") or "openai_compat"),
                            "model": str(vector_cfg.get("model") or ""),
                            "err": str(exc),
                        }
                    },
                )
                vector_runtime_enabled = False
                query_embedding = []
            else:
                fallback_cfg = _rag_hashing_fallback_vector_config(vector_cfg, reason="query_embed_failed")
                try:
                    query_embedding = _rag_embed_text(q_text, vector_cfg=fallback_cfg)
                    query_vector_provider = "hashing_local"
                    vector_cfg = fallback_cfg
                except Exception:
                    vector_runtime_enabled = False
                    query_embedding = []

    # BM25-lite IDF over selected candidate chunks.
    df: dict[str, int] = {t: 0 for t in q_terms_unique}
    chunk_term_counters: list[Counter[str]] = []
    chunk_tokens_all: list[list[str]] = []
    avg_len = 0.0
    for chunk in all_chunks:
        chunk_tokens_list = _rag_tokenize(str(chunk.get("text") or ""))
        chunk_tokens_all.append(chunk_tokens_list)
        counter = Counter(chunk_tokens_list)
        chunk_term_counters.append(counter)
        avg_len += sum(counter.values())
        present = set(counter.keys())
        for t in q_terms_unique:
            if t in present:
                df[t] = int(df.get(t, 0)) + 1
    avg_len = avg_len / max(1, len(all_chunks))
    q_lower = q_text.lower()

    candidates: list[dict[str, Any]] = []
    max_keyword = 0.0
    max_semantic = 0.0
    for chunk, counter, chunk_tokens_list in zip(all_chunks, chunk_term_counters, chunk_tokens_all):
        chunk_tokens = sum(counter.values())
        chunk_text = str(chunk.get("text") or "")
        chunk_lower = chunk_text.lower()
        meeting_meta = chunk.get("meeting_meta") if isinstance(chunk.get("meeting_meta"), dict) else {}
        meta_text = " ".join(
            [
                str(meeting_meta.get("candidate_name") or ""),
                str(meeting_meta.get("vacancy") or ""),
                str(meeting_meta.get("level") or ""),
                str(meeting_meta.get("interviewer") or ""),
            ]
        ).lower()

        keyword_score = 0.0
        k1 = 1.2
        b = 0.75
        k3 = 8.0  # query term frequency saturation (small, but non-zero effect)
        for t in q_terms_unique:
            tf = int(counter.get(t, 0))
            if tf <= 0:
                continue
            dfi = max(0, int(df.get(t, 0)))
            idf = math.log(1.0 + ((total_chunks - dfi + 0.5) / (dfi + 0.5)))
            denom = tf + k1 * (1 - b + b * (chunk_tokens / max(1.0, avg_len)))
            qtf = max(1, int(q_term_qtf.get(t, 1)))
            qtf_weight = ((k3 + 1.0) * qtf) / (k3 + qtf)
            base = (tf * (k1 + 1.0)) / max(0.0001, denom)
            # BM25+ style delta protects longer chunks from being overly penalized.
            keyword_score += idf * ((base + 0.25) * qtf_weight)

        # simple phrase/subsequence boosts
        if q_lower and q_lower in chunk_lower:
            keyword_score += 1.25
        overlap = sum(1 for t in q_terms_unique if t in chunk_lower)
        if overlap:
            keyword_score += min(0.5, overlap * 0.08)
        meta_overlap = sum(1 for t in q_terms_unique if t in meta_text)
        if meta_overlap:
            keyword_score += min(0.4, meta_overlap * 0.06)
        coverage = float(sum(1 for t in q_terms_unique if counter.get(t, 0) > 0) / max(1, len(q_terms_unique)))
        if coverage > 0:
            keyword_score += min(0.55, coverage * 0.28)
        if len(q_terms_unique) >= 2 and chunk_tokens_list:
            ordered_ratio = _rag_ordered_match_ratio(chunk_tokens_list, q_terms_unique)
            if ordered_ratio > 0:
                keyword_score += min(0.35, ordered_ratio * 0.18)
            if coverage >= 0.999:
                span_ratio = _rag_min_cover_span_ratio(chunk_tokens_list, q_terms_unique)
                if span_ratio > 0:
                    keyword_score += min(0.45, span_ratio * 0.22)

        semantic_score = 0.0
        if query_embedding and bool(vector_cfg.get("enabled", False)):
            chunk_embedding = _rag_chunk_embedding(chunk, vector_cfg=vector_cfg)
            if chunk_embedding:
                semantic_score = max(0.0, cosine_similarity_dense(query_embedding, chunk_embedding))

        if keyword_score <= 0 and semantic_score <= 0:
            continue
        max_keyword = max(max_keyword, float(keyword_score))
        max_semantic = max(max_semantic, float(semantic_score))
        candidates.append(
            {
                "chunk": chunk,
                "keyword_score": float(keyword_score),
                "semantic_score": float(semantic_score),
            }
        )

    if not candidates:
        retrieval_mode = (
            "hybrid_ollama_vector"
            if vector_runtime_enabled and query_vector_provider == "openai_compat" and str(vector_cfg.get("provider_label") or "").startswith("ollama")
            else "hybrid_openai_vector"
            if vector_runtime_enabled and query_vector_provider == "openai_compat"
            else "hybrid_hash_vector"
            if vector_runtime_enabled
            else "keyword_only"
        )
        return [], total_chunks, retrieval_mode, RAGRetrievalMetrics()

    hybrid_vector_enabled = bool(vector_runtime_enabled and max_semantic > 0.0)
    kw_weight, vec_weight = _rag_hybrid_weights(vector_enabled=hybrid_vector_enabled)

    ranked: list[tuple[float, float, float, dict[str, Any]]] = []
    for item in candidates:
        chunk = item["chunk"]
        keyword_score = float(item["keyword_score"])
        semantic_score = float(item["semantic_score"])
        keyword_norm = (keyword_score / max_keyword) if max_keyword > 0 else 0.0
        semantic_norm = (semantic_score / max_semantic) if max_semantic > 0 else 0.0
        final_score = (kw_weight * keyword_norm) + (vec_weight * semantic_norm)
        # Small deterministic tie-breakers to preserve exact phrase/query overlap preference.
        chunk_text = str(chunk.get("text") or "")
        chunk_lower = chunk_text.lower()
        if q_lower and q_lower in chunk_lower:
            final_score += 0.03
        final_score += min(0.02, max(0.0, semantic_score) * 0.02)
        if final_score <= 0:
            continue
        ranked.append((final_score, keyword_score, semantic_score, chunk))

    ranked.sort(key=lambda item: item[0], reverse=True)
    ranked = _rag_apply_reranker(
        ranked_rows=ranked,
        query_text=q_text,
        query_terms=q_terms_unique,
        max_semantic_score=max_semantic,
    )
    retrieval_metrics = _rag_compute_retrieval_metrics(
        ranked_rows=ranked,
        query_terms=q_terms_unique,
        top_k=top_k,
    )
    hits: list[RAGHit] = []
    for final_score, keyword_score, semantic_score, chunk in ranked[: max(1, min(top_k, 50))]:
        meeting_meta = chunk.get("meeting_meta") if isinstance(chunk.get("meeting_meta"), dict) else {}
        hits.append(
            RAGHit(
                meeting_id=str(chunk.get("meeting_id") or ""),
                chunk_id=str(chunk.get("chunk_id") or ""),
                transcript_variant=transcript_variant,
                score=round(float(final_score), 6),
                keyword_score=round(float(keyword_score), 6),
                semantic_score=round(float(semantic_score), 6),
                line_start=int(chunk.get("line_start")) if chunk.get("line_start") is not None else None,
                line_end=int(chunk.get("line_end")) if chunk.get("line_end") is not None else None,
                start_ms=int(chunk.get("start_ms")) if chunk.get("start_ms") is not None else None,
                end_ms=int(chunk.get("end_ms")) if chunk.get("end_ms") is not None else None,
                timestamp_start=str(chunk.get("timestamp_start") or ""),
                timestamp_end=str(chunk.get("timestamp_end") or ""),
                speakers=[str(v) for v in list(chunk.get("speakers") or []) if str(v).strip()],
                text=str(chunk.get("text") or ""),
                candidate_name=str(meeting_meta.get("candidate_name") or ""),
                candidate_id=str(meeting_meta.get("candidate_id") or ""),
                vacancy=str(meeting_meta.get("vacancy") or ""),
                level=str(meeting_meta.get("level") or ""),
                interviewer=str(meeting_meta.get("interviewer") or ""),
            )
        )
    retrieval_mode = (
        "hybrid_ollama_vector"
        if hybrid_vector_enabled and query_vector_provider == "openai_compat" and str(vector_cfg.get("provider_label") or "").startswith("ollama")
        else "hybrid_openai_vector"
        if hybrid_vector_enabled and query_vector_provider == "openai_compat"
        else "hybrid_hash_vector"
        if hybrid_vector_enabled
        else "keyword_only"
    )
    return hits, total_chunks, retrieval_mode, retrieval_metrics


def _rag_answer_from_hits(
    *,
    query: str,
    hits: list[RAGHit],
    prompt_override: str | None = None,
) -> tuple[str, bool, list[str]]:
    warnings: list[str] = []
    if not hits:
        return "", False, ["no_hits"]
    orch = _build_llm_artifact_orchestrator()
    if orch is None:
        return "", False, ["llm_unavailable"]

    citations_blocks: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        lines_label = ""
        if hit.line_start is not None and hit.line_end is not None:
            lines_label = f"lines={hit.line_start}-{hit.line_end}"
        time_label = ""
        if hit.timestamp_start or hit.timestamp_end:
            time_label = f"time={hit.timestamp_start or '?'}..{hit.timestamp_end or '?'}"
        meta_parts = [p for p in [lines_label, time_label, f"meeting={hit.meeting_id}", f"chunk={hit.chunk_id}"] if p]
        header = f"[{idx}] " + " ".join(meta_parts)
        citations_blocks.append(header + "\n" + hit.text)

    system = (
        "Ответь строго на основе цитат из транскриптов. "
        "Если данных недостаточно — скажи это явно. "
        "Ссылайся на источники в формате [n]."
    )
    user = (
        f"Вопрос пользователя:\n{query}\n\n"
        f"Доп. инструкция:\n{str(prompt_override or '').strip() or 'Кратко ответь и укажи ключевые цитаты.'}\n\n"
        f"Цитаты:\n\n" + "\n\n".join(citations_blocks)
    )
    try:
        text = orch.complete_text(system=system, user=user).text
        return str(text or "").strip(), True, warnings
    except Exception:
        return "", False, ["llm_error"]


def _rag_query(req: RAGQueryRequest) -> RAGQueryResponse:
    started = time.perf_counter()
    request_id = f"ragq_{uuid.uuid4().hex[:16]}"
    generated_at = _utc_now_iso()
    warnings: list[str] = []
    meeting_ids = _rag_select_meeting_ids(explicit_ids=req.meeting_ids, recent_limit=req.recent_limit)
    try:
        indexes: list[dict[str, Any]] = []
        if not meeting_ids:
            warnings.append("no_meetings_selected")
        else:
            for meeting_id in meeting_ids:
                try:
                    if req.auto_index:
                        index, _cached = _ensure_rag_index(
                            meeting_id,
                            source=req.transcript_variant,
                            force_rebuild=bool(req.force_reindex),
                        )
                    else:
                        index = _rag_read_index(meeting_id, req.transcript_variant)
                    indexes.append(index)
                except Exception:
                    warnings.append(f"index_failed:{meeting_id}")
                    record_rag_query_error(reason="index_failed")
                    continue

        index_version, vector_provider, embedding_model = _rag_vector_meta_from_indexes(indexes)
        hits, total_chunks, retrieval_mode, retrieval_metrics = _rag_rank_hits(
            query=req.query,
            indexes=indexes,
            transcript_variant=req.transcript_variant,
            top_k=req.top_k,
        )
        if not hits:
            record_rag_no_hits()

        answer = ""
        llm_used = False
        if req.answer_mode == "llm":
            llm_started = time.perf_counter()
            answer, llm_used, answer_warnings = _rag_answer_from_hits(
                query=req.query,
                hits=hits,
                prompt_override=req.answer_prompt,
            )
            record_rag_llm_latency_ms(service="api_gateway", elapsed_ms=(time.perf_counter() - llm_started) * 1000.0)
            warnings.extend(answer_warnings)

        answer_quality, citation_coverage, unsupported_claim_rate, hallucination_rate, quality_warnings = _rag_answer_quality(
            answer_text=answer,
            llm_used=llm_used,
            hits_count=len(hits),
        )
        warnings.extend(quality_warnings)
        quality_score = 1.0 - max(unsupported_claim_rate, hallucination_rate)
        record_rag_answer_quality(
            citation_coverage=citation_coverage,
            answer_quality_score=quality_score,
            recall_at_k=retrieval_metrics.recall_at_k,
            mrr=retrieval_metrics.mrr,
            ndcg_at_k=retrieval_metrics.ndcg_at_k,
        )

        response = RAGQueryResponse(
            request_id=request_id,
            generated_at=generated_at,
            query=req.query,
            transcript_variant=req.transcript_variant,
            meeting_ids=list(meeting_ids),
            top_k=int(req.top_k),
            retrieval_mode=retrieval_mode,
            index_version=index_version,
            vector_provider=vector_provider,
            embedding_model=embedding_model,
            searched_meetings=len(meeting_ids),
            indexed_meetings=len(indexes),
            total_chunks_scanned=total_chunks,
            hits=hits,
            retrieval_metrics=retrieval_metrics,
            answer=answer,
            llm_used=llm_used,
            answer_quality=answer_quality,
            citation_coverage=round(_rag_clamp01(citation_coverage), 6),
            unsupported_claim_rate=round(_rag_clamp01(unsupported_claim_rate), 6),
            hallucination_rate=round(_rag_clamp01(hallucination_rate), 6),
            warnings=warnings,
            files=[],
        )

        try:
            files = _rag_store_query_result_files(
                request_id=request_id,
                generated_at=generated_at,
                query_resp=response,
            )
            response.files = files
        except Exception:
            record_rag_export_error(reason="write_failed")
            response.warnings.append("export_write_failed")
        return response
    except HTTPException as exc:
        record_rag_query_error(reason=str(exc.detail or "http_error"))
        raise
    except Exception:
        record_rag_query_error(reason="unhandled_error")
        raise
    finally:
        record_rag_query_latency_ms(service="api_gateway", elapsed_ms=(time.perf_counter() - started) * 1000.0)


@dataclass
class _RAGIndexJobRow:
    meeting_id: str
    status: str = "queued"
    chunk_count: int = 0
    transcript_chars: int = 0
    indexed_at: str = ""
    cached: bool = False
    error: str = ""


@dataclass
class _RAGIndexJob:
    job_id: str
    meeting_ids: list[str]
    transcript_variant: TranscriptVariant
    force_rebuild: bool
    max_lines_per_chunk: int
    overlap_lines: int
    max_chars_per_chunk: int
    status: str = "queued"
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    current_meeting_id: str = ""
    error: str = ""
    items: list[_RAGIndexJobRow] = field(default_factory=list)


def _rag_index_job_error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        try:
            return str(exc.detail or f"http_{exc.status_code}")[:240]
        except Exception:
            return f"http_{exc.status_code}"
    return str(exc or "error")[:240]


class RAGIndexJobManager:
    def __init__(self, *, max_jobs: int = 64) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, _RAGIndexJob] = {}
        self._active_job_id: str | None = None
        self._latest_job_id: str | None = None
        self._max_jobs = max(4, int(max_jobs))

    def _trim_jobs_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return
        removable = [
            job_id
            for job_id, job in self._jobs.items()
            if job_id != self._active_job_id and job.status in {"completed", "failed"}
        ]
        removable.sort(key=lambda job_id: str(self._jobs[job_id].created_at or ""))
        while len(self._jobs) > self._max_jobs and removable:
            old_id = removable.pop(0)
            self._jobs.pop(old_id, None)
            if self._latest_job_id == old_id:
                self._latest_job_id = None

    def _status_snapshot(self, job: _RAGIndexJob, *, reused_active_job: bool = False) -> RAGIndexJobStatusResponse:
        items = [
            RAGIndexJobItem(
                meeting_id=row.meeting_id,
                status=row.status,
                chunk_count=int(row.chunk_count or 0),
                transcript_chars=int(row.transcript_chars or 0),
                indexed_at=str(row.indexed_at or ""),
                cached=bool(row.cached),
                error=str(row.error or ""),
            )
            for row in job.items
        ]
        total = len(items)
        completed = sum(1 for row in items if row.status in {"completed", "failed"})
        ok_count = sum(1 for row in items if row.status == "completed")
        failed_count = sum(1 for row in items if row.status == "failed")
        progress = 1.0 if total == 0 and job.status in {"completed", "failed"} else (completed / max(1, total))
        return RAGIndexJobStatusResponse(
            job_id=job.job_id,
            status=str(job.status or "queued"),
            created_at=str(job.created_at or ""),
            started_at=str(job.started_at or ""),
            finished_at=str(job.finished_at or ""),
            transcript_variant=job.transcript_variant,
            force_rebuild=bool(job.force_rebuild),
            chunking={
                "max_lines_per_chunk": int(job.max_lines_per_chunk),
                "overlap_lines": int(job.overlap_lines),
                "max_chars_per_chunk": int(job.max_chars_per_chunk),
            },
            total_meetings=total,
            completed_meetings=completed,
            ok_meetings=ok_count,
            failed_meetings=failed_count,
            progress=round(float(progress), 6),
            current_meeting_id=str(job.current_meeting_id or ""),
            reused_active_job=bool(reused_active_job),
            error=str(job.error or ""),
            items=items,
        )

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = _utc_now_iso()

        try:
            for row in list(job.items):
                with self._lock:
                    current = self._jobs.get(job_id)
                    if not current:
                        return
                    current.current_meeting_id = row.meeting_id
                    row.status = "running"
                try:
                    payload, cached = _ensure_rag_index(
                        row.meeting_id,
                        source=job.transcript_variant,
                        force_rebuild=bool(job.force_rebuild),
                        max_lines_per_chunk=int(job.max_lines_per_chunk),
                        overlap_lines=int(job.overlap_lines),
                        max_chars_per_chunk=int(job.max_chars_per_chunk),
                    )
                    row.status = "completed"
                    row.cached = bool(cached)
                    row.chunk_count = int(payload.get("chunk_count") or len(list(payload.get("chunks") or [])))
                    row.transcript_chars = int(payload.get("transcript_chars") or 0)
                    row.indexed_at = str(payload.get("indexed_at") or "")
                    row.error = ""
                except Exception as exc:
                    row.status = "failed"
                    row.error = _rag_index_job_error_text(exc)
                finally:
                    with self._lock:
                        current = self._jobs.get(job_id)
                        if current:
                            current.items = list(job.items)
            with self._lock:
                current = self._jobs.get(job_id)
                if current:
                    all_failed = bool(current.items) and all(r.status == "failed" for r in current.items)
                    current.status = "failed" if all_failed else "completed"
                    current.finished_at = _utc_now_iso()
                    current.current_meeting_id = ""
        except Exception as exc:
            with self._lock:
                current = self._jobs.get(job_id)
                if current:
                    current.status = "failed"
                    current.error = _rag_index_job_error_text(exc)
                    current.finished_at = _utc_now_iso()
                    current.current_meeting_id = ""
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None
                self._trim_jobs_locked()

    def start(self, req: RAGIndexJobRequest) -> RAGIndexJobStatusResponse:
        meeting_ids = _safe_meeting_ids(req.meeting_ids)
        if not meeting_ids:
            raise ValueError("meeting_ids_required")
        with self._lock:
            if self._active_job_id:
                active = self._jobs.get(self._active_job_id)
                if active and active.status in {"queued", "running"}:
                    return self._status_snapshot(active, reused_active_job=True)
                self._active_job_id = None
            job_id = f"ragidx-{uuid.uuid4().hex[:10]}"
            job = _RAGIndexJob(
                job_id=job_id,
                meeting_ids=list(meeting_ids),
                transcript_variant=req.transcript_variant,
                force_rebuild=bool(req.force_rebuild),
                max_lines_per_chunk=int(req.max_lines_per_chunk),
                overlap_lines=int(req.overlap_lines),
                max_chars_per_chunk=int(req.max_chars_per_chunk),
                status="queued",
                created_at=_utc_now_iso(),
                items=[_RAGIndexJobRow(meeting_id=mid) for mid in meeting_ids],
            )
            self._jobs[job_id] = job
            self._active_job_id = job_id
            self._latest_job_id = job_id
            self._trim_jobs_locked()
            thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
            thread.start()
            return self._status_snapshot(job)

    def get_status(self, job_id: str | None = None) -> RAGIndexJobStatusResponse | None:
        with self._lock:
            target_id = str(job_id or self._active_job_id or self._latest_job_id or "").strip()
            if not target_id:
                return None
            job = self._jobs.get(target_id)
            if not job:
                return None
            return self._status_snapshot(job)


_RAG_INDEX_JOB_MANAGER = RAGIndexJobManager()


def _rag_index_job_manager() -> RAGIndexJobManager:
    return _RAG_INDEX_JOB_MANAGER


def _load_or_build_report(*, meeting_id: str, source: TranscriptVariant) -> dict[str, Any]:
    filename = _report_json_filename(source)
    if records.exists(meeting_id, filename):
        report = records.read_json(meeting_id, filename)
        if isinstance(report, dict):
            return report
    transcript = _transcript_for_source(meeting_id=meeting_id, source=source)
    report = build_report(enhanced_transcript=transcript, meeting_context={"source": source})
    records.write_json(meeting_id, filename, report)
    text_name = _report_txt_filename(source)
    records.write_text(meeting_id, text_name, report_to_text(report))
    return report


def _compare_item_and_report_from_meeting(
    *,
    meeting,
    source: TranscriptVariant,
) -> tuple[CompareMeetingItem, dict[str, Any]]:
    report = _load_or_build_report(meeting_id=meeting.id, source=source)
    meta = _extract_compare_meta(getattr(meeting, "context", None))
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    data_quality = report.get("data_quality") if isinstance(report.get("data_quality"), dict) else {}
    item = CompareMeetingItem(
        meeting_id=meeting.id,
        created_at=meeting.created_at,
        source=source,
        candidate_name=meta["candidate_name"],
        candidate_id=meta["candidate_id"],
        vacancy=meta["vacancy"],
        level=meta["level"],
        interviewer=meta["interviewer"],
        overall_score=float(report.get("overall_score") or 0.0),
        decision_status=_safe_text(decision.get("status"), limit=48) or "insufficient_data",
        decision_confidence=float(decision.get("confidence") or 0.0),
        transcript_quality=_safe_text(data_quality.get("transcript_quality"), limit=24) or "low",
        comparable=bool(data_quality.get("comparable", False)),
        summary=_safe_text(report.get("summary"), limit=300),
    )
    return item, report


def _compare_item_from_meeting(*, meeting, source: TranscriptVariant) -> CompareMeetingItem:
    item, _ = _compare_item_and_report_from_meeting(meeting=meeting, source=source)
    return item


def _comparison_sort_key(item: CompareMeetingItem) -> tuple[int, float, float, float]:
    created_ts = item.created_at.timestamp() if item.created_at else 0.0
    return (
        1 if item.comparable else 0,
        float(item.overall_score or 0.0),
        float(item.decision_confidence or 0.0),
        created_ts,
    )


def _build_compare_response(
    *,
    source: TranscriptVariant,
    limit: int,
) -> CompareMeetingsResponse:
    with db_session() as session:
        repo = MeetingRepository(session)
        meetings = repo.list_recent(limit=max(1, min(limit, 200)))
    items: list[CompareMeetingItem] = []
    for meeting in meetings:
        try:
            items.append(_compare_item_from_meeting(meeting=meeting, source=source))
        except Exception:
            continue
    items.sort(key=_comparison_sort_key, reverse=True)
    return CompareMeetingsResponse(
        generated_at=datetime.utcnow().isoformat() + "Z",
        source=source,
        items=items,
    )


def _comparison_to_csv(rows: list[CompareMeetingItem]) -> bytes:
    output = io.StringIO()
    fieldnames = [
        "meeting_id",
        "created_at",
        "candidate_name",
        "candidate_id",
        "vacancy",
        "level",
        "interviewer",
        "overall_score",
        "decision_status",
        "decision_confidence",
        "transcript_quality",
        "comparable",
        "summary",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in rows:
        writer.writerow(
            {
                "meeting_id": item.meeting_id,
                "created_at": item.created_at.isoformat() if item.created_at else "",
                "candidate_name": item.candidate_name,
                "candidate_id": item.candidate_id,
                "vacancy": item.vacancy,
                "level": item.level,
                "interviewer": item.interviewer,
                "overall_score": item.overall_score,
                "decision_status": item.decision_status,
                "decision_confidence": item.decision_confidence,
                "transcript_quality": item.transcript_quality,
                "comparable": item.comparable,
                "summary": item.summary,
            }
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _safe_list_texts(value: Any, *, limit: int = 8, item_limit: int = 180) -> list[str]:
    out: list[str] = []
    if not isinstance(value, list):
        return out
    seen: set[str] = set()
    for item in value:
        text = _safe_text(item, limit=item_limit)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _report_topics_and_risks(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    topics: list[str] = []
    topic_seen: set[str] = set()
    risks: list[str] = []
    risk_seen: set[str] = set()

    def _push_topic(value: Any) -> None:
        text = _safe_text(value, limit=180)
        if not text:
            return
        key = text.lower()
        if key in topic_seen:
            return
        topic_seen.add(key)
        topics.append(text)

    def _push_risk(value: Any) -> None:
        text = _safe_text(value, limit=180)
        if not text:
            return
        key = text.lower()
        if key in risk_seen:
            return
        risk_seen.add(key)
        risks.append(text)

    _push_topic(report.get("summary"))
    for item in _safe_list_texts(report.get("bullets"), limit=12, item_limit=180):
        _push_topic(item)

    highlights = report.get("highlights") if isinstance(report.get("highlights"), dict) else {}
    for item in _safe_list_texts(highlights.get("strengths"), limit=8, item_limit=180):
        _push_topic(item)
    for item in _safe_list_texts(highlights.get("concerns"), limit=8, item_limit=180):
        _push_risk(item)

    for item in _safe_list_texts(report.get("risk_flags"), limit=12, item_limit=180):
        _push_risk(item)
    for item in _safe_list_texts(highlights.get("follow_up_questions"), limit=8, item_limit=180):
        _push_risk(item)

    return topics[:8], risks[:8]


def _parse_optional_date(value: str | None, *, is_end: bool = False) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            dt = datetime.strptime(raw, "%Y-%m-%d")
            if is_end:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if getattr(dt, "tzinfo", None) is not None:
            return dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _matches_optional_filter(value: str, expected: str | None) -> bool:
    expected_norm = str(expected or "").strip().lower()
    if not expected_norm:
        return True
    value_norm = str(value or "").strip().lower()
    return expected_norm in value_norm


def _compare_interviewer_sort_key(item: CompareInterviewerItem) -> tuple[int, int, float, float, str]:
    return (
        int(item.comparable_total or 0),
        int(item.interviews_total or 0),
        float(item.avg_score or 0.0),
        float(item.avg_confidence or 0.0),
        str(item.interviewer or "").lower(),
    )


def _build_compare_interviewers_response(
    *,
    source: TranscriptVariant,
    limit: int,
    vacancy: str | None = None,
    level: str | None = None,
    interviewer: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_comparable_ratio: float = 0.0,
    min_interviews: int = 1,
) -> CompareInterviewersResponse:
    start_dt = _parse_optional_date(date_from, is_end=False)
    end_dt = _parse_optional_date(date_to, is_end=True)
    if start_dt and end_dt and start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    with db_session() as session:
        repo = MeetingRepository(session)
        meetings = repo.list_recent(limit=max(1, min(limit, 500)))

    grouped: dict[str, dict[str, Any]] = {}
    for meeting in meetings:
        created_at = getattr(meeting, "created_at", None)
        if start_dt and created_at and created_at < start_dt:
            continue
        if end_dt and created_at and created_at > end_dt:
            continue
        try:
            item, report = _compare_item_and_report_from_meeting(meeting=meeting, source=source)
        except Exception:
            continue

        if not _matches_optional_filter(item.vacancy, vacancy):
            continue
        if not _matches_optional_filter(item.level, level):
            continue
        if not _matches_optional_filter(item.interviewer, interviewer):
            continue

        interviewer_name = _safe_text(item.interviewer, limit=120) or "unknown"
        bucket = grouped.setdefault(
            interviewer_name,
            {
                "items": [],
                "topic_counter": Counter(),
                "risk_counter": Counter(),
                "decision_counter": Counter(),
                "vacancy_counter": Counter(),
                "level_counter": Counter(),
            },
        )
        bucket["items"].append(item)
        bucket["decision_counter"][str(item.decision_status or "insufficient_data")] += 1
        bucket["vacancy_counter"][_safe_text(item.vacancy, limit=120) or "unknown"] += 1
        bucket["level_counter"][_safe_text(item.level, limit=80) or "unknown"] += 1

        topics, risks = _report_topics_and_risks(report)
        for topic in topics:
            bucket["topic_counter"][topic] += 1
        for risk in risks:
            bucket["risk_counter"][risk] += 1

    rows: list[CompareInterviewerItem] = []
    for interviewer_name, bucket in grouped.items():
        items = list(bucket.get("items") or [])
        if not items:
            continue
        interviews_total = len(items)
        comparable_items = [it for it in items if bool(it.comparable)]
        comparable_total = len(comparable_items)
        comparable_ratio = (float(comparable_total) / float(interviews_total)) if interviews_total else 0.0
        if comparable_ratio < float(min_comparable_ratio or 0.0):
            continue
        if interviews_total < int(min_interviews or 1):
            continue

        score_source = comparable_items or items
        score_values = [float(it.overall_score or 0.0) for it in score_source if float(it.overall_score or 0.0) > 0.0]
        conf_values = [
            float(it.decision_confidence or 0.0)
            for it in score_source
            if float(it.decision_confidence or 0.0) > 0.0
        ]
        avg_score = round(sum(score_values) / len(score_values), 2) if score_values else 0.0
        avg_conf = round(sum(conf_values) / len(conf_values), 3) if conf_values else 0.0

        topic_counter = bucket.get("topic_counter") or Counter()
        risk_counter = bucket.get("risk_counter") or Counter()
        decision_counter = bucket.get("decision_counter") or Counter()
        vacancy_counter = bucket.get("vacancy_counter") or Counter()
        level_counter = bucket.get("level_counter") or Counter()

        rows.append(
            CompareInterviewerItem(
                interviewer=interviewer_name,
                interviews_total=interviews_total,
                comparable_total=comparable_total,
                avg_score=avg_score,
                avg_confidence=avg_conf,
                top_topics=[key for key, _ in topic_counter.most_common(5)],
                top_risks=[key for key, _ in risk_counter.most_common(5)],
                decision_breakdown={str(k): int(v) for k, v in decision_counter.items()},
                vacancy_breakdown={str(k): int(v) for k, v in vacancy_counter.items()},
                level_breakdown={str(k): int(v) for k, v in level_counter.items()},
            )
        )

    rows.sort(key=_compare_interviewer_sort_key, reverse=True)
    return CompareInterviewersResponse(
        generated_at=datetime.utcnow().isoformat() + "Z",
        source=source,
        filters={
            "vacancy": _safe_text(vacancy, limit=120),
            "level": _safe_text(level, limit=80),
            "interviewer": _safe_text(interviewer, limit=120),
            "date_from": _safe_text(date_from, limit=40),
            "date_to": _safe_text(date_to, limit=40),
            "min_comparable_ratio": float(min_comparable_ratio or 0.0),
            "min_interviews": int(min_interviews or 1),
        },
        items=rows,
    )


def _compare_interviewers_to_csv(rows: list[CompareInterviewerItem]) -> bytes:
    output = io.StringIO()
    fieldnames = [
        "interviewer",
        "interviews_total",
        "comparable_total",
        "avg_score",
        "avg_confidence",
        "top_topics",
        "top_risks",
        "decision_breakdown",
        "vacancy_breakdown",
        "level_breakdown",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in rows:
        writer.writerow(
            {
                "interviewer": item.interviewer,
                "interviews_total": item.interviews_total,
                "comparable_total": item.comparable_total,
                "avg_score": item.avg_score,
                "avg_confidence": item.avg_confidence,
                "top_topics": " | ".join(item.top_topics),
                "top_risks": " | ".join(item.top_risks),
                "decision_breakdown": json.dumps(item.decision_breakdown, ensure_ascii=False),
                "vacancy_breakdown": json.dumps(item.vacancy_breakdown, ensure_ascii=False),
                "level_breakdown": json.dumps(item.level_breakdown, ensure_ascii=False),
            }
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _compare_interviewers_to_text(payload: CompareInterviewersResponse) -> str:
    lines: list[str] = [
        "Interviewers compare",
        f"Generated at: {payload.generated_at}",
        f"Source: {payload.source}",
        "",
    ]
    if payload.filters:
        lines.append("Filters:")
        for key in (
            "vacancy",
            "level",
            "interviewer",
            "date_from",
            "date_to",
            "min_comparable_ratio",
            "min_interviews",
        ):
            value = payload.filters.get(key)
            if value in (None, "", 0, 0.0):
                continue
            lines.append(f"- {key}: {value}")
        lines.append("")
    if not payload.items:
        lines.append("No data.")
        return "\n".join(lines).strip() + "\n"
    for idx, item in enumerate(payload.items, start=1):
        lines.append(f"{idx}. {item.interviewer}")
        lines.append(
            f"   interviews={item.interviews_total}, comparable={item.comparable_total}, "
            f"avg_score={item.avg_score:.2f}, avg_confidence={item.avg_confidence:.3f}"
        )
        if item.top_topics:
            lines.append(f"   top_topics: {', '.join(item.top_topics)}")
        if item.top_risks:
            lines.append(f"   top_risks: {', '.join(item.top_risks)}")
        if item.decision_breakdown:
            lines.append(
                "   decisions: "
                + ", ".join(f"{k}={v}" for k, v in sorted(item.decision_breakdown.items(), key=lambda kv: kv[0]))
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _senior_brief_text(*, meeting_id: str, source: TranscriptVariant, report: dict[str, Any]) -> str:
    with db_session() as session:
        repo = MeetingRepository(session)
        meeting = repo.get(meeting_id)
    context = meeting.context if meeting else {}
    meta = _extract_compare_meta(context)
    lines = [
        "Senior Brief",
        f"Meeting ID: {meeting_id}",
        f"Source: {source}",
        f"Candidate: {meta['candidate_name'] or '—'}",
        f"Candidate ID: {meta['candidate_id'] or '—'}",
        f"Vacancy: {meta['vacancy'] or '—'}",
        f"Level: {meta['level'] or '—'}",
        f"Interviewer: {meta['interviewer'] or '—'}",
        "",
        report_to_text(report).strip(),
        "",
    ]
    return "\n".join(lines).strip() + "\n"


@router.get("/meetings", response_model=MeetingListResponse)
def list_meetings(
    limit: int = Query(default=50, ge=1, le=200),
    _=Depends(auth_dep),
) -> MeetingListResponse:
    with db_session() as session:
        repo = MeetingRepository(session)
        meetings = repo.list_recent(limit=limit)
        items = []
        for m in meetings:
            meta = records.ensure_meeting_metadata(m.id)
            display_name = str(meta.get("display_name") or "").strip() or m.id
            record_index = int(meta.get("record_index") or 0)
            items.append(
                MeetingListItem(
                    meeting_id=m.id,
                    display_name=display_name,
                    record_index=record_index,
                    status=str(m.status),
                    created_at=m.created_at,
                    finished_at=m.finished_at,
                    audio_mp3=records.exists(m.id, CANONICAL_AUDIO_FILENAME),
                    artifacts=records.list_artifacts(m.id),
                    rag_index_status=_rag_index_status_for_meeting(m.id),
                )
            )
    log.info(
        "meetings_list",
        extra={"payload": {"limit": limit, "items_count": len(items)}},
    )
    return MeetingListResponse(items=items)


@router.post("/meetings/{meeting_id}/finish")
def finish_meeting(
    meeting_id: str,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    log.info("meeting_finish_requested", extra={"payload": {"meeting_id": meeting_id}})
    queue_mode = str(get_settings().queue_mode or "").strip().lower()
    with db_session() as session:
        repo = MeetingRepository(session)
        m = repo.get(meeting_id)
        if not m:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if not m.finished_at:
            m.finished_at = datetime.utcnow()
        if m.status != PipelineStatus.done:
            # Stop завершает запись и закрывает meeting; STT/LLM запускаются позже,
            # только по запросу текстовых/отчётных артефактов.
            m.status = PipelineStatus.done
        repo.save(m)
    records.ensure_meeting_metadata(meeting_id)
    audio_path = materialize_meeting_audio_mp3(meeting_id=meeting_id)
    log.info(
        "meeting_finish_completed",
        extra={
            "payload": {
                "meeting_id": meeting_id,
                "queue_mode": queue_mode,
                "audio_mp3_ready": bool(audio_path),
            }
        },
    )
    return {"ok": True, "meeting_id": meeting_id, "audio_mp3_ready": bool(audio_path)}


@router.post("/meetings/{meeting_id}/transcripts/generate", response_model=TranscriptGenerateResponse)
def generate_transcripts(
    meeting_id: str,
    req: TranscriptGenerateRequest,
    _=Depends(auth_dep),
) -> TranscriptGenerateResponse:
    variants = _dedupe_transcript_variants(req.variants)
    include_normalized = any(v in {"normalized", "clean"} for v in variants)
    include_clean = any(v == "clean" for v in variants)
    payload = _ensure_transcript_variants(
        meeting_id,
        include_normalized=include_normalized,
        include_clean=include_clean,
        force_rebuild=bool(req.force_rebuild),
    )
    items = [
        TranscriptGenerateItem(
            variant=v,
            filename=_transcript_filename(v),
            chars=len(str(payload.get(v) or "")),
            generated=bool(str(payload.get(v) or "").strip()),
        )
        for v in variants
    ]
    return TranscriptGenerateResponse(meeting_id=meeting_id, items=items)


@router.post("/meetings/{meeting_id}/transcripts/rebuild", response_model=TranscriptGenerateResponse)
def rebuild_transcripts(
    meeting_id: str,
    req: TranscriptGenerateRequest,
    _=Depends(auth_dep),
) -> TranscriptGenerateResponse:
    req.force_rebuild = True
    return generate_transcripts(meeting_id=meeting_id, req=req)


@router.get(
    "/meetings/{meeting_id}/transcripts/{variant}",
    response_model=TranscriptTextResponse,
)
def get_transcript(
    meeting_id: str,
    variant: TranscriptVariant,
    fmt: Literal["txt", "json"] = Query(default="txt"),
    force_rebuild: bool = Query(default=False),
    _=Depends(auth_dep),
) -> Any:
    if force_rebuild:
        text = _ensure_transcript_text(
            meeting_id,
            variant=variant,
            force_rebuild=True,
        )
    else:
        text = _read_transcript_text_artifact(meeting_id, variant=variant)
    filename = _transcript_filename(variant)
    if fmt == "json":
        return TranscriptTextResponse(
            meeting_id=meeting_id,
            variant=variant,
            filename=filename,
            chars=len(text),
            text=text,
        )
    try:
        path = records.artifact_path(meeting_id, filename)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")
    if not path.exists():
        raise HTTPException(status_code=409, detail=f"transcript_{variant}_not_ready")
    return FileResponse(path, media_type="text/plain", filename=path.name)


@router.post("/meetings/{meeting_id}/rag/index", response_model=RAGIndexResponse)
def build_rag_index(
    meeting_id: str,
    req: RAGIndexRequest,
    _=Depends(auth_dep),
) -> RAGIndexResponse:
    payload, cached = _ensure_rag_index(
        meeting_id,
        source=req.transcript_variant,
        force_rebuild=bool(req.force_rebuild),
        max_lines_per_chunk=int(req.max_lines_per_chunk),
        overlap_lines=int(req.overlap_lines),
        max_chars_per_chunk=int(req.max_chars_per_chunk),
    )
    return _rag_index_response_from_payload(
        payload,
        meeting_id=meeting_id,
        source=req.transcript_variant,
        cached=cached,
    )


@router.get("/meetings/{meeting_id}/rag/index", response_model=RAGIndexResponse)
def get_rag_index_meta(
    meeting_id: str,
    source: TranscriptVariant = Query(default="clean"),
    auto_build: bool = Query(default=True),
    force_rebuild: bool = Query(default=False),
    _=Depends(auth_dep),
) -> RAGIndexResponse:
    if auto_build:
        payload, cached = _ensure_rag_index(
            meeting_id,
            source=source,
            force_rebuild=bool(force_rebuild),
        )
    else:
        payload = _rag_read_index(meeting_id, source)
        cached = True
    return _rag_index_response_from_payload(payload, meeting_id=meeting_id, source=source, cached=cached)


@router.post("/rag/index-jobs", response_model=RAGIndexJobStatusResponse)
def start_rag_index_job(
    req: RAGIndexJobRequest,
    _=Depends(auth_dep),
) -> RAGIndexJobStatusResponse:
    try:
        return _rag_index_job_manager().start(req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/rag/index-jobs", response_model=RAGIndexJobStatusResponse)
def get_rag_index_job_status_latest(
    job_id: str | None = Query(default=None),
    _=Depends(auth_dep),
) -> RAGIndexJobStatusResponse:
    resp = _rag_index_job_manager().get_status(job_id=job_id)
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rag_index_job_not_found")
    return resp


@router.get("/rag/index-jobs/{job_id}", response_model=RAGIndexJobStatusResponse)
def get_rag_index_job_status(
    job_id: str,
    _=Depends(auth_dep),
) -> RAGIndexJobStatusResponse:
    resp = _rag_index_job_manager().get_status(job_id=job_id)
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rag_index_job_not_found")
    return resp


@router.post("/rag/query", response_model=RAGQueryResponse)
def rag_query(
    req: RAGQueryRequest,
    _=Depends(auth_dep),
) -> RAGQueryResponse:
    return _rag_query(req)


@router.get("/rag/query/export")
def rag_query_export(
    request_id: str = Query(..., min_length=4, max_length=80),
    fmt: Literal["txt", "csv", "json"] = Query(default="json"),
    _=Depends(auth_dep),
) -> Response:
    try:
        path, filename = _rag_query_export_file(request_id=request_id, fmt=fmt)
    except HTTPException as exc:
        record_rag_export_error(reason=str(exc.detail or "not_found"))
        raise
    except Exception:
        record_rag_export_error(reason="unexpected_error")
        raise
    media_type = (
        "application/json"
        if fmt == "json"
        else "text/csv; charset=utf-8"
        if fmt == "csv"
        else "text/plain; charset=utf-8"
    )
    return FileResponse(path, media_type=media_type, filename=filename)


@router.post("/meetings/{meeting_id}/rename")
def rename_meeting(
    meeting_id: str,
    req: RenameMeetingRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    with db_session() as session:
        repo = MeetingRepository(session)
        meeting = repo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    try:
        meta = records.update_meeting_display_name(meeting_id, req.display_name)
    except ValueError as exc:
        log.warning(
            "meeting_rename_invalid",
            extra={"payload": {"meeting_id": meeting_id, "error": str(exc)[:200]}},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    display_name = str(meta.get("display_name") or meeting_id)
    log.info(
        "meeting_renamed",
        extra={"payload": {"meeting_id": meeting_id, "display_name": display_name}},
    )
    return {
        "ok": True,
        "meeting_id": meeting_id,
        "display_name": display_name,
        "record_index": int(meta.get("record_index") or 0),
    }


@router.post("/meetings/{meeting_id}/report")
def generate_report(
    meeting_id: str,
    req: ReportRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    transcript = _transcript_for_source(meeting_id=meeting_id, source=req.source)
    report = build_report(enhanced_transcript=transcript, meeting_context={"source": req.source})
    filename = _report_json_filename(req.source)
    records.write_json(meeting_id, filename, report)
    text_name = _report_txt_filename(req.source)
    records.write_text(meeting_id, text_name, report_to_text(report))
    return {"ok": True, "report": report, "source": req.source}


@router.post("/meetings/{meeting_id}/analysis")
def generate_analysis(
    meeting_id: str,
    req: ReportRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    # Новый термин: analysis. Оставляем legacy /report как совместимый alias.
    return generate_report(meeting_id=meeting_id, req=req, _=_)


@router.post("/meetings/{meeting_id}/senior-brief")
def generate_senior_brief(
    meeting_id: str,
    req: SeniorBriefRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    report = _load_or_build_report(meeting_id=meeting_id, source=req.source)
    brief_text = _senior_brief_text(meeting_id=meeting_id, source=req.source, report=report)
    filename = _senior_brief_filename(req.source)
    records.write_text(meeting_id, filename, brief_text)
    return {"ok": True, "source": req.source, "filename": filename}


@router.get("/meetings/compare", response_model=CompareMeetingsResponse)
def compare_meetings(
    source: TranscriptVariant = Query(default="clean"),
    limit: int = Query(default=30, ge=1, le=200),
    _=Depends(auth_dep),
) -> CompareMeetingsResponse:
    return _build_compare_response(source=source, limit=limit)


@router.get("/meetings/compare/export")
def compare_meetings_export(
    source: TranscriptVariant = Query(default="clean"),
    limit: int = Query(default=30, ge=1, le=200),
    fmt: Literal["csv", "json"] = Query(default="csv"),
    _=Depends(auth_dep),
) -> Response:
    payload = _build_compare_response(source=source, limit=limit)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if fmt == "json":
        body = payload.model_dump_json(indent=2).encode("utf-8")
        return Response(
            content=body,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="compare_{source}_{ts}.json"',
            },
        )
    body = _comparison_to_csv(payload.items)
    return Response(
        content=body,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="compare_{source}_{ts}.csv"',
        },
    )


@router.get("/meetings/compare/interviewers", response_model=CompareInterviewersResponse)
def compare_interviewers(
    source: TranscriptVariant = Query(default="clean"),
    limit: int = Query(default=100, ge=1, le=500),
    vacancy: str | None = Query(default=None),
    level: str | None = Query(default=None),
    interviewer: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    min_comparable_ratio: float = Query(default=0.0, ge=0.0, le=1.0),
    min_interviews: int = Query(default=1, ge=1, le=100),
    _=Depends(auth_dep),
) -> CompareInterviewersResponse:
    return _build_compare_interviewers_response(
        source=source,
        limit=limit,
        vacancy=vacancy,
        level=level,
        interviewer=interviewer,
        date_from=date_from,
        date_to=date_to,
        min_comparable_ratio=min_comparable_ratio,
        min_interviews=min_interviews,
    )


@router.get("/meetings/compare/interviewers/export")
def compare_interviewers_export(
    source: TranscriptVariant = Query(default="clean"),
    limit: int = Query(default=100, ge=1, le=500),
    vacancy: str | None = Query(default=None),
    level: str | None = Query(default=None),
    interviewer: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    min_comparable_ratio: float = Query(default=0.0, ge=0.0, le=1.0),
    min_interviews: int = Query(default=1, ge=1, le=100),
    fmt: Literal["csv", "json", "txt"] = Query(default="csv"),
    _=Depends(auth_dep),
) -> Response:
    payload = _build_compare_interviewers_response(
        source=source,
        limit=limit,
        vacancy=vacancy,
        level=level,
        interviewer=interviewer,
        date_from=date_from,
        date_to=date_to,
        min_comparable_ratio=min_comparable_ratio,
        min_interviews=min_interviews,
    )
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if fmt == "json":
        body = payload.model_dump_json(indent=2).encode("utf-8")
        return Response(
            content=body,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="compare_interviewers_{source}_{ts}.json"',
            },
        )
    if fmt == "txt":
        body = _compare_interviewers_to_text(payload).encode("utf-8")
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="compare_interviewers_{source}_{ts}.txt"',
            },
        )
    body = _compare_interviewers_to_csv(payload.items)
    return Response(
        content=body,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="compare_interviewers_{source}_{ts}.csv"',
        },
    )


@router.post("/meetings/{meeting_id}/structured")
def generate_structured(
    meeting_id: str,
    req: StructuredRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    transcript = _transcript_for_source(meeting_id=meeting_id, source=req.source)
    report_file = _report_json_filename(req.source)
    report = records.read_json(meeting_id, report_file) if records.exists(meeting_id, report_file) else None

    structured = build_structured_rows(
        meeting_id=meeting_id,
        source=req.source,
        transcript=transcript,
        report=report,
    )
    json_name = _structured_json_filename(req.source)
    csv_name = _structured_csv_filename(req.source)
    records.write_json(meeting_id, json_name, structured)
    records.write_bytes(meeting_id, csv_name, structured_to_csv(structured))
    return {
        "ok": True,
        "source": req.source,
        "status": str(structured.get("status") or "ok"),
        "message": str(structured.get("message") or ""),
        "rows": len(structured.get("rows") or []),
    }


@router.post(
    "/meetings/{meeting_id}/artifacts/generate",
    response_model=LLMArtifactResponse,
)
def generate_llm_artifact(
    meeting_id: str,
    req: LLMArtifactGenerateRequest,
    _=Depends(auth_dep),
) -> LLMArtifactResponse:
    try:
        meta, cached = _generate_llm_artifact(meeting_id=meeting_id, req=req)
        return _artifact_response_from_meta(meta, cached=cached)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception(
            "llm_artifact_generate_unhandled",
            extra={
                "payload": {
                    "meeting_id": meeting_id,
                    "mode": str(req.mode or ""),
                    "source": str(req.transcript_variant or ""),
                    "error": _safe_text(exc, limit=280),
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="llm_artifact_generate_failed",
        ) from exc


@router.get(
    "/meetings/{meeting_id}/artifacts/{artifact_id}",
    response_model=LLMArtifactResponse,
)
def get_llm_artifact(
    meeting_id: str,
    artifact_id: str,
    _=Depends(auth_dep),
) -> LLMArtifactResponse:
    meta = _read_llm_artifact_meta(meeting_id=meeting_id, artifact_id=artifact_id)
    return _artifact_response_from_meta(meta, cached=True)


@router.get("/meetings/{meeting_id}/artifacts/{artifact_id}/download")
def download_llm_artifact(
    meeting_id: str,
    artifact_id: str,
    fmt: LLMArtifactDownloadFormat = Query(default="json"),
    _=Depends(auth_dep),
) -> FileResponse:
    path = _artifact_result_download_path(meeting_id=meeting_id, artifact_id=artifact_id, fmt=fmt)
    media_type = "text/plain"
    if path.name.endswith(".json"):
        media_type = "application/json"
    elif path.name.endswith(".csv"):
        media_type = "text/csv"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/meetings/{meeting_id}/artifact")
def download_artifact(
    meeting_id: str,
    kind: Literal["raw", "normalized", "clean", "report", "analysis", "structured", "senior_brief", "audio"] = Query(default="raw"),
    source: TranscriptVariant | None = Query(default=None),
    fmt: Literal["txt", "json", "csv", "mp3"] = Query(default="txt"),
    _=Depends(auth_dep),
) -> FileResponse:
    if kind in {"raw", "normalized", "clean"}:
        variant: TranscriptVariant = "raw"
        if kind == "normalized":
            variant = "normalized"
        elif kind == "clean":
            variant = "clean"
        filename = _transcript_filename(variant)
    elif kind in {"report", "analysis"}:
        if not source:
            raise HTTPException(status_code=400, detail="source_required")
        if fmt not in {"txt", "json"}:
            raise HTTPException(status_code=400, detail="format_required")
        if fmt == "txt":
            filename = _report_txt_filename(source)
            if not records.exists(meeting_id, filename):
                json_name = _report_json_filename(source)
                if records.exists(meeting_id, json_name):
                    report = records.read_json(meeting_id, json_name)
                    records.write_text(meeting_id, filename, report_to_text(report))
        else:
            filename = _report_json_filename(source)
    elif kind == "senior_brief":
        if not source:
            raise HTTPException(status_code=400, detail="source_required")
        if fmt != "txt":
            raise HTTPException(status_code=400, detail="format_required")
        filename = _senior_brief_filename(source)
    elif kind == "audio":
        if fmt != "mp3":
            raise HTTPException(status_code=400, detail="format_required")
        path = materialize_meeting_audio_mp3(meeting_id=meeting_id)
        if not path:
            log.warning(
                "audio_artifact_request_not_available",
                extra={"payload": {"meeting_id": meeting_id, "kind": kind, "fmt": fmt}},
            )
            raise HTTPException(status_code=404, detail="artifact_not_found")
        filename = path.name
    else:
        if not source:
            raise HTTPException(status_code=400, detail="source_required")
        if fmt not in {"json", "csv"}:
            raise HTTPException(status_code=400, detail="format_required")
        filename = _structured_json_filename(source) if fmt == "json" else _structured_csv_filename(source)

    try:
        path = records.artifact_path(meeting_id, filename)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")
    if not path.exists():
        if kind in {"raw", "normalized", "clean"}:
            raise HTTPException(status_code=409, detail=f"transcript_{kind}_not_ready")
        raise HTTPException(status_code=404, detail="artifact_not_found")

    media_type = "text/plain"
    if filename.endswith(".json"):
        media_type = "application/json"
    if filename.endswith(".csv"):
        media_type = "text/csv"
    if filename.endswith(".mp3"):
        media_type = "audio/mpeg"

    return FileResponse(path, media_type=media_type, filename=path.name)
