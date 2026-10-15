# Next Steps (resume here)

## Immediately executable
1. **Phase 12/13 — report & packaging:** finalize docs/research.md; add
   docs/interview-preparation.md; review the §24 acceptance matrix; truthful
   resume bullets; final README pass.
2. **Verify where a runtime exists:** Docker build + `compose up`; GitHub Actions
   run; `helm lint`/`kubectl apply` on a local cluster; `terraform plan`/`apply`
   with real AWS creds; live Grafana/Streamlit; real embedding provider re-run.

## Done since last checkpoint
- Phases 1–5, 7–11 covered. 1–5 & 11 VERIFIED; 10 config-validated (fmt/init/
  validate pass, apply not run); 7, 8, 9 authored/PARTIAL (Docker/compose, hosted
  CI, K8s/Helm, live Grafana/Streamlit NOT VERIFIED — no runtime). 68 tests pass.
  Docs in docs/{research,benchmark-results,quality-gate,deployment,observability,
  traceability,runbook}.md + infrastructure/terraform/README.md.

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
