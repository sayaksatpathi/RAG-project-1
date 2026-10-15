# Benchmark Results

**Actual measured results only.** Reproduce with:

```bash
python -m ragbench.cli evaluate --dataset evaluation/datasets/benchmark_v1.json --k 5
```

Reports (JSON + Markdown) are written to `evaluation/reports/` and are git-ignored
as run artifacts; the summary below is transcribed from a real run.

## Run (recorded 2026-10-15)

- run_id: `bf643c87-d493-4263-83a1-78fc33016023`
- git_commit: `7bc5f30`
- dataset_version: `v1` (50 synthetic cases, 14-doc corpus), k = 5
- index_version: `fake:all-MiniLM-L6-v2:d256:c120:o24`
- embedding_provider: `fake:all-MiniLM-L6-v2:d256` (deterministic, non-semantic)
- reranker: `heuristic-rerank` (deterministic stand-in, NOT a trained cross-encoder)

### Aggregate (cases with relevance labels)

| Baseline | recall@5 | mrr@5 | ndcg@5 | hit@5 | abstain P | abstain R |
|---|---|---|---|---|---|---|
| B0 BM25 | 1.000 | 0.981 | 0.979 | 1.000 | 1.000 | 0.533 |
| B1 dense | 0.929 | 0.901 | 0.885 | 0.971 | 1.000 | 0.467 |
| B2 hybrid (RRF) | 1.000 | 0.960 | 0.960 | 1.000 | 1.000 | 0.467 |
| B3 hybrid + rerank | 0.986 | 0.964 | 0.958 | 1.000 | 1.000 | 0.400 |

## Honest interpretation (and limitations)

These numbers describe **this corpus + dataset under the deterministic fake
embedding**, and must not be read as general claims about BM25 vs dense
retrieval.

1. **BM25 is strongest here.** The dataset questions share substantial lexical
   content with their target documents, and the default embedding is a hash, not
   a semantic model — so sparse retrieval wins. B1 (dense) is the weakest. This
   is expected given the stand-in embedder and is exactly why a real embedding
   provider is needed before drawing retrieval-quality conclusions.
2. **Reranking did not help — and slightly hurt.** B3's mrr@5/ndcg@5 are below
   B0's. A negative result: the heuristic reranker reorders an already-good
   candidate set without a true relevance model. This is reported, not hidden.
3. **Abstention: perfect precision, weak recall.** The system never abstained on
   an answerable question (precision 1.0) but missed many it should have declined
   (recall 0.40–0.53). The misses are dominated by the *misleading_overlap* and
   some *ambiguous* cases, which contain corpus content words and so pass the
   lexical-grounding guard and clear the (uncalibrated) 0.15 threshold.
   Calibrating this threshold on a validation split and reporting the
   precision/recall trade-off is Phase 4 work.

## Per-category abstention (B2 hybrid, same run)

The report's `by_category.<category>.abstain_accuracy` field records, per
category, the fraction of cases where the abstain decision matched the label.
Clearly out-of-corpus categories (`unanswerable`) abstain well; `direct_fact`
answers well; `misleading_overlap` is the known weak spot. See the JSON report
for exact per-category figures for every baseline.

## Phase 3 run — adaptive routing (recorded 2026-10-15)

- run_id: `e25e904b-87c9-40e1-9dfb-d3e7b5fb53d8`, git_commit `a14cc13`, same dataset/config.

| Baseline | recall@5 | mrr@5 | ndcg@5 | hit@5 | abstain P | abstain R |
|---|---|---|---|---|---|---|
| B0 BM25 | 1.000 | 0.981 | 0.979 | 1.000 | 1.000 | 0.533 |
| B1 dense | 0.929 | 0.901 | 0.885 | 0.971 | 1.000 | 0.467 |
| B2 hybrid | 1.000 | 0.960 | 0.960 | 1.000 | 1.000 | 0.467 |
| B3 hybrid+rerank | 0.986 | 0.964 | 0.958 | 1.000 | 1.000 | 0.400 |
| **B4 adaptive** | 1.000 | 0.981 | 0.979 | 1.000 | 1.000 | 0.533 |

- **Routing distribution:** bm25 = 45, hybrid = 4, dense = 1. **Fallback rate: 0.08.**
- **Ablation — adaptive vs strongest fixed (B0 BM25, chosen by mrr@5):** delta
  **+0.000 on every metric**. Removing routing is equivalent to B2 hybrid;
  removing reranking is B3 vs B2 (B3 is slightly worse).

### Finding (H1 for this setup)

**Adaptive routing did NOT improve over the strongest fixed baseline — it tied
it.** The interpretable router correctly recognizes that lexical signals
dominate on this corpus (45/50 queries → BM25) and therefore reproduces BM25's
results. This is a clean neutral result, reported as-is. The caveat is central:
the deterministic fake embedding makes dense retrieval weak, so there is little
headroom for a router to exploit. The experiment would need a real embedding
model (where dense wins on paraphrase/semantic queries) before routing could
plausibly beat every fixed baseline. The harness and router are in place to
re-run that comparison unchanged once a real embedder is configured.

## v1.1 run — 100 cases, graded nDCG (measured 2026-10-15)

Dataset expanded to **100 cases** (`dataset_version: v1.1`) with optional graded
relevance (primary doc grade 3, supporting grade 1) on multi-passage cases, so
nDCG is now graded rather than binary. run_id `879ec810`, git_commit `0e3b130`.

| Baseline | recall@5 | mrr@5 | ndcg@5 | hit@5 | abstain P | abstain R |
|---|---|---|---|---|---|---|
| B0 BM25 | 0.986 | 0.955 | 0.953 | 1.000 | 0.944 | 0.548 |
| B1 dense | 0.920 | 0.843 | 0.843 | 0.957 | 0.938 | 0.484 |
| B2 hybrid | 0.971 | 0.931 | 0.926 | 0.986 | 0.941 | 0.516 |
| B3 hybrid+rerank | 0.964 | 0.949 | 0.938 | 0.986 | 0.933 | 0.452 |
| **B4 adaptive** | 0.986 | 0.955 | 0.953 | 1.000 | 0.944 | 0.548 |

- Routing: bm25=91, hybrid=8, dense=1; fallback rate 0.08.
- Adaptive vs strongest fixed (B0): **+0.000 on all metrics** — the v1 neutral
  H1 result holds at 100 cases.
- The story is unchanged from v1: BM25 strongest, dense weakest, rerank slightly
  negative on recall/ndcg. nDCG now reflects graded relevance (it sits at or
  below recall because the graded multi-passage cases penalize putting a
  supporting doc above the primary one).
- Abstention precision is now 0.944 (a few answerable questions abstain with the
  larger set) — still above the gate's 0.90 floor; recall ~0.55.

## Reliability & load (Phase 11, measured 2026-10-15)

**Failure experiments** (`ragbench failure-demo`) — all 5 scenarios PASS:

| Scenario | Expected behavior | Result |
|---|---|---|
| slow_generation_provider | answer still returned; latency reflects delay | PASS |
| failing_generation_provider | graceful degradation (safe msg + warning) | PASS |
| corrupt_or_unsupported_upload | rejected with ParseError, no partial index | PASS |
| database_unavailable | fails loudly; recovers after reconnect | PASS |
| incompatible_index_config | rejected until re-index, then recovers | PASS |

**Bounded load** (`ragbench loadtest --n 200 --strategy hybrid`):

- conditions: 14-doc corpus, fake embedding (d256), mock LLM, **single thread**,
  in-process (no network).
- throughput ≈ **1343 qps**, **0 errors**.
- latency p50/p95/p99 = **0.71 / 0.90 / 1.34 ms**.

These numbers are for the offline deterministic stack only. With a real
embedding model and a hosted LLM, end-to-end latency would be dominated by
embedding + generation and is NOT represented here. Do not cite these as
production performance.

## Not yet measured (PENDING)

- Answer correctness / faithfulness against reference answers (needs a judge).
- Latency/cost percentiles under declared load (Phase 11).
- Results with a real embedding model and real generation provider.
