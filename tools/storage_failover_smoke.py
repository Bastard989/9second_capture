"""
Storage failover smoke.

Проверяет базовый shared storage сценарий:
1) write blob из "реплики A"
2) read blob в отдельном python-процессе ("реплика B")
3) cleanup
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _py_env(shared_dir: str) -> dict[str, str]:
    env = dict(os.environ)
    root = _project_root()
    py_path = str(root / "src")
    if env.get("PYTHONPATH"):
        py_path = py_path + os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = py_path
    env["STORAGE_MODE"] = "shared_fs"
    env["STORAGE_SHARED_FS_DIR"] = shared_dir
    env.setdefault("APP_ENV", "dev")
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-dir", default="", help="Путь к shared storage mount")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="storage-smoke-") as tmp_dir:
        shared_dir = args.shared_dir or tmp_dir
        env = _py_env(shared_dir)

        cmd_write = (
            "from interview_analytics_agent.storage.blob import put_bytes; "
            "put_bytes('smoke/failover.bin', b'failover-ok'); print('write-ok')"
        )
        cmd_read = (
            "from interview_analytics_agent.storage.blob import get_bytes; "
            "v=get_bytes('smoke/failover.bin'); print(v.decode('utf-8'))"
        )
        cmd_delete = (
            "from interview_analytics_agent.storage.blob import delete; "
            "delete('smoke/failover.bin'); print('delete-ok')"
        )

        subprocess.check_call([sys.executable, "-c", cmd_write], env=env)
        out = subprocess.check_output([sys.executable, "-c", cmd_read], env=env, text=True).strip()
        if out != "failover-ok":
            raise RuntimeError(f"unexpected payload from shared storage: {out!r}")
        subprocess.check_call([sys.executable, "-c", cmd_delete], env=env)

    print("storage failover smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
