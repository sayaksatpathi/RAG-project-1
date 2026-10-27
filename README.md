# RAGBench

An adaptive Retrieval-Augmented Generation (RAG) platform and evaluation
harness. RAGBench ingests a documented corpus, retrieves evidence, produces
grounded answers with inspectable citations, abstains when evidence is
insufficient, and is built to compare retrieval strategies and gate candidate
configurations against a known-good baseline.

> **Status:** early, offline-first core. This repository prioritizes a working,
> tested vertical slice and honest status reporting over breadth. See
> [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for exactly what is
> VERIFIED vs. NOT STARTED / NOT VERIFIED.

## Research question

> Can query-aware retrieval routing improve the quality–latency–cost trade-off
> of RAG compared with strong fixed retrieval baselines while maintaining
> acceptable evidence support and answer correctness?

This is treated as a hypothesis to test fairly, not a foregone conclusion. The
headline result is **neutral** — adaptive routing ties the strongest fixed
baseline on this corpus, reported honestly. See the full
[research report](docs/research-report.md) and the working
[docs/research.md](docs/research.md).

## What is implemented and verified (2026-10-27)

- **Ingestion**: TXT/MD parsing with normalization, content-hash dedup,
  versioned word-window chunking with stable chunk IDs. (PDF supported only if
  the optional `pypdf` package is installed; scanned/OCR PDFs are out of scope.)
- **Storage**: SQLite with a documents/chunks/embeddings schema and parameterized
  queries. (Postgres/pgvector is a documented, unverified option.)
- **Retrieval**: hand-written BM25, brute-force dense cosine, and hybrid
  Reciprocal Rank Fusion (RRF) — fusing ranks, never raw incommensurable scores.
- **Generation**: deterministic offline mock provider producing grounded
  extractive answers with citations. (OpenAI-compatible provider is optional.)
- **Citations & abstention**: citation identifier validation against retrieved
  passages and index version; strategy-independent evidence-based abstention.
- **API**: FastAPI with health/live, health/ready, query, document CRUD
  (token-protected writes), pagination, and metrics summary. **Hardened**:
  constant-time bearer check, security headers on every response, per-client
  rate limiting, a request-body ceiling, path-traversal-safe filenames, an
  upload content-type allowlist and streaming size cap, optional CORS, and a
  consistent error envelope that never leaks internals.
- **CLI**: `ingest`, `query`, `stats`, `evaluate`, `gate-demo`, `failure-demo`,
  `loadtest`, `runs`, `version`.
- **Tests**: 90 unit + integration tests passing; ruff clean.

## Architecture

See [docs/architecture.md](docs/architecture.md). The online query path:

```
query -> retrieval router/strategy -> BM25 / dense / hybrid(RRF)
      -> evidence check (abstain?) -> grounded generation
      -> citation validation -> answer + citations + metadata
```

## Prerequisites

- Python 3.11+ (developed on 3.12). No Docker, Postgres, GPU, or paid API needed
  for the core path, tests, or retrieval-only evaluation.

## Setup

```bash
python -m pip install -e ".[dev]"      # or: pip install fastapi pydantic uvicorn numpy
cp .env.example .env                    # optional; defaults are offline
```

## Run

```bash
# Ingest the sample corpus
python -m ragbench.cli ingest evaluation/datasets/corpus

# Ask a grounded question (offline mock generation)
python -m ragbench.cli query "What is reciprocal rank fusion?" --strategy hybrid

# See corpus/config stats
python -m ragbench.cli stats

# Serve the API
uvicorn ragbench.api.app:app --reload
#   GET  /health/live   GET /health/ready
#   POST /api/v1/query  {"query": "...", "strategy": "hybrid"}
#   POST /api/v1/documents            (Authorization: Bearer dev-local-token)
```

## Tests

```bash
python -m pytest        # unit + integration
python -m ruff check .  # lint
```

## Configuration

All behavior is environment-driven with offline defaults; see `.env.example`.
The `index_version` string changes whenever the embedding or chunk configuration
changes, which forces a deliberate re-index and prevents mixing incompatible
vectors.

## Optional / not verified in this environment

Docker, Kubernetes/Helm, Terraform/cloud, Postgres/pgvector, sentence-transformers,
and OpenAI-compatible generation are config-gated and documented but **not
runtime-verified here** (no Docker/Postgres/kubectl/credentials). They are marked
accordingly in `IMPLEMENTATION_STATUS.md`.

## Limitations

See [docs/assumptions-and-limitations.md](docs/assumptions-and-limitations.md).
Notably, the default deterministic "fake" embedding is a lexical hash, not a
semantic model; it exists so the dense path and tests run reproducibly offline.
Swap in a real embedding provider for meaningful semantic retrieval.
