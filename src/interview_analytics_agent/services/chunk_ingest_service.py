"""
Единый ingest-сервис для аудио-чанков.

Используется в:
- HTTP ingest endpoints
- WebSocket ingest
- внутренний live-ingest коннектора
"""

from __future__ import annotations

from dataclasses import dataclass

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.ids import new_idempotency_key
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.common.utils import b64_decode
from interview_analytics_agent.queue.dispatcher import enqueue_stt
from interview_analytics_agent.queue.idempotency import check_and_set
from interview_analytics_agent.services.local_pipeline import process_chunk_inline
from interview_analytics_agent.storage.blob import put_bytes

log = get_project_logger()


@dataclass
class ChunkIngestResult:
    accepted: bool
    meeting_id: str
    seq: int
    idempotency_key: str
    blob_key: str
    is_duplicate: bool
    inline_updates: list[dict] | None = None


def ingest_audio_chunk_bytes(
    *,
    meeting_id: str,
    seq: int,
    audio_bytes: bytes,
    source_track: str | None = None,
    quality_profile: str = "live",
    capture_levels: dict[str, float] | None = None,
    idempotency_key: str | None = None,
    idempotency_scope: str = "audio_chunk_http",
    idempotency_prefix: str = "http-chunk",
    defer_inline_processing: bool = False,
) -> ChunkIngestResult:
    idem_key = idempotency_key or new_idempotency_key(idempotency_prefix)
    blob_key = f"meetings/{meeting_id}/chunks/{seq}.bin"

    if not check_and_set(idempotency_scope, meeting_id, idem_key):
        log.info(
            "chunk_ingest_duplicate",
            extra={
                "payload": {
                    "meeting_id": meeting_id,
                    "seq": seq,
                    "scope": idempotency_scope,
                    "source_track": source_track or "",
                }
            },
        )
        return ChunkIngestResult(
            accepted=True,
            meeting_id=meeting_id,
            seq=seq,
            idempotency_key=idem_key,
            blob_key=blob_key,
            is_duplicate=True,
        )

    put_bytes(blob_key, audio_bytes)
    if seq < 3 or seq % 25 == 0:
        log.info(
            "chunk_ingest_saved",
            extra={
                "payload": {
                    "meeting_id": meeting_id,
                    "seq": seq,
                    "bytes": len(audio_bytes),
                    "blob_key": blob_key,
                    "source_track": source_track or "",
                    "quality_profile": quality_profile,
                    "capture_levels": capture_levels or {},
                }
            },
        )
    inline_updates: list[dict] | None = None
    settings = get_settings()
    if (settings.queue_mode or "").strip().lower() == "inline":
        if not defer_inline_processing:
            inline_updates = process_chunk_inline(
                meeting_id=meeting_id,
                chunk_seq=seq,
                audio_bytes=audio_bytes,
                blob_key=blob_key,
                quality_profile=quality_profile,
                source_track=source_track,
                capture_levels=capture_levels,
            )
    else:
        enqueue_args = {
            "meeting_id": meeting_id,
            "chunk_seq": seq,
            "blob_key": blob_key,
            "source_track": source_track,
            "quality_profile": quality_profile,
        }
        if capture_levels:
            enqueue_args["capture_levels"] = capture_levels
        enqueue_stt(
            **enqueue_args,
        )
    return ChunkIngestResult(
        accepted=True,
        meeting_id=meeting_id,
        seq=seq,
        idempotency_key=idem_key,
        blob_key=blob_key,
        is_duplicate=False,
        inline_updates=inline_updates,
    )


def ingest_audio_chunk_b64(
    *,
    meeting_id: str,
    seq: int,
    content_b64: str,
    source_track: str | None = None,
    quality_profile: str = "live",
    capture_levels: dict[str, float] | None = None,
    idempotency_key: str | None = None,
    idempotency_scope: str = "audio_chunk_http",
    idempotency_prefix: str = "http-chunk",
) -> ChunkIngestResult:
    try:
        audio_bytes = b64_decode(content_b64)
    except Exception as e:
        raise ValueError("content_b64 decode failed") from e
    return ingest_audio_chunk_bytes(
        meeting_id=meeting_id,
        seq=seq,
        audio_bytes=audio_bytes,
        source_track=source_track,
        quality_profile=quality_profile,
        capture_levels=capture_levels,
        idempotency_key=idempotency_key,
        idempotency_scope=idempotency_scope,
        idempotency_prefix=idempotency_prefix,
    )
