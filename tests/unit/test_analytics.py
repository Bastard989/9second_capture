from __future__ import annotations

from interview_analytics_agent.processing import analytics


def test_build_report_fallback_when_llm_call_fails(monkeypatch) -> None:
    class Settings:
        llm_enabled = True

    class BrokenOrchestrator:
        def complete_json(self, *, system: str, user: str) -> dict:
            raise RuntimeError("provider_down")

    monkeypatch.setattr(analytics, "get_settings", lambda: Settings())
    monkeypatch.setattr(analytics, "_build_orchestrator", lambda: BrokenOrchestrator())

    report = analytics.build_report(enhanced_transcript="test", meeting_context={})
    assert report["summary"] == "LLM unavailable; basic report"
    assert "Pipeline OK" in report["bullets"]
