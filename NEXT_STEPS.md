# Next Steps (resume here)

## Done (2026-10-27)
- **Phases 6, 12, 13 complete.** API hardening (headers, rate limit, body guard,
  filename sanitization, 415/413 upload guards, CORS, 500 envelope; 16 tests);
  the consolidated `docs/research-report.md` with reproduced numbers; packaging
  (LICENSE, pyproject metadata, `ragbench version`, CHANGELOG/SECURITY/
  CONTRIBUTING, Makefile targets). 90 tests pass; ruff clean.

## Immediately executable (all remaining items are runtime-gated)
1. **Verify where a runtime exists:** Docker build + `compose up`; GitHub Actions
   run; `helm lint`/`kubectl apply` on a local cluster; `terraform plan`/`apply`
   with real AWS creds; live Grafana/Streamlit; real embedding provider re-run.
2. **Research deepening:** real embedding provider re-run of the identical
   harness; paired significance testing + confidence intervals; abstention
   threshold calibration on a held-out split.

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
