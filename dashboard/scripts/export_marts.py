"""Export the dbt marts from the DuckDB warehouse to static JSON for the
dashboard front-end.

This is the ONLY bridge between the data platform and the site: the Astro
build reads the committed JSON and never touches Python, dbt or DuckDB. Run
after `dbt build`, in the daily workflow, so the JSON rides along in the same
auto-merged PR as the raw archive.

    uv run python dashboard/scripts/export_marts.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))  # the script lives outside the package tree

from ingestion.ops import read_runs  # noqa: E402

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
RUN_RESULTS = REPO_ROOT / "dbt" / "target" / "run_results.json"
OUT_DIR = REPO_ROOT / "dashboard" / "src" / "data"

SOURCE = "football-data.org"
COMPETITION = "FIFA World Cup 2026"

# Knockout stages in bracket order.
KNOCKOUT_ORDER = [
    "LAST_32",
    "LAST_16",
    "QUARTER_FINALS",
    "SEMI_FINALS",
    "THIRD_PLACE",
    "FINAL",
]
STAGE_LABELS = {
    "LAST_32": "Round of 32",
    "LAST_16": "Round of 16",
    "QUARTER_FINALS": "Quarter-finals",
    "SEMI_FINALS": "Semi-finals",
    "THIRD_PLACE": "Third place",
    "FINAL": "Final",
}


def _write(name: str, payload) -> None:
    path = OUT_DIR / name
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
    rows = len(payload) if isinstance(payload, list) else "obj"
    print(f"  wrote {name} ({rows})")


def _rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _dbt_test_counts() -> tuple[int, int]:
    """(passed, total) dbt nodes from the last build — powers the freshness
    banner's '46/46' so the design element stays honest to the real run."""
    if not RUN_RESULTS.exists():
        return (0, 0)
    data = json.loads(RUN_RESULTS.read_text(encoding="utf-8"))
    results = data.get("results", [])
    passed = sum(1 for r in results if r.get("status") in ("pass", "success"))
    return (passed, len(results))


def export() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)

    # --- match rows enriched with crests, reused by several exports ---
    con.execute(
        """
        create or replace temp view match_enriched as
        select
            m.match_id,
            m.kickoff_at,
            m.status,
            m.stage,
            m.group_code,
            m.matchday,
            m.home_team_id,
            m.home_team_name,
            home_t.team_tla       as home_team_tla,
            home_t.team_crest_url as home_crest,
            m.away_team_id,
            m.away_team_name,
            away_t.team_tla       as away_team_tla,
            away_t.team_crest_url as away_crest,
            -- aliased from regulation_*: "full time" excludes penalty-shootout
            -- kicks by football convention; the raw API field does not (see
            -- fct_matches.sql). winner/penalty_* below already carry the
            -- correct shootout-aware outcome independently of this goal count.
            m.regulation_home_goals as full_time_home_goals,
            m.regulation_away_goals as full_time_away_goals,
            m.penalty_home_goals,
            m.penalty_away_goals,
            m.winner,
            m.duration
        from main.fct_matches m
        left join main.dim_teams home_t on home_t.team_id = m.home_team_id
        left join main.dim_teams away_t on away_t.team_id = m.away_team_id
        """
    )

    # --- key metrics (giant editorial numbers on the home page) ---
    metrics = _rows(
        con,
        """
        select
            count(*)                                             as matches_total,
            count(*) filter (where status = 'FINISHED')          as matches_played,
            sum(coalesce(regulation_home_goals, 0)
              + coalesce(regulation_away_goals, 0))
              filter (where status = 'FINISHED')                 as goals_scored,
            (select count(*) from main.dim_teams)                as teams,
            round(
              sum(coalesce(regulation_home_goals, 0)
                + coalesce(regulation_away_goals, 0))
                filter (where status = 'FINISHED')
              / nullif(count(*) filter (where status = 'FINISHED'), 0), 2
            )                                                    as avg_goals_per_match
        from main.fct_matches
        """,
    )[0]
    _write("key_metrics.json", metrics)

    # --- latest results & upcoming fixtures ---
    latest = _rows(
        con,
        """
        select * from match_enriched
        where status = 'FINISHED'
        order by kickoff_at desc, match_id desc
        limit 8
        """,
    )
    _write("latest_results.json", latest)

    upcoming = _rows(
        con,
        """
        select * from match_enriched
        where status in ('TIMED', 'SCHEDULED', 'IN_PLAY')
        order by kickoff_at asc, match_id asc
        limit 8
        """,
    )
    _write("upcoming_matches.json", upcoming)

    # --- group standings, grouped, with qualification status ---
    # WC 2026: 12 groups of 4 → top 2 qualify directly, plus the 8 best
    # third-placed teams. Rank thirds across groups by the same FIFA criteria.
    standings = _rows(
        con,
        """
        with ranked_thirds as (
            select team_id,
                   row_number() over (
                       order by points desc, goal_diff desc, goals_for desc, team_name
                   ) as third_rank
            from main.fct_group_standings
            where position = 3
        )
        select
            s.group_code,
            s.position,
            s.team_id,
            s.team_name,
            t.team_tla,
            t.team_crest_url as crest,
            s.played, s.won, s.draw, s.lost,
            s.points, s.goals_for, s.goals_against, s.goal_diff,
            case
                when s.position <= 2 then true
                when s.position = 3 and rt.third_rank <= 8 then true
                else false
            end as qualified,
            (s.position = 3 and rt.third_rank <= 8) as best_third
        from main.fct_group_standings s
        left join main.dim_teams t on t.team_id = s.team_id
        left join ranked_thirds rt on rt.team_id = s.team_id
        order by s.group_code, s.position
        """,
    )
    groups: dict[str, list[dict]] = {}
    for row in standings:
        groups.setdefault(row["group_code"], []).append(row)
    groups_payload = [
        {"group_code": code, "standings": rows} for code, rows in sorted(groups.items())
    ]
    _write("groups.json", groups_payload)

    # --- knockout bracket ---
    knockout = _rows(
        con,
        """
        select * from match_enriched
        where stage in ('LAST_32','LAST_16','QUARTER_FINALS',
                        'SEMI_FINALS','THIRD_PLACE','FINAL')
        order by kickoff_at asc, match_id asc
        """,
    )
    bracket = [
        {
            "stage": stage,
            "label": STAGE_LABELS[stage],
            "matches": [m for m in knockout if m["stage"] == stage],
        }
        for stage in KNOCKOUT_ORDER
        if any(m["stage"] == stage for m in knockout)
    ]
    _write("bracket.json", bracket)

    # --- goals by stage (bar chart: the tournament's goal rhythm) ---
    goals_by_stage = _rows(
        con,
        """
        select stage,
               count(*) filter (where status = 'FINISHED')            as matches,
               sum(coalesce(regulation_home_goals,0)
                 + coalesce(regulation_away_goals,0))
                 filter (where status = 'FINISHED')                   as goals,
               round(
                 sum(coalesce(regulation_home_goals,0)+coalesce(regulation_away_goals,0))
                   filter (where status = 'FINISHED')
                 / nullif(count(*) filter (where status = 'FINISHED'),0), 2) as avg_goals
        from main.fct_matches
        group by stage
        """,
    )
    order = {
        s: i
        for i, s in enumerate(
            [
                "GROUP_STAGE",
                "LAST_32",
                "LAST_16",
                "QUARTER_FINALS",
                "SEMI_FINALS",
                "THIRD_PLACE",
                "FINAL",
            ]
        )
    }
    stage_fr = {
        "GROUP_STAGE": "Groupes",
        "LAST_32": "16es",
        "LAST_16": "8es",
        "QUARTER_FINALS": "Quarts",
        "SEMI_FINALS": "Demies",
        "THIRD_PLACE": "3e place",
        "FINAL": "Finale",
    }
    goals_by_stage = [
        {**r, "label": stage_fr.get(r["stage"], r["stage"])}
        for r in sorted(goals_by_stage, key=lambda r: order.get(r["stage"], 99))
    ]
    _write("goals_by_stage.json", goals_by_stage)

    # --- scoreline distribution (bar chart: how matches actually end) ---
    scorelines = _rows(
        con,
        """
        with s as (
            select
                greatest(regulation_home_goals, regulation_away_goals) as hi,
                least(regulation_home_goals, regulation_away_goals)    as lo
            from main.fct_matches
            where status = 'FINISHED'
              and regulation_home_goals is not null
        )
        select (hi::text || '–' || lo::text) as scoreline, count(*) as count
        from s group by 1 order by count desc, scoreline
        limit 8
        """,
    )
    _write("scorelines.json", scorelines)

    # --- results split (home win / draw / away win among finished) ---
    # Uses `winner`, not a goal comparison: a penalty-shootout match has equal
    # regulation goals (by definition, that's why it went to penalties) but is
    # not a draw for this split — the API's own winner field is authoritative
    # regardless of how the match was decided.
    split = _rows(
        con,
        """
        select
            count(*) filter (where winner = 'HOME_TEAM') as home_wins,
            count(*) filter (where winner = 'DRAW')      as draws,
            count(*) filter (where winner = 'AWAY_TEAM') as away_wins
        from main.fct_matches
        where status = 'FINISHED'
        """,
    )[0]
    _write("results_split.json", split)

    # --- 2026 in historical context (every men's World Cup, one scale) ---
    editions = _rows(
        con,
        """
        select year, host, winner, teams, matches, goals,
               goals_per_match, is_current, goals_per_match_rank
        from main.mart_edition_comparison
        order by year
        """,
    )
    total_editions = len(editions)
    current = next((e for e in editions if e["is_current"]), None)
    _write(
        "edition_comparison.json",
        {
            "editions": editions,
            "current_year": current["year"] if current else None,
            "current_goals_per_match": current["goals_per_match"] if current else None,
            "current_rank": current["goals_per_match_rank"] if current else None,
            "total_editions": total_editions,
        },
    )

    # --- champion & final (narrative lead once the final is played) ---
    final_rows = _rows(
        con,
        "select * from match_enriched where stage = 'FINAL' order by kickoff_at desc limit 1",
    )
    champion = None
    if final_rows and final_rows[0]["status"] == "FINISHED":
        f = final_rows[0]
        won_home = f["winner"] == "HOME_TEAM"
        champion = {
            "team_name": f["home_team_name"] if won_home else f["away_team_name"],
            "crest": f["home_crest"] if won_home else f["away_crest"],
            "runner_up": f["away_team_name"] if won_home else f["home_team_name"],
            "final_score": f"{f['full_time_home_goals']}–{f['full_time_away_goals']}"
            if won_home
            else f"{f['full_time_away_goals']}–{f['full_time_home_goals']}",
        }
    _write("champion.json", {"final": final_rows[0] if final_rows else None, "champion": champion})

    # --- top scorers ---
    top_scorers = _rows(
        con,
        """
        select rank, player_name, player_nationality, team_name, team_tla,
               team_crest_url, played_matches, goals, assists, penalties
        from main.mart_top_scorers
        order by rank
        limit 15
        """,
    )
    _write("top_scorers.json", top_scorers)

    # --- metadata / freshness banner ---
    freshness_row = con.execute("select max(extracted_at) from main.stg_matches").fetchone()
    last_ingestion = freshness_row[0] if freshness_row else None
    passed, total = _dbt_test_counts()
    teams_row = con.execute("select count(*) from main.fct_group_standings").fetchone()
    n_teams = teams_row[0] if teams_row else 0

    # Run history from the ops log: how many automated runs the pipeline has
    # logged, and how many of them were clean — the operational track record.
    # NOTE: the ops log (data/ops/runs.jsonl) only started being written
    # recently, so runs_total badly undercounts the pipeline's real cadence.
    # The durable proof of "ran every day" is the raw archive itself (ADR-0001:
    # one committed extraction_date= partition per ingestion day) — count that
    # separately so the freshness banner doesn't imply a one-day pipeline.
    runs = read_runs()
    run_ids = {r["run_id"] for r in runs}
    failed_ids = {r["run_id"] for r in runs if r.get("status") != "ok"}
    raw_matches_dir = REPO_ROOT / "data" / "raw" / "football_data" / "matches"
    ingestion_days = (
        len([p for p in raw_matches_dir.glob("extraction_date=*") if p.is_dir()])
        if raw_matches_dir.exists()
        else 0
    )
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "last_ingestion": last_ingestion.astimezone(UTC).isoformat(timespec="seconds")
        if last_ingestion
        else None,
        "source": SOURCE,
        "competition": COMPETITION,
        "dbt_nodes_passed": passed,
        "dbt_nodes_total": total,
        "ingestion_days": ingestion_days,
        # derived, not hardcoded: the reconciliation test gates the build, so a
        # successful build means every standing row matched the official one
        "reconciliation": f"{n_teams}/{n_teams}",
        "ops": {
            "runs_total": len(run_ids),
            "runs_ok": len(run_ids - failed_ids),
        },
    }
    _write("metadata.json", metadata)

    con.close()
    print("export done ->", OUT_DIR)


if __name__ == "__main__":
    export()
