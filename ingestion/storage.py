"""Raw layer writer: timestamped Parquet in data/raw/, partitioned by extraction date.

Idempotence: one deterministic file per dataset per extraction date, replaced
on rerun (write-by-replacement) — running twice on the same day yields the
same state. Row counts are checked between API payload and written file;
a mismatch raises instead of dropping rows silently.
"""

import logging
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

SOURCE_FOOTBALL_DATA = "football-data.org"


class RowCountMismatchError(Exception):
    """Rows written differ from rows received — never drop rows silently."""


def matches_to_rows(payload: dict) -> list[dict]:
    """One row per match, every API field preserved."""
    return list(payload.get("matches", []))


def standings_to_rows(payload: dict) -> list[dict]:
    """One row per standings table entry, with its group context and the
    payload-level competition/season preserved as nested fields."""
    competition = payload.get("competition")
    season = payload.get("season")
    rows = []
    for group in payload.get("standings", []):
        context = {k: v for k, v in group.items() if k != "table"}
        for entry in group.get("table", []):
            rows.append(
                {**entry, "standing": context, "competition": competition, "season": season}
            )
    return rows


def scorers_to_rows(payload: dict) -> list[dict]:
    """One row per scorer, every API field preserved (player/team as structs)."""
    return list(payload.get("scorers", []))


def write_raw_parquet(
    rows: list[dict],
    *,
    dataset: str,
    root: Path,
    extracted_at: datetime,
    source: str = SOURCE_FOOTBALL_DATA,
) -> Path | None:
    """Write rows to root/<source dir>/<dataset>/extraction_date=YYYY-MM-DD/<dataset>.parquet.

    Returns the written path, or None when there is nothing to write
    (logged explicitly, never silent).
    """
    rows_in = len(rows)
    if rows_in == 0:
        logger.warning("%s: 0 rows received, nothing written", dataset)
        return None

    table = pa.Table.from_pylist(rows)
    table = table.append_column(
        "extracted_at", pa.array([extracted_at] * rows_in, pa.timestamp("us", tz="UTC"))
    )
    table = table.append_column("source", pa.array([source] * rows_in, pa.string()))

    partition = f"extraction_date={extracted_at.date().isoformat()}"
    target_dir = root / "football_data" / dataset / partition
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{dataset}.parquet"

    # Atomic replacement: never leave a half-written file at the final path.
    tmp = target.with_suffix(".parquet.tmp")
    pq.write_table(table, tmp)
    tmp.replace(target)

    rows_out = pq.read_metadata(target).num_rows
    if rows_out != rows_in:
        raise RowCountMismatchError(f"{dataset}: {rows_in} rows in, {rows_out} rows written")
    logger.info("%s: %d rows in -> %d rows written -> %s", dataset, rows_in, rows_out, target)
    return target
