"""
OpenTelemetry bootstrap (безопасный, idempotent).

Поведение:
- если OTEL выключен -> no-op;
- если зависимости отсутствуют -> no-op + warning;
- если инициализация уже выполнена -> no-op.
"""

from __future__ import annotations

from typing import Any

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger

log = get_project_logger()
_OTEL_READY = False


def _normalize_endpoint(endpoint: str | None) -> str | None:
    value = (endpoint or "").strip()
    return value or None


def _setup_otel_provider(*, endpoint: str | None, service_name: str, app_env: str) -> None:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": (app_env or "dev").strip().lower(),
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, timeout=5) if endpoint else OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def maybe_setup_otel() -> None:
    """
    Включает OTEL только если OTEL_ENABLED=true и зависимости доступны.
    """
    global _OTEL_READY

    if _OTEL_READY:
        return

    settings = get_settings()
    enabled = bool(getattr(settings, "otel_enabled", False))
    if not enabled:
        return

    service_name = (getattr(settings, "service_name", None) or "interview-analytics-agent").strip()
    endpoint = _normalize_endpoint(getattr(settings, "otel_exporter_otlp_endpoint", None))
    app_env = str(getattr(settings, "app_env", "dev"))

    try:
        _setup_otel_provider(endpoint=endpoint, service_name=service_name, app_env=app_env)
    except ImportError:
        log.warning(
            "otel_dependencies_missing",
            extra={"payload": {"service_name": service_name}},
        )
        return
    except Exception as e:
        payload: dict[str, Any] = {
            "service_name": service_name,
            "endpoint": endpoint or "default",
            "error": str(e)[:300],
        }
        log.warning("otel_setup_failed", extra={"payload": payload})
        return

    _OTEL_READY = True
    log.info(
        "otel_ready",
        extra={"payload": {"service_name": service_name, "endpoint": endpoint or "default"}},
    )
