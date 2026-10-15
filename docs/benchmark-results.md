# Benchmark Results

**Actual measured results only.** Reproduce with:

```bash
python -m ragbench.cli evaluate --dataset evaluation/datasets/benchmark_v1.json --k 5
```

Reports (JSON + Markdown) are written to `evaluation/reports/` and are git-ignored
as run artifacts; the summary below is transcribed from a real run.

## Run (recorded 2026-10-15)

- run_id: `bf643c87-d493-4263-83a1-78fc33016023`
- git_commit: `7bc5f30`
- dataset_version: `v1` (50 synthetic cases, 14-doc corpus), k = 5
- index_version: `fake:all-MiniLM-L6-v2:d256:c120:o24`
- embedding_provider: `fake:all-MiniLM-L6-v2:d256` (deterministic, non-semantic)
- reranker: `heuristic-rerank` (deterministic stand-in, NOT a trained cross-encoder)

### Aggregate (cases with relevance labels)

| Baseline | recall@5 | mrr@5 | ndcg@5 | hit@5 | abstain P | abstain R |
|---|---|---|---|---|---|---|
| B0 BM25 | 1.000 | 0.981 | 0.979 | 1.000 | 1.000 | 0.533 |
| B1 dense | 0.929 | 0.901 | 0.885 | 0.971 | 1.000 | 0.467 |
| B2 hybrid (RRF) | 1.000 | 0.960 | 0.960 | 1.000 | 1.000 | 0.467 |
| B3 hybrid + rerank | 0.986 | 0.964 | 0.958 | 1.000 | 1.000 | 0.400 |

## Honest interpretation (and limitations)

These numbers describe **this corpus + dataset under the deterministic fake
embedding**, and must not be read as general claims about BM25 vs dense
retrieval.

1. **BM25 is strongest here.** The dataset questions share substantial lexical
   content with their target documents, and the default embedding is a hash, not
   a semantic model — so sparse retrieval wins. B1 (dense) is the weakest. This
   is expected given the stand-in embedder and is exactly why a real embedding
   provider is needed before drawing retrieval-quality conclusions.
2. **Reranking did not help — and slightly hurt.** B3's mrr@5/ndcg@5 are below
   B0's. A negative result: the heuristic reranker reorders an already-good
   candidate set without a true relevance model. This is reported, not hidden.
3. **Abstention: perfect precision, weak recall.** The system never abstained on
   an answerable question (precision 1.0) but missed many it should have declined
   (recall 0.40–0.53). The misses are dominated by the *misleading_overlap* and
   some *ambiguous* cases, which contain corpus content words and so pass the
   lexical-grounding guard and clear the (uncalibrated) 0.15 threshold.
   Calibrating this threshold on a validation split and reporting the
   precision/recall trade-off is Phase 4 work.

## Per-category abstention (B2 hybrid, same run)

The report's `by_category.<category>.abstain_accuracy` field records, per
category, the fraction of cases where the abstain decision matched the label.
Clearly out-of-corpus categories (`unanswerable`) abstain well; `direct_fact`
answers well; `misleading_overlap` is the known weak spot. See the JSON report
for exact per-category figures for every baseline.

## Not yet measured (PENDING)

- Answer correctness / faithfulness against reference answers (needs a judge).
- Latency/cost percentiles under declared load (Phase 11).
- Results with a real embedding model and real generation provider.
