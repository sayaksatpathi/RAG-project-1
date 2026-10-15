# Runbook

Practical diagnosis and recovery for common RAGBench issues. Many conditions are
reproducible offline via `ragbench failure-demo`.

## Query errors / 500s

1. Check liveness/readiness: `GET /health/live`, `GET /health/ready`.
2. Inspect structured logs for the `request_id` (returned in `X-Request-ID`);
   each request logs method/route/status/latency.
3. Check `GET /metrics` → `ragbench_provider_errors_total` for provider faults.

## Poor retrieval quality

1. Confirm the right index is active: `ragbench index-health`.
2. Re-run the benchmark: `ragbench evaluate` and compare per-category metrics in
   the report against the last good run (`ragbench runs`).
3. Verify the embedding provider — the default fake embedding is non-semantic;
   switch to a real provider for semantic recall.

## Citation validation failures

- A `warnings` entry "citations failed identifier validation" means a cited
  passage was not among those retrieved or is from a different index version.
  Check that `index_version` is consistent (`ragbench index-health`); re-index if
  it changed (below).

## Ingestion failure

- `ParseError` → unsupported type, non-UTF-8, oversized (>10 MB), or a scanned
  PDF with no text layer (error E1042 → status `empty`). Supply a valid
  text-based document. Uploads are rejected cleanly; no partial index is written.

## LLM/generation provider rate limits or timeouts

- The query path degrades gracefully: on a provider exception it returns a safe
  "temporarily unable to generate" message with a
  `generation_provider_error` warning rather than crashing (verified by
  `failure-demo`: `failing_generation_provider`). Recovery: retry after the
  provider recovers; there is no unbounded retry storm.

## Database unavailable

- `/health/ready` returns 503; operations raise loudly. Recovery: restore/
  reconnect the database; readiness returns to 200 (verified: `database_
  unavailable`). SQLite is file-backed; ensure the `/data` volume is mounted.

## Incompatible index / re-index required

- Symptom: `IndexMismatchError` — documents exist but none match the active
  `index_version` (embedding or chunk config changed).
- Diagnose: `ragbench index-health` (`reindex_required: true`).
- Recover: `ragbench reindex` rebuilds every document under the active version
  and removes stale-version chunks (verified: `incompatible_index_config`).

## High latency or cost

- Measure: `ragbench loadtest --n 200` (reports p50/p95/p99, throughput, error
  rate, and conditions). Compare against docs/benchmark-results.md.
- If reranking is enabled, weigh its latency vs ranking benefit (B3 vs B2 in the
  benchmark; B3 did not help on the current corpus).

## Quality gate rejection

- `ragbench gate-demo` shows a candidate rejected with explicit reasons. In CI,
  the `retrieval-gate` job fails if the degraded candidate is not rejected. To
  understand a rejection, read the `rejection_reasons` in the decision and the
  thresholds in `evaluation/gate_policy.json`.

## Failed deployment / rollback

- No automatic public deployment is configured. Promotion requires a passing
  gate. Roll back by redeploying the last known-good image tag and restoring the
  last approved baseline (`evaluation/baselines/approved_baseline.json`). See
  docs/deployment.md.
