"""Reconcile FBref's real basic team stats (source #3) with `dim_teams`.

FBref and dim_teams (football-data.org, via dbt) name a handful of teams
differently — mostly short-form vs. long-form country names, plus one
typographic dash. This mapping is explicit rather than fuzzy-matched, so a
future team-name drift fails loudly (`ReconciliationError`) instead of
silently dropping a team from the reality check.
"""

from __future__ import annotations

import csv
from pathlib import Path

RAW = Path("data/raw/fbref/team_basic_2026.csv")

# FBref team name -> dim_teams team name. Every team FBref names
# differently from dim_teams; every other team matches by identity.
NAME_MAP: dict[str, str] = {
    "Bosnia–Herz": "Bosnia-Herzegovina",
    "Cabo Verde": "Cape Verde Islands",
    "Côte d'Ivoire": "Ivory Coast",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
}

FLOAT_COLUMNS = ("possession", "sot_pct", "g_per_sh", "save_pct")
INT_COLUMNS = ("shots", "sot", "ga", "sota", "saves", "cs", "crdy", "crdr")


class ReconciliationError(Exception):
    """One or more FBref team names did not resolve to a dim_teams name."""


def _row_to_stats(row: dict[str, str]) -> dict[str, float | int]:
    stats: dict[str, float | int] = {c: float(row[c]) for c in FLOAT_COLUMNS}
    stats.update({c: int(float(row[c])) for c in INT_COLUMNS})
    return stats


def load_fbref_real(dim_team_names: set[str]) -> dict[str, dict[str, float | int]]:
    """Return {dim_teams team_name: real stats}, reconciled via NAME_MAP.

    Empty dict if the FBref archive hasn't been fetched yet (mirrors
    `real_stats.load_spain_real`'s "absent source" handling). Raises
    `ReconciliationError` listing every FBref name that still didn't match
    a name in `dim_team_names` after NAME_MAP — the sprint's core risk,
    made loud instead of silently dropped.
    """
    if not RAW.exists():
        return {}

    with RAW.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    unmatched: list[str] = []
    out: dict[str, dict[str, float | int]] = {}
    for row in rows:
        fbref_name = row["team"]
        dim_name = NAME_MAP.get(fbref_name, fbref_name)
        if dim_name not in dim_team_names:
            unmatched.append(fbref_name)
            continue
        out[dim_name] = _row_to_stats(row)

    if unmatched:
        raise ReconciliationError(
            f"{len(unmatched)} FBref team(s) did not match dim_teams: {sorted(unmatched)}"
        )
    return out
