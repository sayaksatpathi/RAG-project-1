# Security

RAGBench is a portfolio/research project. It is offline-first and ships safe,
documented defaults; it is **not** a hardened production service as-is.

## Security posture (implemented)

- **Untrusted content boundary.** Retrieved passages and uploaded documents are
  treated as data: never executed, never used to fetch embedded URLs, no macros.
- **Authentication.** Write/admin endpoints (`POST`/`DELETE /api/v1/documents`)
  require a bearer token, compared in constant time.
- **Transport/response hardening.** Every response carries `nosniff`, `DENY`
  framing, `no-referrer`, a `default-src 'none'` CSP, and `no-store`.
- **Abuse limits.** A per-client rate limit, a request-body ceiling, an upload
  content-type allowlist, and a streaming upload size cap.
- **No secret leakage.** Secrets come from the environment (`.env` is
  git-ignored); raw queries and request bodies are never logged; errors return a
  generic envelope with a request id, not internals.

See `docs/assumptions-and-limitations.md` for the full threat model and the
known limitations (e.g. the rate limiter is per-process; CORS is off by default).

## Reporting a vulnerability

This is a personal project without a formal disclosure program. If you find a
security issue, please open a GitHub issue describing it (omit any sensitive
exploit details in public), or contact the maintainer via the email in
`pyproject.toml`.
