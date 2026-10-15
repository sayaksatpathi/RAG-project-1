"""Core domain models shared across the pipeline.

These are plain dataclasses (storage/transport neutral). The API layer defines
its own pydantic request/response schemas in ragbench/api.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Document:
    id: str
    filename: str
    content_hash: str
    parser_version: str
    status: str = "indexed"
    num_chunks: int = 0
    created_at: str = ""


@dataclass
class Chunk:
    id: str
    document_id: str
    sequence: int
    text: str
    content_hash: str
    index_version: str = ""


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    rank: int
    score: float
    strategy: str
    text: str = ""
    index_version: str = ""


@dataclass
class Citation:
    chunk_id: str
    document_id: str
    valid: bool


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    retrieval_strategy: str = ""
    retrieved_passage_ids: list[str] = field(default_factory=list)
    abstained: bool = False
    warnings: list[str] = field(default_factory=list)
    model: str = ""
    index_version: str = ""
