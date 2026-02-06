from __future__ import annotations

import csv
import io
from typing import Any

from interview_analytics_agent.common.config import get_settings


STRUCTURED_COLUMNS = [
    "meeting_id",
    "source",
    "segment_seq",
    "speaker_name",
    "speaker_role",
    "addressed_to",
    "proxy_for",
    "text",
    "clean_text",
    "topic",
    "intent",
    "sentiment",
    "action_item",
    "action_owner",
    "action_due_date",
    "action_priority",
    "decision",
    "decision_owner",
    "decision_deadline",
    "risk",
    "risk_severity",
    "question",
    "answer_summary",
    "filler_words",
    "keywords",
    "project",
    "metric_name",
    "metric_value",
    "timestamp",
]


def _build_orchestrator():
    s = get_settings()
    if not s.llm_enabled:
        return None

    from interview_analytics_agent.llm.mock import MockLLMProvider
    from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider
    from interview_analytics_agent.llm.orchestrator import LLMOrchestrator

    if not (s.openai_api_key or ""):
        return LLMOrchestrator(MockLLMProvider())
    return LLMOrchestrator(OpenAICompatProvider())


def build_structured_rows(
    *,
    meeting_id: str,
    source: str,
    transcript: str,
    report: dict | None,
) -> dict[str, Any]:
    s = get_settings()

    if not s.llm_enabled:
        return {"schema_version": "v1", "columns": STRUCTURED_COLUMNS, "rows": []}

    orch = _build_orchestrator()
    if orch is None:
        return {"schema_version": "v1", "columns": STRUCTURED_COLUMNS, "rows": []}

    system = (
        "Ты аналитик встреч. Верни ТОЛЬКО валидный JSON с ключами "
        "{schema_version:'v1', columns:[...], rows:[{...}]}."
        " columns должны строго совпадать со списком, который я дам."
        " В rows каждая строка — объект с этими полями. Если данных нет — оставь пустую строку."
        " Не выдумывай имена говорящих без явного контекста."
        " Если спикер отвечает за отсутствующего (например: 'Кирилла нет, отвечу за него'), "
        "заполняй proxy_for именем отсутствующего."
        " addressed_to используй для вопросов по имени."
    )
    user = (
        f"meeting_id: {meeting_id}\n"
        f"source: {source}\n"
        f"columns: {STRUCTURED_COLUMNS}\n"
        f"report: {report or {}}\n"
        "transcript:\n"
        f"{transcript}\n"
    )

    data = orch.complete_json(system=system, user=user)
    rows = data.get("rows", []) or []
    return {
        "schema_version": "v1",
        "columns": STRUCTURED_COLUMNS,
        "rows": rows,
    }


def structured_to_csv(structured: dict[str, Any]) -> bytes:
    columns = structured.get("columns") or STRUCTURED_COLUMNS
    rows = structured.get("rows") or []
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return output.getvalue().encode("utf-8")
