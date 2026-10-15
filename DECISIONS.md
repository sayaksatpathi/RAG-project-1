# Architecture Decision Records

## ADR-0001: Offline-first default stack (2026-10-15)

**Context.** The target environment has no Docker, PostgreSQL, kubectl, GPU, or
guaranteed network/paid-LLM access. The brief requires the core vertical slice,
unit tests, and retrieval-only evaluation to have deterministic offline paths.

**Decision.**
- **Storage:** SQLite by default (`ragbench/storage`), with a documented
  Postgres/pgvector option behind the same repository interface.
- **Sparse retrieval:** a hand-written, unit-tested BM25 (Okapi) implementation
  rather than a third-party dependency, for transparency and determinism.
- **Dense retrieval:** a deterministic hash-based "fake" embedding provider by
  default; `sentence-transformers` is an optional provider behind the embedding
  interface.
- **Generation:** a deterministic "mock" provider that composes an extractive
  answer with citations from retrieved passages; an OpenAI-compatible provider
  is optional behind the generation interface.

**Consequences.** Everything demonstrable in this repo runs with zero paid
services and is reproducible bit-for-bit. Heavy/real providers are swappable via
config and are honestly marked NOT VERIFIED where their runtime is absent.

## ADR-0002: Provider-neutral interfaces (2026-10-15)

All model/provider/storage access sits behind narrow Python Protocols so tests
use deterministic fakes and production can swap implementations without touching
business logic. This is the deterministic test seam the brief requires.

## ADR-0003: Scores are not commensurable (2026-10-15)

BM25 and cosine scores are never compared as calibrated probabilities. Hybrid
retrieval fuses *ranks* via Reciprocal Rank Fusion (RRF), not raw scores.
