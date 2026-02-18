from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.logging import get_project_logger
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


class DiagnosticsQualityProfile(BaseModel):
    id: str
    ws_quality_profile: str
    label: str
    description: str


class DiagnosticsPreflightResponse(BaseModel):
    server_time: str
    stt: DiagnosticsSTTStatus
    llm: DiagnosticsLLMStatus
    quality_profiles: list[DiagnosticsQualityProfile] = Field(default_factory=list)


class DiagnosticsUiEventRequest(BaseModel):
    event: str = Field(min_length=2, max_length=120)
    level: str = Field(default="info", min_length=4, max_length=10)
    work_mode: str = Field(default="", max_length=64)
    meeting_id: str = Field(default="", max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


def _is_local_base(api_base: str) -> bool:
    value = (api_base or "").strip()
    if not value:
        return False
    try:
        host = (urlparse(value).hostname or "").strip().lower()
    except Exception:
        host = ""
    return host in {"127.0.0.1", "localhost"}


def _llm_status() -> DiagnosticsLLMStatus:
    s = get_settings()
    enabled = bool(getattr(s, "llm_enabled", False))
    model_id = str(getattr(s, "llm_model_id", "") or "").strip()
    api_base = str(getattr(s, "openai_api_base", "") or "").strip()
    api_key = str(getattr(s, "openai_api_key", "") or "").strip()
    provider = "openai_compat" if api_base else "mock"
    if not enabled:
        return DiagnosticsLLMStatus(
            enabled=False,
            available=False,
            provider=provider,
            model_id=model_id,
            message="LLM disabled",
        )
    if not api_base:
        return DiagnosticsLLMStatus(
            enabled=True,
            available=False,
            provider=provider,
            model_id=model_id,
            message="OPENAI_API_BASE is not configured",
        )

    bearer = api_key or ("ollama" if _is_local_base(api_base) else "")
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    url = api_base.rstrip("/") + "/models"
    try:
        resp = requests.get(url, headers=headers, timeout=3.5)
    except requests.RequestException as err:
        return DiagnosticsLLMStatus(
            enabled=True,
            available=False,
            provider=provider,
            model_id=model_id,
            message=f"LLM unavailable: {err}",
        )
    if resp.status_code >= 400:
        text = (resp.text or "").strip()[:180]
        return DiagnosticsLLMStatus(
            enabled=True,
            available=False,
            provider=provider,
            model_id=model_id,
            message=f"LLM HTTP {resp.status_code}: {text}",
        )
    return DiagnosticsLLMStatus(
        enabled=True,
        available=True,
        provider=provider,
        model_id=model_id,
        message="LLM ready",
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
        quality_profiles=[
            DiagnosticsQualityProfile(
                id="fast",
                ws_quality_profile="live_fast",
                label="Fast",
                description="Низкая задержка, ниже точность, меньше нагрузка на CPU.",
            ),
            DiagnosticsQualityProfile(
                id="balanced",
                ws_quality_profile="live_balanced",
                label="Balanced",
                description="Баланс точности и задержки. Режим по умолчанию.",
            ),
            DiagnosticsQualityProfile(
                id="accurate",
                ws_quality_profile="live_accurate",
                label="Accurate",
                description="Выше точность, больше задержка и нагрузка на CPU.",
            ),
        ],
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
