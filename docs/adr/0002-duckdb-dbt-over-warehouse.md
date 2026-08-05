# 2. dbt-duckdb over a hosted warehouse

Date: 2026-07-11 · Status: accepted

## Context

The modeling layer needs a SQL engine and a transformation framework. The
industry-default stack for a dbt project is a hosted warehouse — Snowflake,
BigQuery, Redshift — with dbt Cloud or a runner on top.

Constraints particular to this project: it runs entirely inside GitHub Actions
on a free plan, has no budget, must rebuild deterministically from the
committed raw layer on every run, and reads Parquet files partitioned on disk
(ADR-0001).

## Decision

Use dbt with the **dbt-duckdb** adapter. DuckDB reads the raw Parquet directly
via an external-location source (`read_parquet(..., hive_partitioning=true,
union_by_name=true)`); the warehouse is a single `data/warehouse.duckdb` file
rebuilt from scratch each run. Staging and intermediate are views, marts are
tables.

## Consequences

**Why this fits.** DuckDB is an in-process OLAP engine: no server, no
credentials, no network — the entire platform is `uv run dbt build` against
local files, which is exactly what a CI job and a laptop can both do
identically. `union_by_name` on the source makes the raw layer's
schema-drift-across-partitions a non-issue at read time. Because the warehouse
is rebuilt from committed raw on every run, it is disposable and reproducible:
delete it, rebuild, get byte-for-identical marts. That reproducibility is what
lets the warehouse stay _out_ of git (only the raw layer and the exported JSON
are versioned).

**Costs accepted.** No warehouse means no shared compute, no concurrent
readers, no time-travel beyond what the raw partitions provide, and a dataset
size ceiling set by "fits in a CI runner's memory/disk". All comfortably
irrelevant at 104 matches; all disqualifying at production analytics scale.
Because the `.duckdb` file is amnesiac across runs, anything that must persist
between runs (the run log, ADR-0005/observability) is written to git as JSONL
rather than to a warehouse table.

**Rejected — hosted warehouse.** The correct choice for a real team with real
scale and real budget, and the natural migration target if this pipeline ever
outgrew a single machine: the dbt models themselves are adapter-portable, so
the move would touch `profiles.yml` and the external-source definition, not the
SQL. Adopting it now would have added cost, secrets, and network dependence to
buy scale the project does not need.
