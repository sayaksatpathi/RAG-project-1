# Next Steps (resume here)

## Immediately executable
1. **Phase 5 — traceability:** persist evaluation-run metadata and enforce that
   an incompatible embedding/chunk change triggers deliberate re-index (the
   `index_version` guard exists; add a stored-run registry and a CI gate job).
2. **Phase 8 — CI:** wire a GitHub Actions workflow running lint, tests, the
   retrieval regression gate, and the gate-demo (offline, no paid API).
3. Configure a real embedding provider (`sentence-transformers`) and re-run the
   harness + `calibrate` to give routing (Phase 3) and abstention genuine
   semantic headroom.
4. Optionally expand `benchmark_v1.json` toward ~100 cases with graded relevance.

## Done since last checkpoint
- Phases 1–4 VERIFIED. Vertical slice; baselines + metrics harness; adaptive
  router + ablation (H1 neutral); quality gate + regression demo (FAIL/PASS) +
  abstention calibration. Results in docs/research.md, docs/benchmark-results.md,
  docs/quality-gate.md.

## Deferred / blocked (environment)
- Docker Compose, Kubernetes/Helm: authored but NOT VERIFIED (no runtime).
- Postgres/pgvector: optional path, NOT VERIFIED (no server).
- Terraform/cloud: validate-only; no credentials.

## How to run what exists now
```bash
python -m ragbench.cli ingest evaluation/datasets/corpus
python -m ragbench.cli query "What is reciprocal rank fusion?"
python -m pytest
```
