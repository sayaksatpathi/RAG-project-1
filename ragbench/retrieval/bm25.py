"""Transparent Okapi BM25 sparse retrieval (hand-written, unit-tested).

We implement BM25 directly rather than depending on a third-party package so the
scoring is inspectable and deterministic. Scores are BM25 scores and are NOT
comparable to cosine similarities; hybrid fusion uses ranks, not raw scores.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.ids: list[str] = []
        self.docs: list[list[str]] = []
        self.doc_len: list[int] = []
        self.df: Counter[str] = Counter()
        self.avgdl: float = 0.0

    def add(self, chunk_id: str, text: str) -> None:
        toks = tokenize(text)
        self.ids.append(chunk_id)
        self.docs.append(toks)
        self.doc_len.append(len(toks))
        for term in set(toks):
            self.df[term] += 1
        n = len(self.doc_len)
        self.avgdl = sum(self.doc_len) / n if n else 0.0

    def _idf(self, term: str) -> float:
        n = len(self.docs)
        df = self.df.get(term, 0)
        # BM25+ style idf, floored at 0 to avoid negative contributions.
        return max(0.0, math.log((n - df + 0.5) / (df + 0.5) + 1.0))

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if not self.docs:
            return []
        q_terms = tokenize(query)
        scored: list[tuple[str, float]] = []
        for i, toks in enumerate(self.docs):
            if not toks:
                scored.append((self.ids[i], 0.0))
                continue
            tf = Counter(toks)
            dl = self.doc_len[i]
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                freq = tf[term]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += self._idf(term) * (freq * (self.k1 + 1)) / denom
            scored.append((self.ids[i], score))
        # Stable sort: score desc, then insertion order for deterministic ties.
        scored.sort(key=lambda x: -x[1])
        return [(cid, s) for cid, s in scored[:top_k]]
