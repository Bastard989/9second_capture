from __future__ import annotations

import pytest

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ProviderError
from interview_analytics_agent.storage import blob


def test_local_fs_put_get_delete(tmp_path) -> None:
    s = get_settings()
    prev = (
        s.app_env,
        s.storage_mode,
        s.chunks_dir,
        s.storage_shared_fs_dir,
        s.storage_require_shared_in_prod,
    )
    s.app_env = "dev"
    s.storage_mode = "local_fs"
    s.chunks_dir = str(tmp_path / "chunks-local")
    s.storage_shared_fs_dir = None
    s.storage_require_shared_in_prod = True
    blob._HEALTH_CACHE["value"] = None
    blob._HEALTH_CACHE["ts"] = 0.0
    try:
        key = "meetings/m-1/chunks/1.bin"
        payload = b"abc123"
        blob.put_bytes(key, payload)
        assert blob.exists(key) is True
        assert blob.get_bytes(key) == payload
        blob.delete(key)
        assert blob.exists(key) is False
    finally:
        (
            s.app_env,
            s.storage_mode,
            s.chunks_dir,
            s.storage_shared_fs_dir,
            s.storage_require_shared_in_prod,
        ) = prev


def test_shared_fs_uses_shared_dir(tmp_path) -> None:
    s = get_settings()
    prev = (
        s.app_env,
        s.storage_mode,
        s.chunks_dir,
        s.storage_shared_fs_dir,
        s.storage_require_shared_in_prod,
    )
    shared_root = tmp_path / "shared"
    local_root = tmp_path / "local"
    s.app_env = "dev"
    s.storage_mode = "shared_fs"
    s.chunks_dir = str(local_root)
    s.storage_shared_fs_dir = str(shared_root)
    s.storage_require_shared_in_prod = True
    try:
        key = "meetings/m-2/chunks/2.bin"
        blob.put_bytes(key, b"x")
        assert (shared_root / key).exists()
        assert not (local_root / key).exists()
    finally:
        (
            s.app_env,
            s.storage_mode,
            s.chunks_dir,
            s.storage_shared_fs_dir,
            s.storage_require_shared_in_prod,
        ) = prev


def test_prod_rejects_local_fs_when_required(tmp_path) -> None:
    s = get_settings()
    prev = (
        s.app_env,
        s.storage_mode,
        s.chunks_dir,
        s.storage_shared_fs_dir,
        s.storage_require_shared_in_prod,
    )
    s.app_env = "prod"
    s.storage_mode = "local_fs"
    s.chunks_dir = str(tmp_path / "chunks")
    s.storage_shared_fs_dir = None
    s.storage_require_shared_in_prod = True
    try:
        with pytest.raises(ProviderError) as e:
            blob.put_bytes("meetings/m-3/chunks/1.bin", b"data")
        assert "STORAGE_MODE=shared_fs" in e.value.message
    finally:
        (
            s.app_env,
            s.storage_mode,
            s.chunks_dir,
            s.storage_shared_fs_dir,
            s.storage_require_shared_in_prod,
        ) = prev
