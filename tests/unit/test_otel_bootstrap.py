from __future__ import annotations

import interview_analytics_agent.common.otel as otel
from interview_analytics_agent.common.config import get_settings


def test_maybe_setup_otel_skips_when_disabled(monkeypatch) -> None:
    s = get_settings()
    snapshot = (
        s.otel_enabled,
        s.otel_exporter_otlp_endpoint,
        s.service_name,
        s.app_env,
        otel._OTEL_READY,
    )
    try:
        s.otel_enabled = False
        calls: list[dict[str, str | None]] = []
        monkeypatch.setattr(
            otel,
            "_setup_otel_provider",
            lambda **kwargs: calls.append(kwargs),
        )
        otel._OTEL_READY = False
        otel.maybe_setup_otel()
        assert calls == []
        assert otel._OTEL_READY is False
    finally:
        (
            s.otel_enabled,
            s.otel_exporter_otlp_endpoint,
            s.service_name,
            s.app_env,
            otel._OTEL_READY,
        ) = snapshot


def test_maybe_setup_otel_calls_setup_once(monkeypatch) -> None:
    s = get_settings()
    snapshot = (
        s.otel_enabled,
        s.otel_exporter_otlp_endpoint,
        s.service_name,
        s.app_env,
        otel._OTEL_READY,
    )
    try:
        s.otel_enabled = True
        s.otel_exporter_otlp_endpoint = "http://otel-collector:4318/v1/traces"
        s.service_name = "api-gateway"
        s.app_env = "prod"

        calls: list[dict[str, str | None]] = []
        monkeypatch.setattr(
            otel,
            "_setup_otel_provider",
            lambda **kwargs: calls.append(kwargs),
        )
        otel._OTEL_READY = False

        otel.maybe_setup_otel()
        otel.maybe_setup_otel()

        assert len(calls) == 1
        assert calls[0]["service_name"] == "api-gateway"
        assert calls[0]["endpoint"] == "http://otel-collector:4318/v1/traces"
        assert calls[0]["app_env"] == "prod"
        assert otel._OTEL_READY is True
    finally:
        (
            s.otel_enabled,
            s.otel_exporter_otlp_endpoint,
            s.service_name,
            s.app_env,
            otel._OTEL_READY,
        ) = snapshot


def test_maybe_setup_otel_handles_import_error(monkeypatch) -> None:
    s = get_settings()
    snapshot = (
        s.otel_enabled,
        s.otel_exporter_otlp_endpoint,
        s.service_name,
        s.app_env,
        otel._OTEL_READY,
    )
    try:
        s.otel_enabled = True
        s.otel_exporter_otlp_endpoint = ""
        s.service_name = "worker-stt"
        s.app_env = "dev"

        def _raise_import_error(**kwargs):
            raise ImportError("no opentelemetry")

        monkeypatch.setattr(otel, "_setup_otel_provider", _raise_import_error)
        otel._OTEL_READY = False

        otel.maybe_setup_otel()
        assert otel._OTEL_READY is False
    finally:
        (
            s.otel_enabled,
            s.otel_exporter_otlp_endpoint,
            s.service_name,
            s.app_env,
            otel._OTEL_READY,
        ) = snapshot
