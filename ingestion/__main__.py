"""Daily ingestion entry point: `uv run python -m ingestion`.

Fetches World Cup matches and standings from football-data.org and archives
them as Parquet in data/raw/, partitioned by extraction date.
"""

import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from ingestion.client import FootballDataClient
from ingestion.ops import record_run
from ingestion.schemas import validate_rows
from ingestion.storage import (
    matches_to_rows,
    scorers_to_rows,
    standings_to_rows,
    write_raw_parquet,
)

logger = logging.getLogger("ingestion")

RAW_ROOT = Path("data/raw")


def main() -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    extracted_at = datetime.now(UTC)
    run_id = extracted_at.isoformat(timespec="seconds")
    logger.info("ingestion run starting (extracted_at=%s)", run_id)

    with FootballDataClient() as client:
        matches_payload = client.fetch_matches()
        standings_payload = client.fetch_standings()
        scorers_payload = client.fetch_scorers()

    # Schema contracts run between fetch and write: a missing or retyped core
    # field fails the run here, at the boundary, before anything is archived.
    written = 0
    for dataset, to_rows, payload in (
        ("matches", matches_to_rows, matches_payload),
        ("standings", standings_to_rows, standings_payload),
        ("scorers", scorers_to_rows, scorers_payload),
    ):
        started = time.monotonic()
        try:
            rows = validate_rows(to_rows(payload), dataset=dataset)
            path = write_raw_parquet(
                rows, dataset=dataset, root=RAW_ROOT, extracted_at=extracted_at
            )
            record_run(
                run_id=run_id,
                stage="ingestion",
                dataset=dataset,
                rows=len(rows) if path is not None else 0,
                duration_s=time.monotonic() - started,
            )
            written += path is not None
        except Exception as exc:
            record_run(
                run_id=run_id,
                stage="ingestion",
                dataset=dataset,
                rows=0,
                duration_s=time.monotonic() - started,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

    logger.info("ingestion run done: %d/3 datasets written", written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
