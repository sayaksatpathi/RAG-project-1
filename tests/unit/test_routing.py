from ragbench.retrieval.bm25 import BM25Index
from ragbench.routing import InterpretableRouter


def _index():
    idx = BM25Index()
    # 10 docs; "fusion" is rare (1 doc), "retrieval" is common (many docs).
    idx.add("d_fusion", "reciprocal rank fusion combines ranked lists")
    for i in range(9):
        idx.add(f"d_{i}", "retrieval system retrieval method retrieval query")
    return idx


def test_exact_identifier_routes_to_bm25():
    r = InterpretableRouter(_index())
    d = r.route("What causes error code E1042?")
    assert d.strategy == "bm25" and d.rule == "exact_identifier" and not d.fallback


def test_acronym_routes_to_bm25():
    r = InterpretableRouter(_index())
    assert r.route("What is BM25?").strategy == "bm25"


def test_rare_term_routes_to_bm25():
    r = InterpretableRouter(_index())
    d = r.route("explain fusion")
    assert d.strategy == "bm25" and d.rule == "rare_term"


def test_long_question_routes_to_dense():
    r = InterpretableRouter(_index())
    # long natural-language question, no identifier, no rare term
    d = r.route("how does a retrieval system method retrieve a query result today?")
    assert d.strategy == "dense" and d.rule == "long_semantic"


def test_uncertain_falls_back_to_hybrid():
    r = InterpretableRouter(_index())
    d = r.route("retrieval system")  # short, common terms only
    assert d.strategy == "hybrid" and d.fallback


def test_rare_doc_freq_threshold_scales_with_corpus():
    r = InterpretableRouter(_index())
    assert r.rare_doc_freq_max == 2  # ceil(0.2 * 10)
