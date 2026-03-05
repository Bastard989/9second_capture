from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from interview_analytics_agent.common.errors import ErrCode, ProviderError

log = logging.getLogger(__name__)


@dataclass
class LLMTextResult:
    text: str


class LLMOrchestrator:
    """Оркестратор вызовов LLM: единый single-call и валидация JSON.

    Важная идея: здесь нет логики провайдера, только orchestration.
    Провайдер должен иметь метод complete_text(system=..., user=...) -> str.
    """

    def __init__(self, provider: Any) -> None:
        self.provider = provider

    def _single_call(self, **kwargs: Any) -> str:
        try:
            return self.provider.complete_text(**kwargs)
        except Exception as err:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "LLM не ответил",
                {"err": str(err)},
            ) from err

    def complete_text(self, *, system: str, user: str) -> LLMTextResult:
        text = self._single_call(system=system, user=user)
        return LLMTextResult(text=text)

    def complete_json(self, *, system: str, user: str) -> dict:
        """Возвращает распарсенный JSON (dict)."""
        res = self.complete_text(system=system, user=user)
        try:
            return json.loads(res.text)
        except Exception as e:
            raise ProviderError(
                ErrCode.LLM_PROVIDER_ERROR,
                "LLM вернул невалидный JSON",
                {"err": str(e), "text_head": res.text[:500]},
            ) from e
