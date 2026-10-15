"""Text extraction and normalization for supported source types.

Supported: .txt, .md, and text-based .pdf (best-effort). Uploaded files are
treated as untrusted data: we never execute content, fetch embedded URLs, or
run macros. Scanned/image-only PDFs are NOT OCR'd (out of scope for the core
slice); such a PDF yields empty text and is rejected by the caller.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

PARSER_VERSION = "1.0.0"
SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".pdf"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB upload ceiling (DoS guard)


class ParseError(ValueError):
    """Raised when a file cannot be parsed into meaningful text."""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of blank lines and trailing whitespace; keep paragraph breaks.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_text(raw: str) -> str:
    cleaned = normalize(raw)
    if not cleaned:
        raise ParseError("no meaningful text content")
    return cleaned


def _parse_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # optional dependency
    except ImportError as exc:  # pragma: no cover - env dependent
        raise ParseError(
            "PDF support requires the optional 'pypdf' package (pip install pypdf)"
        ) from exc
    import io

    reader = PdfReader(io.BytesIO(data))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(parts)


def parse_bytes(data: bytes, suffix: str) -> str:
    if len(data) > MAX_BYTES:
        raise ParseError(f"file exceeds {MAX_BYTES} byte limit")
    suffix = suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ParseError(f"unsupported file type: {suffix}")
    if suffix == ".pdf":
        raw = _parse_pdf(data)
    else:
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParseError("file is not valid UTF-8 text") from exc
    return parse_text(raw)


def parse_file(path: str | Path) -> str:
    p = Path(path)
    if not p.is_file():
        raise ParseError(f"not a file: {p}")
    return parse_bytes(p.read_bytes(), p.suffix)
