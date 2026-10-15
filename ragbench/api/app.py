"""FastAPI application exposing the RAGBench query and document API.

Write operations require a bearer token (development default configurable via
RAGBENCH_API_TOKEN). Health endpoints and query are readable; ingestion and
deletion are protected. Versioned schemas, bounded upload size, pagination, and
meaningful errors are implemented. Retrieved content is treated as untrusted
data — never executed.
"""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from ragbench.config import load_config
from ragbench.ingestion.parsing import MAX_BYTES, ParseError
from ragbench.observability import Metrics, get_logger, new_request_id
from ragbench.observability.metrics import CONTENT_TYPE
from ragbench.pipeline import Pipeline


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


def create_app(pipeline: Pipeline | None = None) -> FastAPI:
    config = load_config()
    pipeline = pipeline or Pipeline(config=config)
    app = FastAPI(title="RAGBench API", version="0.1.0")
    metrics = Metrics()
    log = get_logger("ragbench.api")
    app.state.metrics = metrics

    def require_token(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {config.api_token}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="invalid or missing bearer token")

    def _route(request: Request) -> str:
        route = request.scope.get("route")
        return getattr(route, "path", request.url.path)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request.state.request_id = new_request_id()
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            metrics.provider_errors_total.labels(kind="unhandled").inc()
            raise
        latency = time.perf_counter() - start
        route = _route(request)
        metrics.observe_request(request.method, route, response.status_code, latency)
        response.headers["X-Request-ID"] = request.state.request_id
        # Structured log line; never logs raw query/body content.
        log.info("request", extra={"fields": {
            "request_id": request.state.request_id, "method": request.method,
            "route": route, "status": response.status_code,
            "latency_ms": round(latency * 1000, 2),
        }})
        return response

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
        data = await file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="file too large")
        suffix = "." + file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
        try:
            doc = pipeline.ingest_bytes(data, file.filename or "upload", suffix)
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
