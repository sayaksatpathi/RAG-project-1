# Next Steps (resume here)

## Immediately executable
1. **Verify Docker/CI where a runtime exists:** build the image and run
   `docker compose up` on a machine with Docker; push to GitHub to execute the
   Actions workflow. Flip the NOT VERIFIED markers once done.
2. **Phase 7 — observability & dashboard:** structured logs, request IDs,
   Prometheus metrics, a Streamlit dashboard (RAG playground, experiment
   comparison, quality-gate view) with honest empty states.
3. **Phase 5 — traceability:** persist evaluation-run metadata/registry; enforce
   re-index on incompatible embedding/chunk changes (the `index_version` guard
   exists).
4. Configure a real embedding provider and re-run harness + `calibrate`.

## Done since last checkpoint
- Phases 1–4 VERIFIED. Phase 8 PARTIAL: CI offline steps + gate-demo verified
  locally; Docker/compose authored (NOT VERIFIED, no Docker); hosted CI run NOT
  VERIFIED (no remote). Results in docs/{research,benchmark-results,quality-gate,
  deployment}.md.

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
