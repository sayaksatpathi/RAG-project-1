# Contributing

Thanks for your interest in RAGBench.

## Development setup

```bash
python -m pip install -e ".[dev]"   # Python 3.11+ (developed on 3.12)
cp .env.example .env                 # optional; defaults are fully offline
```

No Docker, Postgres, GPU, or paid API is needed for the core path, the tests, or
retrieval-only evaluation.

## Before you push

```bash
make lint     # ruff
make test     # full unit + integration suite
```

Both must be clean. New behavior needs a test; the project prefers a small,
tested vertical slice over untested breadth.

## Project conventions

- **Honest status.** Claims in docs must be backed by a passing test or a real
  run. Anything unverified (e.g. because a runtime is unavailable) is labeled
  NOT VERIFIED in `IMPLEMENTATION_STATUS.md` rather than asserted.
- **Offline-first.** The default path must stay deterministic and offline. Heavy
  or networked capabilities (sentence-transformers, OpenAI, Postgres, Docker,
  Kubernetes, Terraform) are optional, config-gated, and documented.
- **Reproducibility.** Evaluation changes should be reproducible from a single
  command and recorded in the run registry.

## Commit style

Small, focused commits with imperative subject lines (e.g. "Add API rate
limiting"). Keep the changelog and implementation status current.
