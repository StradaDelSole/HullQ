"""Core vocabulary for the HullQ search kernel — SLICE-0033 (+ SLICE-0035).

Matches the accepted `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` (OQ-009 D1-D10)
truth model, reason codes and result-class vocabulary. SLICE-0033 implemented
the minimum numeric-MUST-AND vertical slice. SLICE-0035 adds the categorical
MUST leaf and configuration-aware evaluation vocabulary (`CategoricalLeafKind`
constants live in `hullq.search.criteria`; `ReasonCode.CONFIGURATION_AMBIGUOUS`
is added here) required by `specs/SEARCH_BENCHMARK.v0.1.md`.

Does not implement: PREFER requirement strength, OR/NOT aggregation, or
ranking — still explicitly out of scope.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "LeafCriterionKind",
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
    """Reason codes implemented across SLICE-0033 and SLICE-0035.

    `RANGE_OVERLAPS_THRESHOLD` (SEARCH_QUERY_SEMANTICS.v0.1.md §7) belongs to
    a bounded-value-range representation this slice does not implement — a
    fake range mechanism must not be invented solely to exercise the enum
    (SLICE-0035 stop condition), so it remains absent from this vocabulary.
    `CONFIGURATION_AMBIGUOUS` IS implemented as of SLICE-0035: it is the
    design-level reason attached when a `DesignQueryEvaluation` is
    `INSUFFICIENT_DATA` because the resolved-configuration space is not
    known to be complete (`DesignConfigurationSet.configuration_space_complete`
    is `False`) and no confirmed match already exists — see
    `hullq.search.configuration_engine.evaluate_design_configuration_set`.
    """

    VALUE_MISSING = "VALUE_MISSING"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    PROVISIONAL_VALUE = "PROVISIONAL_VALUE"
    APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONFIGURATION_AMBIGUOUS = "CONFIGURATION_AMBIGUOUS"


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


class LeafCriterionKind(StrEnum):
    """Discriminator for a mixed-query leaf criterion — SLICE-0035 query v0.2.

    Used only by the serialized query-contract boundary
    (`hullq.search.query_mixed`) to tag each criterion dict with which leaf
    type it deserializes to. Not used by v0.1 numeric-only serialization,
    which carries no such discriminator and remains unchanged.
    """

    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
