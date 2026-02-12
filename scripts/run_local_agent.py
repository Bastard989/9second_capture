"""
Локальный лаунчер для 9second_capture.

Что делает:
- выбирает свободный порт (с памятью последнего успешного)
- поднимает api-gateway на 127.0.0.1
- сохраняет выбранный порт в ./data/local_agent/state.json
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn


def _state_dir() -> Path:
    root = os.getenv("LOCAL_AGENT_STATE_DIR", "./data/local_agent")
    return Path(root).resolve()


def _state_file() -> Path:
    return _state_dir() / "state.json"


def _runtime_overrides_file() -> Path:
    return _state_dir() / "runtime_overrides.json"


def _apply_runtime_overrides() -> None:
    path = _runtime_overrides_file()
    if not path.exists():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(raw, dict):
        return
    allowed_keys = {
        "LLM_MODEL_ID",
        "LLM_ENABLED",
        "LLM_LIVE_ENABLED",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
    }
    for key in allowed_keys:
        value = raw.get(key)
        if value is None:
            continue
        os.environ[key] = str(value)


def _load_last_port() -> int | None:
    try:
        data = json.loads(_state_file().read_text(encoding="utf-8"))
        value = data.get("last_port")
        if isinstance(value, int) and value > 0:
            return value
    except Exception:
        return None
    return None


def _save_last_port(port: int) -> None:
    _state_dir().mkdir(parents=True, exist_ok=True)
    _state_file().write_text(json.dumps({"last_port": port}), encoding="utf-8")


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _pick_port(range_start: int, range_end: int, preferred: int | None = None) -> int:
    if preferred and preferred > 0:
        if _is_port_free(preferred):
            return preferred

    last = _load_last_port()
    if last and _is_port_free(last):
        return last

    for port in range(range_start, range_end + 1):
        if _is_port_free(port):
            return port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    preferred_port = None
    raw_port = os.getenv("API_PORT")
    if raw_port:
        try:
            preferred_port = int(raw_port)
        except ValueError:
            preferred_port = None

    port = _pick_port(8010, 8099, preferred=preferred_port)
    _save_last_port(port)

    os.environ.setdefault("API_HOST", "127.0.0.1")
    os.environ["API_PORT"] = str(port)
    os.environ.setdefault("AUTH_MODE", "none")
    os.environ.setdefault("QUEUE_MODE", "inline")
    os.environ.setdefault("POSTGRES_DSN", "sqlite:///./data/local_agent/agent.db")
    # Рекомендованный профиль для русской речи: баланс качества/скорости.
    os.environ.setdefault("WHISPER_MODEL_SIZE", "medium")
    os.environ.setdefault("WHISPER_COMPUTE_TYPE", "int8")
    os.environ.setdefault("WHISPER_LANGUAGE", "ru")
    os.environ.setdefault("WHISPER_BEAM_SIZE_LIVE", "3")
    os.environ.setdefault("WHISPER_BEAM_SIZE_FINAL", "6")
    os.environ.setdefault("WHISPER_VAD_FILTER", "true")
    os.environ.setdefault("WHISPER_WARMUP_ON_START", "true")
    _state_dir().mkdir(parents=True, exist_ok=True)
    _apply_runtime_overrides()

    url = f"http://127.0.0.1:{port}"
    print(f"[local-agent] UI: {url}")
    print("[local-agent] Press Ctrl+C to stop.")

    auto_open = os.getenv("LOCAL_AGENT_AUTO_OPEN", "true").lower() in {"1", "true", "yes"}
    if auto_open:
        threading.Timer(0.8, lambda: webbrowser.open(url, new=2)).start()

    # Локальный запуск из исходников: добавляем корень репозитория и src в PYTHONPATH.
    repo_root = Path(__file__).resolve().parents[1]
    for path in (repo_root, repo_root / "src"):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)

    try:
        from apps.api_gateway.main import app as fastapi_app
    except Exception:
        # В PyInstaller нужные пути лежат в sys._MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            sys.path.insert(0, meipass)
            sys.path.insert(0, os.path.join(meipass, "src"))
        from apps.api_gateway.main import app as fastapi_app

    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
