"""Numeric MUST leaf criterion and its deterministic evaluation — SLICE-0033.

Implements SEARCH_QUERY_SEMANTICS.v0.1.md §6 (inclusive numeric comparison)
and the slice's Required Behavior §A (numeric leaf truth) over already
canonicalized values. Unit conversion happens upstream of this module —
`NumericLeafCriterion` thresholds and `QualifiedNumericValue.value` MUST
already be in the same canonical unit.

Does not implement: unit conversion, configuration-aware/bounded-value-range
evaluation (§7), PREFER, or OR/NOT aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass

from hullq.search.types import (
    NumericComparisonKind,
    ReasonCode,
    RequirementStrength,
    TruthState,
    ValueQualification,
)
from hullq.search.values import QualifiedNumericValue

__all__ = [
    "CriterionEvaluation",
    "NumericLeafCriterion",
    "evaluate_numeric_leaf",
]

_UNQUALIFIED_REASON: dict[ValueQualification, ReasonCode] = {
    ValueQualification.MISSING: ReasonCode.VALUE_MISSING,
    ValueQualification.UNRESOLVED_CONFLICT: ReasonCode.UNRESOLVED_CONFLICT,
    ValueQualification.PROVISIONAL: ReasonCode.PROVISIONAL_VALUE,
}


@dataclass(frozen=True, slots=True)
class NumericLeafCriterion:
    """One serializable numeric MUST criterion over a named projection field.

    `field` addresses a key in the `SearchableDesignProjection` the criterion
    is evaluated against (see `hullq.search.projection`); it is opaque to
    this module. Thresholds are inclusive by boundary
    (SEARCH_QUERY_SEMANTICS.v0.1.md §6): minimum => value >= threshold,
    maximum => value <= threshold, range => threshold_min <= value <= threshold_max.
    """

    field: str
    comparison: NumericComparisonKind
    threshold_min: float | None = None
    threshold_max: float | None = None
    strength: RequirementStrength = RequirementStrength.MUST

    def __post_init__(self) -> None:
        if not self.field:
            raise ValueError("NumericLeafCriterion.field must be non-empty")
        if self.comparison is NumericComparisonKind.MINIMUM:
            if self.threshold_min is None or self.threshold_max is not None:
                raise ValueError("MINIMUM comparison requires threshold_min only")
        elif self.comparison is NumericComparisonKind.MAXIMUM:
            if self.threshold_max is None or self.threshold_min is not None:
                raise ValueError("MAXIMUM comparison requires threshold_max only")
        elif self.comparison is NumericComparisonKind.RANGE:
            if self.threshold_min is None or self.threshold_max is None:
                raise ValueError("RANGE comparison requires both threshold_min and threshold_max")
            if self.threshold_min > self.threshold_max:
                raise ValueError(
                    f"RANGE comparison requires threshold_min <= threshold_max, "
                    f"got {self.threshold_min} > {self.threshold_max}"
                )


@dataclass(frozen=True, slots=True)
class CriterionEvaluation:
    """Criterion-level truth/reason/explanation for one evaluated design."""

    field: str
    truth: TruthState
    reason: ReasonCode | None
    explanation: str


def _compare(
    comparison: NumericComparisonKind, value: float, criterion: NumericLeafCriterion
) -> bool:
    # threshold presence per comparison kind is enforced by NumericLeafCriterion.__post_init__
    if comparison is NumericComparisonKind.MINIMUM:
        assert criterion.threshold_min is not None
        return value >= criterion.threshold_min
    if comparison is NumericComparisonKind.MAXIMUM:
        assert criterion.threshold_max is not None
        return value <= criterion.threshold_max
    assert criterion.threshold_min is not None
    assert criterion.threshold_max is not None
    return criterion.threshold_min <= value <= criterion.threshold_max


def evaluate_numeric_leaf(
    criterion: NumericLeafCriterion, qualified_value: QualifiedNumericValue
) -> CriterionEvaluation:
    """Evaluate one numeric MUST leaf against one qualified candidate value.

    Fail-closed: any qualification other than `CONFIRMED` yields UNKNOWN with
    the matching reason code, never FALSE or TRUE
    (SEARCH_QUERY_SEMANTICS.v0.1.md §3, slice Required Behavior §A).
    """
    if qualified_value.qualification is not ValueQualification.CONFIRMED:
        reason = _UNQUALIFIED_REASON[qualified_value.qualification]
        return CriterionEvaluation(
            field=criterion.field,
            truth=TruthState.UNKNOWN,
            reason=reason,
            explanation=(
                f"{criterion.field}: value is not qualified for confirmed truth "
                f"({qualified_value.qualification.value})"
            ),
        )

    value = qualified_value.value
    assert value is not None  # enforced by QualifiedNumericValue invariant
    passes = _compare(criterion.comparison, value, criterion)
    truth = TruthState.TRUE if passes else TruthState.FALSE
    explanation = (
        f"{criterion.field}={value} {'satisfies' if passes else 'contradicts'} "
        f"{criterion.comparison.value} "
        f"(min={criterion.threshold_min}, max={criterion.threshold_max})"
    )
    return CriterionEvaluation(
        field=criterion.field, truth=truth, reason=None, explanation=explanation
    )
