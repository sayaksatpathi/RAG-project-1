# Next Steps (resume here)

## Immediately executable
1. **Phase 5 — traceability:** persist evaluation-run metadata/registry; enforce
   re-index on incompatible embedding/chunk changes (the `index_version` guard
   exists). Add `docs/runbook.md` (Phase 14 deliverable) and a controlled
   failure-experiment harness (Phase 11).
2. **Verify where a runtime exists:** build the Docker image + `compose up`;
   push to run GitHub Actions; load the Grafana dashboard against a live
   Prometheus; run the Streamlit dashboard. Flip the NOT VERIFIED markers.
3. Configure a real embedding provider and re-run harness + `calibrate`.
4. Phases 9 (K8s/Helm), 10 (Terraform), 12 (research report) remain.

## Done since last checkpoint
- Phases 1–4 VERIFIED. Phase 8 PARTIAL (CI offline steps + gate-demo verified;
  Docker/compose + hosted CI NOT VERIFIED). Phase 7 PARTIAL: logging/metrics/
  `/metrics` VERIFIED; Grafana + Streamlit authored, live render NOT VERIFIED.
  Docs in docs/{research,benchmark-results,quality-gate,deployment,observability}.md.

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
