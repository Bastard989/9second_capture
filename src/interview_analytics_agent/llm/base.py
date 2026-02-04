"""
Базовые типы для LLM.

Задача:
- единый контракт провайдера для orchestrator
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Интерфейс провайдера LLM.
    """

    @abstractmethod
    def complete_text(self, *, system: str, user: str) -> str:
        """
        Сгенерировать текстовый ответ.
        """
        raise NotImplementedError
