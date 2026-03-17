from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from apps.api_gateway.deps import auth_dep
from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.provider_settings import (
    default_embedding_api_base,
    default_llm_api_base,
    normalize_embedding_provider,
    normalize_llm_provider,
    normalize_stt_provider,
    provider_display_name,
    resolve_embedding_endpoint,
    resolve_embedding_provider,
    resolve_llm_endpoint,
    resolve_llm_provider,
    resolve_stt_model_id,
)
from interview_analytics_agent.llm.factory import list_llm_models
from interview_analytics_agent.services.local_pipeline import (
    reset_stt_provider_runtime,
    stt_runtime_status,
    verify_stt_provider_connection,
)

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


class LLMConfigResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str
    provider_label: str
    api_base: str
    api_key_set: bool
    model_id: str
    llm_enabled: bool


class LLMConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str = Field(min_length=2, max_length=40)
    api_base: str = Field(default="", max_length=300)
    api_key: str = Field(default="", max_length=1000)
    clear_api_key: bool = False
    model_id: str = Field(default="", max_length=200)
    llm_enabled: bool | None = None


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
    message: str = ""
    provider_ready: bool = True
    warmup_started: bool
    warmup_ready: bool
    warmup_error: str = ""
    provider_initialized: bool


class STTModelsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    models: list[str] = Field(default_factory=list)
    current_model: str


class STTConfigResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str
    provider_label: str
    model_id: str
    google_service_account_set: bool = False
    google_recognize_url: str = ""
    salutespeech_client_id: str = ""
    salutespeech_client_secret_set: bool = False
    salutespeech_auth_url: str = ""
    salutespeech_recognize_url: str = ""
    salutespeech_scope: str = ""


class STTConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str = Field(min_length=2, max_length=40)
    model_id: str = Field(default="", max_length=200)
    google_service_account_json: str = Field(default="", max_length=20000)
    clear_google_service_account_json: bool = False
    google_recognize_url: str = Field(default="", max_length=400)
    salutespeech_client_id: str = Field(default="", max_length=400)
    salutespeech_client_secret: str = Field(default="", max_length=2000)
    clear_salutespeech_client_secret: bool = False
    salutespeech_auth_url: str = Field(default="", max_length=400)
    salutespeech_recognize_url: str = Field(default="", max_length=400)
    salutespeech_scope: str = Field(default="", max_length=200)


class STTModelUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(min_length=1, max_length=200)


class STTModelUpdateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    model_id: str


class STTVerifyResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    provider: str
    message: str = ""


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


class EmbeddingConfigResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str
    provider_label: str
    api_base: str
    api_key_set: bool
    model_id: str
    vector_enabled: bool


class EmbeddingConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str = Field(min_length=2, max_length=40)
    api_base: str = Field(default="", max_length=300)
    api_key: str = Field(default="", max_length=1000)
    clear_api_key: bool = False
    model_id: str = Field(default="", max_length=200)
    vector_enabled: bool | None = None


class EmbeddingModelUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(min_length=1, max_length=200)


class EmbeddingModelUpdateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool = True
    model_id: str


def _fetch_provider_models(*, provider: str, api_base: str, api_key: str, timeout_s: int) -> list[str]:
    base = (api_base or "").strip()
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider != "mock" and normalized_provider != "hashing" and not base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API base is not configured",
        )
    try:
        return list_llm_models_for_current_provider(
            provider=normalized_provider,
            api_base=base,
            api_key=(api_key or "").strip(),
            timeout_s=timeout_s,
        )
    except requests.HTTPError as err:
        resp = getattr(err, "response", None)
        status_code = int(getattr(resp, "status_code", 502) or 502)
        text = str(getattr(resp, "text", "") or "")[:300]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider returned HTTP {status_code}: {text}",
        ) from err
    except requests.RequestException as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider is unavailable: {err}",
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider returned invalid response: {err}",
        ) from err


def _fetch_openai_compat_models(*, api_base: str, api_key: str, timeout_s: int) -> list[str]:
    return _fetch_provider_models(
        provider="openai_compat",
        api_base=api_base,
        api_key=api_key,
        timeout_s=timeout_s,
    )


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


def _stt_model_catalog(provider: str = "whisper_local") -> list[str]:
    normalized = normalize_stt_provider(provider)
    if normalized == "google":
        return ["latest_long", "latest_short", "telephony", "default"]
    if normalized == "salutespeech":
        return ["general", "callcenter"]
    if normalized == "mock":
        return ["mock"]
    return [
        "tiny",
        "base",
        "small",
        "medium",
        "large-v3",
    ]


def _looks_like_google_service_account_placeholder(raw_json: str) -> bool:
    value = str(raw_json or "").strip()
    if not value:
        return True
    lowered = value.lower()
    if "example.iam.gserviceaccount.com" in lowered:
        return True
    if "<insert_google_service_account_json_here>" in lowered:
        return True
    return False


def _looks_like_salute_placeholder(*, client_id: str, client_secret: str) -> bool:
    left = str(client_id or "").strip().lower()
    right = str(client_secret or "").strip().lower()
    markers = {
        "demo-client",
        "demo-secret",
        "<insert_salutespeech_client_id_here>",
        "<insert_salutespeech_client_secret_here>",
    }
    return (
        not left
        or not right
        or left in markers
        or right in markers
        or "insert_" in left
        or "insert_" in right
        or left.startswith("example")
        or right.startswith("example")
    )


def _stt_provider_message() -> str:
    s = get_settings()
    provider = normalize_stt_provider(getattr(s, "stt_provider", "whisper_local"))
    if provider == "google":
        raw_json = str(getattr(s, "google_stt_service_account_json", "") or "").strip()
        if not raw_json:
            return "Для Google STT добавьте service account JSON в настройках STT."
        if _looks_like_google_service_account_placeholder(raw_json):
            return "Для Google STT сейчас сохранен пример JSON. Вставьте реальный service account JSON."
        return "Google STT готов к запуску по запросу."
    if provider == "salutespeech":
        client_id = str(getattr(s, "salutespeech_client_id", "") or "").strip()
        client_secret = str(getattr(s, "salutespeech_client_secret", "") or "").strip()
        if not client_id:
            return "Для SaluteSpeech укажите Client ID в настройках STT."
        if not client_secret:
            return "Для SaluteSpeech укажите Client Secret в настройках STT."
        if _looks_like_salute_placeholder(client_id=client_id, client_secret=client_secret):
            return "Для SaluteSpeech сейчас сохранены примерные данные. Укажите реальные Client ID и Client Secret."
        return "SaluteSpeech готов к запуску по запросу."
    if provider == "mock":
        return "Mock STT возвращает тестовый результат без реального распознавания."
    return ""


def _stt_provider_ready() -> bool:
    s = get_settings()
    provider = normalize_stt_provider(getattr(s, "stt_provider", "whisper_local"))
    if provider == "google":
        raw_json = str(getattr(s, "google_stt_service_account_json", "") or "").strip()
        return bool(raw_json) and not _looks_like_google_service_account_placeholder(raw_json)
    if provider == "salutespeech":
        client_id = str(getattr(s, "salutespeech_client_id", "") or "").strip()
        client_secret = str(getattr(s, "salutespeech_client_secret", "") or "").strip()
        return bool(
            client_id
            and client_secret
            and str(getattr(s, "salutespeech_auth_url", "") or "").strip()
            and str(getattr(s, "salutespeech_recognize_url", "") or "").strip()
            and not _looks_like_salute_placeholder(
                client_id=client_id,
                client_secret=client_secret,
            )
        )
    return True


def list_llm_models_for_current_provider(
    *,
    provider: str,
    api_base: str,
    api_key: str,
    timeout_s: int,
) -> list[str]:
    from interview_analytics_agent.llm.factory import list_models_for_endpoint

    return list_models_for_endpoint(
        provider=provider,
        api_base=api_base,
        api_key=api_key,
        timeout_s=timeout_s,
    )


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


def _delete_runtime_override(key: str) -> None:
    try:
        path = _runtime_override_file()
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return
        if key in raw:
            raw.pop(key, None)
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _set_env_and_override(key: str, value: str) -> None:
    os.environ[key] = value
    _save_runtime_override(key, value)


def _clear_env_and_override(key: str) -> None:
    os.environ.pop(key, None)
    _delete_runtime_override(key)


def _apply_llm_config_to_runtime(*, provider: str, api_base: str, api_key: str, model_id: str, llm_enabled: bool | None) -> None:
    s = get_settings()
    normalized_provider = normalize_llm_provider(provider)
    s.llm_provider = normalized_provider
    _set_env_and_override("LLM_PROVIDER", normalized_provider)

    s.llm_api_base = api_base or None
    if api_base:
        _set_env_and_override("LLM_API_BASE", api_base)
    else:
        _clear_env_and_override("LLM_API_BASE")

    s.llm_api_key = api_key or None
    if api_key:
        _set_env_and_override("LLM_API_KEY", api_key)
    else:
        _clear_env_and_override("LLM_API_KEY")

    if normalized_provider in {"openai_compat", "openai"}:
        if api_base:
            s.openai_api_base = api_base
            _set_env_and_override("OPENAI_API_BASE", api_base)
        elif normalized_provider == "openai":
            base = default_llm_api_base(normalized_provider)
            s.openai_api_base = base
            _set_env_and_override("OPENAI_API_BASE", base)
        else:
            s.openai_api_base = None
            _clear_env_and_override("OPENAI_API_BASE")
        if api_key:
            s.openai_api_key = api_key
            _set_env_and_override("OPENAI_API_KEY", api_key)
        else:
            s.openai_api_key = None
            _clear_env_and_override("OPENAI_API_KEY")
    else:
        s.openai_api_base = None
        s.openai_api_key = None
        _clear_env_and_override("OPENAI_API_BASE")
        _clear_env_and_override("OPENAI_API_KEY")

    if model_id:
        s.llm_model_id = model_id
        _set_env_and_override("LLM_MODEL_ID", model_id)
    if llm_enabled is not None:
        s.llm_enabled = bool(llm_enabled)
        _set_env_and_override("LLM_ENABLED", "true" if bool(llm_enabled) else "false")


def _apply_embedding_config_to_runtime(*, provider: str, api_base: str, api_key: str, model_id: str, vector_enabled: bool | None) -> None:
    s = get_settings()
    normalized_provider = normalize_embedding_provider(provider)
    s.embedding_provider = normalized_provider
    _set_env_and_override("EMBEDDING_PROVIDER", normalized_provider)
    s.rag_embedding_provider = "hashing" if normalized_provider == "hashing" else "openai_compat"
    _set_env_and_override("RAG_EMBEDDING_PROVIDER", s.rag_embedding_provider)

    s.embedding_api_base = api_base or None
    if api_base:
        _set_env_and_override("EMBEDDING_API_BASE", api_base)
    else:
        _clear_env_and_override("EMBEDDING_API_BASE")

    s.embedding_api_key = api_key or None
    if api_key:
        _set_env_and_override("EMBEDDING_API_KEY", api_key)
    else:
        _clear_env_and_override("EMBEDDING_API_KEY")

    if model_id:
        s.embedding_model_id = model_id
        _set_env_and_override("EMBEDDING_MODEL_ID", model_id)
    if vector_enabled is not None:
        s.rag_vector_enabled = bool(vector_enabled)
        _set_env_and_override("RAG_VECTOR_ENABLED", "true" if bool(vector_enabled) else "false")


def _apply_stt_config_to_runtime(*, provider: str, model_id: str) -> None:
    s = get_settings()
    normalized_provider = normalize_stt_provider(provider)
    s.stt_provider = normalized_provider
    _set_env_and_override("STT_PROVIDER", normalized_provider)
    if normalized_provider == "whisper_local":
        effective_model = model_id or str(getattr(s, "whisper_model_size", "") or "small")
        s.whisper_model_size = effective_model
        s.stt_model_id = effective_model
        _set_env_and_override("WHISPER_MODEL_SIZE", effective_model)
        _set_env_and_override("STT_MODEL_ID", effective_model)
    else:
        s.stt_model_id = model_id or None
        _clear_env_and_override("WHISPER_MODEL_SIZE")
        if model_id:
            _set_env_and_override("STT_MODEL_ID", model_id)
        else:
            _clear_env_and_override("STT_MODEL_ID")
    reset_stt_provider_runtime(restart_warmup=False)


def _apply_stt_provider_settings(
    provider: str,
    google_service_account_json: str | None = None,
    clear_google_service_account_json: bool = False,
    google_recognize_url: str | None = None,
    salutespeech_client_id: str | None = None,
    salutespeech_client_secret: str | None = None,
    clear_salutespeech_client_secret: bool = False,
    salutespeech_auth_url: str | None = None,
    salutespeech_recognize_url: str | None = None,
    salutespeech_scope: str | None = None,
) -> None:
    s = get_settings()
    normalized_provider = normalize_stt_provider(provider)

    if clear_google_service_account_json:
        s.google_stt_service_account_json = None
        _clear_env_and_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON")
    elif normalized_provider != "google":
        s.google_stt_service_account_json = None
        _clear_env_and_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON")
    elif google_service_account_json is not None:
        value = str(google_service_account_json or "").strip()
        s.google_stt_service_account_json = value or None
        if value:
            _set_env_and_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON", value)
        else:
            _clear_env_and_override("GOOGLE_STT_SERVICE_ACCOUNT_JSON")

    if normalized_provider == "google" and google_recognize_url is not None:
        value = str(google_recognize_url or "").strip()
        s.google_stt_recognize_url = value or "https://speech.googleapis.com/v1/speech:recognize"
        _set_env_and_override("GOOGLE_STT_RECOGNIZE_URL", s.google_stt_recognize_url)
    elif normalized_provider != "google":
        s.google_stt_recognize_url = "https://speech.googleapis.com/v1/speech:recognize"
        _clear_env_and_override("GOOGLE_STT_RECOGNIZE_URL")

    if normalized_provider != "salutespeech":
        s.salutespeech_client_id = None
        _clear_env_and_override("SALUTESPEECH_CLIENT_ID")
    elif salutespeech_client_id is not None:
        value = str(salutespeech_client_id or "").strip()
        s.salutespeech_client_id = value or None
        if value:
            _set_env_and_override("SALUTESPEECH_CLIENT_ID", value)
        else:
            _clear_env_and_override("SALUTESPEECH_CLIENT_ID")

    if clear_salutespeech_client_secret:
        s.salutespeech_client_secret = None
        _clear_env_and_override("SALUTESPEECH_CLIENT_SECRET")
    elif normalized_provider != "salutespeech":
        s.salutespeech_client_secret = None
        _clear_env_and_override("SALUTESPEECH_CLIENT_SECRET")
    elif salutespeech_client_secret is not None:
        value = str(salutespeech_client_secret or "").strip()
        s.salutespeech_client_secret = value or None
        if value:
            _set_env_and_override("SALUTESPEECH_CLIENT_SECRET", value)
        else:
            _clear_env_and_override("SALUTESPEECH_CLIENT_SECRET")

    if normalized_provider == "salutespeech" and salutespeech_auth_url is not None:
        value = str(salutespeech_auth_url or "").strip()
        s.salutespeech_auth_url = value or "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        _set_env_and_override("SALUTESPEECH_AUTH_URL", s.salutespeech_auth_url)
    elif normalized_provider != "salutespeech":
        s.salutespeech_auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        _clear_env_and_override("SALUTESPEECH_AUTH_URL")

    if normalized_provider == "salutespeech" and salutespeech_recognize_url is not None:
        value = str(salutespeech_recognize_url or "").strip()
        s.salutespeech_recognize_url = value or "https://smartspeech.sber.ru/rest/v1/speech:recognize"
        _set_env_and_override("SALUTESPEECH_RECOGNIZE_URL", s.salutespeech_recognize_url)
    elif normalized_provider != "salutespeech":
        s.salutespeech_recognize_url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
        _clear_env_and_override("SALUTESPEECH_RECOGNIZE_URL")

    if normalized_provider == "salutespeech" and salutespeech_scope is not None:
        value = str(salutespeech_scope or "").strip()
        s.salutespeech_scope = value or "SALUTE_SPEECH_PERS"
        _set_env_and_override("SALUTESPEECH_SCOPE", s.salutespeech_scope)
    elif normalized_provider != "salutespeech":
        s.salutespeech_scope = "SALUTE_SPEECH_PERS"
        _clear_env_and_override("SALUTESPEECH_SCOPE")


@router.get("/llm/status", response_model=LLMStatusResponse)
def llm_status(_=Depends(auth_dep)) -> LLMStatusResponse:
    s = get_settings()
    endpoint = resolve_llm_endpoint(s)
    provider = resolve_llm_provider(s)
    return LLMStatusResponse(
        llm_enabled=bool(s.llm_enabled),
        llm_live_enabled=bool(s.llm_live_enabled),
        api_base=endpoint.api_base,
        model_id=endpoint.model_id,
        provider=provider,
    )


@router.get("/llm/config", response_model=LLMConfigResponse)
def llm_config(_=Depends(auth_dep)) -> LLMConfigResponse:
    s = get_settings()
    endpoint = resolve_llm_endpoint(s)
    provider = resolve_llm_provider(s)
    return LLMConfigResponse(
        provider=provider,
        provider_label=provider_display_name(provider),
        api_base=endpoint.api_base,
        api_key_set=bool(endpoint.api_key),
        model_id=endpoint.model_id,
        llm_enabled=bool(s.llm_enabled),
    )


@router.post("/llm/config", response_model=LLMConfigResponse)
def llm_update_config(req: LLMConfigUpdateRequest, _=Depends(auth_dep)) -> LLMConfigResponse:
    provider = normalize_llm_provider(req.provider)
    current = resolve_llm_endpoint(get_settings())
    api_base = str(req.api_base or "").strip() or default_llm_api_base(provider)
    api_key = str(req.api_key or "").strip()
    if req.clear_api_key:
        api_key = ""
    elif not api_key:
        api_key = current.api_key
    model_id = str(req.model_id or "").strip() or current.model_id
    _apply_llm_config_to_runtime(
        provider=provider,
        api_base=api_base,
        api_key=api_key,
        model_id=model_id,
        llm_enabled=req.llm_enabled,
    )
    return llm_config(_)


@router.get("/llm/models", response_model=LLMModelsResponse)
def llm_models(_=Depends(auth_dep)) -> LLMModelsResponse:
    s = get_settings()
    endpoint = resolve_llm_endpoint(s)
    models = _filter_llm_chat_models(
        _fetch_provider_models(
            provider=resolve_llm_provider(s),
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
            timeout_s=int(s.llm_request_timeout_sec or 10),
        )
    )
    current = endpoint.model_id
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
    endpoint = resolve_llm_endpoint(s)
    models = _filter_llm_chat_models(
        _fetch_provider_models(
            provider=resolve_llm_provider(s),
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
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

    _apply_llm_config_to_runtime(
        provider=resolve_llm_provider(s),
        api_base=endpoint.api_base,
        api_key=endpoint.api_key,
        model_id=next_model,
        llm_enabled=None,
    )
    return LLMModelUpdateResponse(model_id=effective_model)


@router.get("/stt/status", response_model=STTStatusResponse)
def stt_status(_=Depends(auth_dep)) -> STTStatusResponse:
    s = get_settings()
    runtime = stt_runtime_status()
    return STTStatusResponse(
        provider=str(getattr(s, "stt_provider", "unknown") or "unknown"),
        model_id=resolve_stt_model_id(s),
        message=_stt_provider_message(),
        provider_ready=_stt_provider_ready(),
        warmup_started=bool(runtime.get("warmup_started", False)),
        warmup_ready=bool(runtime.get("warmup_ready", False)),
        warmup_error=str(runtime.get("warmup_error") or ""),
        provider_initialized=bool(runtime.get("provider_initialized", False)),
    )


@router.get("/stt/config", response_model=STTConfigResponse)
def stt_config(_=Depends(auth_dep)) -> STTConfigResponse:
    s = get_settings()
    provider = normalize_stt_provider(getattr(s, "stt_provider", "whisper_local"))
    return STTConfigResponse(
        provider=provider,
        provider_label=provider_display_name(provider),
        model_id=resolve_stt_model_id(s),
        google_service_account_set=bool(
            str(getattr(s, "google_stt_service_account_json", "") or "").strip()
        ),
        google_recognize_url=str(getattr(s, "google_stt_recognize_url", "") or "").strip(),
        salutespeech_client_id=str(getattr(s, "salutespeech_client_id", "") or "").strip(),
        salutespeech_client_secret_set=bool(
            str(getattr(s, "salutespeech_client_secret", "") or "").strip()
        ),
        salutespeech_auth_url=str(getattr(s, "salutespeech_auth_url", "") or "").strip(),
        salutespeech_recognize_url=str(
            getattr(s, "salutespeech_recognize_url", "") or ""
        ).strip(),
        salutespeech_scope=str(getattr(s, "salutespeech_scope", "") or "").strip(),
    )


@router.post("/stt/config", response_model=STTConfigResponse)
def stt_update_config(req: STTConfigUpdateRequest, _=Depends(auth_dep)) -> STTConfigResponse:
    current = get_settings()
    provider = normalize_stt_provider(req.provider)
    model_id = str(req.model_id or "").strip()
    google_service_account_json = str(req.google_service_account_json or "").strip()
    salutespeech_client_secret = str(req.salutespeech_client_secret or "").strip()
    _apply_stt_config_to_runtime(provider=provider, model_id=model_id)
    _apply_stt_provider_settings(
        provider=provider,
        google_service_account_json=None
        if (not google_service_account_json and not req.clear_google_service_account_json)
        else google_service_account_json,
        clear_google_service_account_json=bool(req.clear_google_service_account_json),
        google_recognize_url=str(req.google_recognize_url or "").strip()
        or str(getattr(current, "google_stt_recognize_url", "") or "").strip(),
        salutespeech_client_id=str(req.salutespeech_client_id or "").strip()
        or str(getattr(current, "salutespeech_client_id", "") or "").strip(),
        salutespeech_client_secret=None
        if (not salutespeech_client_secret and not req.clear_salutespeech_client_secret)
        else salutespeech_client_secret,
        clear_salutespeech_client_secret=bool(req.clear_salutespeech_client_secret),
        salutespeech_auth_url=str(req.salutespeech_auth_url or "").strip()
        or str(getattr(current, "salutespeech_auth_url", "") or "").strip(),
        salutespeech_recognize_url=str(req.salutespeech_recognize_url or "").strip()
        or str(getattr(current, "salutespeech_recognize_url", "") or "").strip(),
        salutespeech_scope=str(req.salutespeech_scope or "").strip()
        or str(getattr(current, "salutespeech_scope", "") or "").strip(),
    )
    return stt_config(_)


@router.get("/stt/models", response_model=STTModelsResponse)
def stt_models(_=Depends(auth_dep)) -> STTModelsResponse:
    s = get_settings()
    provider = normalize_stt_provider(getattr(s, "stt_provider", "whisper_local"))
    current = resolve_stt_model_id(s)
    models = _stt_model_catalog(provider)
    if current and current not in models:
        models = [current, *models]
    return STTModelsResponse(models=models, current_model=current or (models[0] if models else ""))


@router.post("/stt/model", response_model=STTModelUpdateResponse)
def stt_update_model(req: STTModelUpdateRequest, _=Depends(auth_dep)) -> STTModelUpdateResponse:
    next_model = str(req.model_id or "").strip()
    if not next_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required")
    s = get_settings()
    provider = normalize_stt_provider(getattr(s, "stt_provider", "whisper_local"))
    if provider != "whisper_local":
        _apply_stt_config_to_runtime(provider=provider, model_id=next_model)
        return STTModelUpdateResponse(model_id=next_model)
    supported = _stt_model_catalog(provider)
    if next_model not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"STT model '{next_model}' is not supported in UI profile. "
                f"Available: {', '.join(supported)}"
            ),
        )
    _apply_stt_config_to_runtime(provider=provider, model_id=next_model)
    return STTModelUpdateResponse(model_id=next_model)


@router.post("/stt/verify", response_model=STTVerifyResponse)
def stt_verify(_=Depends(auth_dep)) -> STTVerifyResponse:
    payload = verify_stt_provider_connection()
    return STTVerifyResponse(
        ok=bool(payload.get("ok", False)),
        provider=str(payload.get("provider") or "unknown"),
        message=str(payload.get("message") or ""),
    )


@router.get("/llm/embeddings/status", response_model=EmbeddingStatusResponse)
def embedding_status(_=Depends(auth_dep)) -> EmbeddingStatusResponse:
    s = get_settings()
    vector_enabled = bool(getattr(s, "rag_vector_enabled", True))
    provider_requested = resolve_embedding_provider(s)
    endpoint = resolve_embedding_endpoint(s)
    api_base = endpoint.api_base
    model_id = endpoint.model_id
    can_use_provider = bool(api_base and model_id)
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
    if not can_use_provider:
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
            _fetch_provider_models(
                provider=provider_requested,
                api_base=api_base,
                api_key=endpoint.api_key,
                timeout_s=max(3, int(getattr(s, "rag_embedding_request_timeout_sec", 8.0) or 8)),
            )
        )
    except HTTPException as exc:
        detail = str(exc.detail or "provider unavailable")
        provider_name = provider_display_name(provider_requested)
        return EmbeddingStatusResponse(
            vector_enabled=True,
            provider_requested=provider_requested,
            provider=provider_name,
            api_base=api_base,
            model_id=model_id,
            available=False,
            message=f"{detail}; RAG will fall back to hashing",
        )

    provider_name = provider_display_name(provider_requested)
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
    endpoint = resolve_embedding_endpoint(s)
    models = _filter_embedding_models(
        _fetch_provider_models(
            provider=resolve_embedding_provider(s),
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
            timeout_s=max(3, int(getattr(s, "rag_embedding_request_timeout_sec", 8.0) or 8)),
        )
    )
    current = endpoint.model_id
    present, _exact, matched = _resolve_model_match(current, models)
    if present and matched:
        current = matched
    else:
        current = ""
    return EmbeddingModelsResponse(models=models, current_model=current)


@router.get("/llm/embeddings/config", response_model=EmbeddingConfigResponse)
def embedding_config(_=Depends(auth_dep)) -> EmbeddingConfigResponse:
    s = get_settings()
    endpoint = resolve_embedding_endpoint(s)
    provider = resolve_embedding_provider(s)
    return EmbeddingConfigResponse(
        provider=provider,
        provider_label=provider_display_name(provider),
        api_base=endpoint.api_base,
        api_key_set=bool(endpoint.api_key),
        model_id=endpoint.model_id,
        vector_enabled=bool(getattr(s, "rag_vector_enabled", True)),
    )


@router.post("/llm/embeddings/config", response_model=EmbeddingConfigResponse)
def embedding_update_config(
    req: EmbeddingConfigUpdateRequest, _=Depends(auth_dep)
) -> EmbeddingConfigResponse:
    provider = normalize_embedding_provider(req.provider)
    current = resolve_embedding_endpoint(get_settings())
    api_base = str(req.api_base or "").strip()
    if not api_base:
        api_base = default_embedding_api_base(provider)
    api_key = str(req.api_key or "").strip()
    if req.clear_api_key:
        api_key = ""
    elif not api_key:
        api_key = current.api_key
    _apply_embedding_config_to_runtime(
        provider=provider,
        api_base=api_base,
        api_key=api_key,
        model_id=str(req.model_id or "").strip() or current.model_id,
        vector_enabled=req.vector_enabled,
    )
    return embedding_config(_)


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
    endpoint = resolve_embedding_endpoint(s)
    models = _filter_embedding_models(
        _fetch_provider_models(
            provider=resolve_embedding_provider(s),
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
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

    _apply_embedding_config_to_runtime(
        provider=resolve_embedding_provider(s),
        api_base=endpoint.api_base,
        api_key=endpoint.api_key,
        model_id=next_model,
        vector_enabled=None,
    )
    return EmbeddingModelUpdateResponse(model_id=effective_model)
