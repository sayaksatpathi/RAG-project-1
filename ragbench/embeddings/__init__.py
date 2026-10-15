"""Embedding providers behind a narrow Protocol.

The default `FakeEmbeddingProvider` is deterministic and offline: it hashes
token n-grams into a fixed-dimension vector and L2-normalizes. It is NOT a
semantic model, but it is stable, dependency-free, and good enough to exercise
the dense-retrieval path and tests reproducibly. A real sentence-transformers
provider is available as an optional extra.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from ragbench.config import Config


class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


# Minimal English stopword/structural set. Dropping these before hashing makes
# the (non-semantic) fake embedding reflect CONTENT overlap rather than shared
# function words, so unrelated questions score low and abstention works. A real
# embedding model would not need this; it is a property of the fake stand-in.
_STOPWORDS = frozenset(
    "a an the of to in on at for and or is are was were be been being do does "
    "did what which who whom how when where why this that these those it its as "
    "with from by about into over under".split()
)


class FakeEmbeddingProvider:
    def __init__(self, dim: int = 256, model: str = "fake") -> None:
        self.dim = dim
        self.name = f"fake:{model}:d{dim}"

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        tokens = [t.strip(".,;:!?'\"()[]") for t in text.lower().split()]
        tokens = [t for t in tokens if t and t not in _STOPWORDS]
        if not tokens:
            return v
        # Unigrams and bigrams hashed into buckets with signed counts.
        grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        for g in grams:
            h = int.from_bytes(hashlib.md5(g.encode()).digest()[:8], "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 1) & 1 else -1.0
            v[idx] += sign
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else v

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._vec(t) for t in texts]) if texts else np.zeros((0, self.dim))


def build_embedding_provider(config: Config) -> EmbeddingProvider:
    if config.embedding_provider == "fake":
        return FakeEmbeddingProvider(dim=config.embedding_dim, model=config.embedding_model)
    if config.embedding_provider == "sentence-transformers":  # pragma: no cover - optional
        from ragbench.embeddings.sentence_transformers_provider import SentenceTransformerProvider

        return SentenceTransformerProvider(config.embedding_model)
    raise ValueError(f"unknown embedding provider: {config.embedding_provider}")
