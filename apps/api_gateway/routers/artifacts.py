from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.domain.enums import PipelineStatus
from interview_analytics_agent.processing.aggregation import (
    build_enhanced_transcript,
    build_raw_transcript,
)
from interview_analytics_agent.processing.analytics import build_report, report_to_text
from interview_analytics_agent.processing.structured import build_structured_rows, structured_to_csv
from interview_analytics_agent.storage import records
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import MeetingRepository, TranscriptSegmentRepository

router = APIRouter()


class MeetingListItem(BaseModel):
    meeting_id: str
    status: str
    created_at: datetime | None
    finished_at: datetime | None
    artifacts: dict[str, bool] = Field(default_factory=dict)


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]


class ReportRequest(BaseModel):
    source: Literal["raw", "clean"] = "clean"


class StructuredRequest(BaseModel):
    source: Literal["raw", "clean"] = "clean"


def _ensure_transcripts(meeting_id: str) -> tuple[str, str]:
    try:
        raw_path = records.artifact_path(meeting_id, "raw.txt")
        clean_path = records.artifact_path(meeting_id, "clean.txt")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_meeting_id")

    with db_session() as session:
        mrepo = MeetingRepository(session)
        if not mrepo.get(meeting_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
        srepo = TranscriptSegmentRepository(session)
        segs = srepo.list_by_meeting(meeting_id)
        raw = build_raw_transcript(segs)
        clean = build_enhanced_transcript(segs)

    records.write_text(meeting_id, "raw.txt", raw)
    records.write_text(meeting_id, "clean.txt", clean)
    return raw, clean


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
            items.append(
                MeetingListItem(
                    meeting_id=m.id,
                    status=str(m.status),
                    created_at=m.created_at,
                    finished_at=m.finished_at,
                    artifacts=records.list_artifacts(m.id),
                )
            )
    return MeetingListResponse(items=items)


@router.post("/meetings/{meeting_id}/finish")
def finish_meeting(
    meeting_id: str,
    _=Depends(auth_dep),
) -> dict[str, Any]:
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
    _ensure_transcripts(meeting_id)
    return {"ok": True, "meeting_id": meeting_id}


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
    return {"ok": True, "source": req.source}


@router.get("/meetings/{meeting_id}/artifact")
def download_artifact(
    meeting_id: str,
    kind: Literal["raw", "clean", "report", "structured"] = Query(default="raw"),
    source: Literal["raw", "clean"] | None = Query(default=None),
    fmt: Literal["txt", "json", "csv"] = Query(default="txt"),
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

    return FileResponse(path, media_type=media_type, filename=path.name)
