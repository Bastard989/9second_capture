from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
from interview_analytics_agent.common.provider_settings import (
    provider_display_name,
    resolve_embedding_endpoint,
    resolve_embedding_provider,
    resolve_llm_endpoint,
    resolve_llm_provider,
)
from interview_analytics_agent.llm.factory import list_models_for_endpoint
from interview_analytics_agent.services.local_pipeline import stt_runtime_status

router = APIRouter()
log = get_project_logger()


class DiagnosticsSTTStatus(BaseModel):
    provider: str
    warmup_started: bool
    warmup_ready: bool
    warmup_error: str = ""
    provider_initialized: bool


class DiagnosticsLLMStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    enabled: bool
    available: bool
    provider: str
    model_id: str
    message: str = ""


class DiagnosticsEmbeddingsStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    enabled: bool
    provider: str
    model_id: str
    available: bool
    message: str = ""


class DiagnosticsPreflightResponse(BaseModel):
    server_time: str
    stt: DiagnosticsSTTStatus
    llm: DiagnosticsLLMStatus
    embeddings: DiagnosticsEmbeddingsStatus


class DiagnosticsUiEventRequest(BaseModel):
    event: str = Field(min_length=2, max_length=120)
    level: str = Field(default="info", min_length=4, max_length=10)
    work_mode: str = Field(default="", max_length=64)
    meeting_id: str = Field(default="", max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


def _llm_status() -> DiagnosticsLLMStatus:
    s = get_settings()
    enabled = bool(getattr(s, "llm_enabled", False))
    endpoint = resolve_llm_endpoint(s)
    provider = resolve_llm_provider(s)
    if not enabled:
        return DiagnosticsLLMStatus(
            enabled=False,
            available=False,
            provider=provider_display_name(provider),
            model_id=endpoint.model_id,
            message="LLM disabled",
        )
    if provider != "mock" and not endpoint.api_base:
        return DiagnosticsLLMStatus(
            enabled=True,
            available=False,
            provider=provider_display_name(provider),
            model_id=endpoint.model_id,
            message="LLM endpoint is not configured",
        )
    if provider == "mock":
        return DiagnosticsLLMStatus(
            enabled=True,
            available=True,
            provider=provider_display_name(provider),
            model_id=endpoint.model_id or "mock",
            message="Mock LLM is active",
        )
    try:
        models = list_models_for_endpoint(
            provider=provider,
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
            timeout_s=min(5, int(getattr(s, "llm_request_timeout_sec", 5) or 5)),
        )
    except Exception as err:
        return DiagnosticsLLMStatus(
            enabled=True,
            available=False,
            provider=provider_display_name(provider),
            model_id=endpoint.model_id,
            message=f"LLM unavailable: {err}",
        )
    if endpoint.model_id and endpoint.model_id not in models:
        return DiagnosticsLLMStatus(
            enabled=True,
            available=False,
            provider=provider_display_name(provider),
            model_id=endpoint.model_id,
            message=f"Model '{endpoint.model_id}' is not available in provider",
        )
    return DiagnosticsLLMStatus(
        enabled=True,
        available=True,
        provider=provider_display_name(provider),
        model_id=endpoint.model_id,
        message="LLM ready",
    )


def _embeddings_status() -> DiagnosticsEmbeddingsStatus:
    s = get_settings()
    enabled = bool(getattr(s, "rag_vector_enabled", True))
    requested = resolve_embedding_provider(s)
    endpoint = resolve_embedding_endpoint(s)
    if not enabled:
        return DiagnosticsEmbeddingsStatus(
            enabled=False,
            available=False,
            provider="disabled",
            model_id=endpoint.model_id,
            message="RAG vector retrieval disabled",
        )
    if requested == "hashing":
        return DiagnosticsEmbeddingsStatus(
            enabled=True,
            available=True,
            provider="hashing_local",
            model_id=endpoint.model_id or "hashing_local",
            message="Local hashing embeddings fallback",
        )
    if not endpoint.api_base or not endpoint.model_id:
        return DiagnosticsEmbeddingsStatus(
            enabled=True,
            available=True,
            provider="hashing_local",
            model_id=endpoint.model_id or "embedding model not set",
            message="Embeddings config incomplete, hashing fallback will be used",
        )
    try:
        models = list_models_for_endpoint(
            provider=requested,
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
            timeout_s=min(5, int(getattr(s, "rag_embedding_request_timeout_sec", 5) or 5)),
        )
    except Exception as err:
        return DiagnosticsEmbeddingsStatus(
            enabled=True,
            available=False,
            provider=provider_display_name(requested),
            model_id=endpoint.model_id,
            message=f"Embeddings provider unavailable: {err}; hashing fallback",
        )
    if endpoint.model_id not in models:
        return DiagnosticsEmbeddingsStatus(
            enabled=True,
            available=False,
            provider=provider_display_name(requested),
            model_id=endpoint.model_id,
            message=f"Embeddings model '{endpoint.model_id}' is not available; hashing fallback",
        )
    return DiagnosticsEmbeddingsStatus(
        enabled=True,
        available=True,
        provider=provider_display_name(requested),
        model_id=endpoint.model_id,
        message="Embeddings provider ready",
    )


def _normalize_log_level(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in {"debug", "info", "warning", "error"}:
        return value
    return "info"


def _safe_payload(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for idx, (key, value) in enumerate(raw.items()):
        if idx >= 24:
            break
        k = str(key).strip()[:80]
        if not k:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            v: Any = value
            if isinstance(v, str):
                v = v[:500]
            out[k] = v
        elif isinstance(value, dict):
            out[k] = {"_type": "dict", "size": len(value)}
        elif isinstance(value, list):
            out[k] = {"_type": "list", "size": len(value)}
        else:
            out[k] = {"_type": type(value).__name__}
    return out


@router.get("/diagnostics/preflight", response_model=DiagnosticsPreflightResponse)
def diagnostics_preflight(_=Depends(auth_dep)) -> DiagnosticsPreflightResponse:
    stt_status = stt_runtime_status()
    return DiagnosticsPreflightResponse(
        server_time=datetime.now(timezone.utc).isoformat(),
        stt=DiagnosticsSTTStatus(**stt_status),
        llm=_llm_status(),
        embeddings=_embeddings_status(),
    )


@router.post("/diagnostics/ui-event")
def diagnostics_ui_event(req: DiagnosticsUiEventRequest, request: Request, _=Depends(auth_dep)) -> dict[str, Any]:
    level = _normalize_log_level(req.level)
    event = req.event.strip()
    payload = {
        "event": event,
        "work_mode": (req.work_mode or "").strip(),
        "meeting_id": (req.meeting_id or "").strip(),
        "client_ip": request.client.host if request.client else "",
        "user_agent": (request.headers.get("user-agent") or "")[:180],
        "payload": _safe_payload(req.payload),
    }
    if level == "error":
        log.error("ui_event", extra={"payload": payload})
    elif level == "warning":
        log.warning("ui_event", extra={"payload": payload})
    elif level == "debug":
        log.debug("ui_event", extra={"payload": payload})
    else:
        log.info("ui_event", extra={"payload": payload})
    return {"ok": True}
