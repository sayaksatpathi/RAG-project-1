"""Interpretable query-aware retrieval routing.

The router inspects cheap, interpretable query features and selects a retrieval
strategy, falling back to a strong default (fixed hybrid) whenever it is
uncertain, lacks expected features, or errors. This is a hand-specified
heuristic policy — it is explicitly NOT a trained model (see DECISIONS/research
docs). A learned router is a documented future extension.

Decision policy (ordered; first match wins):
  1. exact identifier / error code present            -> bm25
  2. query contains a rare corpus term (low doc freq) -> bm25
  3. long, paraphrase-style natural-language question -> dense
  4. otherwise (uncertain)                            -> hybrid  [fallback]

Rarity is judged against the live BM25 index's document frequencies, so the
router adapts to the indexed corpus rather than a fixed word list.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ragbench.embeddings import _STOPWORDS
from ragbench.retrieval.bm25 import BM25Index, tokenize

# A token that mixes letters and digits (E1042, GPT4, v2) or an all-caps acronym
# of length >= 2 is treated as an exact identifier / code.
_ALNUM_MIX = re.compile(r"(?=[a-z]*\d)(?=\d*[a-z])[a-z\d]+", re.IGNORECASE)
_ACRONYM = re.compile(r"\b[A-Z]{2,}\b")


@dataclass
class QueryFeatures:
    content_tokens: list[str]
    has_exact_identifier: bool
    rare_terms: list[str]
    num_content_tokens: int
    is_question: bool


@dataclass
class RoutingDecision:
    strategy: str
    rule: str
    fallback: bool
    features: QueryFeatures


_QUESTION_STARTS = {"how", "why", "describe", "explain", "compare"}


class InterpretableRouter:
    def __init__(
        self,
        bm25: BM25Index,
        rare_doc_freq_max: int | None = None,
        long_query_tokens: int = 5,
    ) -> None:
        self.bm25 = bm25
        n = max(1, len(bm25.doc_len))
        # "rare" = appears in at most ~20% of documents (at least 1).
        self.rare_doc_freq_max = (
            rare_doc_freq_max if rare_doc_freq_max is not None else max(1, math.ceil(0.2 * n))
        )
        self.long_query_tokens = long_query_tokens

    def features(self, query: str) -> QueryFeatures:
        raw_tokens = tokenize(query)
        content = [t for t in raw_tokens if len(t) > 1 and t not in _STOPWORDS]
        has_id = bool(_ALNUM_MIX.search(query)) or bool(_ACRONYM.search(query))
        rare = [
            t for t in content
            if 0 < self.bm25.df.get(t, 0) <= self.rare_doc_freq_max
        ]
        first = raw_tokens[0] if raw_tokens else ""
        is_question = query.strip().endswith("?") or first in _QUESTION_STARTS
        return QueryFeatures(
            content_tokens=content,
            has_exact_identifier=has_id,
            rare_terms=rare,
            num_content_tokens=len(content),
            is_question=is_question,
        )

    def route(self, query: str) -> RoutingDecision:
        try:
            f = self.features(query)
        except Exception:  # noqa: BLE001 - never let routing break the request
            dummy = QueryFeatures([], False, [], 0, False)
            return RoutingDecision("hybrid", "error_fallback", True, dummy)

        if f.has_exact_identifier:
            return RoutingDecision("bm25", "exact_identifier", False, f)
        if f.rare_terms:
            return RoutingDecision("bm25", "rare_term", False, f)
        if f.is_question and f.num_content_tokens >= self.long_query_tokens:
            return RoutingDecision("dense", "long_semantic", False, f)
        return RoutingDecision("hybrid", "fallback", True, f)
