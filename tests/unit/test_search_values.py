"""Unit tests for hullq.search.values — SLICE-0033 (+ REVIEW amendment, + SLICE-0035).

Covers:
- QualifiedNumericValue's CONFIRMED<->value invariant (both directions)
- FieldResolution.state -> ValueQualification adapter, every enum member
- MetricStatus -> ValueQualification adapter, every enum member, including the
  accepted NOT_APPLICABLE/APPLICABILITY_UNKNOWN semantics (review Finding 2)
- non-CONFIRMED adapter outputs never carry the original value
- is_finite_real_number / CONFIRMED structural fail-closed hardening against
  bool, NaN, +/-Infinity and non-numeric candidate values (review Finding 1)
- SLICE-0035: QualifiedCategoricalValue's CONFIRMED<->value invariant and
  from_resolution_state_categorical adapter
"""

from __future__ import annotations

import math

import pytest

from hullq.domain.derived_metrics import MetricStatus
from hullq.domain.provenance import ResolutionState
from hullq.search.types import ValueQualification
from hullq.search.values import (
    QualifiedCategoricalValue,
    QualifiedNumericValue,
    from_derived_metric_status,
    from_resolution_state,
    from_resolution_state_categorical,
    is_finite_real_number,
)


def test_confirmed_requires_value() -> None:
    with pytest.raises(ValueError, match="CONFIRMED"):
        QualifiedNumericValue(value=None, qualification=ValueQualification.CONFIRMED)


@pytest.mark.parametrize(
    "qualification",
    [
        ValueQualification.MISSING,
        ValueQualification.UNRESOLVED_CONFLICT,
        ValueQualification.PROVISIONAL,
        ValueQualification.APPLICABILITY_UNKNOWN,
        ValueQualification.NOT_APPLICABLE,
    ],
)
def test_non_confirmed_must_not_carry_value(qualification: ValueQualification) -> None:
    with pytest.raises(ValueError, match="must not carry a value"):
        QualifiedNumericValue(value=1.0, qualification=qualification)


def test_confirmed_with_value_is_valid() -> None:
    qv = QualifiedNumericValue(value=11.2, qualification=ValueQualification.CONFIRMED)
    assert qv.value == 11.2


def test_confirmed_normalizes_int_to_float() -> None:
    qv = QualifiedNumericValue(value=11, qualification=ValueQualification.CONFIRMED)
    assert qv.value == 11.0
    assert isinstance(qv.value, float)


# ---------------------------------------------------------------------------
# Finding 1 — structural fail-closed numeric hardening
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [True, False, "11.2", float("nan"), float("inf"), float("-inf"), None, object()],
)
def test_is_finite_real_number_rejects_malformed(value: object) -> None:
    assert is_finite_real_number(value) is False


@pytest.mark.parametrize("value", [0, 1, -1, 0.0, 11.2, -11.2])
def test_is_finite_real_number_accepts_finite_non_bool_numbers(value: object) -> None:
    assert is_finite_real_number(value) is True


@pytest.mark.parametrize("bad_value", [True, False])
def test_confirmed_rejects_bool(bad_value: object) -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        QualifiedNumericValue(value=bad_value, qualification=ValueQualification.CONFIRMED)  # type: ignore[arg-type]


def test_confirmed_rejects_nan() -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        QualifiedNumericValue(value=float("nan"), qualification=ValueQualification.CONFIRMED)


@pytest.mark.parametrize("infinite", [float("inf"), float("-inf")])
def test_confirmed_rejects_infinity(infinite: float) -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        QualifiedNumericValue(value=infinite, qualification=ValueQualification.CONFIRMED)


def test_confirmed_rejects_non_numeric_string() -> None:
    with pytest.raises(ValueError, match="finite, non-bool numeric value"):
        QualifiedNumericValue(value="11.2", qualification=ValueQualification.CONFIRMED)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FieldResolution.state adapter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (ResolutionState.RESOLVED, ValueQualification.CONFIRMED),
        (ResolutionState.RESOLVED_WITH_CONFLICT, ValueQualification.CONFIRMED),
        (ResolutionState.UNKNOWN, ValueQualification.MISSING),
        (ResolutionState.NEEDS_REVIEW, ValueQualification.MISSING),
        (ResolutionState.CONFLICT, ValueQualification.UNRESOLVED_CONFLICT),
    ],
)
def test_from_resolution_state_maps_every_member(
    state: ResolutionState, expected: ValueQualification
) -> None:
    qv = from_resolution_state(state, 5.0)
    assert qv.qualification is expected
    if expected is ValueQualification.CONFIRMED:
        assert qv.value == 5.0
    else:
        assert qv.value is None


def test_from_resolution_state_covers_all_enum_members() -> None:
    confirmed_states = {ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT}
    for state in ResolutionState:
        from_resolution_state(state, 1.0 if state in confirmed_states else None)


# ---------------------------------------------------------------------------
# MetricStatus adapter, including Finding 2 applicability semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (MetricStatus.COMPUTED, ValueQualification.CONFIRMED),
        (MetricStatus.COMPUTED_PROVISIONAL, ValueQualification.PROVISIONAL),
        (MetricStatus.MISSING_INPUT, ValueQualification.MISSING),
        (MetricStatus.UNRESOLVED_INPUT, ValueQualification.UNRESOLVED_CONFLICT),
        (MetricStatus.INVALID_INPUT, ValueQualification.MISSING),
        (MetricStatus.NOT_APPLICABLE, ValueQualification.NOT_APPLICABLE),
        (MetricStatus.APPLICABILITY_UNKNOWN, ValueQualification.APPLICABILITY_UNKNOWN),
        (MetricStatus.NONSTANDARD_INPUT, ValueQualification.MISSING),
    ],
)
def test_from_derived_metric_status_maps_every_member(
    status: MetricStatus, expected: ValueQualification
) -> None:
    qv = from_derived_metric_status(status, 3.9)
    assert qv.qualification is expected
    if expected is ValueQualification.CONFIRMED:
        assert qv.value == 3.9
    else:
        assert qv.value is None


def test_from_derived_metric_status_covers_all_enum_members() -> None:
    for status in MetricStatus:
        from_derived_metric_status(status, None if status != MetricStatus.COMPUTED else 1.0)


def test_computed_provisional_never_yields_confirmed() -> None:
    qv = from_derived_metric_status(MetricStatus.COMPUTED_PROVISIONAL, 42.0)
    assert qv.qualification is not ValueQualification.CONFIRMED
    assert qv.value is None


def test_not_applicable_is_distinct_from_missing() -> None:
    qv = from_derived_metric_status(MetricStatus.NOT_APPLICABLE, 42.0)
    assert qv.qualification is ValueQualification.NOT_APPLICABLE
    assert qv.qualification is not ValueQualification.MISSING
    assert qv.value is None


def test_applicability_unknown_is_distinct_from_missing() -> None:
    qv = from_derived_metric_status(MetricStatus.APPLICABILITY_UNKNOWN, 42.0)
    assert qv.qualification is ValueQualification.APPLICABILITY_UNKNOWN
    assert qv.qualification is not ValueQualification.MISSING
    assert qv.value is None


def test_is_finite_real_number_used_consistently_with_math_isfinite() -> None:
    # Sanity cross-check against the stdlib primitive this helper wraps.
    for candidate in (0, 1.5, -1.5, float("nan"), float("inf"), float("-inf")):
        assert is_finite_real_number(candidate) == (
            isinstance(candidate, (int, float))
            and not isinstance(candidate, bool)
            and math.isfinite(candidate)
        )


# ---------------------------------------------------------------------------
# SLICE-0035 — QualifiedCategoricalValue
# ---------------------------------------------------------------------------


def test_categorical_confirmed_requires_value() -> None:
    with pytest.raises(ValueError, match="CONFIRMED"):
        QualifiedCategoricalValue(value=None, qualification=ValueQualification.CONFIRMED)


@pytest.mark.parametrize(
    "qualification",
    [
        ValueQualification.MISSING,
        ValueQualification.UNRESOLVED_CONFLICT,
        ValueQualification.PROVISIONAL,
        ValueQualification.APPLICABILITY_UNKNOWN,
        ValueQualification.NOT_APPLICABLE,
    ],
)
def test_categorical_non_confirmed_must_not_carry_value(
    qualification: ValueQualification,
) -> None:
    with pytest.raises(ValueError, match="must not carry a value"):
        QualifiedCategoricalValue(value="masthead", qualification=qualification)


def test_categorical_confirmed_with_value_is_valid() -> None:
    qv = QualifiedCategoricalValue(value="masthead", qualification=ValueQualification.CONFIRMED)
    assert qv.value == "masthead"


def test_categorical_confirmed_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        QualifiedCategoricalValue(value=1, qualification=ValueQualification.CONFIRMED)  # type: ignore[arg-type]


def test_categorical_confirmed_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        QualifiedCategoricalValue(value="", qualification=ValueQualification.CONFIRMED)


def test_categorical_confirmed_rejects_whitespace_only_string() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        QualifiedCategoricalValue(value="   ", qualification=ValueQualification.CONFIRMED)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (ResolutionState.RESOLVED, ValueQualification.CONFIRMED),
        (ResolutionState.RESOLVED_WITH_CONFLICT, ValueQualification.CONFIRMED),
        (ResolutionState.UNKNOWN, ValueQualification.MISSING),
        (ResolutionState.NEEDS_REVIEW, ValueQualification.MISSING),
        (ResolutionState.CONFLICT, ValueQualification.UNRESOLVED_CONFLICT),
    ],
)
def test_from_resolution_state_categorical_maps_every_member(
    state: ResolutionState, expected: ValueQualification
) -> None:
    qv = from_resolution_state_categorical(state, "aft")
    assert qv.qualification is expected
    if expected is ValueQualification.CONFIRMED:
        assert qv.value == "aft"
    else:
        assert qv.value is None


def test_from_resolution_state_categorical_covers_all_enum_members() -> None:
    confirmed_states = {ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT}
    for state in ResolutionState:
        from_resolution_state_categorical(state, "fin" if state in confirmed_states else None)
