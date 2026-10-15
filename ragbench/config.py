"""Application configuration, loaded from environment with documented defaults.

The defaults constitute the deterministic offline path: SQLite storage, fake
embeddings, and the mock generation provider. Nothing here requires a paid
service or a downloaded model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    storage: str = _get("RAGBENCH_STORAGE", "sqlite")
    sqlite_path: str = _get("RAGBENCH_SQLITE_PATH", "data/ragbench.db")
    postgres_dsn: str | None = os.environ.get("RAGBENCH_POSTGRES_DSN")

    embedding_provider: str = _get("RAGBENCH_EMBEDDING_PROVIDER", "fake")
    embedding_model: str = _get("RAGBENCH_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embedding_dim: int = int(_get("RAGBENCH_EMBEDDING_DIM", "256"))

    llm_provider: str = _get("RAGBENCH_LLM_PROVIDER", "mock")
    openai_api_key: str | None = os.environ.get("RAGBENCH_OPENAI_API_KEY")
    openai_base_url: str = _get("RAGBENCH_OPENAI_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = _get("RAGBENCH_LLM_MODEL", "gpt-4o-mini")

    top_k: int = int(_get("RAGBENCH_TOP_K", "5"))
    rrf_k: int = int(_get("RAGBENCH_RRF_K", "60"))
    abstain_min_score: float = float(_get("RAGBENCH_ABSTAIN_MIN_SCORE", "0.15"))

    chunk_size: int = int(_get("RAGBENCH_CHUNK_SIZE", "120"))  # words
    chunk_overlap: int = int(_get("RAGBENCH_CHUNK_OVERLAP", "24"))

    api_token: str = _get("RAGBENCH_API_TOKEN", "dev-local-token")

    @property
    def index_version(self) -> str:
        """Identifier that changes when embedding/chunk config changes.

        Vectors built under a different index version must not be mixed.
        """
        return (
            f"{self.embedding_provider}:{self.embedding_model}"
            f":d{self.embedding_dim}:c{self.chunk_size}:o{self.chunk_overlap}"
        )


def load_config() -> Config:
    return Config()
