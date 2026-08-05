"""One-off ingestion of real match statistics from SofaScore (via SportApi7 on
RapidAPI) — source #2. The free plan is 50 requests/month, so we fetch only what
powers the flagship: every Spain match's statistics (real xG, possession, shots)
plus the shot map of each Spain knockout game.

The 2026 tournament is over, so this data is static and already archived under
data/raw/sofascore/. This script documents *how* it was fetched and can
reproduce it, but it will not spend quota on an accidental re-run: it refuses
to fetch when the archive already exists unless called with --force.

    uv run python -m ingestion.sofascore            # no-op if already archived
    uv run python -m ingestion.sofascore --force    # re-fetch (spends ~13 req)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

logger = logging.getLogger("ingestion.sofascore")

WC_UNIQUE_TOURNAMENT = 16
WC_2026_SEASON = 58210
KNOCKOUT_ROUNDS = {"Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final"}
OUT = Path("data/raw/sofascore")

# Spain's SofaScore team id, resolved once from the live API and pinned here so
# the fetch is self-contained (no manual pre-step, no /tmp handoff). Stable for
# a finished tournament; a re-run verifies it against the events it pulls.
SPAIN_TEAM_ID = 4698

EXPECTED_MATCHES = 8  # Spain's full 2026 run: 3 group + 4 knockout + final


def _client() -> httpx.Client:
    load_dotenv()
    try:
        key, host = os.environ["RAPIDAPI_KEY"], os.environ["RAPIDAPI_HOST"]
    except KeyError as exc:
        raise RuntimeError(f"missing env var {exc}; set RAPIDAPI_KEY and RAPIDAPI_HOST") from exc
    return httpx.Client(
        base_url=f"https://{host}/api/v1",
        headers={"x-rapidapi-key": key, "x-rapidapi-host": host},
        timeout=30.0,
    )


def _get(client: httpx.Client, path: str) -> dict:
    r = client.get(path)
    r.raise_for_status()
    remaining = r.headers.get("x-ratelimit-requests-remaining", "?")
    logger.info("GET %s (quota remaining: %s)", path, remaining)
    return r.json()


def _verify_spain(events: list[dict]) -> None:
    """Guard: every event we archive must actually involve the pinned Spain id
    — a mismatch means the id or the API changed, so fail instead of writing
    someone else's matches under the Spain filename."""
    for e in events:
        sides = {e["homeTeam"]["id"], e["awayTeam"]["id"]}
        if SPAIN_TEAM_ID not in sides:
            raise RuntimeError(f"event {e['id']} does not involve Spain id {SPAIN_TEAM_ID}")


def run(force: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    archive = OUT / "spain_events.json"
    if archive.exists() and not force:
        logger.info(
            "archive already present at %s — skipping (pass --force to re-fetch and spend quota)",
            OUT,
        )
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    with _client() as client:
        # 1 request — Spain's recent matches (all competitions), filtered to WC 2026
        events = _get(client, f"/team/{SPAIN_TEAM_ID}/events/last/0")["events"]
        wc = [
            e
            for e in events
            if e.get("tournament", {}).get("uniqueTournament", {}).get("id") == WC_UNIQUE_TOURNAMENT
            and e.get("season", {}).get("id") == WC_2026_SEASON
        ]
        _verify_spain(wc)
        logger.info("Spain WC 2026 matches found: %d (expected %d)", len(wc), EXPECTED_MATCHES)
        if len(wc) != EXPECTED_MATCHES:
            logger.warning("match count differs from the expected %d", EXPECTED_MATCHES)
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
    logger.info("saved -> %s (%d statistics, %d shotmaps)", OUT, len(stats), len(shots))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-fetch even if the archive exists (spends quota)"
    )
    args = parser.parse_args()
    return run(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
