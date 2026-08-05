"""One-off ingestion of real match statistics from SofaScore (via SportApi7 on
RapidAPI) — source #2. The free plan is 50 requests/month, so we fetch only what
powers the flagship: every Spain match's statistics (real xG, possession, shots)
plus the shot map of each Spain knockout game.

The tournament is over, so this data is static: run once.

    uv run python -m ingestion.sofascore
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

WC_UNIQUE_TOURNAMENT = 16
WC_2026_SEASON = 58210
KNOCKOUT_ROUNDS = {"Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final"}
OUT = Path("data/raw/sofascore")


def _client() -> tuple[httpx.Client, str]:
    load_dotenv()
    key, host = os.environ["RAPIDAPI_KEY"], os.environ["RAPIDAPI_HOST"]
    client = httpx.Client(
        base_url=f"https://{host}/api/v1",
        headers={"x-rapidapi-key": key, "x-rapidapi-host": host},
        timeout=30.0,
    )
    return client, host


def _get(client: httpx.Client, path: str) -> dict:
    r = client.get(path)
    r.raise_for_status()
    used = r.headers.get("x-ratelimit-requests-remaining", "?")
    print(f"  GET {path}  (quota remaining: {used})")
    return r.json()


def _spain_team_id() -> int:
    last = json.loads(Path("/tmp/sa_last.json").read_text())
    for e in last["events"]:
        for side in ("homeTeam", "awayTeam"):
            if e[side]["name"] == "Spain":
                return e[side]["id"]
    raise RuntimeError("Spain team id not found in cached events")


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client, _ = _client()
    with client:
        spain_id = _spain_team_id()
        # 1 request — Spain's recent matches (all competitions), filter to WC 2026
        events = _get(client, f"/team/{spain_id}/events/last/0")["events"]
        wc = [
            e
            for e in events
            if e.get("tournament", {}).get("uniqueTournament", {}).get("id") == WC_UNIQUE_TOURNAMENT
            and e.get("season", {}).get("id") == WC_2026_SEASON
        ]
        print(f"Spain WC 2026 matches found: {len(wc)}")
        (OUT / "spain_events.json").write_text(json.dumps(wc, ensure_ascii=False, indent=2))

        stats, shots = {}, {}
        for e in wc:
            eid = e["id"]
            rnd = e.get("roundInfo", {}).get("name", "")
            stats[eid] = _get(client, f"/event/{eid}/statistics")  # xG, possession, shots
            if rnd in KNOCKOUT_ROUNDS:
                shots[eid] = _get(client, f"/event/{eid}/shotmap")  # per-shot xG
        (OUT / "spain_statistics.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2))
        (OUT / "spain_shotmaps.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2))
    print(f"saved -> {OUT}  ({len(stats)} statistics, {len(shots)} shotmaps)")


if __name__ == "__main__":
    run()
