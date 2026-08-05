"""Run-level observability: every pipeline stage appends one record per
dataset to data/ops/runs.jsonl.

Why JSONL in git rather than a warehouse table: the DuckDB file is rebuilt
from scratch on every CI run, so anything written there is amnesiac. The
run log rides in the same daily data PR as the raw archive — append-only,
diffable in review, queryable with read_json_auto, and it survives every
rebuild. The export stage surfaces the recent history on the dashboard.

Record shape (one JSON object per line):
    run_id       ISO timestamp of the run start (UTC) — groups datasets
    stage        "ingestion" | "analytics"
    dataset      e.g. "matches", "team_strength"
    rows         rows written (0 = nothing to write, logged upstream)
    duration_s   stage-level wall time for this dataset
    status       "ok" | "failed"
    error        short message when status == "failed"
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OPS_PATH = Path("data/ops/runs.jsonl")


def record_run(
    *,
    run_id: str,
    stage: str,
    dataset: str,
    rows: int,
    duration_s: float,
    status: str = "ok",
    error: str | None = None,
    path: Path = OPS_PATH,
) -> dict[str, Any]:
    """Append one run record; returns the record. Never raises — a broken
    ops log must not fail a healthy pipeline run (it logs instead)."""
    record: dict[str, Any] = {
        "run_id": run_id,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "stage": stage,
        "dataset": dataset,
        "rows": rows,
        "duration_s": round(duration_s, 2),
        "status": status,
    }
    if error:
        record["error"] = error[:300]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("could not append to the ops run log at %s", path)
    return record


def read_runs(path: Path = OPS_PATH, limit: int | None = None) -> list[dict[str, Any]]:
    """Most-recent-last list of run records; tolerant of a missing file."""
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("skipping malformed ops record: %s", line[:120])
    return records[-limit:] if limit else records
