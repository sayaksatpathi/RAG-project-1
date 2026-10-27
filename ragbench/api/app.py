"""FastAPI application exposing the RAGBench query and document API.

Hardening (Phase 6): write operations require a bearer token checked in constant
time; every response carries restrictive security headers; a per-client rate
limit and a request-body ceiling guard against abuse; uploads are filename-
sanitized (no path traversal), content-type-allowlisted, and size-capped as they
stream; unhandled errors return a consistent envelope with the request id and
never leak internals. Retrieved content is treated as untrusted data — never
executed, never used to fetch anything.
"""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from ragbench import __version__
from ragbench.api.security import (
    SECURITY_HEADERS,
    FixedWindowRateLimiter,
    safe_filename,
    token_matches,
)
from ragbench.config import Config, load_config
from ragbench.ingestion.parsing import MAX_BYTES, SUPPORTED_SUFFIXES, ParseError
from ragbench.observability import Metrics, get_logger, new_request_id
from ragbench.observability.metrics import CONTENT_TYPE
from ragbench.pipeline import Pipeline

# Probes and metric scrapes must never be throttled or they would flap.
_RATE_EXEMPT = frozenset({"/health/live", "/health/ready", "/metrics"})
_UPLOAD_CHUNK = 1 << 20  # 1 MiB read granularity for the streaming size cap


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    strategy: str = Field(default="hybrid", pattern="^(bm25|dense|hybrid)$")
    top_k: int | None = Field(default=None, ge=1, le=50)


class CitationModel(BaseModel):
    chunk_id: str
    document_id: str
    valid: bool


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationModel]
    retrieval_strategy: str
    retrieved_passage_ids: list[str]
    abstained: bool
    request_id: str
    latency_ms: float
    model: str
    index_version: str
    warnings: list[str]


class DocumentModel(BaseModel):
    id: str
    filename: str
    status: str
    num_chunks: int
    created_at: str


def _suffix_of(filename: str) -> str:
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""


def create_app(pipeline: Pipeline | None = None, config: Config | None = None) -> FastAPI:
    config = config or (pipeline.config if pipeline is not None else load_config())
    pipeline = pipeline or Pipeline(config=config)
    app = FastAPI(title="RAGBench API", version=__version__)
    metrics = Metrics()
    log = get_logger("ragbench.api")
    limiter = FixedWindowRateLimiter(config.rate_limit_per_min, window_s=60.0)
    app.state.metrics = metrics
    app.state.limiter = limiter

    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    def _secure(response: Response, request_id: str) -> Response:
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        response.headers["X-Request-ID"] = request_id
        return response

    def require_token(authorization: str | None = Header(default=None)) -> None:
        if not token_matches(authorization, config.api_token):
            metrics.auth_failures_total.inc()
            raise HTTPException(status_code=401, detail="invalid or missing bearer token")

    def _route(request: Request) -> str:
        route = request.scope.get("route")
        return getattr(route, "path", request.url.path)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = getattr(request.state, "request_id", None) or new_request_id()
        request.state.request_id = request_id

        # Body-size guard: a client can lie about Content-Length, so this is
        # defense in depth for the JSON endpoints; the upload path additionally
        # enforces the ceiling as it streams.
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() \
                and int(content_length) > config.max_request_bytes:
            metrics.requests_rejected_total.labels(reason="too_large").inc()
            resp = JSONResponse(status_code=413,
                content={"error": "request entity too large", "request_id": request_id})
            return _secure(resp, request_id)

        if request.url.path not in _RATE_EXEMPT:
            client = request.client.host if request.client else "unknown"
            decision = limiter.check(client)
            if not decision.allowed:
                metrics.requests_rejected_total.labels(reason="rate_limited").inc()
                resp = JSONResponse(status_code=429,
                    content={"error": "rate limit exceeded", "request_id": request_id})
                resp.headers["Retry-After"] = str(decision.retry_after)
                return _secure(resp, request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            metrics.provider_errors_total.labels(kind="unhandled").inc()
            raise
        latency = time.perf_counter() - start
        route = _route(request)
        metrics.observe_request(request.method, route, response.status_code, latency)
        # Structured log line; never logs raw query/body content.
        log.info("request", extra={"fields": {
            "request_id": request_id, "method": request.method,
            "route": route, "status": response.status_code,
            "latency_ms": round(latency * 1000, 2),
        }})
        return _secure(response, request_id)

    @app.exception_handler(Exception)
    async def on_unhandled(request: Request, exc: Exception) -> Response:
        # Consistent envelope; the real exception is already counted in the
        # observe middleware and never echoed to the client.
        request_id = getattr(request.state, "request_id", "")
        return _secure(JSONResponse(status_code=500,
            content={"error": "internal server error", "request_id": request_id}), request_id)

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        metrics.indexed_documents.set(pipeline.store.count_documents())
        return Response(content=metrics.render(), media_type=CONTENT_TYPE)

    @app.get("/health/live")
    def live() -> dict:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict:
        try:
            pipeline.store.count_documents()
            return {"status": "ready"}
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(status_code=503, content={"status": "not ready", "error": str(exc)})

    @app.post("/api/v1/query", response_model=QueryResponse)
    def query(req: QueryRequest, request: Request) -> QueryResponse:
        start = time.perf_counter()
        answer = pipeline.query(req.query, strategy=req.strategy, top_k=req.top_k)
        latency = (time.perf_counter() - start) * 1000
        metrics.observe_query(answer.retrieval_strategy, answer.abstained)
        return QueryResponse(
            answer=answer.text,
            citations=[CitationModel(chunk_id=c.chunk_id, document_id=c.document_id, valid=c.valid)
                       for c in answer.citations],
            retrieval_strategy=answer.retrieval_strategy,
            retrieved_passage_ids=answer.retrieved_passage_ids,
            abstained=answer.abstained,
            request_id=getattr(request.state, "request_id", ""),
            latency_ms=round(latency, 3),
            model=answer.model,
            index_version=answer.index_version,
            warnings=answer.warnings,
        )

    @app.post("/api/v1/documents", dependencies=[Depends(require_token)])
    async def upload(file: UploadFile) -> DocumentModel:
        filename = safe_filename(file.filename)
        suffix = _suffix_of(filename)
        if suffix not in SUPPORTED_SUFFIXES:
            raise HTTPException(status_code=415,
                                detail=f"unsupported file type: {suffix or 'unknown'}")
        # Stream with a hard cap so an oversized upload cannot exhaust memory
        # before any length check (a Content-Length header can be absent or false).
        size = 0
        parts: list[bytes] = []
        while True:
            chunk = await file.read(_UPLOAD_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(status_code=413, detail="file too large")
            parts.append(chunk)
        try:
            doc = pipeline.ingest_bytes(b"".join(parts), filename, suffix)
        except ParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return DocumentModel(id=doc.id, filename=doc.filename, status=doc.status,
                             num_chunks=doc.num_chunks, created_at=doc.created_at)

    @app.get("/api/v1/documents")
    def list_docs(limit: int = 50, offset: int = 0) -> dict:
        limit = max(1, min(limit, 200))
        docs = pipeline.store.list_documents(limit=limit, offset=max(0, offset))
        return {
            "total": pipeline.store.count_documents(),
            "limit": limit, "offset": offset,
            "items": [DocumentModel(id=d.id, filename=d.filename, status=d.status,
                                    num_chunks=d.num_chunks, created_at=d.created_at).model_dump()
                      for d in docs],
        }

    @app.get("/api/v1/documents/{document_id}")
    def get_doc(document_id: str) -> DocumentModel:
        d = pipeline.store.get_document(document_id)
        if not d:
            raise HTTPException(status_code=404, detail="document not found")
        return DocumentModel(id=d.id, filename=d.filename, status=d.status,
                             num_chunks=d.num_chunks, created_at=d.created_at)

    @app.delete("/api/v1/documents/{document_id}", dependencies=[Depends(require_token)])
    def delete_doc(document_id: str) -> dict:
        if not pipeline.delete_document(document_id):
            raise HTTPException(status_code=404, detail="document not found")
        return {"deleted": document_id}

    @app.get("/api/v1/metrics/summary")
    def metrics_summary() -> dict:
        return pipeline.stats()

    return app


app = create_app()
