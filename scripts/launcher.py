#!/usr/bin/env python3
from __future__ import annotations

import atexit
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import shutil
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


STATE_LOCK = threading.Lock()
INSTALL_STATE = "idle"  # idle|running|done|error
INSTALL_LOG: list[str] = []
INSTALL_MODE = "base"  # base|full
INSTALL_ERROR: str | None = None
APP_PROCESS: subprocess.Popen | None = None
APP_URL: str | None = None
LOG_FILE: Path | None = None
APP_LOG_FH = None
LAUNCHER_SERVER: ThreadingHTTPServer | None = None
SHUTDOWN_STARTED = False
SHUTDOWN_LOCK = threading.Lock()

OLLAMA_DEFAULT_MODEL = "llama3.1:8b"
OLLAMA_DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
LOG_ARCHIVE_KEEP = 12
DEFAULT_LLM_PROVIDER = "openai_compat"
DEFAULT_EMBEDDING_PROVIDER = "auto"
DEFAULT_STT_PROVIDER = "whisper_local"


def _normalize_llm_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in {"openai_compat", "openai", "anthropic", "gemini", "mock"}:
        return provider
    return DEFAULT_LLM_PROVIDER


def _normalize_embedding_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in {"auto", "openai_compat", "openai", "gemini", "hashing"}:
        return provider
    return DEFAULT_EMBEDDING_PROVIDER


def _normalize_stt_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in {"whisper_local", "mock", "google", "salutespeech"}:
        return provider
    return DEFAULT_STT_PROVIDER


def _default_llm_api_base(provider: str) -> str:
    normalized = _normalize_llm_provider(provider)
    if normalized == "openai":
        return "https://api.openai.com/v1"
    if normalized == "anthropic":
        return "https://api.anthropic.com/v1"
    if normalized == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta"
    if normalized == "openai_compat":
        return "http://127.0.0.1:11434/v1"
    return ""


def _default_embedding_api_base(provider: str, llm_provider: str) -> str:
    normalized = _normalize_embedding_provider(provider)
    if normalized == "openai":
        return "https://api.openai.com/v1"
    if normalized == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta"
    if normalized == "openai_compat":
        return _default_llm_api_base(llm_provider)
    return ""


def _provider_label(provider: str) -> str:
    mapping = {
        "openai_compat": "OpenAI-compatible",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "gemini": "Gemini",
        "mock": "Mock",
        "auto": "Auto",
        "hashing": "Hashing local",
        "whisper_local": "Whisper local",
        "google": "Google STT",
        "salutespeech": "SaluteSpeech",
    }
    normalized = str(provider or "").strip().lower()
    return mapping.get(normalized, normalized or "Unknown")


def _is_local_ollama_base(api_base: str) -> bool:
    try:
        parsed = urlparse(str(api_base or "").strip())
        host = str(parsed.hostname or "").strip().lower()
        port = int(parsed.port or 0)
    except Exception:
        return False
    return host in {"127.0.0.1", "localhost"} and port == 11434


def _bundle_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    bundle = base / "bundle"
    if bundle.exists():
        return bundle
    return Path(__file__).resolve().parents[1]


def _user_root() -> Path:
    return Path.home() / ".9second_capture"


def _mode_file() -> Path:
    return _user_root() / "install_mode.json"


def _runtime_overrides_path() -> Path:
    return _user_root() / "state" / "runtime_overrides.json"


def _launcher_pid_file() -> Path:
    return _user_root() / "launcher.pid"


def _agent_pid_file() -> Path:
    return _user_root() / "state" / "agent.pid"


def _logs_archive_dir() -> Path:
    return _user_root() / "logs" / "archive"


def _read_pid_file(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not raw:
        return None
    try:
        pid = int(raw)
    except Exception:
        return None
    return pid if pid > 1 else None


def _is_process_running(pid: int) -> bool:
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


def _terminate_pid(pid: int, *, timeout_sec: float = 6.0) -> None:
    if pid <= 1 or not _is_process_running(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        return
    deadline = time.time() + max(0.2, float(timeout_sec))
    while time.time() < deadline:
        if not _is_process_running(pid):
            return
        time.sleep(0.15)
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def _claim_single_launcher_instance() -> None:
    path = _launcher_pid_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    old_pid = _read_pid_file(path)
    current_pid = os.getpid()
    if old_pid and old_pid != current_pid and _is_process_running(old_pid):
        _log(f"[launcher] stopping previous launcher pid={old_pid}")
        _terminate_pid(old_pid, timeout_sec=4.0)
    try:
        path.write_text(str(current_pid), encoding="utf-8")
    except Exception:
        pass


def _clear_launcher_pid() -> None:
    path = _launcher_pid_file()
    pid = _read_pid_file(path)
    if pid and pid != os.getpid():
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _cleanup_stale_agent_pid(expected_pid: int | None = None) -> None:
    path = _agent_pid_file()
    if not path.exists():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    file_pid = None
    if isinstance(raw, dict):
        try:
            file_pid = int(raw.get("pid"))
        except Exception:
            file_pid = None
    keep_live_foreign = (
        file_pid is not None
        and file_pid > 1
        and file_pid != expected_pid
        and _is_process_running(file_pid)
    )
    if keep_live_foreign:
        return
    if file_pid and _is_process_running(file_pid):
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _is_agent_process_running() -> bool:
    path = _agent_pid_file()
    if not path.exists():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    pid = None
    if isinstance(raw, dict):
        try:
            pid = int(raw.get("pid"))
        except Exception:
            pid = None
    return bool(pid and pid > 1 and _is_process_running(pid))


def _archive_log_file(path: Path, *, label: str, keep: int = LOG_ARCHIVE_KEEP) -> Path | None:
    try:
        if not path.exists() or path.stat().st_size <= 0:
            return None
    except Exception:
        return None

    archive_dir = _logs_archive_dir()
    try:
        archive_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return None

    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = archive_dir / f"{label}_{stamp}.log"
    suffix = 1
    while target.exists():
        target = archive_dir / f"{label}_{stamp}_{suffix}.log"
        suffix += 1
    try:
        path.replace(target)
    except Exception:
        return None

    archived = sorted(archive_dir.glob(f"{label}_*.log"), key=lambda item: item.stat().st_mtime, reverse=True)
    for stale in archived[keep:]:
        try:
            stale.unlink(missing_ok=True)
        except Exception:
            pass
    return target


def _prepare_runtime_logs() -> None:
    root = _user_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        return

    global LOG_FILE
    launcher_log = root / "launcher.log"
    agent_log = root / "agent.log"

    _archive_log_file(launcher_log, label="launcher")
    if not _is_agent_process_running():
        _archive_log_file(agent_log, label="agent")

    LOG_FILE = launcher_log
    try:
        launcher_log.write_text("", encoding="utf-8")
    except Exception:
        pass


def _log(line: str) -> None:
    with STATE_LOCK:
        INSTALL_LOG.append(line.rstrip())
        if len(INSTALL_LOG) > 4000:
            del INSTALL_LOG[:500]
    try:
        root = _user_root()
        root.mkdir(parents=True, exist_ok=True)
        global LOG_FILE
        if LOG_FILE is None:
            LOG_FILE = root / "launcher.log"
        LOG_FILE.write_text("\n".join(INSTALL_LOG[-500:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def _write_url_file(url: str) -> None:
    try:
        root = _user_root()
        root.mkdir(parents=True, exist_ok=True)
        (root / "launcher.url").write_text(url + "\n", encoding="utf-8")
    except Exception:
        pass


def _launcher_ui_index() -> Path:
    bundle_root = _bundle_root()
    candidate = bundle_root / "launcher_ui" / "index.html"
    if candidate.exists():
        return candidate
    fallback = bundle_root / "apps" / "launcher" / "ui" / "index.html"
    if fallback.exists():
        return fallback
    return candidate


def _set_state(state: str, error: str | None = None) -> None:
    global INSTALL_STATE, INSTALL_ERROR
    with STATE_LOCK:
        INSTALL_STATE = state
        INSTALL_ERROR = error


def _save_install_mode(mode: str) -> None:
    if mode not in {"base", "full"}:
        return
    try:
        root = _user_root()
        root.mkdir(parents=True, exist_ok=True)
        _mode_file().write_text(json.dumps({"mode": mode}), encoding="utf-8")
    except Exception:
        pass


def _load_install_mode() -> str:
    try:
        raw = json.loads(_mode_file().read_text(encoding="utf-8"))
        mode = str(raw.get("mode", "")).strip().lower()
        if mode in {"base", "full"}:
            return mode
    except Exception:
        pass
    return "base"


def _venv_paths(root: Path) -> tuple[Path, Path]:
    venv_dir = root / "venv"
    python_bin = venv_dir / "bin" / "python"
    return venv_dir, python_bin


def _resolve_system_python() -> Path:
    if not getattr(sys, "frozen", False):
        return Path(sys.executable)
    candidates = [
        os.environ.get("PYTHON3_PATH"),
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for candidate in candidates:
        if candidate:
            return Path(candidate)
    raise RuntimeError("python3 не найден. Установи Python 3 и повтори попытку.")


def _run_and_log(cmd: list[str], env: dict | None = None) -> None:
    _log("[cmd] " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    assert proc.stdout
    for line in proc.stdout:
        _log(line)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"command failed: {code}")


def _ensure_venv(root: Path) -> Path:
    venv_dir, python_bin = _venv_paths(root)
    if python_bin.exists():
        return python_bin
    _log("[setup] create venv...")
    system_python = _resolve_system_python()
    _run_and_log([str(system_python), "-m", "venv", str(venv_dir)])
    return python_bin


def _pip_install(python_bin: Path, req_path: Path) -> None:
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_CACHE_DIR"] = "1"
    if req_path.is_dir():
        # PyInstaller on macOS может упаковать файл как папку с одноимённым файлом внутри.
        candidate = req_path / req_path.name
        if candidate.exists():
            req_path = candidate
    cmd = [str(python_bin), "-m", "pip", "install", "-r", str(req_path)]
    try:
        _run_and_log(cmd, env=env)
    except RuntimeError:
        _log("[install] pip не найден, пробуем ensurepip...")
        _run_and_log([str(python_bin), "-m", "ensurepip", "--upgrade"], env=env)
        _run_and_log(cmd, env=env)


def _venv_has_whisper(python_bin: Path) -> bool:
    try:
        code = subprocess.run(
            [str(python_bin), "-c", "import faster_whisper, av"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        return code == 0
    except Exception:
        return False


def _ollama_bin() -> str | None:
    return shutil.which("ollama")


def _ollama_running(timeout_sec: float = 1.2) -> bool:
    req = Request("http://127.0.0.1:11434/api/tags", method="GET")
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            return 200 <= int(resp.status) < 300
    except Exception:
        return False


def _ollama_models(timeout_sec: float = 2.4) -> list[str]:
    bin_path = _ollama_bin()
    if not bin_path:
        return []
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    try:
        proc = subprocess.run(
            [bin_path, "list"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=timeout_sec,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    rows = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not rows:
        return []
    models: list[str] = []
    for line in rows[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0].strip())
    dedup: list[str] = []
    seen: set[str] = set()
    for model in models:
        if not model or model in seen:
            continue
        seen.add(model)
        dedup.append(model)
    return dedup


def _split_model_id(model_id: str) -> tuple[str, str]:
    value = str(model_id or "").strip().lower()
    if not value:
        return "", ""
    if ":" not in value:
        return value, "latest"
    name, tag = value.split(":", 1)
    return name.strip(), tag.strip()


def _is_compatible_model(target_model: str, candidate_model: str) -> bool:
    target_name, target_tag = _split_model_id(target_model)
    candidate_name, candidate_tag = _split_model_id(candidate_model)
    if not target_name or not candidate_name:
        return False
    tag_match = (
        target_tag == candidate_tag
        or not target_tag
        or not candidate_tag
        or candidate_tag.startswith(target_tag)
        or target_tag.startswith(candidate_tag)
    )
    if not tag_match:
        return False
    if target_name == candidate_name:
        return True
    aliases = {
        "llama3.1": {"llama3"},
        "llama3": {"llama3.1"},
    }
    return candidate_name in aliases.get(target_name, set())


def _resolve_model_match(target_model: str, installed_models: list[str]) -> tuple[bool, bool, str]:
    target = str(target_model or "").strip()
    if not target:
        return False, False, ""
    clean_models = [str(model).strip() for model in installed_models if str(model).strip()]
    exact_lookup = {model.lower(): model for model in clean_models}
    exact = exact_lookup.get(target.lower())
    if exact:
        return True, True, exact
    for model in clean_models:
        if _is_compatible_model(target, model):
            return True, False, model
    return False, False, ""


def _load_runtime_overrides() -> dict[str, str]:
    path = _runtime_overrides_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items() if str(k).strip()}
    except Exception:
        return {}
    return {}


def _delete_runtime_override(key: str) -> None:
    try:
        path = _runtime_overrides_path()
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return
        if key in raw:
            raw.pop(key, None)
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _current_provider_config(runtime: dict[str, str] | None = None) -> dict[str, str]:
    payload = runtime or _load_runtime_overrides()
    llm_provider = _normalize_llm_provider(payload.get("LLM_PROVIDER") or DEFAULT_LLM_PROVIDER)
    llm_api_base = str(
        payload.get("LLM_API_BASE") or payload.get("OPENAI_API_BASE") or _default_llm_api_base(llm_provider)
    ).strip()
    llm_api_key = str(payload.get("LLM_API_KEY") or payload.get("OPENAI_API_KEY") or "").strip()
    embedding_provider = _normalize_embedding_provider(
        payload.get("EMBEDDING_PROVIDER") or payload.get("RAG_EMBEDDING_PROVIDER") or DEFAULT_EMBEDDING_PROVIDER
    )
    embedding_api_base = str(
        payload.get("EMBEDDING_API_BASE")
        or _default_embedding_api_base(embedding_provider, llm_provider)
        or (llm_api_base if embedding_provider in {"auto", "openai_compat"} else "")
    ).strip()
    embedding_api_key = str(payload.get("EMBEDDING_API_KEY") or llm_api_key or "").strip()
    stt_provider = _normalize_stt_provider(payload.get("STT_PROVIDER") or DEFAULT_STT_PROVIDER)
    llm_model_id = str(payload.get("LLM_MODEL_ID") or OLLAMA_DEFAULT_MODEL).strip()
    embedding_model_id = str(payload.get("EMBEDDING_MODEL_ID") or OLLAMA_DEFAULT_EMBEDDING_MODEL).strip()
    stt_model_id = str(
        payload.get("STT_MODEL_ID")
        or payload.get("WHISPER_MODEL_SIZE")
        or ("small" if stt_provider == "whisper_local" else "")
    ).strip()
    google_stt_service_account_json = str(payload.get("GOOGLE_STT_SERVICE_ACCOUNT_JSON") or "").strip()
    google_stt_recognize_url = str(
        payload.get("GOOGLE_STT_RECOGNIZE_URL") or "https://speech.googleapis.com/v1/speech:recognize"
    ).strip()
    salutespeech_client_id = str(payload.get("SALUTESPEECH_CLIENT_ID") or "").strip()
    salutespeech_client_secret = str(payload.get("SALUTESPEECH_CLIENT_SECRET") or "").strip()
    salutespeech_auth_url = str(
        payload.get("SALUTESPEECH_AUTH_URL") or "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    ).strip()
    salutespeech_recognize_url = str(
        payload.get("SALUTESPEECH_RECOGNIZE_URL") or "https://smartspeech.sber.ru/rest/v1/speech:recognize"
    ).strip()
    salutespeech_scope = str(payload.get("SALUTESPEECH_SCOPE") or "SALUTE_SPEECH_PERS").strip()
    return {
        "llm_provider": llm_provider,
        "llm_api_base": llm_api_base,
        "llm_api_key": llm_api_key,
        "llm_model_id": llm_model_id,
        "embedding_provider": embedding_provider,
        "embedding_api_base": embedding_api_base,
        "embedding_api_key": embedding_api_key,
        "embedding_model_id": embedding_model_id,
        "stt_provider": stt_provider,
        "stt_model_id": stt_model_id,
        "google_stt_service_account_json": google_stt_service_account_json,
        "google_stt_recognize_url": google_stt_recognize_url,
        "salutespeech_client_id": salutespeech_client_id,
        "salutespeech_client_secret": salutespeech_client_secret,
        "salutespeech_auth_url": salutespeech_auth_url,
        "salutespeech_recognize_url": salutespeech_recognize_url,
        "salutespeech_scope": salutespeech_scope,
    }


def _save_provider_config(config: dict[str, str]) -> None:
    llm_provider = _normalize_llm_provider(config.get("llm_provider"))
    llm_api_base = str(config.get("llm_api_base") or _default_llm_api_base(llm_provider)).strip()
    llm_api_key = str(config.get("llm_api_key") or "").strip()
    llm_model_id = str(config.get("llm_model_id") or OLLAMA_DEFAULT_MODEL).strip()
    embedding_provider = _normalize_embedding_provider(config.get("embedding_provider"))
    embedding_api_base = str(
        config.get("embedding_api_base")
        or _default_embedding_api_base(embedding_provider, llm_provider)
        or (llm_api_base if embedding_provider in {"auto", "openai_compat"} else "")
    ).strip()
    embedding_api_key = str(config.get("embedding_api_key") or "").strip()
    embedding_model_id = str(config.get("embedding_model_id") or OLLAMA_DEFAULT_EMBEDDING_MODEL).strip()
    stt_provider = _normalize_stt_provider(config.get("stt_provider"))
    stt_model_id = str(config.get("stt_model_id") or "").strip()
    google_stt_service_account_json = str(config.get("google_stt_service_account_json") or "").strip()
    google_stt_recognize_url = str(
        config.get("google_stt_recognize_url") or "https://speech.googleapis.com/v1/speech:recognize"
    ).strip()
    salutespeech_client_id = str(config.get("salutespeech_client_id") or "").strip()
    salutespeech_client_secret = str(config.get("salutespeech_client_secret") or "").strip()
    salutespeech_auth_url = str(
        config.get("salutespeech_auth_url") or "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    ).strip()
    salutespeech_recognize_url = str(
        config.get("salutespeech_recognize_url") or "https://smartspeech.sber.ru/rest/v1/speech:recognize"
    ).strip()
    salutespeech_scope = str(config.get("salutespeech_scope") or "SALUTE_SPEECH_PERS").strip()

    _save_runtime_override("LLM_PROVIDER", llm_provider)
    _save_runtime_override("LLM_API_BASE", llm_api_base)
    if llm_api_key:
        _save_runtime_override("LLM_API_KEY", llm_api_key)
    else:
        _delete_runtime_override("LLM_API_KEY")
    _save_runtime_override("LLM_MODEL_ID", llm_model_id)
    _save_runtime_override("LLM_ENABLED", "true")
    _save_runtime_override("LLM_LIVE_ENABLED", "false")

    if llm_provider in {"openai_compat", "openai"}:
        _save_runtime_override("OPENAI_API_BASE", llm_api_base)
        if llm_api_key:
            _save_runtime_override("OPENAI_API_KEY", llm_api_key)
        else:
            _delete_runtime_override("OPENAI_API_KEY")
    else:
        _delete_runtime_override("OPENAI_API_BASE")
        _delete_runtime_override("OPENAI_API_KEY")

    _save_runtime_override("EMBEDDING_PROVIDER", embedding_provider)
    _save_runtime_override("EMBEDDING_API_BASE", embedding_api_base)
    if embedding_api_key:
        _save_runtime_override("EMBEDDING_API_KEY", embedding_api_key)
    else:
        _delete_runtime_override("EMBEDDING_API_KEY")
    _save_runtime_override("EMBEDDING_MODEL_ID", embedding_model_id)
    _save_runtime_override("RAG_VECTOR_ENABLED", "true")
    _save_runtime_override("RAG_EMBEDDING_PROVIDER", "hashing" if embedding_provider == "hashing" else "openai_compat")

    _save_runtime_override("STT_PROVIDER", stt_provider)
    if stt_provider == "whisper_local":
        effective_stt_model = stt_model_id or "small"
        _save_runtime_override("WHISPER_MODEL_SIZE", effective_stt_model)
        _save_runtime_override("STT_MODEL_ID", effective_stt_model)
    else:
        _delete_runtime_override("WHISPER_MODEL_SIZE")
        if stt_model_id:
            _save_runtime_override("STT_MODEL_ID", stt_model_id)
        else:
            _delete_runtime_override("STT_MODEL_ID")

    if stt_provider == "google":
        if google_stt_service_account_json:
            _save_runtime_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON", google_stt_service_account_json)
        else:
            _delete_runtime_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON")
        _save_runtime_override("GOOGLE_STT_RECOGNIZE_URL", google_stt_recognize_url)
    else:
        _delete_runtime_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON")
        _delete_runtime_override("GOOGLE_STT_RECOGNIZE_URL")

    if stt_provider == "salutespeech":
        if salutespeech_client_id:
            _save_runtime_override("SALUTESPEECH_CLIENT_ID", salutespeech_client_id)
        else:
            _delete_runtime_override("SALUTESPEECH_CLIENT_ID")
        if salutespeech_client_secret:
            _save_runtime_override("SALUTESPEECH_CLIENT_SECRET", salutespeech_client_secret)
        else:
            _delete_runtime_override("SALUTESPEECH_CLIENT_SECRET")
        _save_runtime_override("SALUTESPEECH_AUTH_URL", salutespeech_auth_url)
        _save_runtime_override("SALUTESPEECH_RECOGNIZE_URL", salutespeech_recognize_url)
        _save_runtime_override("SALUTESPEECH_SCOPE", salutespeech_scope)
    else:
        _delete_runtime_override("SALUTESPEECH_CLIENT_ID")
        _delete_runtime_override("SALUTESPEECH_CLIENT_SECRET")
        _delete_runtime_override("SALUTESPEECH_AUTH_URL")
        _delete_runtime_override("SALUTESPEECH_RECOGNIZE_URL")
        _delete_runtime_override("SALUTESPEECH_SCOPE")


def _public_provider_config() -> dict[str, str | bool]:
    config = _current_provider_config()
    return {
        "llm_provider": config["llm_provider"],
        "llm_api_base": config["llm_api_base"],
        "llm_api_key_set": bool(config["llm_api_key"]),
        "llm_model_id": config["llm_model_id"],
        "embedding_provider": config["embedding_provider"],
        "embedding_api_base": config["embedding_api_base"],
        "embedding_api_key_set": bool(config["embedding_api_key"]),
        "embedding_model_id": config["embedding_model_id"],
        "stt_provider": config["stt_provider"],
        "stt_model_id": config["stt_model_id"],
        "google_stt_service_account_set": bool(config["google_stt_service_account_json"]),
        "google_stt_recognize_url": config["google_stt_recognize_url"],
        "salutespeech_client_id": config["salutespeech_client_id"],
        "salutespeech_client_secret_set": bool(config["salutespeech_client_secret"]),
        "salutespeech_auth_url": config["salutespeech_auth_url"],
        "salutespeech_recognize_url": config["salutespeech_recognize_url"],
        "salutespeech_scope": config["salutespeech_scope"],
    }


def _open_ollama_app() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(["open", "-a", "Ollama"], check=False)
        return True
    except Exception:
        return False


def _wait_ollama_ready(timeout_sec: float = 24.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _ollama_running(timeout_sec=1.2):
            return True
        time.sleep(0.6)
    return False


def _pull_ollama_model(model_id: str) -> bool:
    model = str(model_id or "").strip()
    if not model:
        model = OLLAMA_DEFAULT_MODEL
    bin_path = _ollama_bin()
    if not bin_path:
        _log("[llm] ollama binary not found")
        return False
    _log(f"[llm] pulling model: {model}")
    try:
        _run_and_log([bin_path, "pull", model], env=os.environ.copy())
        return True
    except Exception as e:
        _log(f"[llm] model pull failed: {e}")
        return False


def _looks_like_google_placeholder(raw_json: str) -> bool:
    value = str(raw_json or "").strip().lower()
    if not value:
        return True
    return "example.iam.gserviceaccount.com" in value or "<insert_google_service_account_json_here>" in value


def _looks_like_salute_placeholder(*, client_id: str, client_secret: str) -> bool:
    left = str(client_id or "").strip().lower()
    right = str(client_secret or "").strip().lower()
    markers = {
        "demo-client",
        "demo-secret",
        "<insert_salutespeech_client_id_here>",
        "<insert_salutespeech_client_secret_here>",
    }
    return (
        not left
        or not right
        or left in markers
        or right in markers
        or "insert_" in left
        or "insert_" in right
        or left.startswith("example")
        or right.startswith("example")
    )


def _preflight_snapshot() -> dict:
    root = _user_root()
    _venv_dir, python_bin = _venv_paths(root)
    venv_ready = python_bin.exists()
    whisper_ready = bool(venv_ready and _venv_has_whisper(python_bin))
    install_mode_saved = _load_install_mode()
    runtime = _load_runtime_overrides()
    config = _current_provider_config(runtime)
    llm_local = config["llm_provider"] == "openai_compat" and _is_local_ollama_base(config["llm_api_base"])
    embedding_local = config["embedding_provider"] in {"auto", "openai_compat"} and _is_local_ollama_base(
        config["embedding_api_base"] or config["llm_api_base"]
    )
    ollama_cli = _ollama_bin() is not None if (llm_local or embedding_local) else False
    ollama_ready = _ollama_running(timeout_sec=1.4) if ollama_cli else False
    models = _ollama_models(timeout_sec=2.5) if ollama_cli else []
    model_present, model_exact, model_matched = _resolve_model_match(config["llm_model_id"], models)
    emb_present, emb_exact, emb_matched = _resolve_model_match(config["embedding_model_id"], models)
    stt_ready = False
    stt_value = ""
    if config["stt_provider"] == "whisper_local":
        stt_ready = whisper_ready
        stt_value = "Whisper доступен" if whisper_ready else "Whisper не установлен"
    elif config["stt_provider"] == "mock":
        stt_ready = True
        stt_value = "Mock режим для UI и тестов"
    elif config["stt_provider"] == "google":
        stt_ready = bool(config["google_stt_service_account_json"]) and not _looks_like_google_placeholder(
            config["google_stt_service_account_json"]
        )
        if not config["google_stt_service_account_json"]:
            stt_value = "Нужен service account JSON"
        elif not stt_ready:
            stt_value = "Сейчас сохранен пример JSON, нужен реальный service account"
        else:
            stt_value = config["google_stt_recognize_url"]
    elif config["stt_provider"] == "salutespeech":
        stt_ready = bool(
            config["salutespeech_client_id"]
            and config["salutespeech_client_secret"]
            and config["salutespeech_auth_url"]
            and config["salutespeech_recognize_url"]
            and not _looks_like_salute_placeholder(
                client_id=config["salutespeech_client_id"],
                client_secret=config["salutespeech_client_secret"],
            )
        )
        if not (config["salutespeech_client_id"] and config["salutespeech_client_secret"]):
            stt_value = "Нужны Client ID / Client Secret"
        elif not stt_ready:
            stt_value = "Сейчас сохранены примерные данные, нужны реальные Client ID / Client Secret"
        else:
            stt_value = config["salutespeech_recognize_url"]
    return {
        "venv_ready": venv_ready,
        "whisper_ready": whisper_ready,
        "install_mode_saved": install_mode_saved,
        "llm_provider": config["llm_provider"],
        "llm_provider_label": _provider_label(config["llm_provider"]),
        "llm_api_base": config["llm_api_base"],
        "llm_api_key_set": bool(config["llm_api_key"]),
        "llm_provider_local": llm_local,
        "llm_provider_cli_found": ollama_cli,
        "llm_provider_ready": ollama_ready if llm_local else bool(config["llm_api_base"]),
        "llm_model_default": config["llm_model_id"],
        "llm_model_present": model_present if llm_local else bool(config["llm_model_id"]),
        "llm_model_exact": model_exact if llm_local else False,
        "llm_model_matched": model_matched if llm_local else "",
        "embedding_provider": config["embedding_provider"],
        "embedding_provider_label": _provider_label(config["embedding_provider"]),
        "embedding_api_base": config["embedding_api_base"],
        "embedding_api_key_set": bool(config["embedding_api_key"]),
        "embedding_provider_local": embedding_local,
        "embedding_provider_ready": ollama_ready if embedding_local else bool(config["embedding_api_base"]) or config["embedding_provider"] == "hashing",
        "embedding_model_default": config["embedding_model_id"],
        "embedding_model_present": emb_present if embedding_local else bool(config["embedding_model_id"]),
        "embedding_model_exact": emb_exact if embedding_local else False,
        "embedding_model_matched": emb_matched if embedding_local else "",
        "stt_provider": config["stt_provider"],
        "stt_provider_label": _provider_label(config["stt_provider"]),
        "stt_model_id": config["stt_model_id"],
        "stt_provider_ready": stt_ready,
        "stt_provider_value": stt_value,
        "provider_models": models,
    }


def _effective_install_mode(python_bin: Path) -> str:
    mode = _load_install_mode()
    if mode == "full":
        return "full"
    if _venv_has_whisper(python_bin):
        return "full"
    return "base"


def _install(mode: str) -> None:
    global INSTALL_MODE
    try:
        _set_state("running")
        INSTALL_MODE = mode
        root = _user_root()
        root.mkdir(parents=True, exist_ok=True)

        python_bin = _ensure_venv(root)
        bundle = _bundle_root()
        base_req = bundle / "requirements.app.txt"
        whisper_req = bundle / "requirements.whisper.txt"

        _log("[install] base requirements...")
        _pip_install(python_bin, base_req)

        if mode == "full":
            _log("[install] whisper requirements...")
            _pip_install(python_bin, whisper_req)

        INSTALL_MODE = mode
        _save_install_mode(mode)
        _set_state("done")
    except Exception as e:
        _log(traceback.format_exc())
        _set_state("error", str(e))


def _fix_all(config: dict[str, str] | None = None) -> None:
    effective = _current_provider_config()
    if config:
        effective.update({k: str(v) for k, v in config.items() if v is not None})
    effective["llm_provider"] = _normalize_llm_provider(effective.get("llm_provider"))
    effective["embedding_provider"] = _normalize_embedding_provider(effective.get("embedding_provider"))
    effective["stt_provider"] = _normalize_stt_provider(effective.get("stt_provider"))
    effective["llm_api_base"] = str(
        effective.get("llm_api_base") or _default_llm_api_base(effective["llm_provider"])
    ).strip()
    effective["embedding_api_base"] = str(
        effective.get("embedding_api_base")
        or _default_embedding_api_base(effective["embedding_provider"], effective["llm_provider"])
        or (effective["llm_api_base"] if effective["embedding_provider"] in {"auto", "openai_compat"} else "")
    ).strip()
    effective["llm_model_id"] = str(effective.get("llm_model_id") or OLLAMA_DEFAULT_MODEL).strip()
    effective["embedding_model_id"] = str(
        effective.get("embedding_model_id") or OLLAMA_DEFAULT_EMBEDDING_MODEL
    ).strip()
    use_local_ollama = (
        effective["llm_provider"] == "openai_compat" and _is_local_ollama_base(effective["llm_api_base"])
    ) or (
        effective["embedding_provider"] in {"auto", "openai_compat"}
        and _is_local_ollama_base(effective["embedding_api_base"] or effective["llm_api_base"])
    )
    try:
        _set_state("running")
        _log("[wizard] fix-all started")
        install_mode = "full" if effective["stt_provider"] == "whisper_local" else "base"
        _install(install_mode)
        with STATE_LOCK:
            if INSTALL_STATE == "error":
                return

        if use_local_ollama:
            snap = _preflight_snapshot()
            if not snap.get("llm_provider_cli_found"):
                raise RuntimeError("Локальный провайдер не найден. Установите Ollama и повторите.")
            if not snap.get("llm_provider_ready"):
                _log("[wizard] starting local provider app...")
                _open_ollama_app()
                if not _wait_ollama_ready(timeout_sec=35.0):
                    raise RuntimeError("Локальный провайдер не запустился на порту 11434")

            snap = _preflight_snapshot()
            models = [str(model) for model in (snap.get("provider_models") or [])]
            model_present, _model_exact, model_matched = _resolve_model_match(effective["llm_model_id"], models)
            emb_present, _emb_exact, emb_matched = _resolve_model_match(effective["embedding_model_id"], models)
            active_model = effective["llm_model_id"]
            active_embedding_model = effective["embedding_model_id"]
            if model_present:
                if model_matched and model_matched.lower() != effective["llm_model_id"].lower():
                    _log(
                        f"[wizard] compatible LLM model found: {model_matched} "
                        f"(requested {effective['llm_model_id']})"
                    )
                    active_model = model_matched
            else:
                if not _pull_ollama_model(effective["llm_model_id"]):
                    raise RuntimeError(f"Не удалось скачать LLM модель {effective['llm_model_id']}")
            if emb_present:
                if emb_matched and emb_matched.lower() != effective["embedding_model_id"].lower():
                    _log(
                        f"[wizard] compatible embedding model found: {emb_matched} "
                        f"(requested {effective['embedding_model_id']})"
                    )
                    active_embedding_model = emb_matched
            elif effective["embedding_provider"] != "hashing":
                if not _pull_ollama_model(effective["embedding_model_id"]):
                    raise RuntimeError(
                        f"Не удалось скачать embeddings модель {effective['embedding_model_id']}"
                    )
            effective["llm_model_id"] = active_model
            effective["embedding_model_id"] = active_embedding_model

        _save_provider_config(effective)
        _set_state("done")
        _log("[wizard] fix-all completed")
    except Exception as e:
        _log(traceback.format_exc())
        _set_state("error", str(e))


def _save_runtime_override(key: str, value: str) -> None:
    try:
        root = _user_root()
        root.mkdir(parents=True, exist_ok=True)
        path = _runtime_overrides_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, str] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                payload = {str(k): str(v) for k, v in raw.items() if str(k).strip()}
        payload[str(key)] = str(value)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _pull_model_task(model_id: str, override_key: str = "LLM_MODEL_ID") -> None:
    default_model = OLLAMA_DEFAULT_EMBEDDING_MODEL if override_key == "EMBEDDING_MODEL_ID" else OLLAMA_DEFAULT_MODEL
    model = str(model_id or "").strip() or default_model
    try:
        _set_state("running")
        if not _pull_ollama_model(model):
            raise RuntimeError(f"Не удалось скачать модель {model}")
        _save_runtime_override(override_key, model)
        _set_state("done")
    except Exception as e:
        _log(traceback.format_exc())
        _set_state("error", str(e))


def _pick_port() -> int:
    for port in range(8010, 8099):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _pick_launcher_port() -> int:
    env_port = os.environ.get("LAUNCHER_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    for port in range(8799, 8899):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_app() -> str:
    global APP_PROCESS, APP_URL, INSTALL_MODE
    if APP_PROCESS and APP_PROCESS.poll() is None and APP_URL:
        try:
            _wait_app_ready(APP_URL, timeout_sec=6.0)
            return APP_URL
        except Exception:
            _log("[start] existing agent is not ready, restarting...")
            _stop_app()

    bundle = _bundle_root()
    root = _user_root()
    python_bin = _venv_paths(root)[1]
    if not python_bin.exists():
        raise RuntimeError("venv не установлен")
    INSTALL_MODE = _effective_install_mode(python_bin)
    _save_install_mode(INSTALL_MODE)

    port = _pick_port()
    APP_URL = f"http://127.0.0.1:{port}"
    provider_config = _current_provider_config()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{bundle}:{bundle / 'src'}"
    env["API_HOST"] = "127.0.0.1"
    env["API_PORT"] = str(port)
    env["AUTH_MODE"] = "none"
    env["QUEUE_MODE"] = "inline"
    # Не затираем пользовательскую конфигурацию LLM:
    # по умолчанию включаем post-meeting LLM, live-cleanup оставляем выключенным.
    env.setdefault("LLM_ENABLED", "true")
    env.setdefault("LLM_LIVE_ENABLED", "false")
    env.setdefault("LLM_PROVIDER", provider_config["llm_provider"])
    env.setdefault("LLM_API_BASE", provider_config["llm_api_base"])
    if provider_config["llm_api_key"]:
        env.setdefault("LLM_API_KEY", provider_config["llm_api_key"])
    env.setdefault("LLM_MODEL_ID", provider_config["llm_model_id"])
    if provider_config["llm_provider"] in {"openai_compat", "openai"}:
        env.setdefault("OPENAI_API_BASE", provider_config["llm_api_base"])
        if provider_config["llm_api_key"]:
            env.setdefault("OPENAI_API_KEY", provider_config["llm_api_key"])
    env.setdefault("EMBEDDING_PROVIDER", provider_config["embedding_provider"])
    if provider_config["embedding_api_base"]:
        env.setdefault("EMBEDDING_API_BASE", provider_config["embedding_api_base"])
    if provider_config["embedding_api_key"]:
        env.setdefault("EMBEDDING_API_KEY", provider_config["embedding_api_key"])
    env.setdefault("EMBEDDING_MODEL_ID", provider_config["embedding_model_id"])
    env.setdefault("RAG_EMBEDDING_PROVIDER", "hashing" if provider_config["embedding_provider"] == "hashing" else "auto")
    env.setdefault("RAG_VECTOR_ENABLED", "true")
    # 0 means "no hard limit" for local Ollama:
    # - LLM_MAX_TOKENS=0 => do not send max_tokens to provider
    # - LLM_REQUEST_TIMEOUT_SEC=0 => wait until provider responds
    env.setdefault("LLM_MAX_TOKENS", "0")
    env.setdefault("LLM_REQUEST_TIMEOUT_SEC", "0")
    env.setdefault("LLM_RETRIES", "0")
    env.setdefault("LLM_RETRY_BACKOFF_MS", "0")
    env.setdefault("LLM_CLEANUP_PROBE_TIMEOUT_SEC", "2.0")
    # Keep transcript path deterministic and avoid LLM retry tail-latency.
    env.setdefault("LLM_TRANSCRIPT_CLEANUP_ENABLED", "false")
    env.setdefault("BACKUP_AUDIO_RECOVERY_ENABLED", "true")
    env["POSTGRES_DSN"] = f"sqlite:///{(root / 'agent.db').as_posix()}"
    env["RECORDS_DIR"] = str(root / "records")
    env["CHUNKS_DIR"] = str(root / "chunks")
    env["LOCAL_AGENT_STATE_DIR"] = str(root / "state")
    env["STT_PROVIDER"] = provider_config["stt_provider"] if INSTALL_MODE == "full" else "mock"
    if INSTALL_MODE == "full":
        env.setdefault("STT_MODEL_ID", provider_config["stt_model_id"] or "small")
        if provider_config["stt_provider"] == "whisper_local":
            whisper_model = provider_config["stt_model_id"] or "small"
            env.setdefault("WHISPER_MODEL_SIZE", whisper_model)
            env.setdefault("WHISPER_COMPUTE_TYPE", "int8")
            env.setdefault("WHISPER_LANGUAGE", "auto")
            env.setdefault("WHISPER_VAD_FILTER", "true")
            env.setdefault("WHISPER_BEAM_SIZE_LIVE", "4")
            env.setdefault("WHISPER_BEAM_SIZE_FINAL", "5")
            env.setdefault("WHISPER_ADAPTIVE_LOW_SIGNAL_ENABLED", "true")
            env.setdefault("WHISPER_LOW_SIGNAL_FORCE_VAD_OFF", "true")
            env.setdefault("WHISPER_LOW_SIGNAL_GAIN_BOOST", "2.2")
            env.setdefault("WHISPER_LOW_SIGNAL_TRACK_LEVEL_THRESHOLD", "0.015")
            env.setdefault("WHISPER_WARMUP_ON_START", "false")
        if provider_config["stt_provider"] == "google":
            if provider_config["google_stt_service_account_json"]:
                env.setdefault(
                    "GOOGLE_STT_SERVICE_ACCOUNT_JSON",
                    provider_config["google_stt_service_account_json"],
                )
            env.setdefault("GOOGLE_STT_RECOGNIZE_URL", provider_config["google_stt_recognize_url"])
        if provider_config["stt_provider"] == "salutespeech":
            if provider_config["salutespeech_client_id"]:
                env.setdefault("SALUTESPEECH_CLIENT_ID", provider_config["salutespeech_client_id"])
            if provider_config["salutespeech_client_secret"]:
                env.setdefault(
                    "SALUTESPEECH_CLIENT_SECRET",
                    provider_config["salutespeech_client_secret"],
                )
            env.setdefault("SALUTESPEECH_AUTH_URL", provider_config["salutespeech_auth_url"])
            env.setdefault(
                "SALUTESPEECH_RECOGNIZE_URL",
                provider_config["salutespeech_recognize_url"],
            )
            env.setdefault("SALUTESPEECH_SCOPE", provider_config["salutespeech_scope"])
    env["LOCAL_AGENT_AUTO_OPEN"] = "false"
    env["LOCAL_AGENT_PARENT_PID"] = str(os.getpid())
    env["PYTHONUNBUFFERED"] = "1"

    script_path = bundle / "scripts" / "run_local_agent.py"
    if script_path.is_dir():
        candidate = script_path / "run_local_agent.py"
        if candidate.exists():
            script_path = candidate
    if not script_path.exists():
        raise RuntimeError(f"run_local_agent.py not found: {script_path}")

    cmd = [str(python_bin), str(script_path)]
    _log("[start] starting agent...")
    agent_log = root / "agent.log"
    agent_log.parent.mkdir(parents=True, exist_ok=True)
    global APP_LOG_FH
    if APP_LOG_FH is not None:
        try:
            APP_LOG_FH.flush()
            APP_LOG_FH.close()
        except Exception:
            pass
        APP_LOG_FH = None
    APP_LOG_FH = open(agent_log, "a", encoding="utf-8")
    APP_LOG_FH.write(f"\n=== launcher start {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    APP_LOG_FH.flush()
    APP_PROCESS = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=env,
        stdout=APP_LOG_FH,
        stderr=APP_LOG_FH,
    )
    _log(f"[start] agent pid={APP_PROCESS.pid} log={agent_log}")
    _wait_app_ready(APP_URL, timeout_sec=20.0)
    return APP_URL


def _wait_app_ready(url: str, timeout_sec: float = 24.0) -> None:
    deadline = time.time() + timeout_sec
    health_url = f"{url.rstrip('/')}/health"
    root_url = f"{url.rstrip('/')}/"
    stable_hits = 0
    while time.time() < deadline:
        if APP_PROCESS is not None and APP_PROCESS.poll() is not None:
            _log("[start] agent exited early, see agent.log")
            raise RuntimeError("agent_failed_to_start")
        health_ok = False
        root_ok = False
        try:
            with urlopen(health_url, timeout=1.2) as response:
                if 200 <= int(response.status) < 300:
                    health_ok = True
        except Exception:
            pass
        try:
            with urlopen(root_url, timeout=1.2) as response:
                if 200 <= int(response.status) < 300:
                    root_ok = True
        except Exception:
            pass
        if health_ok and root_ok:
            stable_hits += 1
            if stable_hits >= 2:
                _log("[start] agent ready")
                return
        else:
            stable_hits = 0
        time.sleep(0.25)
    _log("[start] timeout waiting for /health")
    raise RuntimeError("agent_start_timeout")


def _stop_app() -> None:
    global APP_PROCESS, APP_URL, APP_LOG_FH
    stopped_pid: int | None = None
    if APP_PROCESS and APP_PROCESS.poll() is None:
        stopped_pid = APP_PROCESS.pid
        APP_PROCESS.terminate()
        try:
            APP_PROCESS.wait(timeout=5)
        except Exception:
            APP_PROCESS.kill()
    elif APP_PROCESS:
        stopped_pid = APP_PROCESS.pid
    APP_PROCESS = None
    APP_URL = None
    if APP_LOG_FH is not None:
        try:
            APP_LOG_FH.flush()
            APP_LOG_FH.close()
        except Exception:
            pass
        APP_LOG_FH = None
    _cleanup_stale_agent_pid(expected_pid=stopped_pid)


def _shutdown_launcher(server: ThreadingHTTPServer | None = None) -> None:
    global SHUTDOWN_STARTED, LAUNCHER_SERVER
    with SHUTDOWN_LOCK:
        if SHUTDOWN_STARTED:
            return
        SHUTDOWN_STARTED = True
    _stop_app()
    target = server or LAUNCHER_SERVER
    if target is not None:
        try:
            target.shutdown()
        except Exception:
            pass
        try:
            target.server_close()
        except Exception:
            pass
    _clear_launcher_pid()


def _signal_handler(signum, _frame) -> None:
    _log(f"[launcher] signal received: {signum}")
    _shutdown_launcher()


class Handler(BaseHTTPRequestHandler):
    def _read_json(self) -> dict:
        try:
            raw_len = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            raw_len = 0
        if raw_len <= 0:
            return {}
        try:
            body = self.rfile.read(raw_len)
            payload = json.loads(body.decode("utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def _send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, text: str, status: int = 200) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            ui_path = _launcher_ui_index()
            self._send_text(ui_path.read_text(encoding="utf-8"))
            return
        if parsed.path == "/api/preflight":
            self._send_json({"ok": True, "checks": _preflight_snapshot()})
            return
        if parsed.path == "/api/config":
            self._send_json({"ok": True, "config": _public_provider_config()})
            return
        if parsed.path == "/api/status":
            with STATE_LOCK:
                data = {
                    "state": INSTALL_STATE,
                    "mode": INSTALL_MODE,
                    "error": INSTALL_ERROR,
                    "log": "\n".join(INSTALL_LOG[-300:]),
                    "app_running": APP_PROCESS is not None and APP_PROCESS.poll() is None,
                    "app_url": APP_URL,
                }
            self._send_json(data)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/install":
            qs = parse_qs(parsed.query)
            mode = (qs.get("mode", ["base"])[0] or "base").strip()
            with STATE_LOCK:
                if INSTALL_STATE == "running":
                    self._send_json({"ok": False, "error": "install_running"}, status=409)
                    return
            t = threading.Thread(target=_install, args=(mode,), daemon=True)
            t.start()
            self._send_json({"ok": True})
            return
        if parsed.path == "/api/fix-all":
            payload = self._read_json()
            config = _current_provider_config()
            config.update(
                {
                    "llm_provider": str(payload.get("llm_provider") or config["llm_provider"]).strip(),
                    "llm_api_base": str(payload.get("llm_api_base") or config["llm_api_base"]).strip(),
                    "llm_api_key": str(payload.get("llm_api_key") or config["llm_api_key"]).strip(),
                    "llm_model_id": str(
                        payload.get("llm_model_id") or payload.get("model_id") or config["llm_model_id"]
                    ).strip(),
                    "embedding_provider": str(payload.get("embedding_provider") or config["embedding_provider"]).strip(),
                    "embedding_api_base": str(payload.get("embedding_api_base") or config["embedding_api_base"]).strip(),
                    "embedding_api_key": str(payload.get("embedding_api_key") or config["embedding_api_key"]).strip(),
                    "embedding_model_id": str(
                        payload.get("embedding_model_id") or config["embedding_model_id"]
                    ).strip(),
                    "stt_provider": str(payload.get("stt_provider") or config["stt_provider"]).strip(),
                    "stt_model_id": str(payload.get("stt_model_id") or config["stt_model_id"]).strip(),
                    "google_stt_service_account_json": str(
                        payload.get("google_stt_service_account_json")
                        or config["google_stt_service_account_json"]
                    ).strip(),
                    "google_stt_recognize_url": str(
                        payload.get("google_stt_recognize_url") or config["google_stt_recognize_url"]
                    ).strip(),
                    "salutespeech_client_id": str(
                        payload.get("salutespeech_client_id") or config["salutespeech_client_id"]
                    ).strip(),
                    "salutespeech_client_secret": str(
                        payload.get("salutespeech_client_secret") or config["salutespeech_client_secret"]
                    ).strip(),
                    "salutespeech_auth_url": str(
                        payload.get("salutespeech_auth_url") or config["salutespeech_auth_url"]
                    ).strip(),
                    "salutespeech_recognize_url": str(
                        payload.get("salutespeech_recognize_url")
                        or config["salutespeech_recognize_url"]
                    ).strip(),
                    "salutespeech_scope": str(
                        payload.get("salutespeech_scope") or config["salutespeech_scope"]
                    ).strip(),
                }
            )
            with STATE_LOCK:
                if INSTALL_STATE == "running":
                    self._send_json({"ok": False, "error": "install_running"}, status=409)
                    return
            t = threading.Thread(target=_fix_all, args=(config,), daemon=True)
            t.start()
            self._send_json({"ok": True, "config": config})
            return
        if parsed.path == "/api/config":
            payload = self._read_json()
            config = _current_provider_config()
            config.update(
                {
                    "llm_provider": str(payload.get("llm_provider") or config["llm_provider"]).strip(),
                    "llm_api_base": str(payload.get("llm_api_base") or config["llm_api_base"]).strip(),
                    "llm_api_key": str(payload.get("llm_api_key") or config["llm_api_key"]).strip(),
                    "llm_model_id": str(payload.get("llm_model_id") or config["llm_model_id"]).strip(),
                    "embedding_provider": str(payload.get("embedding_provider") or config["embedding_provider"]).strip(),
                    "embedding_api_base": str(payload.get("embedding_api_base") or config["embedding_api_base"]).strip(),
                    "embedding_api_key": str(payload.get("embedding_api_key") or config["embedding_api_key"]).strip(),
                    "embedding_model_id": str(payload.get("embedding_model_id") or config["embedding_model_id"]).strip(),
                    "stt_provider": str(payload.get("stt_provider") or config["stt_provider"]).strip(),
                    "stt_model_id": str(payload.get("stt_model_id") or config["stt_model_id"]).strip(),
                    "google_stt_service_account_json": str(
                        payload.get("google_stt_service_account_json")
                        or config["google_stt_service_account_json"]
                    ).strip(),
                    "google_stt_recognize_url": str(
                        payload.get("google_stt_recognize_url") or config["google_stt_recognize_url"]
                    ).strip(),
                    "salutespeech_client_id": str(
                        payload.get("salutespeech_client_id") or config["salutespeech_client_id"]
                    ).strip(),
                    "salutespeech_client_secret": str(
                        payload.get("salutespeech_client_secret") or config["salutespeech_client_secret"]
                    ).strip(),
                    "salutespeech_auth_url": str(
                        payload.get("salutespeech_auth_url") or config["salutespeech_auth_url"]
                    ).strip(),
                    "salutespeech_recognize_url": str(
                        payload.get("salutespeech_recognize_url")
                        or config["salutespeech_recognize_url"]
                    ).strip(),
                    "salutespeech_scope": str(
                        payload.get("salutespeech_scope") or config["salutespeech_scope"]
                    ).strip(),
                }
            )
            _save_provider_config(config)
            self._send_json({"ok": True, "config": _public_provider_config()})
            return
        if parsed.path == "/api/action":
            payload = self._read_json()
            action = str(payload.get("action") or "").strip().lower()
            if action == "open_provider_app":
                config = _current_provider_config()
                opened = False
                if config["llm_provider"] == "openai_compat" and _is_local_ollama_base(config["llm_api_base"]):
                    opened = _open_ollama_app()
                self._send_json({"ok": opened})
                return
            if action == "pull_model":
                config = _current_provider_config()
                if not (
                    config["llm_provider"] == "openai_compat" and _is_local_ollama_base(config["llm_api_base"])
                ):
                    self._send_json({"ok": False, "error": "local_provider_required"}, status=400)
                    return
                kind = str(payload.get("kind") or "llm").strip().lower()
                override_key = "EMBEDDING_MODEL_ID" if kind in {"embedding", "embeddings"} else "LLM_MODEL_ID"
                default_model = (
                    OLLAMA_DEFAULT_EMBEDDING_MODEL if override_key == "EMBEDDING_MODEL_ID" else OLLAMA_DEFAULT_MODEL
                )
                model_id = str(payload.get("model_id") or "").strip() or default_model
                with STATE_LOCK:
                    if INSTALL_STATE == "running":
                        self._send_json({"ok": False, "error": "install_running"}, status=409)
                        return
                t = threading.Thread(target=_pull_model_task, args=(model_id, override_key), daemon=True)
                t.start()
                self._send_json({"ok": True, "model_id": model_id, "kind": kind})
                return
            if action == "set_model":
                kind = str(payload.get("kind") or "llm").strip().lower()
                model_id = str(payload.get("model_id") or "").strip()
                if not model_id:
                    self._send_json({"ok": False, "error": "model_required"}, status=400)
                    return
                config = _current_provider_config()
                if kind in {"embedding", "embeddings"}:
                    config["embedding_model_id"] = model_id
                else:
                    config["llm_model_id"] = model_id
                _save_provider_config(config)
                self._send_json({"ok": True, "model_id": model_id, "kind": kind})
                return
            self._send_json({"ok": False, "error": "unknown_action"}, status=400)
            return
        if parsed.path == "/api/start":
            try:
                url = _start_app()
                self._send_json({"ok": True, "url": url})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=500)
            return
        if parsed.path == "/api/stop":
            _stop_app()
            self._send_json({"ok": True})
            return
        if parsed.path == "/api/shutdown":
            self._send_json({"ok": True})
            t = threading.Thread(target=_shutdown_launcher, daemon=True)
            t.start()
            return
        if parsed.path == "/api/open":
            try:
                url = _start_app()
                self._send_json({"ok": True, "url": url})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=500)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> None:
    global INSTALL_MODE, LAUNCHER_SERVER
    INSTALL_MODE = _load_install_mode()
    _claim_single_launcher_instance()
    _cleanup_stale_agent_pid()
    _prepare_runtime_logs()
    atexit.register(_clear_launcher_pid)
    _log("[launcher] starting...")
    port = _pick_launcher_port()
    url = f"http://127.0.0.1:{port}"
    _write_url_file(url)
    try:
        LAUNCHER_SERVER = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except Exception as e:
        _log(f"[launcher] bind failed: {e}")
        raise
    atexit.register(_shutdown_launcher, LAUNCHER_SERVER)
    for sig_name in ("SIGINT", "SIGTERM", "SIGHUP"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _signal_handler)
        except Exception:
            pass
    print(f"[launcher] UI: {url}")
    serve_thread = threading.Thread(target=LAUNCHER_SERVER.serve_forever, daemon=True)
    serve_thread.start()
    time.sleep(0.3)
    opened = False
    try:
        opened = webbrowser.open(url, new=2)
    except Exception as e:
        _log(f"[launcher] webbrowser failed: {e}")
    if not opened and sys.platform == "darwin":
        try:
            subprocess.Popen(["open", url])
        except Exception as e:
            _log(f"[launcher] open failed: {e}")
    try:
        serve_thread.join()
    finally:
        _shutdown_launcher(LAUNCHER_SERVER)


if __name__ == "__main__":
    main()
