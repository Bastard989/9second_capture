from __future__ import annotations

import pytest

from interview_analytics_agent.common.errors import ProviderError
from interview_analytics_agent.llm import openai_compat


def test_openai_compat_uses_default_local_key(monkeypatch) -> None:
    class Settings:
        openai_api_base = "http://127.0.0.1:11434/v1"
        openai_api_key = ""
        llm_model_id = "llama3.1:8b"
        llm_request_timeout_sec = 15

    monkeypatch.setattr(openai_compat, "get_settings", lambda: Settings())
    provider = openai_compat.OpenAICompatProvider()
    assert provider.cfg.api_key == "ollama"
    assert provider.cfg.api_base == "http://127.0.0.1:11434/v1"


def test_openai_compat_requires_key_for_remote_endpoint(monkeypatch) -> None:
    class Settings:
        openai_api_base = "https://api.example.com/v1"
        openai_api_key = ""
        llm_model_id = "gpt-4o-mini"
        llm_request_timeout_sec = 15

    monkeypatch.setattr(openai_compat, "get_settings", lambda: Settings())
    with pytest.raises(ProviderError):
        openai_compat.OpenAICompatProvider()


def test_openai_compat_is_available_true(monkeypatch) -> None:
    class Settings:
        openai_api_base = "http://127.0.0.1:11434/v1"
        openai_api_key = ""
        llm_model_id = "llama3.1:8b"
        llm_request_timeout_sec = 15

    class Resp:
        status_code = 200

    monkeypatch.setattr(openai_compat, "get_settings", lambda: Settings())
    monkeypatch.setattr(openai_compat.requests, "get", lambda *args, **kwargs: Resp())
    provider = openai_compat.OpenAICompatProvider()
    assert provider.is_available(timeout_s=1.2) is True


def test_openai_compat_is_available_false_on_error(monkeypatch) -> None:
    class Settings:
        openai_api_base = "http://127.0.0.1:11434/v1"
        openai_api_key = ""
        llm_model_id = "llama3.1:8b"
        llm_request_timeout_sec = 15

    monkeypatch.setattr(openai_compat, "get_settings", lambda: Settings())

    def _raise(*args, **kwargs):
        raise openai_compat.requests.RequestException("boom")

    monkeypatch.setattr(openai_compat.requests, "get", _raise)
    provider = openai_compat.OpenAICompatProvider()
    assert provider.is_available(timeout_s=1.2) is False
