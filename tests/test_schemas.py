"""Tests for the raw-layer schema contracts (drift policy at the boundary)."""

import logging

import pytest

from ingestion.schemas import SchemaContractError, validate_rows

VALID_MATCH = {
    "id": 1,
    "utcDate": "2026-06-11T20:00:00Z",
    "status": "FINISHED",
    "stage": "GROUP_STAGE",
    "group": "GROUP_A",
    "homeTeam": {"id": 10, "name": "Mexico"},
    "awayTeam": {"id": 11, "name": "South Africa"},
    "score": {"fullTime": {"home": 2, "away": 0}},
    "lastUpdated": "2026-06-12T00:00:00Z",
}


def test_valid_rows_pass_through_unchanged():
    rows = [VALID_MATCH]
    assert validate_rows(rows, dataset="matches") is rows


def test_nullable_core_field_accepts_none():
    row = {**VALID_MATCH, "group": None}  # knockout matches have no group
    assert validate_rows([row], dataset="matches") == [row]


def test_unknown_fields_are_accepted_and_logged(caplog):
    row = {**VALID_MATCH, "brandNewApiField": {"anything": True}}
    with caplog.at_level(logging.INFO, logger="ingestion.schemas"):
        validate_rows([row], dataset="matches")
    assert "brandNewApiField" in caplog.text
    assert "accepted" in caplog.text


def test_missing_core_field_raises_naming_the_field():
    row = {k: v for k, v in VALID_MATCH.items() if k != "utcDate"}
    with pytest.raises(SchemaContractError, match="missing core field 'utcDate'"):
        validate_rows([row], dataset="matches")


def test_mistyped_core_field_raises_naming_the_type():
    row = {**VALID_MATCH, "id": "not-an-int"}
    with pytest.raises(SchemaContractError, match="field 'id' has type str"):
        validate_rows([row], dataset="matches")


def test_non_nullable_field_rejects_none():
    row = {**VALID_MATCH, "status": None}
    with pytest.raises(SchemaContractError, match="'status'"):
        validate_rows([row], dataset="matches")


def test_all_violations_reported_not_just_the_first():
    bad = {k: v for k, v in VALID_MATCH.items() if k not in ("id", "status")}
    with pytest.raises(SchemaContractError, match="2 contract violation"):
        validate_rows([bad], dataset="matches")


def test_unknown_dataset_passes_through_with_warning(caplog):
    rows = [{"whatever": 1}]
    with caplog.at_level(logging.WARNING, logger="ingestion.schemas"):
        assert validate_rows(rows, dataset="mystery") is rows
    assert "no schema contract" in caplog.text


def test_committed_raw_archive_satisfies_the_contracts():
    """The real archived data must pass its own contracts — guards against
    the contracts drifting away from what the API actually sends."""
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "data" / "raw" / "football_data"
    if not root.exists():
        pytest.skip("no raw archive checked out")
    for dataset in ("matches", "standings", "scorers"):
        partitions = sorted((root / dataset).glob("extraction_date=*/*.parquet"))
        assert partitions, f"no partitions for {dataset}"
        table = pq.read_table(partitions[-1])  # latest partition is enough
        rows = table.to_pylist()
        validate_rows(rows, dataset=dataset)
        assert pa is not None  # keep the import visibly used
