# RAGBench API image. Runs the offline-first stack by default (SQLite, fake
# embeddings, mock generation) — no paid API or model download required.
#
# NOTE: this image has NOT been built/run in the development environment (Docker
# unavailable). The build steps are authored and reviewed; runtime is NOT
# VERIFIED. See docs/deployment.md.

FROM python:3.12-slim AS base

# Do not write .pyc, unbuffered stdout for container logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RAGBENCH_SQLITE_PATH=/data/ragbench.db

WORKDIR /app

# Install dependencies first for layer caching. Copy only metadata, then source.
COPY pyproject.toml README.md ./
COPY ragbench ./ragbench
RUN pip install --no-cache-dir .

# Non-root runtime user and a writable data volume.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000
VOLUME ["/data"]

# Container-level health check hitting the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live').status==200 else 1)"

CMD ["uvicorn", "ragbench.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
