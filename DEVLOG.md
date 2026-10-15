# Development Log

## 2026-10-15 — Phase 0 (audit & bootstrap) + Phase 1 (vertical slice)

**Audit (commands run):**
- `python --version` → 3.12.10
- package probe → fastapi/pydantic/numpy/pandas/sklearn/pytest/httpx/uvicorn present; ruff/rank_bm25/sentence-transformers missing
- `docker --version` → not found; `psql`/`kubectl` → not found; `terraform --version` → 1.16.4
- `git init` → new repo; `pip install ruff` → 0.17.0

**Decisions:** offline-first stack (SQLite, hand-written BM25, fake embeddings,
mock LLM). See DECISIONS.md.

**Built (this session):** project scaffold, config, storage (SQLite), ingestion
(TXT/MD/PDF-text), chunking, BM25 + dense + hybrid retrieval, mock generation
with citation validation and abstention, CLI, FastAPI app, sample corpus, unit
tests.

**Validation (actually run):**
- `python -m pytest` → **24 passed** (unit: chunking, retrieval/BM25/dense/RRF,
  citations; integration: ingest→index→query, idempotent re-ingest, abstention,
  delete, API health/query/auth/404).
- `python -m ruff check .` → **All checks passed**.
- E2E CLI: ingested 4-doc sample corpus; hybrid query "What is reciprocal rank
  fusion?" returned a grounded answer with the RRF doc ranked first and two
  citations that passed identifier validation (`valid: true`).
- Abstention verified both ways: out-of-corpus query ("sourdough bread at high
  altitude") → `abstained: true`; in-corpus RRF query → `abstained: false`.

**Fixes during the session:**
- Abstention originally compared a fixed threshold against RRF fusion scores
  (incommensurable scales) → replaced with a strategy-independent embedding
  evidence score.
- Fake-embedding spurious similarity on shared stopwords → drop stopwords before
  hashing; added a lexical-grounding guard for the fake provider.
- SQLite cross-thread error under FastAPI threadpool → `check_same_thread=False`.

**Phase 1 exit criteria met:** a documented local command demonstrates an
end-to-end query without paid API credentials; tests execute and pass.

## 2026-10-15 — Phase 2 (retrieval baselines + metrics harness)

**Built:** expanded the synthetic corpus to 14 distinct-topic docs; authored a
50-case labeled benchmark (`benchmark_v1.json`) across 8 query categories with
provenance and answerability labels; metrics module (Recall/MRR/nDCG/Hit with
explicit None-on-no-relevant and dedup-before-truncation semantics); a heuristic
reranker (honest stand-in, not a trained cross-encoder); a reproducible harness
running B0 BM25 / B1 dense / B2 hybrid(RRF) / B3 hybrid+rerank through one path,
emitting JSON+Markdown reports with full run metadata (run_id, git commit,
dataset/index versions); `ragbench.cli evaluate`.

**Validation (actually run):** `python -m pytest` → **38 passed**; ruff clean.
Benchmark run `bf643c87` recorded in docs/benchmark-results.md.

**Measured findings (real, incl. negatives):** BM25 strongest on this
fake-embedding setup (recall@5 1.000); dense weakest (0.929); hybrid matches
BM25 recall; the heuristic reranker slightly *reduced* mrr/ndcg vs BM25.
Abstention precision 1.000 but recall only 0.40–0.53 (misleading-overlap cases
leak) — threshold calibration deferred to Phase 4.
