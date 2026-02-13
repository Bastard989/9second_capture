from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timezone
from typing import Any

from interview_analytics_agent.common.config import get_settings

log = logging.getLogger(__name__)


STRUCTURED_COLUMNS = [
    "meeting_id",
    "source",
    "meeting_title",
    "meeting_type",
    "meeting_date",
    "language",
    "source_mode",
    "segment_seq",
    "segment_start_ms",
    "segment_end_ms",
    "segment_duration_ms",
    "speaker_id",
    "speaker_name",
    "speaker_role",
    "speaker_team",
    "speaker_email",
    "addressed_to",
    "proxy_for",
    "text",
    "clean_text",
    "filler_words",
    "topic",
    "topic_tags",
    "intent",
    "sentiment",
    "sentiment_score",
    "emotion",
    "action_item",
    "action_owner",
    "action_due_date",
    "action_priority",
    "action_status",
    "decision",
    "decision_owner",
    "decision_deadline",
    "decision_reason",
    "risk",
    "risk_severity",
    "risk_owner",
    "blocker",
    "next_step",
    "question",
    "answer_summary",
    "keywords",
    "project",
    "project_code",
    "ticket_id",
    "metric_name",
    "metric_value",
    "metric_delta",
    "status",
    "confidence",
    "timestamp",
]


_SPEAKER_LINE_RE = re.compile(r"^([^:\n]{1,64}):\s*(.+)$")
_MIN_STRUCTURED_CHARS = 48
_MIN_STRUCTURED_LINES = 2


def _speaker_id_from_name(name: str) -> str:
    normalized = re.sub(r"[^0-9a-z]+", "_", (name or "").strip().lower())
    return normalized.strip("_")[:48]


def _build_fallback_rows(
    *,
    meeting_id: str,
    source: str,
    transcript: str,
    report: dict | None,
) -> list[dict[str, Any]]:
    lines = [line.strip() for line in (transcript or "").splitlines() if line.strip()]
    if not lines:
        return []

    summary = ""
    if isinstance(report, dict):
        summary = str(report.get("summary") or "").strip()
    topic = summary[:160] if summary else ""
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    rows: list[dict[str, Any]] = []
    for seq, line in enumerate(lines, start=1):
        speaker_name = ""
        text = line
        match = _SPEAKER_LINE_RE.match(line)
        if match:
            speaker_name = match.group(1).strip()
            text = match.group(2).strip()

        row: dict[str, Any] = {
            "meeting_id": meeting_id,
            "source": source,
            "segment_seq": seq,
            "speaker_id": _speaker_id_from_name(speaker_name),
            "speaker_name": speaker_name,
            "text": text,
            "clean_text": text,
            "status": "draft",
            "confidence": 0.3,
            "timestamp": ts,
        }
        if topic:
            row["topic"] = topic
        rows.append(row)
    return rows


def _transcript_insufficient_reason(transcript: str) -> str | None:
    lines = [line.strip() for line in (transcript or "").splitlines() if line.strip()]
    total_chars = sum(len(line) for line in lines)
    if not lines:
        return "Нет распознанного текста для структурирования."
    if len(lines) < _MIN_STRUCTURED_LINES or total_chars < _MIN_STRUCTURED_CHARS:
        return (
            "Недостаточно данных для структурирования "
            f"(строк: {len(lines)}, символов: {total_chars})."
        )
    return None


def _insufficient_rows(*, meeting_id: str, source: str, reason: str) -> list[dict[str, Any]]:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return [
        {
            "meeting_id": meeting_id,
            "source": source,
            "status": "insufficient_data",
            "text": reason,
            "clean_text": reason,
            "timestamp": ts,
            "confidence": 0.0,
        }
    ]


def _build_orchestrator():
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


def build_structured_rows(
    *,
    meeting_id: str,
    source: str,
    transcript: str,
    report: dict | None,
) -> dict[str, Any]:
    insufficient_reason = _transcript_insufficient_reason(transcript)
    if insufficient_reason:
        return {
            "schema_version": "v1",
            "meeting_id": meeting_id,
            "source": source,
            "status": "insufficient_data",
            "message": insufficient_reason,
            "columns": STRUCTURED_COLUMNS,
            "rows": _insufficient_rows(
                meeting_id=meeting_id,
                source=source,
                reason=insufficient_reason,
            ),
        }

    s = get_settings()
    fallback_rows = _build_fallback_rows(
        meeting_id=meeting_id,
        source=source,
        transcript=transcript,
        report=report,
    )

    if not s.llm_enabled:
        return {
            "schema_version": "v1",
            "meeting_id": meeting_id,
            "source": source,
            "status": "ok",
            "message": "",
            "columns": STRUCTURED_COLUMNS,
            "rows": fallback_rows,
        }

    try:
        orch = _build_orchestrator()
    except Exception as err:
        log.warning(
            "structured_llm_init_failed",
            extra={"payload": {"meeting_id": meeting_id, "source": source, "err": str(err)[:200]}},
        )
        return {
            "schema_version": "v1",
            "meeting_id": meeting_id,
            "source": source,
            "status": "ok",
            "message": "",
            "columns": STRUCTURED_COLUMNS,
            "rows": fallback_rows,
        }
    if orch is None:
        return {
            "schema_version": "v1",
            "meeting_id": meeting_id,
            "source": source,
            "status": "ok",
            "message": "",
            "columns": STRUCTURED_COLUMNS,
            "rows": fallback_rows,
        }

    system = (
        "Ты аналитик встреч. Верни ТОЛЬКО валидный JSON с ключами "
        "{schema_version:'v1', columns:[...], rows:[{...}]}."
        " columns должны строго совпадать со списком, который я дам."
        " В rows каждая строка — объект с этими полями. Если данных нет — оставь пустую строку."
        " Не выдумывай имена говорящих без явного контекста."
        " Если спикер отвечает за отсутствующего (например: 'Кирилла нет, отвечу за него'), "
        "заполняй proxy_for именем отсутствующего."
        " Если в тексте есть метка PROXY_FOR_<NAME>, используй NAME как proxy_for."
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

    try:
        data = orch.complete_json(system=system, user=user)
    except Exception as err:
        log.warning(
            "structured_llm_failed",
            extra={"payload": {"meeting_id": meeting_id, "source": source, "err": str(err)[:200]}},
        )
        return {
            "schema_version": "v1",
            "meeting_id": meeting_id,
            "source": source,
            "status": "ok",
            "message": "",
            "columns": STRUCTURED_COLUMNS,
            "rows": fallback_rows,
        }

    rows = data.get("rows", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        rows = []
    if not rows and fallback_rows:
        rows = fallback_rows
    return {
        "schema_version": "v1",
        "meeting_id": meeting_id,
        "source": source,
        "status": "ok",
        "message": "",
        "columns": STRUCTURED_COLUMNS,
        "rows": rows,
    }


def structured_to_csv(structured: dict[str, Any]) -> bytes:
    columns = structured.get("columns") or STRUCTURED_COLUMNS
    rows = structured.get("rows") or []
    if not rows and str(structured.get("status") or "") == "insufficient_data":
        rows = _insufficient_rows(
            meeting_id=str(structured.get("meeting_id") or ""),
            source=str(structured.get("source") or ""),
            reason=str(structured.get("message") or "Нет структурируемых данных"),
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    # BOM для лучшей совместимости с Excel
    return ("\ufeff" + output.getvalue()).encode("utf-8")
