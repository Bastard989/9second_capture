import importlib.util
import json
import os
from pathlib import Path


def _load_run_local_agent_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_local_agent.py"
    spec = importlib.util.spec_from_file_location("run_local_agent_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cleanup_stale_agent_pid_removes_dead_process_file(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCAL_AGENT_STATE_DIR", str(state_dir))
    mod = _load_run_local_agent_module()
    pid_path = state_dir / "agent.pid"
    pid_path.write_text(json.dumps({"pid": 999999, "port": 8010}), encoding="utf-8")

    mod._cleanup_stale_agent_pid()

    assert not pid_path.exists()


def test_cleanup_stale_agent_pid_keeps_live_foreign_process_file(tmp_path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCAL_AGENT_STATE_DIR", str(state_dir))
    mod = _load_run_local_agent_module()
    pid_path = state_dir / "agent.pid"
    pid_path.write_text(json.dumps({"pid": os.getpid(), "port": 8010}), encoding="utf-8")

    mod._cleanup_stale_agent_pid()

    assert pid_path.exists()
