"""Daily ingestion entry point: `uv run python -m ingestion`.

Fetches World Cup matches and standings from football-data.org and archives
them as Parquet in data/raw/, partitioned by extraction date.
"""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from ingestion.client import FootballDataClient
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
    logger.info("ingestion run starting (extracted_at=%s)", extracted_at.isoformat())

    with FootballDataClient() as client:
        matches_payload = client.fetch_matches()
        standings_payload = client.fetch_standings()
        scorers_payload = client.fetch_scorers()

    # Schema contracts run between fetch and write: a missing or retyped core
    # field fails the run here, at the boundary, before anything is archived.
    written = [
        write_raw_parquet(
            validate_rows(matches_to_rows(matches_payload), dataset="matches"),
            dataset="matches",
            root=RAW_ROOT,
            extracted_at=extracted_at,
        ),
        write_raw_parquet(
            validate_rows(standings_to_rows(standings_payload), dataset="standings"),
            dataset="standings",
            root=RAW_ROOT,
            extracted_at=extracted_at,
        ),
        write_raw_parquet(
            validate_rows(scorers_to_rows(scorers_payload), dataset="scorers"),
            dataset="scorers",
            root=RAW_ROOT,
            extracted_at=extracted_at,
        ),
    ]
    logger.info(
        "ingestion run done: %d/%d datasets written",
        sum(p is not None for p in written),
        len(written),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
