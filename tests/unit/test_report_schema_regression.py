from __future__ import annotations

from interview_analytics_agent.processing import analytics


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "objective",
    "summary",
    "bullets",
    "risk_flags",
    "recommendation",
    "decision",
    "scorecard",
    "overall_score",
    "highlights",
    "data_quality",
    "meeting_context",
}


def _assert_report_shape(report: dict) -> None:
    missing = [key for key in REQUIRED_TOP_LEVEL if key not in report]
    assert not missing, f"missing top-level keys: {missing}"
    assert report["schema_version"] == analytics.REPORT_SCHEMA_VERSION
    assert report["objective"] == analytics.REPORT_OBJECTIVE
    assert isinstance(report["scorecard"], list)
    assert len(report["scorecard"]) == 4

    decision = report.get("decision") or {}
    assert decision.get("status") in analytics.DECISION_STATUSES
    assert isinstance(float(decision.get("confidence") or 0.0), float)

    dq = report.get("data_quality") or {}
    for field in [
        "transcript_quality",
        "line_count",
        "speaker_turns",
        "question_count",
        "char_count",
        "token_count",
        "comparable",
        "calibration_profile",
    ]:
        assert field in dq, f"data_quality.{field} is missing"


def test_report_schema_regression_fallback(monkeypatch) -> None:
    class Settings:
        llm_enabled = False

    monkeypatch.setattr(analytics, "get_settings", lambda: Settings())
    report = analytics.build_report(
        enhanced_transcript="interviewer: tell me about your design decisions\ncandidate: I focused on reliability",
        meeting_context={"level": "senior"},
    )
    _assert_report_shape(report)


def test_report_schema_regression_llm_normalized(monkeypatch) -> None:
    class Settings:
        llm_enabled = True

    class Orch:
        def complete_json(self, *, system: str, user: str) -> dict:
            return {
                "summary": "Candidate showed strong architecture skills.",
                "bullets": ["Clear tradeoff analysis", "Explained migration plan"],
                "risk_flags": [],
                "recommendation": "lean yes",
                "decision": {"status": "lean_yes", "confidence": 0.71, "reason": "Good signal"},
                "scorecard": [
                    {"dimension": "technical_depth", "score": 4},
                    {"dimension": "problem_solving", "score": 4},
                    {"dimension": "communication", "score": 3},
                    {"dimension": "ownership", "score": 4},
                ],
                "highlights": {
                    "strengths": ["Solid architecture choices"],
                    "concerns": ["Needs deeper benchmarking examples"],
                    "follow_up_questions": ["How to measure rollback safety?"],
                },
                "data_quality": {"notes": "Sufficient transcript coverage."},
            }

    monkeypatch.setattr(analytics, "get_settings", lambda: Settings())
    monkeypatch.setattr(analytics, "_build_orchestrator", lambda: Orch())

    report = analytics.build_report(
        enhanced_transcript=(
            "interviewer: explain tradeoffs\n"
            "candidate: I would start with monolith and split by domains once load grows"
        ),
        meeting_context={"level": "middle"},
    )
    _assert_report_shape(report)
