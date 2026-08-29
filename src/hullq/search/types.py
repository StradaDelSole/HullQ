"""Core vocabulary for the HullQ search kernel — SLICE-0033.

Matches the accepted `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` (OQ-009 D1-D10)
truth model, reason codes and result-class vocabulary for the implemented
minimum numeric-MUST-AND vertical slice.

Does not implement: PREFER requirement strength, OR/NOT aggregation, ranking,
or option-sensitive/ResolvedConfiguration-scoped configuration-aware
evaluation (REQ-SEARCH-006). `NOT_APPLICABLE` and `APPLICABILITY_UNKNOWN` are
implemented as generic (non-configuration-scoped) statuses only — see
`hullq.search.values.from_derived_metric_status`.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "NumericComparisonKind",
    "ReasonCode",
    "RequirementStrength",
    "ResultClass",
    "TruthState",
    "ValueQualification",
]


class TruthState(StrEnum):
    """Per-criterion semantic truth state — SEARCH_QUERY_SEMANTICS.v0.1.md §1."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class ResultClass(StrEnum):
    """Query-level product outcome — SEARCH_QUERY_SEMANTICS.v0.1.md §1, §4."""

    CONFIRMED_MATCH = "CONFIRMED_MATCH"
    CONFIRMED_NON_MATCH = "CONFIRMED_NON_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ReasonCode(StrEnum):
    """Reason codes implemented by this slice's numeric-MUST-AND vertical.

    `CONFIGURATION_AMBIGUOUS` and `RANGE_OVERLAPS_THRESHOLD` belong to
    option-sensitive/bounded-value-range configuration-aware evaluation
    (REQ-SEARCH-006, SEARCH_QUERY_SEMANTICS.v0.1.md §7), which is explicitly
    out of scope for this slice. `APPLICABILITY_UNKNOWN` and `NOT_APPLICABLE`
    ARE implemented, as generic (non-configuration-scoped) derived-metric
    statuses — see `hullq.search.values.from_derived_metric_status`.
    """

    VALUE_MISSING = "VALUE_MISSING"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    PROVISIONAL_VALUE = "PROVISIONAL_VALUE"
    APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RequirementStrength(StrEnum):
    """Requirement strength for the implemented subset — MUST only.

    PREFER is deliberately not represented: SEARCH_QUERY_SEMANTICS.v0.1.md §11
    and this slice's explicit-out-of-scope list defer PREFER ranking to a
    later slice under its own controlling decision.
    """

    MUST = "MUST"


class ValueQualification(StrEnum):
    """Whether a candidate numeric value may determine confirmed truth.

    Persistence-neutral: derived from either a canonical `FieldResolution`
    state (`hullq.domain.provenance.ResolutionState`) or a derived-metric
    `MetricStatus` (`hullq.domain.derived_metrics.MetricStatus`) by the
    adapters in `hullq.search.values`. `CONFIRMED` may determine TRUE or
    FALSE via numeric comparison. `NOT_APPLICABLE` is the one other member
    that determines a truth state directly — FALSE (confirmed exclusion),
    never via numeric comparison and never inventing a candidate value
    (SEARCH_QUERY_SEMANTICS.v0.1.md §2). Every remaining member fails closed
    to UNKNOWN.
    """

    CONFIRMED = "CONFIRMED"
    MISSING = "MISSING"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    PROVISIONAL = "PROVISIONAL"
    APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class NumericComparisonKind(StrEnum):
    """Shape of a numeric leaf criterion's threshold comparison."""

    MINIMUM = "MINIMUM"
    MAXIMUM = "MAXIMUM"
    RANGE = "RANGE"
