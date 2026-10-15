# Next Steps (resume here)

## Immediately executable
1. **Phase 9 — K8s/Helm:** Deployment/Service, ConfigMap/Secret refs,
   liveness/readiness/startup probes, resource requests/limits, a Helm chart +
   values; validate with available tooling, mark runtime NOT VERIFIED.
2. **Phase 10 — Terraform:** opt-in, minimal, cost-aware IaC; `terraform
   validate` only (no creds); document teardown.
3. **Phase 12 — research report:** finalize docs/research.md (threats, ablations)
   from run artifacts; add docs/interview-preparation.md (Phase 13).
4. **Verify where a runtime exists:** Docker build + `compose up`; GitHub Actions
   run; live Grafana/Streamlit; real embedding provider re-run.

## Done since last checkpoint
- Phases 1–5, 7, 8, 11 covered. 1–5 & 11 VERIFIED; 7 & 8 PARTIAL (Docker/compose,
  hosted CI, live Grafana/Streamlit NOT VERIFIED — no runtime). 68 tests pass.
  Docs in docs/{research,benchmark-results,quality-gate,deployment,observability,
  traceability,runbook}.md.

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
