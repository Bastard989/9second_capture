from __future__ import annotations

from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from secrets import token_hex
from typing import Any


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    meeting_id: str | None
    source: str


_TRACE_CONTEXT: ContextVar[TraceContext | None] = ContextVar("trace_context", default=None)


def new_trace_id() -> str:
    # 16 bytes -> 32 hex chars (W3C trace-id format length)
    return token_hex(16)


def new_span_id() -> str:
    # 8 bytes -> 16 hex chars (W3C span-id format length)
    return token_hex(8)


def _normalize_hex(value: str | None, expected_len: int) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if len(cleaned) != expected_len:
        return None
    if any(c not in "0123456789abcdef" for c in cleaned):
        return None
    return cleaned


def current_trace_context() -> TraceContext | None:
    return _TRACE_CONTEXT.get()


def current_trace_id() -> str | None:
    ctx = current_trace_context()
    return ctx.trace_id if ctx else None


@contextmanager
def start_trace(
    *,
    trace_id: str | None = None,
    meeting_id: str | None = None,
    source: str = "internal",
) -> Iterator[TraceContext]:
    """
    Создаёт span в текущем trace-контексте.

    - если trace_id не передан, наследует trace_id из текущего контекста;
    - если текущего контекста нет, генерирует новый trace_id.
    """
    parent = current_trace_context()
    normalized_trace_id = _normalize_hex(trace_id, 32)
    resolved_trace_id = normalized_trace_id or (parent.trace_id if parent else new_trace_id())
    resolved_meeting_id = meeting_id or (parent.meeting_id if parent else None)
    resolved_source = source or (parent.source if parent else "internal")

    parent_span_id = parent.span_id if parent and resolved_trace_id == parent.trace_id else None
    ctx = TraceContext(
        trace_id=resolved_trace_id,
        span_id=new_span_id(),
        parent_span_id=parent_span_id,
        meeting_id=resolved_meeting_id,
        source=resolved_source,
    )
    token = _TRACE_CONTEXT.set(ctx)
    try:
        yield ctx
    finally:
        _TRACE_CONTEXT.reset(token)


@contextmanager
def start_trace_from_payload(
    payload: Mapping[str, Any] | None,
    *,
    meeting_id: str | None = None,
    source: str = "queue",
) -> Iterator[TraceContext]:
    """
    Создаёт span на основе trace-полей входящего payload (очереди/события).
    """
    p = payload or {}
    payload_trace_id = _normalize_hex(str(p.get("trace_id") or "").strip() or None, 32)
    payload_parent_span = _normalize_hex(str(p.get("span_id") or "").strip() or None, 16)
    payload_meeting = str(p.get("meeting_id") or "").strip() or None

    ctx = TraceContext(
        trace_id=payload_trace_id or new_trace_id(),
        span_id=new_span_id(),
        parent_span_id=payload_parent_span,
        meeting_id=meeting_id or payload_meeting,
        source=source,
    )
    token = _TRACE_CONTEXT.set(ctx)
    try:
        yield ctx
    finally:
        _TRACE_CONTEXT.reset(token)


def inject_trace_context(
    payload: MutableMapping[str, Any],
    *,
    meeting_id: str | None = None,
    source: str = "queue",
) -> MutableMapping[str, Any]:
    """
    Добавляет trace-поля в payload исходящего события.
    """
    ctx = current_trace_context()
    trace_id = ctx.trace_id if ctx else new_trace_id()
    span_id = ctx.span_id if ctx else new_span_id()

    payload["trace_id"] = trace_id
    payload["span_id"] = span_id
    payload["trace_source"] = source

    resolved_meeting_id = meeting_id or (ctx.meeting_id if ctx else None)
    if resolved_meeting_id and not payload.get("meeting_id"):
        payload["meeting_id"] = resolved_meeting_id

    return payload
