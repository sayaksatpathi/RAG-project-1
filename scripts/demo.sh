#!/usr/bin/env bash
# Reproducible RAGBench demo — real behavior, fully offline (no paid provider).
# Usage: bash scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1. Ingest the sample corpus =="
python -m ragbench.cli ingest evaluation/datasets/corpus

echo; echo "== 2. Grounded query with citations (hybrid) =="
python -m ragbench.cli query "What is reciprocal rank fusion?" --strategy hybrid

echo; echo "== 3. Abstention on an out-of-corpus question =="
python -m ragbench.cli query "How do I bake sourdough bread at high altitude?"

echo; echo "== 4. Retrieval baseline comparison (B0-B4) + report =="
python -m ragbench.cli evaluate --no-write

echo; echo "== 5. Quality gate: reject a regression, pass a healthy candidate =="
python -m ragbench.cli gate-demo

echo; echo "== 6. Controlled failure experiments =="
python -m ragbench.cli failure-demo

echo; echo "== 7. Bounded load / latency =="
python -m ragbench.cli loadtest --n 100

echo; echo "== 8. Index health & traceability =="
python -m ragbench.cli index-health
python -m ragbench.cli runs --limit 3

echo; echo "Demo complete."
