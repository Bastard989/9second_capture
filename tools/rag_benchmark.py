#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases") if isinstance(raw, dict) else None
    if not isinstance(cases, list):
        raise ValueError("dataset must contain object with 'cases' list")
    out: list[dict[str, Any]] = []
    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            continue
        query = str(case.get("query") or "").strip()
        if not query:
            continue
        out.append(
            {
                "id": str(case.get("id") or f"case_{idx}").strip(),
                "query": query,
                "meeting_ids": [str(x).strip() for x in list(case.get("meeting_ids") or []) if str(x).strip()],
                "expected_chunk_ids": [
                    str(x).strip() for x in list(case.get("expected_chunk_ids") or []) if str(x).strip()
                ],
                "expected_text_contains": [
                    str(x).strip() for x in list(case.get("expected_text_contains") or []) if str(x).strip()
                ],
            }
        )
    if not out:
        raise ValueError("dataset has no valid cases")
    return out


def _http_post_json(url: str, payload: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        text = resp.read().decode("utf-8")
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("invalid JSON response")
    return obj


def _hit_relevant(
    hit: dict[str, Any],
    *,
    expected_chunk_ids: set[str],
    expected_text_contains: list[str],
) -> bool:
    chunk_id = str(hit.get("chunk_id") or "").strip()
    if chunk_id and chunk_id in expected_chunk_ids:
        return True
    text = str(hit.get("text") or "").lower()
    for snippet in expected_text_contains:
        if snippet.lower() in text:
            return True
    return False


def _dcg(relevances: list[int]) -> float:
    total = 0.0
    for i, rel in enumerate(relevances, start=1):
        if rel <= 0:
            continue
        total += float(rel) / math.log2(i + 1.0)
    return total


def _evaluate_case(resp: dict[str, Any], case: dict[str, Any], top_k: int) -> dict[str, Any]:
    hits = list(resp.get("hits") or [])
    expected_chunk_ids = set(case["expected_chunk_ids"])
    expected_text_contains = list(case["expected_text_contains"])
    relevant_total = len(expected_chunk_ids) + len(expected_text_contains)
    if relevant_total <= 0:
        relevant_total = 1

    relevances: list[int] = []
    first_rel_rank = 0
    for idx, raw_hit in enumerate(hits[:top_k], start=1):
        hit = raw_hit if isinstance(raw_hit, dict) else {}
        relevant = 1 if _hit_relevant(hit, expected_chunk_ids=expected_chunk_ids, expected_text_contains=expected_text_contains) else 0
        relevances.append(relevant)
        if relevant > 0 and first_rel_rank == 0:
            first_rel_rank = idx

    recall = float(sum(relevances)) / float(relevant_total)
    mrr = (1.0 / float(first_rel_rank)) if first_rel_rank > 0 else 0.0
    ideal_rels = [1] * min(top_k, relevant_total)
    ndcg = (_dcg(relevances) / _dcg(ideal_rels)) if ideal_rels else 0.0
    return {
        "id": case["id"],
        "query": case["query"],
        "hits_returned": len(hits),
        "relevant_hits_at_k": int(sum(relevances)),
        "relevant_total": int(relevant_total),
        "recall_at_k": round(recall, 6),
        "mrr": round(mrr, 6),
        "ndcg_at_k": round(ndcg, 6),
        "warnings": list(resp.get("warnings") or []),
    }


def run(args: argparse.Namespace) -> int:
    cases = _load_dataset(Path(args.dataset))
    api_base = str(args.api_base).rstrip("/")
    url = f"{api_base}/v1/rag/query"

    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    for case in cases:
        payload = {
            "query": case["query"],
            "transcript_variant": args.source,
            "meeting_ids": case["meeting_ids"],
            "top_k": int(args.top_k),
            "auto_index": bool(args.auto_index),
            "force_reindex": bool(args.force_reindex),
            "answer_mode": "none",
        }
        try:
            resp = _http_post_json(url=url, payload=payload, timeout_sec=int(args.timeout_sec))
            results.append(_evaluate_case(resp, case, int(args.top_k)))
        except urllib.error.HTTPError as exc:
            results.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "error": f"http_{exc.code}",
                    "recall_at_k": 0.0,
                    "mrr": 0.0,
                    "ndcg_at_k": 0.0,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "error": str(exc)[:200],
                    "recall_at_k": 0.0,
                    "mrr": 0.0,
                    "ndcg_at_k": 0.0,
                }
            )

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    valid = [row for row in results if "error" not in row]
    denom = float(len(valid) or 1.0)
    summary = {
        "cases_total": len(results),
        "cases_ok": len(valid),
        "recall_at_k_avg": round(sum(float(row.get("recall_at_k") or 0.0) for row in valid) / denom, 6),
        "mrr_avg": round(sum(float(row.get("mrr") or 0.0) for row in valid) / denom, 6),
        "ndcg_at_k_avg": round(sum(float(row.get("ndcg_at_k") or 0.0) for row in valid) / denom, 6),
        "elapsed_ms": round(elapsed_ms, 2),
    }
    report = {
        "schema_version": "v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "api_base": api_base,
        "source": args.source,
        "top_k": int(args.top_k),
        "summary": summary,
        "cases": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="RAG retrieval benchmark for 9second_capture")
    p.add_argument("--api-base", default="http://127.0.0.1:8010")
    p.add_argument("--dataset", required=True, help="Path to benchmark dataset JSON")
    p.add_argument("--source", choices=["raw", "normalized", "clean"], default="clean")
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--timeout-sec", type=int, default=120)
    p.add_argument("--auto-index", action="store_true", default=True)
    p.add_argument("--force-reindex", action="store_true", default=False)
    p.add_argument("--output", default="", help="Optional output JSON path")
    return p


if __name__ == "__main__":
    raise SystemExit(run(_parser().parse_args()))
