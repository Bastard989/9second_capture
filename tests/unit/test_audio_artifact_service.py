from __future__ import annotations

from interview_analytics_agent.services import audio_artifact_service
from interview_analytics_agent.storage import records


class _Settings:
    def __init__(self, records_dir: str) -> None:
        self.records_dir = records_dir


def test_materialize_audio_mp3_from_backup_mp3(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(records, "get_settings", lambda: _Settings(str(tmp_path)))
    monkeypatch.setattr(audio_artifact_service, "_meeting_context", lambda _meeting_id: {})

    payload = b"ID3" + b"x" * 4096
    records.write_bytes("meeting1", "backup_audio.mp3", payload)

    result = audio_artifact_service.materialize_meeting_audio_mp3(meeting_id="meeting1")

    assert result is not None
    assert result.name == audio_artifact_service.CANONICAL_AUDIO_FILENAME
    assert result.exists()
    assert result.read_bytes() == payload
