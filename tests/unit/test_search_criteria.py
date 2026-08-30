"""Unit tests for hullq.search.criteria — SLICE-0033 (+ REVIEW amendment, + SLICE-0035).

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
- SLICE-0035: CategoricalLeafCriterion construction validation and exact
  canonical-string equality truth, mirroring the numeric leaf's fail-closed
  qualification handling and NOT_APPLICABLE/negation-loophole guarantees
- SLICE-0035 REVIEW amendment Finding 1: reserved categorical semantic
  sentinels ("unknown"/"not_applicable") routed through the real
  from_resolution_state_categorical adapter can never produce TRUE/FALSE via
  ordinary equality at leaf-evaluation granularity
"""

from __future__ import annotations

import pytest

from hullq.domain.provenance import ResolutionState
from hullq.search.criteria import (
    CategoricalLeafCriterion,
    NumericLeafCriterion,
    evaluate_categorical_leaf,
    evaluate_numeric_leaf,
)
from hullq.search.types import (
    NumericComparisonKind,
    ReasonCode,
    RequirementStrength,
    TruthState,
    ValueQualification,
)
from hullq.search.values import (
    QualifiedCategoricalValue,
    QualifiedNumericValue,
    from_resolution_state_categorical,
)

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


# ---------------------------------------------------------------------------
# SLICE-0035 — CategoricalLeafCriterion construction validation
# ---------------------------------------------------------------------------


def test_categorical_field_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="field"):
        CategoricalLeafCriterion(field="", equals="masthead")


def test_categorical_equals_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="equals"):
        CategoricalLeafCriterion(field="rig.masthead_fractional", equals="")


def test_categorical_equals_must_be_a_string() -> None:
    with pytest.raises(ValueError, match="equals"):
        CategoricalLeafCriterion(field="rig.masthead_fractional", equals=1)  # type: ignore[arg-type]


def test_categorical_strength_must_be_a_requirement_strength_member() -> None:
    with pytest.raises(ValueError, match="RequirementStrength member"):
        CategoricalLeafCriterion(
            field="rig.masthead_fractional",
            equals="masthead",
            strength="PREFER",  # type: ignore[arg-type]
        )


def test_categorical_explicit_must_strength_is_accepted() -> None:
    criterion = CategoricalLeafCriterion(
        field="rig.masthead_fractional", equals="masthead", strength=RequirementStrength.MUST
    )
    assert criterion.strength is RequirementStrength.MUST


# ---------------------------------------------------------------------------
# SLICE-0035 — exact canonical-string equality truth
# ---------------------------------------------------------------------------


def _confirmed_categorical(value: str) -> QualifiedCategoricalValue:
    return QualifiedCategoricalValue(value=value, qualification=ValueQualification.CONFIRMED)


def test_categorical_exact_equality_is_true() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead")
    result = evaluate_categorical_leaf(criterion, _confirmed_categorical("masthead"))
    assert result.truth is TruthState.TRUE
    assert result.reason is None


def test_categorical_inequality_is_false() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead")
    result = evaluate_categorical_leaf(criterion, _confirmed_categorical("fractional"))
    assert result.truth is TruthState.FALSE
    assert result.reason is None


def test_categorical_comparison_is_case_sensitive_no_fuzzy_matching() -> None:
    # slice Required Behavior §A: "no fuzzy synonym matching at evaluator
    # time; no case-folding/normalization hidden inside truth evaluation".
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead")
    result = evaluate_categorical_leaf(criterion, _confirmed_categorical("Masthead"))
    assert result.truth is TruthState.FALSE


@pytest.mark.parametrize(
    ("qualification", "expected_reason"),
    [
        (ValueQualification.MISSING, ReasonCode.VALUE_MISSING),
        (ValueQualification.UNRESOLVED_CONFLICT, ReasonCode.UNRESOLVED_CONFLICT),
        (ValueQualification.PROVISIONAL, ReasonCode.PROVISIONAL_VALUE),
        (ValueQualification.APPLICABILITY_UNKNOWN, ReasonCode.APPLICABILITY_UNKNOWN),
    ],
)
def test_categorical_unqualified_value_yields_unknown_never_true_or_false(
    qualification: ValueQualification, expected_reason: ReasonCode
) -> None:
    criterion = CategoricalLeafCriterion(field="deck.cockpit_position", equals="aft")
    qv = QualifiedCategoricalValue(value=None, qualification=qualification)
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is TruthState.UNKNOWN
    assert result.reason is expected_reason


def test_categorical_not_applicable_yields_false_not_unknown() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead")
    qv = QualifiedCategoricalValue(value=None, qualification=ValueQualification.NOT_APPLICABLE)
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is TruthState.FALSE
    assert result.reason is ReasonCode.NOT_APPLICABLE


def test_categorical_not_applicable_never_becomes_true_through_comparison() -> None:
    # Adversarial checklist Q4: NOT_APPLICABLE must never become TRUE through
    # a comparison loophole, e.g. comparing against the literal string
    # "not_applicable" as if it were a legitimate canonical rig value.
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="not_applicable")
    qv = QualifiedCategoricalValue(value=None, qualification=ValueQualification.NOT_APPLICABLE)
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is TruthState.FALSE
    assert result.reason is ReasonCode.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# REVIEW amendment Finding 1 — reserved sentinels through the real adapter,
# end-to-end at leaf-evaluation granularity
# ---------------------------------------------------------------------------


def test_categorical_unknown_sentinel_via_adapter_never_true() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="unknown")
    qv = from_resolution_state_categorical(ResolutionState.RESOLVED, "unknown")
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is not TruthState.TRUE


def test_categorical_unknown_sentinel_via_adapter_never_false() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead")
    qv = from_resolution_state_categorical(ResolutionState.RESOLVED, "unknown")
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is TruthState.UNKNOWN
    assert result.reason is ReasonCode.VALUE_MISSING


def test_categorical_not_applicable_sentinel_via_adapter_follows_not_applicable_path() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead")
    qv = from_resolution_state_categorical(ResolutionState.RESOLVED, "not_applicable")
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is TruthState.FALSE
    assert result.reason is ReasonCode.NOT_APPLICABLE


def test_categorical_not_applicable_sentinel_via_adapter_never_equality_matches() -> None:
    criterion = CategoricalLeafCriterion(field="rig.masthead_fractional", equals="not_applicable")
    qv = from_resolution_state_categorical(ResolutionState.RESOLVED, "not_applicable")
    result = evaluate_categorical_leaf(criterion, qv)
    assert result.truth is TruthState.FALSE
