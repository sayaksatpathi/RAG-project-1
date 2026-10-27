# RAGBench — Implementation Status

Status legend: NOT STARTED · IN PROGRESS · VERIFIED · BLOCKED · DEFERRED

Last updated: 2026-10-27

## Environment audit (VERIFIED)

| Capability | State | Notes |
|---|---|---|
| OS | Windows 11, PowerShell + Bash | |
| Python | 3.12.10 | |
| FastAPI / pydantic / uvicorn | present | |
| numpy / pandas / scikit-learn | present | |
| pytest | present | |
| ruff | installed this session (0.17.0) | |
| Docker / Compose | **absent** | container paths authored but NOT VERIFIED |
| PostgreSQL / psql | **absent** | SQLite is the verified default backend |
| kubectl / kind / minikube | **absent** | k8s manifests NOT VERIFIED |
| Terraform | 1.16.4 present | validate-only; no cloud creds |
| sentence-transformers | absent | fake deterministic embeddings are the default |
| Network / paid LLM | not assumed | mock provider is the default |

## Phase status

| Phase | Description | Status |
|---|---|---|
| 0 | Audit & bootstrap | VERIFIED |
| 1 | Vertical slice (ingest→index→retrieve→generate→cite→abstain) | VERIFIED (24 tests, ruff clean, E2E CLI) |
| 2 | Retrieval baselines (BM25, dense, hybrid, rerank) | VERIFIED (B0-B3 harness, metrics, report; 38 tests) |
| 3 | Adaptive routing experiment | VERIFIED (B4 router, ablation, 45 tests; H1 neutral result recorded) |
| 4 | Evidence controls & evaluation gate | VERIFIED (gate policy, regression demo FAIL/PASS, calibration; 53 tests) |
| 5 | Data/model/config traceability | VERIFIED (index-mismatch rejection, reindex, run registry; 63 tests) |
| 6 | API & app hardening | VERIFIED (constant-time token, security headers, rate limit, body-size guard, filename sanitization, 415/413 upload guards, CORS, 500 envelope; 16 tests) |
| 7 | Observability & dashboard | PARTIAL — logging/metrics/`/metrics` VERIFIED (59 tests); Grafana + Streamlit authored, live render NOT VERIFIED |
| 8 | Docker & CI/CD | PARTIAL — CI offline steps + gate-demo VERIFIED locally; Docker build/compose authored, NOT VERIFIED (no Docker); hosted CI run NOT VERIFIED (no remote) |
| 9 | Kubernetes & Helm | AUTHORED, NOT VERIFIED — manifests + Helm chart (probes, resources, non-root); YAML/chart metadata validated; no cluster/kubectl/helm |
| 10 | Terraform & cloud | CONFIG VALIDATED — fmt/init/validate pass; apply NOT RUN (no creds, opt-in) |
| 11 | Reliability & performance | VERIFIED (5 failure experiments PASS, load harness p50/p95/p99, runbook; 68 tests) |
| 12 | Research report | VERIFIED (docs/research-report.md; numbers reproduced, run `5f421bd6`) |
| 13 | Final hardening & packaging | VERIFIED (LICENSE, full pyproject metadata, `ragbench version`, CHANGELOG/SECURITY/CONTRIBUTING, Makefile; editable install smoke-tested) |

## Final acceptance matrix (§24)

Evidence = passing tests (90 total), CLI runs this session, or an explicit status.

### A. Functional application
- [x] Upload/parse supported document — ingestion tests + demo
- [x] Chunks retain provenance and stable IDs — `test_chunking.py`
- [x] Sparse + dense indexes created/updated consistently — `test_retrieval.py`, pipeline
- [x] Retrieval configuration selectable/inspectable — CLI `--strategy`, harness
- [x] Grounded answer from retrieved evidence — `test_pipeline_api.py`, demo step 2
- [x] Citations map to real passages — citation validation tests
- [x] Insufficient evidence triggers abstention — demo step 3, abstention tests
- [x] Invalid inputs / provider failures handled safely — API + reliability tests
- [x] Deletion/re-indexing tested — `test_pipeline_api.py`, `test_traceability.py`

### B. Research and evaluation
- [x] Dataset provenance/licenses/limitations documented — `benchmark_v1.json`, research.md
- [x] Labels support reported metrics — document-level relevance documented
- [x] Splits/leakage controls documented — research.md (heuristic router, declared rule)
- [x] BM25/dense/hybrid/reranked/adaptive compared — B0–B4 harness (v1.1, 100 cases)
- [x] Retrieval metrics computed + edge cases tested — `test_metrics.py` (incl. graded nDCG)
- [x] Graded relevance exercises nDCG beyond binary — v1.1 `relevance_grades`
- [x] Answer/evidence metrics only where supported — citation validity + abstention PRF
- [x] Ablations included — research.md, report ablation block
- [x] Results reproducible from commands — `ragbench evaluate`, run registry
- [x] Negative findings reported honestly — H1 neutral, rerank negative

### C. AI quality gate
- [x] Baseline + candidate versions recorded — gate service, approved baseline
- [x] Thresholds explicit/configurable — `evaluation/gate_policy.json`
- [x] Deliberate regression fails the gate — `gate-demo` (B1_dense FAIL)
- [x] Passing config can pass — `gate-demo` (B2_hybrid PASS)
- [x] Reports explain outcome — rejection reasons in decision
- [x] Failing candidate not promoted — CI `retrieval-gate` job

### D. Backend and security
- [x] API schemas/errors documented — pydantic models, FastAPI docs
- [x] Write/admin endpoints protected — bearer token tests
- [x] File validation/limits/deletion tested — parsing + API tests
- [x] Secrets not committed/logged — `.env.example`, no raw query logging
- [x] Prompt injection treated as input boundary — docs + untrusted-data handling
- [x] Threat model / risks documented — docs/assumptions-and-limitations.md, security notes in README

### E. DevOps and operations
- [x] Local dev reproducible — README, demo script
- [ ] Docker build/compose — authored; **NOT VERIFIED** (no Docker)
- [x] CI covers core tests + quality gate — `.github/workflows/ci.yml` (hosted run NOT VERIFIED)
- [x] Health checks behave as documented — health endpoint tests
- [x] Telemetry real or honest empty states — `/metrics` test, dashboard empty states
- [x] Controlled failure tested — `failure-demo` (5/5 PASS)
- [x] Recovery/rollback tested where applicable — DB reconnect, reindex recovery
- [ ] Kubernetes/Helm — authored, YAML-validated; **NOT VERIFIED** (no cluster)
- [~] Terraform — fmt/init/validate **VERIFIED**; apply NOT RUN (no creds)

### F. Portfolio readiness
- [x] README reflects implementation — updated per phase
- [x] Architecture diagrams match code — docs/architecture.md (Mermaid)
- [x] Research results real + reproducible — docs/research.md, run registry
- [x] Threat model, runbook, deployment, experiment protocol exist — docs/
- [x] Demo works — `scripts/demo.sh` runs end-to-end this session
- [x] Interview prep describes real implementation — docs/interview-preparation.md
- [x] Resume bullets verified-only — interview-preparation.md
- [x] Unfinished items explicit — this matrix + NEXT_STEPS.md

## Key decisions (see DECISIONS.md)

- Offline-first: SQLite storage, hand-written BM25, deterministic fake embeddings, mock LLM. No paid API or heavy model needed for the core slice, tests, or retrieval-only evaluation.
- Postgres/pgvector, sentence-transformers, and OpenAI-compatible generation are optional, config-gated, documented, and marked NOT VERIFIED where runtime is unavailable.
