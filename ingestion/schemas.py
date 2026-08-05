"""Schema contracts for the raw layer.

The raw writer archives API payloads as-is — that is the medallion deal —
but "as-is" must not mean "unchecked". Each dataset declares the core
fields the downstream models depend on, with their expected types. The
drift policy, applied before anything is written:

- unknown new fields   -> accepted and logged (the raw layer keeps them;
                          union_by_name absorbs them downstream)
- missing core field   -> SchemaContractError, nothing written
- mistyped core field  -> SchemaContractError, nothing written

So a upstream rename or retype fails the ingestion run at the boundary,
with a message naming the exact field — instead of surfacing hours later
as a cryptic dbt compilation error on yesterday's data.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class SchemaContractError(Exception):
    """A core field is missing or mistyped in the API payload."""


@dataclass(frozen=True)
class FieldSpec:
    """Expected type(s) for a core field. `nullable` fields may be None
    (fixtures without scores, TBD teams in early knockout rows...)."""

    types: tuple[type, ...]
    nullable: bool = True

    def check(self, value: object) -> bool:
        if value is None:
            return self.nullable
        return isinstance(value, self.types)


# Core fields per dataset: the subset of the payload the pipeline actually
# builds on (staging casts, keys, joins). Everything else may drift freely.
MATCHES_CORE: dict[str, FieldSpec] = {
    "id": FieldSpec((int,), nullable=False),
    "utcDate": FieldSpec((str,), nullable=False),
    "status": FieldSpec((str,), nullable=False),
    "stage": FieldSpec((str,), nullable=False),
    "group": FieldSpec((str,)),
    "homeTeam": FieldSpec((dict,), nullable=False),
    "awayTeam": FieldSpec((dict,), nullable=False),
    "score": FieldSpec((dict,), nullable=False),
    "lastUpdated": FieldSpec((str,), nullable=False),
}

STANDINGS_CORE: dict[str, FieldSpec] = {
    "position": FieldSpec((int,), nullable=False),
    "team": FieldSpec((dict,), nullable=False),
    "playedGames": FieldSpec((int,), nullable=False),
    "points": FieldSpec((int,), nullable=False),
    "goalsFor": FieldSpec((int,), nullable=False),
    "goalsAgainst": FieldSpec((int,), nullable=False),
    "goalDifference": FieldSpec((int,), nullable=False),
    "standing": FieldSpec((dict,), nullable=False),  # group context added by storage
}

SCORERS_CORE: dict[str, FieldSpec] = {
    "player": FieldSpec((dict,), nullable=False),
    "team": FieldSpec((dict,), nullable=False),
    "goals": FieldSpec((int,), nullable=False),
    "assists": FieldSpec((int,)),
    "penalties": FieldSpec((int,)),
}

CONTRACTS: dict[str, dict[str, FieldSpec]] = {
    "matches": MATCHES_CORE,
    "standings": STANDINGS_CORE,
    "scorers": SCORERS_CORE,
}


def validate_rows(rows: list[dict], *, dataset: str) -> list[dict]:
    """Validate every row against the dataset's core contract.

    Returns the rows unchanged on success (so it chains naturally into the
    writer). Logs unknown fields once per run. Raises SchemaContractError
    naming every violation, never just the first one.
    """
    contract = CONTRACTS.get(dataset)
    if contract is None:
        logger.warning("%s: no schema contract declared, rows pass through unchecked", dataset)
        return rows

    violations: list[str] = []
    unknown: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            violations.append(f"row {i}: not an object")
            continue
        for name, spec in contract.items():
            if name not in row:
                violations.append(f"row {i}: missing core field '{name}'")
            elif not spec.check(row[name]):
                violations.append(
                    f"row {i}: field '{name}' has type {type(row[name]).__name__}, "
                    f"expected {' | '.join(t.__name__ for t in spec.types)}"
                    f"{' | None' if spec.nullable else ''}"
                )
        unknown.update(k for k in row if k not in contract)

    if unknown:
        logger.info(
            "%s: %d field(s) outside the core contract (accepted, archived as-is): %s",
            dataset,
            len(unknown),
            ", ".join(sorted(unknown)),
        )
    if violations:
        preview = "; ".join(violations[:10])
        more = f" (+{len(violations) - 10} more)" if len(violations) > 10 else ""
        raise SchemaContractError(
            f"{dataset}: {len(violations)} contract violation(s): {preview}{more}"
        )

    logger.info("%s: %d rows validated against the core contract", dataset, len(rows))
    return rows
