"""Poisson team-strength model for the World Cup.

We only have final scores — no shot or event data — so we do NOT compute
tracking-based xG. Instead we fit, by maximum likelihood, an attack and a
defense strength per team (plus a home-advantage term) that best explain the
104 results. From those strengths we derive *model-based* expected goals and
expected points: honest, opponent-adjusted estimates of how good each team
really was.

    log E[goals] = home_adv * is_home + attack[scorer] - defense[conceder]
    goals ~ Poisson(E[goals])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

logger = logging.getLogger(__name__)


class FitError(Exception):
    """The optimiser failed or the data cannot support a fit — never ship
    ratings from a non-converged model."""


@dataclass
class PoissonModel:
    teams: list[int]  # team ids, in index order
    names: dict[int, str]
    attack: dict[int, float]  # higher = scores more
    defense: dict[int, float]  # higher = concedes fewer
    home_adv: float
    ridge: float
    final_nll: float  # converged objective value, for run-to-run comparison
    n_matches: int  # rows actually used by the fit

    def strength(self, team_id: int) -> float:
        """Net rating: attack minus (negated) defense, on the log-goal scale."""
        return self.attack[team_id] + self.defense[team_id]


def fit(matches: list[dict], ridge: float = 0.05) -> PoissonModel:
    """Fit attack/defense/home-advantage by penalised MLE on finished matches.

    `matches`: dicts with home_team_id, away_team_id, home_goals, away_goals,
    home_team_name, away_team_name. Rows with missing goals are ignored.
    """
    rows = [
        m
        for m in matches
        if m.get("home_team_id") is not None
        and m.get("away_team_id") is not None
        and m.get("home_goals") is not None
        and m.get("away_goals") is not None
    ]
    ids = sorted({m["home_team_id"] for m in rows} | {m["away_team_id"] for m in rows})
    idx = {t: i for i, t in enumerate(ids)}
    n = len(ids)
    if n < 2 or not rows:
        raise FitError(f"cannot fit a strength model on {n} team(s) / {len(rows)} match(es)")
    names: dict[int, str] = {}
    for m in rows:
        names.setdefault(m["home_team_id"], m.get("home_team_name") or str(m["home_team_id"]))
        names.setdefault(m["away_team_id"], m.get("away_team_name") or str(m["away_team_id"]))

    h = np.array([idx[m["home_team_id"]] for m in rows])
    a = np.array([idx[m["away_team_id"]] for m in rows])
    gh = np.array([m["home_goals"] for m in rows], dtype=float)
    ga = np.array([m["away_goals"] for m in rows], dtype=float)

    def unpack(theta):
        return theta[:n], theta[n : 2 * n], theta[2 * n]

    def nll(theta):
        att, dfn, hadv = unpack(theta)
        eta_h = hadv + att[h] - dfn[a]
        eta_a = att[a] - dfn[h]
        # Poisson negative log-likelihood (constant log(g!) dropped) + L2 ridge
        loss = np.sum(np.exp(eta_h) - gh * eta_h) + np.sum(np.exp(eta_a) - ga * eta_a)
        loss += ridge * (np.sum(att**2) + np.sum(dfn**2))
        return loss

    theta0 = np.zeros(2 * n + 1)
    res = minimize(nll, theta0, method="L-BFGS-B")
    # A silently non-converged optimiser is the worst failure mode this module
    # has: plausible-looking garbage ratings. Refuse to return them.
    if not res.success:
        raise FitError(f"L-BFGS-B did not converge: {res.message} (nit={res.nit})")
    logger.info(
        "fit converged: %d teams, %d matches, nll=%.2f, nit=%d", n, len(rows), res.fun, res.nit
    )
    att, dfn, hadv = unpack(res.x)
    # Centre attack and defense so ratings are read relative to the average team.
    att = att - att.mean()
    dfn = dfn - dfn.mean()
    return PoissonModel(
        teams=ids,
        names=names,
        attack={t: float(att[idx[t]]) for t in ids},
        defense={t: float(dfn[idx[t]]) for t in ids},
        home_adv=float(hadv),
        ridge=ridge,
        final_nll=float(res.fun),
        n_matches=len(rows),
    )


def goal_means(
    model: PoissonModel, home_id: int, away_id: int, neutral: bool = False
) -> tuple[float, float]:
    """Expected goals for (home, away). Set neutral=True for knockout venues."""
    hadv = 0.0 if neutral else model.home_adv
    lam_home = np.exp(hadv + model.attack[home_id] - model.defense[away_id])
    lam_away = np.exp(model.attack[away_id] - model.defense[home_id])
    return float(lam_home), float(lam_away)


def score_matrix(lam_home: float, lam_away: float, max_goals: int = 10) -> np.ndarray:
    ph = poisson.pmf(np.arange(max_goals + 1), lam_home)
    pa = poisson.pmf(np.arange(max_goals + 1), lam_away)
    return np.outer(ph, pa)


def outcome_probs(
    lam_home: float, lam_away: float, max_goals: int = 10
) -> tuple[float, float, float]:
    """(P home win, P draw, P away win). Normalised so the three sum to 1
    (the score grid is truncated at max_goals, dropping a tiny tail)."""
    m = score_matrix(lam_home, lam_away, max_goals)
    m = m / m.sum()
    p_home = float(np.tril(m, -1).sum())
    p_draw = float(np.trace(m))
    p_away = float(np.triu(m, 1).sum())
    return p_home, p_draw, p_away
