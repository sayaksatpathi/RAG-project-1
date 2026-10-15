# AI Quality Gate

The quality gate compares a **candidate** retrieval/answer configuration against
a pinned **approved baseline** using versioned thresholds, and emits a
machine-readable PASS/FAIL decision with explicit reasons. The decision is
derived purely from measured metrics and the policy file — never from a test
name or a hardcoded expected outcome.

## Policy

Thresholds live in [`evaluation/gate_policy.json`](../evaluation/gate_policy.json)
(versioned, not in source). Two constraint types:

- **regression** — candidate may not fall more than `max_drop` below the
  approved baseline (higher-is-better metrics).
- **min_absolute** — candidate must be at least `min`.

Current policy `v1.0.0`:

| Metric | Type | Threshold | Gate |
|---|---|---|---|
| recall@5 | regression | max drop 0.03 | hard |
| mrr@5 | regression | max drop 0.05 | hard |
| ndcg@5 | min_absolute | ≥ 0.50 | hard |
| abstention.precision | min_absolute | ≥ 0.90 | hard |
| abstention.recall | min_absolute | ≥ 0.60 | warning only |

Regression tolerances are deliberately generous to absorb small-dataset
variance on the 50-case benchmark; tighten them as the dataset grows.

## Regression demonstration (measured 2026-10-15)

`python -m ragbench.cli gate-demo` pins the approved baseline to the strong
hybrid configuration, then evaluates two candidates:

| Candidate | production strategy | Decision |
|---|---|---|
| Deliberately degraded | `B1_dense` | **FAIL** |
| Healthy | `B2_hybrid` | **PASS** |

The degraded candidate fails because switching production retrieval from hybrid
to dense drops recall@5 from 1.000 to 0.929 (−0.071 > 0.03 tolerance) — a
measured regression, with the reason reported in the decision. The healthy
candidate (identical to the baseline strategy) passes. A candidate that passes
is eligible for promotion; a failing candidate must not be promoted.

## Abstention calibration (measured 2026-10-15)

`python -m ragbench.cli calibrate` sweeps the abstention threshold over the
labeled dataset and reports the precision/recall trade-off (positive class =
"should abstain"). Strategy = hybrid:

| threshold | precision | recall | F1 | tp | fp | fn |
|---|---|---|---|---|---|---|
| 0.05 | 1.00 | 0.27 | 0.42 | 4 | 0 | 11 |
| 0.10 | 1.00 | 0.27 | 0.42 | 4 | 0 | 11 |
| **0.15** | **1.00** | **0.47** | **0.64** | 7 | 0 | 8 |
| 0.20 | 0.69 | 0.73 | 0.71 | 11 | 5 | 4 |
| 0.25 | 0.50 | 0.87 | 0.63 | 13 | 13 | 2 |
| 0.35 | 0.38 | 1.00 | 0.55 | 15 | 25 | 0 |
| 0.50 | 0.31 | 1.00 | 0.48 | 15 | 33 | 0 |

### Interpretation (honest trade-off)

- The **F1-optimal** threshold is **0.20** (F1 0.71), but it drops abstention
  precision to 0.69 — meaning it abstains on ~5 answerable questions. That
  **violates the gate's 0.90 precision floor**, so F1-optimal is not
  automatically the right production choice.
- The **precision-safe** choice is **0.15** (precision 1.00, recall 0.47): it
  never abstains on an answerable question, at the cost of missing just over
  half of the should-abstain cases. This is the current default
  (`RAGBENCH_ABSTAIN_MIN_SCORE=0.15`) and it satisfies the gate.
- The ceiling on precision is a property of the non-semantic fake embedding:
  misleading-lexical-overlap questions share content words with the corpus and
  so never score low enough to abstain cleanly. A real embedding model is
  expected to separate these classes better; re-run `calibrate` after switching
  providers.

The sweep is the deliverable, not a single magic number: the production
threshold is an explicit policy choice (precision-safe here), documented
alongside what it costs in recall.
