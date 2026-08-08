"""Tests for the FBref <-> dim_teams name reconciliation (ADR-0006) — the
sprint's core risk: FBref and dim_teams name a handful of teams
differently, and a missed mapping must never mean a team silently
vanishes from a "48 teams" claim.
"""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from analytics.real_fbref import NAME_MAP, ReconciliationError, load_fbref_real

RAW_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "fbref" / "team_basic_2026.csv"
WAREHOUSE = Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"


def _archived_teams() -> list[str]:
    with RAW_CSV.open(encoding="utf-8") as f:
        return [row["team"] for row in csv.DictReader(f)]


def _dim_team_names() -> set[str]:
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    names = {r[0] for r in con.execute("select team_name from main.dim_teams").fetchall()}
    con.close()
    return names


def test_versioned_archive_has_48_unique_teams():
    teams = _archived_teams()
    assert len(teams) == 48
    assert len(set(teams)) == 48


def test_name_map_keys_appear_in_the_archived_teams():
    """A stale or typo'd NAME_MAP key would silently do nothing — catch it."""
    archived = set(_archived_teams())
    stale = set(NAME_MAP) - archived
    assert not stale, f"NAME_MAP keys not present in the FBref archive: {stale}"


def test_name_map_values_are_distinct():
    """Two FBref names mapping to the same dim_teams name would overwrite
    one team's row with another's in load_fbref_real's output dict."""
    targets = list(NAME_MAP.values())
    assert len(targets) == len(set(targets))


def test_unmapped_fbref_name_raises_instead_of_silently_dropping(tmp_path, monkeypatch):
    """A reconciliation gap must fail loudly, never disappear a team."""
    import analytics.real_fbref as real_fbref

    fake_csv = tmp_path / "team_basic_2026.csv"
    fake_csv.write_text(
        "team,possession,shots,sot,sot_pct,g_per_sh,ga,sota,saves,save_pct,cs,crdy,crdr\n"
        "Nowhereland,50.0,10,5,50.0,0.1,1,5,4,80.0,1,2,0\n"
    )
    monkeypatch.setattr(real_fbref, "RAW", fake_csv)
    with pytest.raises(ReconciliationError):
        real_fbref.load_fbref_real({"Spain"})


@pytest.mark.contract
def test_zero_unmatched_against_the_real_48_dim_teams():
    """The reconciliation's actual DoD: every dim_teams team resolves to a
    FBref row, and every FBref team resolves to a dim_teams name — 0
    unmatched in either direction. Marked `contract`: needs the dbt-built
    warehouse for the true dim_teams list, same reason as
    test_export_contract.py's tests."""
    dim_names = _dim_team_names()
    assert len(dim_names) == 48
    real = load_fbref_real(dim_names)
    assert set(real) == dim_names
