"""Phase 11: graceful degradation, failure experiments, and load measurement."""

from ragbench.config import Config
from ragbench.pipeline import Pipeline
from ragbench.reliability import run_failure_experiments, run_load
from ragbench.reliability.faults import FailingProvider, SlowProvider
from ragbench.storage import SQLiteStore


def _pipeline():
    p = Pipeline(config=Config(), store=SQLiteStore(":memory:"))
    p.ingest_bytes(b"BM25 is a sparse lexical ranking function with parameters k1 and b.",
                   "bm25.md", ".md")
    p.ingest_bytes(b"Reciprocal rank fusion combines ranked lists using rank reciprocals.",
                   "rrf.md", ".md")
    return p


def test_failing_provider_degrades_gracefully():
    p = _pipeline()
    p.generator = FailingProvider()
    ans = p.query("what is bm25", strategy="bm25")
    assert ans.citations == []
    assert any("generation_provider_error" in w for w in ans.warnings)


def test_slow_provider_still_answers():
    p = _pipeline()
    p.generator = SlowProvider(delay_s=0.02)
    ans = p.query("what is bm25", strategy="bm25")
    assert not ans.abstained


def test_failure_experiments_all_pass():
    results = run_failure_experiments()
    names = {r.scenario for r in results}
    assert "failing_generation_provider" in names
    assert "database_unavailable" in names
    for r in results:
        assert r.passed, f"{r.scenario}: {r.observed}"


def test_load_harness_reports_percentiles():
    p = _pipeline()
    out = run_load(p, ["what is bm25", "what is reciprocal rank fusion"], n=30)
    assert out["requests"] == 30
    assert out["errors"] == 0
    lat = out["latency_ms"]
    assert lat["p50"] <= lat["p95"] <= lat["p99"]
    assert out["throughput_qps"] is not None


def test_load_harness_concurrency():
    p = _pipeline()
    out = run_load(p, ["what is bm25"], n=20, concurrency=4)
    assert out["concurrency"] == 4
    assert out["errors"] == 0
