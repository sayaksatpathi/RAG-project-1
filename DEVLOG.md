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

## 2026-10-15 — Phase 5 (data/model/config traceability)

**Built:** persist full normalized document text (`documents.text` column +
idempotent ALTER-TABLE migration) so documents can be re-chunked; index-mismatch
enforcement — `IndexMismatchError` raised when documents exist but no chunks
match the active `index_version`, with `Pipeline.index_health()` and
`Pipeline.reindex()` (rebuilds every doc under the active version and removes
other-version chunks, never mixing); a persistent evaluation-run registry
(`ragbench/storage/run_registry.py`) recording run_id/timestamp/git_commit/
dataset_version/index_version/config/metrics/report_path; CLI `index-health`,
`reindex`, `runs`, and auto-registration on `evaluate`.

**Validation:** `python -m pytest` → **63 passed**; ruff clean. CLI smoke:
`index-health` reports active vs present versions; `evaluate` registers a run;
`runs` lists it with its git commit and index version (traceable).

## 2026-10-15 — Phase 11 (reliability & performance)

**Built:** graceful degradation in `Pipeline.query` (generation-provider
exceptions → safe message + `generation_provider_error` warning, no crash);
`ragbench/reliability` with fault-injection providers (FailingProvider,
SlowProvider), a controlled failure-experiment runner (slow provider, failing
provider, corrupt upload, DB unavailable, incompatible index), and a bounded
load/latency harness (p50/p95/p99, throughput, error rate, conditions); CLI
`failure-demo` and `loadtest`; `docs/runbook.md`.

**Validation:** `python -m pytest` → **68 passed**; ruff clean.

**Measured:** `failure-demo` → all 5 scenarios PASS. `loadtest --n 200 hybrid`
→ ~1343 qps, 0 errors, p50/p95/p99 = 0.71/0.90/1.34 ms (offline, 14-doc corpus,
fake embedding, mock LLM, single thread). Conditions stated; not a production
claim. Recorded in docs/benchmark-results.md.

## 2026-10-15 — Phase 9 (Kubernetes & Helm)

**Built:** `deploy/kubernetes/` plain manifests (ConfigMap, Secret template,
PVC, Deployment, Service) and `deploy/helm/ragbench/` Helm chart (Chart,
values, templated deployment/service/configmap/secret/pvc + _helpers). Both
include liveness/readiness/startup probes, resource requests/limits, and a
hardened non-root securityContext. Single replica + Recreate with SQLite (RWO);
scaling documented as requiring the Postgres backend (no false HA claim).

**Validation:** plain manifest YAML and Chart.yaml/values.yaml parse with
PyYAML. **NOT VERIFIED:** no cluster/kubectl/helm available — `helm lint`,
`helm template`, and `kubectl apply` not run. Exact verification commands and
the NOT VERIFIED status are in docs/deployment.md and IMPLEMENTATION_STATUS.md.

## 2026-10-15 — Optional provider paths made real

Closed two dangling optional references the factories pointed at: implemented
`ragbench/embeddings/sentence_transformers_provider.py` and
`ragbench/generation/openai_provider.py`. Both import cleanly with no network or
credential access and fail with a clear, actionable error when their dependency/
credential is absent (previously the config option would have thrown a
ModuleNotFoundError about RAGBench's own package). The OpenAI provider uses the
already-present httpx, a bounded timeout, and bounded transient-only retries.
Also fixed the pipeline to size the dense index from the embedder's actual
dimension rather than the config value. 73 tests pass; ruff clean.

## 2026-10-15 — Benchmark expanded to 100 cases + graded nDCG

Expanded `benchmark_v1.json` to **100 cases** (`dataset_version: v1.1`) across
the same 8 categories, and added optional graded relevance
(`relevance_grades: {doc_key: grade}`, primary 3 / supporting 1) on multi-passage
cases. Wired grades through `BenchmarkCase`/`load_dataset`/the harness into
`ndcg_at_k` so nDCG is graded where labels provide it (binary elsewhere).

Also warmed the retriever in `run_load` before concurrent workers, fixing a
genuine race (threads building the lazy index simultaneously caused intermittent
load errors); after warm-up, queries are pure in-memory and the concurrency test
is stable across repeats.

**Validation:** 74 tests pass; ruff clean; new graded-nDCG unit test proves
graded ≠ binary. Fresh run `879ec810` (v1.1, 100 cases) recorded in
docs/benchmark-results.md — the neutral H1 result holds; BM25 remains strongest;
abstention precision 0.944 (still above the gate's 0.90 floor).

## 2026-10-15 — Phase 10 (Terraform & cloud readiness)

**Built:** `infrastructure/terraform/` — minimal opt-in AWS IaC: ECR repo
(scan-on-push, keep-5 lifecycle) + CloudWatch log group always; an opt-in ECS
Fargate service (`enable_service` default false) that is private by default
(`assign_public_ip=false`, ingress only via explicit `ingress_cidrs`); IAM task
execution role (AWS-managed least-priv policy); region a required variable;
outputs, tfvars example, and a README with resource inventory, cost, teardown,
and exposure notes.

**Validation (actually run):** `terraform fmt` → clean; `terraform init
-backend=false` → success (provider downloaded); `terraform validate` →
**"the configuration is valid."** `plan`/`apply` NOT RUN — no AWS credentials and
apply would create billable resources (not authorized). `.gitignore` updated to
exclude `.terraform/`, state, and tfvars (lock file kept).

## 2026-10-27 — Phases 6, 12, 13 (API hardening, research report, packaging)

**Phase 6 — API & app hardening.** Added `ragbench/api/security.py`
(`safe_filename` path-traversal defense, constant-time `token_matches` via
`hmac.compare_digest`, a thread-safe per-client `FixedWindowRateLimiter`, and the
security-header set). Wired into `ragbench/api/app.py`: security headers on every
response (incl. errors), a Content-Length body-size guard (413), per-client rate
limiting that exempts probes/metrics (429 + `Retry-After`), an upload
content-type allowlist (415), a streaming upload size cap (413), optional CORS,
and an `Exception` handler returning `{error, request_id}` without leaking
internals. New config: `cors_origins`, `rate_limit_per_min`, `max_request_bytes`.
New metrics: `auth_failures_total`, `requests_rejected_total`. **16 new tests**
in `tests/integration/test_api_security.py`.

**Phase 12 — research report.** `docs/research-report.md`: a self-contained
capstone (abstract, question/hypotheses, method, measured v1.1 results,
ablations, abstention analysis, reliability/load, threats, reproducibility,
conclusions). Numbers **reproduced** via a fresh `ragbench evaluate` — run
`5f421bd6`, git `62244a6`, identical to the recorded v1.1 run `879ec810`; the
neutral H1 result holds.

**Phase 13 — final hardening & packaging.** `LICENSE` (MIT); full
`pyproject.toml` metadata (authors, license, readme, classifiers, URLs,
keywords); version bumped to `0.13.0` (the API advertises it); `ragbench version`
/ `--version`; `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`; extra Makefile
targets (`format`, `security`, `report`, `version`, `clean`). Editable install
(`pip install -e .`) smoke-tested; `.env.example` documents the new settings.

**Validation:** **90 tests pass**; ruff clean. The offline-first ethos and honest
NOT-VERIFIED labels for the runtime-gated deployment pieces are unchanged.

## 2026-10-28 — Docker runtime VERIFIED

Docker became available (WSL Docker 29.1.3 + Compose 2.40). Verified the
previously-authored container path for real: `docker build` produces
`ragbench:local`; `docker compose config` is valid; running the image serves
`/health/ready`=200, `/health/live`, `POST /api/v1/query` (grounded/abstain
path), upload auth (401 without token → 200 with), the Phase 6 security headers
on every response, and `/metrics`; the image runs as non-root (`appuser`,
uid 10001). Phase 8 Docker flips PARTIAL → VERIFIED in IMPLEMENTATION_STATUS.md.

Still NOT VERIFIED (next session): Kubernetes/Helm live apply (kind 0.33 is
present but kubectl/helm are not installed), Terraform re-validate, and live
Grafana/Prometheus/Streamlit render. The user's other running containers
(Jenkins, E2B sandbox, an existing kind cluster, Grafana/Prometheus) occupy
ports 8000/8001/3000/9090, so the smoke test used host port 8010 and a dedicated
container, touching none of them.

## 2026-10-29 — Kubernetes/Helm, CI, Terraform, Prometheus/Grafana VERIFIED

Cleared the remaining runtime-gated items where tooling exists:

- **Kubernetes & Helm (Phase 9) → VERIFIED** on a throwaway `kind` cluster
  (`ragbench`, separate from the existing `opsforge` cluster; kubectl v1.35.9 +
  helm v4.3.1 installed to WSL user-space, kind v0.33). Loaded `ragbench:local`,
  applied the raw manifests → Deployment rolled out, pod 1/1 Running,
  /health/ready=200, query works, upload auth 401 — exercising the liveness/
  readiness/startup probes, non-root + readOnlyRootFilesystem security context,
  PVC bind, and ConfigMap/Secret wiring. `helm lint` clean; `helm install` →
  deployed, pod Running, /health/ready=200. Everything torn down; the cluster
  was deleted.
- **Hosted CI (Phase 8) → VERIFIED.** GitHub Actions `CI` workflow ran on the
  Phase-6/12/13 push (run 40506328588) and completed **success** in 52s.
- **Terraform (Phase 10)** re-confirmed: `fmt -check`, `init -backend=false`,
  `validate` all pass (Terraform 1.16.5). `apply` still NOT RUN — it creates
  billable AWS resources and is not authorized.
- **Prometheus config** passes `promtool check config` (via the official
  prom/prometheus:v2.51.2 image); **Grafana dashboard** is valid JSON (6 panels
  referencing real `ragbench_*` metrics); the Streamlit dashboard compiles.

Still NOT VERIFIED (genuinely gated, not incomplete): live Grafana/Streamlit
*render* (needs a wired datasource/instance), `terraform apply` (billable AWS),
and a real embedding-provider re-run (sentence-transformers — multi-GB download).
No app/source code changed in this pass; the deployment artifacts were already
correct and now carry real run evidence.
