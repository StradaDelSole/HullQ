"""Explicit AND query expression, evaluation and JSON serialization — SLICE-0033.

Implements SEARCH_QUERY_SEMANTICS.v0.1.md §1 (AND truth reduction) and §8
(explicit boolean structure — grouping MUST be represented in the query
contract, never inferred) for the implemented numeric-MUST subset, plus the
slice's Required Behavior §B/§C/§D.

Does not implement: OR/NOT, PREFER-influenced ranking, or nested groups —
all explicitly out of scope for this slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from hullq.search.criteria import (
    CriterionEvaluation,
    NumericLeafCriterion,
    evaluate_numeric_leaf,
)
from hullq.search.projection import SearchableDesignProjection
from hullq.search.types import NumericComparisonKind, RequirementStrength, ResultClass, TruthState
from hullq.search.values import is_finite_real_number

__all__ = [
    "AndQuery",
    "QueryEvaluation",
    "and_reduce",
    "evaluate_and_query",
    "query_from_json_dict",
    "query_to_json_dict",
    "result_class_for",
]

_QUERY_TYPE = "AND"
_SCHEMA_VERSION = "0.1"

# Exact known key sets for schema_version 0.1. Any other key is a semantic-drift
# risk (e.g. a silently-ignored "unit") and MUST be rejected, not discarded.
_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset({"schema_version", "type", "criteria"})
_CRITERION_KEYS: Final[frozenset[str]] = frozenset(
    {"field", "comparison", "threshold_min", "threshold_max", "strength"}
)


@dataclass(frozen=True, slots=True)
class AndQuery:
    """An explicit AND-grouped query over one or more numeric MUST leaves.

    Order of `criteria` is part of the serialized identity but does not
    affect evaluation truth (AND is order-independent); it only affects the
    order criterion-level explanations are reported in.
    """

    criteria: tuple[NumericLeafCriterion, ...]

    def __post_init__(self) -> None:
        if not self.criteria:
            raise ValueError("AndQuery requires at least one criterion")


@dataclass(frozen=True, slots=True)
class QueryEvaluation:
    """One design's result class plus full per-criterion explanation."""

    design_id: str
    result_class: ResultClass
    criterion_evaluations: tuple[CriterionEvaluation, ...]


def and_reduce(truths: tuple[TruthState, ...]) -> TruthState:
    """Reduce leaf truth states with explicit AND semantics.

    SEARCH_QUERY_SEMANTICS.v0.1.md §1: any FALSE => FALSE; all TRUE => TRUE;
    otherwise UNKNOWN. `truths` MUST be non-empty.
    """
    if not truths:
        raise ValueError("and_reduce requires at least one truth state")
    if any(t is TruthState.FALSE for t in truths):
        return TruthState.FALSE
    if all(t is TruthState.TRUE for t in truths):
        return TruthState.TRUE
    return TruthState.UNKNOWN


def result_class_for(truth: TruthState) -> ResultClass:
    """Map an aggregate query truth state to its product result class.

    Slice Required Behavior §C: only CONFIRMED_MATCH belongs to the primary
    result set/count; CONFIRMED_NON_MATCH and INSUFFICIENT_DATA are separate.
    """
    if truth is TruthState.TRUE:
        return ResultClass.CONFIRMED_MATCH
    if truth is TruthState.FALSE:
        return ResultClass.CONFIRMED_NON_MATCH
    return ResultClass.INSUFFICIENT_DATA


def evaluate_and_query(query: AndQuery, projection: SearchableDesignProjection) -> QueryEvaluation:
    """Evaluate every leaf of *query* against *projection* and classify the result."""
    evaluations = tuple(
        evaluate_numeric_leaf(criterion, projection.get(criterion.field))
        for criterion in query.criteria
    )
    aggregate = and_reduce(tuple(e.truth for e in evaluations))
    return QueryEvaluation(
        design_id=projection.design_id,
        result_class=result_class_for(aggregate),
        criterion_evaluations=evaluations,
    )


# ---------------------------------------------------------------------------
# Deterministic JSON-compatible serialization
# ---------------------------------------------------------------------------


def _criterion_to_json_dict(criterion: NumericLeafCriterion) -> dict[str, Any]:
    return {
        "field": criterion.field,
        "comparison": criterion.comparison.value,
        "threshold_min": criterion.threshold_min,
        "threshold_max": criterion.threshold_max,
        "strength": criterion.strength.value,
    }


def _criterion_from_json_dict(data: object) -> NumericLeafCriterion:
    if not isinstance(data, dict):
        raise ValueError(f"Numeric leaf criterion must be a JSON object, got {type(data).__name__}")
    unknown_keys = set(data.keys()) - _CRITERION_KEYS
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


def query_to_json_dict(query: AndQuery) -> dict[str, Any]:
    """Serialize *query* to a deterministic JSON-compatible mapping.

    Round-trips losslessly through `query_from_json_dict` — no semantic
    drift in field, comparison, thresholds or requirement strength.
    """
    return {
        "schema_version": _SCHEMA_VERSION,
        "type": _QUERY_TYPE,
        "criteria": [_criterion_to_json_dict(c) for c in query.criteria],
    }


def query_from_json_dict(data: dict[str, Any]) -> AndQuery:
    """Deserialize an `AndQuery` from a mapping produced by `query_to_json_dict`.

    Fails closed (raises `ValueError`) on an unrecognized schema version,
    query type, unknown top-level/criterion key, or malformed/unknown-enum
    criterion — never silently discards or coerces unrecognized input.
    Future query-contract fields require explicit schema/version evolution,
    not silent acceptance.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Query payload must be a JSON object, got {type(data).__name__}")
    unknown_keys = set(data.keys()) - _TOP_LEVEL_KEYS
    if unknown_keys:
        raise ValueError(
            f"Unknown top-level query field(s) {sorted(unknown_keys)}; "
            f"future query-contract fields require explicit schema/version evolution"
        )
    if data.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"Unsupported query schema_version: {data.get('schema_version')!r}")
    if data.get("type") != _QUERY_TYPE:
        raise ValueError(f"Unsupported query type: {data.get('type')!r}")
    raw_criteria = data.get("criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise ValueError("query.criteria must be a non-empty list")
    criteria = tuple(_criterion_from_json_dict(c) for c in raw_criteria)
    return AndQuery(criteria=criteria)
