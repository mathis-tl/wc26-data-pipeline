# 5. Contracts at the boundary, freshness for staleness

Date: 2026-08-05 · Status: accepted

## Context

The pipeline runs unattended every morning against a third-party API we do not
control. Two whole classes of failure were undefended:

1. **Schema drift** — the API renames or retypes a field. The medallion "archive
   as-is" rule meant a retype would be written to the raw layer unchecked and
   surface hours later as a cryptic dbt compile error on that day's data, far
   from the cause.
2. **Silent staleness** — a run produces no _new_ data (upstream hiccup, empty
   response) but does not error. The row-count tests cannot catch this: 104
   matches of yesterday's data still count 104 and pass every test.

The existing defenses (row-count guards, the reconciliation test, `strict=True`
zips) were strong on _correctness of present data_ and blind to _absence and
drift_.

## Decision

**Schema contracts at the ingestion boundary** (`ingestion/schemas.py`). Each
dataset declares the core fields the downstream models actually build on, with
types and nullability. Between fetch and write: unknown new fields are accepted
and logged (the raw layer keeps them, `union_by_name` absorbs them); a missing
or retyped core field raises `SchemaContractError` naming every violation,
before anything is archived.

**Source freshness** (`loaded_at_field: extracted_at`, warn 26h / error 48h),
run in the ingestion workflow right after the fetch and wired into the same
failure gate as `dbt build`. Deliberately _absent_ from PR CI, where the
committed archive is legitimately as old as the last daily run.

**Enforced dbt contracts** on all four marts, so the typed interface consumed by
the export, the analytics stage and the front is pinned, not implied; and
**JSON contract tests** on the exported files, since the Astro build imports
them statically and a renamed key renders `undefined` rather than failing.

## Consequences

**A defense at every boundary.** Drift fails at ingestion naming the field;
staleness fails at freshness; a modeling regression fails at the mart contract
or the reconciliation test; an export-shape break fails at the contract tests
before deploy. Each failure is loud, early, and close to its cause.

**Costs accepted.** The contracts are a second place (besides the staging SQL)
that encodes the source's shape, so a legitimate upstream change means updating
both — a deliberate tripwire, not a burden, given how rarely a stable API
changes. Freshness thresholds (26h/48h) are tuned to a daily cadence and would
need revisiting for a different schedule; they live in the source YAML for that
reason.

**Boundary with ADR-0001.** These guards are why the historical backfill enters
as its own bounded source with its own contract, rather than by relaxing the
2026 contracts to accommodate a different shape.
