# World Cup 2026 Data Pipeline

[![CI](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ci.yml)
[![Daily ingestion](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ingest.yml/badge.svg)](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ingest.yml)

End-to-end ELT pipeline on the 2026 FIFA World Cup: daily ingestion from football
APIs, dimensional modeling with dbt + DuckDB, and a public dashboard built with
Astro — orchestrated by GitHub Actions, on a 100% free stack.

> 🚧 Built **during** the tournament. Daily archives land in [`data/raw/`](data/raw/)
> and [`dashboard/src/data/`](dashboard/src/data/) via automated PRs; check the history.

## Architecture

```
football-data.org ─► Python (httpx) ─► data/raw/ (Parquet) ─► dbt + DuckDB ─► JSON ─► Astro ─► Vercel
                        ▲ GitHub Actions (daily cron, 06:00 UTC)  staging → marts   export   static site
```

- **Raw** — API responses stored untouched as timestamped Parquet, versioned in git.
- **Staging** — typed, deduplicated, group codes normalized across endpoints (dbt).
- **Marts** — star schema (`fct_matches`, `dim_teams`, `fct_group_standings`) with
  FIFA tiebreaker standings, reconciled 48/48 against the official ones.
- **Dashboard** — marts exported to JSON, rendered by a static Astro site. The
  front never depends on Python/dbt to build.

## Quickstart

```bash
# data platform
uv sync --group dbt                                      # install Python deps
cp .env.example .env                                     # then fill in your API keys
uv run python -m ingestion                               # run the daily ingestion
uv run dbt build --project-dir dbt --profiles-dir dbt    # build & test the models
uv run python dashboard/scripts/export_marts.py          # export marts → JSON

# dashboard
cd dashboard && npm install && npm run build             # static site → dashboard/dist/
```

## Project layout

| Path | Role |
|---|---|
| `ingestion/` | Python API client + Parquet writers (E + L) |
| `data/raw/` | Immutable raw layer, partitioned by extraction date |
| `dbt/` | dbt-duckdb project: staging + marts (T) |
| `dashboard/` | Astro static dashboard + the marts→JSON export script |
| `.github/workflows/` | Daily ingestion cron + CI |

## Daily data PRs

The pipeline commits each day's raw + JSON through an **auto-merged PR labelled
`data`** (main is protected and the Actions app cannot bypass the ruleset on a
personal repo). To browse only human PRs, filter with `is:pr -label:data`.

## Status

- [x] Phase 0 — repo scaffolding
- [x] Phase 1 — daily raw ingestion (live since 2026-07-11)
- [x] Phase 2 — dbt modeling + tests (staging, star-schema marts, FIFA
      tiebreaker standings reconciled against the official ones)
- [x] Phase 3 — Astro dashboard (marts → JSON → static site → Vercel)
- [ ] Phase 4 — end-to-end orchestration + CI polish
