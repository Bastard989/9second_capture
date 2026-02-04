from __future__ import annotations

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.services.readiness_service import evaluate_readiness


def test_readiness_prod_fails_on_none_auth_and_local_storage() -> None:
    s = get_settings()
    snapshot = (
        s.app_env,
        s.auth_mode,
        s.storage_mode,
        s.storage_require_shared_in_prod,
        s.cors_allowed_origins,
    )
    try:
        s.app_env = "prod"
        s.auth_mode = "none"
        s.storage_mode = "local_fs"
        s.storage_require_shared_in_prod = True
        s.cors_allowed_origins = "*"
        state = evaluate_readiness()
        codes = {i.code for i in state.issues}
        assert state.ready is False
        assert "auth_none_in_prod" in codes
        assert "storage_not_shared_fs" in codes
        assert "cors_wildcard_in_prod" in codes
    finally:
        (
            s.app_env,
            s.auth_mode,
            s.storage_mode,
            s.storage_require_shared_in_prod,
            s.cors_allowed_origins,
        ) = snapshot


def test_readiness_dev_allows_defaults() -> None:
    s = get_settings()
    snapshot = (
        s.app_env,
        s.auth_mode,
        s.storage_mode,
        s.api_keys,
    )
    try:
        s.app_env = "dev"
        s.auth_mode = "api_key"
        s.storage_mode = "local_fs"
        s.api_keys = "dev-key"
        state = evaluate_readiness()
        # warning'и допустимы, важно что нет ошибок.
        assert state.ready is True
    finally:
        (
            s.app_env,
            s.auth_mode,
            s.storage_mode,
            s.api_keys,
        ) = snapshot
