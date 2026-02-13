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
    assert report["schema_version"] == "interview_report_v2"
    assert isinstance(report.get("scorecard"), list)
    assert len(report["scorecard"]) == 4


def test_build_report_fallback_when_llm_disabled(monkeypatch) -> None:
    class Settings:
        llm_enabled = False

    monkeypatch.setattr(analytics, "get_settings", lambda: Settings())

    report = analytics.build_report(
        enhanced_transcript="interviewer: hello\ncandidate: hi",
        meeting_context={"source": "clean"},
    )
    assert report["schema_version"] == "interview_report_v2"
    assert report["objective"] == "senior_async_review"
    assert report["decision"]["status"] in {
        "strong_yes",
        "yes",
        "lean_yes",
        "lean_no",
        "no",
        "insufficient_data",
    }
    assert len(report["scorecard"]) == 4


def test_build_report_normalizes_llm_scorecard(monkeypatch) -> None:
    class Settings:
        llm_enabled = True

    class Orch:
        def complete_json(self, *, system: str, user: str) -> dict:
            return {
                "summary": "Candidate handled most questions with moderate depth.",
                "bullets": ["Strong communication", "Needs deeper systems design"],
                "recommendation": "lean yes",
                "decision": {"status": "lean_yes", "confidence": 1.6},
                "scorecard": [
                    {"dimension": "technical_depth", "score": 6, "confidence": -1},
                    {"dimension": "communication", "score": 4},
                ],
            }

    monkeypatch.setattr(analytics, "get_settings", lambda: Settings())
    monkeypatch.setattr(analytics, "_build_orchestrator", lambda: Orch())

    report = analytics.build_report(
        enhanced_transcript=(
            "interviewer: walk me through architecture\n"
            "candidate: we use service boundaries, async queues, and idempotent consumers in critical paths\n"
            "interviewer: what about scaling?\n"
            "candidate: horizontal scaling with backpressure, retries, and load shedding at the edge\n"
            "interviewer: how do you debug incidents in production?\n"
            "candidate: we use tracing, structured logs, and postmortems with concrete follow-up actions"
        ),
        meeting_context={"source": "clean"},
    )

    scorecard = report["scorecard"]
    assert len(scorecard) == 4
    by_dim = {item["dimension"]: item for item in scorecard}
    assert by_dim["technical_depth"]["score"] == 5
    assert by_dim["technical_depth"]["confidence"] == 0.0
    assert by_dim["communication"]["score"] == 4
    assert report["decision"]["confidence"] == 1.0
    assert report["overall_score"] >= 1.0


def test_report_to_text_contains_comparable_sections() -> None:
    report = {
        "summary": "Candidate is promising for backend role.",
        "overall_score": 3.75,
        "decision": {"status": "lean_yes", "confidence": 0.64, "reason": "Good signal."},
        "scorecard": [
            {"dimension": "technical_depth", "score": 4, "confidence": 0.7, "rationale": "Solid fundamentals."},
            {"dimension": "problem_solving", "score": 4, "confidence": 0.6, "rationale": ""},
            {"dimension": "communication", "score": 4, "confidence": 0.7, "rationale": ""},
            {"dimension": "ownership", "score": 3, "confidence": 0.5, "rationale": ""},
        ],
        "data_quality": {"transcript_quality": "medium", "comparable": True, "line_count": 12, "speaker_turns": 8, "char_count": 520},
    }

    text = analytics.report_to_text(report)
    assert "Overall score: 3.75/5" in text
    assert "Scorecard:" in text
    assert "Data quality:" in text
