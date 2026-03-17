from __future__ import annotations

from urllib.parse import urlparse

import requests

from interview_analytics_agent.common.config import Settings, get_settings
from interview_analytics_agent.common.provider_settings import (
    provider_display_name,
    resolve_llm_endpoint,
    resolve_llm_provider,
)
from interview_analytics_agent.llm.anthropic import AnthropicProvider
from interview_analytics_agent.llm.gemini import GeminiProvider
from interview_analytics_agent.llm.mock import MockLLMProvider
from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider


def _is_local_openai_base(api_base: str) -> bool:
    value = (api_base or "").strip()
    if not value:
        return False
    try:
        host = (urlparse(value).hostname or "").strip().lower()
    except Exception:
        host = ""
    return host in {"127.0.0.1", "localhost"}


def _openai_headers(api_base: str, api_key: str) -> dict[str, str]:
    token = str(api_key or "").strip()
    if not token and _is_local_openai_base(api_base):
        token = "ollama"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def list_models_for_endpoint(
    *,
    provider: str,
    api_base: str,
    api_key: str,
    timeout_s: int = 10,
) -> list[str]:
    effective_timeout = max(3, int(timeout_s or 10))

    if provider == "mock":
        return []

    if provider in {"openai_compat", "openai"}:
        url = str(api_base or "").rstrip("/") + "/models"
        resp = requests.get(url, headers=_openai_headers(api_base, api_key), timeout=effective_timeout)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("data") if isinstance(payload, dict) else []
        return _extract_ids(rows)

    if provider == "anthropic":
        url = str(api_base or "").rstrip("/") + "/models"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        resp = requests.get(url, headers=headers, timeout=effective_timeout)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("data") if isinstance(payload, dict) else []
        return _extract_ids(rows)

    if provider == "gemini":
        url = str(api_base or "").rstrip("/") + f"/models?key={api_key}"
        resp = requests.get(url, headers={"Content-Type": "application/json"}, timeout=effective_timeout)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("models") if isinstance(payload, dict) else []
        models = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            models.append(name.removeprefix("models/"))
        return _dedupe(models)

    return []


def list_llm_models(settings: Settings | None = None, *, timeout_s: int = 10) -> list[str]:
    s = settings or get_settings()
    endpoint = resolve_llm_endpoint(s)
    provider = resolve_llm_provider(s)
    return list_models_for_endpoint(
        provider=provider,
        api_base=endpoint.api_base,
        api_key=endpoint.api_key,
        timeout_s=timeout_s,
    )


def _extract_ids(rows: object) -> list[str]:
    models: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                value = str(row.get("id") or "").strip()
                if value:
                    models.append(value)
    return _dedupe(models)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_llm_provider(settings: Settings | None = None):
    s = settings or get_settings()
    provider = resolve_llm_provider(s)
    if provider == "mock":
        return MockLLMProvider()
    if provider in {"openai_compat", "openai"}:
        return OpenAICompatProvider()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "gemini":
        return GeminiProvider()
    return MockLLMProvider()


def llm_provider_label(settings: Settings | None = None) -> str:
    return provider_display_name(resolve_llm_provider(settings or get_settings()))
