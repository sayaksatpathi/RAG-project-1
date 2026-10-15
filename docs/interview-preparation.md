# Interview Preparation

Everything here describes the **actual implementation**. Where a capability is
not runtime-verified, it says so — do not overstate it in an interview.

## Two-minute pitch

RAGBench is an adaptive Retrieval-Augmented Generation platform *and* an
evaluation harness. It ingests documents, retrieves evidence with sparse (BM25),
dense, and hybrid (Reciprocal Rank Fusion) strategies, generates grounded
answers with validated citations, and abstains when evidence is insufficient.
The research angle is query-aware routing: a router picks a retrieval strategy
per query against a strong hybrid fallback. Crucially, the repo doesn't just
*claim* quality — it measures it: a reproducible harness computes Recall/MRR/
nDCG over a labeled benchmark, and a CI quality gate rejects a candidate
configuration that regresses against an approved baseline. The whole core runs
offline and deterministically (a hand-written BM25, a deterministic embedding
stand-in, and a mock LLM), so tests and retrieval evaluation need no paid API.
My honest headline finding is a *negative* one: on this corpus the adaptive
router tied, not beat, the strongest fixed baseline — and the project is designed
to report that faithfully rather than hide it.

## Five-minute architecture walkthrough

1. **Ingestion** (`ragbench/ingestion`): parse TXT/MD (text PDF optional),
   normalize, content-hash for dedup, versioned word-window chunking with stable
   chunk IDs. Full text is persisted so documents can be re-chunked.
2. **Storage** (`ragbench/storage`): SQLite with documents/chunks/embeddings and
   a separate evaluation-run registry. Every chunk/embedding is tagged with an
   `index_version` (`provider:model:dim:chunk:overlap`).
3. **Retrieval** (`ragbench/retrieval`): hand-written Okapi BM25, brute-force
   dense cosine, and RRF hybrid that fuses *ranks* (never raw incommensurable
   scores). Optional heuristic reranker.
4. **Routing** (`ragbench/routing`): interpretable rules (exact identifier, rare
   corpus term, length/paraphrase) → bm25/dense/hybrid, with a hybrid fallback.
5. **Generation + evidence** (`ragbench/generation`): provider-neutral interface
   (mock default, OpenAI optional); citation identifier validation; evidence-based
   abstention using a strategy-independent signal.
6. **Evaluation + gate** (`ragbench/evaluation`, `ragbench/gate`): metrics,
   baseline harness (B0–B4), ablations, abstention calibration; a versioned
   quality gate with a regression demo.
7. **Serving + ops** (`ragbench/api`, `ragbench/observability`): FastAPI with
   health/query/document CRUD + `/metrics`, structured logs with request IDs,
   Prometheus metrics; a Streamlit dashboard.
8. **Delivery** (`Dockerfile`, `deploy/`, `infrastructure/`, `.github`): Docker,
   K8s/Helm, Terraform, CI — with honest VERIFIED vs NOT VERIFIED status.

## Technical Q&A (25+)

1. **Why fuse ranks with RRF instead of combining scores?** BM25 and cosine
   scores live on different, uncalibrated scales; summing them is meaningless.
   RRF uses only rank position (1/(k+rank)), which is scale-free.
2. **Why a hand-written BM25?** Transparency and determinism, and to avoid a
   dependency for a well-understood formula. It's unit-tested for ties, empty
   index, and no-match cases.
3. **What is `index_version` and why does it matter?** It encodes the embedding
   and chunk configuration. Chunks are tagged with it so vectors from
   incompatible configs are never mixed; changing config forces a deliberate
   re-index.
4. **What happens if the config changes but you don't re-index?** Queries raise
   `IndexMismatchError` instead of silently serving an empty/stale index;
   `ragbench reindex` rebuilds under the active version.
5. **How does abstention work, and why not a similarity threshold on the
   retrieval score?** Retrieval/fusion scores aren't comparable across
   strategies, so abstention uses a separate embedding-cosine evidence signal
   plus (for the fake embedder) a lexical-grounding guard. The threshold is
   calibrated via a documented sweep, not picked arbitrarily.
6. **How are citations validated?** Each cited passage ID must be among those
   actually retrieved and belong to the expected index version. Identifier
   validity, citation coverage, whether the passage supports the claim, and
   answer correctness are treated as *distinct* measurements, not collapsed.
7. **Why is the default embedding "fake"?** It's a deterministic hash-based
   stand-in so dense retrieval and tests run offline and reproducibly. It's not
   semantic — I'm explicit that real conclusions need a real embedding model.
8. **Didn't that bias your results toward BM25?** Yes, and I say so. BM25 wins
   here partly because the stand-in embedding is weak; that's the main threat to
   validity, documented in docs/research.md.
9. **What did the routing experiment actually show?** Adaptive tied the strongest
   fixed baseline (BM25) — a neutral result for H1. The router sent 45/50 queries
   to BM25 and reproduced its metrics. Honest negative/neutral finding.
10. **Is the router a model?** No — it's a hand-specified ordered rule set with a
    fallback. I deliberately don't call a heuristic a trained model.
11. **How does the quality gate decide pass/fail?** Purely from measured metrics
    vs a versioned policy (regression tolerances + absolute minimums). The
    decision is never keyed off a test name; missing metrics fail closed.
12. **How do you prove the gate catches regressions?** `gate-demo` pins hybrid as
    the baseline, then evaluates a dense candidate; dense's recall drop exceeds
    the tolerance → FAIL, with the reason. A healthy hybrid candidate PASSes.
13. **Why generous regression tolerances?** The benchmark is 50 cases; small-
    dataset variance is real. Tolerances are in a versioned policy file and
    documented as "tighten as the dataset grows."
14. **How do you prevent evaluation leakage?** Routing training/validation/test
    separation is part of the design; the current router is heuristic (no
    training), and the acceptance rule ("strongest fixed by mrr") is declared
    before inspecting the adaptive result.
15. **How is the API secured?** Write/admin endpoints require a bearer token;
    uploads are size-bounded and type-validated; queries are length-bounded;
    retrieved content is treated as untrusted data and never executed.
16. **How do you handle a failing LLM provider?** The query path catches provider
    exceptions and returns a safe degraded answer with a warning instead of
    crashing; `failure-demo` verifies this.
17. **What's your observability story?** Structured JSON logs with request IDs
    (never logging raw query text), Prometheus metrics at `/metrics` (requests,
    latency histogram, strategy, abstentions, provider errors, indexed docs),
    and a Streamlit dashboard with honest empty states.
18. **How do you avoid high-cardinality metric labels?** Labels are route
    templates and strategy names, not raw paths/queries/user IDs.
19. **Why single-replica in Kubernetes?** SQLite uses a ReadWriteOnce volume that
    can't be shared; scaling out requires the Postgres backend. I explicitly do
    not claim HA/auto-scaling from replica count.
20. **What's verified vs not?** Core (ingest→retrieve→generate→cite→abstain),
    baselines, routing, gate, traceability, reliability, logging/metrics: VERIFIED
    by tests/CLI. Docker build, hosted CI, live Grafana/Streamlit, K8s apply:
    NOT VERIFIED (no runtime). Terraform: fmt/init/validate pass, apply not run.
21. **How fast is it?** `loadtest --n 200` gave ~1343 qps, 0 errors, p50/p95/p99
    = 0.71/0.90/1.34 ms — but offline with the mock LLM and a 14-doc corpus. Real
    latency would be dominated by embedding + generation; I don't claim these as
    production numbers.
22. **What breaks first under load with a real LLM?** Generation latency/cost and
    provider rate limits — which is why generation is behind a bounded interface
    with graceful degradation and why fast CI never calls a paid API.
23. **How is a result reproducible?** Every evaluation run records run_id, git
    commit, dataset/index versions, config, and metrics in a registry; reports
    are regenerated by `ragbench evaluate`.
24. **Why RRF k=60?** It's the common default from the original RRF paper; it's a
    config value, documented, and the hybrid pool size is 4×k.
25. **What would you do next?** Swap in a real embedding model and re-run the
    identical harness and calibration (the routing experiment needs semantic
    headroom), expand the dataset with graded relevance, add paired significance
    testing, and verify the Docker/K8s/CI paths on a real runtime.
26. **Biggest weakness?** The non-semantic default embedding bounds what the
    retrieval/routing results can claim — I treat that as the headline caveat
    rather than hiding it.

## Likely "how does it fail" questions

- **Corrupt upload** → `ParseError`, no partial index (`failure-demo`).
- **DB down** → `/health/ready` 503, loud failures, recovers on reconnect.
- **Provider outage** → graceful degraded answer + warning, no retry storm.
- **Config drift** → `IndexMismatchError` until `reindex`.
- **Degraded candidate** → quality gate FAIL with reasons; CI blocks it.

## Limitations (say these plainly)

Non-semantic default embedding; small synthetic benchmark; mock generation;
abstention recall limited by misleading-overlap cases; Docker/K8s/hosted-CI/
cloud not runtime-verified. All tracked in IMPLEMENTATION_STATUS.md.

## Resume bullets (verified claims only)

- Built an offline-first RAG platform (FastAPI + SQLite) with BM25, dense, and
  RRF-hybrid retrieval, grounded generation with validated citations, and
  evidence-based abstention; 68 automated tests, lint-clean.
- Designed a reproducible retrieval-evaluation harness (Recall/MRR/nDCG@k) over a
  labeled benchmark and an interpretable query-aware router; reported a rigorous
  *negative* result (routing tied the strongest fixed baseline) with ablations
  and documented threats to validity.
- Implemented a CI AI-quality gate with versioned thresholds that rejects a
  deliberately regressed configuration from a measured metric comparison, plus a
  calibrated abstention threshold sweep.
- Added full data/config traceability (per-run registry; enforced re-index on
  incompatible embedding/chunk changes) and observability (structured logs,
  Prometheus `/metrics`, Streamlit dashboard).
- Authored containerization and deployment IaC (Docker, Kubernetes/Helm,
  Terraform validated with `terraform validate`) with explicit verified-vs-
  unverified status and no fabricated metrics.
