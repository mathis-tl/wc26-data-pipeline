"""Analytics entry point: `uv run python -m analytics`.

Reads the dbt marts from data/warehouse.duckdb, fits the Poisson strength
model, derives opponent-adjusted metrics and the title simulation, and writes
JSON to dashboard/src/data/ for the front-end. Run after `dbt build`.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from analytics.model import PoissonModel, fit, goal_means, outcome_probs
from analytics.simulate import ROUND_LEVELS, simulate_progression
from ingestion.ops import record_run

logger = logging.getLogger("analytics")

REPO_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
OUT_DIR = REPO_ROOT / "dashboard" / "src" / "data"
N_SIMS = 10000


def _rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _write(name: str, payload) -> None:
    (OUT_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"  wrote {name}")


def _ranks(values: dict[int, float], reverse: bool = True) -> dict[int, int]:
    order = sorted(values, key=lambda t: values[t], reverse=reverse)
    return {t: i + 1 for i, t in enumerate(order)}


def run() -> None:
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    matches = _rows(
        con,
        """
        select match_id, stage, status, winner, kickoff_at, duration,
               home_team_id, home_team_name, regulation_home_goals as home_goals,
               away_team_id, away_team_name, regulation_away_goals as away_goals,
               penalty_home_goals, penalty_away_goals
        from main.fct_matches
        order by match_id  -- deterministic row order: the MLE fit sums in this
                           -- order, so identical data yields identical ratings
                           -- run to run (DuckDB gives no order without this)
        """,
    )
    teams_meta = {
        r["team_id"]: r
        for r in _rows(
            con, "select team_id, team_name, team_tla, team_crest_url from main.dim_teams"
        )
    }
    con.close()

    finished = [m for m in matches if m["status"] == "FINISHED" and m["home_goals"] is not None]
    model: PoissonModel = fit(finished)
    ratings = {t: model.strength(t) for t in model.teams}
    rank_overall = _ranks(ratings)
    rank_attack = _ranks(model.attack)
    rank_defense = _ranks(model.defense)

    # --- per-team aggregates over their finished matches ---
    agg = {
        t: {
            "gf": 0,
            "ga": 0,
            "xgf": 0.0,
            "xga": 0.0,
            "pts": 0,
            "xpts": 0.0,
            "played": 0,
            "opp_rating_sum": 0.0,
        }
        for t in model.teams
    }
    for m in finished:
        h, a = m["home_team_id"], m["away_team_id"]
        gh, ga = m["home_goals"], m["away_goals"]
        # Knockout matches are neutral-venue: "home" is a fixture-listing
        # artifact, not a real advantage, so home_adv must not apply — this
        # feeds every team's aggregate xgf/xga (e.g. spain_case.json's xga).
        lh, la = goal_means(model, h, a, neutral=m["stage"] != "GROUP_STAGE")
        p_home, p_draw, p_away = outcome_probs(lh, la)
        # Points come from `winner`, never from comparing goals: a
        # penalty-shootout match has equal regulation goals by construction
        # (that's why it went to penalties) but is a win/loss, not a draw.
        for team, opp, gf, ga_, xgf, xga, xp, win, draw in (
            (h, a, gh, ga, lh, la, 3 * p_home + p_draw, m["winner"] == "HOME_TEAM", m["winner"] == "DRAW"),
            (a, h, ga, gh, la, lh, 3 * p_away + p_draw, m["winner"] == "AWAY_TEAM", m["winner"] == "DRAW"),
        ):
            d = agg[team]
            d["gf"] += gf
            d["ga"] += ga_
            d["xgf"] += xgf
            d["xga"] += xga
            d["xpts"] += xp
            d["played"] += 1
            d["pts"] += 3 if win else (1 if draw else 0)
            d["opp_rating_sum"] += ratings[opp]

    def meta(t):
        m = teams_meta.get(t, {})
        return m.get("team_name") or str(t), m.get("team_tla"), m.get("team_crest_url")

    team_strength = []
    for t in model.teams:
        d = agg[t]
        name, tla, crest = meta(t)
        team_strength.append(
            {
                "team_id": t,
                "team_name": name,
                "team_tla": tla,
                "crest": crest,
                "attack": round(model.attack[t], 3),
                "defense": round(model.defense[t], 3),
                "rating": round(ratings[t], 3),
                "rank_overall": rank_overall[t],
                "rank_attack": rank_attack[t],
                "rank_defense": rank_defense[t],
                "played": d["played"],
                "goals_for": d["gf"],
                "goals_against": d["ga"],
                "xgf": round(d["xgf"], 2),
                "xga": round(d["xga"], 2),
                "points": d["pts"],
                "xpoints": round(d["xpts"], 2),
                "performance": round(d["pts"] - d["xpts"], 2),
                "sos": round(d["opp_rating_sum"] / d["played"], 3) if d["played"] else 0.0,
            }
        )
    team_strength.sort(key=lambda x: x["rank_overall"])
    _write("team_strength.json", team_strength)

    # --- FBref reality check (source #3): real basic stats next to the model's ratings ---
    from analytics.real_fbref import load_fbref_real

    fbref_real = load_fbref_real({row["team_name"] for row in team_strength})
    if fbref_real:
        team_reality = [
            {
                "team_id": row["team_id"],
                "team_name": row["team_name"],
                "team_tla": row["team_tla"],
                "crest": row["crest"],
                "rank_overall": row["rank_overall"],
                "rank_attack": row["rank_attack"],
                "rank_defense": row["rank_defense"],
                "attack": row["attack"],
                "defense": row["defense"],
                "rating": row["rating"],
                "possession": real["possession"],
                "shots": real["shots"],
                "sot": real["sot"],
                "sot_pct": real["sot_pct"],
                "sota": real["sota"],
                "ga": real["ga"],
                "save_pct": real["save_pct"],
                "cs": real["cs"],
                "conversion": real["g_per_sh"],
            }
            for row in team_strength
            if (real := fbref_real.get(row["team_name"])) is not None
        ]
        # dim_teams -> FBref is the reverse direction of the NAME_MAP check inside
        # load_fbref_real: that guard catches an unmapped FBref name, this one
        # catches a dim_teams team that FBref's own 48 never covered.
        missing = {row["team_name"] for row in team_strength} - fbref_real.keys()
        if missing:
            raise RuntimeError(f"dim_teams team(s) missing from FBref reality check: {sorted(missing)}")
        team_reality.sort(key=lambda x: x["rank_overall"])
        _write("team_reality.json", team_reality)

    # --- upsets: finished matches the winner was least likely to win ---
    upsets = []
    for m in finished:
        if m["winner"] not in ("HOME_TEAM", "AWAY_TEAM"):
            continue
        lh, la = goal_means(model, m["home_team_id"], m["away_team_id"], neutral=m["stage"] != "GROUP_STAGE")
        p_home, p_draw, p_away = outcome_probs(lh, la)
        win_p = p_home if m["winner"] == "HOME_TEAM" else p_away
        home_won = m["winner"] == "HOME_TEAM"
        winner_id = m["home_team_id"] if home_won else m["away_team_id"]
        loser_id = m["away_team_id"] if home_won else m["home_team_id"]
        wn, _, wc = meta(winner_id)
        ln, _, lc = meta(loser_id)
        wg, lg = (m["home_goals"], m["away_goals"]) if home_won else (m["away_goals"], m["home_goals"])
        score = f"{wg}–{lg}"
        # Regulation goals alone would show a shootout win as e.g. "0–0", which
        # reads as no result at all — append how it was actually decided.
        if m.get("duration") == "PENALTY_SHOOTOUT" and m.get("penalty_home_goals") is not None:
            wp, lp = (
                (m["penalty_home_goals"], m["penalty_away_goals"])
                if home_won
                else (m["penalty_away_goals"], m["penalty_home_goals"])
            )
            score += f" ({wp}–{lp} t.a.b.)"
        upsets.append(
            {
                "match_id": m["match_id"],
                "stage": m["stage"],
                "winner_name": wn,
                "winner_crest": wc,
                "loser_name": ln,
                "loser_crest": lc,
                "score": score,
                "win_prob": round(win_p, 3),
            }
        )
    upsets.sort(key=lambda x: x["win_prob"])
    _write("upsets.json", upsets[:8])

    # --- title simulation + round-by-round progression from the Round of 32 ---
    knockout = [
        m
        for m in matches
        if m["stage"] in ("LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL")
    ]
    reach = simulate_progression(model, knockout, n_sims=N_SIMS)
    title = []
    for t, levels in sorted(reach.items(), key=lambda kv: kv[1][5], reverse=True):
        name, tla, crest = meta(t)
        title.append(
            {
                "team_id": t,
                "team_name": name,
                "team_tla": tla,
                "crest": crest,
                "title_prob": round(levels[5], 4),
            }
        )
    _write("title_odds.json", title[:12])
    _write(
        "title_progression.json",
        {
            "levels": ROUND_LEVELS,
            "teams": [
                {
                    "team_name": meta(t)[0],
                    "team_tla": meta(t)[1],
                    "crest": meta(t)[2],
                    "reach": [round(x, 3) for x in reach[t]],
                }
                for t, _ in sorted(reach.items(), key=lambda kv: kv[1][5], reverse=True)[:10]
            ],
        },
    )

    # --- rating vs how far each team actually went ---
    stage_order = {
        "GROUP_STAGE": 0,
        "LAST_32": 1,
        "LAST_16": 2,
        "QUARTER_FINALS": 3,
        "SEMI_FINALS": 4,
        "THIRD_PLACE": 4,
        "FINAL": 5,
    }
    finish = {t: 0 for t in model.teams}
    for m in matches:
        so = stage_order.get(m["stage"], 0)
        for t in (m["home_team_id"], m["away_team_id"]):
            if t in finish:
                finish[t] = max(finish[t], so)
    _write(
        "rating_vs_finish.json",
        [
            {
                "team_name": meta(t)[0],
                "team_tla": meta(t)[1],
                "rating": round(ratings[t], 3),
                "finish": finish[t],
                "highlight": (meta(t)[0] or "").lower() == "spain",
            }
            for t in model.teams
        ],
    )

    # --- Spain: the narrative headline numbers ---
    spain_id = next((t for t in model.teams if (meta(t)[0] or "").lower() == "spain"), None)
    if spain_id is not None:
        s = next(x for x in team_strength if x["team_id"] == spain_id)
        s_prob = next((x["title_prob"] for x in title if x["team_id"] == spain_id), 0.0)
        title_rank = next((i + 1 for i, x in enumerate(title) if x["team_id"] == spain_id), None)
        _write(
            "spain_case.json",
            {
                "team_name": s["team_name"],
                "crest": s["crest"],
                "rank_overall": s["rank_overall"],
                "rank_attack": s["rank_attack"],
                "rank_defense": s["rank_defense"],
                "n_teams": len(model.teams),
                "goals_for": s["goals_for"],
                "xgf": s["xgf"],
                "goals_against": s["goals_against"],
                "xga": s["xga"],
                "points": s["points"],
                "xpoints": s["xpoints"],
                "performance": s["performance"],
                "title_prob": s_prob,
                "title_rank": title_rank,
            },
        )
        # Spain's route to the title: each match with its model win probability
        sp_matches = sorted(
            [
                m
                for m in matches
                if spain_id in (m["home_team_id"], m["away_team_id"]) and m["status"] == "FINISHED"
            ],
            key=lambda m: m["kickoff_at"] or "",
        )
        path = []
        for m in sp_matches:
            home = m["home_team_id"] == spain_id
            opp = m["away_team_id"] if home else m["home_team_id"]
            # Knockout matches are played at neutral venues: the "home" team
            # label is an artifact of fixture listing order, not a real venue
            # advantage, so home_adv must not apply here — same convention as
            # simulate.py's _win_prob_table, which this call was missing.
            neutral = m["stage"] != "GROUP_STAGE"
            lh, la = goal_means(model, m["home_team_id"], m["away_team_id"], neutral=neutral)
            p_home, p_draw, p_away = outcome_probs(lh, la)
            sg = m["home_goals"] if home else m["away_goals"]
            og = m["away_goals"] if home else m["home_goals"]
            oname, otla, ocrest = meta(opp)
            score = f"{sg}–{og}"
            # Same shootout caveat as the upsets score above: regulation goals
            # alone can show a decisive knockout win as a bare tie.
            if m.get("duration") == "PENALTY_SHOOTOUT" and m.get("penalty_home_goals") is not None:
                sp, op = (
                    (m["penalty_home_goals"], m["penalty_away_goals"])
                    if home
                    else (m["penalty_away_goals"], m["penalty_home_goals"])
                )
                score += f" ({sp}–{op} t.a.b.)"
            result = "V" if m["winner"] == ("HOME_TEAM" if home else "AWAY_TEAM") else ("N" if m["winner"] == "DRAW" else "D")
            path.append(
                {
                    "stage": m["stage"],
                    "opponent": oname,
                    "opponent_tla": otla,
                    "opponent_crest": ocrest,
                    "score": score,
                    "result": result,
                    "win_prob": round(p_home if home else p_away, 3),
                    "model_xg_for": round(lh if home else la, 2),
                    "model_xg_against": round(la if home else lh, 2),
                }
            )
        _write("spain_path.json", path)

        # Merge real SofaScore stats (source #2), reconciled by chronology
        from analytics.real_stats import load_spain_real

        real_rows, final_shots = load_spain_real(path)
        if real_rows is not None:
            _write("spain_real.json", real_rows)
            _write("spain_final_shots.json", final_shots)

    _write(
        "model_meta.json",
        {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "n_teams": len(model.teams),
            "n_matches": model.n_matches,
            "home_adv": round(model.home_adv, 3),
            "ridge": model.ridge,
            "final_nll": round(model.final_nll, 2),
            "n_sims": N_SIMS,
            "note": (
                "Modele de buts (Poisson) ajuste sur les resultats. Depuis le sprint FBref, "
                "on dispose de volumes de tir reels (tirs, cadres, buts encaisses, arrets) en "
                "complement — mais toujours aucune donnee de xG de tracking : les buts "
                "attendus du modele restent modelises, jamais mesures, et ne sont jamais "
                "appeles xG (ADR-0004, ADR-0006)."
                if fbref_real
                else "Modele de buts (Poisson) ajuste sur les resultats. Aucune donnee de tir : "
                "les buts attendus sont modelises, pas du xG de tracking."
            ),
        },
    )
    print("analytics done ->", OUT_DIR)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    run_id = datetime.now(UTC).isoformat(timespec="seconds")
    started = time.monotonic()
    try:
        run()
    except Exception as exc:
        record_run(
            run_id=run_id,
            stage="analytics",
            dataset="model+simulation",
            rows=0,
            duration_s=time.monotonic() - started,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    record_run(
        run_id=run_id,
        stage="analytics",
        dataset="model+simulation",
        rows=len(list(OUT_DIR.glob("*.json"))),
        duration_s=time.monotonic() - started,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
