"""Rerankers behind a simple callable interface.

The default `HeuristicReranker` is a deterministic, offline stand-in: it
re-scores candidates by blending lexical token-overlap recall with embedding
cosine similarity to the query. It is explicitly NOT a trained cross-encoder;
it exists so the "+rerank" baseline (B3) runs reproducibly without model
weights. A real cross-encoder can be dropped in behind the same interface.
"""

from __future__ import annotations

import numpy as np

from ragbench.embeddings import EmbeddingProvider
from ragbench.models import RetrievalResult
from ragbench.retrieval.bm25 import tokenize


class HeuristicReranker:
    name = "heuristic-rerank"

    def __init__(self, embedder: EmbeddingProvider, alpha: float = 0.5) -> None:
        self.embedder = embedder
        self.alpha = alpha  # weight on lexical overlap vs embedding cosine

    def __call__(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        if not results:
            return results
        q_terms = set(tokenize(query))
        texts = [r.text for r in results]
        vecs = self.embedder.embed([query] + texts)
        q = vecs[0]
        qn = np.linalg.norm(q)
        q = q / qn if qn > 0 else q
        cosines = vecs[1:] @ q

        scored: list[tuple[float, int, RetrievalResult]] = []
        for i, r in enumerate(results):
            p_terms = set(tokenize(r.text))
            overlap = (len(q_terms & p_terms) / len(q_terms)) if q_terms else 0.0
            blended = self.alpha * overlap + (1 - self.alpha) * float(cosines[i])
            scored.append((blended, i, r))
        # Sort by blended score desc; original index breaks ties deterministically.
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [r for _, _, r in scored]
