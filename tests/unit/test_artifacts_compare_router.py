from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api_gateway.routers import artifacts as artifacts_router
from interview_analytics_agent.common.config import get_settings


@pytest.fixture()
def auth_none_settings():
    s = get_settings()
    snapshot = s.auth_mode
    try:
        s.auth_mode = "none"
        yield s
    finally:
        s.auth_mode = snapshot


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(artifacts_router.router, prefix="/v1")
    return TestClient(app)


def test_compare_endpoint_returns_items(monkeypatch, auth_none_settings) -> None:
    payload = artifacts_router.CompareMeetingsResponse(
        generated_at="2026-02-12T12:40:00Z",
        source="clean",
        items=[
            artifacts_router.CompareMeetingItem(
                meeting_id="m1",
                created_at=datetime(2026, 2, 12, 12, 0, 0),
                source="clean",
                candidate_name="Alice",
                vacancy="Backend Engineer",
                level="Senior",
                interviewer="Bob",
                overall_score=4.2,
                decision_status="yes",
                decision_confidence=0.74,
                transcript_quality="high",
                comparable=True,
                summary="Strong interview signal.",
            )
        ],
    )
    monkeypatch.setattr(artifacts_router, "_build_compare_response", lambda **kwargs: payload)

    client = _client()
    resp = client.get("/v1/meetings/compare?source=clean&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "clean"
    assert len(body["items"]) == 1
    assert body["items"][0]["candidate_name"] == "Alice"


def test_compare_export_csv(monkeypatch, auth_none_settings) -> None:
    payload = artifacts_router.CompareMeetingsResponse(
        generated_at="2026-02-12T12:40:00Z",
        source="clean",
        items=[
            artifacts_router.CompareMeetingItem(
                meeting_id="m1",
                source="clean",
                candidate_name="Alice",
                vacancy="Backend Engineer",
                level="Senior",
                interviewer="Bob",
                overall_score=4.2,
                decision_status="yes",
                decision_confidence=0.74,
                transcript_quality="high",
                comparable=True,
                summary="Strong interview signal.",
            )
        ],
    )
    monkeypatch.setattr(artifacts_router, "_build_compare_response", lambda **kwargs: payload)

    client = _client()
    resp = client.get("/v1/meetings/compare/export?source=clean&fmt=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert resp.content.startswith(b"\xef\xbb\xbf")


def test_generate_senior_brief_writes_artifact(monkeypatch, auth_none_settings) -> None:
    written = {"meeting_id": "", "filename": "", "text": ""}
    monkeypatch.setattr(
        artifacts_router,
        "_load_or_build_report",
        lambda **kwargs: {"summary": "ok", "scorecard": [], "decision": {}},
    )
    monkeypatch.setattr(
        artifacts_router,
        "_senior_brief_text",
        lambda **kwargs: "Senior Brief\n...",
    )
    monkeypatch.setattr(
        artifacts_router.records,
        "write_text",
        lambda meeting_id, filename, text: written.update(
            {"meeting_id": meeting_id, "filename": filename, "text": text}
        ),
    )

    client = _client()
    resp = client.post("/v1/meetings/m1/senior-brief", json={"source": "clean"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["filename"] == "senior_brief_clean.txt"
    assert written["meeting_id"] == "m1"
    assert written["filename"] == "senior_brief_clean.txt"
