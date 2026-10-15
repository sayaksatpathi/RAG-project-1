# Observability

Instrumentation covers the paths that actually exist. No raw query text,
document content, credentials, or personal data is placed in logs or metric
labels; labels are kept low-cardinality (route templates and strategy names).

## Structured logging

JSON logs, one object per line, via `ragbench/observability/logging.py`. The API
emits a `request` log line per request with `request_id`, `method`, `route`,
`status`, and `latency_ms` — correlated by `request_id` (also returned in the
`X-Request-ID` response header). Query text is never logged.

## Prometheus metrics

Exposed at **`GET /metrics`** (Prometheus text format). Each app owns its own
`CollectorRegistry` so multiple apps/tests never collide. Metrics:

| Metric | Type | Labels |
|---|---|---|
| `ragbench_requests_total` | counter | method, route, status |
| `ragbench_request_latency_seconds` | histogram | route |
| `ragbench_retrieval_strategy_total` | counter | strategy |
| `ragbench_abstentions_total` | counter | — |
| `ragbench_provider_errors_total` | counter | kind |
| `ragbench_indexed_documents` | gauge | — |

Scrape config: [`observability/prometheus/prometheus.yml`](../observability/prometheus/prometheus.yml).

## Grafana

A starter dashboard is provided at
[`observability/grafana/ragbench-dashboard.json`](../observability/grafana/ragbench-dashboard.json)
(request rate, p95 latency, strategy distribution, abstention rate, indexed
documents, provider errors). **NOT VERIFIED:** it has not been loaded into a live
Grafana (no runtime here); panels show "no data" gracefully until the API is
scraped. No production traffic history is fabricated.

## Dashboard (Streamlit)

`apps/dashboard/app.py` — RAG Playground, Documents, Experiment Comparison,
Quality Gate, Operations. It calls real pipeline/service behavior and shows
honest empty states (e.g. "No documents indexed yet", "No benchmark reports
found") rather than seeded values. Run:

```bash
streamlit run apps/dashboard/app.py
```

**Status:** the module imports/compiles cleanly; an interactive Streamlit run has
not been performed in this environment (no browser session), so live rendering is
NOT VERIFIED, but it uses only verified pipeline APIs.

## Verified here

- `/metrics` endpoint renders Prometheus text with real counters after traffic
  (integration test `test_metrics_endpoint.py`).
- Metrics recording and the JSON log formatter (unit tests
  `test_observability.py`).
- `X-Request-ID` header present on responses.
