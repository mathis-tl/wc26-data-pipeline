# 1. Version the raw layer in git, not CI artifacts

Date: 2026-07-10 · Status: accepted

## Context

The pipeline captures a live tournament: one shot per day at each day's data,
no replay if a run is missed. The raw API responses have to be persisted
somewhere durable and, ideally, auditable — "what did the API actually say on
July 3rd?" must be answerable months later.

The obvious default is to treat raw captures as build artifacts: upload them
from the daily job to object storage (S3, GCS) or GitHub Actions artifacts,
and keep only the modeled warehouse in the repo.

## Decision

Commit the raw Parquet files to git, partitioned by extraction date
(`data/raw/<source>/<dataset>/extraction_date=YYYY-MM-DD/`). Each daily run
opens an auto-merged `data`-labelled PR containing that day's captures.

## Consequences

**Why this, for this project.** The daily commits _are_ the proof the pipeline
ran: a green dot per day in the repo's history is a timestamped, tamper-evident
record that a hosted artifact bucket does not give a reader browsing the repo.
For a portfolio piece whose whole point is "this ran every morning for a
month", that visible cadence is a feature, not incidental. `git log data/raw`
is the audit trail; `git show <sha>:<path>` reconstructs any day's raw state
with zero extra infrastructure and zero credentials.

**Costs accepted.** Repo size grows monotonically — acceptable here because the
payloads are small (~70 KB/day/dataset, Parquet-compressed) and the tournament
is finite (~40 days). A multi-year or high-volume source would blow this budget
and push the decision back toward object storage; see the boundary in ADR-0005
on why the historical backfill comes in as its own bounded source rather than
by accumulating daily captures forever. `git push` needed
`http.postBuffer=524288000` for the initial large packs.

**Rejected — CI artifacts / object storage.** Durable and scalable, but opaque
from the repo, credential-gated, and with retention policies that quietly
delete history (GitHub artifacts default to 90 days). The auditability and the
"visible daily cadence" were worth more than the scalability we do not need at
this volume.
