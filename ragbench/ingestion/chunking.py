"""Deterministic, versioned word-window chunking with stable IDs.

Chunk IDs are derived from the document ID, the chunk sequence, and the index
version, so the same document re-chunked under the same configuration yields
identical IDs (idempotent ingestion), while a changed configuration yields
different IDs (forcing a deliberate re-index).
"""

from __future__ import annotations

import hashlib
import re

_WORD_RE = re.compile(r"\S+")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_id(document_id: str, sequence: int, index_version: str) -> str:
    h = hashlib.sha256(f"{document_id}|{sequence}|{index_version}".encode()).hexdigest()
    return f"c_{h[:16]}"


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping word windows.

    Raises ValueError on invalid configuration. An empty/whitespace input
    yields an empty list rather than a spurious empty chunk.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    words = _WORD_RE.findall(text)
    if not words:
        return []

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if window:
            chunks.append(" ".join(window))
        if start + chunk_size >= len(words):
            break
    return chunks
