"""
SaluteSpeech STT (заглушка).

Реализация будет добавлена позже:
- получение токена по client_id/client_secret
- вызов API распознавания
"""

from __future__ import annotations

from .base import STTProvider, STTResult


class SaluteSpeechProvider(STTProvider):
    def transcribe_chunk(
        self,
        *,
        audio: bytes,
        sample_rate: int,
        quality_profile: str = "live",
        source_track: str | None = None,
        language_hint: str | None = None,
        capture_levels: dict[str, float] | None = None,
    ) -> STTResult:
        return STTResult(text="", confidence=None)
