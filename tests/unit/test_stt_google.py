from __future__ import annotations

import os
from types import SimpleNamespace

import numpy as np
import pytest

from interview_analytics_agent.common.config import get_settings
from interview_analytics_agent.stt.google import GoogleSTTProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self) -> dict:
        return self._payload


@pytest.fixture()
def google_stt_settings():
    s = get_settings()
    snapshot = {
        "google_stt_service_account_json": getattr(s, "google_stt_service_account_json", None),
        "google_stt_token_uri": getattr(s, "google_stt_token_uri", None),
        "google_stt_recognize_url": getattr(s, "google_stt_recognize_url", None),
        "google_stt_timeout_sec": getattr(s, "google_stt_timeout_sec", None),
        "stt_model_id": getattr(s, "stt_model_id", None),
    }
    env_snapshot = {
        "GOOGLE_STT_SERVICE_ACCOUNT_JSON": os.environ.get("GOOGLE_STT_SERVICE_ACCOUNT_JSON"),
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


def test_google_stt_provider_transcribes_audio(monkeypatch, google_stt_settings) -> None:
    s = google_stt_settings
    fake_key = "-----BEGIN PRIVATE KEY-----\\n" + ("A" * 256) + "\\n-----END PRIVATE KEY-----\\n"
    s.google_stt_service_account_json = (
        """
    {
      "type": "service_account",
      "client_email": "bot@test-project.iam.gserviceaccount.com",
      "private_key": "%s",
      "token_uri": "https://oauth2.googleapis.com/token"
    }
    """.strip()
        % fake_key
    )
    s.google_stt_token_uri = "https://oauth2.googleapis.com/token"
    s.google_stt_recognize_url = "https://speech.googleapis.com/v1/speech:recognize"
    s.google_stt_timeout_sec = 15.0
    s.stt_model_id = "latest_long"

    monkeypatch.setattr(
        "interview_analytics_agent.stt.google.decode_audio_to_float32",
        lambda audio, target_sr=16000: np.array([0.2, -0.2, 0.1], dtype=np.float32),
    )
    monkeypatch.setattr(
        "interview_analytics_agent.stt.google.jwt",
        SimpleNamespace(encode=lambda payload, private_key, algorithm="RS256": "signed-jwt"),
    )

    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if url.endswith("/token"):
            return _FakeResponse(200, {"access_token": "google-token", "expires_in": 3600})
        return _FakeResponse(
            200,
            {
                "results": [
                    {
                        "alternatives": [
                            {
                                "transcript": "Привет мир",
                                "confidence": 0.88,
                            }
                        ]
                    }
                ]
            },
        )

    monkeypatch.setattr("requests.post", fake_post)

    provider = GoogleSTTProvider()
    result = provider.transcribe_chunk(audio=b"fake", sample_rate=44100, language_hint="ru")

    assert result.text == "Привет мир"
    assert result.confidence == pytest.approx(0.88, abs=1e-6)
    assert len(calls) == 2
    assert calls[0]["url"] == "https://oauth2.googleapis.com/token"
    assert calls[1]["url"] == "https://speech.googleapis.com/v1/speech:recognize"
    assert calls[1]["headers"]["Authorization"] == "Bearer google-token"
    assert calls[1]["json"]["config"]["model"] == "latest_long"
    assert calls[1]["json"]["config"]["languageCode"] == "ru-RU"
