"""RAGBench command-line interface.

Usage:
  python -m ragbench.cli ingest <path-or-dir>
  python -m ragbench.cli query "<question>" [--strategy bm25|dense|hybrid]
  python -m ragbench.cli stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ragbench.ingestion.parsing import SUPPORTED_SUFFIXES
from ragbench.pipeline import Pipeline


def _ingest(pipeline: Pipeline, target: str) -> int:
    p = Path(target)
    paths = (
        [f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED_SUFFIXES]
        if p.is_dir()
        else [p]
    )
    count = 0
    for f in paths:
        try:
            doc = pipeline.ingest_bytes(f.read_bytes(), f.name, f.suffix)
            print(f"ingested {f.name} -> {doc.id} ({doc.num_chunks} chunks, {doc.status})")
            count += 1
        except Exception as exc:  # noqa: BLE001 - report, keep going
            print(f"FAILED {f.name}: {exc}", file=sys.stderr)
    print(f"done: {count} file(s)")
    return 0


def _query(pipeline: Pipeline, question: str, strategy: str) -> int:
    answer = pipeline.query(question, strategy=strategy)
    print(json.dumps({
        "answer": answer.text,
        "abstained": answer.abstained,
        "retrieval_strategy": answer.retrieval_strategy,
        "citations": [{"chunk_id": c.chunk_id, "document_id": c.document_id, "valid": c.valid}
                      for c in answer.citations],
        "retrieved_passage_ids": answer.retrieved_passage_ids,
        "warnings": answer.warnings,
        "model": answer.model,
        "index_version": answer.index_version,
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ragbench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest")
    pi.add_argument("path")
    pq = sub.add_parser("query")
    pq.add_argument("question")
    pq.add_argument("--strategy", default="hybrid", choices=["bm25", "dense", "hybrid"])
    sub.add_parser("stats")

    args = parser.parse_args(argv)
    pipeline = Pipeline()
    if args.cmd == "ingest":
        return _ingest(pipeline, args.path)
    if args.cmd == "query":
        return _query(pipeline, args.question, args.strategy)
    if args.cmd == "stats":
        print(json.dumps(pipeline.stats(), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
