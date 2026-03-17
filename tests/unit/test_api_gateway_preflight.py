from fastapi.testclient import TestClient


def test_api_preflight_compat_endpoint_returns_ok(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("POSTGRES_DSN", f"sqlite:///{(tmp_path / 'agent.db').as_posix()}")
    monkeypatch.setenv("AUTH_MODE", "none")

    from apps.api_gateway.main import _create_app

    client = TestClient(_create_app())

    resp = client.get("/api/preflight")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["service"] == "api-gateway"
    assert "stt_provider" in payload
    assert "queue_mode" in payload
