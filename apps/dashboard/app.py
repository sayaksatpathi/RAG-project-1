"""RAGBench Streamlit dashboard.

Screens: RAG Playground, Document Management, Experiment Comparison, Quality
Gate, and Operations. The dashboard calls real pipeline/service behavior and
shows honest empty states — it never seeds fictional values. Run:

    streamlit run apps/dashboard/app.py

Uses the offline providers by default, so it works with no paid API.
"""

from __future__ import annotations

import glob
import json
import time
from pathlib import Path

import streamlit as st

from ragbench.config import load_config
from ragbench.pipeline import Pipeline

st.set_page_config(page_title="RAGBench", layout="wide")


@st.cache_resource
def get_pipeline() -> Pipeline:
    return Pipeline(config=load_config())


pipeline = get_pipeline()
page = st.sidebar.radio(
    "View",
    ["RAG Playground", "Documents", "Experiment Comparison", "Quality Gate", "Operations"],
)
st.sidebar.caption(f"index: {pipeline.config.index_version}")


def _playground() -> None:
    st.header("RAG Playground")
    q = st.text_input("Question", placeholder="e.g. What is reciprocal rank fusion?")
    strategy = st.selectbox("Strategy", ["hybrid", "bm25", "dense", "adaptive"])
    if not q:
        st.info("Enter a question to run a grounded query.")
        return
    start = time.perf_counter()
    ans = pipeline.query(q, strategy=strategy)
    latency_ms = (time.perf_counter() - start) * 1000

    if ans.abstained:
        st.warning("The system abstained: insufficient supporting evidence.")
    else:
        st.success(ans.text)
    c1, c2, c3 = st.columns(3)
    c1.metric("Strategy", ans.retrieval_strategy)
    c2.metric("Abstained", "yes" if ans.abstained else "no")
    c3.metric("Latency (ms)", f"{latency_ms:.1f}")

    st.subheader("Citations")
    if ans.citations:
        st.table([{"chunk_id": c.chunk_id, "document_id": c.document_id, "valid": c.valid}
                  for c in ans.citations])
    else:
        st.caption("No citations (the system abstained or found no evidence).")

    st.subheader("Retrieved passages")
    retrieved = pipeline.retrieve(q, strategy if strategy != "adaptive" else "hybrid")
    if retrieved:
        st.table([{"rank": r.rank, "chunk_id": r.chunk_id, "score": round(r.score, 4),
                   "text": r.text[:160]} for r in retrieved])
    else:
        st.caption("No passages retrieved.")
    if ans.warnings:
        st.caption("Warnings: " + "; ".join(ans.warnings))


def _documents() -> None:
    st.header("Document Management")
    st.caption(f"Active config: {pipeline.stats()['index_version']}")
    up = st.file_uploader("Upload a .txt or .md document", type=["txt", "md", "markdown"])
    if up is not None and st.button("Ingest"):
        suffix = "." + up.name.rsplit(".", 1)[-1]
        try:
            doc = pipeline.ingest_bytes(up.getvalue(), up.name, suffix)
            st.success(f"Ingested {doc.filename} -> {doc.id} ({doc.num_chunks} chunks)")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Ingestion failed: {exc}")

    docs = pipeline.store.list_documents(limit=200)
    if not docs:
        st.info("No documents indexed yet. Upload one above, or run "
                "`ragbench ingest evaluation/datasets/corpus`.")
        return
    st.table([{"id": d.id, "filename": d.filename, "status": d.status,
               "chunks": d.num_chunks, "created": d.created_at} for d in docs])


def _experiments() -> None:
    st.header("Experiment Comparison")
    reports = sorted(glob.glob("evaluation/reports/*.json"))
    if not reports:
        st.info("No benchmark reports found. Run `ragbench evaluate` to generate one.")
        return
    choice = st.selectbox("Report", reports, format_func=lambda p: Path(p).name)
    report = json.loads(Path(choice).read_text(encoding="utf-8"))
    st.caption(f"run {report['run_id'][:8]} · {report['timestamp']} · "
               f"dataset {report['dataset_version']} · k={report['k']}")
    rows = []
    for b in report["baselines"]:
        a = b["aggregate"]
        rows.append({
            "baseline": b["name"],
            f"recall@{report['k']}": a.get(f"recall@{report['k']}"),
            f"mrr@{report['k']}": a.get(f"mrr@{report['k']}"),
            f"ndcg@{report['k']}": a.get(f"ndcg@{report['k']}"),
            "abstain_P": a["abstention"]["precision"],
            "abstain_R": a["abstention"]["recall"],
        })
    st.table(rows)
    if report.get("ablation"):
        st.subheader("Ablation")
        st.json(report["ablation"])


def _quality_gate() -> None:
    st.header("Quality Gate")
    policy_path = Path("evaluation/gate_policy.json")
    if not policy_path.exists():
        st.info("No gate policy found at evaluation/gate_policy.json.")
        return
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    st.caption(f"policy v{policy['policy_version']} · k={policy['k']}")
    st.subheader("Hard gates")
    st.table([{"metric": m, **spec} for m, spec in policy["hard_gates"].items()])
    st.subheader("Warning metrics")
    st.table([{"metric": m, **spec} for m, spec in policy.get("warning_metrics", {}).items()])
    st.caption("Run `ragbench gate-demo` to see a candidate rejected/accepted "
               "against an approved baseline.")


def _operations() -> None:
    st.header("Operations")
    stats = pipeline.stats()
    c1, c2 = st.columns(2)
    c1.metric("Indexed documents", stats["documents"])
    c2.metric("LLM provider", stats["llm_provider"])
    st.json(stats)
    st.caption("Live request metrics are exported by the API at /metrics "
               "(Prometheus format). This dashboard reads pipeline state directly; "
               "start the API and scrape /metrics for request-level telemetry.")


{
    "RAG Playground": _playground,
    "Documents": _documents,
    "Experiment Comparison": _experiments,
    "Quality Gate": _quality_gate,
    "Operations": _operations,
}[page]()
