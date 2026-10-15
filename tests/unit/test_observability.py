import json
import logging

from ragbench.observability.logging import JsonFormatter, new_request_id
from ragbench.observability.metrics import Metrics


def test_json_formatter_includes_fields_and_is_valid_json():
    fmt = JsonFormatter()
    rec = logging.LogRecord("ragbench", logging.INFO, __file__, 1, "request", None, None)
    rec.fields = {"request_id": "abc", "status": 200, "latency_ms": 1.2}
    out = json.loads(fmt.format(rec))
    assert out["msg"] == "request"
    assert out["request_id"] == "abc" and out["status"] == 200


def test_request_ids_unique():
    assert new_request_id() != new_request_id()


def test_metrics_record_and_render():
    m = Metrics()
    m.observe_request("GET", "/api/v1/query", 200, 0.012)
    m.observe_query("hybrid", abstained=False)
    m.observe_query("bm25", abstained=True)
    text = m.render().decode()
    assert "ragbench_requests_total" in text
    assert 'strategy="hybrid"' in text
    assert "ragbench_abstentions_total" in text


def test_multiple_metrics_instances_do_not_collide():
    # Separate registries -> no duplicate timeseries error.
    a, b = Metrics(), Metrics()
    a.observe_request("GET", "/x", 200, 0.01)
    b.observe_request("GET", "/x", 200, 0.01)
    assert "ragbench_requests_total" in a.render().decode()
