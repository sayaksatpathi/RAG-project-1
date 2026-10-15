"""Prometheus metrics for the paths that actually exist.

Each Metrics instance owns its own CollectorRegistry so building multiple apps
(e.g. in tests) never raises duplicate-timeseries errors on the global default
registry. Labels are kept low-cardinality: route templates (not raw paths with
embedded IDs), and retrieval strategy names — never raw queries or user IDs.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

CONTENT_TYPE = CONTENT_TYPE_LATEST


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests_total = Counter(
            "ragbench_requests_total", "HTTP requests",
            ["method", "route", "status"], registry=self.registry,
        )
        self.request_latency = Histogram(
            "ragbench_request_latency_seconds", "HTTP request latency",
            ["route"], registry=self.registry,
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )
        self.retrieval_strategy_total = Counter(
            "ragbench_retrieval_strategy_total", "Retrieval strategy used",
            ["strategy"], registry=self.registry,
        )
        self.abstentions_total = Counter(
            "ragbench_abstentions_total", "Queries that abstained",
            registry=self.registry,
        )
        self.provider_errors_total = Counter(
            "ragbench_provider_errors_total", "Provider errors",
            ["kind"], registry=self.registry,
        )
        self.indexed_documents = Gauge(
            "ragbench_indexed_documents", "Documents currently indexed",
            registry=self.registry,
        )

    def observe_request(self, method: str, route: str, status: int, latency_s: float) -> None:
        self.requests_total.labels(method=method, route=route, status=str(status)).inc()
        self.request_latency.labels(route=route).observe(latency_s)

    def observe_query(self, strategy: str, abstained: bool) -> None:
        self.retrieval_strategy_total.labels(strategy=strategy).inc()
        if abstained:
            self.abstentions_total.inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)
