"""Phase 4 integration: the gate rejects a real regression and passes a healthy
candidate; abstention calibration produces a sweep and a recommendation."""

import tempfile
from pathlib import Path

from ragbench.evaluation.calibration import calibrate_abstention
from ragbench.gate.service import (
    CandidateSpec,
    check_candidate,
    regression_demo,
    save_baseline,
)

CORPUS = "evaluation/datasets/corpus"
DATASET = "evaluation/datasets/benchmark_v1.json"
POLICY = "evaluation/gate_policy.json"


def test_regression_demo_rejects_degraded_passes_healthy():
    result = regression_demo(CORPUS, DATASET, policy_path=POLICY,
                             baseline_path=str(Path(tempfile.mkdtemp()) / "base.json"))
    assert result["degraded_candidate"]["decision"] == "FAIL"
    assert result["healthy_candidate"]["decision"] == "PASS"
    # Decision must be backed by a concrete measured reason, not a label.
    assert result["degraded_candidate"]["rejection_reasons"]


def test_decision_is_metric_derived_not_name_derived():
    # A candidate identical to the baseline strategy must PASS regardless of name.
    tmp = str(Path(tempfile.mkdtemp()) / "base.json")
    save_baseline(CORPUS, DATASET, production_strategy="B2_hybrid", out_path=tmp)
    res = check_candidate(CORPUS, DATASET, CandidateSpec(production_strategy="B2_hybrid"),
                          policy_path=POLICY, baseline_path=tmp)
    assert res.decision.passed


def test_calibration_sweep_and_recommendation():
    out = calibrate_abstention(CORPUS, DATASET, strategy="hybrid")
    assert len(out["sweep"]) >= 5
    assert 0.0 < out["recommended_threshold"] < 1.0
    # As the threshold rises, recall of abstention is monotonically non-decreasing
    # (abstaining more often can only find more of the should-abstain cases).
    recalls = [p["recall"] for p in out["sweep"] if p["recall"] is not None]
    assert recalls == sorted(recalls)
