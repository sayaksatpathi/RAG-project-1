# AI Quality Gate

An AI quality gate is an automated check that compares a candidate retrieval or
answer configuration against an approved baseline before the candidate is
promoted. The gate runs deterministic tests and offline evaluation on a pinned
dataset, compares metrics against versioned thresholds, and emits a pass or fail
decision with reasons. A candidate that regresses a critical metric beyond its
configured tolerance is rejected and must not be promoted. Thresholds live in
versioned configuration, not scattered through source code.
