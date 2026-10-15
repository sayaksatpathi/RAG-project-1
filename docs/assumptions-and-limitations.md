# Assumptions and Limitations

## Environment (observed 2026-10-15)

- Windows 11, Python 3.12.10. No Docker, PostgreSQL, kubectl, or GPU.
- Terraform 1.16.4 present; no cloud credentials assumed.
- No paid LLM access assumed. Network not assumed for the core path.

## Design assumptions

- Corpus sizes are small enough for brute-force dense search and in-memory
  BM25 to be acceptable. ANN indexes are an optional future extension.
- The core path must be fully offline and deterministic, so the defaults are a
  fake embedding provider and a mock generation provider.

## Known limitations (honest)

1. **Fake embeddings are not semantic.** The default embedding is a hash of
   token unigrams/bigrams (stopwords dropped), L2-normalized. It is stable and
   dependency-free but does not capture meaning. Consequences:
   - Dense retrieval cannot match true paraphrases with no lexical overlap.
   - Hash collisions in a finite-dimension space create a spurious floor
     similarity, so abstention adds a **lexical-grounding guard** when the fake
     provider is active (requires ≥1 shared content token). This guard is scoped
     to the fake provider and would be disabled for a real embedding model.
   Swap in `RAGBENCH_EMBEDDING_PROVIDER=sentence-transformers` for semantics.
2. **Abstention threshold is not yet calibrated.** `RAGBENCH_ABSTAIN_MIN_SCORE`
   defaults to 0.15 and is a placeholder. Calibration on validation data and a
   reported precision/recall trade-off is Phase 4 work.
3. **Mock generation is extractive.** It stitches the top passages and cites
   them; it does not reason or synthesize. It faithfully exercises the citation
   and abstention machinery but is not a language model.
4. **PDF support is partial.** Text-based PDFs require the optional `pypdf`
   package; scanned/image PDFs are not OCR'd and are out of scope.
5. **Single-process indexes.** Indexes are rebuilt in memory from SQLite on
   first query after an ingest. No background workers yet.
6. **No evaluation metrics / quality gate / routing / observability / container
   / k8s / cloud yet.** These phases are NOT STARTED or NOT VERIFIED; see
   `IMPLEMENTATION_STATUS.md` and `NEXT_STEPS.md`.

## Not verified in this environment

Docker/Compose, Kubernetes/Helm, Terraform apply, Postgres/pgvector runtime,
sentence-transformers, and real LLM generation. Configuration and code paths
exist or are planned, but their runtime behavior has not been executed here and
must not be claimed as working.
