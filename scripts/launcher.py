#!/usr/bin/env python3
from __future__ import annotations

import json
import os
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

OLLAMA_DEFAULT_MODEL = "llama3.1:8b"


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
    if target_tag != candidate_tag:
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


def _preflight_snapshot() -> dict:
    root = _user_root()
    _venv_dir, python_bin = _venv_paths(root)
    venv_ready = python_bin.exists()
    whisper_ready = bool(venv_ready and _venv_has_whisper(python_bin))
    install_mode_saved = _load_install_mode()
    runtime = _load_runtime_overrides()
    target_model = str(runtime.get("LLM_MODEL_ID") or "").strip() or OLLAMA_DEFAULT_MODEL
    ollama_cli = _ollama_bin() is not None
    ollama_ready = _ollama_running(timeout_sec=1.4) if ollama_cli else False
    models = _ollama_models(timeout_sec=2.5) if ollama_cli else []
    model_present, model_exact, model_matched = _resolve_model_match(target_model, models)
    return {
        "venv_ready": venv_ready,
        "whisper_ready": whisper_ready,
        "install_mode_saved": install_mode_saved,
        "ollama_cli_found": ollama_cli,
        "ollama_running": ollama_ready,
        "ollama_model_default": target_model,
        "ollama_model_present": model_present,
        "ollama_model_exact": model_exact,
        "ollama_model_matched": model_matched,
        "ollama_models": models,
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


def _fix_all(model_id: str | None = None) -> None:
    target_model = str(model_id or "").strip() or OLLAMA_DEFAULT_MODEL
    try:
        _set_state("running")
        _log("[wizard] fix-all started")
        _install("full")
        with STATE_LOCK:
            if INSTALL_STATE == "error":
                return

        snap = _preflight_snapshot()
        if not snap.get("ollama_cli_found"):
            raise RuntimeError("Ollama CLI не найден. Установите Ollama и повторите.")

        if not snap.get("ollama_running"):
            _log("[wizard] starting Ollama app...")
            _open_ollama_app()
            if not _wait_ollama_ready(timeout_sec=35.0):
                raise RuntimeError("Ollama не запустился на порту 11434")

        snap = _preflight_snapshot()
        models = [str(model) for model in (snap.get("ollama_models") or [])]
        model_present, _model_exact, model_matched = _resolve_model_match(target_model, models)
        active_model = target_model
        if model_present:
            if model_matched and model_matched.lower() != target_model.lower():
                _log(f"[wizard] compatible model found: {model_matched} (requested {target_model})")
                active_model = model_matched
        else:
            if not _pull_ollama_model(target_model):
                raise RuntimeError(f"Не удалось скачать модель {target_model}")
            active_model = target_model

        _save_runtime_override("LLM_MODEL_ID", active_model)
        _save_runtime_override("OPENAI_API_BASE", "http://127.0.0.1:11434/v1")
        _save_runtime_override("OPENAI_API_KEY", "ollama")
        _save_runtime_override("LLM_ENABLED", "true")
        _save_runtime_override("LLM_LIVE_ENABLED", "false")
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


def _pull_model_task(model_id: str) -> None:
    model = str(model_id or "").strip() or OLLAMA_DEFAULT_MODEL
    try:
        _set_state("running")
        if not _pull_ollama_model(model):
            raise RuntimeError(f"Не удалось скачать модель {model}")
        _save_runtime_override("LLM_MODEL_ID", model)
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
    env.setdefault("OPENAI_API_BASE", "http://127.0.0.1:11434/v1")
    env.setdefault("OPENAI_API_KEY", "ollama")
    env.setdefault("LLM_MODEL_ID", "llama3.1:8b")
    env.setdefault("BACKUP_AUDIO_RECOVERY_ENABLED", "true")
    env["POSTGRES_DSN"] = f"sqlite:///{(root / 'agent.db').as_posix()}"
    env["RECORDS_DIR"] = str(root / "records")
    env["CHUNKS_DIR"] = str(root / "chunks")
    env["LOCAL_AGENT_STATE_DIR"] = str(root / "state")
    env["STT_PROVIDER"] = "whisper_local" if INSTALL_MODE == "full" else "mock"
    if INSTALL_MODE == "full":
        env.setdefault("WHISPER_MODEL_SIZE", "medium")
        env.setdefault("WHISPER_COMPUTE_TYPE", "int8")
        env.setdefault("WHISPER_LANGUAGE", "ru")
        env.setdefault("WHISPER_VAD_FILTER", "true")
        env.setdefault("WHISPER_BEAM_SIZE_LIVE", "3")
        env.setdefault("WHISPER_BEAM_SIZE_FINAL", "6")
        env.setdefault("WHISPER_WARMUP_ON_START", "true")
    env["LOCAL_AGENT_AUTO_OPEN"] = "false"
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
    log_fh = open(agent_log, "a", encoding="utf-8")
    log_fh.write(f"\n=== launcher start {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    log_fh.flush()
    APP_PROCESS = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=env,
        stdout=log_fh,
        stderr=log_fh,
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
    global APP_PROCESS
    if APP_PROCESS and APP_PROCESS.poll() is None:
        APP_PROCESS.terminate()
        try:
            APP_PROCESS.wait(timeout=5)
        except Exception:
            APP_PROCESS.kill()
    APP_PROCESS = None


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
            model_id = str(payload.get("model_id") or "").strip() or OLLAMA_DEFAULT_MODEL
            with STATE_LOCK:
                if INSTALL_STATE == "running":
                    self._send_json({"ok": False, "error": "install_running"}, status=409)
                    return
            t = threading.Thread(target=_fix_all, args=(model_id,), daemon=True)
            t.start()
            self._send_json({"ok": True, "model_id": model_id})
            return
        if parsed.path == "/api/action":
            payload = self._read_json()
            action = str(payload.get("action") or "").strip().lower()
            if action == "open_ollama":
                opened = _open_ollama_app()
                self._send_json({"ok": opened})
                return
            if action == "pull_model":
                model_id = str(payload.get("model_id") or "").strip() or OLLAMA_DEFAULT_MODEL
                with STATE_LOCK:
                    if INSTALL_STATE == "running":
                        self._send_json({"ok": False, "error": "install_running"}, status=409)
                        return
                t = threading.Thread(target=_pull_model_task, args=(model_id,), daemon=True)
                t.start()
                self._send_json({"ok": True, "model_id": model_id})
                return
            if action == "set_model":
                model_id = str(payload.get("model_id") or "").strip()
                if not model_id:
                    self._send_json({"ok": False, "error": "model_required"}, status=400)
                    return
                _save_runtime_override("LLM_MODEL_ID", model_id)
                self._send_json({"ok": True, "model_id": model_id})
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
        if parsed.path == "/api/open":
            try:
                url = _start_app()
                self._send_json({"ok": True, "url": url})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=500)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> None:
    global INSTALL_MODE
    INSTALL_MODE = _load_install_mode()
    _log("[launcher] starting...")
    port = _pick_launcher_port()
    url = f"http://127.0.0.1:{port}"
    _write_url_file(url)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except Exception as e:
        _log(f"[launcher] bind failed: {e}")
        raise
    print(f"[launcher] UI: {url}")
    serve_thread = threading.Thread(target=server.serve_forever, daemon=True)
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
    serve_thread.join()


if __name__ == "__main__":
    main()
