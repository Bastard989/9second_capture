"""
Smoke check for Alertmanager routing to webhook sink.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import requests


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Alert delivery smoke")
    p.add_argument(
        "--alertmanager-url", default="http://localhost:9093", help="Alertmanager base URL"
    )
    p.add_argument("--sink-url", default="http://localhost:9080", help="Webhook sink base URL")
    p.add_argument("--timeout-sec", type=int, default=90, help="Wait timeout for delivery")
    return p.parse_args()


def _post_smoke_alerts(*, alertmanager_url: str, suffix: str) -> None:
    now = datetime.now(timezone.utc)  # noqa: UP017
    starts_at = _iso(now - timedelta(seconds=10))
    ends_at = _iso(now + timedelta(minutes=5))
    payload = [
        {
            "labels": {
                "alertname": f"CodexSmokeWarning{suffix}",
                "severity": "warning",
                "smoke": "true",
            },
            "annotations": {
                "summary": "Smoke warning alert",
                "runbook_url": "docs/runbooks/alerts.md#queuebackloghigh",
            },
            "startsAt": starts_at,
            "endsAt": ends_at,
        },
        {
            "labels": {
                "alertname": f"CodexSmokeCritical{suffix}",
                "severity": "critical",
                "smoke": "true",
            },
            "annotations": {
                "summary": "Smoke critical alert",
                "runbook_url": "docs/runbooks/alerts.md#apigatewaydown",
            },
            "startsAt": starts_at,
            "endsAt": ends_at,
        },
    ]
    r = requests.post(f"{alertmanager_url}/api/v2/alerts", json=payload, timeout=5)
    r.raise_for_status()


def _reset_sink(*, sink_url: str) -> None:
    r = requests.post(f"{sink_url}/reset", timeout=5)
    r.raise_for_status()


def _load_stats(*, sink_url: str) -> dict:
    r = requests.get(f"{sink_url}/stats", timeout=5)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("invalid sink stats payload")
    return data


def main() -> int:
    args = _args()
    smoke_suffix = uuid4().hex[:8]

    try:
        _reset_sink(sink_url=args.sink_url)
        _post_smoke_alerts(alertmanager_url=args.alertmanager_url, suffix=smoke_suffix)
    except Exception as e:
        print(f"alerts delivery smoke FAILED during setup: {e}")
        return 2

    deadline = time.time() + args.timeout_sec
    while time.time() < deadline:
        try:
            stats = _load_stats(sink_url=args.sink_url)
        except Exception:
            time.sleep(1)
            continue
        channels = stats.get("channels") or {}
        warning_count = int(channels.get("warning", 0))
        critical_count = int(channels.get("critical", 0))
        if warning_count >= 1 and critical_count >= 1:
            print(
                "alerts delivery smoke OK: "
                f"warning={warning_count}, critical={critical_count}, total={stats.get('total', 0)}"
            )
            return 0
        time.sleep(1)

    print("alerts delivery smoke FAILED: warning/critical routes were not delivered in time")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
