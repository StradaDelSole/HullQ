"""Unit tests for hullq.search.criteria — SLICE-0033 (+ REVIEW amendment).

Covers:
- NumericLeafCriterion construction validation (comparison/threshold shape)
- inclusive minimum/maximum/range boundary truth (equality passes)
- contradiction returns FALSE
- every non-CONFIRMED, non-NOT_APPLICABLE qualification returns UNKNOWN with
  the matching reason
- NOT_APPLICABLE returns FALSE (confirmed exclusion) without a value
  (review Finding 2)
- UNKNOWN is never coerced to TRUE or FALSE
- structural fail-closed hardening: bool/non-finite thresholds and
  invalid comparison/strength values are rejected at construction, never
  silently falling into RANGE semantics or reaching comparison logic
  (review Finding 1)
"""

from __future__ import annotations

import pytest

from hullq.search.criteria import NumericLeafCriterion, evaluate_numeric_leaf
from hullq.search.types import (
    NumericComparisonKind,
    ReasonCode,
    RequirementStrength,
    TruthState,
    ValueQualification,
)
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


def test_field_must_be_a_string() -> None:
    with pytest.raises(ValueError, match="field"):
        NumericLeafCriterion(
            field=123,  # type: ignore[arg-type]
            comparison=NumericComparisonKind.MINIMUM,
            threshold_min=1.0,
        )


# ---------------------------------------------------------------------------
# Finding 1 — structural fail-closed numeric hardening (direct construction)
# ---------------------------------------------------------------------------


def test_comparison_must_be_a_numeric_comparison_kind_member() -> None:
    with pytest.raises(ValueError, match="NumericComparisonKind member"):
        NumericLeafCriterion(
            field="loa_m",
            comparison="RANGE",  # type: ignore[arg-type]
            threshold_min=1.0,
            threshold_max=2.0,
        )


def test_invalid_comparison_does_not_silently_fall_into_range_semantics() -> None:
    # A bogus comparison value must be rejected outright, not treated as RANGE
    # merely because it fails the MINIMUM/MAXIMUM identity checks.
    with pytest.raises(ValueError, match="NumericComparisonKind member"):
        NumericLeafCriterion(
            field="loa_m",
            comparison="APPROXIMATELY",  # type: ignore[arg-type]
            threshold_min=1.0,
        )


def test_strength_must_be_a_requirement_strength_member() -> None:
    with pytest.raises(ValueError, match="RequirementStrength member"):
        NumericLeafCriterion(
            field="loa_m",
            comparison=NumericComparisonKind.MINIMUM,
            threshold_min=1.0,
            strength="PREFER",  # type: ignore[arg-type]
        )


def test_explicit_must_strength_is_accepted() -> None:
    criterion = NumericLeafCriterion(
        field="loa_m",
        comparison=NumericComparisonKind.MINIMUM,
        threshold_min=1.0,
        strength=RequirementStrength.MUST,
    )
    assert criterion.strength is RequirementStrength.MUST


@pytest.mark.parametrize("bad_threshold", [True, False])
def test_threshold_min_rejects_bool(bad_threshold: object) -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="loa_m",
            comparison=NumericComparisonKind.MINIMUM,
            threshold_min=bad_threshold,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_threshold", [True, False])
def test_threshold_max_rejects_bool(bad_threshold: object) -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="draft_max_m",
            comparison=NumericComparisonKind.MAXIMUM,
            threshold_max=bad_threshold,  # type: ignore[arg-type]
        )


def test_threshold_rejects_nan() -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="loa_m",
            comparison=NumericComparisonKind.MINIMUM,
            threshold_min=float("nan"),
        )


@pytest.mark.parametrize("infinite", [float("inf"), float("-inf")])
def test_threshold_rejects_infinity(infinite: float) -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="loa_m", comparison=NumericComparisonKind.MINIMUM, threshold_min=infinite
        )


def test_threshold_rejects_non_numeric_string() -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="loa_m",
            comparison=NumericComparisonKind.MINIMUM,
            threshold_min="ten",  # type: ignore[arg-type]
        )


def test_range_threshold_min_rejects_nan_before_ordering_check() -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="beam_m",
            comparison=NumericComparisonKind.RANGE,
            threshold_min=float("nan"),
            threshold_max=4.2,
        )


def test_range_threshold_max_rejects_infinity() -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        NumericLeafCriterion(
            field="beam_m",
            comparison=NumericComparisonKind.RANGE,
            threshold_min=3.5,
            threshold_max=float("inf"),
        )


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
        (ValueQualification.APPLICABILITY_UNKNOWN, ReasonCode.APPLICABILITY_UNKNOWN),
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


# ---------------------------------------------------------------------------
# Finding 2 — NOT_APPLICABLE is confirmed exclusion (FALSE), not UNKNOWN
# ---------------------------------------------------------------------------


def test_not_applicable_yields_false_not_unknown() -> None:
    criterion = NumericLeafCriterion(
        field="ballast_displ_pct", comparison=NumericComparisonKind.MINIMUM, threshold_min=30.0
    )
    qv = QualifiedNumericValue(value=None, qualification=ValueQualification.NOT_APPLICABLE)
    result = evaluate_numeric_leaf(criterion, qv)
    assert result.truth is TruthState.FALSE
    assert result.reason is ReasonCode.NOT_APPLICABLE


def test_not_applicable_never_returned_as_value_missing() -> None:
    criterion = NumericLeafCriterion(
        field="ballast_displ_pct", comparison=NumericComparisonKind.MINIMUM, threshold_min=30.0
    )
    qv = QualifiedNumericValue(value=None, qualification=ValueQualification.NOT_APPLICABLE)
    result = evaluate_numeric_leaf(criterion, qv)
    assert result.reason is not ReasonCode.VALUE_MISSING
    assert result.truth is not TruthState.UNKNOWN


def test_applicability_unknown_never_returned_as_value_missing() -> None:
    criterion = NumericLeafCriterion(
        field="ballast_displ_pct", comparison=NumericComparisonKind.MINIMUM, threshold_min=30.0
    )
    qv = QualifiedNumericValue(value=None, qualification=ValueQualification.APPLICABILITY_UNKNOWN)
    result = evaluate_numeric_leaf(criterion, qv)
    assert result.reason is not ReasonCode.VALUE_MISSING
    assert result.reason is ReasonCode.APPLICABILITY_UNKNOWN
    assert result.truth is TruthState.UNKNOWN
