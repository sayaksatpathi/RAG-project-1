"""Quality-gate policy and evaluator.

The decision is derived purely from measured metrics and the versioned policy —
never from a test name or a hardcoded expected outcome. Thresholds live in a
versioned JSON policy file (`evaluation/gate_policy.json`), not in source.

Two constraint types:
  * ``regression``: candidate may not fall more than ``max_drop`` below the
    approved baseline (for higher-is-better metrics).
  * ``min_absolute``: candidate must be at least ``min``.

Metrics are addressed by dotted paths into a baseline's ``aggregate`` block,
e.g. ``recall@5`` or ``abstention.precision``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Policy:
    policy_version: str
    k: int
    hard_gates: dict
    warning_metrics: dict = field(default_factory=dict)


def load_policy(path: str) -> Policy:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Policy(
        policy_version=data["policy_version"],
        k=data["k"],
        hard_gates=data.get("hard_gates", {}),
        warning_metrics=data.get("warning_metrics", {}),
    )


@dataclass
class GateCheck:
    metric: str
    type: str
    candidate: float | None
    baseline: float | None
    threshold: float
    passed: bool
    hard: bool
    reason: str


@dataclass
class GateDecision:
    passed: bool
    checks: list[GateCheck]
    warnings: list[GateCheck]

    @property
    def failures(self) -> list[GateCheck]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        def c2d(c: GateCheck) -> dict:
            return {
                "metric": c.metric, "type": c.type, "candidate": c.candidate,
                "baseline": c.baseline, "threshold": c.threshold, "passed": c.passed,
                "hard": c.hard, "reason": c.reason,
            }

        return {
            "decision": "PASS" if self.passed else "FAIL",
            "hard_checks": [c2d(c) for c in self.checks],
            "warnings": [c2d(c) for c in self.warnings],
            "rejection_reasons": [c.reason for c in self.failures],
        }


def _lookup(aggregate: dict, dotted: str) -> float | None:
    cur: object = aggregate
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur if isinstance(cur, (int, float)) else None


def _check(metric: str, spec: dict, cand: dict, base: dict, hard: bool) -> GateCheck:
    ctype = spec["type"]
    c_val = _lookup(cand, metric)
    if ctype == "min_absolute":
        thr = float(spec["min"])
        if c_val is None:
            return GateCheck(metric, ctype, None, None, thr, False, hard,
                             f"{metric}: candidate value unavailable")
        passed = c_val >= thr
        reason = (f"{metric}={c_val:.3f} "
                  f"{'>=' if passed else '<'} min {thr:.3f}")
        return GateCheck(metric, ctype, c_val, None, thr, passed, hard, reason)
    if ctype == "regression":
        max_drop = float(spec["max_drop"])
        b_val = _lookup(base, metric)
        if c_val is None or b_val is None:
            return GateCheck(metric, ctype, c_val, b_val, max_drop, False, hard,
                             f"{metric}: candidate or baseline value unavailable")
        drop = b_val - c_val
        passed = drop <= max_drop
        reason = (f"{metric}: candidate {c_val:.3f} vs baseline {b_val:.3f} "
                  f"(drop {drop:+.3f}, max allowed {max_drop:.3f}) "
                  f"-> {'ok' if passed else 'REGRESSION'}")
        return GateCheck(metric, ctype, c_val, b_val, max_drop, passed, hard, reason)
    raise ValueError(f"unknown constraint type: {ctype}")


def evaluate_gate(baseline_aggregate: dict, candidate_aggregate: dict,
                  policy: Policy) -> GateDecision:
    checks = [
        _check(m, spec, candidate_aggregate, baseline_aggregate, hard=True)
        for m, spec in policy.hard_gates.items()
    ]
    warnings = [
        _check(m, spec, candidate_aggregate, baseline_aggregate, hard=False)
        for m, spec in policy.warning_metrics.items()
    ]
    passed = all(c.passed for c in checks)
    return GateDecision(passed=passed, checks=checks, warnings=warnings)
