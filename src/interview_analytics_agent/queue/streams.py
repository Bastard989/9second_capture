"""
Redis Streams utilities for task queues.

Features:
- XADD producer API
- consumer groups with auto-create
- ACK support
- auto-claim for stale pending tasks
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from typing import Any

import redis

from .redis import redis_client

_PAYLOAD_FIELD = "payload"
_GROUP_ERR_PREFIX = "BUSYGROUP"


@dataclass(frozen=True)
class StreamTask:
    stream: str
    entry_id: str
    payload: dict[str, Any]


def consumer_name(prefix: str) -> str:
    host = socket.gethostname()
    pid = os.getpid()
    return f"{prefix}:{host}:{pid}"


def stream_dlq_name(stream: str) -> str:
    return f"{stream}:dlq"


def ensure_group(stream: str, group: str) -> None:
    r = redis_client()
    try:
        # id=0 позволяет забирать pending при восстановлении.
        r.xgroup_create(name=stream, groupname=group, id="0", mkstream=True)
    except redis.ResponseError as e:
        if _GROUP_ERR_PREFIX not in str(e):
            raise


def enqueue(stream: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False)
    return str(redis_client().xadd(stream, {_PAYLOAD_FIELD: raw}))


def _parse_entry(stream: str, entry_id: str, fields: dict[str, Any]) -> StreamTask:
    raw = fields.get(_PAYLOAD_FIELD)
    if raw is None:
        raise ValueError(f"Missing '{_PAYLOAD_FIELD}' in stream entry")
    payload = json.loads(raw)
    return StreamTask(stream=stream, entry_id=str(entry_id), payload=payload)


def _read_new(stream: str, group: str, consumer: str, block_ms: int) -> StreamTask | None:
    r = redis_client()
    rows = r.xreadgroup(
        groupname=group,
        consumername=consumer,
        streams={stream: ">"},
        count=1,
        block=block_ms,
    )
    if not rows:
        return None
    _, entries = rows[0]
    if not entries:
        return None
    entry_id, fields = entries[0]
    return _parse_entry(stream, str(entry_id), fields)


def _claim_stale(
    stream: str,
    group: str,
    consumer: str,
    min_idle_ms: int,
) -> StreamTask | None:
    r = redis_client()
    next_id, claimed, _ = r.xautoclaim(
        name=stream,
        groupname=group,
        consumername=consumer,
        min_idle_time=min_idle_ms,
        start_id="0-0",
        count=1,
    )
    _ = next_id
    if not claimed:
        return None
    entry_id, fields = claimed[0]
    return _parse_entry(stream, str(entry_id), fields)


def read_task(
    *,
    stream: str,
    group: str,
    consumer: str,
    block_ms: int = 5000,
    min_idle_claim_ms: int = 60_000,
) -> StreamTask | None:
    ensure_group(stream, group)

    # Сначала подбираем "зависшие" pending, потом берём новые.
    stale = _claim_stale(
        stream=stream,
        group=group,
        consumer=consumer,
        min_idle_ms=min_idle_claim_ms,
    )
    if stale:
        return stale

    return _read_new(stream=stream, group=group, consumer=consumer, block_ms=block_ms)


def ack_task(*, stream: str, group: str, entry_id: str) -> int:
    return int(redis_client().xack(stream, group, entry_id))
