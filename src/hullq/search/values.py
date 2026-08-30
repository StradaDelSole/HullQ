"""Fail-closed value qualification — SLICE-0033 (+ SLICE-0035 categorical).

`QualifiedNumericValue` and `QualifiedCategoricalValue` are the
persistence-neutral units the search kernel compares against a query leaf.
Neither carries a usable value unless the originating canonical resolution
(or, for numeric values, a derived-metric computation) was fully qualified,
per `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` §3.

The adapters below translate the accepted existing status vocabularies
(`hullq.domain.provenance.ResolutionState` for canonical BoatDesign fields
and `hullq.domain.derived_metrics.MetricStatus` for derived metrics) into the
search kernel's own `ValueQualification`, so evaluation code never has to
reason about raw FieldResolution/FieldEvidence/MetricResult shapes directly.

SLICE-0035 adds `QualifiedCategoricalValue` for the categorical MUST leaf and
its own `from_resolution_state_categorical` adapter (derived metrics are
numeric-only, so there is no categorical `MetricStatus` adapter). Both
qualified-value types are consumed by the configuration-aware evaluator in
`hullq.search.configuration_engine` via `hullq.search.configuration`'s
persistence-neutral `ConfigurationProjection`, never by reading raw BoatDesign
JSON directly (slice Required Behavior §E).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from hullq.domain.derived_metrics import MetricStatus
from hullq.domain.provenance import ResolutionState
from hullq.search.types import ValueQualification

__all__ = [
    "RESERVED_CATEGORICAL_SENTINELS",
    "QualifiedCategoricalValue",
    "QualifiedNumericValue",
    "from_derived_metric_status",
    "from_resolution_state",
    "from_resolution_state_categorical",
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


# ---------------------------------------------------------------------------
# QualifiedCategoricalValue — SLICE-0035 (+ REVIEW amendment 1)
# ---------------------------------------------------------------------------

#: Schema-valid categorical enum literals that are semantic sentinels, not
#: ordinary domain facts: BOAT_DESIGN_SCHEMA.v0.6 categorical enums routinely
#: include `"unknown"` (the value itself is not known) and, for fields such as
#: `rig.masthead_fractional`, `"not_applicable"`. Neither literal may ever be
#: represented as an ordinary `CONFIRMED` string — doing so would let an
#: unqualified/not-applicable domain fact participate in ordinary string
#: equality and manufacture a false confirmed TRUE/FALSE (REVIEW Finding 1).
#: This set is intentionally generic/field-agnostic, exactly like this
#: module's `field` parameters elsewhere: the search kernel does not know any
#: field's specific enum, so the two reserved literals are rejected for every
#: categorical field uniformly rather than requiring a per-field allowlist.
RESERVED_CATEGORICAL_SENTINELS: Final[frozenset[str]] = frozenset({"unknown", "not_applicable"})


@dataclass(frozen=True, slots=True)
class QualifiedCategoricalValue:
    """A candidate canonical string value paired with its fail-closed qualification.

    Invariant: `value` is non-`None` if and only if `qualification` is
    `ValueQualification.CONFIRMED`, and a `CONFIRMED` value MUST be a
    non-empty `str` that is not a member of `RESERVED_CATEGORICAL_SENTINELS`
    — never a numeric type, never whitespace-only, never the literal string
    `"unknown"` or `"not_applicable"`. Constructing any other combination
    raises `ValueError`, the same choke point pattern as `QualifiedNumericValue`
    (slice Required Behavior §A: "no fuzzy synonym matching at evaluator time;
    no case-folding/normalization hidden inside truth evaluation unless the
    projection contract has already canonicalized the value" — so this type
    stores exactly the already-canonicalized string, verbatim, with no
    normalization performed here).

    The reserved-sentinel rejection is enforced here, not only in
    `from_resolution_state_categorical`, so no caller — present or future —
    can bypass it by constructing this type directly (REVIEW Finding 1): a
    reserved sentinel MUST always be represented via the appropriate
    non-`CONFIRMED` qualification (`ValueQualification.MISSING` for
    `"unknown"`, `ValueQualification.NOT_APPLICABLE` for `"not_applicable"`),
    never as an ordinary confirmed string.
    """

    value: str | None
    qualification: ValueQualification

    def __post_init__(self) -> None:
        is_confirmed = self.qualification is ValueQualification.CONFIRMED
        if is_confirmed:
            if not isinstance(self.value, str) or not self.value.strip():
                raise ValueError(
                    f"CONFIRMED qualification requires a non-empty string value; got {self.value!r}"
                )
            if self.value in RESERVED_CATEGORICAL_SENTINELS:
                raise ValueError(
                    f"CONFIRMED qualification must not carry the reserved semantic sentinel "
                    f"value {self.value!r}; use ValueQualification.MISSING for 'unknown' or "
                    f"ValueQualification.NOT_APPLICABLE for 'not_applicable' instead"
                )
        elif self.value is not None:
            raise ValueError(
                f"Non-CONFIRMED qualification {self.qualification!r} must not carry a value"
            )


def from_resolution_state_categorical(
    state: ResolutionState, canonical_value: str | None
) -> QualifiedCategoricalValue:
    """Build a `QualifiedCategoricalValue` from an accepted `FieldResolution.state`.

    Mirrors `from_resolution_state` (same `ResolutionState` ->
    `ValueQualification` mapping) for the categorical baseline/override fields
    introduced by BOAT_DESIGN_SCHEMA.v0.6 (rig.sailplan, rig.masthead_fractional,
    deck.cockpit_position, appendages.keel_type, appendages.rudder_support,
    etc.). There is no categorical derived-metric adapter: HullQ's derived
    metrics (SAD, BDR, comfort ratio, ...) are exclusively numeric.

    REVIEW Finding 1: an otherwise-CONFIRMED `canonical_value` that is a
    reserved semantic sentinel (`RESERVED_CATEGORICAL_SENTINELS`) is rerouted
    to the qualification that actually reflects it, rather than being passed
    through as an ordinary confirmed string: `"unknown"` becomes
    `ValueQualification.MISSING` (the domain value itself is not known —
    `hullq.search.criteria.evaluate_categorical_leaf` yields UNKNOWN /
    `VALUE_MISSING`, never TRUE/FALSE); `"not_applicable"` becomes
    `ValueQualification.NOT_APPLICABLE` (confirmed exclusion via the existing
    NOT_APPLICABLE branch — FALSE, and never equality-matchable against any
    query threshold). A field resolution being `resolved`/
    `resolved_with_conflict` only means the *qualification process* is
    settled; it says nothing about whether the underlying domain fact itself
    is a known, applicable value, so the sentinel check is required even for
    an otherwise-CONFIRMED resolution.
    """
    qualification = _RESOLUTION_STATE_QUALIFICATION[state]
    if qualification is not ValueQualification.CONFIRMED:
        return QualifiedCategoricalValue(value=None, qualification=qualification)
    if canonical_value == "not_applicable":
        return QualifiedCategoricalValue(
            value=None, qualification=ValueQualification.NOT_APPLICABLE
        )
    if canonical_value == "unknown":
        return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)
    return QualifiedCategoricalValue(
        value=canonical_value, qualification=ValueQualification.CONFIRMED
    )
