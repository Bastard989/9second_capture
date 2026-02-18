"""
WebSocket обработчик.

Протокол (MVP):
- клиент присылает JSON {"event_type":"audio.chunk", ...}
- payload содержит base64 audio (content_b64), seq, meeting_id, sample_rate, channels, codec
- gateway сохраняет аудио в локальное хранилище и ставит задачу STT
- воркеры публикуют transcript.update в Redis pubsub channel ws:<meeting_id>
- gateway подписывается и ретранслирует клиенту

Важно:
- в MVP не делаем сложный backpressure, только базовая дедупликация
"""

from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from apps.api_gateway.tenancy import enforce_meeting_access, tenant_enforcement_enabled
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, UnauthorizedError
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.common.security import (
    AuthContext,
    has_any_service_permission,
    is_service_jwt_claims,
    require_auth,
)
from interview_analytics_agent.common.tracing import start_trace
from interview_analytics_agent.common.utils import b64_decode, safe_dict
from interview_analytics_agent.queue.redis import redis_client
from interview_analytics_agent.services.chunk_ingest_service import ingest_audio_chunk_bytes
from interview_analytics_agent.services.local_pipeline import process_chunk_inline
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import MeetingRepository

log = get_project_logger()

ws_router = APIRouter()


async def _ws_send_text_safe(ws: WebSocket, text: str) -> bool:
    if ws.application_state != WebSocketState.CONNECTED:
        return False
    try:
        await ws.send_text(text)
        return True
    except Exception:
        return False


async def _ws_send_json_safe(ws: WebSocket, payload: dict) -> bool:
    return await _ws_send_text_safe(ws, json.dumps(payload, ensure_ascii=False))


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _is_service_ctx(ctx: AuthContext) -> bool:
    return ctx.auth_type == "service_api_key" or (
        ctx.auth_type == "jwt" and is_service_jwt_claims(ctx.claims)
    )


def _ws_client_ip(ws: WebSocket) -> str | None:
    return ws.client.host if ws.client else None


def _parse_scopes(raw: str) -> set[str]:
    return {s.strip() for s in (raw or "").split(",") if s.strip()}


def _should_log_capture_snapshot(seq: int, accepted_chunks: int) -> bool:
    if seq < 3:
        return True
    return accepted_chunks > 0 and accepted_chunks % 25 == 0


def _audit_ws_allow(*, ws: WebSocket, ctx: AuthContext, reason: str) -> None:
    log.info(
        "security_audit_allow",
        extra={
            "payload": {
                "endpoint": ws.url.path,
                "method": "WS",
                "subject": ctx.subject,
                "auth_type": ctx.auth_type,
                "reason": reason,
                "client_ip": _ws_client_ip(ws),
            }
        },
    )


def _audit_ws_deny(
    *,
    ws: WebSocket,
    reason: str,
    error_code: str,
    auth_type: str = "unknown",
    subject: str = "unknown",
) -> None:
    log.warning(
        "security_audit_deny",
        extra={
            "payload": {
                "endpoint": ws.url.path,
                "method": "WS",
                "status_code": status.WS_1008_POLICY_VIOLATION,
                "reason": reason,
                "error_code": error_code,
                "auth_type": auth_type,
                "subject": subject,
                "client_ip": _ws_client_ip(ws),
            }
        },
    )


async def _forward_pubsub_to_ws(ws: WebSocket, meeting_id: str) -> None:
    """
    Фоновая задача: читает pubsub канал ws:<meeting_id> и шлёт сообщения в websocket.
    Реализация через asyncio.to_thread, потому что redis_client() синхронный.
    """
    settings = get_settings()
    if (settings.queue_mode or "").strip().lower() == "inline":
        return

    channel = f"ws:{meeting_id}"
    try:
        r = redis_client()
        pubsub = r.pubsub()
        pubsub.subscribe(channel)
    except Exception as e:
        log.warning(
            "ws_pubsub_unavailable",
            extra={"payload": {"meeting_id": meeting_id, "err": str(e)[:200]}},
        )
        return

    try:
        while True:
            msg = await asyncio.to_thread(pubsub.get_message, True, 1.0)
            if not msg:
                await asyncio.sleep(0.01)
                continue
            if msg.get("type") != "message":
                continue

            data = msg.get("data")
            if not data:
                continue

            # data ожидаем как JSON-строку
            try:
                await ws.send_text(data)
            except Exception:
                break
    finally:
        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
        except Exception:
            pass


async def _process_inline_chunk_job(*, job: dict[str, object]) -> list[dict]:
    meeting_id = str(job.get("meeting_id") or "").strip()
    seq = _as_int(job.get("seq"), -1)
    blob_key = str(job.get("blob_key") or "").strip() or None
    source_track = str(job.get("source_track") or "").strip() or None
    quality_profile = str(job.get("quality_profile") or "live").strip() or "live"
    raw_levels = job.get("capture_levels")
    capture_levels = raw_levels if isinstance(raw_levels, dict) else None
    if not meeting_id or seq < 0:
        return []

    try:
        return await asyncio.to_thread(
            process_chunk_inline,
            meeting_id=meeting_id,
            chunk_seq=seq,
            blob_key=blob_key,
            source_track=source_track,
            quality_profile=quality_profile,
            capture_levels=capture_levels,
        )
    except Exception as e:
        log.error(
            "ws_inline_process_failed",
            extra={
                "payload": {
                    "meeting_id": meeting_id,
                    "seq": seq,
                    "err": str(e)[:200],
                }
            },
        )
        return []


async def _drain_inline_updates_queue(
    *,
    ws: WebSocket,
    queue: asyncio.Queue[dict[str, object] | None],
) -> None:
    while True:
        job = await queue.get()
        if job is None:
            queue.task_done()
            break
        try:
            updates = await _process_inline_chunk_job(job=job)
            for payload in updates:
                sent = await _ws_send_json_safe(ws, payload)
                if not sent:
                    return
        finally:
            queue.task_done()


async def _authorize_ws(ws: WebSocket, *, service_only: bool) -> AuthContext | None:
    try:
        ctx = require_auth(
            authorization=ws.headers.get("authorization"),
            x_api_key=ws.headers.get("x-api-key"),
        )
    except UnauthorizedError as e:
        _audit_ws_deny(ws=ws, reason=e.message, error_code=e.code)
        await ws.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"{e.code}: {e.message}",
        )
        return None

    if service_only:
        if not _is_service_ctx(ctx):
            _audit_ws_deny(
                ws=ws,
                reason="not_service_identity",
                error_code=ErrCode.FORBIDDEN,
                auth_type=ctx.auth_type,
                subject=ctx.subject,
            )
            await ws.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="forbidden: service identity required",
            )
            return None
        if ctx.auth_type == "jwt":
            required_scopes = _parse_scopes(get_settings().jwt_service_required_scopes_ws_internal)
            if required_scopes and not has_any_service_permission(
                ctx.claims, required_permissions=required_scopes
            ):
                _audit_ws_deny(
                    ws=ws,
                    reason="missing_service_scope",
                    error_code=ErrCode.FORBIDDEN,
                    auth_type=ctx.auth_type,
                    subject=ctx.subject,
                )
                await ws.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="forbidden: missing service scope",
                )
                return None
        _audit_ws_allow(ws=ws, ctx=ctx, reason="ws_service_auth_ok")
        return ctx

    # user websocket endpoint
    if _is_service_ctx(ctx):
        _audit_ws_deny(
            ws=ws,
            reason="service_identity_not_allowed",
            error_code=ErrCode.FORBIDDEN,
            auth_type=ctx.auth_type,
            subject=ctx.subject,
        )
        await ws.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="forbidden: use /v1/ws/internal for service identities",
        )
        return None

    _audit_ws_allow(ws=ws, ctx=ctx, reason="ws_user_auth_ok")
    return ctx


async def _websocket_endpoint_impl(ws: WebSocket, *, service_only: bool) -> None:
    ctx = await _authorize_ws(ws, service_only=service_only)
    if ctx is None:
        return

    await ws.accept()

    meeting_id: str | None = None
    meeting_checked = False
    forward_task: asyncio.Task | None = None
    inline_queue: asyncio.Queue[dict[str, object] | None] | None = None
    inline_worker_task: asyncio.Task | None = None
    accepted_chunks = 0
    last_acked_seq = -1
    if (get_settings().queue_mode or "").strip().lower() == "inline":
        inline_queue = asyncio.Queue()
        inline_worker_task = asyncio.create_task(_drain_inline_updates_queue(ws=ws, queue=inline_queue))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                event = json.loads(raw)
            except Exception:
                sent = await _ws_send_json_safe(
                    ws, {"event_type": "error", "code": "bad_json", "message": "Невалидный JSON"}
                )
                if not sent:
                    break
                continue

            et = event.get("event_type")
            if et == "ping":
                hb_meeting_id = event.get("meeting_id") or meeting_id
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "ws.pong",
                        "meeting_id": hb_meeting_id,
                        "ts_ms": int(time.time() * 1000),
                        "last_acked_seq": last_acked_seq,
                        "accepted_chunks": accepted_chunks,
                    },
                )
                if not sent:
                    break
                continue

            if et == "session.resume":
                resume_meeting_id = str(event.get("meeting_id") or "").strip() or meeting_id
                if resume_meeting_id:
                    meeting_id = resume_meeting_id
                    if (
                        forward_task is None
                        and (get_settings().queue_mode or "").strip().lower() != "inline"
                    ):
                        forward_task = asyncio.create_task(_forward_pubsub_to_ws(ws, meeting_id))
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "ws.resumed",
                        "meeting_id": meeting_id,
                        "client_last_seq": _as_int(event.get("last_seq"), -1),
                        "last_acked_seq": last_acked_seq,
                        "accepted_chunks": accepted_chunks,
                    },
                )
                if not sent:
                    break
                continue

            if et != "audio.chunk":
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "error",
                        "code": "bad_event",
                        "message": "Неизвестный event_type",
                    },
                )
                if not sent:
                    break
                continue

            meeting_id = event.get("meeting_id")
            if not meeting_id:
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "error",
                        "code": "no_meeting_id",
                        "message": "meeting_id обязателен",
                    },
                )
                if not sent:
                    break
                continue

            if not meeting_checked and tenant_enforcement_enabled() and not service_only:
                def _check_meeting() -> tuple[bool, str | None]:
                    with db_session() as s:
                        repo = MeetingRepository(s)
                        m = repo.get(meeting_id)
                        if not m:
                            return False, "Встреча не найдена"
                        try:
                            enforce_meeting_access(ctx, m.context)
                        except Exception as e:
                            msg = getattr(e, "detail", None)
                            if isinstance(msg, dict):
                                return False, str(msg.get("message") or "Доступ запрещён")
                            return False, "Доступ запрещён"
                        return True, None

                ok, err = await asyncio.to_thread(_check_meeting)
                if not ok:
                    await _ws_send_json_safe(
                        ws,
                        {
                            "event_type": "error",
                            "code": "forbidden",
                            "message": err or "Доступ запрещён",
                        },
                    )
                    await ws.close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason=err or "forbidden",
                    )
                    return
                meeting_checked = True

            # Запускаем forward только один раз, когда получили meeting_id
            if forward_task is None and (get_settings().queue_mode or "").strip().lower() != "inline":
                forward_task = asyncio.create_task(_forward_pubsub_to_ws(ws, meeting_id))

            seq = _as_int(event.get("seq"), -1)
            if seq < 0:
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "error",
                        "code": "bad_seq",
                        "message": "seq должен быть целым числом >= 0",
                    },
                )
                if not sent:
                    break
                continue
            content_b64 = event.get("content_b64", "")
            source_track = event.get("source_track")
            quality_profile = str(event.get("quality_profile") or "live")
            mixed_level = _as_float(event.get("mixed_level"), -1.0)
            system_level = _as_float(event.get("system_level"), -1.0)
            mic_level = _as_float(event.get("mic_level"), -1.0)
            capture_levels = None
            if mixed_level >= 0.0 or system_level >= 0.0 or mic_level >= 0.0:
                capture_levels = {}
                if mixed_level >= 0.0:
                    capture_levels["mixed"] = mixed_level
                if system_level >= 0.0:
                    capture_levels["system"] = system_level
                if mic_level >= 0.0:
                    capture_levels["mic"] = mic_level
            idem_key = event.get("idempotency_key")

            try:
                audio_bytes = b64_decode(content_b64)
            except Exception:
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "error",
                        "code": "bad_audio",
                        "message": "content_b64 не декодируется",
                    },
                )
                if not sent:
                    break
                continue

            try:
                with start_trace(
                    trace_id=event.get("trace_id"),
                    meeting_id=meeting_id,
                    source="ws.ingest",
                ):
                    result = ingest_audio_chunk_bytes(
                        meeting_id=meeting_id,
                        seq=seq,
                        audio_bytes=audio_bytes,
                        source_track=source_track,
                        quality_profile=quality_profile,
                        capture_levels=capture_levels,
                        idempotency_key=idem_key,
                        idempotency_scope="audio_chunk_ws",
                        idempotency_prefix="ws",
                        defer_inline_processing=bool(inline_queue),
                    )
            except Exception as e:
                log.error(
                    "ws_ingest_failed",
                    extra={"payload": {"meeting_id": meeting_id, "err": str(e)[:200]}},
                )
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "error",
                        "code": "storage_error",
                        "message": "Ошибка записи чанка",
                    },
                )
                if not sent:
                    break
                continue

            if result.is_duplicate:
                sent = await _ws_send_json_safe(
                    ws,
                    {
                        "event_type": "ws.ack",
                        "meeting_id": meeting_id,
                        "seq": seq,
                        "duplicate": True,
                        "last_acked_seq": max(last_acked_seq, seq),
                        "accepted_chunks": accepted_chunks,
                    },
                )
                if not sent:
                    break
                continue
            accepted_chunks += 1
            last_acked_seq = max(last_acked_seq, seq)
            if _should_log_capture_snapshot(seq, accepted_chunks):
                levels = capture_levels if isinstance(capture_levels, dict) else {}
                log.info(
                    "ws_chunk_capture_snapshot",
                    extra={
                        "payload": {
                            "meeting_id": meeting_id,
                            "seq": seq,
                            "accepted_chunks": accepted_chunks,
                            "source_track": source_track or "",
                            "quality_profile": quality_profile,
                            "levels": {
                                "mixed": float(levels.get("mixed", -1.0)),
                                "system": float(levels.get("system", -1.0)),
                                "mic": float(levels.get("mic", -1.0)),
                            },
                        }
                    },
                )
                if float(levels.get("system", -1.0)) >= 0 and float(levels.get("system", 0.0)) < 0.02:
                    log.warning(
                        "ws_chunk_low_system_level",
                        extra={
                            "payload": {
                                "meeting_id": meeting_id,
                                "seq": seq,
                                "system_level": float(levels.get("system", 0.0)),
                                "mic_level": float(levels.get("mic", -1.0)),
                                "hint": "check_loopback_routing",
                            }
                        },
                    )

            sent = await _ws_send_json_safe(
                ws,
                {
                    "event_type": "ws.ack",
                    "meeting_id": meeting_id,
                    "seq": seq,
                    "duplicate": False,
                    "last_acked_seq": last_acked_seq,
                    "accepted_chunks": accepted_chunks,
                },
            )
            if not sent:
                break

            if inline_queue is not None:
                try:
                    inline_queue.put_nowait(
                        {
                            "meeting_id": meeting_id,
                            "seq": seq,
                            "blob_key": result.blob_key,
                            "source_track": source_track,
                            "quality_profile": quality_profile,
                            "capture_levels": capture_levels or {},
                        }
                    )
                except Exception:
                    log.warning(
                        "ws_inline_queue_enqueue_failed",
                        extra={"payload": {"meeting_id": meeting_id, "seq": seq}},
                    )

            if result.inline_updates:
                for payload in result.inline_updates:
                    try:
                        sent = await _ws_send_json_safe(ws, payload)
                        if not sent:
                            return
                    except Exception:
                        return

    except WebSocketDisconnect:
        log.info(
            "ws_client_disconnected",
            extra={
                "payload": {
                    "meeting_id": meeting_id,
                    "accepted_chunks": accepted_chunks,
                }
            },
        )
    except Exception as e:
        message = str(e).lower()
        if "websocket is not connected" in message or "need to call \"accept\" first" in message:
            log.info(
                "ws_disconnected_while_sending",
                extra={"payload": {"meeting_id": meeting_id, "accepted_chunks": accepted_chunks}},
            )
            return
        log.error(
            "ws_fatal",
            extra={
                "payload": {
                    "err": str(e)[:200],
                    "event": safe_dict(event) if 'event' in locals() else None,
                }
            },
        )
    finally:
        if inline_queue is not None:
            try:
                inline_queue.put_nowait(None)
            except Exception:
                pass
        if inline_worker_task:
            inline_worker_task.cancel()
        if forward_task:
            forward_task.cancel()


@ws_router.websocket("/ws")
async def websocket_user_endpoint(ws: WebSocket) -> None:
    await _websocket_endpoint_impl(ws, service_only=False)


@ws_router.websocket("/ws/internal")
async def websocket_internal_endpoint(ws: WebSocket) -> None:
    await _websocket_endpoint_impl(ws, service_only=True)
