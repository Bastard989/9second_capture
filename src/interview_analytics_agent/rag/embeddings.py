from __future__ import annotations

import hashlib
import math
import re
from urllib.parse import urlparse

import requests

_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-я_+\-]{2,}", flags=re.UNICODE)


def hashing_embedding_model_id(*, dim: int = 96, char_ngrams: bool = True) -> str:
    return f"hashing_v1_dim{max(8, int(dim))}_{'char' if char_ngrams else 'word'}"


def _stable_feature_hash(feature: str) -> bytes:
    return hashlib.sha1(feature.encode("utf-8")).digest()


def _feature_index_sign(feature: str, dim: int) -> tuple[int, float]:
    digest = _stable_feature_hash(feature)
    idx = int.from_bytes(digest[:4], "big") % max(1, int(dim))
    sign = 1.0 if (digest[4] & 1) == 0 else -1.0
    return idx, sign


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(str(text or ""))]


def _iter_char_ngrams(token: str, *, n_min: int = 3, n_max: int = 4):
    txt = str(token or "").lower()
    if len(txt) < max(2, n_min):
        return
    padded = f"^{txt}$"
    for n in range(max(2, n_min), max(n_min, n_max) + 1):
        if len(padded) < n:
            continue
        for i in range(0, len(padded) - n + 1):
            yield padded[i : i + n]


def embed_text_hashing(
    text: str,
    *,
    dim: int = 96,
    char_ngrams: bool = True,
) -> list[float]:
    dim_safe = max(8, min(int(dim or 96), 2048))
    vec = [0.0] * dim_safe
    tokens = _tokenize(text)
    if not tokens:
        return vec

    for token in tokens:
        idx, sign = _feature_index_sign(f"w:{token}", dim_safe)
        vec[idx] += 1.0 * sign
        if char_ngrams and len(token) >= 4:
            for gram in _iter_char_ngrams(token):
                gidx, gsign = _feature_index_sign(f"g:{gram}", dim_safe)
                vec[gidx] += 0.18 * gsign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return [0.0] * dim_safe
    return [round(v / norm, 8) for v in vec]


def cosine_similarity_dense(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n <= 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        av = float(a[i] or 0.0)
        bv = float(b[i] or 0.0)
        dot += av * bv
        na += av * av
        nb += bv * bv
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(dot / math.sqrt(na * nb))


def is_local_openai_compat_base(api_base: str) -> bool:
    value = (api_base or "").strip()
    if not value:
        return False
    try:
        host = (urlparse(value).hostname or "").strip().lower()
    except Exception:
        host = ""
    return host in {"127.0.0.1", "localhost"}


def _resolve_openai_compat_bearer(api_base: str, api_key: str) -> str:
    key = (api_key or "").strip()
    if key:
        return key
    if is_local_openai_compat_base(api_base):
        return "ollama"
    return ""


def _normalize_dense_embedding(vec: list[float]) -> list[float]:
    if not vec:
        return []
    norm = math.sqrt(sum(float(v or 0.0) * float(v or 0.0) for v in vec))
    if norm <= 1e-12:
        return [0.0 for _ in vec]
    return [round(float(v or 0.0) / norm, 8) for v in vec]


def embed_text_openai_compat(
    text: str,
    *,
    api_base: str,
    api_key: str,
    model_id: str,
    timeout_s: float = 8.0,
) -> list[float]:
    return embed_texts_openai_compat(
        [text],
        api_base=api_base,
        api_key=api_key,
        model_id=model_id,
        timeout_s=timeout_s,
    )[0]


def embed_texts_openai_compat(
    texts: list[str] | tuple[str, ...],
    *,
    api_base: str,
    api_key: str,
    model_id: str,
    timeout_s: float = 8.0,
) -> list[list[float]]:
    base = str(api_base or "").strip()
    model = str(model_id or "").strip()
    if not base:
        raise ValueError("api_base is required")
    if not model:
        raise ValueError("model_id is required")
    items = [str(text or "") for text in list(texts or [])]
    if not items:
        return []

    url = base.rstrip("/") + "/embeddings"
    headers = {"Content-Type": "application/json"}
    bearer = _resolve_openai_compat_bearer(base, str(api_key or ""))
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    payload = {
        "model": model,
        "input": items if len(items) > 1 else items[0],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=max(1.0, float(timeout_s or 8.0)))
    if resp.status_code >= 400:
        raise RuntimeError(f"embeddings_http_{resp.status_code}:{(resp.text or '')[:180]}")
    try:
        body = resp.json()
    except Exception as exc:
        raise RuntimeError(f"embeddings_invalid_json:{exc}") from exc
    rows = body.get("data") if isinstance(body, dict) else []
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("embeddings_missing_data")
    ordered_rows = [None] * len(rows)
    by_append: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        idx_raw = row.get("index")
        if isinstance(idx_raw, int) and 0 <= idx_raw < len(items):
            ordered_rows[idx_raw] = row
        else:
            by_append.append(row)
    if any(r is None for r in ordered_rows):
        # Fallback for providers that omit `index` but preserve order.
        ordered_rows = []
        for row in rows:
            if isinstance(row, dict):
                ordered_rows.append(row)
    if len(ordered_rows) != len(items):
        raise RuntimeError(
            f"embeddings_count_mismatch:expected={len(items)} got={len(ordered_rows)}"
        )
    out: list[list[float]] = []
    for row in ordered_rows:
        emb = row.get("embedding") if isinstance(row, dict) else None
        if not isinstance(emb, list) or not emb:
            raise RuntimeError("embeddings_missing_vector")
        try:
            values = [float(v or 0.0) for v in emb]
        except Exception as exc:
            raise RuntimeError(f"embeddings_invalid_vector:{exc}") from exc
        out.append(_normalize_dense_embedding(values))
    return out


def embed_text_gemini(
    text: str,
    *,
    api_base: str,
    api_key: str,
    model_id: str,
    timeout_s: float = 8.0,
) -> list[float]:
    items = embed_texts_gemini(
        [text],
        api_base=api_base,
        api_key=api_key,
        model_id=model_id,
        timeout_s=timeout_s,
    )
    return items[0] if items else []


def embed_texts_gemini(
    texts: list[str] | tuple[str, ...],
    *,
    api_base: str,
    api_key: str,
    model_id: str,
    timeout_s: float = 8.0,
) -> list[list[float]]:
    base = str(api_base or "").strip()
    model = str(model_id or "").strip().removeprefix("models/")
    key = str(api_key or "").strip()
    if not base:
        raise ValueError("api_base is required")
    if not model:
        raise ValueError("model_id is required")
    if not key:
        raise ValueError("api_key is required")
    items = [str(text or "") for text in list(texts or [])]
    if not items:
        return []

    out: list[list[float]] = []
    url = base.rstrip("/") + f"/models/{model}:embedContent?key={key}"
    headers = {"Content-Type": "application/json"}
    for text in items:
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=max(1.0, float(timeout_s or 8.0)))
        if resp.status_code >= 400:
            raise RuntimeError(f"embeddings_http_{resp.status_code}:{(resp.text or '')[:180]}")
        try:
            body = resp.json()
        except Exception as exc:
            raise RuntimeError(f"embeddings_invalid_json:{exc}") from exc
        embedding = body.get("embedding") if isinstance(body, dict) else None
        values = embedding.get("values") if isinstance(embedding, dict) else None
        if not isinstance(values, list) or not values:
            raise RuntimeError("embeddings_missing_vector")
        try:
            dense = [float(v or 0.0) for v in values]
        except Exception as exc:
            raise RuntimeError(f"embeddings_invalid_vector:{exc}") from exc
        out.append(_normalize_dense_embedding(dense))
    return out
