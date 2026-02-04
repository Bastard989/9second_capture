"""
Service layer для SberJazz connector.

Содержит:
- выбор провайдера коннектора (real/mock)
- retry/backoff для join/leave
- хранение состояния сессии (in-memory + Redis)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, ProviderError
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.connectors.base import MeetingConnector
from interview_analytics_agent.connectors.salutejazz.adapter import SaluteJazzConnector
from interview_analytics_agent.connectors.salutejazz.mock import MockSaluteJazzConnector
from interview_analytics_agent.queue.redis import redis_client

log = get_project_logger()


@dataclass
class SberJazzSessionState:
    meeting_id: str
    provider: str
    connected: bool
    attempts: int
    last_error: str | None
    updated_at: str


_SESSIONS: dict[str, SberJazzSessionState] = {}
_SESSION_KEY_PREFIX = "connector:sberjazz:session:"
_SESSION_INDEX_KEY = "connector:sberjazz:sessions"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_connector() -> tuple[str, MeetingConnector]:
    s = get_settings()
    provider = (s.meeting_connector_provider or "sberjazz_mock").strip().lower()
    if provider == "sberjazz":
        return provider, SaluteJazzConnector()
    if provider == "sberjazz_mock":
        return provider, MockSaluteJazzConnector()
    raise ProviderError(
        ErrCode.CONNECTOR_PROVIDER_ERROR,
        f"Неизвестный provider: {provider}",
        details={"allowed": "sberjazz,sberjazz_mock"},
    )


def _retry_config() -> tuple[int, float]:
    s = get_settings()
    attempts = max(1, int(s.sberjazz_retries) + 1)
    backoff_sec = max(0, int(s.sberjazz_retry_backoff_ms)) / 1000.0
    return attempts, backoff_sec


def _session_ttl_sec() -> int:
    s = get_settings()
    return max(60, int(getattr(s, "sberjazz_session_ttl_sec", 86_400)))


def _session_key(meeting_id: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{meeting_id}"


def _save_state_redis(state: SberJazzSessionState) -> None:
    r = redis_client()
    payload = json.dumps(asdict(state), ensure_ascii=False)
    r.set(_session_key(state.meeting_id), payload, ex=_session_ttl_sec())
    r.sadd(_SESSION_INDEX_KEY, state.meeting_id)


def _load_state_redis(meeting_id: str) -> SberJazzSessionState | None:
    raw = redis_client().get(_session_key(meeting_id))
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        return None
    try:
        return SberJazzSessionState(
            meeting_id=str(data["meeting_id"]),
            provider=str(data["provider"]),
            connected=bool(data["connected"]),
            attempts=int(data["attempts"]),
            last_error=str(data["last_error"]) if data.get("last_error") is not None else None,
            updated_at=str(data["updated_at"]),
        )
    except Exception:
        return None


def _save_state(state: SberJazzSessionState) -> SberJazzSessionState:
    _SESSIONS[state.meeting_id] = state
    try:
        _save_state_redis(state)
    except Exception as e:
        log.warning(
            "sberjazz_state_redis_write_failed",
            extra={"payload": {"meeting_id": state.meeting_id, "error": str(e)[:200]}},
        )
    return state


def get_sberjazz_meeting_state(meeting_id: str) -> SberJazzSessionState:
    try:
        state = _load_state_redis(meeting_id)
        if state:
            _SESSIONS[meeting_id] = state
            return state
    except Exception as e:
        log.warning(
            "sberjazz_state_redis_read_failed",
            extra={"payload": {"meeting_id": meeting_id, "error": str(e)[:200]}},
        )

    state = _SESSIONS.get(meeting_id)
    if state:
        return state
    provider, _ = _resolve_connector()
    return SberJazzSessionState(
        meeting_id=meeting_id,
        provider=provider,
        connected=False,
        attempts=0,
        last_error=None,
        updated_at=_now_iso(),
    )


def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(UTC)


def list_sberjazz_sessions(limit: int = 100) -> list[SberJazzSessionState]:
    meeting_ids: set[str] = set(_SESSIONS.keys())
    try:
        from_redis = redis_client().smembers(_SESSION_INDEX_KEY)
        meeting_ids.update(str(v) for v in from_redis if str(v).strip())
    except Exception as e:
        log.warning(
            "sberjazz_sessions_list_redis_failed",
            extra={"payload": {"error": str(e)[:200]}},
        )

    states = [get_sberjazz_meeting_state(mid) for mid in meeting_ids]
    states.sort(key=lambda x: _parse_dt(x.updated_at), reverse=True)
    return states[: max(1, limit)]


def join_sberjazz_meeting(meeting_id: str) -> SberJazzSessionState:
    provider, connector = _resolve_connector()
    attempts, backoff_sec = _retry_config()
    last_error: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            connector.join(meeting_id)
            state = SberJazzSessionState(
                meeting_id=meeting_id,
                provider=provider,
                connected=True,
                attempts=attempt,
                last_error=None,
                updated_at=_now_iso(),
            )
            log.info(
                "sberjazz_join_success",
                extra={"payload": {"meeting_id": meeting_id, "attempt": attempt}},
            )
            return _save_state(state)
        except Exception as e:
            last_error = str(e)[:300]
            log.warning(
                "sberjazz_join_retry",
                extra={
                    "payload": {
                        "meeting_id": meeting_id,
                        "attempt": attempt,
                        "error": last_error,
                    }
                },
            )
            if attempt < attempts and backoff_sec > 0:
                time.sleep(backoff_sec * attempt)

    state = SberJazzSessionState(
        meeting_id=meeting_id,
        provider=provider,
        connected=False,
        attempts=attempts,
        last_error=last_error,
        updated_at=_now_iso(),
    )
    _save_state(state)
    raise ProviderError(
        ErrCode.CONNECTOR_PROVIDER_ERROR,
        "SberJazz join не выполнен после retries",
        details=asdict(state),
    )


def leave_sberjazz_meeting(meeting_id: str) -> SberJazzSessionState:
    provider, connector = _resolve_connector()
    attempts, backoff_sec = _retry_config()
    last_error: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            connector.leave(meeting_id)
            state = SberJazzSessionState(
                meeting_id=meeting_id,
                provider=provider,
                connected=False,
                attempts=attempt,
                last_error=None,
                updated_at=_now_iso(),
            )
            log.info(
                "sberjazz_leave_success",
                extra={"payload": {"meeting_id": meeting_id, "attempt": attempt}},
            )
            return _save_state(state)
        except Exception as e:
            last_error = str(e)[:300]
            log.warning(
                "sberjazz_leave_retry",
                extra={
                    "payload": {
                        "meeting_id": meeting_id,
                        "attempt": attempt,
                        "error": last_error,
                    }
                },
            )
            if attempt < attempts and backoff_sec > 0:
                time.sleep(backoff_sec * attempt)

    state = SberJazzSessionState(
        meeting_id=meeting_id,
        provider=provider,
        connected=True,
        attempts=attempts,
        last_error=last_error,
        updated_at=_now_iso(),
    )
    _save_state(state)
    raise ProviderError(
        ErrCode.CONNECTOR_PROVIDER_ERROR,
        "SberJazz leave не выполнен после retries",
        details=asdict(state),
    )


def reconnect_sberjazz_meeting(meeting_id: str) -> SberJazzSessionState:
    state = get_sberjazz_meeting_state(meeting_id)
    if state.connected:
        try:
            leave_sberjazz_meeting(meeting_id)
        except ProviderError as e:
            log.warning(
                "sberjazz_reconnect_leave_failed",
                extra={"payload": {"meeting_id": meeting_id, "error": str(e)[:200]}},
            )
    return join_sberjazz_meeting(meeting_id)


@dataclass
class SberJazzConnectorHealth:
    provider: str
    configured: bool
    healthy: bool
    details: dict[str, str]
    updated_at: str


@dataclass
class SberJazzReconcileResult:
    scanned: int
    stale: int
    reconnected: int
    failed: int
    stale_threshold_sec: int
    updated_at: str


def reconcile_sberjazz_sessions(limit: int = 200) -> SberJazzReconcileResult:
    stale_threshold_sec = max(30, int(getattr(get_settings(), "sberjazz_reconcile_stale_sec", 900)))
    now = datetime.now(UTC)
    scanned = 0
    stale = 0
    reconnected = 0
    failed = 0

    for state in list_sberjazz_sessions(limit=limit):
        scanned += 1
        if not state.connected:
            continue
        age_sec = (now - _parse_dt(state.updated_at)).total_seconds()
        if age_sec < stale_threshold_sec:
            continue

        stale += 1
        try:
            reconnect_sberjazz_meeting(state.meeting_id)
            reconnected += 1
        except Exception as e:
            failed += 1
            log.warning(
                "sberjazz_reconcile_reconnect_failed",
                extra={
                    "payload": {
                        "meeting_id": state.meeting_id,
                        "error": str(e)[:300],
                    }
                },
            )

    return SberJazzReconcileResult(
        scanned=scanned,
        stale=stale,
        reconnected=reconnected,
        failed=failed,
        stale_threshold_sec=stale_threshold_sec,
        updated_at=_now_iso(),
    )


def get_sberjazz_connector_health() -> SberJazzConnectorHealth:
    provider, connector = _resolve_connector()
    if provider == "sberjazz_mock":
        return SberJazzConnectorHealth(
            provider=provider,
            configured=True,
            healthy=True,
            details={"mode": "mock"},
            updated_at=_now_iso(),
        )

    s = get_settings()
    configured = bool((s.sberjazz_api_base or "").strip())
    if not configured:
        return SberJazzConnectorHealth(
            provider=provider,
            configured=False,
            healthy=False,
            details={"error": "SBERJAZZ_API_BASE is empty"},
            updated_at=_now_iso(),
        )

    try:
        # best-effort health ping for real connector
        health_fn = getattr(connector, "health", None)
        if callable(health_fn):
            health_fn()
        return SberJazzConnectorHealth(
            provider=provider,
            configured=True,
            healthy=True,
            details={},
            updated_at=_now_iso(),
        )
    except Exception as e:
        return SberJazzConnectorHealth(
            provider=provider,
            configured=True,
            healthy=False,
            details={"error": str(e)[:300]},
            updated_at=_now_iso(),
        )
