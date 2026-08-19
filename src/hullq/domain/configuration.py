"""Deterministic appendage/configuration normalization boundary — SLICE-0009.

Turns explicit source-backed configuration observations (keel, rudder, skeg,
hull, board) into typed, auditable normalization results using the existing
BOAT_DESIGN_SCHEMA.v0.5 vocabulary.

Rules are source-agnostic, versioned and deterministic: the same explicit
input plus the same ruleset version always produces the same result.

Does not implement: source acquisition, canonical FieldResolution, BoatDesign
mutation, conflict resolution, authority ranking, NLP/LLM inference, or derived
metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from hullq.domain.provenance import JsonPointer, NormalizedCandidate

__all__ = [
    "RULESET_VERSION",
    "ConfigAxis",
    "ConfigurationNormalizationResult",
    "ConfigurationObservation",
    "HullConfiguration",
    "KeelType",
    "NormalizationOutcome",
    "ObservationScope",
    "RudderType",
    "SkegType",
    "canonical_pointer",
    "normalize_configuration",
    "to_normalized_candidate",
]

RULESET_VERSION: Final[str] = "1.0.0"


# ---------------------------------------------------------------------------
# Canonical vocabulary enums — mirror BOAT_DESIGN_SCHEMA.v0.5 exactly
# ---------------------------------------------------------------------------


class HullConfiguration(StrEnum):
    MONOHULL = "monohull"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    OTHER = "other"
    UNKNOWN = "unknown"


class KeelType(StrEnum):
    FULL = "full"
    MODIFIED_FULL = "modified_full"
    LONG_FIN = "long_fin"
    FIN = "fin"
    WING = "wing"
    BULB = "bulb"
    TWIN = "twin"
    BILGE = "bilge"
    CENTERBOARD = "centerboard"
    DAGGERBOARD = "daggerboard"
    SWING = "swing"
    LIFTING = "lifting"
    SHOAL = "shoal"
    OTHER = "other"
    UNKNOWN = "unknown"


class RudderType(StrEnum):
    KEEL_HUNG = "keel_hung"
    SKEG_HUNG = "skeg_hung"
    PARTIAL_SKEG = "partial_skeg"
    SPADE = "spade"
    TRANSOM_HUNG = "transom_hung"
    TWIN = "twin"
    OTHER = "other"
    UNKNOWN = "unknown"


class SkegType(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Configuration axis vocabulary
# ---------------------------------------------------------------------------


class ConfigAxis(StrEnum):
    HULL_CONFIGURATION = "hull_configuration"
    HULL_COUNT = "hull_count"
    KEEL_TYPE = "keel_type"
    KEEL_SUBTYPE = "keel_subtype"
    RUDDER_TYPE = "rudder_type"
    RUDDER_COUNT = "rudder_count"
    SKEG_TYPE = "skeg_type"
    DAGGERBOARD_COUNT = "daggerboard_count"
    CENTERBOARD_COUNT = "centerboard_count"


_COUNT_AXES: frozenset[ConfigAxis] = frozenset(
    {
        ConfigAxis.HULL_COUNT,
        ConfigAxis.RUDDER_COUNT,
        ConfigAxis.DAGGERBOARD_COUNT,
        ConfigAxis.CENTERBOARD_COUNT,
    }
)

_CATEGORICAL_AXES: frozenset[ConfigAxis] = frozenset(
    {
        ConfigAxis.HULL_CONFIGURATION,
        ConfigAxis.KEEL_TYPE,
        ConfigAxis.KEEL_SUBTYPE,
        ConfigAxis.RUDDER_TYPE,
        ConfigAxis.SKEG_TYPE,
    }
)

# keel_subtype is a preserved free-text field — any non-empty string passes
_FREE_TEXT_AXES: frozenset[ConfigAxis] = frozenset({ConfigAxis.KEEL_SUBTYPE})


# ---------------------------------------------------------------------------
# Normalization outcome and observation scope
# ---------------------------------------------------------------------------


class NormalizationOutcome(StrEnum):
    EXACT = "exact"
    ALIAS = "alias"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    MALFORMED = "malformed"


class ObservationScope(StrEnum):
    BASELINE = "baseline"
    NAMED_VARIANT = "named_variant"
    DESIGN_OPTION = "design_option"
    BOARD_UP = "board_up"
    BOARD_DOWN = "board_down"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Normalization input and result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigurationObservation:
    """Immutable explicit source observation for one configuration axis.

    ``raw_value`` is preserved as-is; it is never inferred or guessed.
    ``scope`` and ``scope_ref`` are retained so that option/variant/state
    observations are never silently treated as baseline facts.
    """

    axis: ConfigAxis
    raw_value: object
    scope: ObservationScope = ObservationScope.BASELINE
    scope_ref: str | None = None
    evidence_id: str | None = None


@dataclass(frozen=True)
class ConfigurationNormalizationResult:
    """Immutable normalization outcome for one ConfigurationObservation.

    ``canonical_value`` is a canonical string for categorical axes or an int
    for count axes, or None when the outcome is not EXACT or ALIAS.
    ``ruleset_version`` ties the result to a deterministic ruleset snapshot.
    """

    observation: ConfigurationObservation
    outcome: NormalizationOutcome
    canonical_value: object
    review_reason: str | None
    rule_id: str | None
    ruleset_version: str


# ---------------------------------------------------------------------------
# Canonical JSON Pointer map
# ---------------------------------------------------------------------------

_AXIS_POINTER: dict[ConfigAxis, str] = {
    ConfigAxis.HULL_CONFIGURATION: "/baseline/configuration/hull_configuration",
    ConfigAxis.HULL_COUNT: "/baseline/configuration/hull_count",
    ConfigAxis.KEEL_TYPE: "/baseline/configuration/keel_type",
    ConfigAxis.KEEL_SUBTYPE: "/baseline/configuration/keel_subtype",
    ConfigAxis.RUDDER_TYPE: "/baseline/configuration/rudder_type",
    ConfigAxis.RUDDER_COUNT: "/baseline/configuration/rudder_count",
    ConfigAxis.SKEG_TYPE: "/baseline/configuration/skeg_type",
    ConfigAxis.DAGGERBOARD_COUNT: "/baseline/configuration/daggerboard_count",
    ConfigAxis.CENTERBOARD_COUNT: "/baseline/configuration/centerboard_count",
}


def canonical_pointer(axis: ConfigAxis) -> JsonPointer:
    """Return the RFC 6901 JSON Pointer for a canonical configuration field."""
    return JsonPointer(_AXIS_POINTER[axis])


# ---------------------------------------------------------------------------
# Canonical value sets for categorical axes
# ---------------------------------------------------------------------------

_CANONICAL_VALUES: dict[ConfigAxis, frozenset[str]] = {
    ConfigAxis.HULL_CONFIGURATION: frozenset(v.value for v in HullConfiguration),
    ConfigAxis.KEEL_TYPE: frozenset(v.value for v in KeelType),
    ConfigAxis.RUDDER_TYPE: frozenset(v.value for v in RudderType),
    ConfigAxis.SKEG_TYPE: frozenset(v.value for v in SkegType),
}


# ---------------------------------------------------------------------------
# Alias table — (axis, normalized_token) → (canonical_value, rule_id)
#
# Only explicit, reviewed, unambiguous lexical equivalents belong here.
# Composite, proprietary, or semantically ambiguous terms are in _REVIEW_TABLE.
# ---------------------------------------------------------------------------

_ALIAS_TABLE: dict[tuple[ConfigAxis, str], tuple[str, str]] = {
    # hull_configuration
    (ConfigAxis.HULL_CONFIGURATION, "mono hull"): ("monohull", "hullcfg-alias-001"),
    (ConfigAxis.HULL_CONFIGURATION, "mono-hull"): ("monohull", "hullcfg-alias-002"),
    # keel_type
    (ConfigAxis.KEEL_TYPE, "full keel"): ("full", "keel-alias-001"),
    (ConfigAxis.KEEL_TYPE, "full-keel"): ("full", "keel-alias-002"),
    (ConfigAxis.KEEL_TYPE, "modified full keel"): ("modified_full", "keel-alias-003"),
    (ConfigAxis.KEEL_TYPE, "modified full"): ("modified_full", "keel-alias-004"),
    (ConfigAxis.KEEL_TYPE, "modified_full keel"): ("modified_full", "keel-alias-005"),
    (ConfigAxis.KEEL_TYPE, "long fin"): ("long_fin", "keel-alias-006"),
    (ConfigAxis.KEEL_TYPE, "long fin keel"): ("long_fin", "keel-alias-007"),
    (ConfigAxis.KEEL_TYPE, "long-fin keel"): ("long_fin", "keel-alias-008"),
    (ConfigAxis.KEEL_TYPE, "long_fin keel"): ("long_fin", "keel-alias-009"),
    (ConfigAxis.KEEL_TYPE, "fin keel"): ("fin", "keel-alias-010"),
    (ConfigAxis.KEEL_TYPE, "wing keel"): ("wing", "keel-alias-011"),
    (ConfigAxis.KEEL_TYPE, "bulb keel"): ("bulb", "keel-alias-012"),
    (ConfigAxis.KEEL_TYPE, "twin keel"): ("twin", "keel-alias-013"),
    (ConfigAxis.KEEL_TYPE, "bilge keel"): ("bilge", "keel-alias-014"),
    (ConfigAxis.KEEL_TYPE, "bilge keels"): ("bilge", "keel-alias-015"),
    (ConfigAxis.KEEL_TYPE, "centreboard"): ("centerboard", "keel-alias-016"),
    (ConfigAxis.KEEL_TYPE, "swing keel"): ("swing", "keel-alias-017"),
    (ConfigAxis.KEEL_TYPE, "lifting keel"): ("lifting", "keel-alias-018"),
    (ConfigAxis.KEEL_TYPE, "lift keel"): ("lifting", "keel-alias-019"),
    (ConfigAxis.KEEL_TYPE, "shoal keel"): ("shoal", "keel-alias-020"),
    # rudder_type
    (ConfigAxis.RUDDER_TYPE, "keel hung rudder"): ("keel_hung", "rudder-alias-001"),
    (ConfigAxis.RUDDER_TYPE, "keel-hung rudder"): ("keel_hung", "rudder-alias-002"),
    (ConfigAxis.RUDDER_TYPE, "keel hung"): ("keel_hung", "rudder-alias-003"),
    (ConfigAxis.RUDDER_TYPE, "skeg hung rudder"): ("skeg_hung", "rudder-alias-004"),
    (ConfigAxis.RUDDER_TYPE, "skeg-hung rudder"): ("skeg_hung", "rudder-alias-005"),
    (ConfigAxis.RUDDER_TYPE, "skeg hung"): ("skeg_hung", "rudder-alias-006"),
    (ConfigAxis.RUDDER_TYPE, "partial skeg"): ("partial_skeg", "rudder-alias-007"),
    (ConfigAxis.RUDDER_TYPE, "spade rudder"): ("spade", "rudder-alias-008"),
    (ConfigAxis.RUDDER_TYPE, "transom hung rudder"): ("transom_hung", "rudder-alias-009"),
    (ConfigAxis.RUDDER_TYPE, "transom-hung rudder"): ("transom_hung", "rudder-alias-010"),
    (ConfigAxis.RUDDER_TYPE, "transom hung"): ("transom_hung", "rudder-alias-011"),
    (ConfigAxis.RUDDER_TYPE, "twin rudder"): ("twin", "rudder-alias-012"),
    (ConfigAxis.RUDDER_TYPE, "twin rudders"): ("twin", "rudder-alias-013"),
    # skeg_type
    (ConfigAxis.SKEG_TYPE, "full skeg"): ("full", "skeg-alias-001"),
    (ConfigAxis.SKEG_TYPE, "partial skeg"): ("partial", "skeg-alias-002"),
    (ConfigAxis.SKEG_TYPE, "no skeg"): ("none", "skeg-alias-003"),
}


# Tokens explicitly routed to AMBIGUOUS with a documented reason
_REVIEW_TABLE: dict[tuple[ConfigAxis, str], str] = {
    (ConfigAxis.KEEL_TYPE, "long keel"): (
        "ambiguous: 'long keel' could mean full or long_fin; use explicit type"
    ),
    (ConfigAxis.KEEL_TYPE, "shoal bulb"): (
        "composite: 'shoal bulb' does not unambiguously map to a single canonical keel type"
    ),
    (ConfigAxis.KEEL_TYPE, "shoal bulb keel"): (
        "composite: 'shoal bulb keel' does not unambiguously map to a single canonical keel type"
    ),
    (ConfigAxis.KEEL_TYPE, "keelboat"): ("generic: 'keelboat' is not a specific keel type"),
    (ConfigAxis.RUDDER_TYPE, "semi-balanced"): (
        "unambiguous mapping not established: 'semi-balanced' is not in the canonical rudder vocabulary"
    ),
    (ConfigAxis.RUDDER_TYPE, "protected rudder"): (
        "unambiguous mapping not established: 'protected rudder' is not in the canonical rudder vocabulary"
    ),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_result(
    obs: ConfigurationObservation,
    outcome: NormalizationOutcome,
    canonical_value: object = None,
    review_reason: str | None = None,
    rule_id: str | None = None,
) -> ConfigurationNormalizationResult:
    return ConfigurationNormalizationResult(
        observation=obs,
        outcome=outcome,
        canonical_value=canonical_value,
        review_reason=review_reason,
        rule_id=rule_id,
        ruleset_version=RULESET_VERSION,
    )


def _normalize_categorical(obs: ConfigurationObservation) -> ConfigurationNormalizationResult:
    raw = obs.raw_value
    if not isinstance(raw, str):
        return _make_result(
            obs,
            NormalizationOutcome.MALFORMED,
            review_reason="categorical axis requires string raw_value",
        )
    if not raw.strip():
        return _make_result(
            obs,
            NormalizationOutcome.MALFORMED,
            review_reason="empty or whitespace-only raw_value",
        )

    axis = obs.axis

    # keel_subtype is a free-text preserved field
    if axis in _FREE_TEXT_AXES:
        return _make_result(obs, NormalizationOutcome.EXACT, canonical_value=raw)

    normalized = raw.strip().lower()
    canonical_set = _CANONICAL_VALUES.get(axis, frozenset())

    if normalized in canonical_set:
        return _make_result(obs, NormalizationOutcome.EXACT, canonical_value=normalized)

    alias_key = (axis, normalized)
    if alias_key in _ALIAS_TABLE:
        canonical_val, rule_id = _ALIAS_TABLE[alias_key]
        return _make_result(
            obs, NormalizationOutcome.ALIAS, canonical_value=canonical_val, rule_id=rule_id
        )

    if alias_key in _REVIEW_TABLE:
        return _make_result(
            obs, NormalizationOutcome.AMBIGUOUS, review_reason=_REVIEW_TABLE[alias_key]
        )

    return _make_result(
        obs,
        NormalizationOutcome.UNSUPPORTED,
        review_reason=f"unrecognized value {raw!r} for axis {axis!r}",
    )


def _normalize_count(obs: ConfigurationObservation) -> ConfigurationNormalizationResult:
    raw = obs.raw_value

    # bool is a subclass of int — explicit rejection required
    if isinstance(raw, bool):
        return _make_result(
            obs,
            NormalizationOutcome.MALFORMED,
            review_reason="boolean rejected; counts must be explicit integers",
        )

    if not isinstance(raw, int):
        return _make_result(
            obs,
            NormalizationOutcome.MALFORMED,
            review_reason=f"count axis requires int raw_value, got {type(raw).__name__!r}",
        )

    if raw < 0:
        return _make_result(
            obs,
            NormalizationOutcome.MALFORMED,
            review_reason=f"negative count {raw} is not valid",
        )

    # hull_count schema minimum is 1
    if obs.axis == ConfigAxis.HULL_COUNT and raw < 1:
        return _make_result(
            obs,
            NormalizationOutcome.MALFORMED,
            review_reason="hull_count must be >= 1",
        )

    return _make_result(obs, NormalizationOutcome.EXACT, canonical_value=raw)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_configuration(obs: ConfigurationObservation) -> ConfigurationNormalizationResult:
    """Normalize a single explicit configuration observation deterministically.

    Outcome is one of EXACT, ALIAS, UNSUPPORTED, AMBIGUOUS, or MALFORMED.
    Never guesses. Same input + same ruleset version always produces the same result.
    Does not create FieldResolution or mutate BoatDesign records.
    """
    axis = obs.axis
    if axis in _COUNT_AXES:
        return _normalize_count(obs)
    if axis in _CATEGORICAL_AXES:
        return _normalize_categorical(obs)
    return _make_result(obs, NormalizationOutcome.MALFORMED, review_reason=f"unknown axis {axis!r}")


def to_normalized_candidate(
    result: ConfigurationNormalizationResult,
) -> NormalizedCandidate | None:
    """Convert a successful normalization result to a NormalizedCandidate.

    Returns None for UNSUPPORTED, AMBIGUOUS and MALFORMED outcomes.
    unit is None (categorical/count values are not physical measurements).
    """
    if result.outcome not in (NormalizationOutcome.EXACT, NormalizationOutcome.ALIAS):
        return None
    return NormalizedCandidate(
        value=result.canonical_value,
        unit=None,
        method_id=result.rule_id or "configuration-exact",
        method_version=result.ruleset_version,
    )
