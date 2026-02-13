from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from interview_analytics_agent.common.config import get_settings

_COUNTER_LOCK = threading.Lock()
_META_FILENAME = "meeting_meta.json"
_COUNTER_FILENAME = "_record_counter.json"


def _base_dir() -> Path:
    s = get_settings()
    root = (getattr(s, "records_dir", None) or "./data/records").strip()
    return Path(root).resolve()


def _safe_meeting_id(meeting_id: str) -> str:
    if not meeting_id or "/" in meeting_id or "\\" in meeting_id or ".." in meeting_id:
        raise ValueError("invalid_meeting_id")
    return meeting_id


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _counter_path() -> Path:
    return _base_dir() / _COUNTER_FILENAME


def _meta_path(meeting_id: str) -> Path:
    return meeting_dir(meeting_id) / _META_FILENAME


def _sanitize_display_name(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise ValueError("display_name_required")
    return text[:120]


def _scan_last_record_index() -> int:
    root = _base_dir()
    if not root.exists():
        return 0
    max_idx = 0
    for item in root.iterdir():
        if not item.is_dir():
            continue
        meta_path = item / _META_FILENAME
        if not meta_path.exists():
            continue
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            idx = int(payload.get("record_index") or 0)
            if idx > max_idx:
                max_idx = idx
        except Exception:
            continue
    return max_idx


def _next_record_index() -> int:
    with _COUNTER_LOCK:
        base = _base_dir()
        base.mkdir(parents=True, exist_ok=True)
        path = _counter_path()
        payload: dict[str, Any] = {}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        current = int(payload.get("last_index") or 0)
        if current <= 0:
            current = _scan_last_record_index()
        next_idx = current + 1
        path.write_text(
            json.dumps(
                {
                    "last_index": next_idx,
                    "updated_at": _now_iso(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return next_idx


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


def read_meeting_metadata(meeting_id: str) -> dict[str, Any]:
    path = _meta_path(meeting_id)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except Exception:
        return {}
    return {}


def ensure_meeting_metadata(meeting_id: str, *, default_prefix: str = "Запись") -> dict[str, Any]:
    existing = read_meeting_metadata(meeting_id)
    if existing and str(existing.get("display_name") or "").strip():
        return existing

    record_index = int(existing.get("record_index") or 0)
    if record_index <= 0:
        record_index = _next_record_index()
    display_name = str(existing.get("display_name") or "").strip() or f"{default_prefix} {record_index}"
    created_at = str(existing.get("created_at") or "").strip() or _now_iso()
    payload = {
        "record_index": record_index,
        "display_name": display_name,
        "created_at": created_at,
        "updated_at": _now_iso(),
    }
    write_json(meeting_id, _META_FILENAME, payload)
    return payload


def update_meeting_display_name(meeting_id: str, display_name: str) -> dict[str, Any]:
    name = _sanitize_display_name(display_name)
    meta = ensure_meeting_metadata(meeting_id)
    meta["display_name"] = name
    if not int(meta.get("record_index") or 0):
        meta["record_index"] = _next_record_index()
    if not str(meta.get("created_at") or "").strip():
        meta["created_at"] = _now_iso()
    meta["updated_at"] = _now_iso()
    write_json(meeting_id, _META_FILENAME, meta)
    return meta


def exists(meeting_id: str, filename: str) -> bool:
    return (meeting_dir(meeting_id) / filename).exists()


def artifact_path(meeting_id: str, filename: str) -> Path:
    return meeting_dir(meeting_id) / filename


def list_artifacts(meeting_id: str) -> dict[str, bool]:
    return {
        "raw": exists(meeting_id, "raw.txt"),
        "clean": exists(meeting_id, "clean.txt"),
        "audio_mp3": exists(meeting_id, "meeting_audio.mp3"),
        "report_raw": exists(meeting_id, "report_raw.json"),
        "report_clean": exists(meeting_id, "report_clean.json"),
        "report_raw_txt": exists(meeting_id, "report_raw.txt"),
        "report_clean_txt": exists(meeting_id, "report_clean.txt"),
        "structured_raw_json": exists(meeting_id, "structured_raw.json"),
        "structured_raw_csv": exists(meeting_id, "structured_raw.csv"),
        "structured_clean_json": exists(meeting_id, "structured_clean.json"),
        "structured_clean_csv": exists(meeting_id, "structured_clean.csv"),
    }
