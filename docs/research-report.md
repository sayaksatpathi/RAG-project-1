# RAGBench — Research Report

**Author:** Sayak Satpathi · **Version:** 0.13.0 · **Report date:** 2026-10-27

This is the consolidated capstone report for RAGBench. Every number here is a
**measured** result reproduced from the project's own harness; nothing is
estimated. The headline experiment returns a **neutral result**, reported
exactly as found. Working notes live in [research.md](research.md) and the full
per-run tables in [benchmark-results.md](benchmark-results.md).

---

## 1. Abstract

RAGBench is an offline-first Retrieval-Augmented Generation platform and
evaluation harness. It ingests a documented corpus, retrieves evidence,
generates grounded answers with inspectable citations, and abstains when
evidence is insufficient. On top of that core it runs a fair, reproducible
comparison of five retrieval strategies and gates candidate configurations
against a known-good baseline.

The research question is whether **query-aware adaptive retrieval routing** beats
strong fixed baselines. On the project's corpus, under a deterministic
embedding, it **does not: adaptive ties the strongest fixed baseline exactly**
(delta +0.000 on every retrieval metric). The report explains why this is the
*expected and honest* outcome for this setup, and what would have to change to
give the hypothesis a fair chance of winning.

## 2. Research question and hypotheses

> Can query-aware retrieval routing improve the quality–latency–cost trade-off of
> RAG compared with strong fixed retrieval baselines while maintaining acceptable
> evidence support and answer correctness?

- **H1** — Adaptive retrieval improves ≥1 pre-declared retrieval/answer-quality
  metric versus the strongest fixed baseline.
- **H3** — Reranking improves ranking for some cases but may not be worth its
  cost for all query classes.
- **H4** — Evidence checks and abstention reduce unsupported answers on
  unanswerable questions, with a measurable precision/recall trade-off.

The "strongest fixed" baseline is chosen by `mrr@k` over B0–B3 **before**
inspecting the adaptive result, so H1 cannot be won by post-hoc selection.

## 3. Method

- **Corpus:** 14 synthetic, self-contained documents on IR/RAG topics, written
  for this project (provenance in `evaluation/datasets/`).
- **Dataset:** `benchmark_v1.json`, version **v1.1** — **100 manually authored
  cases** across 8 query categories with document-level relevance,
  answerability, and expected-abstention labels. Multi-passage cases carry
  **graded** relevance (primary doc grade 3, supporting grade 1), so nDCG is
  graded rather than binary. Synthetic and clearly labeled.
- **Baselines (one shared harness):**
  - **B0** BM25 (hand-written sparse lexical).
  - **B1** dense (brute-force cosine over embeddings).
  - **B2** hybrid — Reciprocal Rank Fusion (fuses *ranks*, never incommensurable
    raw scores).
  - **B3** hybrid + heuristic reranker (a deterministic stand-in, **not** a
    trained cross-encoder).
  - **B4** adaptive — an interpretable rule router with a hybrid fallback.
- **Router rules (ordered, hand-specified, not learned):** exact-identifier →
  BM25; rare corpus term → BM25; long paraphrase question → dense; else hybrid.
- **Metrics:** Recall@5, MRR@5, nDCG@5 (graded), Hit@5, plus abstention
  precision/recall. Document-relevance granularity.
- **Default stack (decisive caveat):** a **deterministic "fake" embedding** (a
  256-dim lexical hash, *not* a semantic model) and a **mock generation
  provider**. These exist so the dense path, tests, and retrieval-only
  evaluation run reproducibly offline. Real `sentence-transformers` and an
  OpenAI-compatible provider are optional, config-gated, and were not available
  in this environment.

## 4. Results (measured)

Reproduced run `5f421bd6-62e9-4d9a-a358-00c33d664896` · git `62244a6` ·
dataset v1.1 · 100 cases · k=5 · index `fake:all-MiniLM-L6-v2:d256:c120:o24`.
Identical to the previously recorded v1.1 run `879ec810` — the result is stable.

| Baseline | recall@5 | mrr@5 | ndcg@5 | hit@5 | abstain P | abstain R |
|---|---|---|---|---|---|---|
| B0 BM25 | **0.986** | **0.955** | **0.953** | **1.000** | 0.944 | 0.548 |
| B1 dense | 0.920 | 0.843 | 0.843 | 0.957 | 0.938 | 0.484 |
| B2 hybrid (RRF) | 0.971 | 0.931 | 0.926 | 0.986 | 0.941 | 0.516 |
| B3 hybrid + rerank | 0.964 | 0.949 | 0.938 | 0.986 | 0.933 | 0.452 |
| **B4 adaptive** | **0.986** | **0.955** | **0.953** | **1.000** | 0.944 | 0.548 |

- **Routing distribution:** BM25 = 91, hybrid = 8, dense = 1. **Fallback rate 0.08.**
- **Adaptive vs strongest fixed (B0 BM25, chosen by mrr@5): +0.000 on every
  metric.**

## 5. Findings

- **H1 — not supported (clean neutral).** Adaptive routing *tied* the strongest
  fixed baseline exactly. The interpretable router recognizes that lexical
  signals dominate this corpus and sends 91/100 queries to BM25, thereby
  reproducing BM25 rather than beating it. This is reported as-is, not hidden or
  reframed as a win.
- **H3 — supported, negative for reranking here.** B3's mrr@5/ndcg@5 sit *below*
  B0's: the heuristic reranker reorders an already-strong candidate set without a
  true relevance model, and slightly hurts. A real negative result.
- **H4 — partially supported.** Abstention precision is high (0.944: it rarely
  abstains on answerable questions) but recall is ~0.55: it misses many it should
  decline, concentrated in `misleading_overlap` cases whose corpus content words
  clear the lexical-grounding guard and the uncalibrated 0.15 threshold. A
  genuine precision/recall trade-off, swept in `docs/quality-gate.md`.

## 6. Ablations (measured)

- **Remove routing** (adaptive → fixed hybrid B2): mrr@5 0.955 → 0.931. Routing
  recovers BM25-level MRR by sending lexical queries to BM25; removing it costs
  MRR on this corpus.
- **Remove reranking** (B3 → B2): ndcg@5 0.938 vs 0.926, mrr@5 0.949 vs 0.931 —
  the reranker's effect is small and, on recall/nDCG versus B0, slightly
  negative. Not worth its cost here.
- **Evidence/abstention threshold sweep:** precision stays high up to ~0.15, then
  falls as the threshold rises and recall climbs (see `quality-gate.md`).

## 7. Reliability and performance (Phase 11, measured)

- **Controlled failure experiments — 5/5 PASS:** slow provider (answer still
  returned), failing provider (graceful degraded message + warning), corrupt/
  unsupported upload (rejected, no partial index), database unavailable (fails
  loudly, recovers on reconnect), incompatible index config (rejected until
  re-index, then recovers).
- **Bounded load** (14-doc corpus, fake embedding, mock LLM, single thread,
  in-process): ≈ **1343 qps**, **0 errors**, latency p50/p95/p99 =
  **0.71 / 0.90 / 1.34 ms**.

These figures describe the deterministic offline stack only. With a real
embedding model and a hosted LLM, end-to-end latency would be dominated by
embedding + generation and is **not** represented here — do not read these as
production performance numbers.

## 8. Threats to validity

1. **The embedding is a non-semantic hash.** This is the dominant limitation:
   dense and routing results do not generalize to a real embedding model, and
   there is little headroom for a router to exploit when dense retrieval is
   artificially weak.
2. **Synthetic, small dataset (100 cases).** Confidence intervals and paired
   significance tests are not yet computed; no single composite score is
   reported.
3. **Document-granularity relevance.** One chunk per document in this corpus, so
   passage-level ranking nuance is limited.
4. **Deployment pieces unverified here.** Docker/Compose, Kubernetes/Helm, and
   Terraform are authored and statically validated but were not run (no runtime
   or cloud credentials); they are labeled NOT VERIFIED in
   `IMPLEMENTATION_STATUS.md`.

## 9. Reproducibility

```bash
python -m pip install -e ".[dev]"
python -m ragbench.cli evaluate --dataset evaluation/datasets/benchmark_v1.json --k 5
python -m ragbench.cli runs        # the run registry (run_id, git commit, config, metrics)
```

Every run records run_id, git commit, dataset version, index version, config,
and metrics (see `docs/traceability.md`). Headline runs: `bf643c87` (v1
baselines), `e25e904b` (v1 adaptive), `879ec810` (v1.1), and `5f421bd6` (v1.1,
reproduced for this report). The neutral H1 result holds across every run and
both dataset versions.

## 10. Conclusions and future work

RAGBench meets its stated success criterion: it runs a **fair, reproducible
experiment and reports the result honestly, even though the adaptive method did
not win.** The engineering around the experiment — citation validation,
evidence-based abstention, an AI quality gate that blocks regressions, full
run traceability, observability, reliability experiments, and a hardened API — is
the substance of the contribution.

To give adaptive routing a fair chance of beating fixed baselines:

1. Configure a **real embedding provider** and re-run the identical harness,
   where dense retrieval can win on paraphrase/semantic queries.
2. Expand the dataset and add **paired significance testing** and confidence
   intervals.
3. **Calibrate the abstention threshold** on a held-out split and report the
   precision/recall operating point, rather than using the current fixed 0.15.

The harness, router, and gate are already in place to run that comparison
unchanged the moment a real embedder is available.
