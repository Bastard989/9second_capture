from __future__ import annotations

from interview_analytics_agent.queue.dispatcher import enqueue_stt


def test_enqueue_stt_includes_trace_fields(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "interview_analytics_agent.queue.dispatcher.new_event_id",
        lambda prefix: f"{prefix}-event-1",
    )

    def _inject(payload, *, meeting_id=None, source="queue"):
        payload["trace_id"] = "c" * 32
        payload["span_id"] = "d" * 16
        payload["trace_source"] = source
        if meeting_id:
            payload["meeting_id"] = meeting_id
        return payload

    monkeypatch.setattr(
        "interview_analytics_agent.queue.dispatcher.inject_trace_context",
        _inject,
    )
    monkeypatch.setattr(
        "interview_analytics_agent.queue.dispatcher.enqueue",
        lambda queue, payload: captured.update({"queue": queue, "payload": payload}),
    )

    event_id = enqueue_stt(meeting_id="m-55", chunk_seq=2, blob_key="blob-55")

    assert event_id == "stt-event-1"
    assert captured["queue"] == "q:stt"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["trace_id"] == "c" * 32
    assert payload["span_id"] == "d" * 16
    assert payload["trace_source"] == "queue.stt"
    assert payload["meeting_id"] == "m-55"
