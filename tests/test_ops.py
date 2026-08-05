"""Tests for the run-observability log (append-only JSONL in git)."""

import logging

from ingestion.ops import read_runs, record_run


def test_record_appends_one_line_per_call(tmp_path):
    path = tmp_path / "runs.jsonl"
    record_run(
        run_id="2026-08-05T06:00:00+00:00",
        stage="ingestion",
        dataset="matches",
        rows=104,
        duration_s=1.234,
        path=path,
    )
    record_run(
        run_id="2026-08-05T06:00:00+00:00",
        stage="ingestion",
        dataset="standings",
        rows=48,
        duration_s=0.8,
        path=path,
    )
    runs = read_runs(path)
    assert [r["dataset"] for r in runs] == ["matches", "standings"]
    assert runs[0]["rows"] == 104
    assert runs[0]["status"] == "ok"
    assert runs[0]["duration_s"] == 1.23


def test_failed_run_carries_a_truncated_error(tmp_path):
    path = tmp_path / "runs.jsonl"
    record_run(
        run_id="r1",
        stage="analytics",
        dataset="model",
        rows=0,
        duration_s=0.1,
        status="failed",
        error="x" * 1000,
        path=path,
    )
    (run,) = read_runs(path)
    assert run["status"] == "failed"
    assert len(run["error"]) == 300


def test_read_missing_file_returns_empty(tmp_path):
    assert read_runs(tmp_path / "absent.jsonl") == []


def test_read_skips_malformed_lines(tmp_path, caplog):
    path = tmp_path / "runs.jsonl"
    record_run(run_id="r1", stage="ingestion", dataset="matches", rows=1, duration_s=0, path=path)
    path.open("a").write("{not json}\n")
    record_run(run_id="r2", stage="ingestion", dataset="matches", rows=2, duration_s=0, path=path)
    with caplog.at_level(logging.WARNING, logger="ingestion.ops"):
        runs = read_runs(path)
    assert [r["run_id"] for r in runs] == ["r1", "r2"]
    assert "malformed" in caplog.text


def test_limit_returns_most_recent(tmp_path):
    path = tmp_path / "runs.jsonl"
    for i in range(5):
        record_run(
            run_id=f"r{i}", stage="ingestion", dataset="matches", rows=i, duration_s=0, path=path
        )
    runs = read_runs(path, limit=2)
    assert [r["run_id"] for r in runs] == ["r3", "r4"]


def test_broken_ops_path_never_raises(tmp_path):
    file_as_dir = tmp_path / "blocked"
    file_as_dir.write_text("i am a file, not a directory")
    record = record_run(
        run_id="r1",
        stage="ingestion",
        dataset="matches",
        rows=1,
        duration_s=0,
        path=file_as_dir / "runs.jsonl",  # parent is a file -> OSError inside
    )
    assert record["status"] == "ok"  # the record is still returned
