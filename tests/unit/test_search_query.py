"""Unit tests for hullq.search.query — SLICE-0033.

Covers:
- AndQuery requires at least one criterion
- and_reduce: any FALSE -> FALSE; all TRUE -> TRUE; otherwise UNKNOWN
- result_class_for mapping (§C primary result boundary semantics)
- evaluate_and_query end-to-end against a SearchableDesignProjection
- JSON round-trip without semantic drift
- fail-closed deserialization for unsupported version/type/malformed input
"""

from __future__ import annotations

import pytest

from hullq.search.criteria import NumericLeafCriterion
from hullq.search.projection import SearchableDesignProjection
from hullq.search.query import (
    AndQuery,
    and_reduce,
    evaluate_and_query,
    query_from_json_dict,
    query_to_json_dict,
    result_class_for,
)
from hullq.search.types import NumericComparisonKind, ResultClass, TruthState, ValueQualification
from hullq.search.values import QualifiedNumericValue

# ---------------------------------------------------------------------------
# AndQuery construction
# ---------------------------------------------------------------------------


def test_and_query_requires_at_least_one_criterion() -> None:
    with pytest.raises(ValueError, match="at least one criterion"):
        AndQuery(criteria=())


# ---------------------------------------------------------------------------
# and_reduce / result_class_for
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("truths", "expected"),
    [
        ((TruthState.TRUE, TruthState.TRUE), TruthState.TRUE),
        ((TruthState.TRUE, TruthState.FALSE), TruthState.FALSE),
        ((TruthState.FALSE, TruthState.UNKNOWN), TruthState.FALSE),
        ((TruthState.TRUE, TruthState.UNKNOWN), TruthState.UNKNOWN),
        ((TruthState.UNKNOWN,), TruthState.UNKNOWN),
    ],
)
def test_and_reduce(truths: tuple[TruthState, ...], expected: TruthState) -> None:
    assert and_reduce(truths) is expected


def test_and_reduce_requires_non_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        and_reduce(())


@pytest.mark.parametrize(
    ("truth", "expected"),
    [
        (TruthState.TRUE, ResultClass.CONFIRMED_MATCH),
        (TruthState.FALSE, ResultClass.CONFIRMED_NON_MATCH),
        (TruthState.UNKNOWN, ResultClass.INSUFFICIENT_DATA),
    ],
)
def test_result_class_for(truth: TruthState, expected: ResultClass) -> None:
    assert result_class_for(truth) is expected


# ---------------------------------------------------------------------------
# evaluate_and_query end-to-end
# ---------------------------------------------------------------------------


def _query() -> AndQuery:
    return AndQuery(
        criteria=(
            NumericLeafCriterion(
                field="loa_m",
                comparison=NumericComparisonKind.RANGE,
                threshold_min=10.0,
                threshold_max=12.5,
            ),
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.8
            ),
        )
    )


def _confirmed(value: float) -> QualifiedNumericValue:
    return QualifiedNumericValue(value=value, qualification=ValueQualification.CONFIRMED)


def test_evaluate_and_query_confirmed_match() -> None:
    projection = SearchableDesignProjection(
        design_id="d1",
        values={"loa_m": _confirmed(11.0), "draft_max_m": _confirmed(1.5)},
        is_fixture=True,
    )
    evaluation = evaluate_and_query(_query(), projection)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert len(evaluation.criterion_evaluations) == 2


def test_evaluate_and_query_confirmed_non_match() -> None:
    projection = SearchableDesignProjection(
        design_id="d2",
        values={"loa_m": _confirmed(20.0), "draft_max_m": _confirmed(1.5)},
        is_fixture=True,
    )
    evaluation = evaluate_and_query(_query(), projection)
    assert evaluation.result_class is ResultClass.CONFIRMED_NON_MATCH


def test_evaluate_and_query_insufficient_data_on_missing_field() -> None:
    projection = SearchableDesignProjection(
        design_id="d3", values={"loa_m": _confirmed(11.0)}, is_fixture=True
    )
    evaluation = evaluate_and_query(_query(), projection)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_query_json_round_trip_without_semantic_drift() -> None:
    original = _query()
    data = query_to_json_dict(original)
    restored = query_from_json_dict(data)
    assert restored == original
    assert query_to_json_dict(restored) == data


def test_query_from_json_dict_rejects_unsupported_schema_version() -> None:
    data = query_to_json_dict(_query())
    data["schema_version"] = "9.9"
    with pytest.raises(ValueError, match="schema_version"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_unsupported_type() -> None:
    data = query_to_json_dict(_query())
    data["type"] = "OR"
    with pytest.raises(ValueError, match="type"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_empty_criteria() -> None:
    data = query_to_json_dict(_query())
    data["criteria"] = []
    with pytest.raises(ValueError, match="non-empty"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_unknown_comparison() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["comparison"] = "APPROXIMATELY"
    with pytest.raises(ValueError):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_missing_criterion_key() -> None:
    data = query_to_json_dict(_query())
    del data["criteria"][0]["threshold_min"]
    with pytest.raises(ValueError, match="Malformed numeric leaf criterion"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_non_string_field() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["field"] = 123
    with pytest.raises(ValueError, match="field must be a string"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_non_numeric_threshold_min() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["threshold_min"] = "ten"
    with pytest.raises(ValueError, match="threshold_min must be a finite, non-bool numeric"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_non_numeric_threshold_max() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["threshold_max"] = "twelve"
    with pytest.raises(ValueError, match="threshold_max must be a finite, non-bool numeric"):
        query_from_json_dict(data)


# ---------------------------------------------------------------------------
# Finding 1 (query boundary) — bool / NaN / Infinity thresholds via JSON tamper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_threshold", [True, False])
def test_query_from_json_dict_rejects_bool_threshold_min(bad_threshold: object) -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["threshold_min"] = bad_threshold
    with pytest.raises(ValueError, match="threshold_min must be a finite, non-bool numeric"):
        query_from_json_dict(data)


@pytest.mark.parametrize("bad_threshold", [True, False])
def test_query_from_json_dict_rejects_bool_threshold_max(bad_threshold: object) -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["threshold_max"] = bad_threshold
    with pytest.raises(ValueError, match="threshold_max must be a finite, non-bool numeric"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_nan_threshold() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["threshold_min"] = float("nan")
    with pytest.raises(ValueError, match="threshold_min must be a finite, non-bool numeric"):
        query_from_json_dict(data)


@pytest.mark.parametrize("infinite", [float("inf"), float("-inf")])
def test_query_from_json_dict_rejects_infinite_threshold(infinite: float) -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["threshold_max"] = infinite
    with pytest.raises(ValueError, match="threshold_max must be a finite, non-bool numeric"):
        query_from_json_dict(data)


# ---------------------------------------------------------------------------
# Finding 3 — unknown-key / malformed-shape tamper tests
# ---------------------------------------------------------------------------


def test_query_from_json_dict_rejects_unknown_top_level_key() -> None:
    data = query_to_json_dict(_query())
    data["extra_field"] = "unexpected"
    with pytest.raises(ValueError, match="Unknown top-level query field"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_unknown_criterion_key_unit() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0]["unit"] = "ft"
    with pytest.raises(ValueError, match="Unknown numeric leaf criterion field"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_non_object_criterion_entry() -> None:
    data = query_to_json_dict(_query())
    data["criteria"][0] = "not-a-criterion-object"
    with pytest.raises(ValueError, match="must be a JSON object"):
        query_from_json_dict(data)


def test_query_from_json_dict_rejects_non_object_top_level_payload() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        query_from_json_dict(["not", "an", "object"])  # type: ignore[arg-type]


def test_query_from_json_dict_unit_is_not_silently_discarded() -> None:
    # The exact adversarial example from the review finding: 40 must never be
    # evaluated under a canonical-unit assumption while "unit": "ft" is dropped.
    data = query_to_json_dict(_query())
    data["criteria"][0] = {
        "field": "loa_m",
        "comparison": "MAXIMUM",
        "threshold_min": None,
        "threshold_max": 40,
        "unit": "ft",
    }
    with pytest.raises(ValueError, match="Unknown numeric leaf criterion field"):
        query_from_json_dict(data)
