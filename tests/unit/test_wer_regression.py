from __future__ import annotations

import json
from pathlib import Path

from interview_analytics_agent.processing.wer import evaluate_wer_cases


def test_stt_wer_regression_cases_guardrail() -> None:
    cases_path = Path(__file__).resolve().parents[1] / "fixtures" / "stt_wer_regression_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))

    results = evaluate_wer_cases(cases)
    assert results, "WER regression suite is empty"

    failed = [item for item in results if not item.passed]
    assert not failed, (
        "WER regression failed: "
        + ", ".join(f"{item.case_id}={item.wer:.3f}>{item.max_wer:.3f}" for item in failed)
    )

    avg_wer = sum(item.wer for item in results) / float(len(results))
    assert avg_wer <= 0.2, f"Average WER is too high: {avg_wer:.3f}"

