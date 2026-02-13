"""
Release checks for GitHub release workflow.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def _bootstrap_pythonpath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for path in (repo_root, repo_root / "src"):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


_bootstrap_pythonpath()

from interview_analytics_agent.common.release_policy import (
    verify_openapi_file,
    verify_release_tag_matches_project_version,
)


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate release policy")
    p.add_argument(
        "--tag", default=os.getenv("GITHUB_REF_NAME", ""), help="Release tag (e.g. v0.1.0)"
    )
    p.add_argument("--pyproject", default="pyproject.toml", help="Path to pyproject.toml")
    p.add_argument("--openapi", default="openapi/openapi.json", help="Path to OpenAPI spec")
    p.add_argument(
        "--wer-manifest",
        default="tests/fixtures/stt_audio_wer_manifest.json",
        help="Path to WER audio manifest",
    )
    return p.parse_args()


def _verify_wer_manifest(path: str) -> None:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise ValueError(f"WER manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("WER manifest is empty")
    for idx, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"WER manifest case#{idx} is not an object")
        audio_path = Path(str(item.get("audio_path") or "").strip())
        if not audio_path.exists():
            raise ValueError(f"WER manifest case#{idx} audio file missing: {audio_path}")
        reference = str(item.get("reference") or "").strip()
        if not reference:
            raise ValueError(f"WER manifest case#{idx} missing reference transcript")


def main() -> int:
    args = _args()
    try:
        v = verify_release_tag_matches_project_version(tag=args.tag, pyproject_path=args.pyproject)
        verify_openapi_file(args.openapi)
        _verify_wer_manifest(args.wer_manifest)
    except ValueError as e:
        print(f"release-check failed: {e}")
        return 2

    print(f"release-check OK: version={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
