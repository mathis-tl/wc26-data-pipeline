"""Monte-Carlo title simulation.

The knockout bracket has no explicit parent/child links in the data, so we
reconstruct it from results: a round-N match's two teams are the winners of two
round-(N-1) matches. We then replay the bracket many times, replacing each
result with a model-drawn winner, to estimate every team's title probability
*as of the Round of 32*.
"""

from __future__ import annotations

import numpy as np

from analytics.model import PoissonModel, goal_means, outcome_probs

TITLE_PATH = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]


def _winner_id(m: dict) -> int | None:
    if m.get("winner") == "HOME_TEAM":
        return m.get("home_team_id")
    if m.get("winner") == "AWAY_TEAM":
        return m.get("away_team_id")
    return None


def reconstruct_bracket(knockout: list[dict]) -> dict:
    """Return {match_id: {teams, children}} plus the final's id. children is a
    pair of child match ids, or None for Round-of-32 leaves."""
    by_stage = {s: [m for m in knockout if m["stage"] == s] for s in TITLE_PATH}
    winner_to_match = {
        s: {_winner_id(m): m["match_id"] for m in by_stage[s] if _winner_id(m) is not None}
        for s in TITLE_PATH
    }
    nodes: dict = {}
    for i, stage in enumerate(TITLE_PATH):
        for m in by_stage[stage]:
            teams = (m["home_team_id"], m["away_team_id"])
            children = None
            if i > 0:
                prev = winner_to_match[TITLE_PATH[i - 1]]
                children = tuple(prev.get(t) for t in teams)
                if any(c is None for c in children):
                    children = None  # incomplete bracket; treat as leaf
            nodes[m["match_id"]] = {"teams": teams, "children": children}
    final_id = by_stage["FINAL"][0]["match_id"] if by_stage["FINAL"] else None
    return {"nodes": nodes, "final_id": final_id}


def _win_prob_table(model: PoissonModel, teams: list[int]) -> dict[tuple[int, int], float]:
    """P(i beats j) at a neutral venue (draws split 50/50, as after ET/pens)."""
    table: dict[tuple[int, int], float] = {}
    for i in teams:
        for j in teams:
            if i == j:
                continue
            lh, la = goal_means(model, i, j, neutral=True)
            p_home, p_draw, _ = outcome_probs(lh, la)
            table[(i, j)] = p_home + p_draw / 2
    return table


def simulate_title(
    model: PoissonModel, knockout: list[dict], n_sims: int = 10000, seed: int = 42
) -> dict[int, float]:
    """Title probability per team, simulated from the Round of 32."""
    bracket = reconstruct_bracket(knockout)
    nodes, final_id = bracket["nodes"], bracket["final_id"]
    if final_id is None:
        return {}
    teams = sorted({t for node in nodes.values() for t in node["teams"] if t is not None})
    wp = _win_prob_table(model, teams)
    rng = np.random.default_rng(seed)

    def play(node_id: int, draws: dict) -> int:
        node = nodes[node_id]
        if node["children"] is None:
            a, b = node["teams"]
        else:
            a = play(node["children"][0], draws)
            b = play(node["children"][1], draws)
        u = rng.random()
        return a if u < wp.get((a, b), 0.5) else b

    counts: dict[int, int] = dict.fromkeys(teams, 0)
    for _ in range(n_sims):
        champ = play(final_id, {})
        counts[champ] += 1
    return {t: counts[t] / n_sims for t in teams}
