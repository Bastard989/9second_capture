from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.services.local_pipeline import stt_runtime_status

router = APIRouter()


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
