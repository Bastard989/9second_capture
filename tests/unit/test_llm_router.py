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
    snapshot_stt_provider = getattr(s, "stt_provider", "whisper_local")
    snapshot_stt_model = getattr(s, "whisper_model_size", "medium")
    snapshot_embedding_model = getattr(s, "embedding_model_id", "nomic-embed-text")
    snapshot_api_base = s.openai_api_base
    snapshot_api_key = s.openai_api_key
    snapshot_embedding_api_base = getattr(s, "embedding_api_base", None)
    snapshot_embedding_api_key = getattr(s, "embedding_api_key", None)
    snapshot_rag_embedding_provider = getattr(s, "rag_embedding_provider", "auto")
    snapshot_rag_vector_enabled = getattr(s, "rag_vector_enabled", True)
    snapshot_env_model = os.environ.get("LLM_MODEL_ID")
    snapshot_env_stt_model = os.environ.get("WHISPER_MODEL_SIZE")
    snapshot_env_embedding_model = os.environ.get("EMBEDDING_MODEL_ID")
    try:
        s.auth_mode = "none"
        s.llm_enabled = True
        s.llm_live_enabled = False
        s.llm_model_id = "llama3.1:8b"
        s.stt_provider = "whisper_local"
        s.whisper_model_size = "medium"
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
        s.llm_model_id = snapshot_model
        s.stt_provider = snapshot_stt_provider
        s.whisper_model_size = snapshot_stt_model
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
        if snapshot_env_stt_model is None:
            os.environ.pop("WHISPER_MODEL_SIZE", None)
        else:
            os.environ["WHISPER_MODEL_SIZE"] = snapshot_env_stt_model
        if snapshot_env_embedding_model is None:
            os.environ.pop("EMBEDDING_MODEL_ID", None)
        else:
            os.environ["EMBEDDING_MODEL_ID"] = snapshot_env_embedding_model


def test_llm_status_endpoint(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.get("/v1/llm/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_enabled"] is True
    assert body["provider"] == "openai_compat"
    assert body["model_id"] == "llama3.1:8b"


def test_llm_models_endpoint_returns_models(monkeypatch, auth_none_settings) -> None:
    class _Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "data": [
                    {"id": "llama3.1:8b"},
                    {"id": "qwen2.5:7b"},
                ]
            }

    monkeypatch.setattr(llm_router.requests, "get", lambda *args, **kwargs: _Resp())

    client = TestClient(app)
    resp = client.get("/v1/llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["current_model"] == "llama3.1:8b"
    assert "qwen2.5:7b" in body["models"]


def test_llm_models_endpoint_filters_out_embedding_models(monkeypatch, auth_none_settings) -> None:
    class _Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "data": [
                    {"id": "llama3.1:8b"},
                    {"id": "nomic-embed-text"},
                    {"id": "mxbai-embed-large"},
                ]
            }

    monkeypatch.setattr(llm_router.requests, "get", lambda *args, **kwargs: _Resp())

    client = TestClient(app)
    resp = client.get("/v1/llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == ["llama3.1:8b"]


def test_llm_model_update_endpoint_updates_runtime(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_openai_compat_models",
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
        "_fetch_openai_compat_models",
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

    def _fake_reset_stt_provider_runtime(*, restart_warmup: bool = True) -> None:
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
    assert called["value"] is True


def test_embedding_status_endpoint_openai_compat_ready(monkeypatch, auth_none_settings) -> None:
    class _Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"data": [{"id": "nomic-embed-text"}, {"id": "llama3.1:8b"}]}

    monkeypatch.setattr(llm_router.requests, "get", lambda *args, **kwargs: _Resp())

    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["vector_enabled"] is True
    assert body["available"] is True
    assert body["provider"] in {"ollama_openai_compat", "openai_compat"}
    assert body["model_id"] == "nomic-embed-text"


def test_embedding_models_endpoint_returns_models(monkeypatch, auth_none_settings) -> None:
    class _Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "data": [
                    {"id": "nomic-embed-text"},
                    {"id": "mxbai-embed-large"},
                ]
            }

    monkeypatch.setattr(llm_router.requests, "get", lambda *args, **kwargs: _Resp())

    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["current_model"] == "nomic-embed-text"
    assert "mxbai-embed-large" in body["models"]


def test_embedding_models_endpoint_filters_out_chat_models(monkeypatch, auth_none_settings) -> None:
    class _Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "data": [
                    {"id": "llama3.1:8b"},
                    {"id": "nomic-embed-text"},
                    {"id": "qwen2.5:7b"},
                ]
            }

    monkeypatch.setattr(llm_router.requests, "get", lambda *args, **kwargs: _Resp())

    client = TestClient(app)
    resp = client.get("/v1/llm/embeddings/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == ["nomic-embed-text"]


def test_embedding_model_update_endpoint_updates_runtime(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        llm_router,
        "_fetch_openai_compat_models",
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

    monkeypatch.setattr(llm_router, "_fetch_openai_compat_models", _fake_fetch)
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
