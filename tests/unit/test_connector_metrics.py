from __future__ import annotations

from types import SimpleNamespace

from interview_analytics_agent.common import metrics


def test_refresh_connector_metrics_sets_gauges(monkeypatch) -> None:
    monkeypatch.setattr(
        "interview_analytics_agent.services.sberjazz_service.list_sberjazz_sessions",
        lambda limit=2000: [
            SimpleNamespace(connected=True),
            SimpleNamespace(connected=False),
            SimpleNamespace(connected=True),
        ],
    )
    monkeypatch.setattr(
        "interview_analytics_agent.services.sberjazz_service.get_sberjazz_connector_health",
        lambda: SimpleNamespace(healthy=True),
    )

    metrics.refresh_connector_metrics()

    connected = metrics.SBERJAZZ_SESSIONS_TOTAL.labels(state="connected")._value.get()
    disconnected = metrics.SBERJAZZ_SESSIONS_TOTAL.labels(state="disconnected")._value.get()
    healthy = metrics.SBERJAZZ_CONNECTOR_HEALTH._value.get()

    assert connected == 2
    assert disconnected == 1
    assert healthy == 1
