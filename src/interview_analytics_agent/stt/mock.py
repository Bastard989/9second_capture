from __future__ import annotations

from interview_analytics_agent.stt.base import STTProvider, STTResult


class MockSTTProvider(STTProvider):
    """Заглушка STT: возвращает предсказуемый текст для проверки пайплайна end-to-end."""

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
        return STTResult(text=f"mock_transcript bytes={len(audio)} sr={sample_rate}")
