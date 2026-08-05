# Architecture Decision Records

Short, dated records of the decisions that shaped this pipeline and — as
importantly — the alternatives that were rejected and why. An ADR is written
when a choice is load-bearing enough that a future maintainer (or reviewer)
would otherwise have to reverse-engineer the reasoning from the code.

Format: [Michael Nygard's template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
Status is one of `accepted`, `superseded by ADR-NNN`, or `proposed`.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-versioned-raw-in-git.md) | Version the raw layer in git, not CI artifacts | accepted |
| [0002](0002-duckdb-dbt-over-warehouse.md) | dbt-duckdb over a hosted warehouse | accepted |
| [0003](0003-standings-recomputed-not-copied.md) | Recompute standings from results; reconcile against the API | accepted |
| [0004](0004-model-based-expected-goals.md) | Model-based expected goals, never called xG | accepted |
| [0005](0005-schema-contracts-and-freshness.md) | Contracts at the boundary, freshness for staleness | accepted |
