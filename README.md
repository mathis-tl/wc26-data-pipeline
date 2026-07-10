# World Cup 2026 Data Pipeline

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
uv sync                        # install dependencies
cp .env.example .env           # then fill in your API keys
uv run python -m ingestion     # run the daily ingestion (Phase 1)
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
- [ ] Phase 1 — daily raw ingestion (in progress)
- [ ] Phase 2 — dbt modeling + tests
- [ ] Phase 3 — Evidence dashboard on Vercel
- [ ] Phase 4 — end-to-end orchestration + CI
