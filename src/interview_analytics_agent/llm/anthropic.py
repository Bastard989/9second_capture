from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, ProviderError
from interview_analytics_agent.common.provider_settings import resolve_llm_endpoint

log = logging.getLogger(__name__)

_ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class AnthropicConfig:
    api_base: str
    api_key: str
    model: str
    timeout_s: Optional[int]
    max_tokens: Optional[int]
    temperature: float
    top_p: float


class AnthropicProvider:
    def __init__(self) -> None:
        s = get_settings()
        endpoint = resolve_llm_endpoint(s)
        timeout_raw = getattr(s, "llm_request_timeout_sec", 60)
        max_tokens_raw = getattr(s, "llm_max_tokens", 900)
        try:
            timeout_s = int(timeout_raw)
        except Exception:
            timeout_s = 60
        timeout_opt: Optional[int] = None if timeout_s <= 0 else max(1, timeout_s)
        try:
            max_tokens = int(max_tokens_raw)
        except Exception:
            max_tokens = 900
        max_tokens_opt: Optional[int] = None if max_tokens <= 0 else max(64, max_tokens)
        temperature = float(getattr(s, "llm_temperature", 0.2) or 0.2)
        top_p = float(getattr(s, "llm_top_p", 0.95) or 0.95)
        if not endpoint.api_base:
            raise ProviderError(ErrCode.LLM_PROVIDER_ERROR, "LLM_API_BASE не задан")
        if not endpoint.api_key:
            raise ProviderError(ErrCode.LLM_PROVIDER_ERROR, "LLM_API_KEY не задан")
        self.cfg = AnthropicConfig(
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
            model=endpoint.model_id or "claude-3-5-sonnet-latest",
            timeout_s=timeout_opt,
            max_tokens=max_tokens_opt,
            temperature=temperature,
            top_p=top_p,
        )

    def _models_url(self) -> str:
        return self.cfg.api_base.rstrip("/") + "/models"

    def _messages_url(self) -> str:
        return self.cfg.api_base.rstrip("/") + "/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.cfg.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    def is_available(self, timeout_s: float = 2.5) -> bool:
        try:
            resp = requests.get(self._models_url(), headers=self._headers(), timeout=max(0.8, float(timeout_s)))
        except requests.RequestException:
            return False
        return resp.status_code < 400

    def complete_text(self, *, system: str, user: str) -> str:
        payload: dict[str, object] = {
            "model": self.cfg.model,
            "messages": [{"role": "user", "content": user}],
            "system": system,
            "temperature": self.cfg.temperature,
            "top_p": self.cfg.top_p,
        }
        if self.cfg.max_tokens is not None:
            payload["max_tokens"] = self.cfg.max_tokens
        try:
            resp = requests.post(
                self._messages_url(),
                headers=self._headers(),
                json=payload,
                timeout=self.cfg.timeout_s,
            )
        except requests.RequestException as e:
            log.error("llm_http_error", extra={"provider": "anthropic", "payload": {"err": str(e)}})
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Ошибка HTTP при вызове Anthropic",
                {"err": str(e)},
            ) from e
        if resp.status_code >= 400:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Anthropic вернул ошибку",
                {"status": resp.status_code, "text_head": resp.text[:500]},
            )
        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Anthropic вернул невалидный JSON",
                {"err": str(e), "text_head": resp.text[:500]},
            ) from e
        try:
            content = data.get("content") if isinstance(data, dict) else None
            if not isinstance(content, list):
                raise KeyError("content")
            parts = []
            for row in content:
                if not isinstance(row, dict):
                    continue
                if str(row.get("type") or "").strip().lower() != "text":
                    continue
                text = str(row.get("text") or "")
                if text:
                    parts.append(text)
            out = "\n".join(part for part in parts if part).strip()
            if not out:
                raise KeyError("text")
            return out
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Не удалось извлечь текст из ответа Anthropic",
                {"err": str(e), "data_head": str(data)[:500]},
            ) from e
