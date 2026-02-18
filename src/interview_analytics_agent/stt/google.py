"""
Google STT (заглушка).

Реализация будет добавлена позже:
- загрузка credentials из GOOGLE_STT_JSON
- streaming/recognize API
"""

from __future__ import annotations

from .base import STTProvider, STTResult


class GoogleSTTProvider(STTProvider):
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
