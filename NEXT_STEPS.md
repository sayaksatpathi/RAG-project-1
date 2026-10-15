# Next Steps (resume here)

## Immediately executable
1. **Phase 2 — baselines:** wire B0–B3 (BM25 / dense / hybrid / +rerank stub)
   through one harness; compute Recall@k, MRR@k, nDCG@k on the labeled dataset.
2. Build the ~100-case benchmark dataset under `evaluation/datasets/` with
   provenance and answerability labels (start from the sample corpus).
3. **Phase 3 — adaptive router:** interpretable feature-based policy + strong
   fallback; compare vs strongest fixed baseline; ablations.
4. **Phase 4 — quality gate:** candidate-vs-baseline evaluator with versioned
   thresholds; deliberate-regression demo that the gate rejects.

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
