from __future__ import annotations

from interview_analytics_agent.processing import enhancer


def _settings_stub():
    class Settings:
        llm_enabled = True
        llm_transcript_cleanup_enabled = True
        openai_api_base = "http://127.0.0.1:11434/v1"
        openai_api_key = "ollama"
        llm_cleanup_probe_timeout_sec = 1.6

    return Settings()


def test_build_cleanup_orchestrator_skips_when_provider_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(enhancer, "get_settings", _settings_stub)

    class ProviderUnavailable:
        def is_available(self, timeout_s: float = 2.5) -> bool:
            return False

    monkeypatch.setattr(
        "interview_analytics_agent.llm.openai_compat.OpenAICompatProvider",
        ProviderUnavailable,
    )
    monkeypatch.setattr(
        "interview_analytics_agent.llm.orchestrator.LLMOrchestrator",
        lambda provider: {"provider": provider},
    )

    assert enhancer._build_transcript_cleanup_orchestrator() is None


def test_build_cleanup_orchestrator_uses_provider_when_available(monkeypatch) -> None:
    monkeypatch.setattr(enhancer, "get_settings", _settings_stub)
    captured: dict[str, float] = {}

    class ProviderAvailable:
        def is_available(self, timeout_s: float = 2.5) -> bool:
            captured["timeout"] = timeout_s
            return True

    monkeypatch.setattr(
        "interview_analytics_agent.llm.openai_compat.OpenAICompatProvider",
        ProviderAvailable,
    )
    monkeypatch.setattr(
        "interview_analytics_agent.llm.orchestrator.LLMOrchestrator",
        lambda provider: {"provider": provider},
    )

    result = enhancer._build_transcript_cleanup_orchestrator()
    assert isinstance(result, dict)
    assert 1.0 <= float(captured.get("timeout", 0.0)) <= 2.8
