from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.storage.blob import get_bytes
from interview_analytics_agent.storage import records
from interview_analytics_agent.storage.db import db_session
from interview_analytics_agent.storage.repositories import MeetingRepository

log = get_project_logger()

CANONICAL_AUDIO_FILENAME = "meeting_audio.mp3"


def _meeting_context(meeting_id: str) -> dict[str, Any]:
    with db_session() as session:
        repo = MeetingRepository(session)
        meeting = repo.get(meeting_id)
        if not meeting:
            return {}
        context = getattr(meeting, "context", None)
        if isinstance(context, dict):
            return context
    return {}


def _candidate_filenames(meeting_id: str, preferred_filename: str | None = None) -> list[str]:
    ctx = _meeting_context(meeting_id)
    candidates: list[str] = []

    if preferred_filename:
        candidates.append(str(preferred_filename).strip())

    filename_hint = str(ctx.get("filename") or "").strip()
    if filename_hint and "." in filename_hint:
        ext = filename_hint.rsplit(".", 1)[-1].strip().lower()
        if ext and ext.isalnum():
            candidates.append(f"source_upload.{ext}")

    source_defaults = [
        "backup_audio.mp3",
        "backup_audio.webm",
        "backup_audio.wav",
        "backup_audio.ogg",
        "backup_audio.m4a",
        "backup_audio.mp4",
        "source_upload.mp3",
        "source_upload.wav",
        "source_upload.ogg",
        "source_upload.webm",
        "source_upload.m4a",
        "source_upload.mp4",
    ]
    candidates.extend(source_defaults)

    dedup: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        value = str(item or "").strip()
        if not value:
            continue
        if value == CANONICAL_AUDIO_FILENAME:
            continue
        if value in seen:
            continue
        seen.add(value)
        dedup.append(value)
    return dedup


def _transcode_to_mp3(src: Path, dst: Path) -> bool:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return False
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(dst),
    ]
    try:
        proc = subprocess.run(cmd, check=False)
    except Exception:
        return False
    return proc.returncode == 0 and dst.exists() and dst.stat().st_size > 1024


def materialize_meeting_audio_mp3(
    *,
    meeting_id: str,
    preferred_filename: str | None = None,
) -> Path | None:
    try:
        target = records.artifact_path(meeting_id, CANONICAL_AUDIO_FILENAME)
    except ValueError:
        return None

    if target.exists() and target.stat().st_size > 1024:
        return target

    for filename in _candidate_filenames(meeting_id, preferred_filename=preferred_filename):
        if not records.exists(meeting_id, filename):
            continue
        src = records.artifact_path(meeting_id, filename)
        if not src.exists() or src.stat().st_size <= 1024:
            continue

        try:
            if src.suffix.lower() == ".mp3":
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                if target.exists() and target.stat().st_size > 1024:
                    return target
                continue

            with tempfile.NamedTemporaryFile(prefix="meeting_audio_", suffix=".mp3", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                if _transcode_to_mp3(src, tmp_path):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    tmp_path.replace(target)
                    return target
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception:
            continue

    # Last fallback: try reconstructing from a full-size blob chunk.
    for seq in (0, 1):
        blob_key = f"meetings/{meeting_id}/chunks/{seq}.bin"
        try:
            payload = get_bytes(blob_key)
        except Exception:
            continue
        if not payload or len(payload) <= 1024:
            continue
        with tempfile.NamedTemporaryFile(prefix="meeting_chunk_", suffix=".bin", delete=False) as src_tmp:
            src_tmp_path = Path(src_tmp.name)
            src_tmp.write(payload)
        with tempfile.NamedTemporaryFile(prefix="meeting_audio_", suffix=".mp3", delete=False) as dst_tmp:
            dst_tmp_path = Path(dst_tmp.name)
        try:
            if _transcode_to_mp3(src_tmp_path, dst_tmp_path):
                target.parent.mkdir(parents=True, exist_ok=True)
                dst_tmp_path.replace(target)
                return target
        finally:
            src_tmp_path.unlink(missing_ok=True)
            dst_tmp_path.unlink(missing_ok=True)

    return None


def audio_artifact_summary(meeting_id: str) -> dict[str, Any]:
    path = materialize_meeting_audio_mp3(meeting_id=meeting_id)
    if not path:
        return {
            "available": False,
            "filename": CANONICAL_AUDIO_FILENAME,
            "size_bytes": 0,
        }
    return {
        "available": True,
        "filename": path.name,
        "size_bytes": int(path.stat().st_size),
    }
