from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from apps.api_gateway import ws as ws_module
from apps.api_gateway.main import app
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.services.chunk_ingest_service import ChunkIngestResult


@pytest.fixture()
def auth_none_settings():
    s = get_settings()
    snapshot_auth = s.auth_mode
    snapshot_tenant = getattr(s, "tenant_enforcement_enabled", False)
    snapshot_queue_mode = getattr(s, "queue_mode", "redis")
    try:
        s.auth_mode = "none"
        if hasattr(s, "tenant_enforcement_enabled"):
            s.tenant_enforcement_enabled = False
        if hasattr(s, "queue_mode"):
            s.queue_mode = "redis"
        yield s
    finally:
        s.auth_mode = snapshot_auth
        if hasattr(s, "tenant_enforcement_enabled"):
            s.tenant_enforcement_enabled = snapshot_tenant
        if hasattr(s, "queue_mode"):
            s.queue_mode = snapshot_queue_mode


def test_ws_ping_pong(auth_none_settings) -> None:
    client = TestClient(app)
    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"event_type": "ping", "meeting_id": "m_ping"})
        data = ws.receive_json()
        assert data["event_type"] == "ws.pong"
        assert data["meeting_id"] == "m_ping"


def test_ws_session_resume(auth_none_settings) -> None:
    client = TestClient(app)
    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"event_type": "session.resume", "meeting_id": "m_resume", "last_seq": 11})
        data = ws.receive_json()
        assert data["event_type"] == "ws.resumed"
        assert data["meeting_id"] == "m_resume"
        assert data["client_last_seq"] == 11


def test_ws_audio_chunk_returns_ack(monkeypatch, auth_none_settings) -> None:
    def fake_ingest_audio_chunk_bytes(**kwargs):
        return ChunkIngestResult(
            accepted=True,
            meeting_id=str(kwargs["meeting_id"]),
            seq=int(kwargs["seq"]),
            idempotency_key=str(kwargs.get("idempotency_key") or "idem"),
            blob_key="meetings/m_ack/chunks/1.bin",
            is_duplicate=False,
            inline_updates=[],
        )

    monkeypatch.setattr(ws_module, "ingest_audio_chunk_bytes", fake_ingest_audio_chunk_bytes)

    client = TestClient(app)
    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json(
            {
                "schema_version": "v1",
                "event_type": "audio.chunk",
                "meeting_id": "m_ack",
                "seq": 1,
                "timestamp_ms": 1,
                "codec": "audio/webm",
                "sample_rate": 48000,
                "channels": 1,
                "content_b64": base64.b64encode(b"abc").decode("ascii"),
                "idempotency_key": "m_ack:1:test",
            }
        )
        data = ws.receive_json()
        assert data["event_type"] == "ws.ack"
        assert data["seq"] == 1
        assert data["last_acked_seq"] == 1
        assert data["duplicate"] is False


def test_ws_resume_duplicate_chunk_ack(monkeypatch, auth_none_settings) -> None:
    seen_by_meeting: dict[str, set[int]] = {}

    def fake_ingest_audio_chunk_bytes(**kwargs):
        meeting_id = str(kwargs["meeting_id"])
        seq = int(kwargs["seq"])
        seen = seen_by_meeting.setdefault(meeting_id, set())
        duplicate = seq in seen
        seen.add(seq)
        return ChunkIngestResult(
            accepted=True,
            meeting_id=meeting_id,
            seq=seq,
            idempotency_key=str(kwargs.get("idempotency_key") or f"{meeting_id}:{seq}"),
            blob_key=f"meetings/{meeting_id}/chunks/{seq}.bin",
            is_duplicate=duplicate,
            inline_updates=[],
        )

    monkeypatch.setattr(ws_module, "ingest_audio_chunk_bytes", fake_ingest_audio_chunk_bytes)

    payload_seq_1 = {
        "schema_version": "v1",
        "event_type": "audio.chunk",
        "meeting_id": "m_resume_ack",
        "seq": 1,
        "timestamp_ms": 1,
        "codec": "pcm",
        "sample_rate": 16000,
        "channels": 1,
        "content_b64": base64.b64encode(b"abc").decode("ascii"),
    }
    payload_seq_2 = {
        **payload_seq_1,
        "seq": 2,
        "content_b64": base64.b64encode(b"def").decode("ascii"),
    }

    client = TestClient(app)
    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json(payload_seq_1)
        ack_1 = ws.receive_json()
        assert ack_1["event_type"] == "ws.ack"
        assert ack_1["seq"] == 1
        assert ack_1["duplicate"] is False

    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"event_type": "session.resume", "meeting_id": "m_resume_ack", "last_seq": 1})
        resumed = ws.receive_json()
        assert resumed["event_type"] == "ws.resumed"
        assert resumed["meeting_id"] == "m_resume_ack"
        assert resumed["client_last_seq"] == 1

        ws.send_json(payload_seq_1)
        dup_ack = ws.receive_json()
        assert dup_ack["event_type"] == "ws.ack"
        assert dup_ack["seq"] == 1
        assert dup_ack["duplicate"] is True

        ws.send_json(payload_seq_2)
        ack_2 = ws.receive_json()
        assert ack_2["event_type"] == "ws.ack"
        assert ack_2["seq"] == 2
        assert ack_2["duplicate"] is False
        assert ack_2["last_acked_seq"] == 2
