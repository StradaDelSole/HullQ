"""Loader and small declarative helpers for the SLICE-0036 marine-technical
entailment contract (`specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md` /
`specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`).

This module is deliberately thin: it loads the hand-maintained coverage/rule
registry and exposes small, non-recursive lookups. It is not a generic rule
engine and must not become one -- each authorized entailment is a single hop
from its named qualified input(s) to its output(s), applied explicitly by a
caller (or, for the one conditional case, by `project_twin_rudder_count`
below), never chained or executed generically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "RudderCountEntailmentConflict",
    "field_token_classification",
    "load_registry",
    "project_twin_rudder_count",
    "rules_by_id",
]

_DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3] / "specs" / "MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json"
)


class RudderCountEntailmentConflict(ValueError):
    """Legacy v0.5 rudder_type='twin' disagrees with a concrete source rudder_count.

    Raised, never silently resolved, by :func:`project_twin_rudder_count`. Mirrors
    rule MTE-LEGACY-RUD-006 and the pre-existing accepted
    `RudderCountMappingConflict` behavior documented in
    `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.2: two
    disagreeing qualified predecessor facts are flagged for manual/conflict
    resolution (TECHNICAL_PROFILE_SPEC.v0.1.md sections 5-6), not mechanically
    arbitrated.
    """


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load the marine-technical entailment rule registry JSON document.

    Performs no network access and no schema-drift reconciliation; callers that
    need to verify the registry against the live `BOAT_DESIGN_SCHEMA` enum sets
    should do so explicitly (see `tests/contract/test_marine_technical_entailment.py`).
    """
    registry_path = path if path is not None else _DEFAULT_REGISTRY_PATH
    raw: object = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"Registry root must be a JSON object, got {type(raw).__name__}")
    return raw


def field_token_classification(registry: dict[str, Any], field: str, token: str) -> str:
    """Return the classification string for *token* of in-scope *field*.

    Raises `KeyError` for an unrecognized field or an unrecognized token of a
    recognized enum field -- there is no silent default classification: an
    unclassified token is a coverage gap, not a value to guess about.
    """
    field_entry = registry["fields"][field]
    tokens = field_entry["tokens"]
    return str(tokens[token]["classification"])


def rules_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the registry's rule list indexed by rule ID.

    Raises `ValueError` if a duplicate rule ID is present.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for rule in registry["rules"]:
        rule_id = str(rule["id"])
        if rule_id in by_id:
            raise ValueError(f"Duplicate rule id in registry: {rule_id!r}")
        by_id[rule_id] = rule
    return by_id


def project_twin_rudder_count(source_rudder_count: int | None) -> int:
    """Apply rule MTE-LEGACY-RUD-006 to a legacy rudder_type='twin' record.

    A null/unrecorded source count projects to the guaranteed reading of the
    word itself (2). A source count already 2 stays 2 (the two facts agree).
    Any other concrete source count is an internally inconsistent predecessor
    payload; this function refuses to silently pick a winner and raises
    :class:`RudderCountEntailmentConflict` instead.
    """
    if source_rudder_count is None or source_rudder_count == 2:
        return 2
    raise RudderCountEntailmentConflict(
        f"legacy rudder_type='twin' but rudder_count={source_rudder_count!r}; "
        "this is an internally inconsistent predecessor record. Rule "
        "MTE-LEGACY-RUD-006 does not silently resolve it -- flag for manual/"
        "conflict resolution (TECHNICAL_PROFILE_SPEC.v0.1.md sections 5-6)."
    )
