"""
Service для персистентного security audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import SecurityAuditRepository

log = get_project_logger()


@dataclass
class SecurityAuditEventView:
    id: int
    created_at: str
    outcome: str
    endpoint: str
    method: str
    subject: str
    auth_type: str
    reason: str
    error_code: str | None
    status_code: int
    client_ip: str | None


def _normalize_outcome(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"allow", "deny"}:
        return normalized
    raise ValueError("outcome должен быть allow или deny")


def write_security_audit_event(
    *,
    outcome: str,
    endpoint: str,
    method: str,
    subject: str,
    auth_type: str,
    reason: str,
    status_code: int,
    error_code: str | None = None,
    client_ip: str | None = None,
) -> None:
    if not bool(getattr(get_settings(), "security_audit_db_enabled", True)):
        return
    normalized_outcome = _normalize_outcome(outcome)
    if normalized_outcome is None:
        return
    try:
        with db_session() as session:
            repo = SecurityAuditRepository(session)
            repo.add_event(
                outcome=normalized_outcome,
                endpoint=endpoint,
                method=method,
                subject=subject,
                auth_type=auth_type,
                reason=reason,
                status_code=status_code,
                error_code=error_code,
                client_ip=client_ip,
            )
    except Exception as e:
        log.warning(
            "security_audit_db_write_failed",
            extra={"payload": {"error": str(e)[:200], "endpoint": endpoint, "method": method}},
        )


def list_security_audit_events(
    *,
    limit: int = 100,
    outcome: str | None = None,
    subject: str | None = None,
) -> list[SecurityAuditEventView]:
    normalized_outcome = _normalize_outcome(outcome)
    if not bool(getattr(get_settings(), "security_audit_db_enabled", True)):
        return []
    with db_session() as session:
        repo = SecurityAuditRepository(session)
        events = repo.list_recent(limit=limit, outcome=normalized_outcome, subject=subject)
    return [
        SecurityAuditEventView(
            id=e.id,
            created_at=e.created_at.isoformat(),
            outcome=e.outcome,
            endpoint=e.endpoint,
            method=e.method,
            subject=e.subject,
            auth_type=e.auth_type,
            reason=e.reason,
            error_code=e.error_code,
            status_code=e.status_code,
            client_ip=e.client_ip,
        )
        for e in events
    ]
