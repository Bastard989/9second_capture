"""
HTTP ingestion endpoints for post-meeting uploads.

Задача:
- принимать аудио-чанки через HTTP
- сохранять в blob storage
- ставить задачу в STT очередь
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from apps.api_gateway.deps import auth_dep, service_auth_write_dep
from apps.api_gateway.tenancy import enforce_meeting_access, tenant_enforcement_enabled
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.common.security import AuthContext
from interview_analytics_agent.common.tracing import start_trace
from interview_analytics_agent.services.chunk_ingest_service import (
    ingest_audio_chunk_b64,
    ingest_audio_chunk_bytes,
)
from interview_analytics_agent.services.audio_artifact_service import materialize_meeting_audio_mp3
from interview_analytics_agent.storage import records
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import MeetingRepository

log = get_project_logger()
router = APIRouter()


class ChunkIngestRequest(BaseModel):
    seq: int = Field(ge=0)
    content_b64: str
    codec: str = "pcm"
    sample_rate: int = 16000
    channels: int = 1
    source_track: str | None = None
    quality_profile: str = "live"
    idempotency_key: str | None = None


class ChunkIngestResponse(BaseModel):
    accepted: bool
    meeting_id: str
    seq: int
    idempotency_key: str
    blob_key: str
    inline_updates: list[dict[str, Any]] = Field(default_factory=list)


class BackupAudioUploadResponse(BaseModel):
    ok: bool
    meeting_id: str
    filename: str
    size_bytes: int


def _ingest_chunk_impl(meeting_id: str, req: ChunkIngestRequest) -> ChunkIngestResponse:
    with start_trace(meeting_id=meeting_id, source="http.ingest"):
        try:
            result = ingest_audio_chunk_b64(
                meeting_id=meeting_id,
                seq=req.seq,
                content_b64=req.content_b64,
                source_track=req.source_track,
                quality_profile=req.quality_profile,
                idempotency_key=req.idempotency_key,
                idempotency_scope="audio_chunk_http",
                idempotency_prefix="http-chunk",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "bad_audio", "message": "content_b64 не декодируется"},
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "ingest_error", "message": "Ошибка ingest аудио-чанка"},
            ) from e

        log.info(
            "http_chunk_ingested",
            extra={
                "payload": {"meeting_id": meeting_id, "seq": req.seq, "codec": req.codec},
            },
        )
        return ChunkIngestResponse(
            accepted=result.accepted,
            meeting_id=result.meeting_id,
            seq=result.seq,
            idempotency_key=result.idempotency_key,
            blob_key=result.blob_key,
            inline_updates=list(getattr(result, "inline_updates", None) or []),
        )


def _ensure_meeting_access(ctx: AuthContext, meeting_id: str) -> None:
    if not tenant_enforcement_enabled():
        return
    with db_session() as s:
        repo = MeetingRepository(s)
        m = repo.get(meeting_id)
        if not m:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": "Встреча не найдена"},
            )
        enforce_meeting_access(ctx, m.context)


@router.post("/meetings/{meeting_id}/chunks", response_model=ChunkIngestResponse)
def ingest_chunk(
    meeting_id: str,
    req: ChunkIngestRequest,
    ctx: AuthContext = Depends(auth_dep),
) -> ChunkIngestResponse:
    _ensure_meeting_access(ctx, meeting_id)
    return _ingest_chunk_impl(meeting_id=meeting_id, req=req)


@router.post("/meetings/{meeting_id}/upload", response_model=ChunkIngestResponse)
async def upload_audio(
    meeting_id: str,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(auth_dep),
) -> ChunkIngestResponse:
    _ensure_meeting_access(ctx, meeting_id)
    payload = await file.read()
    ext = "bin"
    if file.filename and "." in file.filename:
        value = file.filename.rsplit(".", 1)[-1].strip().lower()
        if value and value.isalnum():
            ext = value
    source_name = f"source_upload.{ext}"
    records.write_bytes(meeting_id, source_name, payload)
    materialize_meeting_audio_mp3(meeting_id=meeting_id, preferred_filename=source_name)
    result = ingest_audio_chunk_bytes(
        meeting_id=meeting_id,
        seq=0,
        audio_bytes=payload,
        idempotency_key=None,
        idempotency_scope="audio_chunk_upload",
        idempotency_prefix="upload",
    )
    return ChunkIngestResponse(
        accepted=result.accepted,
        meeting_id=result.meeting_id,
        seq=result.seq,
        idempotency_key=result.idempotency_key,
        blob_key=result.blob_key,
        inline_updates=list(getattr(result, "inline_updates", None) or []),
    )


@router.post("/meetings/{meeting_id}/backup-audio", response_model=BackupAudioUploadResponse)
async def upload_backup_audio(
    meeting_id: str,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(auth_dep),
) -> BackupAudioUploadResponse:
    _ensure_meeting_access(ctx, meeting_id)
    payload = await file.read()
    filename = "backup_audio.webm"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].strip().lower()
        if ext and ext.isalnum():
            filename = f"backup_audio.{ext}"
    records.write_bytes(meeting_id, filename, payload)
    materialize_meeting_audio_mp3(meeting_id=meeting_id, preferred_filename=filename)
    return BackupAudioUploadResponse(
        ok=True,
        meeting_id=meeting_id,
        filename=filename,
        size_bytes=len(payload),
    )


@router.post(
    "/internal/meetings/{meeting_id}/chunks",
    response_model=ChunkIngestResponse,
    dependencies=[Depends(service_auth_write_dep)],
)
def ingest_chunk_internal(meeting_id: str, req: ChunkIngestRequest) -> ChunkIngestResponse:
    return _ingest_chunk_impl(meeting_id=meeting_id, req=req)
