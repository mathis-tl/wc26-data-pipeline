"""Tests for the Poisson analytics model — synthetic data, no network."""

import math

from analytics.model import fit, outcome_probs
from analytics.simulate import reconstruct_bracket, simulate_title


def _m(hid, aid, hg, ag):
    return {
        "home_team_id": hid, "away_team_id": aid,
        "home_goals": hg, "away_goals": ag,
        "home_team_name": f"T{hid}", "away_team_name": f"T{aid}",
    }


SYNTH = [
    _m(1, 2, 3, 0), _m(1, 3, 3, 0), _m(1, 4, 3, 0),  # team 1 dominates
    _m(2, 3, 1, 1), _m(2, 4, 3, 0),
    _m(3, 4, 3, 0),                                    # team 4 loses everything
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
    assert max(s, key=s.get) == 1
    assert min(s, key=s.get) == 4
    assert s[1] > s[4]


def test_reconstruct_bracket_links_final_to_semis():
    knockout = [
        {"match_id": 10, "stage": "SEMI_FINALS", "winner": "HOME_TEAM", "home_team_id": 1, "away_team_id": 2},
        {"match_id": 11, "stage": "SEMI_FINALS", "winner": "HOME_TEAM", "home_team_id": 3, "away_team_id": 4},
        {"match_id": 20, "stage": "FINAL", "winner": "HOME_TEAM", "home_team_id": 1, "away_team_id": 3},
    ]
    b = reconstruct_bracket(knockout)
    assert b["final_id"] == 20
    assert set(b["nodes"][20]["children"]) == {10, 11}
    assert b["nodes"][10]["children"] is None  # semis are leaves


def test_title_probabilities_valid():
    model = fit(SYNTH)
    knockout = [
        {"match_id": 10, "stage": "SEMI_FINALS", "winner": "HOME_TEAM", "home_team_id": 1, "away_team_id": 2},
        {"match_id": 11, "stage": "SEMI_FINALS", "winner": "HOME_TEAM", "home_team_id": 3, "away_team_id": 4},
        {"match_id": 20, "stage": "FINAL", "winner": "HOME_TEAM", "home_team_id": 1, "away_team_id": 3},
    ]
    odds = simulate_title(model, knockout, n_sims=2000, seed=1)
    assert math.isclose(sum(odds.values()), 1.0, abs_tol=1e-6)
    assert all(0.0 <= p <= 1.0 for p in odds.values())
    # the strongest team should be the most likely champion
    assert max(odds, key=odds.get) == 1
