import math

from ragbench.evaluation.metrics import (
    hit_at_k,
    mean_ignoring_none,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
)


def test_recall_basic():
    assert recall_at_k(["a", "b", "c"], {"a", "d"}, 3) == 0.5
    assert recall_at_k(["a", "b"], {"a", "b"}, 5) == 1.0


def test_recall_dedup_before_truncation():
    # Dedup collapses duplicates first, then top-k is taken of the distinct list.
    assert recall_at_k(["a", "a", "b"], {"b"}, 2) == 1.0
    # A duplicate does not push a relevant item out of top-k.
    assert recall_at_k(["a", "a", "z"], {"z"}, 2) == 1.0
    # But a genuinely lower-ranked relevant item beyond k is missed.
    assert recall_at_k(["x", "y", "b"], {"b"}, 2) == 0.0


def test_no_relevant_returns_none():
    assert recall_at_k(["a"], set(), 3) is None
    assert mrr_at_k(["a"], set(), 3) is None
    assert ndcg_at_k(["a"], set(), 3) is None
    assert hit_at_k(["a"], set(), 3) is None


def test_empty_retrieval_with_relevant_is_zero():
    assert recall_at_k([], {"a"}, 3) == 0.0
    assert mrr_at_k([], {"a"}, 3) == 0.0
    assert hit_at_k([], {"a"}, 3) == 0.0


def test_mrr_first_relevant_position():
    assert mrr_at_k(["x", "a", "y"], {"a"}, 5) == 0.5
    assert mrr_at_k(["a", "x"], {"a"}, 5) == 1.0
    assert mrr_at_k(["x", "y"], {"a"}, 5) == 0.0


def test_hit():
    assert hit_at_k(["a", "b"], {"b"}, 2) == 1.0
    assert hit_at_k(["a", "b"], {"z"}, 2) == 0.0


def test_ndcg_perfect_and_partial():
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 2) == 1.0
    # one relevant at rank 2 -> dcg=1/log2(3); idcg=1/log2(2)=1
    val = ndcg_at_k(["x", "a"], {"a"}, 2)
    assert math.isclose(val, (1 / math.log2(3)) / 1.0, rel_tol=1e-9)


def test_ndcg_graded():
    grades = {"a": 3.0, "b": 1.0}
    # ideal orders a then b; put b first to make it imperfect
    val = ndcg_at_k(["b", "a"], {"a", "b"}, 2, grades=grades)
    assert 0 < val < 1


def test_ndcg_graded_differs_from_binary():
    # Same ranking, same relevant set, but graded relevance penalizes putting the
    # low-grade doc first more than binary does.
    ranking, rel = ["b", "a"], {"a", "b"}
    binary = ndcg_at_k(ranking, rel, 2)
    graded = ndcg_at_k(ranking, rel, 2, grades={"a": 3.0, "b": 1.0})
    assert binary == 1.0  # both relevant, binary gains equal -> perfect
    assert graded < binary  # graded is sensitive to the primary doc's position


def test_mean_ignoring_none():
    assert mean_ignoring_none([1.0, None, 0.0]) == 0.5
    assert mean_ignoring_none([None, None]) is None
