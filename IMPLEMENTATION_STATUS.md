# RAGBench — Implementation Status

Status legend: NOT STARTED · IN PROGRESS · VERIFIED · BLOCKED · DEFERRED

Last updated: 2026-10-15

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
| 5 | Data/model/config traceability | NOT STARTED |
| 6 | API & app hardening | NOT STARTED |
| 7 | Observability & dashboard | NOT STARTED |
| 8 | Docker & CI/CD | PARTIAL — CI offline steps + gate-demo VERIFIED locally; Docker build/compose authored, NOT VERIFIED (no Docker); hosted CI run NOT VERIFIED (no remote) |
| 9 | Kubernetes & Helm | NOT STARTED |
| 10 | Terraform & cloud | NOT STARTED |
| 11 | Reliability & performance | NOT STARTED |
| 12 | Research report | NOT STARTED |
| 13 | Final hardening & packaging | NOT STARTED |

## Key decisions (see DECISIONS.md)

- Offline-first: SQLite storage, hand-written BM25, deterministic fake embeddings, mock LLM. No paid API or heavy model needed for the core slice, tests, or retrieval-only evaluation.
- Postgres/pgvector, sentence-transformers, and OpenAI-compatible generation are optional, config-gated, documented, and marked NOT VERIFIED where runtime is unavailable.
