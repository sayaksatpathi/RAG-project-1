# Research

## Question

> Can query-aware retrieval routing improve the quality–latency–cost trade-off
> of RAG compared with strong fixed retrieval baselines while maintaining
> acceptable evidence support and answer correctness?

Treated as a hypothesis, not a foregone conclusion. The project is successful if
it runs a fair, reproducible experiment — even if the adaptive method does not
win.

## Hypotheses

- **H1** — Adaptive retrieval improves ≥1 predeclared retrieval/answer-quality
  metric vs the strongest fixed baseline on the selected corpus.
- **H3** — Reranking improves ranking for some cases but its latency may not be
  worth it for all query classes.
- **H4** — Evidence checks and abstention reduce unsupported answers on
  unanswerable questions, with a measurable precision/recall trade-off.

Acceptance rules are per-metric improvements over the strongest fixed baseline,
declared before inspecting the held-out result (the "strongest fixed" baseline
is chosen by mrr@k over B0–B3, independent of the adaptive result).

## Method

- **Corpus:** 14 synthetic, self-contained documents on IR/RAG topics.
- **Dataset:** 50 manually-authored cases across 8 query categories with
  document-level relevance, answerability, and expected-abstention labels
  (`evaluation/datasets/benchmark_v1.json`). Provenance in the file; synthetic
  and clearly labeled.
- **Baselines:** B0 BM25, B1 dense, B2 hybrid (RRF), B3 hybrid+heuristic-rerank,
  B4 adaptive (interpretable router with hybrid fallback). All run through one
  harness; metrics Recall/MRR/nDCG/Hit@5 plus abstention precision/recall.
- **Router:** ordered interpretable rules (exact-identifier → bm25; rare corpus
  term → bm25; long paraphrase question → dense; else hybrid). It is a
  hand-specified heuristic, **not** a trained model.

## Findings (measured; see docs/benchmark-results.md for run IDs)

- **H1: not supported on this setup (neutral).** Adaptive tied the strongest
  fixed baseline (BM25) exactly (delta +0.000 on all metrics), routing 45/50
  queries to BM25. On this corpus, lexical retrieval dominates and the router
  correctly reproduces it rather than improving on it.
- **H3: supported (negative for rerank here).** The heuristic reranker (B3)
  slightly *reduced* mrr@5/ndcg@5 vs BM25 — reranking was not worth it here.
- **H4: partially supported.** Abstention precision is perfect (1.000: never
  abstains on an answerable question) but recall is low (0.40–0.53): the system
  fails to abstain on misleading-lexical-overlap questions. A real trade-off,
  pending threshold calibration (Phase 4).

## Threats to validity

- The default embedding is a non-semantic hash; dense/routing results do not
  generalize to a real embedding model. This is the dominant limitation.
- The dataset is synthetic and small (50 cases); confidence intervals and paired
  tests are not yet computed. No composite score is reported.
- Relevance is binary at document granularity (one chunk per doc here).

## Ablations (measured)

- **Remove routing** (adaptive → fixed hybrid B2): recall@5 1.000→1.000,
  mrr@5 0.981→0.960. Routing recovers BM25-level mrr by sending lexical queries
  to BM25; removing it costs mrr on this corpus.
- **Remove reranking** (B3 → B2): mrr@5 0.964→0.960, ndcg@5 0.958→0.960 — the
  reranker's effect is within noise and slightly negative on ndcg.
- **Evidence/abstention** (threshold sweep): see docs/quality-gate.md — precision
  stays 1.0 up to threshold 0.15, then falls; recall rises with the threshold.

## Reproducibility

```bash
python -m ragbench.cli evaluate   # writes a report to evaluation/reports/ and
                                  # registers the run (ragbench runs)
```

Every run records run_id, git commit, dataset version, index version, config,
and metrics (see docs/traceability.md). The headline runs referenced here are
`bf643c87` (baselines, v1/50 cases), `e25e904b` (adaptive, v1), and `879ec810`
(v1.1/100 cases with graded nDCG). The neutral H1 result (adaptive ties the
strongest fixed baseline) holds on both dataset versions.

## Further work

Configure a real embedding provider and re-run the identical harness; expand the
dataset toward ~100 with graded relevance; calibrate abstention on a held-out
split; add paired significance testing. See `NEXT_STEPS.md`.
