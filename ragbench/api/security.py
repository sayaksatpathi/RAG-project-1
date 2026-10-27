"""Hardening helpers for the HTTP API: safe filenames, a constant-time bearer
check, an in-process rate limiter, and the security response headers.

These are deliberately dependency-free and offline. The rate limiter is a
per-process fixed-window counter — correct for a single instance and honest
about its scope: horizontal scaling would need a shared store (documented in
docs/deployment.md), not a false claim of distributed limiting here.
"""

from __future__ import annotations

import hmac
import re
import threading
import time
from dataclasses import dataclass

# Applied to every reply. The API serves JSON/text only and renders no HTML,
# so a restrictive policy has no legitimate cost and closes off sniffing,
# framing, and referrer-leak classes of issue.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_NAME = 128


def safe_filename(name: str | None) -> str:
    """Reduce an uploaded filename to a safe basename.

    Strips directory components (defeating traversal such as ``../../etc/passwd``
    or Windows ``..\\``), removes control/unusual characters, bounds the length,
    and never returns an empty or dot-only name. The original is untrusted
    input; only the sanitized basename is ever stored or echoed back.
    """
    raw = (name or "").replace("\\", "/").split("/")[-1]
    raw = raw.replace("\x00", "").strip()
    cleaned = _UNSAFE.sub("_", raw).strip("._")
    if not cleaned:
        return "upload"
    return cleaned[:_MAX_NAME]


def token_matches(authorization: str | None, expected_token: str) -> bool:
    """Constant-time check of an ``Authorization: Bearer <token>`` header.

    Uses :func:`hmac.compare_digest` so a wrong token cannot be narrowed down by
    measuring how early the comparison diverges.
    """
    if not authorization:
        return False
    return hmac.compare_digest(authorization, f"Bearer {expected_token}")


@dataclass
class RateDecision:
    allowed: bool
    retry_after: int = 0


class FixedWindowRateLimiter:
    """Thread-safe per-key fixed-window limiter.

    ``limit`` requests are allowed per ``window_s`` seconds for each key (the
    client host). A limit of 0 disables limiting entirely. Per-process only —
    stated plainly rather than pretending to be distributed.
    """

    def __init__(self, limit: int, window_s: float = 60.0) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> RateDecision:
        if self.limit <= 0:
            return RateDecision(True)
        now = time.monotonic() if now is None else now
        with self._lock:
            window_start, count = self._hits.get(key, (now, 0))
            if now - window_start >= self.window_s:
                window_start, count = now, 0
            count += 1
            self._hits[key] = (window_start, count)
            if count > self.limit:
                retry = int(self.window_s - (now - window_start)) + 1
                return RateDecision(False, max(retry, 1))
        return RateDecision(True)
