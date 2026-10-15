from fastapi.testclient import TestClient

from ragbench.api.app import create_app
from ragbench.config import Config
from ragbench.pipeline import Pipeline
from ragbench.storage import SQLiteStore


def _client():
    store = SQLiteStore(":memory:")
    p = Pipeline(config=Config(), store=store)
    p.ingest_bytes(b"BM25 is a sparse lexical ranking function.", "bm25.md", ".md")
    return TestClient(create_app(pipeline=p))


def test_metrics_endpoint_exposes_prometheus_text():
    client = _client()
    # Generate some traffic first.
    client.post("/api/v1/query", json={"query": "what is bm25", "strategy": "bm25"})
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "ragbench_requests_total" in body
    assert "ragbench_retrieval_strategy_total" in body
    assert "ragbench_indexed_documents" in body


def test_request_id_header_present():
    client = _client()
    r = client.get("/health/live")
    assert r.headers.get("X-Request-ID")
