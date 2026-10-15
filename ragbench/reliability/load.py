"""Bounded load / latency measurement for the offline query path.

Measures p50/p95/p99 latency, throughput, and error rate over a fixed number of
queries, optionally with thread concurrency. This exercises the in-process
pipeline (no network); it is a bounded benchmark, not a production load claim.
The reported conditions (corpus size, strategy, provider, concurrency) must
accompany any numbers.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from ragbench.pipeline import Pipeline


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    # Nearest-rank percentile.
    k = max(0, min(len(sorted_vals) - 1, int(round(pct / 100 * len(sorted_vals) + 0.5)) - 1))
    return sorted_vals[k]


def run_load(
    pipeline: Pipeline,
    queries: list[str],
    n: int = 100,
    strategy: str = "hybrid",
    concurrency: int = 1,
) -> dict:
    if not queries:
        raise ValueError("queries must be non-empty")
    # Warm up the in-memory index once up front so concurrent workers do not race
    # on the lazy first build (and so measured latency reflects steady state).
    pipeline._ensure_retriever()
    plan = [queries[i % len(queries)] for i in range(n)]
    latencies: list[float] = []
    errors = 0

    def _one(q: str) -> float:
        start = time.perf_counter()
        try:
            pipeline.query(q, strategy=strategy)
        except Exception:  # noqa: BLE001 - counted as an error, not raised
            return -1.0
        return (time.perf_counter() - start) * 1000

    wall_start = time.perf_counter()
    if concurrency <= 1:
        results = [_one(q) for q in plan]
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(_one, plan))
    wall = time.perf_counter() - wall_start

    for r in results:
        if r < 0:
            errors += 1
        else:
            latencies.append(r)
    latencies.sort()

    return {
        "requests": n,
        "concurrency": concurrency,
        "strategy": strategy,
        "errors": errors,
        "error_rate": round(errors / n, 4),
        "throughput_qps": round(n / wall, 2) if wall > 0 else None,
        "latency_ms": {
            "p50": round(_percentile(latencies, 50), 3),
            "p95": round(_percentile(latencies, 95), 3),
            "p99": round(_percentile(latencies, 99), 3),
            "min": round(latencies[0], 3) if latencies else None,
            "max": round(latencies[-1], 3) if latencies else None,
        },
        "conditions": {
            "documents": pipeline.store.count_documents(),
            "index_version": pipeline.config.index_version,
            "embedding_provider": pipeline.embedder.name,
            "llm_provider": pipeline.generator.name,
        },
    }
