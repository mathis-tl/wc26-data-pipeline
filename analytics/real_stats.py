"""Reconcile SofaScore's real match stats (source #2) with our tournament.

The two sources share no IDs, so we align Spain's matches by chronology (both
are Spain's WC 2026 games in date order). We surface real xG, possession and
shots per match — and the final's shot map for a real shot chart.
"""

from __future__ import annotations

import json
from pathlib import Path

RAW = Path("data/raw/sofascore")
KNOCKOUT = {"Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final"}


def _num(x):
    if x is None:
        return None
    s = str(x).replace("%", "").replace(" km", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _find(groups, name):
    for g in groups:
        for it in g.get("statisticsItems", []):
            if it["name"] == name:
                return it
    return None


def load_spain_real(spain_path: list[dict]):
    """Return (per-match rows aligned with spain_path, final shot list) or
    (None, None) if the raw SofaScore data isn't present."""
    if not (RAW / "spain_statistics.json").exists():
        return None, None
    events = json.loads((RAW / "spain_events.json").read_text())
    stats = json.loads((RAW / "spain_statistics.json").read_text())
    shots = json.loads((RAW / "spain_shotmaps.json").read_text())
    events.sort(key=lambda e: e.get("startTimestamp", 0))

    rows = []
    # strict: one stats payload per path step is the reconciliation invariant —
    # a length mismatch means the two sources diverged and must fail loudly.
    for e, step in zip(events, spain_path, strict=True):
        eid = str(e["id"])
        spain_home = e["homeTeam"]["name"] == "Spain"
        st = stats.get(eid)
        groups = st["statistics"][0]["groups"] if st else []

        def side(name, mine=True, *, groups=groups, spain_home=spain_home):
            it = _find(groups, name)
            if not it:
                return None
            want_home = spain_home if mine else (not spain_home)
            return _num(it["home"] if want_home else it["away"])

        rows.append(
            {
                "stage": step["stage"],
                "opponent": step["opponent"],
                "score": step["score"],
                "possession": side("Ball possession"),
                "xg_for": side("Expected goals"),
                "xg_against": side("Expected goals", mine=False),
                "model_xg_for": step.get("model_xg_for"),
                "model_xg_against": step.get("model_xg_against"),
                "shots": side("Total shots"),
                "sot": side("Shots on target"),
                "big_chances": side("Big chances"),
            }
        )

    # final shot map (last chronological event) — pitch coords + per-shot xG
    final_ev = events[-1]
    spain_home = final_ev["homeTeam"]["name"] == "Spain"
    fs = shots.get(str(final_ev["id"]), {})
    shotmap = []
    for s in fs.get("shotmap", []):
        coord = s.get("playerCoordinates") or {}
        shotmap.append(
            {
                "x": coord.get("x"),
                "y": coord.get("y"),
                "xg": round(_num(s.get("xg")) or 0.0, 3),
                "goal": s.get("shotType") == "goal",
                "spain": s.get("isHome") == spain_home,
                "player": s.get("player", {}).get("name"),
            }
        )
    return rows, {"opponent": spain_path[-1]["opponent"], "shots": shotmap}
