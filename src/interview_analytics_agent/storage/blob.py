from __future__ import annotations

import os
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, ProviderError

_HEALTH_CACHE: dict[str, object] = {"ts": 0.0, "value": None}


@dataclass
class StorageHealth:
    mode: str
    base_dir: str
    healthy: bool
    error: str | None = None


def _is_prod_env(app_env: str | None) -> bool:
    env = (app_env or "").strip().lower()
    return env in {"prod", "production"}


def _storage_mode() -> str:
    s = get_settings()
    mode = (s.storage_mode or "local_fs").strip().lower()
    if mode not in {"local_fs", "shared_fs"}:
        raise ProviderError(
            ErrCode.STORAGE_ERROR,
            f"Неизвестный STORAGE_MODE: {mode}",
            details={"allowed": "local_fs,shared_fs"},
        )
    if (
        _is_prod_env(s.app_env)
        and bool(getattr(s, "storage_require_shared_in_prod", True))
        and mode != "shared_fs"
    ):
        raise ProviderError(
            ErrCode.STORAGE_ERROR,
            "В APP_ENV=prod требуется STORAGE_MODE=shared_fs",
            details={"storage_mode": mode},
        )
    return mode


def _base_dir() -> Path:
    s = get_settings()
    mode = _storage_mode()
    if mode == "shared_fs":
        root = (s.storage_shared_fs_dir or s.chunks_dir or "").strip()
    else:
        root = (s.chunks_dir or os.getenv("CHUNKS_DIR", "./data/chunks")).strip()
    return Path(root or "./data/chunks").resolve()


def _key_to_path(key: str) -> Path:
    # защита от path traversal
    key = key.lstrip("/")
    if ".." in key.split("/"):
        raise ValueError("invalid key")
    return _base_dir() / key


def put_bytes(key: str, data: bytes) -> str:
    """Сохранить bytes и вернуть ключ."""
    p = _key_to_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.parent / f".tmp-{p.name}-{uuid4().hex}"
    tmp.write_bytes(data)
    tmp.replace(p)
    return key


def get_bytes(key: str) -> bytes:
    return _key_to_path(key).read_bytes()


def exists(key: str) -> bool:
    return _key_to_path(key).exists()


def delete(key: str) -> None:
    p = _key_to_path(key)
    with suppress(FileNotFoundError):
        p.unlink()


def check_storage_health() -> StorageHealth:
    try:
        mode = _storage_mode()
        base = _base_dir()
        base.mkdir(parents=True, exist_ok=True)
        probe_key = f"health/probe-{uuid4().hex}.bin"
        payload = b"ok"
        put_bytes(probe_key, payload)
        got = get_bytes(probe_key)
        delete(probe_key)
        if got != payload:
            return StorageHealth(
                mode=mode,
                base_dir=str(base),
                healthy=False,
                error="storage read/write mismatch",
            )
        return StorageHealth(mode=mode, base_dir=str(base), healthy=True)
    except Exception as e:
        s = get_settings()
        return StorageHealth(
            mode=(s.storage_mode or "unknown"),
            base_dir=(s.storage_shared_fs_dir or s.chunks_dir or "unknown"),
            healthy=False,
            error=str(e)[:300],
        )


def check_storage_health_cached(max_age_sec: int = 30) -> StorageHealth:
    now = time.time()
    last_ts = float(_HEALTH_CACHE.get("ts", 0.0) or 0.0)
    cached = _HEALTH_CACHE.get("value")
    if isinstance(cached, StorageHealth) and (now - last_ts) < max(1, max_age_sec):
        return cached
    current = check_storage_health()
    _HEALTH_CACHE["ts"] = now
    _HEALTH_CACHE["value"] = current
    return current
