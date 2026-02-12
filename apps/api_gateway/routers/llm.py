from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings

router = APIRouter()


class LLMStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    llm_enabled: bool
    llm_live_enabled: bool
    api_base: str
    model_id: str
    provider: str


class LLMModelsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    models: list[str] = Field(default_factory=list)
    current_model: str


class LLMModelUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(min_length=1, max_length=200)


class LLMModelUpdateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    model_id: str


def _is_local_base(api_base: str) -> bool:
    value = (api_base or "").strip()
    if not value:
        return False
    try:
        host = (urlparse(value).hostname or "").strip().lower()
    except Exception:
        host = ""
    return host in {"127.0.0.1", "localhost"}


def _resolve_bearer_token(api_base: str, api_key: str) -> str:
    key = (api_key or "").strip()
    if key:
        return key
    if _is_local_base(api_base):
        return "ollama"
    return ""


def _fetch_openai_compat_models(*, api_base: str, api_key: str, timeout_s: int) -> list[str]:
    base = (api_base or "").strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OPENAI_API_BASE is not configured",
        )

    url = base.rstrip("/") + "/models"
    headers = {"Content-Type": "application/json"}
    bearer = _resolve_bearer_token(base, api_key)
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    try:
        resp = requests.get(url, headers=headers, timeout=max(3, timeout_s))
    except requests.RequestException as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider is unavailable: {err}",
        ) from err

    if resp.status_code >= 400:
        text = (resp.text or "")[:300]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider returned HTTP {resp.status_code}: {text}",
        )

    try:
        payload = resp.json()
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider returned invalid JSON: {err}",
        ) from err

    rows = payload.get("data") if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    models: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            model_id = str(row.get("id") or "").strip()
            if model_id:
                models.append(model_id)

    # dedupe, stable order
    seen: set[str] = set()
    unique: list[str] = []
    for model_id in models:
        if model_id in seen:
            continue
        seen.add(model_id)
        unique.append(model_id)
    return unique


def _runtime_override_file() -> Path:
    root = (os.getenv("LOCAL_AGENT_STATE_DIR") or "./data/local_agent").strip()
    return Path(root).resolve() / "runtime_overrides.json"


def _save_runtime_override(key: str, value: str) -> None:
    try:
        path = _runtime_override_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, str] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                payload = {str(k): str(v) for k, v in raw.items() if str(k).strip()}
        payload[str(key)] = str(value)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # runtime override persistence is best-effort only
        return


@router.get("/llm/status", response_model=LLMStatusResponse)
def llm_status(_=Depends(auth_dep)) -> LLMStatusResponse:
    s = get_settings()
    api_base = (s.openai_api_base or "").strip()
    provider = "openai_compat" if api_base else "mock"
    return LLMStatusResponse(
        llm_enabled=bool(s.llm_enabled),
        llm_live_enabled=bool(s.llm_live_enabled),
        api_base=api_base,
        model_id=(s.llm_model_id or "").strip(),
        provider=provider,
    )


@router.get("/llm/models", response_model=LLMModelsResponse)
def llm_models(_=Depends(auth_dep)) -> LLMModelsResponse:
    s = get_settings()
    models = _fetch_openai_compat_models(
        api_base=(s.openai_api_base or "").strip(),
        api_key=(s.openai_api_key or "").strip(),
        timeout_s=int(s.llm_request_timeout_sec or 10),
    )
    current = (s.llm_model_id or "").strip()
    if current and current not in models:
        models.append(current)
    return LLMModelsResponse(models=models, current_model=current)


@router.post("/llm/model", response_model=LLMModelUpdateResponse)
def llm_update_model(req: LLMModelUpdateRequest, _=Depends(auth_dep)) -> LLMModelUpdateResponse:
    next_model = req.model_id.strip()
    if not next_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required")
    s = get_settings()
    s.llm_model_id = next_model
    os.environ["LLM_MODEL_ID"] = next_model
    _save_runtime_override("LLM_MODEL_ID", next_model)
    return LLMModelUpdateResponse(model_id=next_model)
