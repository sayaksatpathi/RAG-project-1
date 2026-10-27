# Changelog

All notable changes to RAGBench. Dates are the day the work was recorded; the
project values honest status, so items are listed as VERIFIED only where tests
or real runs back them (see `IMPLEMENTATION_STATUS.md`).

The format follows [Keep a Changelog](https://keepachangelog.com/), and the
project aims to follow [Semantic Versioning](https://semver.org/).

## [0.13.0] - 2026-10-27

Completes the planned phase set (Phases 6, 12, 13) on top of the verified core.

### Added
- **API hardening (Phase 6):** constant-time bearer-token comparison; restrictive
  security headers on every response (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Content-Security-Policy`, `Cache-Control`); per-client
  fixed-window rate limiting (configurable, probes/metrics exempt) returning 429
  with `Retry-After`; a request-body-size guard; path-traversal-safe upload
  filenames; a content-type allowlist (415) and a streaming upload size cap
  (413); optional CORS; and a consistent 500 error envelope that never leaks
  internals. New metrics `ragbench_auth_failures_total` and
  `ragbench_requests_rejected_total`. 16 new tests.
- **Research report (Phase 12):** `docs/research-report.md` — a self-contained
  capstone consolidating question, method, measured results (v1 and v1.1),
  ablations, abstention analysis, reliability/load, honest negative findings,
  threats to validity, and reproducibility commands with run IDs.
- **Packaging (Phase 13):** `LICENSE` (MIT); full `pyproject.toml` metadata
  (authors, license, readme, classifiers, URLs, keywords); `ragbench version` /
  `--version`; `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`; additional
  Makefile targets (`format`, `security`, `report`, `version`, `clean`).

### Changed
- Version bumped to `0.13.0`; the API advertises this version.
- `.env.example` documents the new hardening settings.

## [0.1.0] - 2026-10-15

Initial offline-first core: ingestion, SQLite storage, BM25/dense/hybrid
retrieval, grounded generation with citations and abstention, an adaptive
router experiment, an evaluation harness with an AI quality gate, traceability,
observability, reliability/load experiments, and authored (runtime-unverified)
Docker/CI/Kubernetes/Helm/Terraform assets.
