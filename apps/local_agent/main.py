"""
Локальный лаунчер для 9second_capture.

Что делает:
- выбирает свободный порт (с памятью последнего успешного)
- поднимает api-gateway на 127.0.0.1
- сохраняет выбранный порт в state-файл локального профиля агента
"""

from __future__ import annotations

import atexit
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


def _agent_root_dir() -> Path:
    explicit_root = str(os.getenv("LOCAL_AGENT_ROOT_DIR", "") or "").strip()
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()
    explicit_state = str(os.getenv("LOCAL_AGENT_STATE_DIR", "") or "").strip()
    if explicit_state:
        return Path(explicit_state).expanduser().resolve().parent
    return (Path.home() / ".9second_capture").resolve()


def _state_dir() -> Path:
    root = str(os.getenv("LOCAL_AGENT_STATE_DIR", "") or "").strip()
    if root:
        return Path(root).expanduser().resolve()
    return (_agent_root_dir() / "state").resolve()


def _state_file() -> Path:
    return _state_dir() / "state.json"


def _runtime_overrides_file() -> Path:
    return _state_dir() / "runtime_overrides.json"


def _agent_pid_file() -> Path:
    return _state_dir() / "agent.pid"


def _read_agent_pid_payload() -> dict:
    path = _agent_pid_file()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_agent_pid(port: int) -> None:
    try:
        payload = {"pid": os.getpid(), "port": int(port)}
        _state_dir().mkdir(parents=True, exist_ok=True)
        _agent_pid_file().write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        return


def _cleanup_agent_pid() -> None:
    path = _agent_pid_file()
    if not path.exists():
        return
    raw = _read_agent_pid_payload()
    file_pid = None
    if isinstance(raw, dict):
        try:
            file_pid = int(raw.get("pid"))
        except Exception:
            file_pid = None
    if file_pid and file_pid != os.getpid() and _pid_exists(file_pid):
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return


def _cleanup_stale_agent_pid() -> None:
    path = _agent_pid_file()
    if not path.exists():
        return
    raw = _read_agent_pid_payload()
    file_pid = None
    if isinstance(raw, dict):
        try:
            file_pid = int(raw.get("pid"))
        except Exception:
            file_pid = None
    if file_pid and _pid_exists(file_pid):
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return


def _pid_exists(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def _start_parent_watchdog() -> None:
    raw_parent = str(os.getenv("LOCAL_AGENT_PARENT_PID", "") or "").strip()
    if not raw_parent:
        return
    try:
        parent_pid = int(raw_parent)
    except Exception:
        return
    if parent_pid <= 1:
        return

    def _watch() -> None:
        while True:
            time.sleep(2.0)
            if _pid_exists(parent_pid):
                continue
            print(f"[local-agent] parent pid={parent_pid} exited, stopping agent")
            _cleanup_agent_pid()
            os._exit(0)

    threading.Thread(target=_watch, daemon=True).start()


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
        "LLM_PROVIDER",
        "LLM_API_BASE",
        "LLM_API_KEY",
        "LLM_MODEL_ID",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_MODEL_ID",
        "STT_PROVIDER",
        "STT_MODEL_ID",
        "GOOGLE_STT_SERVICE_ACCOUNT_JSON",
        "GOOGLE_STT_TOKEN_URI",
        "GOOGLE_STT_RECOGNIZE_URL",
        "GOOGLE_STT_TIMEOUT_SEC",
        "SALUTESPEECH_CLIENT_ID",
        "SALUTESPEECH_CLIENT_SECRET",
        "SALUTESPEECH_AUTH_URL",
        "SALUTESPEECH_RECOGNIZE_URL",
        "SALUTESPEECH_SCOPE",
        "SALUTESPEECH_TIMEOUT_SEC",
        "SALUTESPEECH_VERIFY_TLS",
        "LLM_ENABLED",
        "LLM_LIVE_ENABLED",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "EMBEDDING_API_BASE",
        "EMBEDDING_API_KEY",
        "RAG_EMBEDDING_PROVIDER",
        "RAG_VECTOR_ENABLED",
        "LLM_MAX_TOKENS",
        "LLM_REQUEST_TIMEOUT_SEC",
        "LLM_RETRIES",
        "LLM_RETRY_BACKOFF_MS",
        "LLM_TRANSCRIPT_CLEANUP_ENABLED",
        "WHISPER_MODEL_SIZE",
        "WHISPER_COMPUTE_TYPE",
        "WHISPER_LANGUAGE",
        "WHISPER_VAD_FILTER",
        "WHISPER_BEAM_SIZE_LIVE",
        "WHISPER_BEAM_SIZE_FINAL",
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


def _ensure_local_stt_dependencies(repo_root: Path) -> None:
    provider = (os.getenv("STT_PROVIDER", "whisper_local") or "").strip().lower()
    if provider != "whisper_local":
        return
    auto_install = (os.getenv("LOCAL_AGENT_AUTO_INSTALL_WHISPER_DEPS", "true") or "").strip().lower()
    if auto_install not in {"1", "true", "yes"}:
        return
    try:
        import av  # noqa: F401
        from faster_whisper import WhisperModel  # noqa: F401
        return
    except Exception:
        pass

    req = repo_root / "requirements.whisper.txt"
    if not req.exists():
        return
    print("[local-agent] whisper deps missing, installing requirements.whisper.txt ...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req)],
            check=True,
        )
        print("[local-agent] whisper deps installed")
    except Exception as err:
        print(f"[local-agent] whisper deps install failed: {err}")


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
    agent_root = _agent_root_dir()
    agent_root.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("API_HOST", "127.0.0.1")
    os.environ["API_PORT"] = str(port)
    os.environ.setdefault("AUTH_MODE", "none")
    os.environ.setdefault("QUEUE_MODE", "inline")
    os.environ.setdefault("POSTGRES_DSN", f"sqlite:///{(agent_root / 'agent.db').as_posix()}")
    os.environ.setdefault("RECORDS_DIR", str(agent_root / "records"))
    os.environ.setdefault("CHUNKS_DIR", str(agent_root / "chunks"))
    os.environ.setdefault("LLM_ENABLED", "true")
    os.environ.setdefault("LLM_LIVE_ENABLED", "false")
    os.environ.setdefault("LLM_PROVIDER", "openai_compat")
    os.environ.setdefault("OPENAI_API_BASE", "http://127.0.0.1:11434/v1")
    os.environ.setdefault("OPENAI_API_KEY", "ollama")
    os.environ.setdefault("LLM_API_BASE", os.environ.get("OPENAI_API_BASE", "http://127.0.0.1:11434/v1"))
    os.environ.setdefault("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "ollama"))
    os.environ.setdefault("LLM_MODEL_ID", "llama3.1:8b")
    os.environ.setdefault("EMBEDDING_PROVIDER", "auto")
    os.environ.setdefault("EMBEDDING_MODEL_ID", "nomic-embed-text")
    os.environ.setdefault("EMBEDDING_API_BASE", os.environ.get("LLM_API_BASE", ""))
    os.environ.setdefault("EMBEDDING_API_KEY", os.environ.get("LLM_API_KEY", ""))
    os.environ.setdefault("RAG_EMBEDDING_PROVIDER", "auto")
    os.environ.setdefault("RAG_VECTOR_ENABLED", "true")
    # 0 means "no hard limit" for local Ollama:
    # - LLM_MAX_TOKENS=0 => do not send max_tokens to provider
    # - LLM_REQUEST_TIMEOUT_SEC=0 => wait until provider responds
    os.environ.setdefault("LLM_MAX_TOKENS", "0")
    os.environ.setdefault("LLM_REQUEST_TIMEOUT_SEC", "0")
    os.environ.setdefault("LLM_RETRIES", "0")
    os.environ.setdefault("LLM_RETRY_BACKOFF_MS", "0")
    os.environ.setdefault("LLM_CLEANUP_PROBE_TIMEOUT_SEC", "2.0")
    # For local desktop mode prioritize predictable latency of transcript generation.
    os.environ.setdefault("LLM_TRANSCRIPT_CLEANUP_ENABLED", "false")
    os.environ.setdefault("BACKUP_AUDIO_FINAL_PASS_ENABLED", "true")
    # Faster default for local CPU runs; users can switch to medium/large in UI if needed.
    os.environ.setdefault("WHISPER_MODEL_SIZE", "small")
    os.environ.setdefault("WHISPER_COMPUTE_TYPE", "int8")
    os.environ.setdefault("WHISPER_LANGUAGE", "auto")
    os.environ.setdefault("WHISPER_BEAM_SIZE_LIVE", "4")
    os.environ.setdefault("WHISPER_BEAM_SIZE_FINAL", "5")
    os.environ.setdefault("WHISPER_VAD_FILTER", "true")
    os.environ.setdefault("WHISPER_ADAPTIVE_LOW_SIGNAL_ENABLED", "true")
    os.environ.setdefault("WHISPER_LOW_SIGNAL_FORCE_VAD_OFF", "true")
    os.environ.setdefault("WHISPER_LOW_SIGNAL_GAIN_BOOST", "2.2")
    os.environ.setdefault("WHISPER_LOW_SIGNAL_TRACK_LEVEL_THRESHOLD", "0.015")
    os.environ.setdefault("WHISPER_AUDIO_NOISE_GATE_DB", "-48")
    os.environ.setdefault("WHISPER_AUDIO_SPECTRAL_DENOISE_STRENGTH", "0.22")
    os.environ.setdefault("WHISPER_WARMUP_ON_START", "false")
    _state_dir().mkdir(parents=True, exist_ok=True)
    _cleanup_stale_agent_pid()

    url = f"http://127.0.0.1:{port}"
    print(f"[local-agent] UI: {url}")
    print("[local-agent] Press Ctrl+C to stop.")
    _write_agent_pid(port)
    atexit.register(_cleanup_agent_pid)
    _start_parent_watchdog()

    auto_open = os.getenv("LOCAL_AGENT_AUTO_OPEN", "true").lower() in {"1", "true", "yes"}
    if auto_open:
        threading.Timer(0.8, lambda: webbrowser.open(url, new=2)).start()

    # Локальный запуск из исходников: добавляем корень репозитория и src в PYTHONPATH.
    repo_root = Path(__file__).resolve().parents[2]
    for path in (repo_root, repo_root / "src"):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    _ensure_local_stt_dependencies(repo_root)
    _apply_runtime_overrides()

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
