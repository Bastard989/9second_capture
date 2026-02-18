"""
STT WER guardrail for benchmark audio fixtures.

Manifest JSON format:
[
  {
    "id": "case_backend_interview_1",
    "audio_path": "tests/fixtures/audio/backend_interview_1.wav",
    "reference": "expected transcript text",
    "max_wer": 0.24,
    "quality_profile": "final",
    "source_track": "mixed"
  }
]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any


def _bootstrap_pythonpath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for path in (repo_root, repo_root / "src"):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


_bootstrap_pythonpath()

from interview_analytics_agent.processing.wer import word_error_rate  # noqa: E402


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="STT WER guardrail for real audio fixtures")
    p.add_argument(
        "--manifest",
        default="tests/fixtures/stt_audio_wer_manifest.json",
        help="Path to audio WER manifest JSON",
    )
    p.add_argument(
        "--report-json",
        default="reports/stt_wer_guardrail.json",
        help="Where to write JSON report",
    )
    p.add_argument(
        "--max-avg-wer",
        type=float,
        default=0.42,
        help="Maximum average WER across executed cases",
    )
    p.add_argument(
        "--max-avg-wer-fast",
        type=float,
        default=0.52,
        help="Maximum average WER for fast/live_fast profile",
    )
    p.add_argument(
        "--max-avg-wer-balanced",
        type=float,
        default=0.45,
        help="Maximum average WER for balanced/live_balanced profile",
    )
    p.add_argument(
        "--max-avg-wer-accurate",
        type=float,
        default=0.40,
        help="Maximum average WER for accurate/live_accurate/final profile",
    )
    p.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Sample rate hint passed to STT provider",
    )
    p.add_argument(
        "--allow-missing-fixtures",
        action="store_true",
        help="Do not fail when manifest/audio files are absent (report will be marked skipped)",
    )
    return p.parse_args()


def _load_manifest(path: Path, *, allow_missing: bool) -> list[dict[str, Any]]:
    if not path.exists():
        if allow_missing:
            return []
        raise FileNotFoundError(f"manifest_not_found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("manifest_invalid: root must be an array")
    cases: list[dict[str, Any]] = []
    for idx, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"manifest_invalid_case_{idx}: case must be an object")
        cases.append(item)
    return cases


def _run_case(
    *,
    provider: Any,
    case: dict[str, Any],
    sample_rate: int,
) -> dict[str, Any]:
    case_id = str(case.get("id") or "").strip() or "case"
    audio_path = Path(str(case.get("audio_path") or "").strip())
    reference = str(case.get("reference") or "")
    max_wer = float(case.get("max_wer") or 1.0)
    quality_profile = str(case.get("quality_profile") or "final").strip() or "final"
    source_track = str(case.get("source_track") or "mixed").strip() or "mixed"
    language_hint = str(case.get("language_hint") or "").strip() or None

    if not audio_path.exists():
        return {
            "id": case_id,
            "audio_path": str(audio_path),
            "status": "missing_audio",
            "reference": reference,
            "hypothesis": "",
            "wer": None,
            "max_wer": max_wer,
            "quality_profile": quality_profile,
            "language_hint": language_hint or "",
            "passed": False,
        }

    audio_bytes = audio_path.read_bytes()
    stt = provider.transcribe_chunk(
        audio=audio_bytes,
        sample_rate=sample_rate,
        quality_profile=quality_profile,
        source_track=source_track,
        language_hint=language_hint,
    )
    hypothesis = str(stt.text or "").strip()
    wer = word_error_rate(reference, hypothesis)
    return {
        "id": case_id,
        "audio_path": str(audio_path),
        "status": "ok",
        "reference": reference,
        "hypothesis": hypothesis,
        "wer": wer,
        "max_wer": max_wer,
        "quality_profile": quality_profile,
        "language_hint": language_hint or "",
        "passed": wer <= max_wer,
    }


def _profile_bucket(quality_profile: str) -> str:
    qp = str(quality_profile or "").strip().lower()
    if qp in {"fast", "live_fast"}:
        return "fast"
    if qp in {"accurate", "live_accurate", "final"}:
        return "accurate"
    return "balanced"


def _probe_whisper_runtime_init(timeout_sec: int = 15) -> str:
    """
    Запускает отдельный процесс с инициализацией WhisperLocalProvider.
    Это защищает основной guardrail от native-crash/hang в OpenMP runtime.
    """
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    py_path_parts: list[str] = [str(repo_root), str(repo_root / "src")]
    existing_py = str(env.get("PYTHONPATH") or "").strip()
    if existing_py:
        py_path_parts.append(existing_py)
    env["PYTHONPATH"] = os.pathsep.join(py_path_parts)

    probe_code = (
        "from interview_analytics_agent.stt.whisper_local import WhisperLocalProvider;"
        "WhisperLocalProvider();"
        "print('ok')"
    )
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", probe_code],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except Exception as err:
        return f"whisper_runtime_probe_spawn_error:{err}"

    try:
        out, err = proc.communicate(timeout=int(timeout_sec))
    except subprocess.TimeoutExpired:
        with suppress(Exception):
            proc.kill()
        return f"whisper_runtime_probe_timeout:{int(timeout_sec)}s"
    except Exception as err:
        with suppress(Exception):
            proc.kill()
        return f"whisper_runtime_probe_error:{err}"

    if proc.returncode == 0:
        return ""
    details = " ".join(
        part.strip()
        for part in (str(out or "").strip(), str(err or "").strip())
        if part and part.strip()
    ).strip()
    return details or f"whisper_runtime_probe_failed:exit_code={int(proc.returncode or -1)}"


def main() -> int:
    args = _args()
    manifest_path = Path(args.manifest).resolve()
    report_path = Path(args.report_json).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        cases = _load_manifest(manifest_path, allow_missing=bool(args.allow_missing_fixtures))
    except Exception as err:
        report = {
            "ok": False,
            "status": "failed",
            "error": str(err),
            "manifest": str(manifest_path),
            "cases_total": 0,
            "cases_executed": 0,
            "results": [],
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[stt-wer-guardrail] failed: {err}")
        return 1

    if not cases:
        report = {
            "ok": True,
            "status": "skipped",
            "reason": "no_manifest_or_no_cases",
            "manifest": str(manifest_path),
            "cases_total": 0,
            "cases_executed": 0,
            "results": [],
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[stt-wer-guardrail] skipped: no cases found")
        return 0

    try:
        from interview_analytics_agent.stt.whisper_local import WhisperLocalProvider
    except Exception as err:
        report = {
            "ok": bool(args.allow_missing_fixtures),
            "status": "skipped" if bool(args.allow_missing_fixtures) else "failed",
            "reason": "stt_runtime_unavailable",
            "error": str(err),
            "manifest": str(manifest_path),
            "cases_total": len(cases),
            "cases_executed": 0,
            "results": [],
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[stt-wer-guardrail] stt runtime unavailable: {err}")
        return 0 if bool(args.allow_missing_fixtures) else 1

    probe_error = _probe_whisper_runtime_init()
    if probe_error:
        report = {
            "ok": bool(args.allow_missing_fixtures),
            "status": "skipped" if bool(args.allow_missing_fixtures) else "failed",
            "reason": "stt_runtime_init_failed",
            "error": probe_error,
            "manifest": str(manifest_path),
            "cases_total": len(cases),
            "cases_executed": 0,
            "results": [],
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[stt-wer-guardrail] stt runtime init failed: {probe_error}")
        return 0 if bool(args.allow_missing_fixtures) else 1

    provider = WhisperLocalProvider()
    results: list[dict[str, Any]] = []
    for case in cases:
        results.append(_run_case(provider=provider, case=case, sample_rate=int(args.sample_rate)))

    missing_audio = [item for item in results if item.get("status") == "missing_audio"]
    executed = [item for item in results if item.get("status") == "ok"]
    failed = [item for item in executed if not bool(item.get("passed"))]
    avg_wer = 0.0
    if executed:
        avg_wer = sum(float(item.get("wer") or 0.0) for item in executed) / float(len(executed))

    profile_limits = {
        "fast": float(args.max_avg_wer_fast),
        "balanced": float(args.max_avg_wer_balanced),
        "accurate": float(args.max_avg_wer_accurate),
    }
    profile_summary: dict[str, dict[str, Any]] = {}
    for profile in ("fast", "balanced", "accurate"):
        rows = [item for item in executed if _profile_bucket(str(item.get("quality_profile") or "")) == profile]
        avg_value = (
            sum(float(item.get("wer") or 0.0) for item in rows) / float(len(rows))
            if rows
            else None
        )
        threshold = profile_limits[profile]
        profile_summary[profile] = {
            "cases": len(rows),
            "avg_wer": avg_value,
            "max_avg_wer": threshold,
            "ok": avg_value is None or avg_value <= threshold,
        }

    missing_blocker = bool(missing_audio) and not bool(args.allow_missing_fixtures)
    avg_ok = avg_wer <= float(args.max_avg_wer)
    profiles_ok = all(bool(item.get("ok")) for item in profile_summary.values())
    ok = (not missing_blocker) and (not failed) and avg_ok and profiles_ok and bool(executed)
    status = "ok" if ok else "failed"

    report = {
        "ok": ok,
        "status": status,
        "manifest": str(manifest_path),
        "cases_total": len(cases),
        "cases_executed": len(executed),
        "missing_audio_count": len(missing_audio),
        "failed_count": len(failed),
        "avg_wer": avg_wer,
        "max_avg_wer": float(args.max_avg_wer),
        "profile_summary": profile_summary,
        "results": results,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if missing_audio:
        print(
            "[stt-wer-guardrail] missing audio fixtures: "
            + ", ".join(str(item.get("audio_path") or "") for item in missing_audio)
        )
    if failed:
        print(
            "[stt-wer-guardrail] failed cases: "
            + ", ".join(f"{item['id']}={float(item['wer']):.3f}>{float(item['max_wer']):.3f}" for item in failed)
        )
    print(
        "[stt-wer-guardrail] "
        f"executed={len(executed)} avg_wer={avg_wer:.3f} threshold={float(args.max_avg_wer):.3f}"
    )
    for profile in ("fast", "balanced", "accurate"):
        summary = profile_summary.get(profile) or {}
        avg_text = (
            "n/a" if summary.get("avg_wer") is None else f"{float(summary.get('avg_wer') or 0.0):.3f}"
        )
        print(
            "[stt-wer-guardrail] "
            f"profile={profile} cases={int(summary.get('cases') or 0)} "
            f"avg_wer={avg_text} threshold={float(summary.get('max_avg_wer') or 0.0):.3f}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
