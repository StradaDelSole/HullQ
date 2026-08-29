"""Unit tests for hullq.search.values — SLICE-0033.

Covers:
- QualifiedNumericValue's CONFIRMED<->value invariant (both directions)
- FieldResolution.state -> ValueQualification adapter, every enum member
- MetricStatus -> ValueQualification adapter, every enum member
- non-CONFIRMED adapter outputs never carry the original value
"""

from __future__ import annotations

import pytest

from hullq.domain.derived_metrics import MetricStatus
from hullq.domain.provenance import ResolutionState
from hullq.search.types import ValueQualification
from hullq.search.values import (
    QualifiedNumericValue,
    from_derived_metric_status,
    from_resolution_state,
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
    ],
)
def test_non_confirmed_must_not_carry_value(qualification: ValueQualification) -> None:
    with pytest.raises(ValueError, match="must not carry a value"):
        QualifiedNumericValue(value=1.0, qualification=qualification)


def test_confirmed_with_value_is_valid() -> None:
    qv = QualifiedNumericValue(value=11.2, qualification=ValueQualification.CONFIRMED)
    assert qv.value == 11.2


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


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (MetricStatus.COMPUTED, ValueQualification.CONFIRMED),
        (MetricStatus.COMPUTED_PROVISIONAL, ValueQualification.PROVISIONAL),
        (MetricStatus.MISSING_INPUT, ValueQualification.MISSING),
        (MetricStatus.UNRESOLVED_INPUT, ValueQualification.UNRESOLVED_CONFLICT),
        (MetricStatus.INVALID_INPUT, ValueQualification.MISSING),
        (MetricStatus.NOT_APPLICABLE, ValueQualification.MISSING),
        (MetricStatus.APPLICABILITY_UNKNOWN, ValueQualification.MISSING),
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
