# Data, Model & Configuration Traceability

## Index versioning and re-index enforcement

The active index is identified by:

```
index_version = embedding_provider:model:dim:chunk_size:overlap
```

Every chunk and embedding is stored tagged with the `index_version` that
produced it, and the retriever only loads chunks for the **active** version, so
vectors from incompatible embedding/chunk configurations are never mixed.

If documents exist but **no chunks** are present for the active `index_version`
(i.e. the embedding or chunk configuration changed), the pipeline **rejects**
queries with an `IndexMismatchError` rather than silently serving an empty or
stale index. The operator then runs a deliberate re-index:

```bash
ragbench index-health   # shows active version, present versions, reindex_required
ragbench reindex        # re-chunks + re-embeds every document under the active version
```

Re-indexing is possible because the full normalized document text is persisted
(the `documents.text` column), so documents can be re-chunked without the
original upload. `reindex` removes chunks from any other version, guaranteeing a
single consistent index.

Verified by `tests/integration/test_traceability.py`: changing the chunk config
makes `reindex_required` true and queries raise `IndexMismatchError`; after
`reindex()` queries work again and only the new `index_version` remains.

## Evaluation run registry

Every `ragbench evaluate` run is recorded in a persistent SQLite registry
(`RAGBENCH_RUNS_DB`, default `data/ragbench_runs.db`) capturing: `run_id`,
`timestamp`, `git_commit`, `dataset_version`, `index_version`, the full config
block, a per-baseline metrics summary, and the path to the full report artifact.

```bash
ragbench evaluate     # writes a report AND registers the run
ragbench runs         # list recorded runs (most recent first)
```

This makes every result traceable to the dataset, code revision, and
configuration that created it — the Phase 5 exit criterion. The registry DB is a
local artifact (git-ignored); the committed report metadata lives in
`docs/benchmark-results.md`.
