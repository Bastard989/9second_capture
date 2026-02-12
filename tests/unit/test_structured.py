from __future__ import annotations

from interview_analytics_agent.processing import structured


def test_build_structured_rows_fallback_when_llm_disabled(monkeypatch) -> None:
    class Settings:
        llm_enabled = False

    monkeypatch.setattr(structured, "get_settings", lambda: Settings())

    result = structured.build_structured_rows(
        meeting_id="m1",
        source="raw",
        transcript="mic: hello\ncandidate: answer",
        report={"summary": "standup"},
    )

    assert result["schema_version"] == "v1"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["speaker_name"] == "mic"
    assert result["rows"][0]["text"] == "hello"


def test_build_structured_rows_fallback_when_llm_returns_empty_rows(monkeypatch) -> None:
    class Settings:
        llm_enabled = True

    class Orch:
        def complete_json(self, *, system: str, user: str) -> dict:
            return {"schema_version": "v1", "columns": [], "rows": []}

    monkeypatch.setattr(structured, "get_settings", lambda: Settings())
    monkeypatch.setattr(structured, "_build_orchestrator", lambda: Orch())

    result = structured.build_structured_rows(
        meeting_id="m2",
        source="clean",
        transcript="speaker: some text",
        report=None,
    )

    assert len(result["rows"]) == 1
    assert result["rows"][0]["text"] == "some text"
