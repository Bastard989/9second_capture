from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.common.errors import ErrCode, ProviderError

log = logging.getLogger(__name__)


@dataclass
class OpenAICompatConfig:
    """Настройки OpenAI-compatible API."""

    api_base: str
    api_key: str
    model: str = "gpt-4o-mini"
    timeout_s: int = 60


class OpenAICompatProvider:
    """Минимальный провайдер LLM через OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        s = get_settings()
        api_base = (getattr(s, "openai_api_base", "") or "").strip()
        api_key = (getattr(s, "openai_api_key", "") or "").strip()
        model = getattr(s, "llm_model_id", "gpt-4o-mini") or "gpt-4o-mini"
        timeout_s = int(getattr(s, "llm_request_timeout_sec", 60) or 60)

        if not api_base:
            raise ProviderError(ErrCode.LLM_PROVIDER_ERROR, "OPENAI_API_BASE не задан")
        if not api_key and ("127.0.0.1" in api_base or "localhost" in api_base):
            # Для локальных OpenAI-compatible провайдеров (например, Ollama)
            # часто достаточно фиктивного bearer token.
            api_key = "ollama"
        if not api_key:
            raise ProviderError(ErrCode.LLM_PROVIDER_ERROR, "OPENAI_API_KEY не задан")

        self.cfg = OpenAICompatConfig(
            api_base=api_base, api_key=api_key, model=model, timeout_s=timeout_s
        )

    def _models_url(self) -> str:
        return self.cfg.api_base.rstrip("/") + "/models"

    def _chat_url(self) -> str:
        return self.cfg.api_base.rstrip("/") + "/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        return headers

    def is_available(self, timeout_s: float = 2.5) -> bool:
        try:
            resp = requests.get(
                self._models_url(),
                headers=self._headers(),
                timeout=max(0.8, float(timeout_s)),
            )
        except requests.RequestException:
            return False
        return resp.status_code < 400

    def complete_text(self, *, system: str, user: str) -> str:
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }

        try:
            resp = requests.post(
                self._chat_url(),
                headers=self._headers(),
                json=payload,
                timeout=self.cfg.timeout_s,
            )
        except requests.RequestException as e:
            log.error(
                "llm_http_error",
                extra={"provider": "openai_compat", "payload": {"err": str(e)}},
            )
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Ошибка HTTP при вызове LLM",
                {"err": str(e)},
            ) from e

        if resp.status_code >= 400:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "LLM вернул ошибку",
                {"status": resp.status_code, "text_head": resp.text[:500]},
            )

        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "LLM вернул невалидный JSON",
                {"err": str(e), "text_head": resp.text[:500]},
            ) from e

        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "Не удалось извлечь текст из ответа LLM",
                {"err": str(e), "data_head": str(data)[:500]},
            ) from e
