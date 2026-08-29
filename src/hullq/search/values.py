"""Fail-closed value qualification — SLICE-0033.

`QualifiedNumericValue` is the persistence-neutral unit the search kernel
compares against thresholds. It never carries a usable value unless the
originating canonical resolution or derived-metric computation was fully
qualified, per `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` §3.

The adapters below translate the two accepted existing status vocabularies
(`hullq.domain.provenance.ResolutionState` for canonical BoatDesign fields
and `hullq.domain.derived_metrics.MetricStatus` for derived metrics) into the
search kernel's own `ValueQualification`, so evaluation code never has to
reason about raw FieldResolution/FieldEvidence/MetricResult shapes directly.

Does not implement: option-sensitive/ResolvedConfiguration-scoped
qualification — that belongs to REQ-SEARCH-006 and is explicitly out of
scope for this slice. `NOT_APPLICABLE`/`APPLICABILITY_UNKNOWN` ARE
implemented here as generic (non-configuration-scoped) statuses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from hullq.domain.derived_metrics import MetricStatus
from hullq.domain.provenance import ResolutionState
from hullq.search.types import ValueQualification

__all__ = [
    "QualifiedNumericValue",
    "from_derived_metric_status",
    "from_resolution_state",
    "is_finite_real_number",
]


def is_finite_real_number(value: object) -> bool:
    """True iff *value* is a finite, non-bool `int`/`float`.

    The single shared guard used everywhere a numeric candidate value or
    threshold enters this package: `bool` is a subclass of `int` in Python
    and would otherwise silently pass an `isinstance(x, (int, float))`
    check, and `NaN`/`+Infinity`/`-Infinity` are valid `float` values that
    would otherwise reach comparison logic and produce a bogus TRUE/FALSE.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True, slots=True)
class QualifiedNumericValue:
    """A candidate numeric value paired with its fail-closed qualification.

    Invariant: `value` is non-`None` if and only if `qualification` is
    `ValueQualification.CONFIRMED`, and a `CONFIRMED` value MUST be a finite,
    non-bool real number (see `is_finite_real_number`) — never `bool`,
    `NaN`, `+Infinity` or `-Infinity`. Constructing any other combination
    raises `ValueError` — this is the single choke point that keeps missing,
    provisional, unresolved-conflict, not-applicable, applicability-unknown
    and malformed numeric values from silently reaching comparison logic.

    A `CONFIRMED` `int` value is normalized to `float` on construction.
    """

    value: float | None
    qualification: ValueQualification

    def __post_init__(self) -> None:
        is_confirmed = self.qualification is ValueQualification.CONFIRMED
        if is_confirmed:
            if not is_finite_real_number(self.value):
                raise ValueError(
                    f"CONFIRMED qualification requires a finite, non-bool numeric value; "
                    f"got {self.value!r}"
                )
            object.__setattr__(self, "value", float(self.value))  # type: ignore[arg-type]
        elif self.value is not None:
            raise ValueError(
                f"Non-CONFIRMED qualification {self.qualification!r} must not carry a value"
            )


# ---------------------------------------------------------------------------
# FieldResolution.state adapter — canonical BoatDesign baseline fields
# ---------------------------------------------------------------------------

_RESOLUTION_STATE_QUALIFICATION: Final[dict[ResolutionState, ValueQualification]] = {
    ResolutionState.RESOLVED: ValueQualification.CONFIRMED,
    ResolutionState.RESOLVED_WITH_CONFLICT: ValueQualification.CONFIRMED,
    ResolutionState.UNKNOWN: ValueQualification.MISSING,
    ResolutionState.NEEDS_REVIEW: ValueQualification.MISSING,
    ResolutionState.CONFLICT: ValueQualification.UNRESOLVED_CONFLICT,
}


def from_resolution_state(
    state: ResolutionState, canonical_value: float | None
) -> QualifiedNumericValue:
    """Build a `QualifiedNumericValue` from an accepted `FieldResolution.state`.

    `resolved`/`resolved_with_conflict` carry an accepted current canonical
    value (SEARCH_QUERY_SEMANTICS.v0.1.md §3: "a source-backed canonical
    value with accepted/current resolution may produce TRUE or FALSE") and
    are therefore `CONFIRMED`. `conflict` (a genuinely unresolved conflict,
    no canonical value picked) maps to `UNRESOLVED_CONFLICT`. `unknown` and
    `needs_review` map to `MISSING`. In every non-`CONFIRMED` case the
    supplied value is discarded, not merely ignored, so a caller cannot
    accidentally leak an unqualified value downstream.
    """
    qualification = _RESOLUTION_STATE_QUALIFICATION[state]
    value = canonical_value if qualification is ValueQualification.CONFIRMED else None
    return QualifiedNumericValue(value=value, qualification=qualification)


# ---------------------------------------------------------------------------
# MetricStatus adapter — derived metrics
# ---------------------------------------------------------------------------

_METRIC_STATUS_QUALIFICATION: Final[dict[MetricStatus, ValueQualification]] = {
    MetricStatus.COMPUTED: ValueQualification.CONFIRMED,
    MetricStatus.COMPUTED_PROVISIONAL: ValueQualification.PROVISIONAL,
    MetricStatus.MISSING_INPUT: ValueQualification.MISSING,
    MetricStatus.UNRESOLVED_INPUT: ValueQualification.UNRESOLVED_CONFLICT,
    MetricStatus.INVALID_INPUT: ValueQualification.MISSING,
    MetricStatus.NOT_APPLICABLE: ValueQualification.NOT_APPLICABLE,
    MetricStatus.APPLICABILITY_UNKNOWN: ValueQualification.APPLICABILITY_UNKNOWN,
    MetricStatus.NONSTANDARD_INPUT: ValueQualification.MISSING,
}


def from_derived_metric_status(status: MetricStatus, value: float | None) -> QualifiedNumericValue:
    """Build a `QualifiedNumericValue` from an accepted derived-metric `MetricStatus`.

    Only `computed` is `CONFIRMED`. `computed_provisional` maps to
    `PROVISIONAL` and MUST NOT by itself produce confirmed inclusion or
    exclusion (SEARCH_QUERY_SEMANTICS.v0.1.md §3). `not_applicable` and
    `applicability_unknown` preserve their own accepted semantics
    (SEARCH_QUERY_SEMANTICS.v0.1.md §2) rather than being relabeled
    `MISSING`: `not_applicable` maps to `ValueQualification.NOT_APPLICABLE`,
    which `hullq.search.criteria.evaluate_numeric_leaf` resolves directly to
    FALSE (confirmed exclusion) without inventing a numeric candidate value;
    `applicability_unknown` maps to `ValueQualification.APPLICABILITY_UNKNOWN`,
    which resolves to UNKNOWN with `ReasonCode.APPLICABILITY_UNKNOWN`. This is
    the generic (non-configuration-scoped) status only — evaluating
    `not_applicable`/`applicability_unknown` against a specific
    ResolvedConfiguration/design-option scope belongs to REQ-SEARCH-006 and
    remains out of scope. Every remaining status (missing/unresolved/invalid/
    nonstandard input) maps to `MISSING` or `UNRESOLVED_CONFLICT` and is
    never treated as usable.
    """
    qualification = _METRIC_STATUS_QUALIFICATION[status]
    resolved_value = value if qualification is ValueQualification.CONFIRMED else None
    return QualifiedNumericValue(value=resolved_value, qualification=qualification)
