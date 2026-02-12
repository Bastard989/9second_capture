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
