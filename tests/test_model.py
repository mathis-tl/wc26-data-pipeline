"""Tests for the Poisson analytics model — synthetic data, no network."""

import math

import pytest

from analytics.model import FitError, fit, goal_means, outcome_probs
from analytics.simulate import (
    ROUND_LEVELS,
    reconstruct_bracket,
    simulate_progression,
    simulate_title,
)


def _m(hid, aid, hg, ag):
    return {
        "home_team_id": hid,
        "away_team_id": aid,
        "home_goals": hg,
        "away_goals": ag,
        "home_team_name": f"T{hid}",
        "away_team_name": f"T{aid}",
    }


SYNTH = [
    _m(1, 2, 3, 0),
    _m(1, 3, 3, 0),
    _m(1, 4, 3, 0),  # team 1 dominates
    _m(2, 3, 1, 1),
    _m(2, 4, 3, 0),
    _m(3, 4, 3, 0),  # team 4 loses everything
]


def test_outcome_probs_sum_to_one():
    for lh, la in [(1.5, 1.2), (0.3, 2.4), (2.0, 2.0)]:
        p = outcome_probs(lh, la)
        assert math.isclose(sum(p), 1.0, abs_tol=1e-6)
        assert all(0.0 <= x <= 1.0 for x in p)


def test_fit_recovers_strength_order():
    model = fit(SYNTH)
    s = {t: model.strength(t) for t in model.teams}
    # the dominant team is strongest, the whipping boy is weakest
    assert max(s, key=lambda t: s[t]) == 1
    assert min(s, key=lambda t: s[t]) == 4
    assert s[1] > s[4]


def test_reconstruct_bracket_links_final_to_semis():
    knockout = [
        {
            "match_id": 10,
            "stage": "SEMI_FINALS",
            "winner": "HOME_TEAM",
            "home_team_id": 1,
            "away_team_id": 2,
        },
        {
            "match_id": 11,
            "stage": "SEMI_FINALS",
            "winner": "HOME_TEAM",
            "home_team_id": 3,
            "away_team_id": 4,
        },
        {
            "match_id": 20,
            "stage": "FINAL",
            "winner": "HOME_TEAM",
            "home_team_id": 1,
            "away_team_id": 3,
        },
    ]
    b = reconstruct_bracket(knockout)
    assert b["final_id"] == 20
    assert set(b["nodes"][20]["children"]) == {10, 11}
    assert b["nodes"][10]["children"] is None  # semis are leaves


def test_title_probabilities_valid():
    model = fit(SYNTH)
    knockout = [
        {
            "match_id": 10,
            "stage": "SEMI_FINALS",
            "winner": "HOME_TEAM",
            "home_team_id": 1,
            "away_team_id": 2,
        },
        {
            "match_id": 11,
            "stage": "SEMI_FINALS",
            "winner": "HOME_TEAM",
            "home_team_id": 3,
            "away_team_id": 4,
        },
        {
            "match_id": 20,
            "stage": "FINAL",
            "winner": "HOME_TEAM",
            "home_team_id": 1,
            "away_team_id": 3,
        },
    ]
    odds = simulate_title(model, knockout, n_sims=2000, seed=1)
    assert math.isclose(sum(odds.values()), 1.0, abs_tol=1e-6)
    assert all(0.0 <= p <= 1.0 for p in odds.values())
    # the strongest team should be the most likely champion
    assert max(odds, key=lambda t: odds[t]) == 1


# --- fit guards -----------------------------------------------------------


def test_fit_refuses_empty_input():
    with pytest.raises(FitError, match="0 team"):
        fit([])


def test_fit_ignores_rows_with_missing_goals():
    rows = [*SYNTH, _m(1, 2, None, None)]  # fixture without a result
    model = fit(rows)
    assert model.n_matches == len(SYNTH)


def test_fit_exposes_convergence_metadata():
    model = fit(SYNTH)
    assert model.n_matches == len(SYNTH)
    assert math.isfinite(model.final_nll)


def test_goal_means_neutral_removes_home_advantage():
    model = fit(SYNTH)
    lam_home, lam_away = goal_means(model, 1, 4)
    lam_home_n, lam_away_n = goal_means(model, 1, 4, neutral=True)
    # neutral venue must not change the away side, only strip the home bump
    assert math.isclose(lam_away, lam_away_n, rel_tol=1e-12)
    assert lam_home != lam_home_n or math.isclose(model.home_adv, 0.0, abs_tol=1e-9)


# --- bracket edge cases ---------------------------------------------------


def _semi_final_bracket():
    return [
        {
            "match_id": 10,
            "stage": "SEMI_FINALS",
            "winner": "HOME_TEAM",
            "home_team_id": 1,
            "away_team_id": 2,
        },
        {
            "match_id": 11,
            "stage": "SEMI_FINALS",
            "winner": "HOME_TEAM",
            "home_team_id": 3,
            "away_team_id": 4,
        },
        {
            "match_id": 20,
            "stage": "FINAL",
            "winner": "HOME_TEAM",
            "home_team_id": 1,
            "away_team_id": 3,
        },
    ]


def test_reconstruct_bracket_missing_winner_degrades_to_leaf():
    """A parent whose child has no recorded winner must become a leaf, not
    crash and not link to a wrong child."""
    knockout = _semi_final_bracket()
    knockout[1]["winner"] = None  # semi 11 unresolved
    b = reconstruct_bracket(knockout)
    assert b["nodes"][20]["children"] is None  # final can't link both semis
    assert b["final_id"] == 20


def test_reconstruct_bracket_without_final_returns_none_id():
    knockout = [m for m in _semi_final_bracket() if m["stage"] != "FINAL"]
    b = reconstruct_bracket(knockout)
    assert b["final_id"] is None


def test_simulate_title_empty_without_final():
    model = fit(SYNTH)
    assert simulate_title(model, [], n_sims=10) == {}


def test_simulate_title_is_deterministic_for_a_seed():
    model = fit(SYNTH)
    knockout = _semi_final_bracket()
    a = simulate_title(model, knockout, n_sims=500, seed=7)
    b = simulate_title(model, knockout, n_sims=500, seed=7)
    assert a == b


# --- progression invariants ----------------------------------------------


def test_progression_is_monotonic_and_anchored():
    """P(reach round k) must decrease with k, start at 1.0 (everyone enters)
    and end at the title probability."""
    model = fit(SYNTH)
    knockout = _semi_final_bracket()
    prog = simulate_progression(model, knockout, n_sims=2000, seed=1)
    odds = simulate_title(model, knockout, n_sims=2000, seed=1)
    for team, levels in prog.items():
        assert len(levels) == len(ROUND_LEVELS)
        assert levels[0] == 1.0
        assert all(levels[k] >= levels[k + 1] for k in range(len(levels) - 1))
        assert math.isclose(levels[-1], odds[team], abs_tol=1e-9)
