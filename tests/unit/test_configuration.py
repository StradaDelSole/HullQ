"""Tests for hullq.domain.configuration — SLICE-0009.

Covers all 21 required scenarios from
docs/slices/SLICE-0009-appendage-configuration-normalization.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hullq.domain.configuration import (
    RULESET_VERSION,
    ConfigAxis,
    ConfigurationNormalizationResult,
    ConfigurationObservation,
    HullConfiguration,
    KeelType,
    NormalizationOutcome,
    ObservationScope,
    RudderType,
    SkegType,
    baseline_projection,
    canonical_pointer,
    normalize_configuration,
    to_normalized_candidate,
)
from hullq.domain.provenance import NormalizedCandidate

_SPECS = Path(__file__).parent.parent.parent / "specs"
_SCHEMA = _SPECS / "BOAT_DESIGN_SCHEMA.v0.5.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _obs(
    axis: ConfigAxis,
    raw_value: object,
    scope: ObservationScope = ObservationScope.BASELINE,
    scope_ref: str | None = None,
    evidence_id: str | None = None,
) -> ConfigurationObservation:
    return ConfigurationObservation(
        axis=axis,
        raw_value=raw_value,
        scope=scope,
        scope_ref=scope_ref,
        evidence_id=evidence_id,
    )


def _norm(
    axis: ConfigAxis, raw_value: object, **kwargs: object
) -> ConfigurationNormalizationResult:
    return normalize_configuration(_obs(axis, raw_value, **kwargs))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Requirement 1: vocabulary matches BOAT_DESIGN_SCHEMA.v0.5 exactly
# ---------------------------------------------------------------------------


def test_hull_configuration_vocab_matches_schema() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    schema_values = set(
        schema["properties"]["baseline"]["properties"]["configuration"]["properties"][
            "hull_configuration"
        ]["enum"]
    )
    runtime_values = {v.value for v in HullConfiguration}
    assert runtime_values == schema_values


def test_keel_type_vocab_matches_schema() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    schema_values = set(
        schema["properties"]["baseline"]["properties"]["configuration"]["properties"]["keel_type"][
            "enum"
        ]
    )
    runtime_values = {v.value for v in KeelType}
    assert runtime_values == schema_values


def test_rudder_type_vocab_matches_schema() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    schema_values = set(
        schema["properties"]["baseline"]["properties"]["configuration"]["properties"][
            "rudder_type"
        ]["enum"]
    )
    runtime_values = {v.value for v in RudderType}
    assert runtime_values == schema_values


def test_skeg_type_vocab_matches_schema() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    schema_values = set(
        schema["properties"]["baseline"]["properties"]["configuration"]["properties"]["skeg_type"][
            "enum"
        ]
    )
    runtime_values = {v.value for v in SkegType}
    assert runtime_values == schema_values


# ---------------------------------------------------------------------------
# Requirement 2: exact canonical values normalize idempotently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [v.value for v in HullConfiguration])
def test_hull_configuration_exact_canonical_idempotent(value: str) -> None:
    result = _norm(ConfigAxis.HULL_CONFIGURATION, value)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == value


@pytest.mark.parametrize("value", [v.value for v in KeelType])
def test_keel_type_exact_canonical_idempotent(value: str) -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, value)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == value


@pytest.mark.parametrize("value", [v.value for v in RudderType])
def test_rudder_type_exact_canonical_idempotent(value: str) -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, value)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == value


@pytest.mark.parametrize("value", [v.value for v in SkegType])
def test_skeg_type_exact_canonical_idempotent(value: str) -> None:
    result = _norm(ConfigAxis.SKEG_TYPE, value)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == value


# ---------------------------------------------------------------------------
# Requirement 3: case/whitespace/punctuation normalization is deterministic
# ---------------------------------------------------------------------------


def test_uppercase_keel_type_normalizes_to_exact() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "FIN")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "fin"


def test_mixed_case_rudder_type_normalizes_to_exact() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "Spade")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "spade"


def test_leading_trailing_whitespace_stripped() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "  fin  ")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "fin"


def test_hyphenated_full_keel_alias() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "full-keel")
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == "full"


def test_hyphenated_keel_hung_rudder_alias() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "keel-hung rudder")
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == "keel_hung"


# ---------------------------------------------------------------------------
# Requirement 4: British/American centreboard/centerboard equivalence
# ---------------------------------------------------------------------------


def test_centreboard_british_spelling_maps_to_centerboard() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "centreboard")
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == "centerboard"


def test_centerboard_american_spelling_is_exact() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "centerboard")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "centerboard"


# ---------------------------------------------------------------------------
# Requirement 5: clear keel aliases map correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token,expected",
    [
        ("fin keel", "fin"),
        ("full keel", "full"),
        ("full-keel", "full"),
        ("modified full keel", "modified_full"),
        ("modified full", "modified_full"),
        ("wing keel", "wing"),
        ("twin keel", "twin"),
        ("bilge keel", "bilge"),
        ("bilge keels", "bilge"),
        ("centreboard", "centerboard"),
        ("swing keel", "swing"),
        ("lifting keel", "lifting"),
        ("lift keel", "lifting"),
        ("long fin keel", "long_fin"),
        ("long-fin keel", "long_fin"),
        ("bulb keel", "bulb"),
        ("shoal keel", "shoal"),
    ],
)
def test_keel_alias(token: str, expected: str) -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, token)
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == expected


# ---------------------------------------------------------------------------
# Requirement 6: clear rudder aliases map correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token,expected",
    [
        ("keel hung rudder", "keel_hung"),
        ("keel-hung rudder", "keel_hung"),
        ("keel hung", "keel_hung"),
        ("skeg hung rudder", "skeg_hung"),
        ("skeg-hung rudder", "skeg_hung"),
        ("skeg hung", "skeg_hung"),
        ("partial skeg", "partial_skeg"),
        ("spade rudder", "spade"),
        ("transom hung rudder", "transom_hung"),
        ("transom-hung rudder", "transom_hung"),
        ("transom hung", "transom_hung"),
        ("twin rudder", "twin"),
        ("twin rudders", "twin"),
    ],
)
def test_rudder_alias(token: str, expected: str) -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, token)
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == expected


# ---------------------------------------------------------------------------
# Requirement 7: clear skeg aliases map correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token,expected",
    [
        ("full skeg", "full"),
        ("partial skeg", "partial"),
        ("no skeg", "none"),
    ],
)
def test_skeg_alias(token: str, expected: str) -> None:
    result = _norm(ConfigAxis.SKEG_TYPE, token)
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == expected


# ---------------------------------------------------------------------------
# Requirement 8: unknown/proprietary terms do not map to a guessed canonical value
# ---------------------------------------------------------------------------


def test_long_keel_is_ambiguous_not_guessed() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "long keel")
    assert result.outcome == NormalizationOutcome.AMBIGUOUS
    assert result.canonical_value is None
    assert result.review_reason is not None
    assert "ambiguous" in result.review_reason


def test_shoal_bulb_composite_is_ambiguous() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "shoal bulb")
    assert result.outcome == NormalizationOutcome.AMBIGUOUS
    assert result.canonical_value is None


def test_keelboat_generic_is_ambiguous() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "keelboat")
    assert result.outcome == NormalizationOutcome.AMBIGUOUS
    assert result.canonical_value is None


def test_proprietary_keel_name_is_unsupported() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "HydroFoil XR-7 Proprietary Keel")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED
    assert result.canonical_value is None


def test_semi_balanced_rudder_is_ambiguous() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "semi-balanced")
    assert result.outcome == NormalizationOutcome.AMBIGUOUS


def test_protected_rudder_is_ambiguous() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "protected rudder")
    assert result.outcome == NormalizationOutcome.AMBIGUOUS


def test_unknown_hull_config_token_is_unsupported() -> None:
    result = _norm(ConfigAxis.HULL_CONFIGURATION, "proa")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED
    assert result.canonical_value is None


# ---------------------------------------------------------------------------
# Requirement 9: a term valid on one axis is not accepted on another axis
# ---------------------------------------------------------------------------


def test_skeg_type_full_not_accepted_on_keel_axis() -> None:
    # "full" is valid for skeg_type but also for keel_type — here we test
    # that "partial skeg" (a skeg alias) is NOT accepted on the keel axis
    result = _norm(ConfigAxis.KEEL_TYPE, "partial skeg")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED


def test_keel_type_fin_not_accepted_on_rudder_axis() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "fin")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED


def test_rudder_type_spade_not_accepted_on_keel_axis() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "spade")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED


def test_hull_config_catamaran_not_accepted_on_keel_axis() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "catamaran")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED


def test_keel_hung_rudder_alias_not_on_keel_axis() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "keel hung rudder")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED


# ---------------------------------------------------------------------------
# Requirement 10: malformed/empty observations are explicit failures
# ---------------------------------------------------------------------------


def test_empty_string_is_malformed() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "")
    assert result.outcome == NormalizationOutcome.MALFORMED
    assert result.canonical_value is None


def test_whitespace_only_is_malformed() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "   ")
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_non_string_on_categorical_axis_is_malformed() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, 42)
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_none_on_categorical_axis_is_malformed() -> None:
    result = _norm(ConfigAxis.HULL_CONFIGURATION, None)
    assert result.outcome == NormalizationOutcome.MALFORMED


# ---------------------------------------------------------------------------
# Requirement 11: count normalization rejects booleans, negatives, non-integers
# ---------------------------------------------------------------------------


def test_count_rejects_bool_true() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, True)
    assert result.outcome == NormalizationOutcome.MALFORMED
    assert "boolean" in (result.review_reason or "")


def test_count_rejects_bool_false() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, False)
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_count_rejects_negative() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, -1)
    assert result.outcome == NormalizationOutcome.MALFORMED
    assert result.review_reason is not None and "negative" in result.review_reason


def test_count_rejects_float() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, 2.0)
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_count_rejects_string_prose() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, "two rudders")
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_count_rejects_string_digit() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, "2")
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_hull_count_zero_is_malformed() -> None:
    result = _norm(ConfigAxis.HULL_COUNT, 0)
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_hull_count_negative_is_malformed() -> None:
    result = _norm(ConfigAxis.HULL_COUNT, -1)
    assert result.outcome == NormalizationOutcome.MALFORMED


# ---------------------------------------------------------------------------
# Requirement 12: explicit count values normalize without prose inference
# ---------------------------------------------------------------------------


def test_rudder_count_1_normalizes() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, 1)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 1


def test_rudder_count_2_normalizes() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, 2)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 2


def test_hull_count_1_normalizes() -> None:
    result = _norm(ConfigAxis.HULL_COUNT, 1)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 1


def test_hull_count_2_normalizes() -> None:
    result = _norm(ConfigAxis.HULL_COUNT, 2)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 2


def test_centerboard_count_zero_normalizes() -> None:
    result = _norm(ConfigAxis.CENTERBOARD_COUNT, 0)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 0


def test_daggerboard_count_1_normalizes() -> None:
    result = _norm(ConfigAxis.DAGGERBOARD_COUNT, 1)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 1


# ---------------------------------------------------------------------------
# Requirement 13: twin-rudder semantics do not imply unrelated skeg/keel facts
# ---------------------------------------------------------------------------


def test_twin_rudder_does_not_produce_skeg_fact() -> None:
    # Normalizing "twin rudders" on RUDDER_TYPE axis only produces rudder_type=twin
    rudder_result = _norm(ConfigAxis.RUDDER_TYPE, "twin rudders")
    assert rudder_result.outcome == NormalizationOutcome.ALIAS
    assert rudder_result.canonical_value == "twin"
    # It must not yield a skeg type candidate
    cand = to_normalized_candidate(rudder_result)
    assert cand is not None
    assert rudder_result.observation.axis == ConfigAxis.RUDDER_TYPE


def test_twin_rudder_does_not_produce_keel_fact() -> None:
    rudder_result = _norm(ConfigAxis.RUDDER_TYPE, "twin rudder")
    assert rudder_result.observation.axis == ConfigAxis.RUDDER_TYPE
    assert rudder_result.canonical_value == "twin"
    # Submitting a SEPARATE keel_type observation is required — the normalizer
    # does not auto-derive one from the rudder observation.
    keel_result = _norm(ConfigAxis.KEEL_TYPE, "twin rudder")
    assert keel_result.outcome == NormalizationOutcome.UNSUPPORTED


def test_twin_rudder_count_not_inferred_from_type() -> None:
    # normalize_configuration on RUDDER_TYPE produces only rudder_type semantics;
    # an explicit RUDDER_COUNT observation is needed to normalize count=2.
    rudder_type_result = _norm(ConfigAxis.RUDDER_TYPE, "twin rudders")
    assert rudder_type_result.observation.axis == ConfigAxis.RUDDER_TYPE
    # Count must be supplied separately and explicitly
    rudder_count_result = _norm(ConfigAxis.RUDDER_COUNT, 2)
    assert rudder_count_result.outcome == NormalizationOutcome.EXACT
    assert rudder_count_result.canonical_value == 2


# ---------------------------------------------------------------------------
# Requirement 14: option-scoped observation cannot be projected as baseline
# ---------------------------------------------------------------------------


def test_option_scoped_keel_observation_preserves_scope() -> None:
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "lifting keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="option-lift-keel",
        )
    )
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == "lifting"
    assert result.observation.scope == ObservationScope.DESIGN_OPTION


def test_named_variant_keel_observation_preserves_scope() -> None:
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "shoal",
            scope=ObservationScope.NAMED_VARIANT,
            scope_ref="shallow-draft-variant",
        )
    )
    assert result.observation.scope == ObservationScope.NAMED_VARIANT


def test_baseline_scope_is_default() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    assert result.observation.scope == ObservationScope.BASELINE


# ---------------------------------------------------------------------------
# Requirement 15: board-up/down state remains separate from board type/count
# ---------------------------------------------------------------------------


def test_board_up_scope_preserved() -> None:
    result = normalize_configuration(
        _obs(ConfigAxis.CENTERBOARD_COUNT, 1, scope=ObservationScope.BOARD_UP)
    )
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.observation.scope == ObservationScope.BOARD_UP


def test_board_down_scope_preserved() -> None:
    result = normalize_configuration(
        _obs(ConfigAxis.DAGGERBOARD_COUNT, 2, scope=ObservationScope.BOARD_DOWN)
    )
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.observation.scope == ObservationScope.BOARD_DOWN


def test_centerboard_keel_type_and_board_count_are_separate_axes() -> None:
    # Normalizing keel_type=centerboard does not produce a centerboard_count fact.
    keel_result = _norm(ConfigAxis.KEEL_TYPE, "centerboard")
    assert keel_result.outcome == NormalizationOutcome.EXACT
    assert keel_result.observation.axis == ConfigAxis.KEEL_TYPE
    # Count must be a separate explicit observation.
    count_result = _norm(ConfigAxis.CENTERBOARD_COUNT, 1)
    assert count_result.outcome == NormalizationOutcome.EXACT
    assert count_result.observation.axis == ConfigAxis.CENTERBOARD_COUNT


# ---------------------------------------------------------------------------
# Requirement 16: multiple conflicting observations are not auto-resolved
# ---------------------------------------------------------------------------


def test_two_conflicting_keel_observations_produce_two_independent_results() -> None:
    result_a = _norm(ConfigAxis.KEEL_TYPE, "fin")
    result_b = _norm(ConfigAxis.KEEL_TYPE, "full")
    assert result_a.canonical_value == "fin"
    assert result_b.canonical_value == "full"
    # Each result is independent — the normalizer does not merge or resolve them
    assert result_a.observation.raw_value == "fin"
    assert result_b.observation.raw_value == "full"


def test_conflicting_observations_preserve_independent_raw_values() -> None:
    obs_a = _obs(ConfigAxis.RUDDER_TYPE, "spade", evidence_id="ev-001")
    obs_b = _obs(ConfigAxis.RUDDER_TYPE, "keel_hung", evidence_id="ev-002")
    result_a = normalize_configuration(obs_a)
    result_b = normalize_configuration(obs_b)
    assert result_a.observation.evidence_id == "ev-001"
    assert result_b.observation.evidence_id == "ev-002"
    assert result_a.canonical_value != result_b.canonical_value


# ---------------------------------------------------------------------------
# Requirement 17: raw source representation remains available after normalization
# ---------------------------------------------------------------------------


def test_raw_value_preserved_for_alias_result() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    assert result.canonical_value == "fin"
    assert result.observation.raw_value == "fin keel"


def test_raw_value_preserved_for_exact_result() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "spade")
    assert result.canonical_value == "spade"
    assert result.observation.raw_value == "spade"


def test_raw_value_preserved_for_unsupported_result() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "mystery keel v3")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED
    assert result.observation.raw_value == "mystery keel v3"
    assert result.canonical_value is None


def test_raw_value_preserved_for_count_result() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, 2)
    assert result.canonical_value == 2
    assert result.observation.raw_value == 2


# ---------------------------------------------------------------------------
# Requirement 18: deterministic rule/version metadata is emitted
# ---------------------------------------------------------------------------


def test_ruleset_version_is_present_on_exact_result() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    assert result.ruleset_version == RULESET_VERSION
    assert result.ruleset_version != ""


def test_ruleset_version_is_present_on_alias_result() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    assert result.ruleset_version == RULESET_VERSION
    assert result.rule_id is not None
    assert result.rule_id != ""


def test_ruleset_version_is_present_on_unsupported_result() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "unknown manufacturer keel")
    assert result.ruleset_version == RULESET_VERSION


def test_ruleset_version_is_present_on_malformed_result() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, True)
    assert result.ruleset_version == RULESET_VERSION


def test_alias_rule_id_is_stable() -> None:
    result1 = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    result2 = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    assert result1.rule_id == result2.rule_id


def test_exact_result_has_no_rule_id() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.rule_id is None


# ---------------------------------------------------------------------------
# Requirement 19: no FieldResolution / canonical BoatDesign write
# ---------------------------------------------------------------------------


def test_normalize_configuration_returns_result_not_resolution() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    assert isinstance(result, ConfigurationNormalizationResult)
    # There is no FieldResolution in the return type
    from hullq.domain.provenance import FieldResolution

    assert not isinstance(result, FieldResolution)


def test_to_normalized_candidate_returns_candidate_not_resolution() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    candidate = to_normalized_candidate(result)
    assert isinstance(candidate, NormalizedCandidate)
    from hullq.domain.provenance import FieldResolution

    assert not isinstance(candidate, FieldResolution)


def test_to_normalized_candidate_returns_none_for_unsupported() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "mystery keel")
    assert to_normalized_candidate(result) is None


def test_to_normalized_candidate_returns_none_for_ambiguous() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "long keel")
    assert result.outcome == NormalizationOutcome.AMBIGUOUS
    assert to_normalized_candidate(result) is None


def test_to_normalized_candidate_returns_none_for_malformed() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "")
    assert to_normalized_candidate(result) is None


# ---------------------------------------------------------------------------
# Additional edge-case scenarios from SLICE-0009 Section 7
# ---------------------------------------------------------------------------


# Full/long-keel design with keel-hung rudder (two separate axis observations)
def test_full_keel_design_with_keel_hung_rudder() -> None:
    keel_result = _norm(ConfigAxis.KEEL_TYPE, "full keel")
    rudder_result = _norm(ConfigAxis.RUDDER_TYPE, "keel hung rudder")
    assert keel_result.canonical_value == "full"
    assert rudder_result.canonical_value == "keel_hung"


# Fin or bulb/wing/shoal-style explicit keel wording
def test_fin_keel_explicit() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    assert result.canonical_value == "fin"


def test_bulb_keel_explicit() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "bulb keel")
    assert result.canonical_value == "bulb"


def test_wing_keel_explicit() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "wing keel")
    assert result.canonical_value == "wing"


# Centerboarder: board state separate from keel taxonomy
def test_centerboard_keel_type_observation() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "centerboard")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "centerboard"


def test_centreboard_british_spelling_on_keel_axis() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "centreboard")
    assert result.canonical_value == "centerboard"
    assert result.observation.axis == ConfigAxis.KEEL_TYPE


# Lifting/swing keel as explicit option rather than baseline
def test_lifting_keel_as_design_option() -> None:
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "lifting keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="option-lift-keel",
        )
    )
    assert result.canonical_value == "lifting"
    assert result.observation.scope == ObservationScope.DESIGN_OPTION


def test_swing_keel_as_design_option() -> None:
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "swing keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="option-swing-keel",
        )
    )
    assert result.canonical_value == "swing"
    assert result.observation.scope == ObservationScope.DESIGN_OPTION


# Twin rudders
def test_twin_rudders_observation() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "twin rudders")
    assert result.canonical_value == "twin"


# Skeg-hung rudder
def test_skeg_hung_rudder_observation() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "skeg hung rudder")
    assert result.canonical_value == "skeg_hung"


# Partial-skeg rudder
def test_partial_skeg_rudder_on_rudder_axis() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "partial skeg")
    assert result.canonical_value == "partial_skeg"


# Partial skeg on skeg axis
def test_partial_skeg_on_skeg_axis() -> None:
    result = _norm(ConfigAxis.SKEG_TYPE, "partial skeg")
    assert result.canonical_value == "partial"


# Twin rudders with separate skeg observation (skeg semantics not derived from rudder)
def test_twin_rudders_with_skeg_are_separate_observations() -> None:
    rudder_result = _norm(ConfigAxis.RUDDER_TYPE, "twin rudders")
    skeg_result = _norm(ConfigAxis.SKEG_TYPE, "partial")
    assert rudder_result.canonical_value == "twin"
    assert skeg_result.canonical_value == "partial"
    # They are independent — normalizer does not couple them
    assert rudder_result.observation.axis != skeg_result.observation.axis


# Catamaran/trimaran hull configuration and explicit hull count
def test_catamaran_hull_configuration() -> None:
    result = _norm(ConfigAxis.HULL_CONFIGURATION, "catamaran")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "catamaran"


def test_trimaran_hull_configuration() -> None:
    result = _norm(ConfigAxis.HULL_CONFIGURATION, "trimaran")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "trimaran"


def test_catamaran_hull_count_explicit() -> None:
    result = _norm(ConfigAxis.HULL_COUNT, 2)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 2


def test_trimaran_hull_count_explicit() -> None:
    result = _norm(ConfigAxis.HULL_COUNT, 3)
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == 3


# Proprietary/unknown manufacturer terminology routed to review
def test_proprietary_terminology_unsupported() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "VortexKeel™ Deep Blue Edition")
    assert result.outcome == NormalizationOutcome.UNSUPPORTED
    assert result.canonical_value is None
    assert result.review_reason is not None


# Conflicting observations retained as independent results (not auto-resolved)
def test_conflicting_keel_types_not_auto_resolved() -> None:
    obs_a = _obs(ConfigAxis.KEEL_TYPE, "fin", evidence_id="src-A")
    obs_b = _obs(ConfigAxis.KEEL_TYPE, "full", evidence_id="src-B")
    result_a = normalize_configuration(obs_a)
    result_b = normalize_configuration(obs_b)
    assert result_a.canonical_value == "fin"
    assert result_b.canonical_value == "full"
    assert result_a != result_b


# ---------------------------------------------------------------------------
# NormalizedCandidate integration
# ---------------------------------------------------------------------------


def test_to_normalized_candidate_exact_keel() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    candidate = to_normalized_candidate(result)
    assert candidate is not None
    assert candidate.value == "fin"
    assert candidate.unit is None
    assert candidate.method_version == RULESET_VERSION


def test_to_normalized_candidate_alias_keel() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    candidate = to_normalized_candidate(result)
    assert candidate is not None
    assert candidate.value == "fin"
    assert candidate.unit is None
    assert candidate.method_id is not None


def test_to_normalized_candidate_exact_count() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, 2)
    candidate = to_normalized_candidate(result)
    assert candidate is not None
    assert candidate.value == 2
    assert candidate.unit is None


# ---------------------------------------------------------------------------
# Canonical pointer tests
# ---------------------------------------------------------------------------


def test_canonical_pointer_keel_type() -> None:
    ptr = canonical_pointer(ConfigAxis.KEEL_TYPE)
    assert str(ptr) == "/baseline/configuration/keel_type"


def test_canonical_pointer_hull_configuration() -> None:
    ptr = canonical_pointer(ConfigAxis.HULL_CONFIGURATION)
    assert str(ptr) == "/baseline/configuration/hull_configuration"


def test_canonical_pointer_rudder_count() -> None:
    ptr = canonical_pointer(ConfigAxis.RUDDER_COUNT)
    assert str(ptr) == "/baseline/configuration/rudder_count"


def test_canonical_pointer_all_axes_defined() -> None:
    for axis in ConfigAxis:
        ptr = canonical_pointer(axis)
        assert str(ptr).startswith("/baseline/configuration/")


# ---------------------------------------------------------------------------
# keel_subtype free-text passthrough
# ---------------------------------------------------------------------------


def test_keel_subtype_free_text_passes_through() -> None:
    result = _norm(ConfigAxis.KEEL_SUBTYPE, "deep draft carbon blade")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "deep draft carbon blade"


def test_keel_subtype_any_non_empty_string_valid() -> None:
    result = _norm(ConfigAxis.KEEL_SUBTYPE, "manufacturer proprietary name")
    assert result.outcome == NormalizationOutcome.EXACT


def test_keel_subtype_empty_string_is_malformed() -> None:
    result = _norm(ConfigAxis.KEEL_SUBTYPE, "")
    assert result.outcome == NormalizationOutcome.MALFORMED


def test_keel_subtype_non_string_is_malformed() -> None:
    result = _norm(ConfigAxis.KEEL_SUBTYPE, 42)
    assert result.outcome == NormalizationOutcome.MALFORMED


# ---------------------------------------------------------------------------
# Finding 1 — Scope-safe projection via baseline_projection()
# ---------------------------------------------------------------------------


# 1. BASELINE observation projects successfully
def test_baseline_keel_projects_to_baseline_pointer() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    projection = baseline_projection(result)
    assert projection is not None
    pointer, candidate = projection
    assert str(pointer) == "/baseline/configuration/keel_type"
    assert candidate.value == "fin"


def test_baseline_alias_keel_projects_to_baseline_pointer() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin keel")
    projection = baseline_projection(result)
    assert projection is not None
    pointer, candidate = projection
    assert str(pointer) == "/baseline/configuration/keel_type"
    assert candidate.value == "fin"


def test_baseline_count_projects_to_baseline_pointer() -> None:
    result = _norm(ConfigAxis.RUDDER_COUNT, 2)
    projection = baseline_projection(result)
    assert projection is not None
    pointer, candidate = projection
    assert str(pointer) == "/baseline/configuration/rudder_count"
    assert candidate.value == 2


# 2. DESIGN_OPTION is refused by baseline_projection
def test_design_option_refused_by_baseline_projection() -> None:
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "lifting keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="option-lift",
        )
    )
    assert result.outcome == NormalizationOutcome.ALIAS
    assert baseline_projection(result) is None


# 3. NAMED_VARIANT is refused by baseline_projection
def test_named_variant_refused_by_baseline_projection() -> None:
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "shoal",
            scope=ObservationScope.NAMED_VARIANT,
            scope_ref="shallow-draft",
        )
    )
    assert result.outcome == NormalizationOutcome.EXACT
    assert baseline_projection(result) is None


# 4. BOARD_UP is refused by baseline_projection
def test_board_up_refused_by_baseline_projection() -> None:
    result = normalize_configuration(
        _obs(ConfigAxis.CENTERBOARD_COUNT, 1, scope=ObservationScope.BOARD_UP)
    )
    assert result.outcome == NormalizationOutcome.EXACT
    assert baseline_projection(result) is None


# 5. BOARD_DOWN is refused by baseline_projection
def test_board_down_refused_by_baseline_projection() -> None:
    result = normalize_configuration(
        _obs(ConfigAxis.DAGGERBOARD_COUNT, 2, scope=ObservationScope.BOARD_DOWN)
    )
    assert result.outcome == NormalizationOutcome.EXACT
    assert baseline_projection(result) is None


# 6. DESIGN_OPTION requires non-empty scope_ref
def test_design_option_without_scope_ref_raises() -> None:
    with pytest.raises(ValueError, match="scope_ref"):
        ConfigurationObservation(
            axis=ConfigAxis.KEEL_TYPE,
            raw_value="lifting keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref=None,
        )


def test_design_option_with_empty_scope_ref_raises() -> None:
    with pytest.raises(ValueError, match="scope_ref"):
        ConfigurationObservation(
            axis=ConfigAxis.KEEL_TYPE,
            raw_value="lifting keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="",
        )


def test_design_option_with_whitespace_scope_ref_raises() -> None:
    with pytest.raises(ValueError, match="scope_ref"):
        ConfigurationObservation(
            axis=ConfigAxis.KEEL_TYPE,
            raw_value="lifting keel",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="   ",
        )


# 7. NAMED_VARIANT requires non-empty scope_ref
def test_named_variant_without_scope_ref_raises() -> None:
    with pytest.raises(ValueError, match="scope_ref"):
        ConfigurationObservation(
            axis=ConfigAxis.KEEL_TYPE,
            raw_value="shoal",
            scope=ObservationScope.NAMED_VARIANT,
            scope_ref=None,
        )


def test_named_variant_with_empty_scope_ref_raises() -> None:
    with pytest.raises(ValueError, match="scope_ref"):
        ConfigurationObservation(
            axis=ConfigAxis.KEEL_TYPE,
            raw_value="shoal",
            scope=ObservationScope.NAMED_VARIANT,
            scope_ref="",
        )


# 8. Baseline normalization behavior unchanged
def test_baseline_normalization_unchanged_fin() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "fin")
    assert result.outcome == NormalizationOutcome.EXACT
    assert result.canonical_value == "fin"
    assert result.ruleset_version == RULESET_VERSION


def test_baseline_normalization_unchanged_alias() -> None:
    result = _norm(ConfigAxis.RUDDER_TYPE, "keel hung rudder")
    assert result.outcome == NormalizationOutcome.ALIAS
    assert result.canonical_value == "keel_hung"


# 9. to_normalized_candidate is scope-agnostic; baseline_projection is the safe path
def test_to_normalized_candidate_does_not_check_scope() -> None:
    # to_normalized_candidate converts outcome only — it is scope-agnostic
    result = normalize_configuration(
        _obs(
            ConfigAxis.KEEL_TYPE,
            "fin",
            scope=ObservationScope.DESIGN_OPTION,
            scope_ref="opt-fin",
        )
    )
    # The low-level helper still converts the outcome
    candidate = to_normalized_candidate(result)
    assert candidate is not None
    assert candidate.value == "fin"
    # But the scope-safe path (baseline_projection) refuses it
    assert baseline_projection(result) is None


# baseline_projection also refuses non-successful outcomes at baseline scope
def test_baseline_projection_refuses_unsupported_outcome() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "mystery keel")
    assert result.observation.scope == ObservationScope.BASELINE
    assert result.outcome == NormalizationOutcome.UNSUPPORTED
    assert baseline_projection(result) is None


def test_baseline_projection_refuses_malformed_outcome() -> None:
    result = _norm(ConfigAxis.KEEL_TYPE, "")
    assert result.observation.scope == ObservationScope.BASELINE
    assert result.outcome == NormalizationOutcome.MALFORMED
    assert baseline_projection(result) is None


# BOARD_UP/BOARD_DOWN do not require scope_ref (board state does not fabricate an option ID)
def test_board_up_does_not_require_scope_ref() -> None:
    obs = ConfigurationObservation(
        axis=ConfigAxis.CENTERBOARD_COUNT,
        raw_value=1,
        scope=ObservationScope.BOARD_UP,
        scope_ref=None,
    )
    assert obs.scope == ObservationScope.BOARD_UP
    assert obs.scope_ref is None


def test_board_down_does_not_require_scope_ref() -> None:
    obs = ConfigurationObservation(
        axis=ConfigAxis.DAGGERBOARD_COUNT,
        raw_value=2,
        scope=ObservationScope.BOARD_DOWN,
        scope_ref=None,
    )
    assert obs.scope == ObservationScope.BOARD_DOWN


# ---------------------------------------------------------------------------
# Finding 2 — ConfigurationObservation raw_value snapshot safety
# ---------------------------------------------------------------------------


def test_dict_raw_value_snapshotted_at_construction() -> None:
    raw: dict[str, object] = {"type": "fin"}
    obs = ConfigurationObservation(axis=ConfigAxis.KEEL_TYPE, raw_value=raw)
    raw["type"] = "full"
    assert obs.raw_value == {"type": "fin"}


def test_dict_raw_value_snapshotted_before_normalization() -> None:
    raw: dict[str, object] = {"type": "fin"}
    obs = ConfigurationObservation(axis=ConfigAxis.KEEL_TYPE, raw_value=raw)
    result = normalize_configuration(obs)
    raw["type"] = "full"
    assert result.observation.raw_value == {"type": "fin"}


def test_list_raw_value_snapshotted_at_construction() -> None:
    raw: list[str] = ["fin"]
    obs = ConfigurationObservation(axis=ConfigAxis.KEEL_TYPE, raw_value=raw)
    raw.append("full")
    assert obs.raw_value == ["fin"]


def test_nested_dict_raw_value_snapshotted_deeply() -> None:
    raw: dict[str, object] = {"outer": {"inner": "fin"}}
    obs = ConfigurationObservation(axis=ConfigAxis.KEEL_TYPE, raw_value=raw)
    inner = raw["outer"]
    assert isinstance(inner, dict)
    inner["inner"] = "full"
    assert obs.raw_value == {"outer": {"inner": "fin"}}


def test_malformed_dict_raw_value_still_snapshotted() -> None:
    # Even MALFORMED observations must have stable raw provenance
    raw: dict[str, object] = {"unexpected": 42}
    obs = ConfigurationObservation(axis=ConfigAxis.RUDDER_COUNT, raw_value=raw)
    result = normalize_configuration(obs)
    assert result.outcome == NormalizationOutcome.MALFORMED
    raw["unexpected"] = 99
    assert result.observation.raw_value == {"unexpected": 42}
