"""SQLite persistence for documents, chunks, and embeddings.

Parameterized queries throughout (no string interpolation of values). Vectors
are stored as float32 bytes alongside their index version so incompatible
vectors are never mixed. A Postgres/pgvector store can implement the same
methods behind this interface (documented, not verified in this environment).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from ragbench.models import Chunk, Document

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    parser_version TEXT NOT NULL,
    status TEXT NOT NULL,
    num_chunks INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    index_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    index_version TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
"""


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI runs sync handlers in a threadpool.
        # SQLite serializes access internally; our writes are short and committed.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- documents -------------------------------------------------------
    def find_document_by_hash(self, content_hash: str) -> Document | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        return self._doc(row) if row else None

    def add_document(self, doc: Document) -> None:
        self.conn.execute(
            "INSERT INTO documents(id, filename, content_hash, parser_version, status, num_chunks)"
            " VALUES (?,?,?,?,?,?)",
            (doc.id, doc.filename, doc.content_hash, doc.parser_version, doc.status,
             doc.num_chunks),
        )
        self.conn.commit()

    def list_documents(self, limit: int = 50, offset: int = 0) -> list[Document]:
        rows = self.conn.execute(
            "SELECT * FROM documents ORDER BY created_at, id LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [self._doc(r) for r in rows]

    def count_documents(self) -> int:
        return self.conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]

    def get_document(self, doc_id: str) -> Document | None:
        row = self.conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return self._doc(row) if row else None

    def delete_document(self, doc_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # --- chunks / embeddings --------------------------------------------
    def add_chunk(self, chunk: Chunk, vector: np.ndarray) -> None:
        self.conn.execute(
            "INSERT INTO chunks(id, document_id, sequence, text, content_hash, index_version)"
            " VALUES (?,?,?,?,?,?)",
            (chunk.id, chunk.document_id, chunk.sequence, chunk.text, chunk.content_hash,
             chunk.index_version),
        )
        v = vector.astype(np.float32)
        self.conn.execute(
            "INSERT INTO embeddings(chunk_id, index_version, dim, vector) VALUES (?,?,?,?)",
            (chunk.id, chunk.index_version, int(v.shape[0]), v.tobytes()),
        )
        self.conn.commit()

    def iter_chunks(self, index_version: str | None = None) -> list[tuple[Chunk, np.ndarray]]:
        if index_version:
            rows = self.conn.execute(
                "SELECT c.*, e.vector, e.dim FROM chunks c JOIN embeddings e ON c.id = e.chunk_id"
                " WHERE c.index_version = ? ORDER BY c.document_id, c.sequence",
                (index_version,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT c.*, e.vector, e.dim FROM chunks c JOIN embeddings e ON c.id = e.chunk_id"
                " ORDER BY c.document_id, c.sequence"
            ).fetchall()
        out = []
        for r in rows:
            chunk = Chunk(
                id=r["id"], document_id=r["document_id"], sequence=r["sequence"],
                text=r["text"], content_hash=r["content_hash"], index_version=r["index_version"],
            )
            vec = np.frombuffer(r["vector"], dtype=np.float32, count=r["dim"])
            out.append((chunk, vec))
        return out

    def chunk_belongs_to(self, chunk_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT document_id FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        return row["document_id"] if row else None

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _doc(row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"], filename=row["filename"], content_hash=row["content_hash"],
            parser_version=row["parser_version"], status=row["status"],
            num_chunks=row["num_chunks"], created_at=row["created_at"],
        )
