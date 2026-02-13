"""
Локальный STT на базе faster-whisper.

Что делает:
- принимает bytes аудио чанка
- декодирует через ffmpeg (нужен пакет ffmpeg в образе)
- запускает Whisper модель локально
- возвращает текст + (примерную) уверенность

Примечание:
- для реально качественного realtime лучше подавать PCM16/mono/16k,
  но в MVP достаточно принять байты, декодировать, распознать.
"""

from __future__ import annotations

import io
import math
import wave

import av  # PyAV (ffmpeg bindings)
import numpy as np
from faster_whisper import WhisperModel

from interview_analytics_agent.common.config import get_settings

from .base import STTProvider, STTResult


def _decode_audio_to_float32(audio_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
    """
    Декодирует произвольный аудио-контейнер/кодек в моно float32 16kHz.

    Требование:
    - ffmpeg/libav должен быть доступен (через PyAV)
    """
    try:
        container = av.open(io.BytesIO(audio_bytes))
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.audio.resampler.AudioResampler(
            format="fltp", layout="mono", rate=target_sr
        )
    except Exception:
        # Fallback для PCM/WAV чанков без ffmpeg-декодирования.
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                channels = wav_file.getnchannels()
                framerate = wav_file.getframerate()
                sampwidth = wav_file.getsampwidth()
                frames = wav_file.readframes(wav_file.getnframes())
            if sampwidth != 2 or framerate <= 0:
                return np.zeros((0,), dtype=np.float32)
            pcm = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                pcm = pcm.reshape(-1, channels).mean(axis=1)
            if framerate != target_sr:
                duration = pcm.shape[0] / float(framerate)
                if duration <= 0:
                    return np.zeros((0,), dtype=np.float32)
                old_t = np.linspace(0.0, duration, num=pcm.shape[0], endpoint=False)
                new_len = int(duration * target_sr)
                if new_len <= 0:
                    return np.zeros((0,), dtype=np.float32)
                new_t = np.linspace(0.0, duration, num=new_len, endpoint=False)
                pcm = np.interp(new_t, old_t, pcm).astype(np.float32)
            return pcm.astype(np.float32)
        except Exception:
            return np.zeros((0,), dtype=np.float32)

    samples: list[np.ndarray] = []
    try:
        for frame in container.decode(stream):
            frames = resampler.resample(frame)
            # PyAV может вернуть один фрейм или список
            if isinstance(frames, (list, tuple)):
                frames_iter = frames
            else:
                frames_iter = [frames]
            for fr in frames_iter:
                if fr is None:
                    continue
                # fr.to_ndarray() -> shape (channels, samples) в float
                arr = fr.to_ndarray()
                if arr.ndim == 2:
                    arr = arr[0]
                samples.append(arr.astype(np.float32))
    except Exception:
        return np.zeros((0,), dtype=np.float32)

    if not samples:
        return np.zeros((0,), dtype=np.float32)

    return np.concatenate(samples)


def _normalize_audio(samples: np.ndarray) -> np.ndarray:
    if samples.size == 0:
        return samples

    audio = samples.astype(np.float32)
    audio = audio - float(np.mean(audio))
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-6:
        return np.zeros((0,), dtype=np.float32)

    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms > 0:
        target_rms = 0.12
        gain = max(1.0, min(60.0, target_rms / rms))
    else:
        gain = 1.0
    if peak * gain > 0.99:
        gain = 0.99 / peak

    audio = np.clip(audio * gain, -1.0, 1.0)
    return audio.astype(np.float32)


def _high_pass_filter(samples: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    if samples.size == 0:
        return samples
    cutoff = max(20.0, float(cutoff_hz))
    sr = float(max(8000, sample_rate))
    dt = 1.0 / sr
    rc = 1.0 / (2.0 * math.pi * cutoff)
    alpha = rc / (rc + dt)

    out = np.empty_like(samples, dtype=np.float32)
    out[0] = samples[0]
    prev_out = float(out[0])
    prev_in = float(samples[0])
    for i in range(1, samples.shape[0]):
        current = float(samples[i])
        prev_out = alpha * (prev_out + current - prev_in)
        out[i] = prev_out
        prev_in = current
    return out


def _noise_gate(samples: np.ndarray, gate_db: float) -> np.ndarray:
    if samples.size == 0:
        return samples
    threshold = 10 ** (float(gate_db) / 20.0)
    win = 256
    padded = np.pad(samples, (win, win), mode="edge")
    energy = np.convolve(padded * padded, np.ones(win) / win, mode="valid")
    env = np.sqrt(np.maximum(energy[: samples.shape[0]], 0.0))
    mask = (env >= threshold).astype(np.float32)
    softened = np.convolve(mask, np.ones(9) / 9.0, mode="same")
    return (samples * np.clip(softened, 0.0, 1.0)).astype(np.float32)


def _spectral_denoise(samples: np.ndarray, *, strength: float = 0.32) -> np.ndarray:
    if samples.size < 1024:
        return samples
    n_fft = 512
    hop = 256
    window = np.hanning(n_fft).astype(np.float32)
    pad = n_fft // 2
    padded = np.pad(samples.astype(np.float32), (pad, pad), mode="reflect")
    frames = []
    for start in range(0, padded.shape[0] - n_fft + 1, hop):
        frame = padded[start : start + n_fft]
        frames.append(np.fft.rfft(frame * window))
    if not frames:
        return samples

    spec = np.vstack(frames)
    mag = np.abs(spec)
    phase = np.angle(spec)

    noise_frames = min(max(4, mag.shape[0] // 12), 24)
    noise_profile = np.median(mag[:noise_frames, :], axis=0)
    reduce = np.clip(float(strength), 0.0, 0.9)
    cleaned_mag = np.maximum(mag - noise_profile * (1.0 + reduce), noise_profile * 0.08)

    reconstructed = cleaned_mag * np.exp(1j * phase)
    out_len = hop * (reconstructed.shape[0] - 1) + n_fft
    output = np.zeros((out_len,), dtype=np.float32)
    win_acc = np.zeros((out_len,), dtype=np.float32)
    for i, spectrum in enumerate(reconstructed):
        start = i * hop
        frame = np.fft.irfft(spectrum).astype(np.float32)
        output[start : start + n_fft] += frame * window
        win_acc[start : start + n_fft] += window * window

    win_acc = np.where(win_acc < 1e-6, 1.0, win_acc)
    output = output / win_acc
    output = output[pad : pad + samples.shape[0]]
    return output.astype(np.float32)


class WhisperLocalProvider(STTProvider):
    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        language: str | None = None,
        vad_filter: bool | None = None,
        beam_size: int | None = None,
        **_: object,
    ) -> None:
        s = get_settings()

        # берём параметры из аргументов, иначе из настроек
        model_size = model_size or s.whisper_model_size
        device = device or s.whisper_device
        compute_type = compute_type or s.whisper_compute_type

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

        lang_value = (language or s.whisper_language or "").strip().lower()
        self.language = None if lang_value in {"", "auto"} else lang_value
        self.vad_filter = s.whisper_vad_filter if vad_filter is None else vad_filter
        self.beam_size = beam_size or s.whisper_beam_size
        self.beam_size_live = max(1, int(getattr(s, "whisper_beam_size_live", 1) or 1))
        self.beam_size_final = max(
            self.beam_size_live,
            int(getattr(s, "whisper_beam_size_final", self.beam_size) or self.beam_size),
        )
        self.hpf_enabled = bool(getattr(s, "whisper_audio_hpf_enabled", True))
        self.hpf_cutoff_hz = int(getattr(s, "whisper_audio_hpf_cutoff_hz", 80) or 80)
        self.noise_suppress_enabled = bool(
            getattr(s, "whisper_audio_noise_suppress_enabled", True)
        )
        self.noise_gate_db = float(getattr(s, "whisper_audio_noise_gate_db", -42.0) or -42.0)
        self.spectral_denoise_enabled = bool(
            getattr(s, "whisper_audio_spectral_denoise_enabled", True)
        )
        self.spectral_denoise_strength = float(
            getattr(s, "whisper_audio_spectral_denoise_strength", 0.32) or 0.32
        )

    def _normalize_language_hint(self, language_hint: str | None) -> str:
        hint = str(language_hint or "").strip().lower()
        if not hint:
            return "auto"
        if hint.startswith("ru"):
            return "ru"
        if hint.startswith("en"):
            return "en"
        if hint in {"mixed", "auto"}:
            return "auto"
        return "auto"

    def _beam_for_quality_profile(self, quality_profile: str) -> int:
        normalized = str(quality_profile or "live").strip().lower()
        if normalized == "final":
            return self.beam_size_final
        if normalized in {"live_fast", "fast"}:
            return max(1, self.beam_size_live - 1)
        if normalized in {"live_accurate", "accurate"}:
            return max(1, min(self.beam_size_final, self.beam_size_live + 1))
        return self.beam_size_live

    def _transcribe_with_params(
        self,
        wav: np.ndarray,
        *,
        language: str | None,
        beam_size: int,
        quality_profile: str,
        language_profile: str = "auto",
        relaxed: bool = False,
    ) -> tuple[str, float | None]:
        profile = self._normalize_language_hint(language_profile)
        if quality_profile == "final":
            base_vad = self.vad_filter
            no_speech_threshold = 0.5
            log_prob_threshold = -1.7
            compression_ratio_threshold = 2.5
        else:
            base_vad = self.vad_filter
            no_speech_threshold = 0.55
            log_prob_threshold = -2.2
            compression_ratio_threshold = 2.9

        if profile == "ru":
            no_speech_threshold = max(0.42, no_speech_threshold - 0.07)
            log_prob_threshold = min(log_prob_threshold + 0.22, -1.45)
        elif profile == "en":
            no_speech_threshold = min(0.64, no_speech_threshold + 0.03)
            log_prob_threshold = max(log_prob_threshold - 0.08, -2.5)
        kwargs = {
            "language": language,
            "vad_filter": False if relaxed else base_vad,
            "beam_size": 1 if relaxed else beam_size,
            "condition_on_previous_text": False,
            "temperature": 0.0,
            "no_speech_threshold": 0.72 if relaxed else no_speech_threshold,
            "log_prob_threshold": -3.0 if relaxed else log_prob_threshold,
            "compression_ratio_threshold": 3.2 if relaxed else compression_ratio_threshold,
        }
        try:
            segments, _info = self.model.transcribe(wav, **kwargs)
        except TypeError:
            kwargs.pop("condition_on_previous_text", None)
            kwargs.pop("temperature", None)
            kwargs.pop("no_speech_threshold", None)
            kwargs.pop("log_prob_threshold", None)
            kwargs.pop("compression_ratio_threshold", None)
            segments, _info = self.model.transcribe(wav, **kwargs)

        text_parts: list[str] = []
        for seg in segments:
            if seg.text:
                text_parts.append(seg.text.strip())
        return " ".join([t for t in text_parts if t]).strip(), None

    def _preprocess_audio(self, wav: np.ndarray, sample_rate: int) -> np.ndarray:
        processed = wav
        if self.hpf_enabled:
            processed = _high_pass_filter(processed, sample_rate=sample_rate, cutoff_hz=self.hpf_cutoff_hz)
        if self.noise_suppress_enabled:
            processed = _noise_gate(processed, gate_db=self.noise_gate_db)
        if self.spectral_denoise_enabled:
            processed = _spectral_denoise(
                processed,
                strength=self.spectral_denoise_strength,
            )
        return _normalize_audio(processed)

    def transcribe_chunk(
        self,
        *,
        audio: bytes,
        sample_rate: int,
        quality_profile: str = "live",
        source_track: str | None = None,
        language_hint: str | None = None,
    ) -> STTResult:
        wav = _decode_audio_to_float32(audio, target_sr=16000)
        wav = self._preprocess_audio(wav, sample_rate=16000)
        if wav.size == 0:
            return STTResult(text="", confidence=None)

        language_profile = self._normalize_language_hint(language_hint)
        language_target = self.language
        if language_profile in {"ru", "en"}:
            language_target = language_profile
        if language_profile == "auto":
            language_target = self.language

        beam = self._beam_for_quality_profile(quality_profile)
        if language_profile in {"ru", "en"} and quality_profile in {"live_balanced", "live_accurate", "final"}:
            beam = max(beam, self.beam_size_live)
        text, confidence = self._transcribe_with_params(
            wav,
            language=language_target,
            beam_size=beam,
            quality_profile=quality_profile,
            language_profile=language_profile,
        )
        if not text:
            text, confidence = self._transcribe_with_params(
                wav,
                language=None,
                beam_size=beam,
                quality_profile=quality_profile,
                language_profile=language_profile,
            )
        if not text:
            text, confidence = self._transcribe_with_params(
                wav,
                language=language_target,
                beam_size=beam,
                quality_profile=quality_profile,
                language_profile=language_profile,
                relaxed=True,
            )
        if not text:
            text, confidence = self._transcribe_with_params(
                wav,
                language=None,
                beam_size=beam,
                quality_profile=quality_profile,
                language_profile=language_profile,
                relaxed=True,
            )

        # faster-whisper не даёт "confidence" как одно число стабильно,
        # оставим None, позже можно считать среднюю logprob.
        normalized_track = (source_track or "").strip().lower()
        if normalized_track not in {"system", "mic", "mixed"}:
            normalized_track = ""
        speaker = normalized_track or None
        return STTResult(text=text, confidence=confidence, speaker=speaker)
