from ragbench.gate.policy import Policy, evaluate_gate


def _policy():
    return Policy(
        policy_version="test",
        k=5,
        hard_gates={
            "recall@5": {"type": "regression", "max_drop": 0.03},
            "ndcg@5": {"type": "min_absolute", "min": 0.50},
        },
        warning_metrics={"abstention.recall": {"type": "min_absolute", "min": 0.60}},
    )


def test_passes_when_candidate_matches_baseline():
    base = {"recall@5": 1.0, "ndcg@5": 0.96, "abstention": {"recall": 0.5}}
    cand = {"recall@5": 1.0, "ndcg@5": 0.96, "abstention": {"recall": 0.5}}
    d = evaluate_gate(base, cand, _policy())
    assert d.passed
    # warning fired but does not block
    assert any(not w.passed for w in d.warnings)


def test_fails_on_recall_regression():
    base = {"recall@5": 1.0, "ndcg@5": 0.96}
    cand = {"recall@5": 0.90, "ndcg@5": 0.96}  # drop 0.10 > 0.03
    d = evaluate_gate(base, cand, _policy())
    assert not d.passed
    assert any("REGRESSION" in c.reason for c in d.failures)


def test_fails_on_min_absolute():
    base = {"recall@5": 1.0, "ndcg@5": 0.96}
    cand = {"recall@5": 1.0, "ndcg@5": 0.40}  # below min 0.50
    d = evaluate_gate(base, cand, _policy())
    assert not d.passed
    assert any(c.metric == "ndcg@5" and not c.passed for c in d.checks)


def test_missing_metric_fails_closed():
    base = {"recall@5": 1.0, "ndcg@5": 0.96}
    cand = {"recall@5": 1.0}  # ndcg missing
    d = evaluate_gate(base, cand, _policy())
    assert not d.passed


def test_decision_dict_shape():
    d = evaluate_gate({"recall@5": 1.0, "ndcg@5": 0.9},
                      {"recall@5": 1.0, "ndcg@5": 0.9}, _policy())
    out = d.to_dict()
    assert out["decision"] == "PASS"
    assert "hard_checks" in out and "rejection_reasons" in out
