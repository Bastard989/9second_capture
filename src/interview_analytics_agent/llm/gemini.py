from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, ProviderError
from interview_analytics_agent.common.provider_settings import resolve_llm_endpoint

log = logging.getLogger(__name__)


@dataclass
class GeminiConfig:
    api_base: str
    api_key: str
    model: str
    timeout_s: Optional[int]
    max_tokens: Optional[int]
    temperature: float
    top_p: float


class GeminiProvider:
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
        if not endpoint.api_base:
            raise ProviderError(ErrCode.LLM_PROVIDER_ERROR, "LLM_API_BASE не задан")
        if not endpoint.api_key:
            raise ProviderError(ErrCode.LLM_PROVIDER_ERROR, "LLM_API_KEY не задан")
        self.cfg = GeminiConfig(
            api_base=endpoint.api_base,
            api_key=endpoint.api_key,
            model=(endpoint.model_id or "gemini-2.0-flash").removeprefix("models/"),
            timeout_s=timeout_opt,
            max_tokens=max_tokens_opt,
            temperature=float(getattr(s, "llm_temperature", 0.2) or 0.2),
            top_p=float(getattr(s, "llm_top_p", 0.95) or 0.95),
        )

    def _models_url(self) -> str:
        return self.cfg.api_base.rstrip("/") + f"/models?key={self.cfg.api_key}"

    def _generate_url(self) -> str:
        return self.cfg.api_base.rstrip("/") + f"/models/{self.cfg.model}:generateContent?key={self.cfg.api_key}"

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def is_available(self, timeout_s: float = 2.5) -> bool:
        try:
            resp = requests.get(self._models_url(), headers=self._headers(), timeout=max(0.8, float(timeout_s)))
        except requests.RequestException:
            return False
        return resp.status_code < 400

    def complete_text(self, *, system: str, user: str) -> str:
        generation_config: dict[str, object] = {
            "temperature": self.cfg.temperature,
            "topP": self.cfg.top_p,
        }
        if self.cfg.max_tokens is not None:
            generation_config["maxOutputTokens"] = self.cfg.max_tokens
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": generation_config,
        }
        try:
            resp = requests.post(
                self._generate_url(),
                headers=self._headers(),
                json=payload,
                timeout=self.cfg.timeout_s,
            )
        except requests.RequestException as e:
            log.error("llm_http_error", extra={"provider": "gemini", "payload": {"err": str(e)}})
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Ошибка HTTP при вызове Gemini",
                {"err": str(e)},
            ) from e
        if resp.status_code >= 400:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Gemini вернул ошибку",
                {"status": resp.status_code, "text_head": resp.text[:500]},
            )
        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Gemini вернул невалидный JSON",
                {"err": str(e), "text_head": resp.text[:500]},
            ) from e
        try:
            candidates = data.get("candidates") if isinstance(data, dict) else None
            if not isinstance(candidates, list) or not candidates:
                raise KeyError("candidates")
            first = candidates[0] if isinstance(candidates[0], dict) else {}
            content = first.get("content") if isinstance(first, dict) else {}
            parts = content.get("parts") if isinstance(content, dict) else None
            if not isinstance(parts, list):
                raise KeyError("parts")
            out_parts = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                text = str(part.get("text") or "")
                if text:
                    out_parts.append(text)
            out = "\n".join(out_parts).strip()
            if not out:
                raise KeyError("text")
            return out
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Не удалось извлечь текст из ответа Gemini",
                {"err": str(e), "data_head": str(data)[:500]},
            ) from e
