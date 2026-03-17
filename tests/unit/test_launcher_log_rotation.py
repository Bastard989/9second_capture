import importlib.util
import json
import os
from pathlib import Path


def _load_launcher_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "launcher.py"
    spec = importlib.util.spec_from_file_location("launcher_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_runtime_logs_archives_current_session_logs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    mod = _load_launcher_module()
    user_root = Path(tmp_path) / ".9second_capture"
    user_root.mkdir(parents=True, exist_ok=True)
    (user_root / "launcher.log").write_text("launcher history\n", encoding="utf-8")
    (user_root / "agent.log").write_text("agent history\n", encoding="utf-8")

    mod._prepare_runtime_logs()

    archive_dir = user_root / "logs" / "archive"
    launcher_archives = list(archive_dir.glob("launcher_*.log"))
    agent_archives = list(archive_dir.glob("agent_*.log"))
    assert len(launcher_archives) == 1
    assert len(agent_archives) == 1
    assert (user_root / "launcher.log").read_text(encoding="utf-8") == ""
    assert not (user_root / "agent.log").exists()


def test_prepare_runtime_logs_keeps_agent_log_when_agent_process_is_live(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    mod = _load_launcher_module()
    user_root = Path(tmp_path) / ".9second_capture"
    state_dir = user_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (user_root / "launcher.log").write_text("launcher history\n", encoding="utf-8")
    (user_root / "agent.log").write_text("active agent log\n", encoding="utf-8")
    (state_dir / "agent.pid").write_text(json.dumps({"pid": os.getpid(), "port": 8010}), encoding="utf-8")

    mod._prepare_runtime_logs()

    archive_dir = user_root / "logs" / "archive"
    launcher_archives = list(archive_dir.glob("launcher_*.log"))
    agent_archives = list(archive_dir.glob("agent_*.log"))
    assert len(launcher_archives) == 1
    assert len(agent_archives) == 0
    assert (user_root / "agent.log").read_text(encoding="utf-8") == "active agent log\n"
