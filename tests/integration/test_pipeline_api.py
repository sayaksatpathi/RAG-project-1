"""End-to-end integration tests using in-memory SQLite and offline providers."""

import pytest
from fastapi.testclient import TestClient

from ragbench.api.app import create_app
from ragbench.config import Config
from ragbench.pipeline import Pipeline
from ragbench.storage import SQLiteStore

CORPUS = {
    "rrf.md": "Reciprocal Rank Fusion combines ranked lists using 1/(k+rank) "
    "contributions and avoids comparing incommensurable scores.",
    "bm25.md": "BM25 is a sparse lexical ranking function with parameters k1 and b "
    "that is strong for exact identifiers and rare terms.",
}


@pytest.fixture
def pipeline():
    store = SQLiteStore(":memory:")
    p = Pipeline(config=Config(), store=store)
    for name, text in CORPUS.items():
        p.ingest_bytes(text.encode("utf-8"), name, ".md")
    return p


def test_ingest_index_and_grounded_query(pipeline):
    ans = pipeline.query("What is reciprocal rank fusion?", strategy="hybrid")
    assert not ans.abstained
    assert ans.retrieved_passage_ids
    assert all(c.valid for c in ans.citations)  # citations map to retrieved passages


def test_duplicate_ingest_is_idempotent(pipeline):
    before = pipeline.store.count_documents()
    pipeline.ingest_bytes(CORPUS["rrf.md"].encode("utf-8"), "rrf.md", ".md")
    assert pipeline.store.count_documents() == before


def test_abstains_on_unanswerable(pipeline):
    ans = pipeline.query("What is the capital of the moon's underground economy?",
                         strategy="bm25")
    assert ans.abstained
    assert ans.citations == []


def test_delete_document_removes_it(pipeline):
    doc = pipeline.store.list_documents()[0]
    assert pipeline.delete_document(doc.id)
    assert pipeline.store.get_document(doc.id) is None


def test_api_health_and_query():
    store = SQLiteStore(":memory:")
    p = Pipeline(config=Config(), store=store)
    p.ingest_bytes(CORPUS["bm25.md"].encode("utf-8"), "bm25.md", ".md")
    client = TestClient(create_app(pipeline=p))

    assert client.get("/health/live").json()["status"] == "live"
    assert client.get("/health/ready").json()["status"] == "ready"

    r = client.post("/api/v1/query", json={"query": "what is bm25", "strategy": "bm25"})
    assert r.status_code == 200
    body = r.json()
    assert "request_id" in body and body["index_version"]


def test_api_upload_requires_token():
    store = SQLiteStore(":memory:")
    client = TestClient(create_app(pipeline=Pipeline(config=Config(), store=store)))
    files = {"file": ("x.txt", b"hello world content here", "text/plain")}
    assert client.post("/api/v1/documents", files=files).status_code == 401
    ok = client.post("/api/v1/documents", files=files,
                     headers={"Authorization": "Bearer dev-local-token"})
    assert ok.status_code == 200


def test_api_404_on_missing_document():
    store = SQLiteStore(":memory:")
    client = TestClient(create_app(pipeline=Pipeline(config=Config(), store=store)))
    assert client.get("/api/v1/documents/nope").status_code == 404
