from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


NAME_RE = re.compile(r"\b([A-ZА-ЯЁ][a-zа-яё]{1,20})\b")
INTRO_RE = re.compile(
    r"\b(я|меня зовут)\s+([A-ZА-ЯЁ][a-zа-яё]{1,20})\b", re.IGNORECASE
)
HOST_RE = re.compile(r"\b(я веду|я сегодня веду|веду встречу)\b", re.IGNORECASE)
CALL_RE = re.compile(r"\b([A-ZА-ЯЁ][a-zа-яё]{1,20})\s*[,?:!]\s*", re.UNICODE)
ABSENT_RE = re.compile(
    r"\b(нет|не может|занят|сегодня нет|пропустил|отсутствует|болеет|не в онлайне)\b",
    re.IGNORECASE,
)
SKIP_RE = re.compile(r"\b(ладно|ок|тогда|идем дальше|следующий)\b", re.IGNORECASE)
PROXY_RE = re.compile(
    r"\b(отвечу за|скажу за|за него|за нее|за неё|я скажу за|я отвечу за)\b",
    re.IGNORECASE,
)


@dataclass
class SpeakerDecision:
    seq: int
    speaker: str | None
    addressed_to: str | None = None
    proxy_for: str | None = None


def infer_speakers(
    segments: Iterable[tuple[int, str, str]],
    *,
    response_window_sec: int = 8,
) -> list[SpeakerDecision]:
    """
    segments: iterable of (seq, raw_text, enhanced_text)
    """
    decisions: list[SpeakerDecision] = []
    host_name: str | None = None
    pending_name: str | None = None
    pending_until_seq: int | None = None

    for seq, raw_text, enh_text in segments:
        text = (enh_text or raw_text or "").strip()
        speaker: str | None = None
        addressed_to: str | None = None
        proxy_for: str | None = None

        if text:
            intro = INTRO_RE.search(text)
            if intro:
                host_name = intro.group(2).capitalize()
                speaker = host_name
            if host_name and HOST_RE.search(text):
                speaker = host_name

            if host_name:
                call = CALL_RE.search(text)
                if call:
                    name = call.group(1).capitalize()
                    if name != host_name:
                        pending_name = name
                        pending_until_seq = seq + max(1, response_window_sec)
                        addressed_to = name
                        speaker = host_name

            if pending_name and pending_until_seq is not None:
                if PROXY_RE.search(text):
                    speaker = f"proxy_for_{pending_name}"
                    proxy_for = pending_name
                    pending_name = None
                    pending_until_seq = None
                elif ABSENT_RE.search(text) or SKIP_RE.search(text):
                    speaker = host_name or speaker
                    proxy_for = pending_name if ABSENT_RE.search(text) else None
                    pending_name = None
                    pending_until_seq = None
                elif seq <= pending_until_seq and speaker is None:
                    speaker = pending_name
                    pending_name = None
                    pending_until_seq = None

        decisions.append(
            SpeakerDecision(
                seq=seq,
                speaker=speaker,
                addressed_to=addressed_to,
                proxy_for=proxy_for,
            )
        )

    return decisions
