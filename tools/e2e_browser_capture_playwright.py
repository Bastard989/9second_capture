"""
Playwright e2e for browser capture scenarios in local UI.

Scenarios:
1) system mode capture
2) screen+audio capture
3) ws reconnect during recording
4) busy-device start failure (NotReadableError)
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable

import requests


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Playwright browser-capture e2e")
    p.add_argument("--base-url", default="http://127.0.0.1:8010", help="Agent base URL")
    p.add_argument("--user-key", default="", help="Optional API key for UI")
    p.add_argument("--timeout-sec", type=float, default=90.0, help="Timeout per scenario")
    p.add_argument("--headed", action="store_true", help="Run headed browser")
    p.add_argument(
        "--skip-if-playwright-missing",
        action="store_true",
        help="Exit 0 when playwright package is unavailable",
    )
    return p.parse_args()


def _wait_health(base_url: str, timeout_sec: float = 40.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url.rstrip('/')}/health", timeout=2.0)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.7)
    raise RuntimeError("health_not_ready")


def _safe_click(page, selector: str) -> None:
    page.wait_for_selector(selector, timeout=20000)
    page.click(selector)


def _set_required_fields(page, user_key: str) -> None:
    if user_key:
        page.fill("#apiKey", user_key)
    page.fill("#metaCandidateName", "Candidate E2E")
    page.fill("#metaCandidateId", "cand-e2e-001")
    page.fill("#metaVacancy", "Backend Engineer")
    page.fill("#metaLevel", "Senior")
    page.fill("#metaInterviewer", "Senior Reviewer")


def _force_virtual_system_source(page) -> None:
    page.evaluate(
        """
        () => {
          const s = document.getElementById('deviceSelect');
          if (!s) return false;
          if (!s.options.length) {
            const opt = document.createElement('option');
            opt.value = 'default';
            opt.textContent = 'BlackHole 2ch (Virtual)';
            s.appendChild(opt);
          }
          const first = s.options[0];
          if (!first.value) first.value = 'default';
          first.textContent = 'BlackHole 2ch (Virtual)';
          s.value = first.value;
          s.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
        """
    )


def _wait_recording_started(page, timeout_ms: int = 30000) -> None:
    page.wait_for_function(
        """
        () => {
          const t = (document.getElementById('statusText')?.textContent || '').toLowerCase();
          return t.includes('запись') || t.includes('recording');
        }
        """,
        timeout=timeout_ms,
    )


def _wait_chunks_progress(page, timeout_ms: int = 30000) -> None:
    page.wait_for_function(
        """
        () => {
          const v = Number((document.getElementById('chunkCount')?.textContent || '0').trim() || '0');
          return Number.isFinite(v) && v >= 1;
        }
        """,
        timeout=timeout_ms,
    )


def _stop_recording_if_needed(page) -> None:
    try:
        _safe_click(page, "#stopBtn")
        page.wait_for_timeout(1200)
    except Exception:
        return


def _scenario_system_with_ws_reconnect(page, timeout_sec: float) -> None:
    _safe_click(page, "input[name='captureMode'][value='system']")
    _force_virtual_system_source(page)
    _safe_click(page, "#startBtn")
    _wait_recording_started(page, timeout_ms=int(timeout_sec * 1000))
    _wait_chunks_progress(page, timeout_ms=int(timeout_sec * 1000))

    # Force WS reconnect path while recording.
    page.evaluate(
        """
        () => {
          try {
            if (typeof state !== 'undefined' && state && state.ws) {
              state.ws.close();
            }
          } catch (_err) {}
        }
        """
    )
    page.wait_for_timeout(1800)
    _wait_chunks_progress(page, timeout_ms=int(timeout_sec * 1000))
    _stop_recording_if_needed(page)


def _scenario_screen_audio(page, timeout_sec: float) -> None:
    page.evaluate(
        """
        () => {
          const md = navigator.mediaDevices;
          if (!md || md.__displayPatched) return;
          const origGetUserMedia = md.getUserMedia.bind(md);
          md.getDisplayMedia = async () => origGetUserMedia({ audio: true, video: true });
          md.__displayPatched = true;
        }
        """
    )
    _safe_click(page, "input[name='captureMode'][value='screen']")
    _safe_click(page, "#startBtn")
    _wait_recording_started(page, timeout_ms=int(timeout_sec * 1000))
    _wait_chunks_progress(page, timeout_ms=int(timeout_sec * 1000))
    _stop_recording_if_needed(page)


def _scenario_busy_device(page, timeout_sec: float) -> None:
    page.evaluate(
        """
        () => {
          const md = navigator.mediaDevices;
          if (!md || md.__busyPatched) return;
          const original = md.getUserMedia.bind(md);
          md.getUserMedia = async (...args) => {
            const err = new DOMException('device busy', 'NotReadableError');
            throw err;
          };
          md.__busyPatched = true;
          md.__busyRestore = () => { md.getUserMedia = original; md.__busyPatched = false; };
        }
        """
    )
    _safe_click(page, "input[name='captureMode'][value='system']")
    _safe_click(page, "#startBtn")
    page.wait_for_function(
        """
        () => {
          const status = (document.getElementById('statusText')?.textContent || '').toLowerCase();
          const hint = (document.getElementById('statusHint')?.textContent || '').toLowerCase();
          return (
            status.includes('ошибка') || status.includes('error') ||
            hint.includes('занят') || hint.includes('busy')
          );
        }
        """,
        timeout=int(timeout_sec * 1000),
    )
    page.evaluate("""() => { if (navigator.mediaDevices.__busyRestore) navigator.mediaDevices.__busyRestore(); }""")


def _run_scenario(name: str, fn: Callable[[], None]) -> None:
    started = time.time()
    fn()
    elapsed = time.time() - started
    print(f"[playwright-e2e] {name}: OK ({elapsed:.1f}s)")


def main() -> int:
    args = _args()
    base_url = args.base_url.rstrip("/")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as err:
        if args.skip_if_playwright_missing:
            print(f"[playwright-e2e] skipped: playwright unavailable: {err}")
            return 0
        print(f"[playwright-e2e] playwright import failed: {err}")
        return 2

    _wait_health(base_url)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=not bool(args.headed),
            args=[
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                "--allow-http-screen-capture",
                "--auto-select-desktop-capture-source=Entire screen",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(f"{base_url}/", wait_until="domcontentloaded")

        _set_required_fields(page, args.user_key)
        _run_scenario(
            "system-mode+ws-reconnect",
            lambda: _scenario_system_with_ws_reconnect(page, timeout_sec=float(args.timeout_sec)),
        )
        _run_scenario(
            "screen+audio",
            lambda: _scenario_screen_audio(page, timeout_sec=float(args.timeout_sec)),
        )
        _run_scenario(
            "busy-device",
            lambda: _scenario_busy_device(page, timeout_sec=float(args.timeout_sec)),
        )

        context.close()
        browser.close()

    print("[playwright-e2e] all scenarios passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:
        print(f"[playwright-e2e] failed: {err}")
        raise
