"""Numeric MUST leaf criterion and its deterministic evaluation — SLICE-0033.

Implements SEARCH_QUERY_SEMANTICS.v0.1.md §6 (inclusive numeric comparison)
and the slice's Required Behavior §A (numeric leaf truth) over already
canonicalized values. Unit conversion happens upstream of this module —
`NumericLeafCriterion` thresholds and `QualifiedNumericValue.value` MUST
already be in the same canonical unit.

Does not implement: unit conversion, option-sensitive/bounded-value-range
configuration-aware evaluation (§7), PREFER, or OR/NOT aggregation.
`ValueQualification.NOT_APPLICABLE`/`APPLICABILITY_UNKNOWN` are handled here
as generic (non-configuration-scoped) statuses only.
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
from hullq.search.values import QualifiedNumericValue, is_finite_real_number

__all__ = [
    "CriterionEvaluation",
    "NumericLeafCriterion",
    "evaluate_numeric_leaf",
]

# ValueQualification.NOT_APPLICABLE is handled separately in evaluate_numeric_leaf
# (it resolves to FALSE, not UNKNOWN) and is deliberately absent from this map.
_UNQUALIFIED_REASON: dict[ValueQualification, ReasonCode] = {
    ValueQualification.MISSING: ReasonCode.VALUE_MISSING,
    ValueQualification.UNRESOLVED_CONFLICT: ReasonCode.UNRESOLVED_CONFLICT,
    ValueQualification.PROVISIONAL: ReasonCode.PROVISIONAL_VALUE,
    ValueQualification.APPLICABILITY_UNKNOWN: ReasonCode.APPLICABILITY_UNKNOWN,
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
        if not isinstance(self.field, str) or not self.field:
            raise ValueError(
                f"NumericLeafCriterion.field must be a non-empty string; got {self.field!r}"
            )
        if not isinstance(self.comparison, NumericComparisonKind):
            raise ValueError(
                f"NumericLeafCriterion.comparison must be a NumericComparisonKind member; "
                f"got {self.comparison!r}"
            )
        if not isinstance(self.strength, RequirementStrength):
            raise ValueError(
                f"NumericLeafCriterion.strength must be a RequirementStrength member; "
                f"got {self.strength!r}"
            )
        for name, threshold in (
            ("threshold_min", self.threshold_min),
            ("threshold_max", self.threshold_max),
        ):
            if threshold is not None and not is_finite_real_number(threshold):
                raise ValueError(
                    f"NumericLeafCriterion.{name} must be a finite, non-bool numeric value "
                    f"or null; got {threshold!r}"
                )

        # NumericComparisonKind is validated as a genuine enum member above, so this
        # if/elif/else is exhaustive over {MINIMUM, MAXIMUM, RANGE} — no untyped value
        # can silently fall through into RANGE semantics.
        if self.comparison is NumericComparisonKind.MINIMUM:
            if self.threshold_min is None or self.threshold_max is not None:
                raise ValueError("MINIMUM comparison requires threshold_min only")
        elif self.comparison is NumericComparisonKind.MAXIMUM:
            if self.threshold_max is None or self.threshold_min is not None:
                raise ValueError("MAXIMUM comparison requires threshold_max only")
        else:
            if self.threshold_min is None or self.threshold_max is None:
                raise ValueError("RANGE comparison requires both threshold_min and threshold_max")
            if self.threshold_min > self.threshold_max:
                raise ValueError(
                    f"RANGE comparison requires threshold_min <= threshold_max, "
                    f"got {self.threshold_min} > {self.threshold_max}"
                )

        object.__setattr__(
            self, "threshold_min", None if self.threshold_min is None else float(self.threshold_min)
        )
        object.__setattr__(
            self, "threshold_max", None if self.threshold_max is None else float(self.threshold_max)
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

    Fail-closed: any qualification other than `CONFIRMED`/`NOT_APPLICABLE`
    yields UNKNOWN with the matching reason code, never FALSE or TRUE
    (SEARCH_QUERY_SEMANTICS.v0.1.md §3, slice Required Behavior §A).
    `NOT_APPLICABLE` is the one qualification that resolves directly to
    FALSE — confirmed exclusion, not insufficient data
    (SEARCH_QUERY_SEMANTICS.v0.1.md §2) — without comparing any numeric
    value, since `QualifiedNumericValue` never carries one for this
    qualification.
    """
    if qualified_value.qualification is ValueQualification.NOT_APPLICABLE:
        return CriterionEvaluation(
            field=criterion.field,
            truth=TruthState.FALSE,
            reason=ReasonCode.NOT_APPLICABLE,
            explanation=(
                f"{criterion.field}: criterion is not applicable to this design "
                f"(confirmed exclusion, not insufficient data)"
            ),
        )

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
