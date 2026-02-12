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

import logging
import re

from interview_analytics_agent.common.config import get_settings

from .pii import mask_pii

FILLER_RE = re.compile(r"\b(ээ+|мм+|ну+|типа|как бы|в общем|короче)\b", re.IGNORECASE)
MULTISPACE_RE = re.compile(r"\s+")
log = logging.getLogger(__name__)


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

            has_api_base = bool((settings.openai_api_base or "").strip())
            has_api_key = bool((settings.openai_api_key or "").strip())
            provider = (
                OpenAICompatProvider()
                if (has_api_base or has_api_key)
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


def _split_text_for_llm(text: str, *, max_chars: int) -> list[str]:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    limit = max(600, int(max_chars or 1800))
    for line in lines:
        line_len = len(line) + (1 if current else 0)
        if current and current_len + line_len > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def _build_transcript_cleanup_orchestrator():
    s = get_settings()
    if not s.llm_enabled or not bool(getattr(s, "llm_transcript_cleanup_enabled", True)):
        return None
    has_api_base = bool((s.openai_api_base or "").strip())
    has_api_key = bool((s.openai_api_key or "").strip())
    if not has_api_base and not has_api_key:
        return None

    from interview_analytics_agent.llm.openai_compat import OpenAICompatProvider
    from interview_analytics_agent.llm.orchestrator import LLMOrchestrator

    return LLMOrchestrator(OpenAICompatProvider())


def cleanup_transcript_with_llm(transcript: str) -> tuple[str, dict]:
    """
    Сглаживает финальный clean-транскрипт целиком:
    - исправляет очевидные ASR-ошибки
    - сохраняет speaker-префиксы вида `speaker: text`
    - не добавляет новые факты
    """
    s = get_settings()
    meta: dict = {"applied": [], "chunks": 0, "errors": 0}
    text = (transcript or "").strip()
    if not text:
        return transcript, meta

    try:
        orch = _build_transcript_cleanup_orchestrator()
    except Exception as err:
        log.warning(
            "llm_transcript_cleanup_init_failed",
            extra={"payload": {"err": str(err)[:200]}},
        )
        return transcript, meta
    if orch is None:
        return transcript, meta

    max_chars = int(getattr(s, "llm_transcript_cleanup_chunk_chars", 1800) or 1800)
    chunks = _split_text_for_llm(text, max_chars=max_chars)
    if not chunks:
        return transcript, meta

    cleaned_chunks: list[str] = []
    system = (
        "Исправь транскрипт после ASR. Верни ТОЛЬКО очищенный текст без JSON. "
        "Сохраняй язык и смысл, не добавляй новых фактов. "
        "Если в строке есть speaker-префикс вида `name:`, сохрани его."
    )
    for chunk in chunks:
        user = f"Текст:\n{chunk}"
        try:
            result = orch.complete_text(system=system, user=user).text.strip()
            cleaned_chunks.append(result or chunk)
            meta["chunks"] += 1
        except Exception as err:
            meta["errors"] += 1
            cleaned_chunks.append(chunk)
            log.warning(
                "llm_transcript_cleanup_failed_chunk",
                extra={"payload": {"err": str(err)[:200]}},
            )

    cleaned = "\n".join([c for c in cleaned_chunks if c]).strip()
    if cleaned and cleaned != text:
        meta["applied"].append("llm_transcript_cleanup")
        return cleaned, meta
    return transcript, meta
