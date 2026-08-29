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

Does not implement: configuration-aware/option-sensitive qualification,
applicability-as-confirmed-exclusion (`NOT_APPLICABLE` as FALSE) — both
belong to REQ-SEARCH-006 and are explicitly out of scope for this slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from hullq.domain.derived_metrics import MetricStatus
from hullq.domain.provenance import ResolutionState
from hullq.search.types import ValueQualification

__all__ = [
    "QualifiedNumericValue",
    "from_derived_metric_status",
    "from_resolution_state",
]


@dataclass(frozen=True, slots=True)
class QualifiedNumericValue:
    """A candidate numeric value paired with its fail-closed qualification.

    Invariant: `value` is non-`None` if and only if `qualification` is
    `ValueQualification.CONFIRMED`. Constructing any other combination raises
    `ValueError` — this is the single choke point that keeps missing,
    provisional and unresolved-conflict values from silently reaching
    comparison logic as a usable number.
    """

    value: float | None
    qualification: ValueQualification

    def __post_init__(self) -> None:
        is_confirmed = self.qualification is ValueQualification.CONFIRMED
        if is_confirmed and self.value is None:
            raise ValueError("CONFIRMED qualification requires a non-null value")
        if not is_confirmed and self.value is not None:
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
    MetricStatus.NOT_APPLICABLE: ValueQualification.MISSING,
    MetricStatus.APPLICABILITY_UNKNOWN: ValueQualification.MISSING,
    MetricStatus.NONSTANDARD_INPUT: ValueQualification.MISSING,
}


def from_derived_metric_status(status: MetricStatus, value: float | None) -> QualifiedNumericValue:
    """Build a `QualifiedNumericValue` from an accepted derived-metric `MetricStatus`.

    Only `computed` is `CONFIRMED`. `computed_provisional` maps to
    `PROVISIONAL` and MUST NOT by itself produce confirmed inclusion or
    exclusion (SEARCH_QUERY_SEMANTICS.v0.1.md §3). Every other status
    (missing/unresolved/invalid input, not-applicable, applicability-unknown,
    nonstandard input) maps to `MISSING` or `UNRESOLVED_CONFLICT` and is
    never treated as usable — this slice does not implement `NOT_APPLICABLE`
    as confirmed exclusion, which belongs to configuration-aware evaluation
    (REQ-SEARCH-006, out of scope here).
    """
    qualification = _METRIC_STATUS_QUALIFICATION[status]
    resolved_value = value if qualification is ValueQualification.CONFIRMED else None
    return QualifiedNumericValue(value=resolved_value, qualification=qualification)
