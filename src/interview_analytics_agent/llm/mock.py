"""
Mock LLM для тестов и dev.

Назначение:
- Быстро гонять пайплайн без реальных вызовов LLM
- Предсказуемый результат
"""

from __future__ import annotations

import json

from .base import LLMProvider


class MockLLMProvider(LLMProvider):
    def complete_json(self, *, system: str, user: str) -> str:
        payload = {
            "summary": "mock_summary",
            "bullets": ["mock_point_1", "mock_point_2"],
            "risk_flags": [],
            "recommendation": "",
        }
        return json.dumps(payload, ensure_ascii=False)

    def complete_text(self, *, system: str, user: str) -> str:
        return self.complete_json(system=system, user=user)
