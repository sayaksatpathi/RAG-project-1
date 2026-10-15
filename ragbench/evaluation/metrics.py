"""Ranking metrics with explicit edge-case behavior.

All functions take a ranked list of retrieved IDs (best first) and a set of
relevant IDs. Edge behavior is defined explicitly:

- No relevant IDs: metrics return ``None`` (undefined — the case contributes
  nothing to a mean rather than a misleading 0.0 or 1.0). Callers that aggregate
  must skip ``None``.
- Empty retrieval with relevant IDs present: metrics return 0.0.
- Duplicate IDs in the ranked list: only the first (best) occurrence counts.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def _dedup(ranked: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in ranked:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    topk = _dedup(ranked)[:k]
    found = len(set(topk) & relevant)
    return found / len(relevant)


def hit_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    topk = _dedup(ranked)[:k]
    return 1.0 if set(topk) & relevant else 0.0


def mrr_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    for rank, item in enumerate(_dedup(ranked)[:k], start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    ranked: Sequence[str],
    relevant: set[str],
    k: int,
    grades: dict[str, float] | None = None,
) -> float | None:
    """nDCG@k with binary gains by default, or graded gains via ``grades``.

    Relevance gain defaults to 1.0 for IDs in ``relevant``; if ``grades`` is
    given, each relevant ID uses its grade. The ideal ranking orders all
    relevant items by descending gain.
    """
    if not relevant:
        return None
    topk = _dedup(ranked)[:k]

    def gain(item: str) -> float:
        if item not in relevant:
            return 0.0
        return grades.get(item, 1.0) if grades else 1.0

    dcg = sum(gain(item) / math.log2(i + 1) for i, item in enumerate(topk, start=1))
    ideal_gains = sorted(
        ((grades.get(r, 1.0) if grades else 1.0) for r in relevant), reverse=True
    )[:k]
    idcg = sum(g / math.log2(i + 1) for i, g in enumerate(ideal_gains, start=1))
    return (dcg / idcg) if idcg > 0 else 0.0


def mean_ignoring_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None
