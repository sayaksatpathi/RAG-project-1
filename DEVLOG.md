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
