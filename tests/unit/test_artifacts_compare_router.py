from __future__ import annotations

from datetime import datetime
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api_gateway.routers import artifacts as artifacts_router
from interview_analytics_agent.common.config import get_settings


@pytest.fixture()
def auth_none_settings():
    s = get_settings()
    snapshot = s.auth_mode
    snapshot_rag_provider = getattr(s, "rag_embedding_provider", "auto")
    snapshot_openai_api_base = getattr(s, "openai_api_base", None)
    snapshot_embedding_api_base = getattr(s, "embedding_api_base", None)
    try:
        s.auth_mode = "none"
        s.rag_embedding_provider = "hashing"
        s.openai_api_base = None
        s.embedding_api_base = None
        yield s
    finally:
        s.auth_mode = snapshot
        s.rag_embedding_provider = snapshot_rag_provider
        s.openai_api_base = snapshot_openai_api_base
        s.embedding_api_base = snapshot_embedding_api_base


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(artifacts_router.router, prefix="/v1")
    return TestClient(app)


def test_compare_endpoint_returns_items(monkeypatch, auth_none_settings) -> None:
    payload = artifacts_router.CompareMeetingsResponse(
        generated_at="2026-02-12T12:40:00Z",
        source="clean",
        items=[
            artifacts_router.CompareMeetingItem(
                meeting_id="m1",
                created_at=datetime(2026, 2, 12, 12, 0, 0),
                source="clean",
                candidate_name="Alice",
                vacancy="Backend Engineer",
                level="Senior",
                interviewer="Bob",
                overall_score=4.2,
                decision_status="yes",
                decision_confidence=0.74,
                transcript_quality="high",
                comparable=True,
                summary="Strong interview signal.",
            )
        ],
    )
    monkeypatch.setattr(artifacts_router, "_build_compare_response", lambda **kwargs: payload)

    client = _client()
    resp = client.get("/v1/meetings/compare?source=clean&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "clean"
    assert len(body["items"]) == 1
    assert body["items"][0]["candidate_name"] == "Alice"


def test_compare_export_csv(monkeypatch, auth_none_settings) -> None:
    payload = artifacts_router.CompareMeetingsResponse(
        generated_at="2026-02-12T12:40:00Z",
        source="clean",
        items=[
            artifacts_router.CompareMeetingItem(
                meeting_id="m1",
                source="clean",
                candidate_name="Alice",
                vacancy="Backend Engineer",
                level="Senior",
                interviewer="Bob",
                overall_score=4.2,
                decision_status="yes",
                decision_confidence=0.74,
                transcript_quality="high",
                comparable=True,
                summary="Strong interview signal.",
            )
        ],
    )
    monkeypatch.setattr(artifacts_router, "_build_compare_response", lambda **kwargs: payload)

    client = _client()
    resp = client.get("/v1/meetings/compare/export?source=clean&fmt=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert resp.content.startswith(b"\xef\xbb\xbf")


def test_generate_senior_brief_writes_artifact(monkeypatch, auth_none_settings) -> None:
    written = {"meeting_id": "", "filename": "", "text": ""}
    monkeypatch.setattr(
        artifacts_router,
        "_load_or_build_report",
        lambda **kwargs: {"summary": "ok", "scorecard": [], "decision": {}},
    )
    monkeypatch.setattr(
        artifacts_router,
        "_senior_brief_text",
        lambda **kwargs: "Senior Brief\n...",
    )
    monkeypatch.setattr(
        artifacts_router.records,
        "write_text",
        lambda meeting_id, filename, text: written.update(
            {"meeting_id": meeting_id, "filename": filename, "text": text}
        ),
    )

    client = _client()
    resp = client.post("/v1/meetings/m1/senior-brief", json={"source": "clean"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["filename"] == "senior_brief_clean.txt"
    assert written["meeting_id"] == "m1"
    assert written["filename"] == "senior_brief_clean.txt"


def test_generate_transcripts_endpoint_returns_requested_variants(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "_ensure_transcript_variants",
        lambda *args, **kwargs: {
            "raw": "A: raw text",
            "normalized": "A: normalized text",
            "clean": "A: clean text",
        },
    )

    client = _client()
    resp = client.post(
        "/v1/meetings/m1/transcripts/generate",
        json={"variants": ["raw", "normalized"], "force_rebuild": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["meeting_id"] == "m1"
    assert [item["variant"] for item in body["items"]] == ["raw", "normalized"]
    assert body["items"][1]["filename"] == "normalized.txt"
    assert body["items"][1]["generated"] is True


def test_get_transcript_json_endpoint_returns_text(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "_ensure_transcript_text",
        lambda *args, **kwargs: "CANDIDATE: привет.",
    )

    client = _client()
    resp = client.get("/v1/meetings/m1/transcripts/normalized?fmt=json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["variant"] == "normalized"
    assert body["filename"] == "normalized.txt"
    assert body["text"] == "CANDIDATE: привет."


def test_generate_report_accepts_normalized_source(monkeypatch, auth_none_settings) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        artifacts_router,
        "_transcript_for_source",
        lambda **kwargs: "CANDIDATE: normalized transcript",
    )
    monkeypatch.setattr(
        artifacts_router,
        "build_report",
        lambda **kwargs: calls.setdefault("report_payload", {"summary": "ok", "decision": {}, "scorecard": []}),
    )
    monkeypatch.setattr(
        artifacts_router.records,
        "write_json",
        lambda meeting_id, filename, payload: calls.update(
            {"json_meeting_id": meeting_id, "json_filename": filename, "json_payload": payload}
        ),
    )
    monkeypatch.setattr(
        artifacts_router.records,
        "write_text",
        lambda meeting_id, filename, text: calls.update(
            {"txt_meeting_id": meeting_id, "txt_filename": filename, "txt_payload": text}
        ),
    )
    monkeypatch.setattr(artifacts_router, "report_to_text", lambda report: "analysis text")

    client = _client()
    resp = client.post("/v1/meetings/m1/report", json={"source": "normalized"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["source"] == "normalized"
    assert calls["json_filename"] == "report_normalized.json"
    assert calls["txt_filename"] == "report_normalized.txt"


def test_generate_analysis_alias_calls_report(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "generate_report",
        lambda meeting_id, req, _=None: {"ok": True, "meeting_id": meeting_id, "source": req.source, "alias": "analysis"},
    )

    client = _client()
    resp = client.post("/v1/meetings/m1/analysis", json={"source": "clean"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["alias"] == "analysis"
    assert body["source"] == "clean"


def _sample_llm_artifact_meta(*, meeting_id: str = "m1", artifact_id: str = "abc123") -> dict:
    return {
        "schema_version": "v1",
        "artifact_id": artifact_id,
        "meeting_id": meeting_id,
        "mode": "template",
        "transcript_variant": "clean",
        "template_id": "analysis",
        "status": "ok",
        "created_at": "2026-02-26T12:00:00Z",
        "transcript_chars": 128,
        "transcript_sha256": "deadbeef",
        "result_kind": "analysis",
        "files": [
            {"fmt": "json", "filename": "result.json", "bytes": 12},
            {"fmt": "txt", "filename": "result.txt", "bytes": 34},
        ],
    }


def test_llm_artifact_generate_endpoint_returns_response(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "_generate_llm_artifact",
        lambda **kwargs: (_sample_llm_artifact_meta(), False),
    )

    client = _client()
    resp = client.post(
        "/v1/meetings/m1/artifacts/generate",
        json={
            "mode": "template",
            "template_id": "analysis",
            "transcript_variant": "normalized",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["meeting_id"] == "m1"
    assert body["artifact_id"] == "abc123"
    assert body["cached"] is False
    assert body["files"][0]["fmt"] == "json"


def test_llm_artifact_meta_endpoint_reads_saved_meta(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "_read_llm_artifact_meta",
        lambda **kwargs: _sample_llm_artifact_meta(meeting_id="m9", artifact_id="aid9"),
    )

    client = _client()
    resp = client.get("/v1/meetings/m9/artifacts/aid9")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meeting_id"] == "m9"
    assert body["artifact_id"] == "aid9"
    assert body["cached"] is True


def test_llm_artifact_download_endpoint_returns_requested_file(monkeypatch, tmp_path, auth_none_settings) -> None:
    path = tmp_path / "result.csv"
    path.write_bytes(b"\xef\xbb\xbfcol1,col2\n1,2\n")
    monkeypatch.setattr(artifacts_router, "_artifact_result_download_path", lambda **kwargs: path)

    client = _client()
    resp = client.get("/v1/meetings/m1/artifacts/a1/download?fmt=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.content.startswith(b"\xef\xbb\xbf")


def test_generate_llm_artifact_template_caches_by_fingerprint(monkeypatch, tmp_path, auth_none_settings) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir
    try:
        settings.records_dir = str(tmp_path)
        monkeypatch.setattr(
            artifacts_router,
            "_transcript_for_source",
            lambda **kwargs: "CANDIDATE: raw transcript text",
        )
        monkeypatch.setattr(
            artifacts_router,
            "build_report",
            lambda **kwargs: {"summary": "ok", "decision": {}, "scorecard": []},
        )
        monkeypatch.setattr(artifacts_router, "report_to_text", lambda report: "analysis text")

        req = artifacts_router.LLMArtifactGenerateRequest(
            transcript_variant="clean",
            mode="template",
            template_id="analysis",
        )
        meta_1, cached_1 = artifacts_router._generate_llm_artifact("m1", req)
        meta_2, cached_2 = artifacts_router._generate_llm_artifact("m1", req)

        assert cached_1 is False
        assert cached_2 is True
        assert meta_1["artifact_id"] == meta_2["artifact_id"]
        assert len(meta_1["artifact_id"]) == 24
        file_names = {item["filename"] for item in meta_1["files"]}
        assert "result.json" in file_names
        assert "result.txt" in file_names
        assert artifacts_router.records.exists("m1", f"artifacts/{meta_1['artifact_id']}/meta.json")
        assert artifacts_router.records.exists("m1", f"artifacts/{meta_1['artifact_id']}/result.json")
        assert artifacts_router.records.exists("m1", f"artifacts/{meta_1['artifact_id']}/result.txt")
    finally:
        settings.records_dir = records_dir_snapshot


def test_generate_llm_artifact_custom_schema_returns_json_and_txt(monkeypatch, tmp_path, auth_none_settings) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir

    class _DummyOrchestrator:
        def complete_json(self, *, system: str, user: str) -> dict:
            assert "валидный JSON" in system
            assert "Schema guide" in user
            return {"candidate": "Alice", "score": 4}

    try:
        settings.records_dir = str(tmp_path)
        monkeypatch.setattr(
            artifacts_router,
            "_transcript_for_source",
            lambda **kwargs: "INTERVIEWER: ...\nCANDIDATE: ...",
        )
        monkeypatch.setattr(
            artifacts_router,
            "_build_llm_artifact_orchestrator",
            lambda: _DummyOrchestrator(),
        )

        req = artifacts_router.LLMArtifactGenerateRequest(
            transcript_variant="normalized",
            mode="custom",
            prompt="Сделай JSON карточку кандидата",
            schema={"type": "object", "properties": {"candidate": {"type": "string"}}},
        )
        meta, cached = artifacts_router._generate_llm_artifact("m2", req)

        assert cached is False
        assert meta["mode"] == "custom"
        assert meta["transcript_variant"] == "normalized"
        assert meta["result_kind"] == "json"
        file_names = {item["filename"] for item in meta["files"]}
        assert file_names == {"result.json", "result.txt"}
        saved = artifacts_router.records.read_json("m2", f"artifacts/{meta['artifact_id']}/result.json")
        assert saved["candidate"] == "Alice"
    finally:
        settings.records_dir = records_dir_snapshot


def test_llm_artifact_request_accepts_schema_alias() -> None:
    req = artifacts_router.LLMArtifactGenerateRequest(
        mode="custom",
        transcript_variant="clean",
        prompt="x",
        schema={"type": "object", "properties": {"a": {"type": "string"}}},
    )
    assert req.schema_guide == {"type": "object", "properties": {"a": {"type": "string"}}}


def test_generate_llm_artifact_table_falls_back_to_deterministic_builder_without_llm(
    monkeypatch,
    tmp_path,
    auth_none_settings,
) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir
    try:
        settings.records_dir = str(tmp_path)
        monkeypatch.setattr(
            artifacts_router,
            "_transcript_for_source",
            lambda **kwargs: "CANDIDATE: опыт Python и SQL",
        )
        monkeypatch.setattr(artifacts_router, "_build_llm_artifact_orchestrator", lambda: None)
        monkeypatch.setattr(
            artifacts_router,
            "build_structured_rows",
            lambda **kwargs: {
                "status": "ok",
                "columns": ["field", "value"],
                "rows": [{"field": "skills", "value": "Python, SQL"}],
            },
        )
        monkeypatch.setattr(
            artifacts_router,
            "structured_to_csv",
            lambda payload: b"\xef\xbb\xbffield,value\nskills,\"Python, SQL\"\n",
        )

        req = artifacts_router.LLMArtifactGenerateRequest(
            transcript_variant="clean",
            mode="table",
            prompt="Сделай таблицу навыков",
        )
        meta, cached = artifacts_router._generate_llm_artifact("m3", req)

        assert cached is False
        assert meta["result_kind"] == "table"
        file_names = {item["filename"] for item in meta["files"]}
        assert file_names == {"result.json", "result.csv"}
        assert artifacts_router.records.exists("m3", f"artifacts/{meta['artifact_id']}/result.csv")
    finally:
        settings.records_dir = records_dir_snapshot


def test_rag_index_builds_chunks_with_citations_and_caches(monkeypatch, tmp_path, auth_none_settings) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir
    try:
        settings.records_dir = str(tmp_path)
        monkeypatch.setattr(
            artifacts_router,
            "_transcript_for_source",
            lambda **kwargs: "\n".join(
                [
                    "INTERVIEWER: Расскажите про опыт.",
                    "CANDIDATE: Я делал backend на Python и SQL.",
                    "INTERVIEWER: Что с нагрузкой?",
                ]
            ),
        )
        monkeypatch.setattr(
            artifacts_router,
            "_rag_segment_line_metadata",
            lambda meeting_id: [
                {"seq": 1, "speaker": "INTERVIEWER", "start_ms": 0, "end_ms": 4000},
                {"seq": 2, "speaker": "CANDIDATE", "start_ms": 4000, "end_ms": 9000},
                {"seq": 3, "speaker": "INTERVIEWER", "start_ms": 9000, "end_ms": 12000},
            ],
        )
        monkeypatch.setattr(
            artifacts_router,
            "_rag_meeting_meta",
            lambda meeting_id: {
                "display_name": "Запись 1",
                "candidate_name": "Alice",
                "candidate_id": "c-1",
                "vacancy": "Backend Engineer",
                "level": "Senior",
                "interviewer": "Bob",
            },
        )

        payload1, cached1 = artifacts_router._ensure_rag_index(
            "m1",
            source="clean",
            force_rebuild=False,
            max_lines_per_chunk=2,
            overlap_lines=1,
            max_chars_per_chunk=400,
        )
        payload2, cached2 = artifacts_router._ensure_rag_index(
            "m1",
            source="clean",
            force_rebuild=False,
            max_lines_per_chunk=2,
            overlap_lines=1,
            max_chars_per_chunk=400,
        )

        assert cached1 is False
        assert cached2 is True
        assert payload1["chunk_count"] >= 2
        first = payload1["chunks"][0]
        assert first["line_start"] == 1
        assert first["line_end"] == 2
        assert first["start_ms"] == 0
        assert first["end_ms"] == 9000
        assert first["timestamp_start"] == "00:00:00.000"
        assert first["timestamp_end"] == "00:00:09.000"
        assert "INTERVIEWER" in first["speakers"]
        assert "CANDIDATE" in first["speakers"]
        assert first["meeting_meta"]["candidate_name"] == "Alice"
        assert payload1["schema_version"] == "rag_index_v2"
        assert isinstance(payload1.get("vector"), dict)
        assert bool(payload1["vector"].get("enabled")) is True
        assert isinstance(first.get("embedding"), list)
        assert len(first["embedding"]) == int(payload1["vector"].get("dim") or 0)
        assert artifacts_router.records.exists("m1", "artifacts/rag/index_clean.json")
    finally:
        settings.records_dir = records_dir_snapshot


def test_rag_embed_texts_batches_dedupes_and_caches_provider(monkeypatch, auth_none_settings) -> None:
    vector_cfg = {
        "enabled": True,
        "provider": "openai_compat",
        "provider_label": "ollama_openai_compat",
        "model": "nomic-embed-text",
        "openai_api_base": "http://127.0.0.1:11434/v1",
        "openai_api_key": "ollama",
        "openai_timeout_s": 2.0,
        "dim": 2,
        "char_ngrams": True,
    }
    calls: list[list[str]] = []

    def _fake_embed_texts(texts, **kwargs):
        calls.append([str(t) for t in list(texts or [])])
        return [[float(len(str(t))), 1.0] for t in list(texts or [])]

    monkeypatch.setattr(artifacts_router, "_rag_embedding_batch_size", lambda: 2)
    monkeypatch.setattr(artifacts_router, "_rag_embedding_cache_max_items", lambda: 100)
    monkeypatch.setattr(artifacts_router, "_rag_embedding_disk_cache_enabled", lambda: False)
    monkeypatch.setattr(artifacts_router, "embed_texts_openai_compat", _fake_embed_texts)

    with artifacts_router._RAG_EMBEDDING_CACHE_LOCK:
        artifacts_router._RAG_EMBEDDING_CACHE.clear()
    try:
        rows1 = artifacts_router._rag_embed_texts(["alpha", "beta", "alpha", "gamma"], vector_cfg=vector_cfg)
        rows2 = artifacts_router._rag_embed_texts(["gamma", "alpha"], vector_cfg=vector_cfg)
    finally:
        with artifacts_router._RAG_EMBEDDING_CACHE_LOCK:
            artifacts_router._RAG_EMBEDDING_CACHE.clear()

    assert rows1[0] == rows1[2]
    assert rows2[0] == rows1[3]
    assert rows2[1] == rows1[0]
    # Unique texts: alpha, beta, gamma. Batch size=2 -> two provider calls total.
    assert calls == [["alpha", "beta"], ["gamma"]]


def test_rag_embed_texts_uses_disk_cache_after_ram_clear(monkeypatch, tmp_path, auth_none_settings) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir
    vector_cfg = {
        "enabled": True,
        "provider": "openai_compat",
        "provider_label": "ollama_openai_compat",
        "model": "nomic-embed-text",
        "openai_api_base": "http://127.0.0.1:11434/v1",
        "openai_api_key": "ollama",
        "openai_timeout_s": 2.0,
        "dim": 2,
        "char_ngrams": True,
    }
    calls: list[list[str]] = []

    def _fake_embed_texts(texts, **kwargs):
        calls.append([str(t) for t in list(texts or [])])
        return [[0.25, 0.75] for _ in list(texts or [])]

    monkeypatch.setattr(artifacts_router, "embed_texts_openai_compat", _fake_embed_texts)
    monkeypatch.setattr(artifacts_router, "_rag_embedding_cache_max_items", lambda: 100)
    monkeypatch.setattr(artifacts_router, "_rag_embedding_disk_cache_enabled", lambda: True)

    try:
        settings.records_dir = str(tmp_path)
        with artifacts_router._RAG_EMBEDDING_CACHE_LOCK:
            artifacts_router._RAG_EMBEDDING_CACHE.clear()

        rows1 = artifacts_router._rag_embed_texts(["alpha"], vector_cfg=vector_cfg)
        key = artifacts_router._rag_embedding_cache_key("alpha", vector_cfg=vector_cfg)
        cache_path = artifacts_router._rag_embedding_disk_cache_path(key)
        assert cache_path.exists()

        with artifacts_router._RAG_EMBEDDING_CACHE_LOCK:
            artifacts_router._RAG_EMBEDDING_CACHE.clear()

        rows2 = artifacts_router._rag_embed_texts(["alpha"], vector_cfg=vector_cfg)

        assert rows1 == [[0.25, 0.75]]
        assert rows2 == rows1
        assert calls == [["alpha"]]
    finally:
        with artifacts_router._RAG_EMBEDDING_CACHE_LOCK:
            artifacts_router._RAG_EMBEDDING_CACHE.clear()
        settings.records_dir = records_dir_snapshot


def test_ensure_rag_index_uses_batched_embeddings(monkeypatch, tmp_path, auth_none_settings) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir
    batch_calls: list[list[str]] = []
    try:
        settings.records_dir = str(tmp_path)
        monkeypatch.setattr(
            artifacts_router,
            "_transcript_for_source",
            lambda **kwargs: "\n".join(
                [
                    "A: one",
                    "B: two",
                    "A: three",
                    "B: four",
                ]
            ),
        )
        monkeypatch.setattr(artifacts_router, "_rag_segment_line_metadata", lambda meeting_id: [])
        monkeypatch.setattr(artifacts_router, "_rag_meeting_meta", lambda meeting_id: {"display_name": "m1"})
        monkeypatch.setattr(
            artifacts_router,
            "_rag_vector_config",
            lambda: {
                "enabled": True,
                "provider": "hashing_local",
                "provider_label": "hashing_local",
                "model": "hashing_v1_dim2_char",
                "dim": 2,
                "char_ngrams": True,
            },
        )

        def _fake_batch_embed(texts, *, vector_cfg):
            batch_calls.append([str(t) for t in list(texts or [])])
            return [[1.0, 0.0] for _ in list(texts or [])]

        monkeypatch.setattr(artifacts_router, "_rag_embed_texts", _fake_batch_embed)

        payload, cached = artifacts_router._ensure_rag_index(
            "m1",
            source="clean",
            max_lines_per_chunk=2,
            overlap_lines=0,
            max_chars_per_chunk=500,
        )

        assert cached is False
        assert payload["chunk_count"] >= 2
        assert len(batch_calls) == 1
        assert len(batch_calls[0]) == payload["chunk_count"]
        assert all(chunk.get("embedding") == [1.0, 0.0] for chunk in payload["chunks"])
    finally:
        settings.records_dir = records_dir_snapshot


def test_rag_index_status_for_meeting_detects_indexed_missing_outdated(tmp_path, auth_none_settings) -> None:
    settings = get_settings()
    records_dir_snapshot = settings.records_dir
    try:
        settings.records_dir = str(tmp_path)
        records = artifacts_router.records

        records.write_text("m_status", "raw.txt", "RAW transcript text")
        raw_sha = artifacts_router.sha256_hex("RAW transcript text".encode("utf-8"))
        artifacts_router._rag_write_index("m_status", "raw", {"transcript_sha256": raw_sha})

        records.write_text("m_status", "clean.txt", "CLEAN transcript text")
        artifacts_router._rag_write_index("m_status", "clean", {"transcript_sha256": "not_actual_sha"})

        status_map = artifacts_router._rag_index_status_for_meeting("m_status")

        assert status_map["raw"] == "indexed"
        assert status_map["normalized"] == "missing"
        assert status_map["clean"] == "outdated"
    finally:
        settings.records_dir = records_dir_snapshot


def test_rag_rank_hits_supports_vector_score_without_keyword_overlap(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "_rag_vector_config",
        lambda: {
            "enabled": True,
            "provider": "hashing_local",
            "model": "hashing_v1_dim2_char",
            "dim": 2,
            "char_ngrams": True,
        },
    )
    monkeypatch.setattr(artifacts_router, "_rag_hybrid_weights", lambda **kwargs: (0.5, 0.5))
    monkeypatch.setattr(artifacts_router, "_rag_embed_text", lambda text, **kwargs: [1.0, 0.0])

    hits, total_chunks, retrieval_mode = artifacts_router._rag_rank_hits(
        query="python",
        indexes=[
            {
                "chunks": [
                    {
                        "meeting_id": "m1",
                        "chunk_id": "c0001",
                        "text": "completely unrelated token set",
                        "embedding": [1.0, 0.0],
                        "line_start": 1,
                        "line_end": 1,
                        "speakers": ["CANDIDATE"],
                        "meeting_meta": {"candidate_name": "Alice"},
                    }
                ]
            }
        ],
        transcript_variant="clean",
        top_k=5,
    )

    assert total_chunks == 1
    assert retrieval_mode == "hybrid_hash_vector"
    assert len(hits) == 1
    assert hits[0].meeting_id == "m1"
    assert hits[0].keyword_score == 0.0
    assert hits[0].semantic_score > 0.0
    assert hits[0].score > 0.0


def test_rag_rank_hits_keyword_score_respects_query_term_repetition(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(artifacts_router, "_rag_vector_config", lambda: {"enabled": False})

    indexes = [
        {
            "chunks": [
                {
                    "meeting_id": "m1",
                    "chunk_id": "c1",
                    "text": "CANDIDATE: python sql production backend",
                    "line_start": 1,
                    "line_end": 1,
                }
            ]
        }
    ]

    hits1, _, _ = artifacts_router._rag_rank_hits(
        query="backend python sql",
        indexes=indexes,
        transcript_variant="clean",
        top_k=5,
    )
    hits2, _, _ = artifacts_router._rag_rank_hits(
        query="backend python python sql",
        indexes=indexes,
        transcript_variant="clean",
        top_k=5,
    )

    assert hits1 and hits2
    assert hits2[0].keyword_score > hits1[0].keyword_score


def test_rag_rank_hits_prefers_query_order_when_keyword_overlap_is_same(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(artifacts_router, "_rag_vector_config", lambda: {"enabled": False})

    hits, total_chunks, retrieval_mode = artifacts_router._rag_rank_hits(
        query="python sql kafka",
        indexes=[
            {
                "chunks": [
                    {
                        "meeting_id": "m1",
                        "chunk_id": "c_rev",
                        "text": "CANDIDATE: kafka sql python опыт продакшн",
                        "line_start": 1,
                        "line_end": 1,
                    },
                    {
                        "meeting_id": "m2",
                        "chunk_id": "c_ord",
                        "text": "CANDIDATE: python sql kafka опыт продакшн",
                        "line_start": 1,
                        "line_end": 1,
                    },
                ]
            }
        ],
        transcript_variant="clean",
        top_k=5,
    )

    assert total_chunks == 2
    assert retrieval_mode == "keyword_only"
    assert len(hits) == 2
    assert hits[0].chunk_id == "c_ord"
    assert hits[0].keyword_score >= hits[1].keyword_score


def test_rag_query_ranks_across_selected_meetings(monkeypatch, auth_none_settings) -> None:
    index_map = {
        "m1": {
            "chunks": [
                {
                    "meeting_id": "m1",
                    "chunk_id": "c0001",
                    "text": "CANDIDATE: worked with Java and Kafka",
                    "line_start": 1,
                    "line_end": 1,
                    "start_ms": 0,
                    "end_ms": 3000,
                    "timestamp_start": "00:00:00.000",
                    "timestamp_end": "00:00:03.000",
                    "speakers": ["CANDIDATE"],
                    "meeting_meta": {"candidate_name": "Alice", "vacancy": "Backend", "level": "Senior"},
                }
            ]
        },
        "m2": {
            "chunks": [
                {
                    "meeting_id": "m2",
                    "chunk_id": "c0002",
                    "text": "CANDIDATE: strong Python SQL experience in production",
                    "line_start": 4,
                    "line_end": 4,
                    "start_ms": 10000,
                    "end_ms": 15000,
                    "timestamp_start": "00:00:10.000",
                    "timestamp_end": "00:00:15.000",
                    "speakers": ["CANDIDATE"],
                    "meeting_meta": {"candidate_name": "Bob", "vacancy": "Data", "level": "Middle"},
                }
            ]
        },
    }
    monkeypatch.setattr(artifacts_router, "_rag_select_meeting_ids", lambda **kwargs: ["m1", "m2"])
    monkeypatch.setattr(
        artifacts_router,
        "_ensure_rag_index",
        lambda meeting_id, **kwargs: (index_map[meeting_id], True),
    )

    resp = artifacts_router._rag_query(
        artifacts_router.RAGQueryRequest(
            query="python sql",
            transcript_variant="clean",
            meeting_ids=["m1", "m2"],
            top_k=5,
            auto_index=True,
        )
    )

    assert resp.ok is True
    assert resp.indexed_meetings == 2
    assert resp.searched_meetings == 2
    assert resp.total_chunks_scanned == 2
    assert len(resp.hits) >= 1
    assert resp.hits[0].meeting_id == "m2"
    assert resp.hits[0].chunk_id == "c0002"
    assert resp.hits[0].timestamp_start == "00:00:10.000"
    assert resp.hits[0].line_start == 4
    assert resp.hits[0].score > 0
    assert resp.retrieval_mode in {
        "keyword_only",
        "hybrid_hash_vector",
        "hybrid_openai_vector",
        "hybrid_ollama_vector",
    }


def test_rag_index_endpoint_returns_response(monkeypatch, auth_none_settings) -> None:
    payload = {
        "chunk_count": 3,
        "transcript_chars": 123,
        "transcript_sha256": "abc",
        "indexed_at": "2026-02-26T12:00:00Z",
        "chunking": {"max_lines_per_chunk": 6, "overlap_lines": 1, "max_chars_per_chunk": 1200},
        "chunks": [],
    }
    monkeypatch.setattr(
        artifacts_router,
        "_ensure_rag_index",
        lambda meeting_id, **kwargs: (payload, False),
    )

    client = _client()
    resp = client.post("/v1/meetings/m1/rag/index", json={"transcript_variant": "normalized"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["meeting_id"] == "m1"
    assert body["transcript_variant"] == "normalized"
    assert body["chunk_count"] == 3
    assert body["cached"] is False


def test_rag_query_endpoint_returns_hits(monkeypatch, auth_none_settings) -> None:
    monkeypatch.setattr(
        artifacts_router,
        "_rag_query",
        lambda req: artifacts_router.RAGQueryResponse(
            query=req.query,
            transcript_variant=req.transcript_variant,
            searched_meetings=1,
            indexed_meetings=1,
            total_chunks_scanned=2,
            hits=[
                artifacts_router.RAGHit(
                    meeting_id="m1",
                    chunk_id="c1",
                    transcript_variant=req.transcript_variant,
                    score=1.23,
                    keyword_score=1.23,
                    text="CANDIDATE: Python SQL",
                )
            ],
        ),
    )

    client = _client()
    resp = client.post(
        "/v1/rag/query",
        json={"query": "python sql", "transcript_variant": "clean", "meeting_ids": ["m1"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["query"] == "python sql"
    assert body["hits"][0]["chunk_id"] == "c1"


def test_rag_index_job_manager_completes_and_reports_progress(monkeypatch, auth_none_settings) -> None:
    manager = artifacts_router.RAGIndexJobManager(max_jobs=8)

    def _fake_ensure_rag_index(meeting_id, **kwargs):
        time.sleep(0.01)
        return (
            {
                "chunk_count": 3 if meeting_id == "m1" else 2,
                "transcript_chars": 120,
                "indexed_at": "2026-02-26T12:00:00Z",
                "chunks": [],
            },
            False,
        )

    monkeypatch.setattr(artifacts_router, "_ensure_rag_index", _fake_ensure_rag_index)

    started = manager.start(
        artifacts_router.RAGIndexJobRequest(
            meeting_ids=["m1", "m2"],
            transcript_variant="clean",
            force_rebuild=False,
        )
    )
    assert started.job_id.startswith("ragidx-")
    assert started.total_meetings == 2

    deadline = time.time() + 2.0
    latest = started
    while time.time() < deadline:
        status = manager.get_status(job_id=started.job_id)
        assert status is not None
        latest = status
        if latest.status in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert latest.status == "completed"
    assert latest.completed_meetings == 2
    assert latest.ok_meetings == 2
    assert latest.failed_meetings == 0
    assert latest.progress == 1.0
    assert [item.status for item in latest.items] == ["completed", "completed"]


def test_rag_index_jobs_endpoints_start_and_status(monkeypatch, auth_none_settings) -> None:
    class _FakeMgr:
        def start(self, req):
            assert req.meeting_ids == ["m1", "m2"]
            return artifacts_router.RAGIndexJobStatusResponse(
                job_id="ragidx-test",
                status="running",
                transcript_variant=req.transcript_variant,
                total_meetings=2,
                completed_meetings=1,
                ok_meetings=1,
                failed_meetings=0,
                progress=0.5,
                current_meeting_id="m2",
                items=[
                    artifacts_router.RAGIndexJobItem(meeting_id="m1", status="completed", chunk_count=3),
                    artifacts_router.RAGIndexJobItem(meeting_id="m2", status="running"),
                ],
            )

        def get_status(self, job_id=None):
            assert job_id in {None, "ragidx-test"}
            return artifacts_router.RAGIndexJobStatusResponse(
                job_id="ragidx-test",
                status="completed",
                transcript_variant="clean",
                total_meetings=2,
                completed_meetings=2,
                ok_meetings=2,
                failed_meetings=0,
                progress=1.0,
                items=[
                    artifacts_router.RAGIndexJobItem(meeting_id="m1", status="completed", chunk_count=3),
                    artifacts_router.RAGIndexJobItem(meeting_id="m2", status="completed", chunk_count=2),
                ],
            )

    monkeypatch.setattr(artifacts_router, "_rag_index_job_manager", lambda: _FakeMgr())

    client = _client()
    start_resp = client.post(
        "/v1/rag/index-jobs",
        json={"meeting_ids": ["m1", "m2"], "transcript_variant": "clean"},
    )
    assert start_resp.status_code == 200
    start_body = start_resp.json()
    assert start_body["job_id"] == "ragidx-test"
    assert start_body["status"] == "running"
    assert start_body["completed_meetings"] == 1

    status_resp = client.get("/v1/rag/index-jobs/ragidx-test")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == "completed"
    assert status_body["completed_meetings"] == 2
    assert len(status_body["items"]) == 2
