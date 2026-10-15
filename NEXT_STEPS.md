# Next Steps (resume here)

## Immediately executable
1. **Phase 4 — quality gate:** candidate-vs-baseline evaluator reading the
   harness report, versioned thresholds in a policy file, machine-readable
   pass/fail, and a deliberate-regression demo the gate rejects. Also calibrate
   `abstain_min_score` on a validation split and report precision/recall.
2. Configure a real embedding provider (`sentence-transformers`) and re-run the
   identical harness to give the routing experiment (Phase 3) genuine headroom.
3. Optionally expand `benchmark_v1.json` toward ~100 cases and add graded
   relevance labels to exercise nDCG beyond binary.

## Done since last checkpoint
- Phase 1 vertical slice (VERIFIED). Phase 2 baselines + metrics harness
  (VERIFIED). Phase 3 adaptive router + ablation (VERIFIED); H1 neutral result
  recorded in docs/research.md and docs/benchmark-results.md.

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
