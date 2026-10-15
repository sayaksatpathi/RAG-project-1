"""RAGBench pipeline: the online query path and the ingestion path.

This is the cohesive core that the CLI, API, and evaluation harness all call.
It loads the persisted corpus into in-memory BM25 + dense indexes for the active
index version, then serves queries with retrieval, grounded generation, citation
validation, and evidence-based abstention.
"""

from __future__ import annotations

import hashlib
import time

from ragbench.config import Config, load_config
from ragbench.embeddings import build_embedding_provider
from ragbench.generation import build_generation_provider, validate_citations
from ragbench.ingestion import chunk_text, parse_bytes
from ragbench.ingestion.chunking import chunk_id as make_chunk_id
from ragbench.ingestion.chunking import content_hash
from ragbench.ingestion.parsing import PARSER_VERSION
from ragbench.models import Answer, Chunk, Document
from ragbench.retrieval import BM25Index, DenseIndex, HybridRetriever
from ragbench.storage import SQLiteStore


def _doc_id(content_hash_hex: str) -> str:
    return f"d_{content_hash_hex[:16]}"


class IndexMismatchError(RuntimeError):
    """Raised when documents exist but none are indexed under the active
    index_version (embedding/chunk configuration changed). The caller must run a
    deliberate re-index rather than silently serve an empty or stale index."""


class Pipeline:
    def __init__(self, config: Config | None = None, store: SQLiteStore | None = None) -> None:
        self.config = config or load_config()
        self.store = store or SQLiteStore(self.config.sqlite_path)
        self.embedder = build_embedding_provider(self.config)
        self.generator = build_generation_provider(self.config)
        self._retriever: HybridRetriever | None = None
        self._router = None
        self._dirty = True

    # --- ingestion -------------------------------------------------------
    def ingest_bytes(self, data: bytes, filename: str, suffix: str) -> Document:
        text = parse_bytes(data, suffix)
        chash = content_hash(text)
        existing = self.store.find_document_by_hash(chash)
        if existing:
            return existing  # idempotent: duplicate content is a no-op

        iv = self.config.index_version
        doc = Document(
            id=_doc_id(chash), filename=filename, content_hash=chash,
            parser_version=PARSER_VERSION, status="indexing", text=text,
        )
        self.store.add_document(doc)

        chunks = chunk_text(text, self.config.chunk_size, self.config.chunk_overlap)
        if not chunks:
            doc.status = "empty"
            return doc
        vectors = self.embedder.embed(chunks)
        for seq, (ctext, vec) in enumerate(zip(chunks, vectors, strict=True)):
            cid = make_chunk_id(doc.id, seq, iv)
            self.store.add_chunk(
                Chunk(id=cid, document_id=doc.id, sequence=seq, text=ctext,
                      content_hash=content_hash(ctext), index_version=iv),
                vec,
            )
        doc.num_chunks = len(chunks)
        doc.status = "indexed"
        # Persist final status/count.
        self.store.conn.execute(
            "UPDATE documents SET status = ?, num_chunks = ? WHERE id = ?",
            (doc.status, doc.num_chunks, doc.id),
        )
        self.store.conn.commit()
        self._dirty = True
        return doc

    def delete_document(self, doc_id: str) -> bool:
        ok = self.store.delete_document(doc_id)
        if ok:
            self._dirty = True
        return ok

    def reindex(self) -> dict:
        """Deliberately rebuild every document's chunks/embeddings under the
        active index_version, removing chunks from any other version so
        incompatible vectors are never mixed. Returns a summary."""
        iv = self.config.index_version
        docs = self.store.iter_documents()
        total_chunks = 0
        for doc in docs:
            self.store.delete_chunks_for_document(doc.id)
            chunks = chunk_text(doc.text, self.config.chunk_size, self.config.chunk_overlap)
            status = "indexed" if chunks else "empty"
            if chunks:
                vectors = self.embedder.embed(chunks)
                for seq, (ctext, vec) in enumerate(zip(chunks, vectors, strict=True)):
                    cid = make_chunk_id(doc.id, seq, iv)
                    self.store.add_chunk(
                        Chunk(id=cid, document_id=doc.id, sequence=seq, text=ctext,
                              content_hash=content_hash(ctext), index_version=iv),
                        vec,
                    )
            self.store.conn.execute(
                "UPDATE documents SET status = ?, num_chunks = ? WHERE id = ?",
                (status, len(chunks), doc.id),
            )
            self.store.conn.commit()
            total_chunks += len(chunks)
        self._dirty = True
        return {"documents": len(docs), "index_version": iv, "chunks": total_chunks}

    # --- indexing --------------------------------------------------------
    def index_health(self) -> dict:
        iv = self.config.index_version
        present = self.store.distinct_index_versions()
        docs = self.store.count_documents()
        active_chunks = self.store.count_chunks(iv)
        return {
            "active_index_version": iv,
            "present_index_versions": sorted(present),
            "documents": docs,
            "active_chunks": active_chunks,
            "reindex_required": docs > 0 and active_chunks == 0,
        }

    def _ensure_retriever(self) -> HybridRetriever:
        if self._retriever is not None and not self._dirty:
            return self._retriever
        iv = self.config.index_version
        # Reject an incompatible index rather than silently serving nothing.
        if self.store.count_documents() > 0 and self.store.count_chunks(iv) == 0:
            present = sorted(self.store.distinct_index_versions())
            raise IndexMismatchError(
                f"no chunks for active index_version '{iv}'; present versions: "
                f"{present}. The embedding/chunk configuration changed — run a "
                f"re-index (ragbench reindex / Pipeline.reindex())."
            )
        bm25 = BM25Index()
        dense = DenseIndex(self.config.embedding_dim)
        texts: dict[str, str] = {}
        doc_of: dict[str, str] = {}
        for chunk, vec in self.store.iter_chunks(index_version=iv):
            bm25.add(chunk.id, chunk.text)
            dense.add(chunk.id, vec)
            texts[chunk.id] = chunk.text
            doc_of[chunk.id] = chunk.document_id
        self._retriever = HybridRetriever(
            bm25=bm25, dense=dense, embedder=self.embedder, texts=texts, doc_of=doc_of,
            index_version=iv, rrf_k=self.config.rrf_k,
        )
        self._router = None  # rebuilt against the fresh index on next route()
        self._dirty = False
        return self._retriever

    def retrieve(self, query: str, strategy: str = "hybrid", top_k: int | None = None):
        retriever = self._ensure_retriever()
        if strategy == "adaptive":
            strategy = self.route(query).strategy
        return retriever.retrieve(query, strategy, top_k or self.config.top_k)

    def route(self, query: str):
        """Return the router's decision for a query (builds router on demand)."""
        from ragbench.routing import InterpretableRouter

        retriever = self._ensure_retriever()
        if self._router is None:
            self._router = InterpretableRouter(retriever.bm25)
        return self._router.route(query)

    # --- online query path ----------------------------------------------
    def query(self, question: str, strategy: str = "hybrid", top_k: int | None = None) -> Answer:
        start = time.perf_counter()
        iv = self.config.index_version
        results = self.retrieve(question, strategy, top_k)

        warnings: list[str] = []
        # Abstention uses a strategy-INDEPENDENT evidence signal: the cosine
        # similarity between the query and the best retrieved passage. This
        # avoids comparing a fixed threshold against fusion scores (e.g. RRF),
        # which live on an entirely different, incommensurable scale.
        evidence_score = self._evidence_score(question, results)
        abstain = (not results) or (evidence_score < self.config.abstain_min_score)

        if abstain:
            return Answer(
                text="I don't have enough supporting evidence to answer confidently.",
                citations=[], retrieval_strategy=strategy,
                retrieved_passage_ids=[r.chunk_id for r in results], abstained=True,
                warnings=warnings + ["abstained: top retrieval score below threshold"],
                model=self.generator.name, index_version=iv,
            )

        gen = self.generator.generate(question, results)
        citations = validate_citations(gen.cited_passage_ids, results, iv)
        if any(not c.valid for c in citations):
            warnings.append("one or more citations failed identifier validation")
        _ = time.perf_counter() - start  # latency measured by callers/telemetry
        return Answer(
            text=gen.text, citations=citations, retrieval_strategy=strategy,
            retrieved_passage_ids=[r.chunk_id for r in results], abstained=False,
            warnings=warnings, model=gen.model, index_version=iv,
        )

    def _evidence_score(self, question: str, results: list) -> float:
        if not results:
            return 0.0
        import numpy as np

        from ragbench.retrieval.bm25 import tokenize

        vecs = self.embedder.embed([question] + [r.text for r in results[:5]])
        q = vecs[0]
        qn = np.linalg.norm(q)
        if qn == 0:
            return 0.0
        q = q / qn
        sims = vecs[1:] @ q  # passage vectors are already L2-normalized
        cosine = float(sims.max()) if len(sims) else 0.0

        # Lexical-grounding guard: the deterministic fake embedding is hash-based,
        # so unrelated content words collide and produce a spurious floor cosine.
        # When using the fake provider we additionally require that at least one
        # non-stopword query token appears in the retrieved passages; otherwise
        # evidence is treated as absent. A real semantic embedding model would
        # not need this guard (it can match paraphrases with no lexical overlap),
        # so it is scoped to the fake provider only.
        if self.embedder.name.startswith("fake:"):
            from ragbench.embeddings import _STOPWORDS

            # Ignore stopwords and single-character tokens (e.g. the "s" from a
            # tokenized possessive), which are never meaningful content signals.
            q_terms = {t for t in tokenize(question) if len(t) > 1 and t not in _STOPWORDS}
            passage_terms: set[str] = set()
            for r in results[:5]:
                passage_terms.update(tokenize(r.text))
            if q_terms and not (q_terms & passage_terms):
                return 0.0
        return cosine

    def stats(self) -> dict:
        return {
            "documents": self.store.count_documents(),
            "index_version": self.config.index_version,
            "embedding_provider": self.embedder.name,
            "llm_provider": self.generator.name,
        }


def corpus_fingerprint(texts: list[str]) -> str:
    h = hashlib.sha256()
    for t in sorted(texts):
        h.update(t.encode("utf-8"))
    return h.hexdigest()[:16]
