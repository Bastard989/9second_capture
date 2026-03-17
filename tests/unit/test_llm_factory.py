from __future__ import annotations

import pytest

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.llm.anthropic import AnthropicProvider
from interview_analytics_agent.llm.factory import build_llm_provider
from interview_analytics_agent.llm.gemini import GeminiProvider
from interview_analytics_agent.llm.mock import MockLLMProvider
from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider


@pytest.fixture()
def llm_provider_state():
    s = get_settings()
    snapshot = {
        "llm_provider": s.llm_provider,
        "llm_api_base": s.llm_api_base,
        "llm_api_key": s.llm_api_key,
        "openai_api_base": s.openai_api_base,
        "openai_api_key": s.openai_api_key,
        "llm_model_id": s.llm_model_id,
        "llm_request_timeout_sec": s.llm_request_timeout_sec,
        "llm_max_tokens": s.llm_max_tokens,
    }
    try:
        yield s
    finally:
        for key, value in snapshot.items():
            setattr(s, key, value)


def test_build_llm_provider_returns_openai_compat_provider(llm_provider_state) -> None:
    s = llm_provider_state
    s.llm_provider = "openai_compat"
    s.llm_api_base = "http://127.0.0.1:11434/v1"
    s.llm_api_key = "ollama"
    s.llm_model_id = "llama3.1:8b"

    provider = build_llm_provider(s)

    assert isinstance(provider, OpenAICompatProvider)


def test_build_llm_provider_returns_openai_provider(llm_provider_state) -> None:
    s = llm_provider_state
    s.llm_provider = "openai"
    s.llm_api_base = "https://api.openai.com/v1"
    s.llm_api_key = "sk-test"
    s.llm_model_id = "gpt-4.1-mini"

    provider = build_llm_provider(s)

    assert isinstance(provider, OpenAICompatProvider)


def test_build_llm_provider_returns_anthropic_provider(llm_provider_state) -> None:
    s = llm_provider_state
    s.llm_provider = "anthropic"
    s.llm_api_base = "https://api.anthropic.com/v1"
    s.llm_api_key = "anthropic-test"
    s.llm_model_id = "claude-3-5-sonnet-latest"

    provider = build_llm_provider(s)

    assert isinstance(provider, AnthropicProvider)


def test_build_llm_provider_returns_gemini_provider(llm_provider_state) -> None:
    s = llm_provider_state
    s.llm_provider = "gemini"
    s.llm_api_base = "https://generativelanguage.googleapis.com/v1beta"
    s.llm_api_key = "gemini-test"
    s.llm_model_id = "gemini-2.0-flash"

    provider = build_llm_provider(s)

    assert isinstance(provider, GeminiProvider)


def test_build_llm_provider_returns_mock_provider(llm_provider_state) -> None:
    s = llm_provider_state
    s.llm_provider = "mock"
    s.llm_api_base = None
    s.llm_api_key = None
    s.llm_model_id = ""

    provider = build_llm_provider(s)

    assert isinstance(provider, MockLLMProvider)

