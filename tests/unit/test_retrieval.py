import numpy as np

from ragbench.retrieval.bm25 import BM25Index, tokenize
from ragbench.retrieval.dense import DenseIndex
from ragbench.retrieval.fusion import reciprocal_rank_fusion


def test_bm25_ranks_relevant_doc_first():
    idx = BM25Index()
    idx.add("a", "the cat sat on the mat")
    idx.add("b", "a dog chased the ball in the park")
    idx.add("c", "quantum chromodynamics and particle physics")
    results = idx.search("dog ball park", top_k=3)
    assert results[0][0] == "b"
    assert results[0][1] > 0


def test_bm25_empty_index_and_no_match():
    assert BM25Index().search("anything", 5) == []
    idx = BM25Index()
    idx.add("a", "hello world")
    res = idx.search("zzz", 5)
    assert res[0][1] == 0.0  # no term match -> zero score


def test_bm25_tie_is_deterministic():
    idx = BM25Index()
    idx.add("a", "same words here")
    idx.add("b", "same words here")
    res = idx.search("same words", 2)
    assert [r[0] for r in res] == ["a", "b"]  # insertion order on tie


def test_dense_cosine_ranking():
    idx = DenseIndex(dim=3)
    idx.add("x", np.array([1.0, 0.0, 0.0], dtype=np.float32))
    idx.add("y", np.array([0.0, 1.0, 0.0], dtype=np.float32))
    res = idx.search(np.array([0.9, 0.1, 0.0], dtype=np.float32), top_k=2)
    assert res[0][0] == "x"


def test_dense_empty():
    assert DenseIndex(dim=4).search(np.ones(4, dtype=np.float32), 3) == []


def test_rrf_combines_and_dedupes():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]], k=60)
    ids = [i for i, _ in fused]
    # a and b appear in both lists near the top -> should outrank c and d
    assert set(ids[:2]) == {"a", "b"}
    assert "c" in ids and "d" in ids


def test_rrf_handles_empty_lists():
    assert reciprocal_rank_fusion([[], []]) == []
    assert [i for i, _ in reciprocal_rank_fusion([["a"], []])] == ["a"]


def test_tokenize_lowercases_and_splits():
    assert tokenize("Hello, WORLD-123!") == ["hello", "world", "123"]
