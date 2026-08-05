"""Analytics entry point: `uv run python -m analytics`.

Reads the dbt marts from data/warehouse.duckdb, fits the Poisson strength
model, derives opponent-adjusted metrics and the title simulation, and writes
JSON to dashboard/src/data/ for the front-end. Run after `dbt build`.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from analytics.model import PoissonModel, fit, goal_means, outcome_probs
from analytics.simulate import ROUND_LEVELS, simulate_progression

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
        select match_id, stage, status, winner, kickoff_at,
               home_team_id, home_team_name, full_time_home_goals as home_goals,
               away_team_id, away_team_name, full_time_away_goals as away_goals
        from main.fct_matches
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
        lh, la = goal_means(model, h, a)
        p_home, p_draw, p_away = outcome_probs(lh, la)
        for team, opp, gf, ga_, xgf, xga, xp in (
            (h, a, gh, ga, lh, la, 3 * p_home + p_draw),
            (a, h, ga, gh, la, lh, 3 * p_away + p_draw),
        ):
            d = agg[team]
            d["gf"] += gf
            d["ga"] += ga_
            d["xgf"] += xgf
            d["xga"] += xga
            d["xpts"] += xp
            d["played"] += 1
            d["pts"] += 3 if gf > ga_ else (1 if gf == ga_ else 0)
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

    # --- upsets: finished matches the winner was least likely to win ---
    upsets = []
    for m in finished:
        if m["winner"] not in ("HOME_TEAM", "AWAY_TEAM"):
            continue
        lh, la = goal_means(model, m["home_team_id"], m["away_team_id"])
        p_home, p_draw, p_away = outcome_probs(lh, la)
        win_p = p_home if m["winner"] == "HOME_TEAM" else p_away
        winner_id = m["home_team_id"] if m["winner"] == "HOME_TEAM" else m["away_team_id"]
        loser_id = m["away_team_id"] if m["winner"] == "HOME_TEAM" else m["home_team_id"]
        wn, _, wc = meta(winner_id)
        ln, _, lc = meta(loser_id)
        upsets.append(
            {
                "match_id": m["match_id"],
                "stage": m["stage"],
                "winner_name": wn,
                "winner_crest": wc,
                "loser_name": ln,
                "loser_crest": lc,
                "score": f"{max(m['home_goals'], m['away_goals'])}–{min(m['home_goals'], m['away_goals'])}",
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
            lh, la = goal_means(model, m["home_team_id"], m["away_team_id"])
            p_home, p_draw, p_away = outcome_probs(lh, la)
            sg = m["home_goals"] if home else m["away_goals"]
            og = m["away_goals"] if home else m["home_goals"]
            oname, otla, ocrest = meta(opp)
            path.append(
                {
                    "stage": m["stage"],
                    "opponent": oname,
                    "opponent_tla": otla,
                    "opponent_crest": ocrest,
                    "score": f"{sg}–{og}",
                    "result": "V" if sg > og else ("N" if sg == og else "D"),
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
            "note": "Modele de buts (Poisson) ajuste sur les resultats. Aucune donnee de tir : "
            "les buts attendus sont modelises, pas du xG de tracking.",
        },
    )
    print("analytics done ->", OUT_DIR)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
