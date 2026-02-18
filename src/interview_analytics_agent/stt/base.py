"""
Базовый интерфейс STT (Speech-to-Text).

Назначение:
- единый контракт для всех провайдеров
- потоковая и пакетная обработка
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class STTResult:
    text: str
    confidence: float | None = None
    speaker: str | None = None


class STTProvider(Protocol):
    def transcribe_chunk(
        self,
        *,
        audio: bytes,
        sample_rate: int,
        quality_profile: str = "live",
        source_track: str | None = None,
        language_hint: str | None = None,
        capture_levels: dict[str, float] | None = None,
    ) -> STTResult: ...
