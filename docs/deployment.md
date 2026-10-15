# Deployment

## Status honesty

| Target | Status |
|---|---|
| Local (Python) | **VERIFIED** — CLI, API, tests, evaluate, gate-demo, calibrate all run. |
| Docker image / Compose | **NOT VERIFIED** — authored and YAML-validated; Docker is unavailable in the dev environment, so the image has not been built or run. |
| GitHub Actions CI | **NOT VERIFIED on GitHub** — workflow YAML is valid and its offline steps (`evaluate`, `gate-demo`, `pytest`, `ruff`) are verified locally; the hosted run has not executed (no remote). |
| Kubernetes / Helm | **AUTHORED, NOT VERIFIED** — manifests + Helm chart written; plain manifest YAML and chart metadata validate with PyYAML; no cluster/kubectl/helm available to apply, lint, or render. |
| Terraform / cloud | **CONFIG VALIDATED, NOT DEPLOYED** — `terraform fmt`/`init`/`validate` pass; `plan`/`apply` not run (no credentials, would reach AWS). |

## Local (verified)

```bash
python -m pip install -e ".[dev]"
python -m ragbench.cli ingest evaluation/datasets/corpus
python -m ragbench.cli query "What is reciprocal rank fusion?"
uvicorn ragbench.api.app:app --port 8000
```

## Docker (authored, not verified)

```bash
docker build -t ragbench:local .
docker run --rm -p 8000:8000 -v ragbench_data:/data ragbench:local
# or the full local stack:
docker compose up --build
# optional Postgres+pgvector backend:
docker compose --profile postgres up
```

The image runs as a non-root user, persists SQLite to a `/data` volume, and
declares a container `HEALTHCHECK` against `/health/live`. The default
configuration is fully offline (fake embeddings, mock generation); override
`RAGBENCH_API_TOKEN` (and any provider settings) via environment for a real
deployment. No external hosted LLM access is required to start the service.

## Kubernetes (authored, not verified)

Plain manifests in `deploy/kubernetes/` (ConfigMap, Secret template, PVC,
Deployment, Service) and a Helm chart in `deploy/helm/ragbench/`. Both set
liveness/readiness/startup probes, resource requests/limits, and a hardened
non-root security context (`runAsNonRoot`, `readOnlyRootFilesystem`, dropped
capabilities). SQLite uses a ReadWriteOnce volume, so the Deployment runs a
**single replica** with a `Recreate` strategy — this is deliberate and is **not**
an auto-scaling or HA claim; horizontal scaling requires the Postgres backend.

```bash
# Build and load the image into a local cluster (e.g. kind), then:
kubectl create secret generic ragbench-secret \
  --from-literal=RAGBENCH_API_TOKEN=$(openssl rand -hex 24)
kubectl apply -f deploy/kubernetes/configmap.yaml \
               -f deploy/kubernetes/pvc.yaml \
               -f deploy/kubernetes/deployment.yaml \
               -f deploy/kubernetes/service.yaml
kubectl rollout status deploy/ragbench-api
kubectl logs deploy/ragbench-api
kubectl rollout undo deploy/ragbench-api   # rollback

# Or with Helm:
helm lint deploy/helm/ragbench
helm template rb deploy/helm/ragbench      # render to inspect
helm install rb deploy/helm/ragbench --set apiToken=$(openssl rand -hex 24)
```

**NOT VERIFIED:** no cluster, `kubectl`, or `helm` is available in this
environment, so `helm lint`/`template` and `kubectl apply` have not been run.
The plain-YAML manifests and the chart's `Chart.yaml`/`values.yaml` parse
cleanly; the Go-templated files are unrendered. If `readOnlyRootFilesystem`
causes a write error at runtime, mount an `emptyDir` at `/tmp`.

## Terraform / AWS (opt-in, config validated)

`infrastructure/terraform/` provisions a minimal, cost-aware AWS setup: an ECR
repository and a CloudWatch log group (cheap, always), plus an **opt-in** ECS
Fargate service (`enable_service`, default false) that is private by default
(`assign_public_ip=false`, no ingress unless `ingress_cidrs` is set). Region is a
required variable. `terraform fmt`, `init -backend=false`, and `validate` all
pass (VERIFIED 2026-10-15); `plan`/`apply` are **not run** (no credentials, and
apply would create billable resources — do not apply without authorization). See
`infrastructure/terraform/README.md` for resource inventory, cost, teardown, and
exposure notes.

## CI (GitHub Actions)

`.github/workflows/ci.yml` defines least-privilege (`contents: read`) jobs:

- **lint** — `ruff check .`
- **test** — `pytest` on the full offline suite
- **retrieval-gate** — runs the offline retrieval benchmark and the quality-gate
  regression demo; `gate-demo` exits non-zero if the expected FAIL (degraded) /
  PASS (healthy) outcomes are not observed, so a broken gate fails CI
- **docker-build** — builds the image to catch Dockerfile breakage (no push)
- **dependency-scan** — `pip-audit` over declared dependencies

Fast PR checks require no paid LLM API. Actions are pinned to major versions per
a reasonable repository policy; tighten to commit SHAs if required.

## Migrations / initialization

SQLite schema is created on first connection (idempotent `CREATE TABLE IF NOT
EXISTS`). No separate migration step is needed for the default backend. The
Postgres backend (optional) would use Alembic migrations — not yet implemented.

## Rollback

Promotion is gated: a candidate configuration is eligible only after the quality
gate passes (see docs/quality-gate.md). No automatic deployment to a public
service is configured. Where a real staging/production target exists, keep the
last approved baseline (`evaluation/baselines/approved_baseline.json`) and the
last known-good image tag to roll back to; this repo demonstrates the gate
locally and does not simulate a production deployment.
