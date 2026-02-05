"""
Guardrail smoke for alert-relay retry/backoff profile.
"""

from __future__ import annotations

import argparse
import re
import time
from typing import Any

import requests


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Alert relay retry/backoff guardrail")
    p.add_argument("--relay-url", default="http://localhost:9081", help="Alert relay base URL")
    p.add_argument("--expected-status", type=int, default=502, choices=[200, 502])
    p.add_argument("--expect-fail-on-error", choices=["true", "false"], default="true")
    p.add_argument("--channel", choices=["default", "warning", "critical"], default="critical")
    p.add_argument("--target-kind", choices=["target", "shadow"], default="target")
    p.add_argument("--retry-reason", default="connection_error")
    p.add_argument("--backoff-lower-ratio", type=float, default=0.9)
    p.add_argument("--backoff-upper-ratio", type=float, default=3.0)
    p.add_argument("--timeout-sec", type=int, default=45)
    return p.parse_args()


def _parse_labels(labels_raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in labels_raw.split(","):
        chunk = token.strip()
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        out[key.strip()] = value.strip().strip('"')
    return out


def _metric_sum(metrics_text: str, metric: str, *, labels: dict[str, str]) -> float:
    total = 0.0
    pattern = rf"^{re.escape(metric)}\{{([^}}]*)\}}\s+([0-9.eE+\-]+)$"
    for line in metrics_text.splitlines():
        match = re.match(pattern, line.strip())
        if not match:
            continue
        sample_labels = _parse_labels(match.group(1))
        if all(sample_labels.get(k) == v for k, v in labels.items()):
            total += float(match.group(2))
    return total


def _load_health(*, relay_url: str) -> dict[str, Any]:
    r = requests.get(f"{relay_url}/health", timeout=5)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("invalid /health payload")
    return data


def _wait_health(
    *, relay_url: str, expected_fail_on_error: bool, timeout_sec: int
) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            data = _load_health(relay_url=relay_url)
            if bool(data.get("fail_on_error")) is expected_fail_on_error:
                return data
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("relay health did not reach expected mode in time")


def _load_metrics(*, relay_url: str) -> str:
    r = requests.get(f"{relay_url}/metrics", timeout=5)
    r.raise_for_status()
    return r.text


def _send_webhook(*, relay_url: str, channel: str) -> requests.Response:
    payload: dict[str, Any] = {
        "alerts": [
            {
                "labels": {"alertname": "RelayRetryGuardrail", "severity": channel},
                "annotations": {"summary": "Relay retry guardrail"},
            }
        ]
    }
    return requests.post(f"{relay_url}/webhook/{channel}", json=payload, timeout=30)


def main() -> int:
    args = _args()
    expected_fail_on_error = args.expect_fail_on_error == "true"
    labels_base = {"channel": args.channel, "target": args.target_kind}

    try:
        health = _wait_health(
            relay_url=args.relay_url,
            expected_fail_on_error=expected_fail_on_error,
            timeout_sec=args.timeout_sec,
        )
        retries_cfg = int(health.get("retries", 0))
        backoff_sec = float(health.get("retry_backoff_sec", 0.0))
        attempts_cfg = retries_cfg + 1

        before = _load_metrics(relay_url=args.relay_url)
        before_retries = _metric_sum(
            before,
            "agent_alert_relay_retries_total",
            labels={**labels_base, "reason": args.retry_reason},
        )
        before_errors = _metric_sum(
            before,
            "agent_alert_relay_forward_total",
            labels={**labels_base, "result": "error"},
        )
        before_attempt_count = _metric_sum(
            before,
            "agent_alert_relay_forward_attempt_latency_ms_count",
            labels=labels_base,
        )

        started = time.perf_counter()
        resp = _send_webhook(relay_url=args.relay_url, channel=args.channel)
        elapsed_sec = time.perf_counter() - started
        if resp.status_code != args.expected_status:
            raise RuntimeError(
                f"unexpected status: got={resp.status_code}, expected={args.expected_status}"
            )

        after = _load_metrics(relay_url=args.relay_url)
        after_retries = _metric_sum(
            after,
            "agent_alert_relay_retries_total",
            labels={**labels_base, "reason": args.retry_reason},
        )
        after_errors = _metric_sum(
            after,
            "agent_alert_relay_forward_total",
            labels={**labels_base, "result": "error"},
        )
        after_attempt_count = _metric_sum(
            after,
            "agent_alert_relay_forward_attempt_latency_ms_count",
            labels=labels_base,
        )

        retries_delta = after_retries - before_retries
        errors_delta = after_errors - before_errors
        attempts_delta = after_attempt_count - before_attempt_count
        if retries_delta < retries_cfg:
            raise RuntimeError(
                f"retry delta too low: got={retries_delta}, expected_at_least={retries_cfg}"
            )
        if errors_delta < 1:
            raise RuntimeError(f"error delta too low: got={errors_delta}, expected_at_least=1")
        if attempts_delta < attempts_cfg:
            raise RuntimeError(
                f"attempt_count delta too low: got={attempts_delta}, expected_at_least={attempts_cfg}"
            )

        # Для backoff sec=0 пропускаем guardrail по времени.
        if backoff_sec > 0:
            expected_backoff_sec = backoff_sec * (retries_cfg * (retries_cfg + 1) / 2.0)
            lower_bound = expected_backoff_sec * max(0.0, args.backoff_lower_ratio)
            upper_bound = expected_backoff_sec * max(
                args.backoff_upper_ratio, args.backoff_lower_ratio
            )
            if elapsed_sec < lower_bound:
                raise RuntimeError(
                    f"elapsed below backoff guardrail: elapsed={elapsed_sec:.3f}s, "
                    f"lower_bound={lower_bound:.3f}s"
                )
            if elapsed_sec > upper_bound:
                raise RuntimeError(
                    f"elapsed above backoff guardrail: elapsed={elapsed_sec:.3f}s, "
                    f"upper_bound={upper_bound:.3f}s"
                )
    except Exception as e:
        print(f"alert relay retry guardrail FAILED: {e}")
        return 2

    print(
        "alert relay retry guardrail OK: "
        f"channel={args.channel}, retries={retries_cfg}, elapsed={elapsed_sec:.3f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
