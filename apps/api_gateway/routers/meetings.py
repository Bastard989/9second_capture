"""
HTTP роуты для встреч.

MVP:
- POST /v1/meetings/start
- GET  /v1/meetings/{meeting_id}

Авторизация: Depends(auth_dep)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api_gateway.deps import auth_dep
from apps.api_gateway.tenancy import apply_tenant_to_context, enforce_meeting_access
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, ProviderError
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.common.security import AuthContext
from interview_analytics_agent.contracts.http_api import (
    MeetingGetResponse,
    MeetingStartRequest,
    MeetingStartResponse,
)
from interview_analytics_agent.domain.enums import MeetingMode, PipelineStatus
from interview_analytics_agent.services.meeting_service import create_meeting
from interview_analytics_agent.services.sberjazz_service import join_sberjazz_meeting
from interview_analytics_agent.storage import records
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import MeetingRepository

log = get_project_logger()

router = APIRouter()

_WORK_MODE_REALTIME = {"driver_audio", "browser_screen_audio"}
_WORK_MODE_POSTMEETING = {"api_upload", "link_fallback"}
_KNOWN_WORK_MODES = _WORK_MODE_REALTIME | _WORK_MODE_POSTMEETING


def _normalize_context_for_work_mode(
    *,
    req: MeetingStartRequest,
    context: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(context or {})
    raw_work_mode = str(payload.get("work_mode") or payload.get("source_mode") or "").strip().lower()
    if not raw_work_mode:
        return payload

    if raw_work_mode not in _KNOWN_WORK_MODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_work_mode",
                "message": raw_work_mode,
            },
        )

    if raw_work_mode in _WORK_MODE_REALTIME and req.mode != MeetingMode.realtime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_work_mode_for_mode",
                "message": f"{raw_work_mode} requires mode=realtime",
            },
        )
    if raw_work_mode in _WORK_MODE_POSTMEETING and req.mode != MeetingMode.postmeeting:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_work_mode_for_mode",
                "message": f"{raw_work_mode} requires mode=postmeeting",
            },
        )

    payload["work_mode"] = raw_work_mode
    payload["source_mode"] = raw_work_mode

    if raw_work_mode == "driver_audio":
        payload["capture_mode"] = "system"
        payload.pop("filename", None)
    elif raw_work_mode == "browser_screen_audio":
        payload["capture_mode"] = "screen"
        payload.pop("filename", None)
    elif raw_work_mode in {"api_upload", "link_fallback"}:
        payload.pop("capture_mode", None)
        payload.pop("include_mic", None)
        payload.pop("mic_device_id", None)

    return payload


def _should_auto_join(req: MeetingStartRequest) -> bool:
    if req.auto_join_connector is not None:
        return bool(req.auto_join_connector)

    if req.mode != MeetingMode.realtime:
        return False

    settings = get_settings()
    provider = (settings.meeting_connector_provider or "").strip().lower()
    if provider in {"", "none"}:
        return False
    return bool(settings.meeting_auto_join_on_start)


def _find_active_local_recording(
    *,
    repo: MeetingRepository,
    requested_meeting_id: str | None,
) -> str | None:
    for meeting in repo.list_active():
        if requested_meeting_id and meeting.id == requested_meeting_id:
            continue
        if getattr(meeting, "finished_at", None) is not None:
            continue
        if meeting.status == PipelineStatus.done:
            continue
        context = meeting.context or {}
        source = str(context.get("source") or "").strip().lower()
        if source == "local_ui":
            return meeting.id
    return None


@router.post("/meetings/start", response_model=MeetingStartResponse)
def start_meeting(
    req: MeetingStartRequest,
    ctx: AuthContext = Depends(auth_dep),
) -> MeetingStartResponse:
    connector_auto_join = _should_auto_join(req)
    connector_provider: str | None = None
    connector_connected: bool | None = None
    context = apply_tenant_to_context(ctx, req.context)
    context = _normalize_context_for_work_mode(req=req, context=context)

    with db_session() as s:
        repo = MeetingRepository(s)
        if req.mode == MeetingMode.realtime:
            active_meeting_id = _find_active_local_recording(
                repo=repo,
                requested_meeting_id=req.meeting_id,
            )
            if active_meeting_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "active_recording_exists",
                        "message": active_meeting_id,
                    },
                )
        m = create_meeting(meeting_id=req.meeting_id, context=context, consent=req.consent)
        repo.save(m)

        if connector_auto_join:
            try:
                conn_state = join_sberjazz_meeting(m.id)
                connector_provider = conn_state.provider
                connector_connected = conn_state.connected
            except ProviderError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": ErrCode.CONNECTOR_PROVIDER_ERROR,
                        "message": e.message,
                        "details": e.details or {},
                    },
                ) from e

        log.info("meeting_created", extra={"meeting_id": m.id})
        records.ensure_meeting_metadata(m.id)
        return MeetingStartResponse(
            meeting_id=m.id,
            status=str(m.status),
            connector_auto_join=connector_auto_join,
            connector_provider=connector_provider,
            connector_connected=connector_connected,
        )


@router.get("/meetings/{meeting_id}", response_model=MeetingGetResponse)
def get_meeting(
    meeting_id: str,
    ctx: AuthContext = Depends(auth_dep),
) -> MeetingGetResponse:
    with db_session() as s:
        repo = MeetingRepository(s)
        m = repo.get(meeting_id)
        if not m:
            return MeetingGetResponse(meeting_id=meeting_id, status="not_found")
        enforce_meeting_access(ctx, m.context)

        return MeetingGetResponse(
            meeting_id=m.id,
            status=str(m.status),
            raw_transcript=m.raw_transcript or "",
            enhanced_transcript=m.enhanced_transcript or "",
            report=m.report,
        )
