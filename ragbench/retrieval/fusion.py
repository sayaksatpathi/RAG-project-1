"""Reciprocal Rank Fusion (RRF).

RRF combines ranked lists using only ranks, avoiding the fallacy of comparing
raw BM25 and cosine scores. For an item at rank r (1-based) in a list, its
contribution is 1 / (k + r). Contributions sum across lists.

Reference: Cormack, Clarke & Buettcher (2009), "Reciprocal Rank Fusion
outperforms Condorcet and individual rank learning methods."
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse ranked ID lists into one ranking.

    Duplicates within a single list are ignored after their first (best)
    occurrence. Empty lists contribute nothing. Ties break by first-seen order
    for determinism.
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    order = 0
    for ids in ranked_lists:
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ids, start=1):
            if item in seen_in_list:
                continue
            seen_in_list.add(item)
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            if item not in first_seen:
                first_seen[item] = order
                order += 1
    fused = sorted(scores.items(), key=lambda x: (-x[1], first_seen[x[0]]))
    return fused
