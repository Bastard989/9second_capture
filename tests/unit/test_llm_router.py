from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from apps.api_gateway.main import app
from apps.api_gateway.routers import llm as llm_router
from interview_analytics_agent.common.config import get_settings


@pytest.fixture()
def auth_none_settings():
    s = get_settings()
    snapshot_auth = s.auth_mode
    snapshot_llm_enabled = s.llm_enabled
    snapshot_llm_live_enabled = s.llm_live_enabled
    snapshot_model = s.llm_model_id
    snapshot_llm_provider = getattr(s, "llm_provider", "openai_compat")
    snapshot_llm_api_base = getattr(s, "llm_api_base", None)
    snapshot_llm_api_key = getattr(s, "llm_api_key", None)
    snapshot_stt_provider = getattr(s, "stt_provider", "whisper_local")
    snapshot_stt_model_id = getattr(s, "stt_model_id", None)
    snapshot_stt_model = getattr(s, "whisper_model_size", "medium")
    snapshot_google_stt_service_account_json = getattr(s, "google_stt_service_account_json", None)
    snapshot_google_stt_recognize_url = getattr(s, "google_stt_recognize_url", None)
    snapshot_salutespeech_client_id = getattr(s, "salutespeech_client_id", None)
    snapshot_salutespeech_client_secret = getattr(s, "salutespeech_client_secret", None)
    snapshot_salutespeech_auth_url = getattr(s, "salutespeech_auth_url", None)
    snapshot_salutespeech_recognize_url = getattr(s, "salutespeech_recognize_url", None)
    snapshot_salutespeech_scope = getattr(s, "salutespeech_scope", None)
    snapshot_embedding_provider = getattr(s, "embedding_provider", "auto")
    snapshot_embedding_model = getattr(s, "embedding_model_id", "nomic-embed-text")
    snapshot_api_base = s.openai_api_base
    snapshot_api_key = s.openai_api_key
    snapshot_embedding_api_base = getattr(s, "embedding_api_base", None)
    snapshot_embedding_api_key = getattr(s, "embedding_api_key", None)
    snapshot_rag_embedding_provider = getattr(s, "rag_embedding_provider", "auto")
    snapshot_rag_vector_enabled = getattr(s, "rag_vector_enabled", True)
    snapshot_env_model = os.environ.get("LLM_MODEL_ID")
    snapshot_env_llm_provider = os.environ.get("LLM_PROVIDER")
    snapshot_env_llm_api_base = os.environ.get("LLM_API_BASE")
    snapshot_env_llm_api_key = os.environ.get("LLM_API_KEY")
    snapshot_env_stt_model = os.environ.get("WHISPER_MODEL_SIZE")
    snapshot_env_stt_provider = os.environ.get("STT_PROVIDER")
    snapshot_env_stt_model_id = os.environ.get("STT_MODEL_ID")
    snapshot_env_google_stt_service_account_json = os.environ.get("GOOGLE_STT_SERVICE_ACCOUNT_JSON")
    snapshot_env_google_stt_recognize_url = os.environ.get("GOOGLE_STT_RECOGNIZE_URL")
    snapshot_env_salutespeech_client_id = os.environ.get("SALUTESPEECH_CLIENT_ID")
    snapshot_env_salutespeech_client_secret = os.environ.get("SALUTESPEECH_CLIENT_SECRET")
    snapshot_env_salutespeech_auth_url = os.environ.get("SALUTESPEECH_AUTH_URL")
    snapshot_env_salutespeech_recognize_url = os.environ.get("SALUTESPEECH_RECOGNIZE_URL")
    snapshot_env_salutespeech_scope = os.environ.get("SALUTESPEECH_SCOPE")
    snapshot_env_embedding_model = os.environ.get("EMBEDDING_MODEL_ID")
    snapshot_env_embedding_provider = os.environ.get("EMBEDDING_PROVIDER")
    try:
        s.auth_mode = "none"
        s.llm_enabled = True
        s.llm_live_enabled = False
        s.llm_provider = "openai_compat"
        s.llm_api_base = "http://127.0.0.1:11434/v1"
        s.llm_api_key = "ollama"
        s.llm_model_id = "llama3.1:8b"
        s.stt_provider = "whisper_local"
        s.stt_model_id = None
        s.whisper_model_size = "medium"
        s.google_stt_service_account_json = None
        s.google_stt_recognize_url = "https://speech.googleapis.com/v1/speech:recognize"
        s.salutespeech_client_id = None
        s.salutespeech_client_secret = None
        s.salutespeech_auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        s.salutespeech_recognize_url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
        s.salutespeech_scope = "SALUTE_SPEECH_PERS"
        s.embedding_provider = "openai_compat"
        s.embedding_model_id = "nomic-embed-text"
        s.openai_api_base = "http://127.0.0.1:11434/v1"
        s.openai_api_key = "ollama"
        s.embedding_api_base = None
        s.embedding_api_key = None
        s.rag_embedding_provider = "openai_compat"
        s.rag_vector_enabled = True
        yield s
    finally:
        s.auth_mode = snapshot_auth
        s.llm_enabled = snapshot_llm_enabled
        s.llm_live_enabled = snapshot_llm_live_enabled
        s.llm_provider = snapshot_llm_provider
        s.llm_api_base = snapshot_llm_api_base
        s.llm_api_key = snapshot_llm_api_key
        s.llm_model_id = snapshot_model
        s.stt_provider = snapshot_stt_provider
        s.stt_model_id = snapshot_stt_model_id
        s.whisper_model_size = snapshot_stt_model
        s.google_stt_service_account_json = snapshot_google_stt_service_account_json
        s.google_stt_recognize_url = snapshot_google_stt_recognize_url
        s.salutespeech_client_id = snapshot_salutespeech_client_id
        s.salutespeech_client_secret = snapshot_salutespeech_client_secret
        s.salutespeech_auth_url = snapshot_salutespeech_auth_url
        s.salutespeech_recognize_url = snapshot_salutespeech_recognize_url
        s.salutespeech_scope = snapshot_salutespeech_scope
        s.embedding_provider = snapshot_embedding_provider
        s.embedding_model_id = snapshot_embedding_model
        s.openai_api_base = snapshot_api_base
        s.openai_api_key = snapshot_api_key
        s.embedding_api_base = snapshot_embedding_api_base
        s.embedding_api_key = snapshot_embedding_api_key
        s.rag_embedding_provider = snapshot_rag_embedding_provider
        s.rag_vector_enabled = snapshot_rag_vector_enabled
        if snapshot_env_model is None:
            os.environ.pop("LLM_MODEL_ID", None)
        else:
            os.environ["LLM_MODEL_ID"] = snapshot_env_model
        if snapshot_env_llm_provider is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = snapshot_env_llm_provider
        if snapshot_env_llm_api_base is None:
            os.environ.pop("LLM_API_BASE", None)
        else:
            os.environ["LLM_API_BASE"] = snapshot_env_llm_api_base
        if snapshot_env_llm_api_key is None:
            os.environ.pop("LLM_API_KEY", None)
        else:
            os.environ["LLM_API_KEY"] = snapshot_env_llm_api_key
        if snapshot_env_stt_model is None:
            os.environ.pop("WHISPER_MODEL_SIZE", None)
        else:
            os.environ["WHISPER_MODEL_SIZE"] = snapshot_env_stt_model
        if snapshot_env_stt_provider is None:
            os.environ.pop("STT_PROVIDER", None)
        else:
            os.environ["STT_PROVIDER"] = snapshot_env_stt_provider
        if snapshot_env_stt_model_id is None:
            os.environ.pop("STT_MODEL_ID", None)
        else:
            os.environ["STT_MODEL_ID"] = snapshot_env_stt_model_id
        if snapshot_env_google_stt_service_account_json is None:
            os.environ.pop("GOOGLE_STT_SERVICE_ACCOUNT_JSON", None)
        else:
            os.environ["GOOGLE_STT_SERVICE_ACCOUNT_JSON"] = snapshot_env_google_stt_service_account_json
        if snapshot_env_google_stt_recognize_url is None:
            os.environ.pop("GOOGLE_STT_RECOGNIZE_URL", None)
        else:
            os.environ["GOOGLE_STT_RECOGNIZE_URL"] = snapshot_env_google_stt_recognize_url
        if snapshot_env_salutespeech_client_id is None:
            os.environ.pop("SALUTESPEECH_CLIENT_ID", None)
        else:
            os.environ["SALUTESPEECH_CLIENT_ID"] = snapshot_env_salutespeech_client_id
        if snapshot_env_salutespeech_client_secret is None:
            os.environ.pop("SALUTESPEECH_CLIENT_SECRET", None)
        else:
            os.environ["SALUTESPEECH_CLIENT_SECRET"] = snapshot_env_salutespeech_client_secret
        if snapshot_env_salutespeech_auth_url is None:
            os.environ.pop("SALUTESPEECH_AUTH_URL", None)
        else:
            os.environ["SALUTESPEECH_AUTH_URL"] = snapshot_env_salutespeech_auth_url
        if snapshot_env_salutespeech_recognize_url is None:
            os.environ.pop("SALUTESPEECH_RECOGNIZE_URL", None)
        else:
            os.environ["SALUTESPEECH_RECOGNIZE_URL"] = snapshot_env_salutespeech_recognize_url
        if snapshot_env_salutespeech_scope is None:
            os.environ.pop("SALUTESPEECH_SCOPE", None)
        else:
            os.environ["SALUTESPEECH_SCOPE"] = snapshot_env_salutespeech_scope
        if snapshot_env_embedding_model is None:
            os.environ.pop("EMBEDDING_MODEL_ID", None)
        else:
            os.environ["EMBEDDING_MODEL_ID"] = snapshot_env_embedding_model
        if snapshot_env_embedding_provider is None:
            os.environ.pop("EMBEDDING_PROVIDER", None)
        else:
            os.environ["EMBEDDING_PROVIDER"] = snapshot_env_embedding_provider


def test_llm_status_endpoint(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.get("/v1/llm/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_enabled"] is True
    assert body["provider"] == "openai_compat"
    assert body["model_id"] == "llama3.1:8b"


def test_llm_models_endpoint_returns_models(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["llama3.1:8b", "qwen2.5:7b"],
    )

    client = TestClient(app)
    resp = client.get("/v1/llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["current_model"] == "llama3.1:8b"
    assert "qwen2.5:7b" in body["models"]


def test_llm_models_endpoint_filters_out_embedding_models(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["llama3.1:8b", "nomic-embed-text", "mxbai-embed-large"],
    )

    client = TestClient(app)
    resp = client.get("/v1/llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == ["llama3.1:8b"]


def test_llm_model_update_endpoint_updates_runtime(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["llama3.1:8b", "qwen2.5:14b"],
    )
    client = TestClient(app)
    resp = client.post("/v1/llm/model", json={"model_id": "qwen2.5:14b"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["model_id"] == "qwen2.5:14b"
    s = get_settings()
    assert s.llm_model_id == "qwen2.5:14b"
    assert os.environ.get("LLM_MODEL_ID") == "qwen2.5:14b"


def test_llm_model_update_rejects_embedding_model(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["llama3.1:8b", "nomic-embed-text"],
    )
    client = TestClient(app)
    resp = client.post("/v1/llm/model", json={"model_id": "nomic-embed-text"})
    assert resp.status_code == 400
    body = resp.json()
    assert "embedding model" in str(body.get("detail", "")).lower()


def test_stt_status_endpoint(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.get("/v1/stt/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "whisper_local"
    assert body["model_id"] == "medium"
    assert body["provider_ready"] is True


def test_stt_models_endpoint_returns_catalog(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.get("/v1/stt/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["current_model"] == "medium"
    assert "small" in body["models"]
    assert "large-v3" in body["models"]


def test_stt_model_update_endpoint_updates_runtime(monkeypatch, auth_none_settings) -> None:
    called = {"value": False}

    def _fake_reset_stt_provider_runtime(*, restart_warmup: bool = False) -> None:
        called["value"] = bool(restart_warmup)

    monkeypatch.setattr(
        llm_router,
        "reset_stt_provider_runtime",
        _fake_reset_stt_provider_runtime,
    )

    client = TestClient(app)
    resp = client.post("/v1/stt/model", json={"model_id": "small"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["model_id"] == "small"
    s = get_settings()
    assert s.whisper_model_size == "small"
    assert os.environ.get("WHISPER_MODEL_SIZE") == "small"
    assert called["value"] is False


def test_embedding_status_endpoint_openai_compat_ready(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["nomic-embed-text", "llama3.1:8b"],
    )

    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["vector_enabled"] is True
    assert body["available"] is True
    assert body["provider"] == "OpenAI-compatible"
    assert body["model_id"] == "nomic-embed-text"


def test_embedding_models_endpoint_returns_models(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["nomic-embed-text", "mxbai-embed-large"],
    )

    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["current_model"] == "nomic-embed-text"
    assert "mxbai-embed-large" in body["models"]


def test_embedding_models_endpoint_filters_out_chat_models(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["llama3.1:8b", "nomic-embed-text", "qwen2.5:7b"],
    )

    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == ["nomic-embed-text"]


def test_embedding_model_update_endpoint_updates_runtime(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_provider_models",
        lambda **kwargs: ["nomic-embed-text", "mxbai-embed-large"],
    )
    client = TestClient(app)
    resp = client.post("/v1/llm/embeddings/model", json={"model_id": "mxbai-embed-large"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["model_id"] == "mxbai-embed-large"
    s = get_settings()
    assert s.embedding_model_id == "mxbai-embed-large"
    assert os.environ.get("EMBEDDING_MODEL_ID") == "mxbai-embed-large"


def test_embedding_model_update_rejects_chat_model(monkeypatch, auth_none_settings) -> None:
    called = {"value": False}

    def _fake_fetch(**kwargs):
        called["value"] = True
        return ["nomic-embed-text"]

    monkeypatch.setattr(llm_router, "_fetch_provider_models", _fake_fetch)
    client = TestClient(app)
    resp = client.post("/v1/llm/embeddings/model", json={"model_id": "llama3.1:8b"})
    assert resp.status_code == 400
    body = resp.json()
    assert "not an embedding model" in str(body.get("detail", "")).lower()
    assert called["value"] is False


def test_embedding_status_hashing_fallback_when_disabled(auth_none_settings) -> None:
    s = get_settings()
    s.rag_vector_enabled = False
    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["vector_enabled"] is False
    assert body["provider"] == "disabled"


def test_llm_config_endpoint_returns_provider_info(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.get("/v1/llm/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "openai_compat"
    assert body["api_base"] == "http://127.0.0.1:11434/v1"
    assert body["api_key_set"] is True


def test_llm_config_update_keeps_existing_key_when_blank(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/llm/config",
        json={
            "provider": "openai",
            "api_base": "https://api.openai.com/v1",
            "api_key": "",
            "model_id": "gpt-4.1-mini",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "openai"
    s = get_settings()
    assert s.llm_api_key == "ollama"
    assert s.llm_model_id == "gpt-4.1-mini"


def test_embedding_config_update_sets_hashing_provider(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/llm/embeddings/config",
        json={
            "provider": "hashing",
            "api_base": "",
            "api_key": "",
            "model_id": "hashing_local",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "hashing"
    s = get_settings()
    assert s.embedding_provider == "hashing"
    assert s.rag_embedding_provider == "hashing"


def test_stt_config_update_switches_provider(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.post("/v1/stt/config", json={"provider": "mock", "model_id": "mock"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mock"
    s = get_settings()
    assert s.stt_provider == "mock"


def test_stt_config_update_sets_google_credentials(auth_none_settings) -> None:
    client = TestClient(app)
    service_json = '{"type":"service_account","client_email":"bot@example.iam.gserviceaccount.com","private_key":"-----BEGIN PRIVATE KEY-----\\\\nabc\\\\n-----END PRIVATE KEY-----\\\\n"}'
    resp = client.post(
        "/v1/stt/config",
        json={
            "provider": "google",
            "model_id": "latest_long",
            "google_service_account_json": service_json,
            "google_recognize_url": "https://speech.googleapis.com/v1/speech:recognize",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "google"
    assert body["google_service_account_set"] is True
    s = get_settings()
    assert s.stt_provider == "google"
    assert s.stt_model_id == "latest_long"
    assert s.google_stt_service_account_json == service_json
    assert os.environ.get("GOOGLE_STT_SERVICE_ACCOUNT_JSON") == service_json


def test_stt_status_reports_missing_salute_credentials(auth_none_settings) -> None:
    s = get_settings()
    s.stt_provider = "salutespeech"
    s.stt_model_id = "general"
    s.salutespeech_client_id = ""
    s.salutespeech_client_secret = ""
    client = TestClient(app)
    resp = client.get("/v1/stt/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "salutespeech"
    assert body["provider_ready"] is False
    assert "SaluteSpeech" in body["message"]


def test_stt_config_update_clears_inactive_google_secret(auth_none_settings) -> None:
    s = get_settings()
    s.stt_provider = "google"
    s.google_stt_service_account_json = '{"type":"service_account"}'
    os.environ["GOOGLE_STT_SERVICE_ACCOUNT_JSON"] = '{"type":"service_account"}'

    client = TestClient(app)
    resp = client.post(
        "/v1/stt/config",
        json={
            "provider": "salutespeech",
            "model_id": "general",
            "salutespeech_client_id": "demo-client",
            "salutespeech_client_secret": "demo-secret",
            "salutespeech_auth_url": "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            "salutespeech_recognize_url": "https://smartspeech.sber.ru/rest/v1/speech:recognize",
            "salutespeech_scope": "SALUTE_SPEECH_PERS",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "salutespeech"
    assert body["google_service_account_set"] is False
    assert s.google_stt_service_account_json is None
    assert os.environ.get("GOOGLE_STT_SERVICE_ACCOUNT_JSON") is None


def test_stt_verify_endpoint_returns_provider_message(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "verify_stt_provider_connection",
        lambda: {
            "ok": True,
            "provider": "google",
            "message": "Google STT: доступ подтвержден, токен получен.",
        },
    )
    client = TestClient(app)
    resp = client.post("/v1/stt/verify", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["provider"] == "google"
    assert "токен получен" in body["message"].lower()


def test_stt_status_reports_google_placeholder_as_not_ready(auth_none_settings) -> None:
    s = get_settings()
    s.stt_provider = "google"
    s.google_stt_service_account_json = (
        '{"type":"service_account","client_email":"bot@example.iam.gserviceaccount.com",'
        '"private_key":"-----BEGIN PRIVATE KEY-----\\\\nabc\\\\n-----END PRIVATE KEY-----\\\\n"}'
    )
    client = TestClient(app)
    resp = client.get("/v1/stt/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "google"
    assert body["provider_ready"] is False
    assert "пример" in body["message"].lower()


def test_stt_status_reports_salute_placeholder_as_not_ready(auth_none_settings) -> None:
    s = get_settings()
    s.stt_provider = "salutespeech"
    s.stt_model_id = "general"
    s.salutespeech_client_id = "demo-client"
    s.salutespeech_client_secret = "demo-secret"
    s.salutespeech_auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    s.salutespeech_recognize_url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
    client = TestClient(app)
    resp = client.get("/v1/stt/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "salutespeech"
    assert body["provider_ready"] is False
    assert "пример" in body["message"].lower()
