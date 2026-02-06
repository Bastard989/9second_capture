from __future__ import annotations

import json
from pathlib import Path

from interview_analytics_agent.common.config import get_settings


def _base_dir() -> Path:
    s = get_settings()
    root = (getattr(s, "records_dir", None) or "./data/records").strip()
    return Path(root).resolve()


def _safe_meeting_id(meeting_id: str) -> str:
    if not meeting_id or "/" in meeting_id or "\\" in meeting_id or ".." in meeting_id:
        raise ValueError("invalid_meeting_id")
    return meeting_id


def meeting_dir(meeting_id: str) -> Path:
    return _base_dir() / _safe_meeting_id(meeting_id)


def ensure_meeting_dir(meeting_id: str) -> Path:
    d = meeting_dir(meeting_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(meeting_id: str, filename: str, text: str) -> Path:
    d = ensure_meeting_dir(meeting_id)
    p = d / filename
    p.write_text(text or "", encoding="utf-8")
    return p


def read_text(meeting_id: str, filename: str) -> str:
    return (meeting_dir(meeting_id) / filename).read_text(encoding="utf-8")


def write_json(meeting_id: str, filename: str, payload: dict) -> Path:
    d = ensure_meeting_dir(meeting_id)
    p = d / filename
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def read_json(meeting_id: str, filename: str) -> dict:
    raw = (meeting_dir(meeting_id) / filename).read_text(encoding="utf-8")
    return json.loads(raw)


def write_bytes(meeting_id: str, filename: str, payload: bytes) -> Path:
    d = ensure_meeting_dir(meeting_id)
    p = d / filename
    p.write_bytes(payload)
    return p


def exists(meeting_id: str, filename: str) -> bool:
    return (meeting_dir(meeting_id) / filename).exists()


def artifact_path(meeting_id: str, filename: str) -> Path:
    return meeting_dir(meeting_id) / filename


def list_artifacts(meeting_id: str) -> dict[str, bool]:
    return {
        "raw": exists(meeting_id, "raw.txt"),
        "clean": exists(meeting_id, "clean.txt"),
        "report_raw": exists(meeting_id, "report_raw.json"),
        "report_clean": exists(meeting_id, "report_clean.json"),
        "structured_raw_json": exists(meeting_id, "structured_raw.json"),
        "structured_raw_csv": exists(meeting_id, "structured_raw.csv"),
        "structured_clean_json": exists(meeting_id, "structured_clean.json"),
        "structured_clean_csv": exists(meeting_id, "structured_clean.csv"),
    }
