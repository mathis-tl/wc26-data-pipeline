# 3. Recompute standings from results; reconcile against the API

Date: 2026-07-12 · Status: accepted

## Context

football-data.org exposes a `/standings` endpoint that returns the official
group tables directly. The dashboard needs group standings. The path of least
resistance is to clean that endpoint and serve it.

But the standings endpoint is a black box: it gives positions and points with
no way to verify them, and it teaches the reader nothing about how a group
table is actually built.

## Decision

Compute `fct_group_standings` **exclusively from match results**
(`fct_matches`), implementing the FIFA tiebreaker order in SQL: points → goal
difference → goals for (criteria 1–3), then head-to-head points / goal
difference / goals for restricted to the perfectly tied teams (criteria 4–6),
then a deterministic `team_name ASC` fallback. The official `/standings`
endpoint is reserved as an **independent oracle**: a singular test
(`assert_computed_standings_match_official`) full-outer-joins computed against
official and fails the build on any divergence in position, points, goal
difference or goals for — for any of the 48 teams.

## Consequences

**Why this is the whole point.** The endpoint-copy version has nothing to say;
the recomputed version _demonstrates_ the transformation and then _proves_ it
against ground truth on every run. "Reconciled 48/48" on the dashboard is a
live, earned claim, not decoration. This is the difference between a data-display
app and a data-engineering artifact, which is the entire thesis of the project.

**Known limitations, documented not hidden.** Criterion 7 (fair-play points) is
not in the free tier, so it is skipped; criterion 8 (drawing of lots) is
replaced by the deterministic name fallback so results are reproducible. Both
are stated in the model description and surfaced in the essay — the honest move
is to name the gap, not paper over it. Head-to-head is implemented one level
deep (recompute among the tied set), not recursively; no 2026 group needed
deeper, and the reconciliation test would catch it if one did.

**Cost accepted.** More SQL to write and maintain than a passthrough, and a
build that fails when our computation and the official table disagree — which
is precisely the failure we _want_ loud, because it means either our logic or
the upstream data is wrong.

**Rejected — serve the endpoint directly.** Less code, but unverifiable,
uninstructive, and it throws away the one artifact that makes this a portfolio
piece: a provably-correct reimplementation of the competition rules.
