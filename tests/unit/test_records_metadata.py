from __future__ import annotations

from interview_analytics_agent.storage import records


class _Settings:
    def __init__(self, records_dir: str) -> None:
        self.records_dir = records_dir


def test_meeting_metadata_auto_increment(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(records, "get_settings", lambda: _Settings(str(tmp_path)))

    meta1 = records.ensure_meeting_metadata("m1")
    meta2 = records.ensure_meeting_metadata("m2")

    assert int(meta1["record_index"]) == 1
    assert int(meta2["record_index"]) == 2
    assert str(meta1["display_name"]) == "Запись 1"
    assert str(meta2["display_name"]) == "Запись 2"


def test_meeting_metadata_rename(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(records, "get_settings", lambda: _Settings(str(tmp_path)))

    records.ensure_meeting_metadata("m1")
    updated = records.update_meeting_display_name("m1", "Интервью Python")

    assert str(updated["display_name"]) == "Интервью Python"
    loaded = records.read_meeting_metadata("m1")
    assert str(loaded.get("display_name") or "") == "Интервью Python"
