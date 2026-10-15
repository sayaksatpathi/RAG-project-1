"""Dense vector retrieval via brute-force cosine over normalized embeddings.

Brute force is appropriate at the corpus sizes this project targets and keeps
the offline path dependency-free (no ANN index). An ANN backend (pgvector,
FAISS) is a documented optional extension behind the same interface.
"""

from __future__ import annotations

import numpy as np


class DenseIndex:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.ids: list[str] = []
        self._matrix: np.ndarray = np.zeros((0, dim), dtype=np.float32)

    def add(self, chunk_id: str, vector: np.ndarray) -> None:
        if vector.shape != (self.dim,):
            raise ValueError(f"expected vector of dim {self.dim}, got {vector.shape}")
        self.ids.append(chunk_id)
        self._matrix = np.vstack([self._matrix, vector.astype(np.float32)])

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        if not self.ids:
            return []
        q = query_vector.astype(np.float32)
        qn = np.linalg.norm(q)
        if qn > 0:
            q = q / qn
        sims = self._matrix @ q  # rows are already L2-normalized
        order = np.argsort(-sims, kind="stable")[:top_k]
        return [(self.ids[i], float(sims[i])) for i in order]
