"""Gate service: pin an approved baseline, evaluate a candidate, demo a regression.

A "configuration" here is captured by the production strategy the gate inspects
(e.g. ``B2_hybrid``) plus the pipeline Config used to run the harness. The gate
runs the harness on a candidate configuration, extracts that strategy's
aggregate metrics, and compares them to a pinned approved-baseline file using
the versioned policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ragbench.config import Config
from ragbench.evaluation.harness import run_benchmark
from ragbench.gate.policy import GateDecision, Policy, evaluate_gate, load_policy

DEFAULT_BASELINE_PATH = "evaluation/baselines/approved_baseline.json"


@dataclass
class CandidateSpec:
    """A candidate configuration to evaluate. ``production_strategy`` names the
    baseline (B0..B4) whose metrics represent the production system."""

    production_strategy: str = "B2_hybrid"
    config: Config | None = None


def _strategy_aggregate(report: dict, strategy_name: str) -> dict:
    for b in report["baselines"]:
        if b["name"] == strategy_name:
            return b["aggregate"]
    raise KeyError(f"strategy {strategy_name} not in report")


def save_baseline(corpus: str, dataset: str, production_strategy: str,
                  out_path: str = DEFAULT_BASELINE_PATH, config: Config | None = None) -> dict:
    report = run_benchmark(corpus, dataset, config=config)
    agg = _strategy_aggregate(report, production_strategy)
    baseline = {
        "production_strategy": production_strategy,
        "aggregate": agg,
        "k": report["k"],
        "index_version": report["config"]["index_version"],
        "dataset_version": report["dataset_version"],
        "git_commit": report["git_commit"],
        "run_id": report["run_id"],
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline


def load_baseline(path: str = DEFAULT_BASELINE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass
class GateResult:
    decision: GateDecision
    candidate_strategy: str
    baseline_strategy: str
    condition_warnings: list[str]

    def to_dict(self) -> dict:
        d = self.decision.to_dict()
        d["candidate_strategy"] = self.candidate_strategy
        d["baseline_strategy"] = self.baseline_strategy
        d["condition_warnings"] = self.condition_warnings
        return d


def check_candidate(
    corpus: str,
    dataset: str,
    candidate: CandidateSpec,
    policy_path: str = "evaluation/gate_policy.json",
    baseline_path: str = DEFAULT_BASELINE_PATH,
) -> GateResult:
    policy: Policy = load_policy(policy_path)
    baseline = load_baseline(baseline_path)
    report = run_benchmark(corpus, dataset, k=policy.k, config=candidate.config)
    cand_agg = _strategy_aggregate(report, candidate.production_strategy)

    condition_warnings: list[str] = []
    if report["dataset_version"] != baseline.get("dataset_version"):
        condition_warnings.append("dataset_version differs from the approved baseline")
    if report["config"]["index_version"] != baseline.get("index_version"):
        condition_warnings.append("index_version differs from the approved baseline")

    decision = evaluate_gate(baseline["aggregate"], cand_agg, policy)
    return GateResult(
        decision=decision,
        candidate_strategy=candidate.production_strategy,
        baseline_strategy=baseline["production_strategy"],
        condition_warnings=condition_warnings,
    )


def regression_demo(corpus: str, dataset: str,
                    policy_path: str = "evaluation/gate_policy.json",
                    baseline_path: str = DEFAULT_BASELINE_PATH) -> dict:
    """Demonstrate the gate rejecting a deliberately degraded candidate and
    accepting a healthy one.

    The approved baseline is pinned to the strong hybrid configuration. The
    regression candidate switches the production strategy to dense retrieval,
    which measurably underperforms on this corpus; the gate must FAIL it. The
    healthy candidate keeps hybrid and must PASS. Both decisions derive solely
    from measured metrics vs the policy.
    """
    save_baseline(corpus, dataset, production_strategy="B2_hybrid",
                  out_path=baseline_path)
    degraded = check_candidate(
        corpus, dataset, CandidateSpec(production_strategy="B1_dense"),
        policy_path=policy_path, baseline_path=baseline_path,
    )
    healthy = check_candidate(
        corpus, dataset, CandidateSpec(production_strategy="B2_hybrid"),
        policy_path=policy_path, baseline_path=baseline_path,
    )
    return {
        "degraded_candidate": degraded.to_dict(),
        "healthy_candidate": healthy.to_dict(),
    }
