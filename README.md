# World Cup 2026 Data Pipeline

[![CI](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ci.yml)
[![Daily ingestion](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ingest.yml/badge.svg)](https://github.com/mathis-tl/wc26-data-pipeline/actions/workflows/ingest.yml)

End-to-end ELT pipeline on the 2026 FIFA World Cup: daily ingestion from football
APIs, dimensional modeling with dbt + DuckDB, and a public dashboard built with
Evidence — orchestrated by GitHub Actions, on a 100% free stack.

> 🚧 Work in progress — the pipeline is being built **during** the tournament.
> Daily raw archives land in [`data/raw/`](data/raw/); check the commit history.

## Architecture

```
football-data.org ─┐
API-Football      ─┼─► Python (httpx) ─► data/raw/ (Parquet) ─► dbt + DuckDB ─► Evidence ─► Vercel
openfootball      ─┘        ▲ GitHub Actions (daily cron)      staging → marts
```

- **Raw** — API responses stored untouched as timestamped Parquet, versioned in git.
- **Staging** — typed, deduplicated, IDs reconciled across sources (dbt).
- **Marts** — star schema (`fct_matches`, `dim_teams`, …) feeding the dashboard.

## Quickstart

```bash
uv sync --group dbt            # install dependencies
cp .env.example .env           # then fill in your API keys
uv run python -m ingestion     # run the daily ingestion
uv run dbt build --project-dir dbt --profiles-dir dbt   # build & test the models
```

## Project layout

| Path | Role |
|---|---|
| `ingestion/` | Python API clients + Parquet writers (E + L) |
| `data/raw/` | Immutable raw layer, partitioned by extraction date |
| `dbt/` | dbt-duckdb project: staging + marts (T) — Phase 2 |
| `dashboard/` | Evidence dashboard — Phase 3 |
| `.github/workflows/` | Daily ingestion cron + CI |

## Status

- [x] Phase 0 — repo scaffolding
- [x] Phase 1 — daily raw ingestion (live since 2026-07-11)
- [x] Phase 2 — dbt modeling + tests (staging, star-schema marts, FIFA
      tiebreaker standings reconciled against the official ones)
- [ ] Phase 3 — Evidence dashboard on Vercel
- [ ] Phase 4 — end-to-end orchestration + CI polish
