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

from ragbench import __version__
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
    args_in = sys.argv[1:] if argv is None else list(argv)
    # Report the version without requiring a subcommand (argparse's required
    # subparser would otherwise reject a bare `--version`).
    if args_in and args_in[0] in ("--version", "-V", "version"):
        print(f"ragbench {__version__}")
        return 0

    parser = argparse.ArgumentParser(prog="ragbench")
    parser.add_argument("--version", "-V", action="version", version=f"ragbench {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="print the RAGBench version and exit")
    pi = sub.add_parser("ingest")
    pi.add_argument("path")
    pq = sub.add_parser("query")
    pq.add_argument("question")
    pq.add_argument("--strategy", default="hybrid", choices=["bm25", "dense", "hybrid"])
    sub.add_parser("stats")
    sub.add_parser("reindex", help="rebuild all documents under the active index_version")
    sub.add_parser("index-health")
    pr = sub.add_parser("runs", help="list recorded evaluation runs")
    pr.add_argument("--limit", type=int, default=20)
    pe = sub.add_parser("evaluate")
    pe.add_argument("--corpus", default="evaluation/datasets/corpus")
    pe.add_argument("--dataset", default="evaluation/datasets/benchmark_v1.json")
    pe.add_argument("--k", type=int, default=5)
    pe.add_argument("--no-write", action="store_true", help="print only, do not save a report")
    pg = sub.add_parser("gate-demo", help="demonstrate the quality gate rejecting a regression")
    pg.add_argument("--corpus", default="evaluation/datasets/corpus")
    pg.add_argument("--dataset", default="evaluation/datasets/benchmark_v1.json")
    pc = sub.add_parser("calibrate", help="sweep the abstention threshold")
    pc.add_argument("--corpus", default="evaluation/datasets/corpus")
    pc.add_argument("--dataset", default="evaluation/datasets/benchmark_v1.json")
    pc.add_argument("--strategy", default="hybrid", choices=["bm25", "dense", "hybrid"])
    sub.add_parser("failure-demo", help="run controlled failure experiments")
    pl = sub.add_parser("loadtest", help="bounded load/latency measurement")
    pl.add_argument("--n", type=int, default=100)
    pl.add_argument("--concurrency", type=int, default=1)
    pl.add_argument("--strategy", default="hybrid", choices=["bm25", "dense", "hybrid"])

    args = parser.parse_args(argv)
    if args.cmd == "evaluate":
        # Uses its own in-memory pipeline; never touches the persistent DB.
        from ragbench.evaluation.harness import render_markdown, run_benchmark, write_report

        report = run_benchmark(args.corpus, args.dataset, k=args.k)
        print(render_markdown(report))
        if not args.no_write:
            json_path, md_path = write_report(report)
            print(f"wrote {json_path}\nwrote {md_path}")
            from ragbench.config import load_config
            from ragbench.storage import RunRegistry

            reg = RunRegistry(load_config().runs_db_path)
            reg.record(report, report_path=json_path)
            reg.close()
            print(f"registered run {report['run_id'][:8]} in the run registry")
        return 0
    if args.cmd == "gate-demo":
        from ragbench.gate.service import regression_demo

        result = regression_demo(args.corpus, args.dataset)
        deg = result["degraded_candidate"]
        heal = result["healthy_candidate"]
        print(json.dumps(result, indent=2))
        print(f"\ndegraded candidate ({deg['candidate_strategy']}): {deg['decision']}")
        print(f"healthy candidate  ({heal['candidate_strategy']}): {heal['decision']}")
        # Exit non-zero only if the demo itself is broken (expected FAIL/PASS flipped).
        ok = deg["decision"] == "FAIL" and heal["decision"] == "PASS"
        return 0 if ok else 2
    if args.cmd == "calibrate":
        from ragbench.evaluation.calibration import calibrate_abstention

        result = calibrate_abstention(args.corpus, args.dataset, strategy=args.strategy)
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "failure-demo":
        from dataclasses import asdict

        from ragbench.reliability import run_failure_experiments

        results = [asdict(r) for r in run_failure_experiments()]
        print(json.dumps(results, indent=2))
        for r in results:
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['scenario']}")
        return 0 if all(r["passed"] for r in results) else 2
    if args.cmd == "loadtest":
        from ragbench.reliability import run_load

        p = Pipeline()
        if p.store.count_documents() == 0:
            print("No documents indexed. Run `ragbench ingest evaluation/datasets/corpus` first.")
            return 1
        qs = ["what is reciprocal rank fusion", "what is bm25", "what is nDCG",
              "how do embeddings work", "what causes E1042"]
        print(json.dumps(run_load(p, qs, n=args.n, strategy=args.strategy,
                                  concurrency=args.concurrency), indent=2))
        return 0

    pipeline = Pipeline()
    if args.cmd == "ingest":
        return _ingest(pipeline, args.path)
    if args.cmd == "query":
        return _query(pipeline, args.question, args.strategy)
    if args.cmd == "stats":
        print(json.dumps(pipeline.stats(), indent=2))
        return 0
    if args.cmd == "index-health":
        print(json.dumps(pipeline.index_health(), indent=2))
        return 0
    if args.cmd == "reindex":
        print(json.dumps(pipeline.reindex(), indent=2))
        return 0
    if args.cmd == "runs":
        from ragbench.storage import RunRegistry

        reg = RunRegistry(pipeline.config.runs_db_path)
        print(json.dumps(reg.list_runs(limit=args.limit), indent=2))
        reg.close()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
