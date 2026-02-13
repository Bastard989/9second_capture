from __future__ import annotations

from interview_analytics_agent.domain.enums import PipelineStatus
from interview_analytics_agent.services.local_pipeline import (
    _language_hint_from_context,
    _status_for_chunk_processing,
)


def test_status_for_chunk_processing_open_meeting() -> None:
    assert _status_for_chunk_processing(finished_at=None) == PipelineStatus.processing


def test_status_for_chunk_processing_finished_meeting() -> None:
    assert _status_for_chunk_processing(finished_at="2026-02-11 14:00:00") == PipelineStatus.done


def test_language_hint_from_context_prefers_profile() -> None:
    ctx = {"language_profile": "ru", "locale": "en"}
    assert _language_hint_from_context(ctx) == "ru"


def test_language_hint_from_context_handles_mixed() -> None:
    ctx = {"language_profile": "mixed"}
    assert _language_hint_from_context(ctx) == "auto"
