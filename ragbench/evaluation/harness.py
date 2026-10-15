"""Reproducible retrieval-evaluation harness.

Runs the configured baselines through ONE code path over a pinned dataset and
corpus, computes retrieval and abstention metrics per query category and in
aggregate, and emits a machine-readable report with full run metadata. The
harness requires no external model APIs: it uses the offline providers.

Baselines:
  B0 bm25           - sparse only
  B1 dense          - dense only
  B2 hybrid         - RRF(bm25, dense)
  B3 hybrid+rerank  - hybrid candidates reordered by the heuristic reranker
"""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ragbench.config import Config
from ragbench.evaluation.metrics import (
    hit_at_k,
    mean_ignoring_none,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
)
from ragbench.ingestion.parsing import SUPPORTED_SUFFIXES
from ragbench.models import RetrievalResult
from ragbench.pipeline import Pipeline
from ragbench.reranking import HeuristicReranker
from ragbench.storage import SQLiteStore

BASELINES = [
    ("B0_bm25", "bm25", False),
    ("B1_dense", "dense", False),
    ("B2_hybrid", "hybrid", False),
    ("B3_hybrid_rerank", "hybrid", True),
]


@dataclass
class BenchmarkCase:
    id: str
    question: str
    category: str
    answerable: bool
    relevant_doc_keys: list[str]
    expected_abstention: bool


@dataclass
class EvalConfig:
    corpus_dir: str
    dataset_path: str
    k: int = 5


@dataclass
class BaselineResult:
    name: str
    strategy: str
    reranked: bool
    aggregate: dict = field(default_factory=dict)
    by_category: dict = field(default_factory=dict)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_dataset(path: str) -> tuple[dict, list[BenchmarkCase]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [
        BenchmarkCase(
            id=c["id"], question=c["question"], category=c["category"],
            answerable=c["answerable"], relevant_doc_keys=c["relevant_doc_keys"],
            expected_abstention=c["expected_abstention"],
        )
        for c in data["cases"]
    ]
    return data, cases


class Harness:
    def __init__(self, eval_config: EvalConfig, config: Config | None = None) -> None:
        self.eval_config = eval_config
        self.config = config or Config()
        self.pipeline = Pipeline(config=self.config, store=SQLiteStore(":memory:"))
        self.reranker = HeuristicReranker(self.pipeline.embedder)
        self.key_to_doc: dict[str, str] = {}

    def _ingest_corpus(self) -> None:
        for f in sorted(Path(self.eval_config.corpus_dir).rglob("*")):
            if f.suffix.lower() in SUPPORTED_SUFFIXES:
                doc = self.pipeline.ingest_bytes(f.read_bytes(), f.name, f.suffix)
                self.key_to_doc[f.stem] = doc.id

    def _ranked_docs(self, question: str, strategy: str, reranked: bool) -> list[RetrievalResult]:
        retriever = self.pipeline._ensure_retriever()
        pool = max(self.eval_config.k * 4, 20)
        results = retriever.retrieve(question, strategy, pool)
        if reranked:
            results = self.reranker(question, results)
        return results

    def _doc_ranking(self, results: list[RetrievalResult]) -> list[str]:
        seen: set[str] = set()
        order: list[str] = []
        for r in results:
            if r.document_id not in seen:
                seen.add(r.document_id)
                order.append(r.document_id)
        return order

    def run(self) -> dict:
        self._ingest_corpus()
        data, cases = load_dataset(self.eval_config.dataset_path)
        k = self.eval_config.k
        report_baselines: list[dict] = []

        for name, strategy, reranked in BASELINES:
            per_case = []
            for case in cases:
                relevant = {self.key_to_doc[key] for key in case.relevant_doc_keys
                            if key in self.key_to_doc}
                results = self._ranked_docs(case.question, strategy, reranked)
                doc_ranking = self._doc_ranking(results)
                # Abstention consistent with the production pipeline logic.
                evidence = self.pipeline._evidence_score(case.question, results)
                abstained = (not results) or (evidence < self.config.abstain_min_score)
                per_case.append({
                    "id": case.id, "category": case.category,
                    "recall": recall_at_k(doc_ranking, relevant, k),
                    "mrr": mrr_at_k(doc_ranking, relevant, k),
                    "ndcg": ndcg_at_k(doc_ranking, relevant, k),
                    "hit": hit_at_k(doc_ranking, relevant, k),
                    "abstained": abstained,
                    "expected_abstention": case.expected_abstention,
                })
            report_baselines.append(
                self._summarize(name, strategy, reranked, per_case, k)
            )

        return {
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "dataset_version": data.get("dataset_version"),
            "dataset_provenance": data.get("provenance"),
            "num_cases": len(cases),
            "k": k,
            "config": {
                "index_version": self.config.index_version,
                "embedding_provider": self.pipeline.embedder.name,
                "rrf_k": self.config.rrf_k,
                "abstain_min_score": self.config.abstain_min_score,
                "reranker": self.reranker.name,
            },
            "baselines": report_baselines,
        }

    @staticmethod
    def _abstention_prf(per_case: list[dict]) -> dict:
        # Positive class = "should abstain". Precision/recall of abstaining.
        tp = sum(1 for c in per_case if c["expected_abstention"] and c["abstained"])
        fp = sum(1 for c in per_case if not c["expected_abstention"] and c["abstained"])
        fn = sum(1 for c in per_case if c["expected_abstention"] and not c["abstained"])
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn}

    def _summarize(self, name, strategy, reranked, per_case, k) -> dict:
        def agg(metric: str, subset: list[dict]) -> float | None:
            return mean_ignoring_none([c[metric] for c in subset])

        categories = sorted({c["category"] for c in per_case})
        by_cat = {}
        for cat in categories:
            subset = [c for c in per_case if c["category"] == cat]
            correct_abstain = sum(
                1 for c in subset if c["abstained"] == c["expected_abstention"]
            )
            by_cat[cat] = {
                f"recall@{k}": agg("recall", subset),
                f"mrr@{k}": agg("mrr", subset),
                f"ndcg@{k}": agg("ndcg", subset),
                f"hit@{k}": agg("hit", subset),
                "abstain_accuracy": correct_abstain / len(subset) if subset else None,
                "n": len(subset),
            }
        return {
            "name": name, "strategy": strategy, "reranked": reranked,
            "aggregate": {
                f"recall@{k}": agg("recall", per_case),
                f"mrr@{k}": agg("mrr", per_case),
                f"ndcg@{k}": agg("ndcg", per_case),
                f"hit@{k}": agg("hit", per_case),
                "abstention": self._abstention_prf(per_case),
            },
            "by_category": by_cat,
        }


def run_benchmark(corpus_dir: str, dataset_path: str, k: int = 5,
                  config: Config | None = None) -> dict:
    return Harness(EvalConfig(corpus_dir, dataset_path, k), config).run()


def write_report(report: dict, out_dir: str = "evaluation/reports") -> tuple[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    stamp = report["timestamp"].replace(":", "").replace("-", "")[:15]
    json_path = Path(out_dir) / f"benchmark_{stamp}_{report['run_id'][:8]}.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path = json_path.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return str(json_path), str(md_path)


def render_markdown(report: dict) -> str:
    k = report["k"]
    lines = [
        f"# Benchmark report {report['run_id'][:8]}",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- timestamp: {report['timestamp']}",
        f"- git_commit: `{report['git_commit']}`",
        f"- dataset_version: {report['dataset_version']}",
        f"- cases: {report['num_cases']}, k={k}",
        f"- index_version: `{report['config']['index_version']}`",
        f"- embedding_provider: `{report['config']['embedding_provider']}`",
        f"- reranker: `{report['config']['reranker']}`",
        "",
        "## Aggregate (all cases with relevance labels)",
        "",
        f"| Baseline | recall@{k} | mrr@{k} | ndcg@{k} | hit@{k} | abstain P | abstain R |",
        "|---|---|---|---|---|---|---|",
    ]

    def fmt(x):
        return "n/a" if x is None else f"{x:.3f}"

    for b in report["baselines"]:
        a = b["aggregate"]
        ab = a["abstention"]
        lines.append(
            f"| {b['name']} | {fmt(a[f'recall@{k}'])} | {fmt(a[f'mrr@{k}'])} | "
            f"{fmt(a[f'ndcg@{k}'])} | {fmt(a[f'hit@{k}'])} | "
            f"{fmt(ab['precision'])} | {fmt(ab['recall'])} |"
        )
    lines += ["", "## Notes",
              "- Metrics are at document relevance granularity (see dataset provenance).",
              "- Cases without relevance labels (unanswerable/ambiguous/etc.) are excluded "
              "from recall/mrr/ndcg means and appear only in abstention precision/recall.",
              "- Scores depend on the deterministic fake embedding; absolute values are not "
              "comparable to a real embedding model."]
    return "\n".join(lines) + "\n"
