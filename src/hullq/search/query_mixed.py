"""Mixed numeric + categorical AND query — serialized query-contract v0.2 (SLICE-0035).

Implements slice In-scope item 4 and Deliverables: a versioned mixed
numeric/categorical query representation that (a) keeps the existing
serialized query v0.1 (`hullq.search.query`, numeric-only) readable with
identical meaning, and (b) introduces an explicit v0.2 that adds categorical
leaves without adding silent optional keys to v0.1. `MixedAndQuery.criteria`
may freely combine `NumericLeafCriterion` and `CategoricalLeafCriterion`; the
AND reduction itself is unchanged (`hullq.search.query.and_reduce`) since it
only ever consumes leaf `TruthState`, never a leaf's concrete type.

v0.1 is never rewritten: `mixed_query_from_json_dict` recognizes a "0.1"
payload and delegates parsing byte-for-byte to the untouched
`hullq.search.query.query_from_json_dict`, so v0.1 validation/error messages
and accepted-key sets do not drift. v0.2 criteria carry an explicit "kind"
discriminator ("NUMERIC" | "CATEGORICAL"); any other/missing kind, unknown
top-level/criterion key, or unsupported schema_version/type fails closed.

Does not implement: OR/NOT, PREFER-influenced ranking, nested groups, or
configuration-aware evaluation itself (`hullq.search.configuration_engine`
consumes a `MixedAndQuery`'s `criteria` directly; this module is the
serialization boundary only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from hullq.search.criteria import CategoricalLeafCriterion, NumericLeafCriterion
from hullq.search.query import AndQuery, query_from_json_dict
from hullq.search.types import LeafCriterionKind, NumericComparisonKind, RequirementStrength
from hullq.search.values import is_finite_real_number

__all__ = [
    "MixedAndQuery",
    "MixedLeafCriterion",
    "mixed_query_from_json_dict",
    "mixed_query_to_json_dict",
]

_QUERY_TYPE = "AND"
_SCHEMA_VERSION_V1 = "0.1"
_SCHEMA_VERSION_V2 = "0.2"

_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset({"schema_version", "type", "criteria"})
_NUMERIC_CRITERION_KEYS: Final[frozenset[str]] = frozenset(
    {"kind", "field", "comparison", "threshold_min", "threshold_max", "strength"}
)
_CATEGORICAL_CRITERION_KEYS: Final[frozenset[str]] = frozenset(
    {"kind", "field", "equals", "strength"}
)

MixedLeafCriterion = NumericLeafCriterion | CategoricalLeafCriterion


@dataclass(frozen=True, slots=True)
class MixedAndQuery:
    """An explicit AND-grouped query over one or more numeric/categorical MUST leaves.

    Order of `criteria` is part of the serialized identity but does not
    affect evaluation truth (AND is order-independent), matching `AndQuery`.
    """

    criteria: tuple[MixedLeafCriterion, ...]

    def __post_init__(self) -> None:
        if not self.criteria:
            raise ValueError("MixedAndQuery requires at least one criterion")
        for criterion in self.criteria:
            if not isinstance(criterion, NumericLeafCriterion | CategoricalLeafCriterion):
                raise ValueError(
                    f"MixedAndQuery.criteria entries must be NumericLeafCriterion or "
                    f"CategoricalLeafCriterion; got {type(criterion).__name__}"
                )


# ---------------------------------------------------------------------------
# Serialization — always emits v0.2
# ---------------------------------------------------------------------------


def _numeric_criterion_to_json_dict(criterion: NumericLeafCriterion) -> dict[str, Any]:
    return {
        "kind": LeafCriterionKind.NUMERIC.value,
        "field": criterion.field,
        "comparison": criterion.comparison.value,
        "threshold_min": criterion.threshold_min,
        "threshold_max": criterion.threshold_max,
        "strength": criterion.strength.value,
    }


def _categorical_criterion_to_json_dict(criterion: CategoricalLeafCriterion) -> dict[str, Any]:
    return {
        "kind": LeafCriterionKind.CATEGORICAL.value,
        "field": criterion.field,
        "equals": criterion.equals,
        "strength": criterion.strength.value,
    }


def _criterion_to_json_dict(criterion: MixedLeafCriterion) -> dict[str, Any]:
    if isinstance(criterion, NumericLeafCriterion):
        return _numeric_criterion_to_json_dict(criterion)
    return _categorical_criterion_to_json_dict(criterion)


def mixed_query_to_json_dict(query: MixedAndQuery) -> dict[str, Any]:
    """Serialize *query* to a deterministic v0.2 JSON-compatible mapping.

    Always emits schema_version "0.2", even when every leaf happens to be
    numeric: a `MixedAndQuery` is never silently downgraded to v0.1, so a
    caller can never lose track of which parser round-trips it losslessly.
    Round-trips losslessly through `mixed_query_from_json_dict`.
    """
    return {
        "schema_version": _SCHEMA_VERSION_V2,
        "type": _QUERY_TYPE,
        "criteria": [_criterion_to_json_dict(c) for c in query.criteria],
    }


# ---------------------------------------------------------------------------
# Deserialization — accepts v0.1 (delegated) and v0.2
# ---------------------------------------------------------------------------


def _numeric_criterion_from_json_dict(data: dict[str, Any]) -> NumericLeafCriterion:
    unknown_keys = set(data.keys()) - _NUMERIC_CRITERION_KEYS
    if unknown_keys:
        raise ValueError(
            f"Unknown numeric leaf criterion field(s) {sorted(unknown_keys)}; "
            f"future query-contract fields require explicit schema/version evolution"
        )
    try:
        field_name = data["field"]
        comparison = NumericComparisonKind(data["comparison"])
        strength = RequirementStrength(data["strength"])
        threshold_min = data["threshold_min"]
        threshold_max = data["threshold_max"]
    except KeyError as exc:
        raise ValueError(f"Malformed numeric leaf criterion, missing key: {exc}") from exc
    if not isinstance(field_name, str):
        raise ValueError(f"criterion.field must be a string, got {type(field_name).__name__}")
    if threshold_min is not None and not is_finite_real_number(threshold_min):
        raise ValueError(
            f"criterion.threshold_min must be a finite, non-bool numeric value or null; "
            f"got {threshold_min!r}"
        )
    if threshold_max is not None and not is_finite_real_number(threshold_max):
        raise ValueError(
            f"criterion.threshold_max must be a finite, non-bool numeric value or null; "
            f"got {threshold_max!r}"
        )
    return NumericLeafCriterion(
        field=field_name,
        comparison=comparison,
        threshold_min=None if threshold_min is None else float(threshold_min),
        threshold_max=None if threshold_max is None else float(threshold_max),
        strength=strength,
    )


def _categorical_criterion_from_json_dict(data: dict[str, Any]) -> CategoricalLeafCriterion:
    unknown_keys = set(data.keys()) - _CATEGORICAL_CRITERION_KEYS
    if unknown_keys:
        raise ValueError(
            f"Unknown categorical leaf criterion field(s) {sorted(unknown_keys)}; "
            f"future query-contract fields require explicit schema/version evolution"
        )
    try:
        field_name = data["field"]
        equals = data["equals"]
        strength = RequirementStrength(data["strength"])
    except KeyError as exc:
        raise ValueError(f"Malformed categorical leaf criterion, missing key: {exc}") from exc
    if not isinstance(field_name, str):
        raise ValueError(f"criterion.field must be a string, got {type(field_name).__name__}")
    if not isinstance(equals, str):
        raise ValueError(f"criterion.equals must be a string, got {type(equals).__name__}")
    return CategoricalLeafCriterion(field=field_name, equals=equals, strength=strength)


def _mixed_criterion_from_json_dict(data: object) -> MixedLeafCriterion:
    if not isinstance(data, dict):
        raise ValueError(
            f"Query v0.2 leaf criterion must be a JSON object, got {type(data).__name__}"
        )
    kind = data.get("kind")
    if kind == LeafCriterionKind.NUMERIC.value:
        return _numeric_criterion_from_json_dict(data)
    if kind == LeafCriterionKind.CATEGORICAL.value:
        return _categorical_criterion_from_json_dict(data)
    raise ValueError(
        f"Unsupported or missing query v0.2 leaf criterion kind: {kind!r}; expected "
        f"{LeafCriterionKind.NUMERIC.value!r} or {LeafCriterionKind.CATEGORICAL.value!r}"
    )


def mixed_query_from_json_dict(data: dict[str, Any]) -> MixedAndQuery:
    """Deserialize a `MixedAndQuery` from a v0.1 or v0.2 payload.

    A "0.1" payload is parsed by the unmodified
    `hullq.search.query.query_from_json_dict` (byte-for-byte identical
    validation/semantics to SLICE-0033) and its numeric criteria are wrapped
    unchanged into a `MixedAndQuery` — no re-interpretation, no drift. A
    "0.2" payload is parsed directly, dispatching each criterion on its
    explicit "kind" discriminator. Any other schema_version, an unsupported
    "type", an unknown top-level/criterion key, or an unrecognized/missing
    "kind" raises `ValueError` — fails closed, never silently discards or
    coerces unrecognized input.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Query payload must be a JSON object, got {type(data).__name__}")

    schema_version = data.get("schema_version")
    if schema_version == _SCHEMA_VERSION_V1:
        v1_query: AndQuery = query_from_json_dict(data)
        return MixedAndQuery(criteria=tuple(v1_query.criteria))
    if schema_version != _SCHEMA_VERSION_V2:
        raise ValueError(f"Unsupported query schema_version: {schema_version!r}")

    unknown_keys = set(data.keys()) - _TOP_LEVEL_KEYS
    if unknown_keys:
        raise ValueError(
            f"Unknown top-level query field(s) {sorted(unknown_keys)}; "
            f"future query-contract fields require explicit schema/version evolution"
        )
    if data.get("type") != _QUERY_TYPE:
        raise ValueError(f"Unsupported query type: {data.get('type')!r}")
    raw_criteria = data.get("criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise ValueError("query.criteria must be a non-empty list")
    criteria = tuple(_mixed_criterion_from_json_dict(c) for c in raw_criteria)
    return MixedAndQuery(criteria=criteria)
