"""Hybrid retriever orchestrating sparse, dense, and fused strategies.

Strategies: "bm25", "dense", "hybrid" (RRF of the two). Each returns a list of
RetrievalResult preserving id, rank, strategy, score, and index version. A
reranking hook is provided as an optional, documented extension point.
"""

from __future__ import annotations

from collections.abc import Callable

from ragbench.embeddings import EmbeddingProvider
from ragbench.models import RetrievalResult
from ragbench.retrieval.bm25 import BM25Index
from ragbench.retrieval.dense import DenseIndex
from ragbench.retrieval.fusion import reciprocal_rank_fusion

Reranker = Callable[[str, list[RetrievalResult]], list[RetrievalResult]]


class HybridRetriever:
    def __init__(
        self,
        bm25: BM25Index,
        dense: DenseIndex,
        embedder: EmbeddingProvider,
        texts: dict[str, str],
        doc_of: dict[str, str],
        index_version: str,
        rrf_k: int = 60,
        reranker: Reranker | None = None,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.embedder = embedder
        self.texts = texts
        self.doc_of = doc_of
        self.index_version = index_version
        self.rrf_k = rrf_k
        self.reranker = reranker

    def _results(self, ranked: list[tuple[str, float]], strategy: str) -> list[RetrievalResult]:
        out = []
        for rank, (cid, score) in enumerate(ranked, start=1):
            out.append(
                RetrievalResult(
                    chunk_id=cid,
                    document_id=self.doc_of.get(cid, ""),
                    rank=rank,
                    score=float(score),
                    strategy=strategy,
                    text=self.texts.get(cid, ""),
                    index_version=self.index_version,
                )
            )
        return out

    def retrieve(
        self, query: str, strategy: str, top_k: int, use_reranker: bool = False
    ) -> list[RetrievalResult]:
        if strategy == "bm25":
            results = self._results(self.bm25.search(query, top_k), "bm25")
        elif strategy == "dense":
            qv = self.embedder.embed([query])[0]
            results = self._results(self.dense.search(qv, top_k), "dense")
        elif strategy == "hybrid":
            pool = max(top_k * 4, 20)
            bm = [cid for cid, _ in self.bm25.search(query, pool)]
            qv = self.embedder.embed([query])[0]
            dn = [cid for cid, _ in self.dense.search(qv, pool)]
            fused = reciprocal_rank_fusion([bm, dn], k=self.rrf_k)[:top_k]
            results = self._results(fused, "hybrid")
        else:
            raise ValueError(f"unknown strategy: {strategy}")

        if use_reranker and self.reranker is not None:
            results = self.reranker(query, results)
            for rank, r in enumerate(results, start=1):
                r.rank = rank
                r.strategy = f"{results[0].strategy}+rerank" if results else r.strategy
        return results
