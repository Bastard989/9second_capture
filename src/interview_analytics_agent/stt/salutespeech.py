from __future__ import annotations

import base64
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests

from interview_analytics_agent.common.config import get_settings

from .audio_utils import decode_audio_to_float32, float32_to_pcm16_bytes, normalize_cloud_audio
from .base import STTProvider, STTResult

log = logging.getLogger(__name__)


@dataclass
class SaluteSpeechConfig:
    client_id: str
    client_secret: str
    auth_url: str
    recognize_url: str
    scope: str
    model: str
    timeout_s: float
    verify_tls: bool


def _salute_language(language_hint: str | None) -> str:
    hint = str(language_hint or "").strip().lower()
    if hint.startswith("en"):
        return "en-US"
    return "ru-RU"


def _confidence_from_payload(data: dict[str, Any]) -> float | None:
    candidates: list[float] = []
    stack: list[Any] = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if key in {"confidence", "score"}:
                    try:
                        candidates.append(float(value))
                    except Exception:
                        pass
                elif isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    if not candidates:
        return None
    return sum(candidates) / float(len(candidates))


def _extract_salute_text(data: Any) -> str:
    snippets: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("text", "transcript", "normalized_text", "utterance", "result"):
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    snippets.append(value.strip())
            for value in node.values():
                if isinstance(value, (dict, list)):
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(data)
    unique: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        if snippet in seen:
            continue
        seen.add(snippet)
        unique.append(snippet)
    return " ".join(unique).strip()


def _looks_like_placeholder(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return True
    return normalized in {
        "demo-client",
        "demo-secret",
        "<insert_salutespeech_client_id_here>",
        "<insert_salutespeech_client_secret_here>",
    } or "insert_" in normalized or normalized.startswith("example")


class SaluteSpeechProvider(STTProvider):
    def __init__(self) -> None:
        s = get_settings()
        client_id = str(getattr(s, "salutespeech_client_id", "") or "").strip()
        client_secret = str(getattr(s, "salutespeech_client_secret", "") or "").strip()
        if not client_id or not client_secret:
            raise RuntimeError(
                "Для SaluteSpeech нужны SALUTESPEECH_CLIENT_ID и SALUTESPEECH_CLIENT_SECRET"
            )
        if _looks_like_placeholder(client_id) or _looks_like_placeholder(client_secret):
            raise RuntimeError(
                "Для SaluteSpeech сейчас сохранены примерные данные. Укажите реальные Client ID и Client Secret."
            )
        self.cfg = SaluteSpeechConfig(
            client_id=client_id,
            client_secret=client_secret,
            auth_url=str(getattr(s, "salutespeech_auth_url", "") or "").strip()
            or "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            recognize_url=str(getattr(s, "salutespeech_recognize_url", "") or "").strip()
            or "https://smartspeech.sber.ru/rest/v1/speech:recognize",
            scope=str(getattr(s, "salutespeech_scope", "") or "SALUTE_SPEECH_PERS").strip()
            or "SALUTE_SPEECH_PERS",
            model=str(getattr(s, "stt_model_id", "") or "").strip() or "general",
            timeout_s=max(5.0, float(getattr(s, "salutespeech_timeout_sec", 45.0) or 45.0)),
            verify_tls=bool(getattr(s, "salutespeech_verify_tls", True)),
        )
        self._access_token = ""
        self._access_token_deadline = 0.0

    def verify_connection(self) -> str:
        self._get_access_token()
        return "SaluteSpeech: доступ подтвержден, токен получен."

    def _issue_access_token(self) -> str:
        basic = base64.b64encode(
            f"{self.cfg.client_id}:{self.cfg.client_secret}".encode("utf-8")
        ).decode("ascii")
        headers = {
            "Authorization": f"Bearer {basic}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.post(
            self.cfg.auth_url,
            headers=headers,
            data=urlencode({"scope": self.cfg.scope}),
            timeout=self.cfg.timeout_s,
            verify=self.cfg.verify_tls,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"salutespeech_token_http_{resp.status_code}:{resp.text[:300]}")
        data = resp.json()
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("salutespeech_token_missing_access_token")
        expires_at = float(data.get("expires_at") or 0.0)
        expires_in = float(data.get("expires_in") or 1800.0)
        if expires_at > 0:
            self._access_token_deadline = max(time.time() + 60.0, expires_at - 60.0)
        else:
            self._access_token_deadline = time.time() + max(60.0, expires_in - 60.0)
        self._access_token = token
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

        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "audio/x-pcm;bit=16;rate=16000",
            "RqUID": str(uuid.uuid4()),
        }
        params = {
            "language": _salute_language(language_hint),
            "model": self.cfg.model,
            "sample_rate": 16000,
        }
        resp = requests.post(
            self.cfg.recognize_url,
            headers=headers,
            params=params,
            data=pcm_bytes,
            timeout=self.cfg.timeout_s,
            verify=self.cfg.verify_tls,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"salutespeech_recognize_http_{resp.status_code}:{resp.text[:400]}")
        data = resp.json()
        if not isinstance(data, dict):
            return STTResult(text="", confidence=None)
        return STTResult(
            text=_extract_salute_text(data),
            confidence=_confidence_from_payload(data),
        )
