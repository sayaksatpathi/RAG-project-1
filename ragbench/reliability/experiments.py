"""Controlled, repeatable failure experiments.

Each scenario injects a specific fault, records the expected behavior, the
observed result, whether they matched, and (where applicable) the recovery
action and measured recovery time. Experiments are offline and deterministic;
none touches external infrastructure.
"""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field

from ragbench.config import Config
from ragbench.ingestion.parsing import ParseError
from ragbench.pipeline import IndexMismatchError, Pipeline
from ragbench.reliability.faults import FailingProvider, SlowProvider
from ragbench.storage import SQLiteStore

_CORPUS = {
    "rrf.md": "Reciprocal rank fusion combines ranked lists using 1/(k+rank) "
    "contributions and avoids comparing incommensurable retrieval scores.",
    "bm25.md": "BM25 is a sparse lexical ranking function with parameters k1 and b.",
}


@dataclass
class ScenarioResult:
    scenario: str
    expected: str
    observed: str
    passed: bool
    recovery: str = ""
    recovery_ms: float | None = None
    evidence: dict = field(default_factory=dict)


def _fresh_pipeline(config: Config | None = None) -> Pipeline:
    cfg = config or Config()
    p = Pipeline(config=cfg, store=SQLiteStore(":memory:"))
    for name, text in _CORPUS.items():
        p.ingest_bytes(text.encode(), name, ".md")
    return p


def _slow_provider_scenario() -> ScenarioResult:
    p = _fresh_pipeline()
    p.generator = SlowProvider(delay_s=0.05)
    start = time.perf_counter()
    ans = p.query("what is reciprocal rank fusion", strategy="bm25")
    latency_ms = (time.perf_counter() - start) * 1000
    ok = (not ans.abstained) and latency_ms >= 50
    return ScenarioResult(
        "slow_generation_provider",
        "answer still returned; latency reflects the provider delay",
        f"returned={not ans.abstained}, latency_ms={latency_ms:.1f}",
        ok, recovery="bounded delay; no retry storm",
        evidence={"latency_ms": round(latency_ms, 1)},
    )


def _failing_provider_scenario() -> ScenarioResult:
    p = _fresh_pipeline()
    p.generator = FailingProvider()
    ans = p.query("what is reciprocal rank fusion", strategy="bm25")
    ok = (not any(c.valid for c in ans.citations)) and any(
        "generation_provider_error" in w for w in ans.warnings
    )
    return ScenarioResult(
        "failing_generation_provider",
        "graceful degradation: safe message + warning, no exception",
        f"warnings={ans.warnings}",
        ok, recovery="retry after provider recovers",
    )


def _corrupt_upload_scenario() -> ScenarioResult:
    p = _fresh_pipeline()
    observed = "no error raised"
    passed = False
    try:
        p.ingest_bytes(b"\x00\x01\x02 not utf8 \xff\xfe", "bad.txt", ".txt")
    except ParseError as exc:
        observed = f"ParseError: {exc}"
        passed = True
    except Exception as exc:  # noqa: BLE001
        observed = f"unexpected {type(exc).__name__}: {exc}"
    return ScenarioResult(
        "corrupt_or_unsupported_upload",
        "rejected with a ParseError; no crash, no partial index",
        observed, passed, recovery="reject upload; ask for a valid document",
    )


def _db_unavailable_scenario() -> ScenarioResult:
    p = _fresh_pipeline()
    p.store.conn.close()  # simulate the database becoming unavailable
    observed = "no error"
    failed_as_expected = False
    try:
        p.store.count_documents()
    except Exception as exc:  # noqa: BLE001
        observed = f"raised {type(exc).__name__}"
        failed_as_expected = True
    # Recovery: reconnect a fresh store and confirm readiness.
    start = time.perf_counter()
    p.store = SQLiteStore(":memory:")
    recovered = isinstance(p.store.count_documents(), int)
    recovery_ms = (time.perf_counter() - start) * 1000
    return ScenarioResult(
        "database_unavailable",
        "operations fail loudly; readiness recovers after reconnect",
        f"{observed}; recovered={recovered}",
        failed_as_expected and recovered,
        recovery="reconnect store", recovery_ms=round(recovery_ms, 1),
    )


def _index_mismatch_scenario() -> ScenarioResult:
    store = SQLiteStore(":memory:")
    cfg = Config()
    p = _fresh_pipeline(cfg)
    # reuse same store by re-ingesting into a shared store:
    store = p.store
    cfg2 = dataclasses.replace(cfg, chunk_size=20, chunk_overlap=5)
    p2 = Pipeline(config=cfg2, store=store)
    rejected = False
    try:
        p2.query("what is bm25", strategy="bm25")
    except IndexMismatchError:
        rejected = True
    start = time.perf_counter()
    p2.reindex()
    recovered = not p2.query("what is bm25", strategy="bm25").abstained
    recovery_ms = (time.perf_counter() - start) * 1000
    return ScenarioResult(
        "incompatible_index_config",
        "queries rejected until deliberate re-index, then recover",
        f"rejected={rejected}, recovered={recovered}",
        rejected and recovered,
        recovery="ragbench reindex", recovery_ms=round(recovery_ms, 1),
    )


def run_failure_experiments() -> list[ScenarioResult]:
    return [
        _slow_provider_scenario(),
        _failing_provider_scenario(),
        _corrupt_upload_scenario(),
        _db_unavailable_scenario(),
        _index_mismatch_scenario(),
    ]
