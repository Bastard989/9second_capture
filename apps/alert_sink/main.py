"""
Internal webhook sink for Alertmanager routing smoke checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, Query, Request

app = FastAPI(title="Alert Webhook Sink", version="1.0.0")

_LOCK = Lock()
_EVENTS: list[dict[str, Any]] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


@app.get("/health")
def health() -> dict[str, Any]:
    with _LOCK:
        count = len(_EVENTS)
    return {"status": "ok", "events": count}


@app.post("/reset")
def reset() -> dict[str, Any]:
    with _LOCK:
        _EVENTS.clear()
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request, channel: str = Query(default="default")) -> dict[str, Any]:
    body = await request.body()
    try:
        payload: Any = await request.json()
    except Exception:
        payload = {"raw_body": body.decode("utf-8", errors="replace")}

    event = {"ts": _now_iso(), "channel": channel, "payload": payload}
    with _LOCK:
        _EVENTS.append(event)
    return {"status": "ok", "channel": channel}


@app.get("/stats")
def stats() -> dict[str, Any]:
    with _LOCK:
        counts: dict[str, int] = {}
        for item in _EVENTS:
            channel = str(item.get("channel") or "default")
            counts[channel] = counts.get(channel, 0) + 1
        total = len(_EVENTS)
    return {"total": total, "channels": counts}


@app.get("/events")
def events(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    with _LOCK:
        items = _EVENTS[-limit:]
    return {"items": items, "count": len(items)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9080)
