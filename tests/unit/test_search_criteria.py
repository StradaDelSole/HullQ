"""Unit tests for hullq.search.criteria — SLICE-0033.

Covers:
- NumericLeafCriterion construction validation (comparison/threshold shape)
- inclusive minimum/maximum/range boundary truth (equality passes)
- contradiction returns FALSE
- every non-CONFIRMED qualification returns UNKNOWN with the matching reason
- UNKNOWN is never coerced to TRUE or FALSE
"""

from __future__ import annotations

import pytest

from hullq.search.criteria import NumericLeafCriterion, evaluate_numeric_leaf
from hullq.search.types import NumericComparisonKind, ReasonCode, TruthState, ValueQualification
from hullq.search.values import QualifiedNumericValue

# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_minimum_requires_threshold_min_only() -> None:
    with pytest.raises(ValueError, match="MINIMUM"):
        NumericLeafCriterion(field="loa_m", comparison=NumericComparisonKind.MINIMUM)
    with pytest.raises(ValueError, match="MINIMUM"):
        NumericLeafCriterion(
            field="loa_m",
            comparison=NumericComparisonKind.MINIMUM,
            threshold_min=1.0,
            threshold_max=2.0,
        )


def test_maximum_requires_threshold_max_only() -> None:
    with pytest.raises(ValueError, match="MAXIMUM"):
        NumericLeafCriterion(field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM)


def test_range_requires_both_thresholds_ordered() -> None:
    with pytest.raises(ValueError, match="RANGE"):
        NumericLeafCriterion(
            field="beam_m", comparison=NumericComparisonKind.RANGE, threshold_min=1.0
        )
    with pytest.raises(ValueError, match="threshold_min <= threshold_max"):
        NumericLeafCriterion(
            field="beam_m",
            comparison=NumericComparisonKind.RANGE,
            threshold_min=5.0,
            threshold_max=1.0,
        )


def test_field_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="field"):
        NumericLeafCriterion(field="", comparison=NumericComparisonKind.MINIMUM, threshold_min=1.0)


# ---------------------------------------------------------------------------
# Inclusive boundary truth
# ---------------------------------------------------------------------------


def _confirmed(value: float) -> QualifiedNumericValue:
    return QualifiedNumericValue(value=value, qualification=ValueQualification.CONFIRMED)


@pytest.mark.parametrize(
    ("value", "expected"), [(10.0, TruthState.TRUE), (9.999, TruthState.FALSE)]
)
def test_minimum_inclusive_boundary(value: float, expected: TruthState) -> None:
    criterion = NumericLeafCriterion(
        field="loa_m", comparison=NumericComparisonKind.MINIMUM, threshold_min=10.0
    )
    result = evaluate_numeric_leaf(criterion, _confirmed(value))
    assert result.truth is expected
    assert result.reason is None


@pytest.mark.parametrize(("value", "expected"), [(1.8, TruthState.TRUE), (1.801, TruthState.FALSE)])
def test_maximum_inclusive_boundary(value: float, expected: TruthState) -> None:
    criterion = NumericLeafCriterion(
        field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.8
    )
    result = evaluate_numeric_leaf(criterion, _confirmed(value))
    assert result.truth is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (3.5, TruthState.TRUE),  # lower boundary
        (4.2, TruthState.TRUE),  # upper boundary
        (3.9, TruthState.TRUE),  # interior
        (3.49, TruthState.FALSE),
        (4.21, TruthState.FALSE),
    ],
)
def test_range_inclusive_boundaries(value: float, expected: TruthState) -> None:
    criterion = NumericLeafCriterion(
        field="beam_m", comparison=NumericComparisonKind.RANGE, threshold_min=3.5, threshold_max=4.2
    )
    result = evaluate_numeric_leaf(criterion, _confirmed(value))
    assert result.truth is expected


# ---------------------------------------------------------------------------
# Fail-closed qualification handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("qualification", "expected_reason"),
    [
        (ValueQualification.MISSING, ReasonCode.VALUE_MISSING),
        (ValueQualification.UNRESOLVED_CONFLICT, ReasonCode.UNRESOLVED_CONFLICT),
        (ValueQualification.PROVISIONAL, ReasonCode.PROVISIONAL_VALUE),
    ],
)
def test_unqualified_value_yields_unknown_never_true_or_false(
    qualification: ValueQualification, expected_reason: ReasonCode
) -> None:
    criterion = NumericLeafCriterion(
        field="loa_m", comparison=NumericComparisonKind.MINIMUM, threshold_min=10.0
    )
    qv = QualifiedNumericValue(value=None, qualification=qualification)
    result = evaluate_numeric_leaf(criterion, qv)
    assert result.truth is TruthState.UNKNOWN
    assert result.reason is expected_reason
