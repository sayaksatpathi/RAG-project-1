"""Phase 6 API hardening tests: security headers, rate limiting, body-size
guard, upload content-type allowlist, path-traversal-safe filenames, the 500
envelope, and CORS. All offline with in-memory SQLite."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from ragbench.api.app import create_app
from ragbench.api.security import FixedWindowRateLimiter, safe_filename, token_matches
from ragbench.config import Config
from ragbench.pipeline import Pipeline
from ragbench.storage import SQLiteStore

TOKEN = {"Authorization": "Bearer dev-local-token"}


def _client(config: Config | None = None) -> TestClient:
    config = config or Config()
    pipeline = Pipeline(config=config, store=SQLiteStore(":memory:"))
    return TestClient(create_app(pipeline=pipeline))


# --- unit-level helpers ------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("../../../etc/passwd.md", "passwd.md"),
    ("..\\..\\windows\\system32\\evil.txt", "evil.txt"),
    ("my report.md", "my_report.md"),
    ("", "upload"),
    ("...", "upload"),
    ("\x00\x00.md", "md"),
])
def test_safe_filename_strips_paths_and_junk(raw, expected):
    assert safe_filename(raw) == expected


def test_token_matches_is_exact_and_rejects_wrong():
    assert token_matches("Bearer s3cret", "s3cret")
    assert not token_matches("Bearer s3cre!", "s3cret")  # same length, wrong value
    assert not token_matches("s3cret", "s3cret")          # missing scheme
    assert not token_matches(None, "s3cret")


def test_rate_limiter_allows_then_blocks_and_resets():
    rl = FixedWindowRateLimiter(limit=2, window_s=60.0)
    assert rl.check("ip", now=0.0).allowed
    assert rl.check("ip", now=1.0).allowed
    blocked = rl.check("ip", now=2.0)
    assert not blocked.allowed and blocked.retry_after >= 1
    assert rl.check("ip", now=61.0).allowed  # new window


# --- HTTP-level behavior -----------------------------------------------------

def test_security_headers_on_every_response():
    r = _client().get("/health/live")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Request-ID"]


def test_rate_limit_returns_429_with_retry_after():
    cfg = dataclasses.replace(Config(), rate_limit_per_min=3)
    client = _client(cfg)
    body = {"query": "what is bm25", "strategy": "bm25"}
    codes = [client.post("/api/v1/query", json=body).status_code for _ in range(3)]
    assert codes == [200, 200, 200]
    blocked = client.post("/api/v1/query", json=body)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.json()["request_id"]


def test_health_is_exempt_from_rate_limit():
    cfg = dataclasses.replace(Config(), rate_limit_per_min=1)
    client = _client(cfg)
    assert all(client.get("/health/live").status_code == 200 for _ in range(5))


def test_body_size_guard_rejects_oversized_request():
    cfg = dataclasses.replace(Config(), max_request_bytes=20)
    client = _client(cfg)
    r = client.post("/api/v1/query", json={"query": "this body is clearly over twenty bytes"})
    assert r.status_code == 413
    assert r.json()["request_id"]


def test_upload_rejects_unsupported_type():
    client = _client()
    files = {"file": ("malware.exe", b"MZ binary payload", "application/octet-stream")}
    assert client.post("/api/v1/documents", files=files, headers=TOKEN).status_code == 415


def test_upload_sanitizes_traversal_filename():
    client = _client()
    files = {"file": ("../../../etc/passwd.md", b"reciprocal rank fusion content", "text/plain")}
    r = client.post("/api/v1/documents", files=files, headers=TOKEN)
    assert r.status_code == 200
    assert r.json()["filename"] == "passwd.md"  # no path components survive


def test_unhandled_error_returns_clean_500_envelope():
    pipeline = Pipeline(config=Config(), store=SQLiteStore(":memory:"))

    def _boom() -> dict:
        raise RuntimeError("internal detail that must not leak")

    pipeline.stats = _boom  # type: ignore[method-assign]
    client = TestClient(create_app(pipeline=pipeline), raise_server_exceptions=False)
    r = client.get("/api/v1/metrics/summary")
    assert r.status_code == 500
    body = r.json()
    assert body == {"error": "internal server error", "request_id": body["request_id"]}
    assert "internal detail" not in r.text
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_cors_header_present_when_configured():
    cfg = dataclasses.replace(Config(), cors_origins=("https://app.example.com",))
    client = _client(cfg)
    r = client.get("/health/live", headers={"Origin": "https://app.example.com"})
    assert r.headers.get("access-control-allow-origin") == "https://app.example.com"
