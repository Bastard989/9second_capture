from __future__ import annotations

from datetime import datetime

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
