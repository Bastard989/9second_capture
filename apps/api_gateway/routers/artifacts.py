from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.domain.enums import PipelineStatus
from interview_analytics_agent.processing.aggregation import (
    build_enhanced_transcript,
    build_raw_transcript,
)
from interview_analytics_agent.processing.analytics import build_report, report_to_text
from interview_analytics_agent.processing.enhancer import cleanup_transcript_with_llm
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


class MeetingListItem(BaseModel):
    meeting_id: str
    display_name: str = ""
    record_index: int = 0
    status: str
    created_at: datetime | None
    finished_at: datetime | None
    audio_mp3: bool = False
    artifacts: dict[str, bool] = Field(default_factory=dict)


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]


class ReportRequest(BaseModel):
    source: Literal["raw", "clean"] = "clean"


class StructuredRequest(BaseModel):
    source: Literal["raw", "clean"] = "clean"


class SeniorBriefRequest(BaseModel):
    source: Literal["raw", "clean"] = "clean"


class RenameMeetingRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class CompareMeetingItem(BaseModel):
    meeting_id: str
    created_at: datetime | None = None
    source: Literal["raw", "clean"] = "clean"
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
    source: Literal["raw", "clean"]
    items: list[CompareMeetingItem] = Field(default_factory=list)


def _ensure_transcripts(meeting_id: str) -> tuple[str, str]:
    try:
        raw_path = records.artifact_path(meeting_id, "raw.txt")
        clean_path = records.artifact_path(meeting_id, "clean.txt")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")

    with db_session() as session:
        mrepo = MeetingRepository(session)
        meeting = mrepo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        srepo = TranscriptSegmentRepository(session)
        segs = srepo.list_by_meeting(meeting_id)
        raw = build_raw_transcript(segs)
        clean = build_enhanced_transcript(segs)
        clean = _maybe_cleanup_clean_transcript_with_cache(
            meeting_id=meeting_id,
            clean_text=clean,
            segs=segs,
        )
        meeting.raw_transcript = raw
        meeting.enhanced_transcript = clean
        if meeting.finished_at and meeting.status != PipelineStatus.done:
            meeting.status = PipelineStatus.done
        mrepo.save(meeting)

    records.write_text(meeting_id, "raw.txt", raw)
    records.write_text(meeting_id, "clean.txt", clean)
    return raw, clean


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


def _load_or_build_report(*, meeting_id: str, source: Literal["raw", "clean"]) -> dict[str, Any]:
    filename = "report_raw.json" if source == "raw" else "report_clean.json"
    if records.exists(meeting_id, filename):
        report = records.read_json(meeting_id, filename)
        if isinstance(report, dict):
            return report
    raw, clean = _ensure_transcripts(meeting_id)
    transcript = raw if source == "raw" else clean
    report = build_report(enhanced_transcript=transcript, meeting_context={"source": source})
    records.write_json(meeting_id, filename, report)
    text_name = "report_raw.txt" if source == "raw" else "report_clean.txt"
    records.write_text(meeting_id, text_name, report_to_text(report))
    return report


def _compare_item_from_meeting(*, meeting, source: Literal["raw", "clean"]) -> CompareMeetingItem:
    report = _load_or_build_report(meeting_id=meeting.id, source=source)
    meta = _extract_compare_meta(getattr(meeting, "context", None))
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    data_quality = report.get("data_quality") if isinstance(report.get("data_quality"), dict) else {}
    return CompareMeetingItem(
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
    source: Literal["raw", "clean"],
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


def _senior_brief_text(*, meeting_id: str, source: Literal["raw", "clean"], report: dict[str, Any]) -> str:
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
    with db_session() as session:
        repo = MeetingRepository(session)
        m = repo.get(meeting_id)
        if not m:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        if not m.finished_at:
            m.finished_at = datetime.utcnow()
        if m.status != PipelineStatus.done:
            m.status = PipelineStatus.processing
            if (get_settings().queue_mode or "").strip().lower() == "inline":
                m.status = PipelineStatus.done
        repo.save(m)
    if (get_settings().queue_mode or "").strip().lower() == "inline":
        settings = get_settings()
        used_backup_final_pass = False
        if bool(getattr(settings, "backup_audio_final_pass_enabled", True)):
            used_backup_final_pass = bool(final_pass_from_backup_audio(meeting_id=meeting_id))
        if not used_backup_final_pass:
            retranscribe_meeting_high_quality(meeting_id=meeting_id)
            if bool(settings.backup_audio_recovery_enabled):
                recover_transcript_from_backup_audio(meeting_id=meeting_id)
    _ensure_transcripts(meeting_id)
    records.ensure_meeting_metadata(meeting_id)
    materialize_meeting_audio_mp3(meeting_id=meeting_id)
    log.info(
        "meeting_finish_completed",
        extra={"payload": {"meeting_id": meeting_id, "queue_mode": str(get_settings().queue_mode or "")}},
    )
    return {"ok": True, "meeting_id": meeting_id}


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
    raw, clean = _ensure_transcripts(meeting_id)
    transcript = raw if req.source == "raw" else clean
    report = build_report(enhanced_transcript=transcript, meeting_context={"source": req.source})
    filename = "report_raw.json" if req.source == "raw" else "report_clean.json"
    records.write_json(meeting_id, filename, report)
    text_name = "report_raw.txt" if req.source == "raw" else "report_clean.txt"
    records.write_text(meeting_id, text_name, report_to_text(report))
    return {"ok": True, "report": report, "source": req.source}


@router.post("/meetings/{meeting_id}/senior-brief")
def generate_senior_brief(
    meeting_id: str,
    req: SeniorBriefRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    report = _load_or_build_report(meeting_id=meeting_id, source=req.source)
    brief_text = _senior_brief_text(meeting_id=meeting_id, source=req.source, report=report)
    filename = "senior_brief_raw.txt" if req.source == "raw" else "senior_brief_clean.txt"
    records.write_text(meeting_id, filename, brief_text)
    return {"ok": True, "source": req.source, "filename": filename}


@router.get("/meetings/compare", response_model=CompareMeetingsResponse)
def compare_meetings(
    source: Literal["raw", "clean"] = Query(default="clean"),
    limit: int = Query(default=30, ge=1, le=200),
    _=Depends(auth_dep),
) -> CompareMeetingsResponse:
    return _build_compare_response(source=source, limit=limit)


@router.get("/meetings/compare/export")
def compare_meetings_export(
    source: Literal["raw", "clean"] = Query(default="clean"),
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


@router.post("/meetings/{meeting_id}/structured")
def generate_structured(
    meeting_id: str,
    req: StructuredRequest,
    _=Depends(auth_dep),
) -> dict[str, Any]:
    raw, clean = _ensure_transcripts(meeting_id)
    transcript = raw if req.source == "raw" else clean
    report_file = "report_raw.json" if req.source == "raw" else "report_clean.json"
    report = records.read_json(meeting_id, report_file) if records.exists(meeting_id, report_file) else None

    structured = build_structured_rows(
        meeting_id=meeting_id,
        source=req.source,
        transcript=transcript,
        report=report,
    )
    json_name = "structured_raw.json" if req.source == "raw" else "structured_clean.json"
    csv_name = "structured_raw.csv" if req.source == "raw" else "structured_clean.csv"
    records.write_json(meeting_id, json_name, structured)
    records.write_bytes(meeting_id, csv_name, structured_to_csv(structured))
    return {
        "ok": True,
        "source": req.source,
        "status": str(structured.get("status") or "ok"),
        "message": str(structured.get("message") or ""),
        "rows": len(structured.get("rows") or []),
    }


@router.get("/meetings/{meeting_id}/artifact")
def download_artifact(
    meeting_id: str,
    kind: Literal["raw", "clean", "report", "structured", "senior_brief", "audio"] = Query(default="raw"),
    source: Literal["raw", "clean"] | None = Query(default=None),
    fmt: Literal["txt", "json", "csv", "mp3"] = Query(default="txt"),
    _=Depends(auth_dep),
) -> FileResponse:
    if kind in {"raw", "clean"}:
        filename = "raw.txt" if kind == "raw" else "clean.txt"
        _ensure_transcripts(meeting_id)
    elif kind == "report":
        if not source:
            raise HTTPException(status_code=400, detail="source_required")
        if fmt not in {"txt", "json"}:
            raise HTTPException(status_code=400, detail="format_required")
        if fmt == "txt":
            filename = "report_raw.txt" if source == "raw" else "report_clean.txt"
            if not records.exists(meeting_id, filename):
                json_name = "report_raw.json" if source == "raw" else "report_clean.json"
                if records.exists(meeting_id, json_name):
                    report = records.read_json(meeting_id, json_name)
                    records.write_text(meeting_id, filename, report_to_text(report))
        else:
            filename = "report_raw.json" if source == "raw" else "report_clean.json"
    elif kind == "senior_brief":
        if not source:
            raise HTTPException(status_code=400, detail="source_required")
        if fmt != "txt":
            raise HTTPException(status_code=400, detail="format_required")
        filename = "senior_brief_raw.txt" if source == "raw" else "senior_brief_clean.txt"
        if not records.exists(meeting_id, filename):
            report = _load_or_build_report(
                meeting_id=meeting_id,
                source=source,
            )
            records.write_text(
                meeting_id,
                filename,
                _senior_brief_text(meeting_id=meeting_id, source=source, report=report),
            )
    elif kind == "audio":
        if fmt != "mp3":
            raise HTTPException(status_code=400, detail="format_required")
        path = materialize_meeting_audio_mp3(meeting_id=meeting_id)
        if not path:
            raise HTTPException(status_code=404, detail="artifact_not_found")
        filename = path.name
    else:
        if not source:
            raise HTTPException(status_code=400, detail="source_required")
        if fmt not in {"json", "csv"}:
            raise HTTPException(status_code=400, detail="format_required")
        filename = (
            f"structured_{source}.json" if fmt == "json" else f"structured_{source}.csv"
        )

    try:
        path = records.artifact_path(meeting_id, filename)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")
    if not path.exists():
        raise HTTPException(status_code=404, detail="artifact_not_found")

    media_type = "text/plain"
    if filename.endswith(".json"):
        media_type = "application/json"
    if filename.endswith(".csv"):
        media_type = "text/csv"
    if filename.endswith(".mp3"):
        media_type = "audio/mpeg"

    return FileResponse(path, media_type=media_type, filename=path.name)
