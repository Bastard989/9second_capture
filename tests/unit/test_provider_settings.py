from __future__ import annotations

import pytest

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.provider_settings import (
    resolve_embedding_endpoint,
    resolve_embedding_provider,
    resolve_llm_endpoint,
    resolve_llm_provider,
    resolve_stt_model_id,
)


@pytest.fixture()
def provider_settings_state():
    s = get_settings()
    snapshot = {
        "llm_provider": s.llm_provider,
        "llm_api_base": s.llm_api_base,
        "llm_api_key": s.llm_api_key,
        "openai_api_base": s.openai_api_base,
        "openai_api_key": s.openai_api_key,
        "llm_model_id": s.llm_model_id,
        "embedding_provider": s.embedding_provider,
        "embedding_api_base": s.embedding_api_base,
        "embedding_api_key": s.embedding_api_key,
        "embedding_model_id": s.embedding_model_id,
        "rag_embedding_provider": s.rag_embedding_provider,
        "stt_provider": s.stt_provider,
        "stt_model_id": s.stt_model_id,
        "whisper_model_size": s.whisper_model_size,
    }
    try:
        yield s
    finally:
        for key, value in snapshot.items():
            setattr(s, key, value)


def test_resolve_llm_endpoint_for_native_openai(provider_settings_state) -> None:
    s = provider_settings_state
    s.llm_provider = "openai"
    s.llm_api_base = ""
    s.llm_api_key = "sk-test"
    s.openai_api_base = None
    s.openai_api_key = None
    s.llm_model_id = "gpt-4.1-mini"

    endpoint = resolve_llm_endpoint(s)

    assert resolve_llm_provider(s) == "openai"
    assert endpoint.api_base == "https://api.openai.com/v1"
    assert endpoint.api_key == "sk-test"
    assert endpoint.model_id == "gpt-4.1-mini"


def test_embedding_auto_follows_native_openai(provider_settings_state) -> None:
    s = provider_settings_state
    s.llm_provider = "openai"
    s.llm_api_base = "https://api.openai.com/v1"
    s.llm_api_key = "sk-test"
    s.llm_model_id = "gpt-4.1-mini"
    s.embedding_provider = "auto"
    s.embedding_api_base = None
    s.embedding_api_key = None
    s.embedding_model_id = "text-embedding-3-large"

    endpoint = resolve_embedding_endpoint(s)

    assert resolve_embedding_provider(s) == "openai"
    assert endpoint.api_base == "https://api.openai.com/v1"
    assert endpoint.api_key == "sk-test"
    assert endpoint.model_id == "text-embedding-3-large"


def test_embedding_auto_falls_back_to_hashing_without_remote_config(provider_settings_state) -> None:
    s = provider_settings_state
    s.llm_provider = "mock"
    s.llm_api_base = None
    s.llm_api_key = None
    s.openai_api_base = None
    s.openai_api_key = None
    s.llm_model_id = ""
    s.embedding_provider = "auto"
    s.embedding_api_base = None
    s.embedding_api_key = None

    endpoint = resolve_embedding_endpoint(s)

    assert resolve_embedding_provider(s) == "hashing"
    assert endpoint.provider == "hashing"
    assert endpoint.api_base == ""


def test_resolve_stt_model_id_uses_explicit_model_for_non_whisper(provider_settings_state) -> None:
    s = provider_settings_state
    s.stt_provider = "google"
    s.stt_model_id = "chirp-2"
    s.whisper_model_size = "medium"

    assert resolve_stt_model_id(s) == "chirp-2"

