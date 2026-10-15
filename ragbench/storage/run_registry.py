"""Persistent registry of evaluation runs.

Each recorded run captures enough metadata to trace a result back to the
dataset, code revision, and configuration that produced it: run_id, timestamp,
git commit, dataset version, index version, the full config block, a metrics
summary, and the path to the full report artifact. Stored in its own SQLite
database so it survives across processes independently of the document store.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    git_commit TEXT,
    dataset_version TEXT,
    index_version TEXT,
    config_json TEXT,
    metrics_json TEXT,
    report_path TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class RunRegistry:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def record(self, report: dict, report_path: str | None = None) -> str:
        # A compact metrics summary per baseline (traceable, not the whole report).
        metrics = {
            b["name"]: b["aggregate"] for b in report.get("baselines", [])
        }
        self.conn.execute(
            "INSERT OR REPLACE INTO evaluation_runs(run_id, timestamp, git_commit,"
            " dataset_version, index_version, config_json, metrics_json, report_path)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                report["run_id"], report["timestamp"], report.get("git_commit"),
                report.get("dataset_version"),
                report.get("config", {}).get("index_version"),
                json.dumps(report.get("config", {})),
                json.dumps(metrics),
                report_path,
            ),
        )
        self.conn.commit()
        return report["run_id"]

    def list_runs(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT run_id, timestamp, git_commit, dataset_version, index_version,"
            " report_path FROM evaluation_runs ORDER BY recorded_at DESC, run_id LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM evaluation_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["config"] = json.loads(d.pop("config_json") or "{}")
        d["metrics"] = json.loads(d.pop("metrics_json") or "{}")
        return d

    def close(self) -> None:
        self.conn.close()
