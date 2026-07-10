"""Tests for the raw Parquet writer — layout, idempotence, row counts."""

import logging
from datetime import datetime, timezone

import pyarrow.parquet as pq

from ingestion.storage import matches_to_rows, standings_to_rows, write_raw_parquet

EXTRACTED_AT = datetime(2026, 7, 10, 6, 0, 0, tzinfo=timezone.utc)

MATCHES_PAYLOAD = {
    "competition": {"code": "WC"},
    "matches": [
        {"id": 1, "status": "FINISHED", "score": {"fullTime": {"home": 2, "away": 0}}},
        {"id": 2, "status": "SCHEDULED", "score": {"fullTime": {"home": None, "away": None}}},
    ],
}

STANDINGS_PAYLOAD = {
    "competition": {"code": "WC"},
    "season": {"id": 2026},
    "standings": [
        {"group": "GROUP_A", "type": "TOTAL", "table": [{"position": 1}, {"position": 2}]},
        {"group": "GROUP_B", "type": "TOTAL", "table": [{"position": 1}]},
    ],
}


def test_matches_to_rows_preserves_every_match():
    rows = matches_to_rows(MATCHES_PAYLOAD)
    assert len(rows) == 2
    assert rows[0] == MATCHES_PAYLOAD["matches"][0]


def test_standings_to_rows_keeps_group_and_season_context():
    rows = standings_to_rows(STANDINGS_PAYLOAD)
    assert len(rows) == 3
    assert rows[0]["standing"] == {"group": "GROUP_A", "type": "TOTAL"}
    assert rows[2]["standing"]["group"] == "GROUP_B"
    assert rows[0]["season"] == {"id": 2026}
    assert rows[0]["competition"] == {"code": "WC"}


def test_write_creates_hive_partitioned_file_with_metadata_columns(tmp_path):
    rows = matches_to_rows(MATCHES_PAYLOAD)
    path = write_raw_parquet(rows, dataset="matches", root=tmp_path, extracted_at=EXTRACTED_AT)
    assert path == (
        tmp_path / "football_data" / "matches" / "extraction_date=2026-07-10" / "matches.parquet"
    )
    table = pq.read_table(path)
    assert table.num_rows == 2
    assert {"extracted_at", "source", "id", "status", "score"} <= set(table.column_names)
    assert table.column("source").to_pylist() == ["football-data.org"] * 2
    # nested struct fields survive the round-trip untouched
    assert table.column("score").to_pylist()[0] == {"fullTime": {"home": 2, "away": 0}}


def test_rerun_same_day_replaces_file_idempotently(tmp_path):
    rows = matches_to_rows(MATCHES_PAYLOAD)
    first = write_raw_parquet(rows, dataset="matches", root=tmp_path, extracted_at=EXTRACTED_AT)
    second = write_raw_parquet(rows, dataset="matches", root=tmp_path, extracted_at=EXTRACTED_AT)
    assert first == second
    partition_dir = first.parent
    assert [p.name for p in partition_dir.iterdir()] == ["matches.parquet"]
    assert pq.read_metadata(first).num_rows == 2


def test_different_days_land_in_different_partitions(tmp_path):
    rows = matches_to_rows(MATCHES_PAYLOAD)
    day1 = write_raw_parquet(rows, dataset="matches", root=tmp_path, extracted_at=EXTRACTED_AT)
    day2 = write_raw_parquet(
        rows,
        dataset="matches",
        root=tmp_path,
        extracted_at=datetime(2026, 7, 11, 6, 0, 0, tzinfo=timezone.utc),
    )
    assert day1 != day2
    assert day1.parent.name == "extraction_date=2026-07-10"
    assert day2.parent.name == "extraction_date=2026-07-11"


def test_zero_rows_writes_nothing_but_logs_it(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="ingestion.storage"):
        path = write_raw_parquet([], dataset="matches", root=tmp_path, extracted_at=EXTRACTED_AT)
    assert path is None
    assert not (tmp_path / "football_data").exists()
    assert "0 rows received" in caplog.text


def test_row_counts_are_logged(tmp_path, caplog):
    rows = standings_to_rows(STANDINGS_PAYLOAD)
    with caplog.at_level(logging.INFO, logger="ingestion.storage"):
        write_raw_parquet(rows, dataset="standings", root=tmp_path, extracted_at=EXTRACTED_AT)
    assert "3 rows in -> 3 rows written" in caplog.text
