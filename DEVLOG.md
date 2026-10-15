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

## 2026-10-15 — Phase 3 (adaptive routing experiment)

**Built:** interpretable router (`ragbench/routing`) with ordered rules
(exact-identifier/rare-term → bm25; long paraphrase question → dense; else
hybrid fallback) adapting rarity to the live BM25 doc-frequencies; `adaptive`
strategy wired into the pipeline; harness baseline B4 with routing-distribution
and fallback-rate reporting; a pre-declared ablation comparing adaptive vs the
strongest fixed baseline (chosen by mrr@k) and noting remove-routing /
remove-rerank equivalents.

**Validation:** `python -m pytest` → **45 passed**; ruff clean. Run `e25e904b`.

**Measured finding (H1 neutral):** adaptive routed 45/50 queries to BM25 (4
hybrid fallback, 1 dense; fallback rate 0.08) and **tied** the strongest fixed
baseline BM25 exactly (+0.000 on all metrics). On this corpus lexical retrieval
dominates, so routing reproduces BM25 rather than beating it; the dominant
caveat is the non-semantic fake embedding. Recorded honestly in
docs/research.md and docs/benchmark-results.md.

## 2026-10-15 — Phase 4 (evidence controls & evaluation gate)

**Built:** versioned gate policy (`evaluation/gate_policy.json`); a gate
evaluator (`ragbench/gate/policy.py`) with regression and min_absolute
constraints, machine-readable decision + reasons, fail-closed on missing
metrics; a gate service (`ragbench/gate/service.py`) to pin an approved
baseline, check a candidate, and run a deliberate-regression demo; abstention
calibration sweep (`ragbench/evaluation/calibration.py`); CLI `gate-demo` and
`calibrate`.

**Validation:** `python -m pytest` → **53 passed**; ruff clean.

**Measured results:**
- `gate-demo`: degraded candidate (production strategy switched hybrid→dense,
  recall 1.000→0.929, −0.071 > 0.03 tolerance) → **FAIL** with reason; healthy
  candidate (hybrid) → **PASS**. Decision derives from metrics, not test names.
- `calibrate` (hybrid): F1-optimal threshold 0.20 (P0.69/R0.73) breaches the
  gate's 0.90 precision floor; precision-safe 0.15 (P1.00/R0.47) is the current
  default and satisfies the gate. Full sweep in docs/quality-gate.md.

## 2026-10-15 — Phase 8 (Docker & CI/CD)

**Built:** `[build-system]` added to pyproject (editable install + `ragbench`
console script verified); `.dockerignore`; non-root `Dockerfile` (python:3.12-
slim, `/data` volume, HEALTHCHECK on /health/live); `docker-compose.yml` (API +
optional pgvector profile); `.github/workflows/ci.yml` with least-privilege
jobs: lint, test, retrieval-gate (evaluate + gate-demo), docker-build,
dependency-scan (pip-audit); `docs/deployment.md`.

**Validation:** CI and compose YAML parse OK (PyYAML). `pip install -e .` and
`ragbench stats` work. The CI retrieval-gate commands (`ragbench evaluate
--no-write`, `ragbench gate-demo`) are the same ones verified to pass earlier
this session. **NOT VERIFIED:** Docker build/compose runtime (Docker
unavailable) and the hosted GitHub Actions run (no remote) — marked honestly in
docs/deployment.md and IMPLEMENTATION_STATUS.md.

## 2026-10-15 — Phase 7 (observability & dashboard)

**Built:** structured JSON logging with request IDs + `X-Request-ID` header
(no raw query/content logged); Prometheus metrics (`ragbench/observability`,
per-app CollectorRegistry) for requests, latency histogram, retrieval strategy,
abstentions, provider errors, indexed-documents gauge; `/metrics` endpoint;
API middleware wiring; a Streamlit dashboard (`apps/dashboard/app.py`) with
RAG playground / documents / experiment comparison / quality gate / operations
screens and honest empty states; Prometheus scrape config and a starter Grafana
dashboard JSON; `docs/observability.md`.

**Validation:** `python -m pytest` → **59 passed**; ruff clean; dashboard
`py_compile` clean. `/metrics` verified to render real counters after traffic
(integration test). **NOT VERIFIED:** live Grafana load and interactive
Streamlit render (no runtime) — marked honestly.
