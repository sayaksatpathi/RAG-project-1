"""Smoke + sanity tests for the evaluation harness on the real sample corpus."""

from ragbench.evaluation.harness import run_benchmark

CORPUS = "evaluation/datasets/corpus"
DATASET = "evaluation/datasets/benchmark_v1.json"


def test_harness_runs_all_baselines():
    report = run_benchmark(CORPUS, DATASET, k=5)
    names = [b["name"] for b in report["baselines"]]
    assert names == ["B0_bm25", "B1_dense", "B2_hybrid", "B3_hybrid_rerank"]
    assert report["num_cases"] == 50
    assert report["git_commit"]  # populated or 'unknown'


def test_harness_metrics_present_and_bounded():
    report = run_benchmark(CORPUS, DATASET, k=5)
    for b in report["baselines"]:
        agg = b["aggregate"]
        for key in ("recall@5", "mrr@5", "ndcg@5", "hit@5"):
            v = agg[key]
            assert v is None or 0.0 <= v <= 1.0


def test_bm25_finds_exact_identifier_case():
    # The exact-identifier query "E1042" should retrieve its document at rank 1
    # for BM25, giving perfect metrics on that category.
    report = run_benchmark(CORPUS, DATASET, k=5)
    b0 = next(b for b in report["baselines"] if b["name"] == "B0_bm25")
    assert b0["by_category"]["exact_identifier"]["hit@5"] == 1.0


def test_abstains_well_on_clearly_unanswerable():
    # Clearly out-of-corpus questions (no shared content) should abstain.
    report = run_benchmark(CORPUS, DATASET, k=5)
    b2 = next(b for b in report["baselines"] if b["name"] == "B2_hybrid")
    assert b2["by_category"]["unanswerable"]["abstain_accuracy"] >= 0.8


def test_answerable_cases_mostly_do_not_abstain():
    report = run_benchmark(CORPUS, DATASET, k=5)
    b2 = next(b for b in report["baselines"] if b["name"] == "B2_hybrid")
    # direct_fact questions share content with the corpus -> should answer.
    assert b2["by_category"]["direct_fact"]["abstain_accuracy"] >= 0.8
