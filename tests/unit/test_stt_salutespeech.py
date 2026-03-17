from __future__ import annotations

import os

import numpy as np
import pytest

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.stt.salutespeech import SaluteSpeechProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self) -> dict:
        return self._payload


@pytest.fixture()
def salute_stt_settings():
    s = get_settings()
    snapshot = {
        "salutespeech_client_id": getattr(s, "salutespeech_client_id", None),
        "salutespeech_client_secret": getattr(s, "salutespeech_client_secret", None),
        "salutespeech_auth_url": getattr(s, "salutespeech_auth_url", None),
        "salutespeech_recognize_url": getattr(s, "salutespeech_recognize_url", None),
        "salutespeech_scope": getattr(s, "salutespeech_scope", None),
        "salutespeech_timeout_sec": getattr(s, "salutespeech_timeout_sec", None),
        "salutespeech_verify_tls": getattr(s, "salutespeech_verify_tls", None),
        "stt_model_id": getattr(s, "stt_model_id", None),
    }
    env_snapshot = {
        "SALUTESPEECH_CLIENT_ID": os.environ.get("SALUTESPEECH_CLIENT_ID"),
        "SALUTESPEECH_CLIENT_SECRET": os.environ.get("SALUTESPEECH_CLIENT_SECRET"),
    }
    try:
        yield s
    finally:
        for key, value in snapshot.items():
            setattr(s, key, value)
        for key, value in env_snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_salutespeech_provider_transcribes_audio(monkeypatch, salute_stt_settings) -> None:
    s = salute_stt_settings
    s.salutespeech_client_id = "client-id"
    s.salutespeech_client_secret = "secret-value"
    s.salutespeech_auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    s.salutespeech_recognize_url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
    s.salutespeech_scope = "SALUTE_SPEECH_PERS"
    s.salutespeech_timeout_sec = 12.0
    s.salutespeech_verify_tls = False
    s.stt_model_id = "general"

    monkeypatch.setattr(
        "interview_analytics_agent.stt.salutespeech.decode_audio_to_float32",
        lambda audio, target_sr=16000: np.array([0.1, -0.1, 0.25], dtype=np.float32),
    )

    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if url.endswith("/oauth"):
            return _FakeResponse(200, {"access_token": "salute-token", "expires_in": 1800})
        return _FakeResponse(
            200,
            {
                "result": [
                    {
                        "text": "готово",
                        "confidence": 0.73,
                    }
                ]
            },
        )

    monkeypatch.setattr("requests.post", fake_post)

    provider = SaluteSpeechProvider()
    result = provider.transcribe_chunk(audio=b"fake", sample_rate=48000, language_hint="ru")

    assert result.text == "готово"
    assert result.confidence == pytest.approx(0.73, abs=1e-6)
    assert len(calls) == 2
    assert calls[0]["url"] == "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    assert calls[0]["verify"] is False
    assert calls[1]["url"] == "https://smartspeech.sber.ru/rest/v1/speech:recognize"
    assert calls[1]["headers"]["Authorization"] == "Bearer salute-token"
    assert calls[1]["params"]["model"] == "general"
    assert calls[1]["params"]["language"] == "ru-RU"
