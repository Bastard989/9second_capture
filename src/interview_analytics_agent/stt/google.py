from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from interview_analytics_agent.common.config import get_settings

from .audio_utils import decode_audio_to_float32, float32_to_pcm16_bytes, normalize_cloud_audio
from .base import STTProvider, STTResult

try:
    import jwt
except Exception:  # pragma: no cover - optional import guard
    jwt = None

log = logging.getLogger(__name__)

_GOOGLE_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


@dataclass
class GoogleSTTConfig:
    service_account_json: str
    token_uri: str
    recognize_url: str
    model: str
    timeout_s: float


def _google_language_config(language_hint: str | None) -> tuple[str, list[str]]:
    hint = str(language_hint or "").strip().lower()
    if hint.startswith("ru"):
        return "ru-RU", ["en-US"]
    if hint.startswith("en"):
        return "en-US", ["ru-RU"]
    return "ru-RU", ["en-US"]


def _parse_service_account(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(str(raw or "").strip())
    except Exception as exc:
        raise RuntimeError("GOOGLE_STT_SERVICE_ACCOUNT_JSON содержит невалидный JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GOOGLE_STT_SERVICE_ACCOUNT_JSON должен быть JSON объектом")
    for key in ("client_email", "private_key"):
        if not str(payload.get(key) or "").strip():
            raise RuntimeError(f"GOOGLE_STT_SERVICE_ACCOUNT_JSON не содержит поле {key}")
    client_email = str(payload.get("client_email") or "").strip().lower()
    private_key = str(payload.get("private_key") or "").strip()
    if client_email.endswith("@example.iam.gserviceaccount.com"):
        raise RuntimeError(
            "Для Google STT сейчас сохранен пример service account JSON. Вставьте реальный JSON из Google Cloud."
        )
    if "BEGIN PRIVATE KEY" in private_key and len(private_key) < 200:
        raise RuntimeError(
            "Для Google STT сохранен слишком короткий private key. Похоже, в настройках не реальный service account JSON."
        )
    return payload


def _average_confidence(items: list[float | None]) -> float | None:
    values = [float(item) for item in items if item is not None]
    if not values:
        return None
    return sum(values) / float(len(values))


class GoogleSTTProvider(STTProvider):
    def __init__(self) -> None:
        s = get_settings()
        raw_json = str(getattr(s, "google_stt_service_account_json", "") or "").strip()
        if not raw_json:
            raise RuntimeError(
                "Для Google STT нужен GOOGLE_STT_SERVICE_ACCOUNT_JSON или GOOGLE_STT_SERVICE_ACCOUNT_JSON_FILE"
            )
        self._creds = _parse_service_account(raw_json)
        self.cfg = GoogleSTTConfig(
            service_account_json=raw_json,
            token_uri=str(
                getattr(s, "google_stt_token_uri", "") or self._creds.get("token_uri") or ""
            ).strip()
            or "https://oauth2.googleapis.com/token",
            recognize_url=str(getattr(s, "google_stt_recognize_url", "") or "").strip()
            or "https://speech.googleapis.com/v1/speech:recognize",
            model=str(getattr(s, "stt_model_id", "") or "").strip() or "latest_long",
            timeout_s=max(5.0, float(getattr(s, "google_stt_timeout_sec", 45.0) or 45.0)),
        )
        self._access_token = ""
        self._access_token_deadline = 0.0

    def verify_connection(self) -> str:
        self._get_access_token()
        return "Google STT: доступ подтвержден, токен получен."

    def _issue_access_token(self) -> str:
        if jwt is None:
            raise RuntimeError("Для Google STT нужен пакет PyJWT[crypto]")
        now = int(time.time())
        payload = {
            "iss": self._creds["client_email"],
            "sub": self._creds["client_email"],
            "aud": self.cfg.token_uri,
            "scope": _GOOGLE_SCOPE,
            "iat": now,
            "exp": now + 3600,
        }
        assertion = jwt.encode(payload, self._creds["private_key"], algorithm="RS256")
        resp = requests.post(
            self.cfg.token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=self.cfg.timeout_s,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"google_stt_token_http_{resp.status_code}:{resp.text[:300]}")
        data = resp.json()
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("google_stt_token_missing_access_token")
        expires_in = int(data.get("expires_in") or 3600)
        self._access_token = token
        self._access_token_deadline = time.time() + max(60, expires_in - 60)
        return token

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._access_token_deadline:
            return self._access_token
        return self._issue_access_token()

    def transcribe_chunk(
        self,
        *,
        audio: bytes,
        sample_rate: int,
        quality_profile: str = "balanced",
        source_track: str | None = None,
        language_hint: str | None = None,
        capture_levels: dict[str, float] | None = None,
    ) -> STTResult:
        del sample_rate, quality_profile, source_track, capture_levels
        wav = decode_audio_to_float32(audio, target_sr=16000)
        wav = normalize_cloud_audio(wav)
        pcm_bytes = float32_to_pcm16_bytes(wav)
        if not pcm_bytes:
            return STTResult(text="", confidence=None)

        language_code, alt_languages = _google_language_config(language_hint)
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": 16000,
                "languageCode": language_code,
                "alternativeLanguageCodes": alt_languages,
                "enableAutomaticPunctuation": True,
                "model": self.cfg.model,
                "audioChannelCount": 1,
            },
            "audio": {
                "content": base64.b64encode(pcm_bytes).decode("ascii"),
            },
        }
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            self.cfg.recognize_url,
            headers=headers,
            json=payload,
            timeout=self.cfg.timeout_s,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"google_stt_recognize_http_{resp.status_code}:{resp.text[:400]}")
        data = resp.json()
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return STTResult(text="", confidence=None)

        text_parts: list[str] = []
        confidences: list[float | None] = []
        for row in results:
            if not isinstance(row, dict):
                continue
            alternatives = row.get("alternatives")
            if not isinstance(alternatives, list) or not alternatives:
                continue
            alt = alternatives[0] if isinstance(alternatives[0], dict) else {}
            transcript = str(alt.get("transcript") or "").strip()
            if transcript:
                text_parts.append(transcript)
            try:
                confidence = float(alt.get("confidence"))
            except Exception:
                confidence = None
            confidences.append(confidence)

        return STTResult(
            text=" ".join(part for part in text_parts if part).strip(),
            confidence=_average_confidence(confidences),
        )
