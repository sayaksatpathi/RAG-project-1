"""Optional sentence-transformers embedding provider.

This module always imports cleanly; the heavy `sentence-transformers` dependency
is imported lazily inside the constructor so that merely having this file does
not require the package or trigger a model download. If the package is absent, a
clear, actionable error is raised instead of a confusing ModuleNotFoundError
about RAGBench's own modules.

Install with: pip install "ragbench[ml]"  (or pip install sentence-transformers)
Model weights are downloaded on first use by sentence-transformers and cached by
it; this is the one place RAGBench may touch the network, and only when this
provider is explicitly selected.
"""

from __future__ import annotations

import numpy as np


class SentenceTransformerProvider:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised only without the dep
            raise RuntimeError(
                "RAGBENCH_EMBEDDING_PROVIDER=sentence-transformers requires the "
                "optional 'sentence-transformers' package. Install it with "
                '`pip install "ragbench[ml]"` or use the default fake provider.'
            ) from exc
        self._model = SentenceTransformer(model_name)
        self.name = f"sentence-transformers:{model_name}"
        # Dimensionality is defined by the model, not by config.
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return vecs.astype(np.float32)
