from __future__ import annotations

from dataclasses import dataclass

from interview_analytics_agent.common.config import Settings, get_settings


_OPENAI_BASE = "https://api.openai.com/v1"
_ANTHROPIC_BASE = "https://api.anthropic.com/v1"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

_LLM_PROVIDERS = {"mock", "openai_compat", "openai", "anthropic", "gemini"}
_EMBEDDING_PROVIDERS = {"auto", "hashing", "openai_compat", "openai", "gemini"}
_STT_PROVIDERS = {"mock", "whisper_local", "google", "salutespeech"}


@dataclass(frozen=True)
class ResolvedEndpoint:
    provider: str
    api_base: str
    api_key: str
    model_id: str


def _settings(value: Settings | None = None) -> Settings:
    return value or get_settings()


def normalize_llm_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in _LLM_PROVIDERS:
        return provider
    return "mock" if not provider else "openai_compat"


def normalize_embedding_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in _EMBEDDING_PROVIDERS:
        return provider
    return "auto"


def normalize_stt_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in _STT_PROVIDERS:
        return provider
    return "whisper_local"


def default_llm_api_base(provider: str) -> str:
    normalized = normalize_llm_provider(provider)
    if normalized == "openai":
        return _OPENAI_BASE
    if normalized == "anthropic":
        return _ANTHROPIC_BASE
    if normalized == "gemini":
        return _GEMINI_BASE
    return ""


def default_embedding_api_base(provider: str) -> str:
    normalized = normalize_embedding_provider(provider)
    if normalized == "openai":
        return _OPENAI_BASE
    if normalized == "gemini":
        return _GEMINI_BASE
    return ""


def resolve_llm_provider(settings: Settings | None = None) -> str:
    s = _settings(settings)
    explicit = normalize_llm_provider(getattr(s, "llm_provider", ""))
    if explicit != "mock" or str(getattr(s, "llm_provider", "") or "").strip():
        return explicit
    legacy_base = str(getattr(s, "openai_api_base", "") or "").strip()
    legacy_key = str(getattr(s, "openai_api_key", "") or "").strip()
    if legacy_base or legacy_key:
        return "openai_compat"
    return "mock"


def resolve_llm_endpoint(settings: Settings | None = None) -> ResolvedEndpoint:
    s = _settings(settings)
    provider = resolve_llm_provider(s)
    api_base = str(getattr(s, "llm_api_base", "") or "").strip()
    api_key = str(getattr(s, "llm_api_key", "") or "").strip()
    if not api_base:
        api_base = str(getattr(s, "openai_api_base", "") or "").strip()
    if not api_key:
        api_key = str(getattr(s, "openai_api_key", "") or "").strip()
    if not api_base:
        api_base = default_llm_api_base(provider)
    return ResolvedEndpoint(
        provider=provider,
        api_base=api_base,
        api_key=api_key,
        model_id=str(getattr(s, "llm_model_id", "") or "").strip(),
    )


def resolve_embedding_provider(settings: Settings | None = None) -> str:
    s = _settings(settings)
    raw = str(getattr(s, "embedding_provider", "") or "").strip()
    explicit = normalize_embedding_provider(raw)
    if raw and explicit != "auto":
        return explicit
    legacy = normalize_embedding_provider(getattr(s, "rag_embedding_provider", "auto"))
    if legacy in {"hashing", "openai_compat"}:
        return legacy
    endpoint = resolve_llm_endpoint(s)
    if endpoint.api_base and endpoint.model_id:
        if endpoint.provider == "openai":
            return "openai"
        if endpoint.provider == "gemini":
            return "gemini"
        return "openai_compat"
    return "hashing"


def resolve_embedding_endpoint(settings: Settings | None = None) -> ResolvedEndpoint:
    s = _settings(settings)
    provider = resolve_embedding_provider(s)
    api_base = str(getattr(s, "embedding_api_base", "") or "").strip()
    api_key = str(getattr(s, "embedding_api_key", "") or "").strip()
    if not api_base and provider in {"openai_compat", "openai"}:
        api_base = str(getattr(s, "llm_api_base", "") or getattr(s, "openai_api_base", "") or "").strip()
    if not api_key and provider in {"openai_compat", "openai"}:
        api_key = str(getattr(s, "llm_api_key", "") or getattr(s, "openai_api_key", "") or "").strip()
    if not api_base:
        api_base = default_embedding_api_base(provider)
    return ResolvedEndpoint(
        provider=provider,
        api_base=api_base,
        api_key=api_key,
        model_id=str(getattr(s, "embedding_model_id", "") or "").strip(),
    )


def resolve_stt_model_id(settings: Settings | None = None) -> str:
    s = _settings(settings)
    provider = normalize_stt_provider(getattr(s, "stt_provider", "whisper_local"))
    if provider == "whisper_local":
        return str(getattr(s, "whisper_model_size", "") or "").strip()
    value = str(getattr(s, "stt_model_id", "") or "").strip()
    return value


def provider_display_name(provider: str) -> str:
    normalized = str(provider or "").strip().lower()
    mapping = {
        "mock": "Mock",
        "openai_compat": "OpenAI-compatible",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "gemini": "Gemini",
        "hashing": "Hashing",
        "hashing_local": "Hashing (local)",
        "whisper_local": "Whisper local",
        "google": "Google STT",
        "salutespeech": "SaluteSpeech",
    }
    return mapping.get(normalized, normalized or "Unknown")
