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
from interview_analytics_agent.services.local_pipeline import reset_stt_provider_runtime, stt_runtime_status

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


class STTStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str
    model_id: str
    warmup_started: bool
    warmup_ready: bool
    warmup_error: str = ""
    provider_initialized: bool


class STTModelsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    models: list[str] = Field(default_factory=list)
    current_model: str


class STTModelUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(min_length=1, max_length=200)


class STTModelUpdateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    model_id: str


class EmbeddingStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    vector_enabled: bool
    provider_requested: str
    provider: str
    api_base: str
    model_id: str
    available: bool
    fallback_provider: str = "hashing_local"
    message: str = ""


class EmbeddingModelsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    models: list[str] = Field(default_factory=list)
    current_model: str


class EmbeddingModelUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(min_length=1, max_length=200)


class EmbeddingModelUpdateResponse(BaseModel):
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


def _split_model_id(model_id: str) -> tuple[str, str]:
    value = str(model_id or "").strip().lower()
    if not value:
        return "", ""
    if ":" not in value:
        return value, "latest"
    name, tag = value.split(":", 1)
    return name.strip(), tag.strip()


_EMBEDDING_MODEL_HINTS = (
    "embed",
    "embedding",
    "text-embedding",
    "nomic-embed",
    "mxbai-embed",
    "bge",
    "e5",
    "gte",
    "minilm",
    "arctic-embed",
    "jina-embeddings",
)


def _is_embedding_model(model_id: str) -> bool:
    name, _tag = _split_model_id(model_id)
    candidate = (name or str(model_id or "").strip().lower()).replace("_", "-")
    if not candidate:
        return False
    return any(hint in candidate for hint in _EMBEDDING_MODEL_HINTS)


def _filter_llm_chat_models(models: list[str]) -> list[str]:
    return [model for model in models if not _is_embedding_model(model)]


def _filter_embedding_models(models: list[str]) -> list[str]:
    return [model for model in models if _is_embedding_model(model)]


def _is_compatible_model(target_model: str, candidate_model: str) -> bool:
    target_name, target_tag = _split_model_id(target_model)
    candidate_name, candidate_tag = _split_model_id(candidate_model)
    if not target_name or not candidate_name:
        return False
    tag_match = (
        target_tag == candidate_tag
        or not target_tag
        or not candidate_tag
        or candidate_tag.startswith(target_tag)
        or target_tag.startswith(candidate_tag)
    )
    if not tag_match:
        return False
    if target_name == candidate_name:
        return True
    aliases = {
        "llama3.1": {"llama3"},
        "llama3": {"llama3.1"},
    }
    return candidate_name in aliases.get(target_name, set())


def _resolve_model_match(target_model: str, installed_models: list[str]) -> tuple[bool, bool, str]:
    target = str(target_model or "").strip()
    if not target:
        return False, False, ""
    clean_models = [str(model).strip() for model in installed_models if str(model).strip()]
    exact_lookup = {model.lower(): model for model in clean_models}
    exact = exact_lookup.get(target.lower())
    if exact:
        return True, True, exact
    for model in clean_models:
        if _is_compatible_model(target, model):
            return True, False, model
    return False, False, ""


def _available_models_hint(models: list[str], *, limit: int = 8) -> str:
    visible = [str(model).strip() for model in models if str(model).strip()][: max(1, limit)]
    if not visible:
        return "none"
    suffix = " ..." if len(models) > len(visible) else ""
    return ", ".join(visible) + suffix


def _runtime_override_file() -> Path:
    root = (os.getenv("LOCAL_AGENT_STATE_DIR") or "./data/local_agent").strip()
    return Path(root).resolve() / "runtime_overrides.json"


def _stt_model_catalog() -> list[str]:
    # Поддерживаемый набор faster-whisper моделей для локального переключения.
    return [
        "tiny",
        "base",
        "small",
        "medium",
        "large-v3",
    ]


def _embedding_api_base() -> str:
    s = get_settings()
    return str(getattr(s, "embedding_api_base", "") or getattr(s, "openai_api_base", "") or "").strip()


def _embedding_api_key() -> str:
    s = get_settings()
    return str(getattr(s, "embedding_api_key", "") or getattr(s, "openai_api_key", "") or "").strip()


def _embedding_provider_requested() -> str:
    s = get_settings()
    value = str(getattr(s, "rag_embedding_provider", "auto") or "auto").strip().lower()
    return value or "auto"


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
    models = _filter_llm_chat_models(
        _fetch_openai_compat_models(
            api_base=(s.openai_api_base or "").strip(),
            api_key=(s.openai_api_key or "").strip(),
            timeout_s=int(s.llm_request_timeout_sec or 10),
        )
    )
    current = (s.llm_model_id or "").strip()
    present, _exact, matched = _resolve_model_match(current, models)
    if present and matched:
        current = matched
    else:
        current = ""
    return LLMModelsResponse(models=models, current_model=current)


@router.post("/llm/model", response_model=LLMModelUpdateResponse)
def llm_update_model(req: LLMModelUpdateRequest, _=Depends(auth_dep)) -> LLMModelUpdateResponse:
    next_model = req.model_id.strip()
    if not next_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required")
    if _is_embedding_model(next_model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Model '{next_model}' looks like an embedding model. "
                "Select a chat/LLM model in LLM section."
            ),
        )
    s = get_settings()
    models = _filter_llm_chat_models(
        _fetch_openai_compat_models(
            api_base=(s.openai_api_base or "").strip(),
            api_key=(s.openai_api_key or "").strip(),
            timeout_s=max(3, int(getattr(s, "llm_request_timeout_sec", 10) or 10)),
        )
    )
    present, exact, matched = _resolve_model_match(next_model, models)
    if not present:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Model '{next_model}' is not installed in provider. "
                f"Available chat models: {_available_models_hint(models)}"
            ),
        )
    effective_model = matched if matched else next_model
    if not exact and matched:
        next_model = matched

    s.llm_model_id = next_model
    os.environ["LLM_MODEL_ID"] = next_model
    _save_runtime_override("LLM_MODEL_ID", next_model)
    return LLMModelUpdateResponse(model_id=effective_model)


@router.get("/stt/status", response_model=STTStatusResponse)
def stt_status(_=Depends(auth_dep)) -> STTStatusResponse:
    s = get_settings()
    runtime = stt_runtime_status()
    return STTStatusResponse(
        provider=str(getattr(s, "stt_provider", "unknown") or "unknown"),
        model_id=str(getattr(s, "whisper_model_size", "") or "").strip(),
        warmup_started=bool(runtime.get("warmup_started", False)),
        warmup_ready=bool(runtime.get("warmup_ready", False)),
        warmup_error=str(runtime.get("warmup_error") or ""),
        provider_initialized=bool(runtime.get("provider_initialized", False)),
    )


@router.get("/stt/models", response_model=STTModelsResponse)
def stt_models(_=Depends(auth_dep)) -> STTModelsResponse:
    s = get_settings()
    current = str(getattr(s, "whisper_model_size", "") or "").strip()
    return STTModelsResponse(models=_stt_model_catalog(), current_model=current)


@router.post("/stt/model", response_model=STTModelUpdateResponse)
def stt_update_model(req: STTModelUpdateRequest, _=Depends(auth_dep)) -> STTModelUpdateResponse:
    next_model = str(req.model_id or "").strip()
    if not next_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required")
    supported = _stt_model_catalog()
    if next_model not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"STT model '{next_model}' is not supported in UI profile. "
                f"Available: {', '.join(supported)}"
            ),
        )

    s = get_settings()
    s.whisper_model_size = next_model
    os.environ["WHISPER_MODEL_SIZE"] = next_model
    _save_runtime_override("WHISPER_MODEL_SIZE", next_model)
    reset_stt_provider_runtime(restart_warmup=True)
    return STTModelUpdateResponse(model_id=next_model)


@router.get("/llm/embeddings/status", response_model=EmbeddingStatusResponse)
def embedding_status(_=Depends(auth_dep)) -> EmbeddingStatusResponse:
    s = get_settings()
    vector_enabled = bool(getattr(s, "rag_vector_enabled", True))
    provider_requested = _embedding_provider_requested()
    api_base = _embedding_api_base()
    model_id = str(getattr(s, "embedding_model_id", "") or "").strip()
    can_use_openai = bool(api_base and model_id)
    if not vector_enabled:
        return EmbeddingStatusResponse(
            vector_enabled=False,
            provider_requested=provider_requested,
            provider="disabled",
            api_base=api_base,
            model_id=model_id,
            available=False,
            message="RAG vector retrieval disabled (RAG_VECTOR_ENABLED=false)",
        )
    if provider_requested == "hashing":
        return EmbeddingStatusResponse(
            vector_enabled=True,
            provider_requested=provider_requested,
            provider="hashing_local",
            api_base="",
            model_id=model_id or "hashing_local",
            available=True,
            message="Local hashing embeddings fallback (offline)",
        )
    if not can_use_openai:
        return EmbeddingStatusResponse(
            vector_enabled=True,
            provider_requested=provider_requested,
            provider="hashing_local",
            api_base=api_base,
            model_id=model_id or "nomic-embed-text",
            available=True,
            message="Embedding provider config is incomplete; using hashing fallback",
        )

    try:
        models = _filter_embedding_models(
            _fetch_openai_compat_models(
                api_base=api_base,
                api_key=_embedding_api_key(),
                timeout_s=max(3, int(getattr(s, "rag_embedding_request_timeout_sec", 8.0) or 8)),
            )
        )
    except HTTPException as exc:
        detail = str(exc.detail or "provider unavailable")
        provider_name = "ollama_openai_compat" if _is_local_base(api_base) else "openai_compat"
        return EmbeddingStatusResponse(
            vector_enabled=True,
            provider_requested=provider_requested,
            provider=provider_name,
            api_base=api_base,
            model_id=model_id,
            available=False,
            message=f"{detail}; RAG will fall back to hashing",
        )

    provider_name = "ollama_openai_compat" if _is_local_base(api_base) else "openai_compat"
    if model_id and model_id in models:
        msg = "Embeddings provider ready"
    elif model_id:
        if _is_embedding_model(model_id):
            msg = (
                f"Embeddings API ready, model '{model_id}' not found "
                "(hashing fallback will be used)"
            )
        else:
            msg = (
                f"Model '{model_id}' is not an embedding model "
                "(hashing fallback will be used)"
            )
    else:
        msg = "Embeddings API ready, model is not selected"
    return EmbeddingStatusResponse(
        vector_enabled=True,
        provider_requested=provider_requested,
        provider=provider_name,
        api_base=api_base,
        model_id=model_id,
        available=True,
        message=msg,
    )


@router.get("/llm/embeddings/models", response_model=EmbeddingModelsResponse)
def embedding_models(_=Depends(auth_dep)) -> EmbeddingModelsResponse:
    s = get_settings()
    api_base = _embedding_api_base()
    api_key = _embedding_api_key()
    models = _filter_embedding_models(
        _fetch_openai_compat_models(
            api_base=api_base,
            api_key=api_key,
            timeout_s=max(3, int(getattr(s, "rag_embedding_request_timeout_sec", 8.0) or 8)),
        )
    )
    current = str(getattr(s, "embedding_model_id", "") or "").strip()
    present, _exact, matched = _resolve_model_match(current, models)
    if present and matched:
        current = matched
    else:
        current = ""
    return EmbeddingModelsResponse(models=models, current_model=current)


@router.post("/llm/embeddings/model", response_model=EmbeddingModelUpdateResponse)
def embedding_update_model(
    req: EmbeddingModelUpdateRequest, _=Depends(auth_dep)
) -> EmbeddingModelUpdateResponse:
    next_model = req.model_id.strip()
    if not next_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required")
    if not _is_embedding_model(next_model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Model '{next_model}' is not an embedding model. "
                "Select an embedding model in Embeddings section."
            ),
        )
    s = get_settings()
    models = _filter_embedding_models(
        _fetch_openai_compat_models(
            api_base=_embedding_api_base(),
            api_key=_embedding_api_key(),
            timeout_s=max(3, int(getattr(s, "rag_embedding_request_timeout_sec", 8.0) or 8)),
        )
    )
    present, exact, matched = _resolve_model_match(next_model, models)
    if not present:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Embedding model '{next_model}' is not installed in provider. "
                f"Available embedding models: {_available_models_hint(models)}"
            ),
        )
    effective_model = matched if matched else next_model
    if not exact and matched:
        next_model = matched

    s.embedding_model_id = next_model
    os.environ["EMBEDDING_MODEL_ID"] = next_model
    _save_runtime_override("EMBEDDING_MODEL_ID", next_model)
    return EmbeddingModelUpdateResponse(model_id=effective_model)
