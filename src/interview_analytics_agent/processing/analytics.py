"""
Аналитика интервью с упором на сравнимые отчёты для async-review сеньорами.

Цель формата:
- единая шкала компетенций (1..5)
- явный hiring signal + confidence
- оценка качества данных (чтобы не делать ложных выводов на слабом транскрипте)
"""

from __future__ import annotations

import re
from typing import Any

from interview_analytics_agent.common.config import get_settings


REPORT_SCHEMA_VERSION = "interview_report_v2"
REPORT_OBJECTIVE = "senior_async_review"
DECISION_STATUSES = {"strong_yes", "yes", "lean_yes", "lean_no", "no", "insufficient_data"}
RUBRIC_DIMENSIONS = (
    "technical_depth",
    "problem_solving",
    "communication",
    "ownership",
)
LEVEL_WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "junior": {
        "technical_depth": 0.25,
        "problem_solving": 0.3,
        "communication": 0.25,
        "ownership": 0.2,
    },
    "middle": {
        "technical_depth": 0.3,
        "problem_solving": 0.3,
        "communication": 0.2,
        "ownership": 0.2,
    },
    "senior": {
        "technical_depth": 0.35,
        "problem_solving": 0.25,
        "communication": 0.15,
        "ownership": 0.25,
    },
}

_SPEAKER_LINE_RE = re.compile(r"^[^:\n]{1,64}:\s+.+$")


def _build_orchestrator():
    """
    Ленивая сборка orchestrator, чтобы сервисы работали без LLM-зависимостей,
    пока LLM выключен.
    """
    s = get_settings()
    if not s.llm_enabled:
        return None

    from interview_analytics_agent.llm.mock import MockLLMProvider
    from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider
    from interview_analytics_agent.llm.orchestrator import LLMOrchestrator

    has_api_base = bool((s.openai_api_base or "").strip())
    has_api_key = bool((s.openai_api_key or "").strip())
    if not has_api_base and not has_api_key:
        return LLMOrchestrator(MockLLMProvider())

    return LLMOrchestrator(OpenAICompatProvider())


def _to_str_list(value: Any, *, limit: int = 8) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [value]
    else:
        items = []
    out: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        out.append(text[:280])
        if len(out) >= limit:
            break
    return out


def _clamp_score(value: Any, *, default: int = 3) -> int:
    try:
        raw = int(round(float(value)))
    except Exception:
        raw = default
    return max(1, min(5, raw))


def _clamp_confidence(value: Any, *, default: float = 0.5) -> float:
    try:
        raw = float(value)
    except Exception:
        raw = default
    return max(0.0, min(1.0, raw))


def _transcript_stats(text: str) -> dict[str, int]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    speaker_turns = sum(1 for line in lines if _SPEAKER_LINE_RE.match(line))
    question_count = sum(line.count("?") for line in lines)
    char_count = sum(len(line) for line in lines)
    token_count = sum(len(line.split()) for line in lines)

    return {
        "line_count": len(lines),
        "speaker_turns": speaker_turns,
        "question_count": question_count,
        "char_count": char_count,
        "token_count": token_count,
    }


def _quality_label(stats: dict[str, int]) -> str:
    chars = stats.get("char_count", 0)
    lines = stats.get("line_count", 0)
    turns = stats.get("speaker_turns", 0)
    if chars < 180 or lines < 4 or turns < 2:
        return "low"
    if chars < 900 or lines < 14 or turns < 6:
        return "medium"
    return "high"


def _scorecard_template(score: int = 3, confidence: float = 0.45) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for dim in RUBRIC_DIMENSIONS:
        items.append(
            {
                "dimension": dim,
                "score": _clamp_score(score),
                "evidence": [],
                "rationale": "",
                "confidence": _clamp_confidence(confidence),
            }
        )
    return items


def _normalized_level(meeting_context: dict[str, Any] | None) -> str:
    raw = str((meeting_context or {}).get("level") or "").strip().lower()
    if "senior" in raw:
        return "senior"
    if "middle" in raw or "mid" in raw:
        return "middle"
    if "junior" in raw or "jr" in raw:
        return "junior"
    return "middle"


def _weighted_overall_score(
    *,
    scorecard: list[dict[str, Any]],
    meeting_context: dict[str, Any] | None,
) -> float:
    level = _normalized_level(meeting_context)
    weights = LEVEL_WEIGHT_PROFILES.get(level) or LEVEL_WEIGHT_PROFILES["middle"]
    by_dim = {str(item.get("dimension") or ""): _clamp_score(item.get("score"), default=3) for item in scorecard}
    total = 0.0
    for dim in RUBRIC_DIMENSIONS:
        w = float(weights.get(dim, 0.0))
        total += float(by_dim.get(dim, 3)) * w
    return round(max(1.0, min(5.0, total)), 2)


def _decision_from_recommendation(recommendation: str, quality: str) -> str:
    rec = (recommendation or "").strip().lower()
    if quality == "low":
        return "insufficient_data"
    if any(word in rec for word in ("strong yes", "hire", "нанять")):
        return "yes"
    if any(word in rec for word in ("lean yes", "скорее да")):
        return "lean_yes"
    if any(word in rec for word in ("lean no", "скорее нет")):
        return "lean_no"
    if any(word in rec for word in ("reject", "no hire", "отклон")):
        return "no"
    return "insufficient_data" if quality == "low" else "lean_no"


def _default_report(
    *,
    enhanced_transcript: str,
    meeting_context: dict[str, Any] | None,
    summary: str,
    bullets: list[str],
    recommendation: str,
) -> dict[str, Any]:
    stats = _transcript_stats(enhanced_transcript)
    quality = _quality_label(stats)
    comparable = quality in {"medium", "high"} and stats["speaker_turns"] >= 4
    scorecard = _scorecard_template(
        score=2 if quality == "low" else 3,
        confidence=0.35 if quality == "low" else 0.45,
    )
    avg_score = _weighted_overall_score(scorecard=scorecard, meeting_context=meeting_context)
    decision_status = _decision_from_recommendation(recommendation, quality)

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "objective": REPORT_OBJECTIVE,
        "summary": summary,
        "bullets": bullets,
        "risk_flags": (
            ["insufficient_interview_evidence"] if quality == "low" else []
        ),
        "recommendation": recommendation,
        "decision": {
            "status": decision_status,
            "confidence": _clamp_confidence(0.28 if quality == "low" else 0.42),
            "reason": (
                "Low transcript coverage; decision should be validated by reviewer."
                if quality == "low"
                else "Fallback heuristic decision."
            ),
        },
        "scorecard": scorecard,
        "overall_score": round(avg_score, 2),
        "highlights": {
            "strengths": [],
            "concerns": [],
            "follow_up_questions": [],
        },
        "data_quality": {
            "transcript_quality": quality,
            "line_count": stats["line_count"],
            "speaker_turns": stats["speaker_turns"],
            "question_count": stats["question_count"],
            "char_count": stats["char_count"],
            "token_count": stats["token_count"],
            "comparable": comparable,
            "notes": "Fallback report without reliable interview evidence.",
            "calibration_profile": _normalized_level(meeting_context),
        },
        "meeting_context": meeting_context or {},
    }


def _normalize_scorecard(value: Any) -> list[dict[str, Any]]:
    result = {dim: {"dimension": dim, "score": 3, "evidence": [], "rationale": "", "confidence": 0.5} for dim in RUBRIC_DIMENSIONS}

    raw_items: list[Any] = []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, dict):
        for dim, raw in value.items():
            if isinstance(raw, dict):
                raw_items.append({"dimension": dim, **raw})
            else:
                raw_items.append({"dimension": dim, "score": raw})

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        dim = str(item.get("dimension") or "").strip().lower()
        if dim not in result:
            continue
        result[dim] = {
            "dimension": dim,
            "score": _clamp_score(item.get("score"), default=result[dim]["score"]),
            "evidence": _to_str_list(item.get("evidence"), limit=4),
            "rationale": str(item.get("rationale") or "").strip()[:400],
            "confidence": _clamp_confidence(item.get("confidence"), default=0.5),
        }

    return [result[dim] for dim in RUBRIC_DIMENSIONS]


def _normalize_llm_report(
    *,
    data: dict[str, Any],
    enhanced_transcript: str,
    meeting_context: dict[str, Any] | None,
) -> dict[str, Any]:
    stats = _transcript_stats(enhanced_transcript)
    quality = _quality_label(stats)
    comparable = quality in {"medium", "high"} and stats["speaker_turns"] >= 4

    summary = str(data.get("summary") or "").strip()
    if not summary:
        summary = "Interview summary is unavailable."

    bullets = _to_str_list(data.get("bullets"))
    risk_flags = _to_str_list(data.get("risk_flags"), limit=12)
    recommendation = str(data.get("recommendation") or "").strip()
    scorecard = _normalize_scorecard(data.get("scorecard"))
    avg_score = _weighted_overall_score(scorecard=scorecard, meeting_context=meeting_context)

    raw_decision = data.get("decision") if isinstance(data.get("decision"), dict) else {}
    status = str(raw_decision.get("status") or "").strip().lower()
    if status not in DECISION_STATUSES:
        status = _decision_from_recommendation(recommendation, quality)
    if quality == "low":
        status = "insufficient_data"
    decision_confidence = _clamp_confidence(
        raw_decision.get("confidence"),
        default=0.62 if quality != "low" else 0.3,
    )
    if quality == "low":
        decision_confidence = min(decision_confidence, 0.35)

    highlights = data.get("highlights") if isinstance(data.get("highlights"), dict) else {}
    strengths = _to_str_list(highlights.get("strengths"), limit=6)
    concerns = _to_str_list(highlights.get("concerns"), limit=6)
    follow_up = _to_str_list(highlights.get("follow_up_questions"), limit=8)

    notes_from_llm = ""
    raw_quality = data.get("data_quality")
    if isinstance(raw_quality, dict):
        notes_from_llm = str(raw_quality.get("notes") or "").strip()[:280]

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "objective": REPORT_OBJECTIVE,
        "summary": summary,
        "bullets": bullets,
        "risk_flags": risk_flags,
        "recommendation": recommendation,
        "decision": {
            "status": status,
            "confidence": decision_confidence,
            "reason": str(raw_decision.get("reason") or "").strip()[:500],
        },
        "scorecard": scorecard,
        "overall_score": round(avg_score, 2),
        "highlights": {
            "strengths": strengths,
            "concerns": concerns,
            "follow_up_questions": follow_up,
        },
        "data_quality": {
            "transcript_quality": quality,
            "line_count": stats["line_count"],
            "speaker_turns": stats["speaker_turns"],
            "question_count": stats["question_count"],
            "char_count": stats["char_count"],
            "token_count": stats["token_count"],
            "comparable": comparable,
            "notes": notes_from_llm,
            "calibration_profile": _normalized_level(meeting_context),
        },
        "meeting_context": meeting_context or {},
    }


def build_report(*, enhanced_transcript: str, meeting_context: dict) -> dict[str, Any]:
    """
    Сборка отчёта по интервью в сравнимом формате.
    """
    s = get_settings()
    text = (enhanced_transcript or "").strip()
    fallback_disabled = _default_report(
        enhanced_transcript=text,
        meeting_context=meeting_context,
        summary="LLM disabled; basic report",
        bullets=["Pipeline OK", "LLM enrichment disabled"],
        recommendation="insufficient_data",
    )

    if not s.llm_enabled:
        return fallback_disabled

    try:
        orch = _build_orchestrator()
    except Exception:
        return _default_report(
            enhanced_transcript=text,
            meeting_context=meeting_context,
            summary="LLM unavailable; basic report",
            bullets=["Pipeline OK", "LLM unavailable"],
            recommendation="insufficient_data",
        )
    if orch is None:
        return _default_report(
            enhanced_transcript=text,
            meeting_context=meeting_context,
            summary="LLM unavailable; basic report",
            bullets=["Pipeline OK", "LLM unavailable"],
            recommendation="insufficient_data",
        )

    system = (
        "Ты старший интервью-аналитик. Верни ТОЛЬКО валидный JSON. "
        "Схема: "
        "{"
        "summary: str, "
        "bullets: [str], "
        "risk_flags: [str], "
        "recommendation: str, "
        "decision: {status: str, confidence: number, reason: str}, "
        "scorecard: ["
        "{dimension:'technical_depth'|'problem_solving'|'communication'|'ownership', score:1..5, evidence:[str], rationale:str, confidence:number}"
        "], "
        "highlights: {strengths:[str], concerns:[str], follow_up_questions:[str]}, "
        "data_quality: {notes:str}"
        "}. "
        "Обязательно: не выдумывай факты, опирайся только на транскрипт; "
        "если данных мало, ставь decision.status='insufficient_data' и снижай confidence."
    )
    user = (
        f"meeting_context: {meeting_context or {}}\n\n"
        "transcript:\n"
        f"{text}\n"
    )

    try:
        data = orch.complete_json(system=system, user=user)
    except Exception:
        return _default_report(
            enhanced_transcript=text,
            meeting_context=meeting_context,
            summary="LLM unavailable; basic report",
            bullets=["Pipeline OK", "LLM unavailable"],
            recommendation="insufficient_data",
        )

    if not isinstance(data, dict):
        return _default_report(
            enhanced_transcript=text,
            meeting_context=meeting_context,
            summary="LLM returned invalid data; basic report",
            bullets=["Pipeline OK", "Invalid LLM response"],
            recommendation="insufficient_data",
        )

    return _normalize_llm_report(
        data=data,
        enhanced_transcript=text,
        meeting_context=meeting_context,
    )


def report_to_text(report: dict[str, Any]) -> str:
    lines: list[str] = []

    summary = str(report.get("summary") or "").strip()
    if summary:
        lines.append(summary)

    overall_score = report.get("overall_score")
    if overall_score is not None:
        lines.append("")
        lines.append(f"Overall score: {overall_score}/5")

    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    if decision:
        lines.append(
            "Decision: "
            f"{str(decision.get('status') or '').strip()} "
            f"(confidence={_clamp_confidence(decision.get('confidence'), default=0.0):.2f})"
        )
        reason = str(decision.get("reason") or "").strip()
        if reason:
            lines.append(f"Reason: {reason}")

    scorecard = report.get("scorecard") if isinstance(report.get("scorecard"), list) else []
    if scorecard:
        lines.append("")
        lines.append("Scorecard:")
        for item in scorecard:
            if not isinstance(item, dict):
                continue
            dim = str(item.get("dimension") or "").strip()
            score = _clamp_score(item.get("score"), default=3)
            conf = _clamp_confidence(item.get("confidence"), default=0.5)
            lines.append(f"- {dim}: {score}/5 (confidence={conf:.2f})")
            rationale = str(item.get("rationale") or "").strip()
            if rationale:
                lines.append(f"  rationale: {rationale}")

    bullets = _to_str_list(report.get("bullets"))
    if bullets:
        lines.append("")
        lines.append("Bullets:")
        lines.extend([f"- {b}" for b in bullets])

    risk_flags = _to_str_list(report.get("risk_flags"), limit=12)
    if risk_flags:
        lines.append("")
        lines.append("Risk flags:")
        lines.extend([f"- {r}" for r in risk_flags])

    highlights = report.get("highlights") if isinstance(report.get("highlights"), dict) else {}
    strengths = _to_str_list(highlights.get("strengths"), limit=6)
    concerns = _to_str_list(highlights.get("concerns"), limit=6)
    follow_up = _to_str_list(highlights.get("follow_up_questions"), limit=8)

    if strengths:
        lines.append("")
        lines.append("Strengths:")
        lines.extend([f"- {item}" for item in strengths])
    if concerns:
        lines.append("")
        lines.append("Concerns:")
        lines.extend([f"- {item}" for item in concerns])
    if follow_up:
        lines.append("")
        lines.append("Follow-up questions:")
        lines.extend([f"- {item}" for item in follow_up])

    quality = report.get("data_quality") if isinstance(report.get("data_quality"), dict) else {}
    if quality:
        lines.append("")
        lines.append(
            "Data quality: "
            f"{str(quality.get('transcript_quality') or '').strip()} "
            f"(comparable={bool(quality.get('comparable', False))})"
        )
        lines.append(
            "Coverage: "
            f"lines={int(quality.get('line_count') or 0)}, "
            f"turns={int(quality.get('speaker_turns') or 0)}, "
            f"chars={int(quality.get('char_count') or 0)}"
        )
        notes = str(quality.get("notes") or "").strip()
        if notes:
            lines.append(f"Notes: {notes}")

    recommendation = str(report.get("recommendation") or "").strip()
    if recommendation:
        lines.append("")
        lines.append("Recommendation:")
        lines.append(recommendation)

    return "\n".join(lines).strip() + "\n"
