"""
Улучшение текста (enhancer).

Назначение:
- пунктуация/нормализация
- удаление "ээ/мм" и мусора
- приведение терминов (в будущем)
- (опционально) PII маскирование

На старте: простые эвристики + возможность подключить LLM позже.
"""

from __future__ import annotations

import re

from interview_analytics_agent.common.config import get_settings

from .pii import mask_pii

FILLER_RE = re.compile(r"\b(ээ+|мм+|ну+|типа|как бы|в общем|короче)\b", re.IGNORECASE)
MULTISPACE_RE = re.compile(r"\s+")


def enhance_text(raw_text: str) -> tuple[str, dict]:
    """
    Возвращает:
    - улучшенный текст
    - метаданные преобразований (для трассировки)
    """
    settings = get_settings()
    meta: dict = {"applied": []}

    if not raw_text:
        return raw_text, meta

    text = raw_text

    # 0) LLM live (опционально)
    if settings.llm_enabled and settings.llm_live_enabled:
        try:
            from interview_analytics_agent.llm.mock import MockLLMProvider
            from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider
            from interview_analytics_agent.llm.orchestrator import LLMOrchestrator

            provider = (
                OpenAICompatProvider()
                if (settings.openai_api_key or "")
                else MockLLMProvider()
            )
            orch = LLMOrchestrator(provider)
            system = (
                "Ты помогаешь очистить транскрипт. Верни ТОЛЬКО JSON: "
                "{clean_text: str}. Убери слова-паразиты и лишние повторы, "
                "сохрани смысл. Не добавляй нового."
            )
            user = f"Текст:\n{text}"
            data = orch.complete_json(system=system, user=user)
            clean_text = (data.get("clean_text") or "").strip()
            if clean_text:
                meta["applied"].append("llm_live_cleanup")
                text = clean_text
        except Exception:
            # fallback на эвристики ниже
            pass

    # 1) удаляем слова-паразиты
    text2 = FILLER_RE.sub("", text)
    if text2 != text:
        meta["applied"].append("filler_cleanup")
        text = text2

    # 2) нормализуем пробелы
    text2 = MULTISPACE_RE.sub(" ", text).strip()
    if text2 != text:
        meta["applied"].append("whitespace_normalize")
        text = text2

    # 3) простейшая "псевдо-пунктуация" (MVP):
    # если нет точки в конце — добавим.
    if text and text[-1] not in ".!?":
        text += "."
        meta["applied"].append("final_punct")

    # 4) PII маскирование по политике
    if settings.pii_masking:
        masked = mask_pii(text)
        if masked != text:
            meta["applied"].append("pii_mask")
            text = masked

    return text, meta
