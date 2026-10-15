"""Abstention threshold calibration.

Rather than pick an arbitrary abstention threshold, we sweep candidate
thresholds over the labeled dataset, compute abstention precision/recall/F1 at
each, and select a recommended threshold. This exposes the precision/recall
trade-off honestly instead of asserting a single magic number.

Positive class = "should abstain" (expected_abstention == True).
"""

from __future__ import annotations

from dataclasses import dataclass

from ragbench.config import Config
from ragbench.evaluation.harness import EvalConfig, Harness, load_dataset


@dataclass
class SweepPoint:
    threshold: float
    precision: float | None
    recall: float | None
    f1: float | None
    tp: int
    fp: int
    fn: int
    tn: int


def _prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision and recall and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0 if (precision is not None and recall is not None) else None
    return precision, recall, f1


def calibrate_abstention(
    corpus_dir: str,
    dataset_path: str,
    strategy: str = "hybrid",
    thresholds: list[float] | None = None,
    config: Config | None = None,
) -> dict:
    thresholds = thresholds or [round(x / 100, 2) for x in range(5, 60, 5)]
    harness = Harness(EvalConfig(corpus_dir, dataset_path), config=config)
    harness._ingest_corpus()
    _, cases = load_dataset(dataset_path)

    # Precompute each case's evidence score once (independent of threshold).
    scored = []
    for case in cases:
        results, _, _ = harness._ranked_docs(case.question, strategy, False)
        evidence = harness.pipeline._evidence_score(case.question, results)
        scored.append((evidence, case.expected_abstention))

    sweep: list[SweepPoint] = []
    for thr in thresholds:
        tp = fp = fn = tn = 0
        for evidence, expect_abstain in scored:
            abstained = evidence < thr
            if expect_abstain and abstained:
                tp += 1
            elif expect_abstain and not abstained:
                fn += 1
            elif not expect_abstain and abstained:
                fp += 1
            else:
                tn += 1
        p, r, f1 = _prf(tp, fp, fn)
        sweep.append(SweepPoint(thr, p, r, f1, tp, fp, fn, tn))

    # Recommend: highest F1, breaking ties toward higher precision then lower
    # threshold (prefer not abstaining on answerable questions).
    def key(pt: SweepPoint):
        return (pt.f1 or -1.0, pt.precision or -1.0, -pt.threshold)

    best = max(sweep, key=key)
    return {
        "strategy": strategy,
        "num_cases": len(cases),
        "index_version": harness.config.index_version,
        "sweep": [vars(p) for p in sweep],
        "recommended_threshold": best.threshold,
        "recommended_precision": best.precision,
        "recommended_recall": best.recall,
        "recommended_f1": best.f1,
    }
