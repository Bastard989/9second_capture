from __future__ import annotations

import re
from dataclasses import dataclass

_NON_WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_MULTI_SPACE_RE = re.compile(r"\s+")


def normalize_for_wer(text: str) -> str:
    cleaned = _NON_WORD_RE.sub(" ", str(text or "").lower())
    return _MULTI_SPACE_RE.sub(" ", cleaned).strip()


def _levenshtein_distance(ref: list[str], hyp: list[str]) -> int:
    if not ref:
        return len(hyp)
    if not hyp:
        return len(ref)

    prev = list(range(len(hyp) + 1))
    for i, r_word in enumerate(ref, start=1):
        curr = [i] + [0] * len(hyp)
        for j, h_word in enumerate(hyp, start=1):
            cost = 0 if r_word == h_word else 1
            curr[j] = min(
                prev[j] + 1,  # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution
            )
        prev = curr
    return prev[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_tokens = normalize_for_wer(reference).split()
    hyp_tokens = normalize_for_wer(hypothesis).split()
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    distance = _levenshtein_distance(ref_tokens, hyp_tokens)
    return float(distance) / float(len(ref_tokens))


@dataclass
class WERCaseResult:
    case_id: str
    wer: float
    max_wer: float
    passed: bool


def evaluate_wer_cases(cases: list[dict[str, object]]) -> list[WERCaseResult]:
    results: list[WERCaseResult] = []
    for raw_case in cases:
        case_id = str(raw_case.get("id") or "").strip() or "case"
        reference = str(raw_case.get("reference") or "")
        hypothesis = str(raw_case.get("hypothesis") or "")
        max_wer = float(raw_case.get("max_wer") or 1.0)
        wer = word_error_rate(reference, hypothesis)
        results.append(
            WERCaseResult(
                case_id=case_id,
                wer=wer,
                max_wer=max_wer,
                passed=wer <= max_wer,
            )
        )
    return results

