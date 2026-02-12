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
    snapshot_api_base = s.openai_api_base
    snapshot_api_key = s.openai_api_key
    snapshot_env_model = os.environ.get("LLM_MODEL_ID")
    try:
        s.auth_mode = "none"
        s.llm_enabled = True
        s.llm_live_enabled = False
        s.llm_model_id = "llama3.1:8b"
        s.openai_api_base = "http://127.0.0.1:11434/v1"
        s.openai_api_key = "ollama"
        yield s
    finally:
        s.auth_mode = snapshot_auth
        s.llm_enabled = snapshot_llm_enabled
        s.llm_live_enabled = snapshot_llm_live_enabled
        s.llm_model_id = snapshot_model
        s.openai_api_base = snapshot_api_base
        s.openai_api_key = snapshot_api_key
        if snapshot_env_model is None:
            os.environ.pop("LLM_MODEL_ID", None)
        else:
            os.environ["LLM_MODEL_ID"] = snapshot_env_model


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


def test_llm_model_update_endpoint_updates_runtime(auth_none_settings) -> None:
    client = TestClient(app)
    resp = client.post("/v1/llm/model", json={"model_id": "qwen2.5:14b"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["model_id"] == "qwen2.5:14b"
    s = get_settings()
    assert s.llm_model_id == "qwen2.5:14b"
    assert os.environ.get("LLM_MODEL_ID") == "qwen2.5:14b"
