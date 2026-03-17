import importlib.util
from pathlib import Path


def _load_launcher_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "launcher.py"
    spec = importlib.util.spec_from_file_location("launcher_script_preflight", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_marks_google_placeholder_not_ready(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    mod = _load_launcher_module()

    monkeypatch.setattr(mod, "_venv_paths", lambda root: (root / "venv", tmp_path / "python"))
    monkeypatch.setattr(mod, "_venv_has_whisper", lambda python_bin: True)
    monkeypatch.setattr(mod, "_load_install_mode", lambda: "full")
    monkeypatch.setattr(mod, "_load_runtime_overrides", lambda: {})
    monkeypatch.setattr(
        mod,
        "_current_provider_config",
        lambda runtime: {
            "llm_provider": "mock",
            "llm_api_base": "",
            "llm_api_key": "",
            "llm_model_id": "mock",
            "embedding_provider": "hashing",
            "embedding_api_base": "",
            "embedding_api_key": "",
            "embedding_model_id": "hashing",
            "stt_provider": "google",
            "stt_model_id": "latest_long",
            "google_stt_service_account_json": (
                '{"type":"service_account","client_email":"bot@example.iam.gserviceaccount.com"}'
            ),
            "google_stt_recognize_url": "https://speech.googleapis.com/v1/speech:recognize",
            "salutespeech_client_id": "",
            "salutespeech_client_secret": "",
            "salutespeech_auth_url": "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            "salutespeech_recognize_url": "https://smartspeech.sber.ru/rest/v1/speech:recognize",
        },
    )

    payload = mod._preflight_snapshot()

    assert payload["stt_provider"] == "google"
    assert payload["stt_provider_ready"] is False
    assert "пример" in payload["stt_provider_value"].lower()


def test_preflight_marks_salute_placeholder_not_ready(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    mod = _load_launcher_module()

    monkeypatch.setattr(mod, "_venv_paths", lambda root: (root / "venv", tmp_path / "python"))
    monkeypatch.setattr(mod, "_venv_has_whisper", lambda python_bin: True)
    monkeypatch.setattr(mod, "_load_install_mode", lambda: "full")
    monkeypatch.setattr(mod, "_load_runtime_overrides", lambda: {})
    monkeypatch.setattr(
        mod,
        "_current_provider_config",
        lambda runtime: {
            "llm_provider": "mock",
            "llm_api_base": "",
            "llm_api_key": "",
            "llm_model_id": "mock",
            "embedding_provider": "hashing",
            "embedding_api_base": "",
            "embedding_api_key": "",
            "embedding_model_id": "hashing",
            "stt_provider": "salutespeech",
            "stt_model_id": "general",
            "google_stt_service_account_json": "",
            "google_stt_recognize_url": "https://speech.googleapis.com/v1/speech:recognize",
            "salutespeech_client_id": "demo-client",
            "salutespeech_client_secret": "demo-secret",
            "salutespeech_auth_url": "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            "salutespeech_recognize_url": "https://smartspeech.sber.ru/rest/v1/speech:recognize",
        },
    )

    payload = mod._preflight_snapshot()

    assert payload["stt_provider"] == "salutespeech"
    assert payload["stt_provider_ready"] is False
    assert "пример" in payload["stt_provider_value"].lower()
