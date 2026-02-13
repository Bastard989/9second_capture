from __future__ import annotations

from interview_analytics_agent.processing import structured


def test_build_structured_rows_fallback_when_llm_disabled(monkeypatch) -> None:
    class Settings:
        llm_enabled = False

    monkeypatch.setattr(structured, "get_settings", lambda: Settings())

    result = structured.build_structured_rows(
        meeting_id="m1",
        source="raw",
        transcript=(
            "mic: hello team, let's review blockers and finalize ownership today\n"
            "candidate: agreed, I will prepare update and send the summary after standup"
        ),
        report={"summary": "standup"},
    )

    assert result["schema_version"] == "v1"
    assert result["status"] == "ok"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["speaker_name"] == "mic"
    assert result["rows"][0]["text"] == "hello team, let's review blockers and finalize ownership today"


def test_build_structured_rows_reports_insufficient_data(monkeypatch) -> None:
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

    assert result["status"] == "insufficient_data"
    assert "Недостаточно данных" in result["message"]
    assert len(result["rows"]) == 1
    assert result["rows"][0]["status"] == "insufficient_data"
