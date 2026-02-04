from __future__ import annotations

import pytest

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.services.security_audit_service import list_security_audit_events


def test_list_security_audit_events_returns_empty_when_disabled() -> None:
    s = get_settings()
    prev = s.security_audit_db_enabled
    s.security_audit_db_enabled = False
    try:
        assert list_security_audit_events(limit=10) == []
    finally:
        s.security_audit_db_enabled = prev


def test_list_security_audit_events_rejects_invalid_outcome() -> None:
    s = get_settings()
    prev = s.security_audit_db_enabled
    s.security_audit_db_enabled = True
    try:
        with pytest.raises(ValueError):
            _ = list_security_audit_events(limit=10, outcome="bad")
    finally:
        s.security_audit_db_enabled = prev
