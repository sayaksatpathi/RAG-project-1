"""Structured JSON logging with request/trace correlation.

Logs are emitted as one JSON object per line. We never log raw query text,
document content, credentials, or personal data — only safe aggregate fields
(e.g. query length, not the query). Request IDs correlate a request across log
lines.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Structured extras attached via logger.info(..., extra={"fields": {...}}).
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("ragbench")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str = "ragbench") -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def new_request_id() -> str:
    return str(uuid.uuid4())
