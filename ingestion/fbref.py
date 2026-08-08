"""One-off ingestion of basic real team statistics from FBref (via
`soccerdata`) — source #3. For international competitions FBref only
exposes 5 aggregated season tables (standard, keeper, shooting,
playing_time, misc), and **none of them carries an "Expected" column for
the 2026 World Cup** — confirmed by inspection, not assumed (see
ADR-0006). What we do get: real shot volumes, goalkeeper numbers and
cards — a genuine reality check on the model's ratings, just not xG.

The 2026 tournament is over, so this data is static and already archived
under data/raw/fbref/. This script documents *how* it was fetched and can
reproduce it, but refuses to re-fetch (and re-solve FBref's Cloudflare
challenge) when the archive already exists, unless called with --force.

    uv run python -m ingestion.fbref            # no-op if already archived
    uv run python -m ingestion.fbref --force     # re-fetch
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import cast

import pandas as pd

logger = logging.getLogger("ingestion.fbref")

LEAGUE = "INT-World Cup"
SEASON = 2026
EXPECTED_TEAMS = 48
OUT = Path("data/raw/fbref")

# stat_type -> {FBref column tuple: output column name}. Only the columns
# the reality-check join actually needs; the rest of each table (per-90
# rates, subs, fouls...) is left on FBref rather than copied wholesale.
TABLE_COLUMNS: dict[str, dict[tuple[str, str], str]] = {
    "standard": {("Poss", ""): "possession"},
    "shooting": {
        ("Standard", "Sh"): "shots",
        ("Standard", "SoT"): "sot",
        ("Standard", "SoT%"): "sot_pct",
        ("Standard", "G/Sh"): "g_per_sh",
    },
    "keeper": {
        ("Performance", "GA"): "ga",
        ("Performance", "SoTA"): "sota",
        ("Performance", "Saves"): "saves",
        ("Performance", "Save%"): "save_pct",
        ("Performance", "CS"): "cs",
    },
    "misc": {
        ("Performance", "CrdY"): "crdy",
        ("Performance", "CrdR"): "crdr",
    },
}
# Fetched to keep the 5-table shape FBref actually offers for this
# competition, but not part of the export: playing_time only adds
# minutes/subs detail, already redundant with matches-played elsewhere.
UNUSED_TABLE = "playing_time"

ALL_TABLES = (*TABLE_COLUMNS, UNUSED_TABLE)


def _fetch_table(fb, stat_type: str) -> pd.DataFrame:
    df = fb.read_team_season_stats(stat_type=stat_type).reset_index()
    if len(df) != EXPECTED_TEAMS:
        raise RuntimeError(f"{stat_type}: expected {EXPECTED_TEAMS} teams, got {len(df)}")
    return df


def run(force: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    archive = OUT / "team_basic_2026.csv"
    if archive.exists() and not force:
        logger.info(
            "archive already present at %s — skipping (pass --force to re-fetch)", archive
        )
        return 0

    import soccerdata as sd  # heavy optional dep — only imported on an actual fetch

    fb = sd.FBref(leagues=LEAGUE, seasons=SEASON)

    merged: pd.DataFrame | None = None
    for stat_type, columns in TABLE_COLUMNS.items():
        df = _fetch_table(fb, stat_type)
        subset = cast(pd.DataFrame, df[[("team", ""), *columns]].copy())
        subset.columns = ["team", *columns.values()]
        merged = subset if merged is None else merged.merge(subset, on="team", validate="one_to_one")
        logger.info("%s: %d teams, kept %s", stat_type, len(subset), list(columns.values()))

    _fetch_table(fb, UNUSED_TABLE)  # verifies the 5th table has the same shape, unused otherwise

    assert merged is not None
    if len(merged) != EXPECTED_TEAMS or merged["team"].nunique() != EXPECTED_TEAMS:
        raise RuntimeError(f"expected {EXPECTED_TEAMS} unique teams after merge, got {len(merged)}")

    OUT.mkdir(parents=True, exist_ok=True)
    merged.sort_values("team").to_csv(archive, index=False)
    logger.info("saved -> %s (%d teams, %d columns)", archive, len(merged), len(merged.columns))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-fetch even if the archive exists"
    )
    args = parser.parse_args()
    return run(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
