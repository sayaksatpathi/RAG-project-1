# Next Steps (resume here)

## Immediately executable
1. **Phase 11 — reliability:** controlled failure experiments (slow/failed
   provider, DB unavailable, malformed upload, bounded load) + latency
   percentiles; add `docs/runbook.md`.
2. **Phase 9 — K8s/Helm:** local deployment manifests + Helm chart with probes,
   resources; validate with available tooling, mark runtime NOT VERIFIED.
3. **Phase 12 — research report:** regenerate tables from run artifacts; expand
   docs/research.md with threats/ablations.
4. **Verify where a runtime exists:** Docker build + `compose up`; GitHub Actions
   run; live Grafana/Streamlit. Configure a real embedding provider; re-run
   harness + `calibrate`. Phase 10 (Terraform) remains.

## Done since last checkpoint
- Phases 1–5 + 7 + 8 covered. 1–4 & 5 VERIFIED; 7 & 8 PARTIAL (Docker/compose,
  hosted CI, live Grafana/Streamlit NOT VERIFIED — no runtime). 63 tests pass.
  Docs in docs/{research,benchmark-results,quality-gate,deployment,observability,
  traceability}.md.

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
