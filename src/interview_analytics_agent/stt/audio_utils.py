from __future__ import annotations

import io
import wave

import av
import numpy as np


def decode_audio_to_float32(audio_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
    try:
        container = av.open(io.BytesIO(audio_bytes))
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.audio.resampler.AudioResampler(
            format="fltp",
            layout="mono",
            rate=target_sr,
        )
    except Exception:
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
            frames_iter = frames if isinstance(frames, (list, tuple)) else [frames]
            for fr in frames_iter:
                if fr is None:
                    continue
                arr = fr.to_ndarray()
                if arr.ndim == 2:
                    arr = arr[0]
                samples.append(arr.astype(np.float32))
    except Exception:
        return np.zeros((0,), dtype=np.float32)

    if not samples:
        return np.zeros((0,), dtype=np.float32)
    return np.concatenate(samples)


def normalize_cloud_audio(samples: np.ndarray) -> np.ndarray:
    if samples.size == 0:
        return samples
    audio = samples.astype(np.float32)
    audio = audio - float(np.mean(audio))
    peak = float(np.max(np.abs(audio)))
    if peak <= 1e-8:
        return np.zeros((0,), dtype=np.float32)
    if peak > 0.99:
        audio = audio / peak * 0.99
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def float32_to_pcm16_bytes(samples: np.ndarray) -> bytes:
    if samples.size == 0:
        return b""
    clipped = np.clip(samples.astype(np.float32), -1.0, 1.0)
    pcm = np.round(clipped * 32767.0).astype("<i2")
    return pcm.tobytes()
