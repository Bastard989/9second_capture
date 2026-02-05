from __future__ import annotations

from interview_analytics_agent.common.tracing import (
    current_trace_context,
    inject_trace_context,
    start_trace,
    start_trace_from_payload,
)


def test_start_trace_creates_context_and_child_span() -> None:
    with start_trace(meeting_id="m-100", source="http") as root:
        assert len(root.trace_id) == 32
        assert len(root.span_id) == 16
        assert root.parent_span_id is None
        assert root.meeting_id == "m-100"

        with start_trace(source="http.ingest") as child:
            assert child.trace_id == root.trace_id
            assert child.parent_span_id == root.span_id
            assert child.meeting_id == "m-100"

    assert current_trace_context() is None


def test_start_trace_from_payload_uses_payload_trace_fields() -> None:
    payload = {"trace_id": "a" * 32, "span_id": "b" * 16, "meeting_id": "m-42"}
    with start_trace_from_payload(payload, source="worker.stt") as ctx:
        assert ctx.trace_id == "a" * 32
        assert ctx.parent_span_id == "b" * 16
        assert ctx.meeting_id == "m-42"
        assert len(ctx.span_id) == 16


def test_inject_trace_context_inherits_current_context() -> None:
    payload: dict[str, str] = {}
    with start_trace(meeting_id="m-7", source="http") as ctx:
        inject_trace_context(payload, source="queue.stt")

    assert payload["trace_id"] == ctx.trace_id
    assert payload["span_id"] == ctx.span_id
    assert payload["trace_source"] == "queue.stt"
    assert payload["meeting_id"] == "m-7"
