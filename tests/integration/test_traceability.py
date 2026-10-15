"""Phase 5: index-mismatch rejection, deliberate re-index, and the run registry."""

import dataclasses

import pytest

from ragbench.config import Config
from ragbench.pipeline import IndexMismatchError, Pipeline
from ragbench.storage import RunRegistry, SQLiteStore

CORPUS_TEXT = (
    "Reciprocal rank fusion combines ranked lists using 1/(k+rank) contributions "
    "and avoids comparing incommensurable retrieval scores across methods."
)


def _pipeline(config: Config, store: SQLiteStore) -> Pipeline:
    return Pipeline(config=config, store=store)


def test_changed_chunk_config_rejects_until_reindex():
    store = SQLiteStore(":memory:")
    cfg = Config()
    p = _pipeline(cfg, store)
    p.ingest_bytes(CORPUS_TEXT.encode(), "rrf.md", ".md")
    assert not p.query("what is reciprocal rank fusion", strategy="bm25").abstained

    # Change the chunk configuration -> new index_version with no chunks yet.
    cfg2 = dataclasses.replace(cfg, chunk_size=20, chunk_overlap=5)
    p2 = _pipeline(cfg2, store)
    assert p2.index_health()["reindex_required"] is True
    with pytest.raises(IndexMismatchError):
        p2.query("what is reciprocal rank fusion", strategy="bm25")

    # Deliberate re-index rebuilds under the new config, and queries work again.
    summary = p2.reindex()
    assert summary["chunks"] > 0
    assert p2.index_health()["reindex_required"] is False
    assert not p2.query("what is reciprocal rank fusion", strategy="bm25").abstained


def test_reindex_does_not_mix_index_versions():
    store = SQLiteStore(":memory:")
    cfg = Config()
    p = _pipeline(cfg, store)
    p.ingest_bytes(CORPUS_TEXT.encode(), "rrf.md", ".md")
    cfg2 = dataclasses.replace(cfg, chunk_size=20, chunk_overlap=5)
    Pipeline(config=cfg2, store=store).reindex()
    # Only the new active index_version remains in the chunk store.
    assert store.distinct_index_versions() == {cfg2.index_version}


def test_document_text_is_persisted():
    store = SQLiteStore(":memory:")
    p = _pipeline(Config(), store)
    doc = p.ingest_bytes(CORPUS_TEXT.encode(), "rrf.md", ".md")
    stored = store.get_document(doc.id)
    assert stored.text.startswith("Reciprocal rank fusion")


def test_run_registry_records_and_traces():
    reg = RunRegistry(":memory:")
    report = {
        "run_id": "run-123", "timestamp": "2026-10-15T00:00:00+00:00",
        "git_commit": "abc1234", "dataset_version": "v1",
        "config": {"index_version": "fake:x:d256:c120:o24"},
        "baselines": [{"name": "B0_bm25", "aggregate": {"recall@5": 1.0}}],
    }
    reg.record(report, report_path="evaluation/reports/x.json")
    runs = reg.list_runs()
    assert runs[0]["run_id"] == "run-123"
    full = reg.get_run("run-123")
    assert full["config"]["index_version"] == "fake:x:d256:c120:o24"
    assert full["metrics"]["B0_bm25"]["recall@5"] == 1.0
