"""Contract tests on the exported JSON — the interface the front consumes.

The Astro build imports these files statically: a silently renamed or
missing key does not break the build, it renders `undefined` into the
page. These tests pin the minimum shape of every file the front imports,
so an interface break fails CI instead of shipping a broken UI.

Marked `contract`: they read the committed dashboard/src/data files (in
the daily workflow those are regenerated two steps earlier), so they are
excluded from the default unit run and executed after dbt build in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

DATA_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "src" / "data"

# file -> (is_list, required keys of the object / of each row)
CONTRACTS: dict[str, tuple[bool, set[str]]] = {
    "key_metrics.json": (
        False,
        {"matches_total", "matches_played", "goals_scored", "teams", "avg_goals_per_match"},
    ),
    "metadata.json": (
        False,
        {
            "generated_at",
            "last_ingestion",
            "source",
            "dbt_nodes_passed",
            "dbt_nodes_total",
            "reconciliation",
            "ops",
        },
    ),
    "champion.json": (False, {"final", "champion"}),
    "groups.json": (True, {"group_code", "standings"}),
    "bracket.json": (True, {"stage", "label", "matches"}),
    "goals_by_stage.json": (True, {"stage", "goals"}),
    "scorelines.json": (True, {"scoreline", "count"}),
    "results_split.json": (False, {"home_wins", "draws", "away_wins"}),
    "edition_comparison.json": (
        False,
        {"editions", "current_year", "current_goals_per_match", "current_rank", "total_editions"},
    ),
    "top_scorers.json": (True, {"rank", "player_name", "team_tla", "goals", "assists"}),
    "team_strength.json": (
        True,
        {
            "team_id",
            "team_name",
            "attack",
            "defense",
            "rating",
            "rank_overall",
            "rank_attack",
            "rank_defense",
            "points",
            "xpoints",
            "performance",
        },
    ),
    "team_reality.json": (
        True,
        {
            "team_id",
            "team_name",
            "rank_overall",
            "rank_attack",
            "rank_defense",
            "attack",
            "defense",
            "possession",
            "shots",
            "sota",
            "ga",
            "save_pct",
            "conversion",
        },
    ),
    "spain_case.json": (
        False,
        {
            "points",
            "xpoints",
            "performance",
            "xga",
            "xgf",
            "goals_for",
            "goals_against",
            "rank_attack",
            "title_prob",
        },
    ),
    "spain_path.json": (True, {"stage", "opponent", "score", "win_prob"}),
    "spain_real.json": (
        True,
        {"opponent", "possession", "xg_for", "xg_against", "shots", "model_xg_for"},
    ),
    "spain_final_shots.json": (False, {"opponent", "shots"}),
    "title_odds.json": (True, {"team_tla", "title_prob"}),
    "title_progression.json": (False, {"levels", "teams"}),
    "model_meta.json": (
        False,
        {"generated_at", "n_teams", "n_matches", "home_adv", "ridge", "final_nll", "n_sims"},
    ),
}


@pytest.mark.parametrize("filename", sorted(CONTRACTS))
def test_exported_file_honours_its_contract(filename: str):
    path = DATA_DIR / filename
    assert path.exists(), f"{filename} missing from the export"
    payload = json.loads(path.read_text(encoding="utf-8"))
    is_list, required = CONTRACTS[filename]
    if is_list:
        assert isinstance(payload, list) and payload, f"{filename}: expected a non-empty list"
        missing = required - payload[0].keys()
    else:
        assert isinstance(payload, dict), f"{filename}: expected an object"
        missing = required - payload.keys()
    assert not missing, f"{filename}: missing keys {sorted(missing)}"


def test_every_front_imported_file_has_a_contract():
    """If the front starts importing a new export, it must get a contract."""
    import re

    src = Path(__file__).resolve().parents[1] / "dashboard" / "src"
    imported: set[str] = set()
    for astro in src.rglob("*.astro"):
        imported.update(re.findall(r"data/([a-z_]+\.json)", astro.read_text(encoding="utf-8")))
    uncovered = imported - set(CONTRACTS)
    assert not uncovered, f"front imports without a contract: {sorted(uncovered)}"
