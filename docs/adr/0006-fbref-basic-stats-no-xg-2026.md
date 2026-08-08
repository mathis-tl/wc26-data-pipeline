# 6. FBref basic team stats as a third source — real, but no xG for 2026

Date: 2026-08-06 · Status: accepted

## Context

ADR-0004 commits to never calling the Poisson model's output "xG", precisely
because the primary source (football-data.org) carries no shot data to
validate it against. The SofaScore source (ADR context, `analytics/real_stats.py`)
closes that gap for Spain's 8 matches alone — real xG, but scoped to one team
and gated by a 50-request/month free quota.

The natural next question: can the model's ratings be checked against real
shot volumes for **all 48 teams**, not just Spain? `soccerdata`'s FBref reader
was evaluated for this. Two things were verified by inspection, not assumed:

1. **It works for this tournament.** `soccerdata` gets past FBref's Cloudflare
   challenge and `read_team_season_stats(league="INT-World Cup", season=2026)`
   returns all 48 teams.
2. **It has no xG for 2026.** For international competitions FBref exposes
   exactly 5 aggregated season tables — `standard`, `keeper`, `shooting`,
   `playing_time`, `misc` — and **none carries an "Expected" column**. FBref's
   xG pages exist for the 2022 World Cup (StatsBomb-sourced) but not 2026.
   Real xG for all 48 teams remains unavailable for free (SofaScore's own free
   tier is 50 req/month against ~105 needed; API-Football is unverified).

So the source is real and free, but it answers a narrower question than "is
the model's xG right" — it answers "does the model's *ranking* survive contact
with real shot volumes, keeper numbers and discipline".

## Decision

Add FBref (via `soccerdata`) as source #3, scoped to what it actually offers:

- **`ingestion/fbref.py`** — run-once, refuses to re-fetch (and re-solve the
  Cloudflare challenge) unless `--force`, mirroring `ingestion/sofascore.py`.
  Pulls the 5 basic tables, keeps only the columns the reality check needs
  (shots, SoT, SoT%, G/Sh, possession, GA, SoTA, saves, save%, clean sheets,
  cards), writes `data/raw/fbref/team_basic_2026.csv` — versioned in git per
  ADR-0001.
- **`analytics/real_fbref.py`** — reconciles FBref's team names against
  `dim_teams` via an **explicit** `NAME_MAP` (not fuzzy matching): FBref says
  "Cabo Verde", "Côte d'Ivoire", "IR Iran", "Korea Republic", "Türkiye",
  "Bosnia–Herz"; `dim_teams` says "Cape Verde Islands", "Ivory Coast", "Iran",
  "South Korea", "Turkey", "Bosnia-Herzegovina". Every other team name matches
  by identity. Both mismatch directions raise loudly instead of dropping a
  team silently: an unmapped FBref name (`ReconciliationError`), or a
  `dim_teams` team FBref's 48 never covered (`RuntimeError` in
  `analytics/__main__.py`).
- **`dashboard/src/data/team_reality.json`** — one row per team, the model's
  `rank_overall` / `rank_attack` / `rank_defense` / `attack` / `defense` /
  `rating` next to FBref's real `possession`, `shots`, `sot`, `sot_pct`,
  `sota`, `ga`, `save_pct`, `cs`, `conversion` (`G/Sh`, i.e. goals per shot —
  named "conversion", never "xG").
- **`model_meta.json`'s note is nuanced, not rewritten**: the model still
  produces *modeled* expected goals, never measured; it now also says real
  shot volumes exist as a complement, and still names ADR-0004 and this ADR
  as the reason "xG" never appears for the model's output.

## Consequences

**Why this is worth the reconciliation risk.** Team-name reconciliation across
sources is the one place this kind of join silently rots — a single unmapped
name means a team quietly vanishes from a "48 teams" claim. Making the map
explicit and asserting on both directions (FBref → dim_teams and back) turns
that failure mode into a loud one at pipeline-run time instead of a reader
noticing a missing row on the dashboard.

**Boundary with ADR-0004.** FBref basic stats are shot *volumes*, not
shot-quality (xG) — `G/Sh` (goals per shot actually taken) is a real,
unambiguous ratio, but it is not the same claim as "probability this shot
becomes a goal" that xG makes from shot location and type. The field is named
`conversion`, and the ADR-0004 discipline (never call model output "xG") is
joined by a matching discipline here: never call *this* "xG" either, even
though it is real and shot-based — it just isn't shot-quality data.

**Costs accepted.** A third source means a third reconciliation surface and a
third raw-archive format to keep versioned (ADR-0001). Accepted because the
gain — a 48-team reality check instead of a 1-team one — is exactly the
upgrade the flagship analysis needed, and the fetch is genuinely run-once
(tournament is over, `--force` is the only way to spend the Cloudflare-solve
cost again).

**Rejected — fuzzy name matching (e.g. `difflib`, edit distance).** Would
silently "resolve" a genuine drift (a renamed or newly-added team) to the
nearest wrong name instead of failing. With only 48 teams and 6 real
divergences, an explicit map costs nothing and fails safely.

**Rejected — chasing real xG for all 48 teams.** Ruled out this session:
FBref doesn't have it for 2026; SofaScore's free tier can't cover 105+
requests; API-Football's `expected_goals` field is unverified. Real xG stays
scoped to Spain (SofaScore, `spain_real.json`) until a paid tier or a verified
free source changes that trade-off — a decision for its own ADR if it happens.
