"""Unit tests for hullq.search.power_criteria_registry — SLICE-0093, extended
SLICE-0094.

Proves the bounded five-token/eight-token public whitelists and that this
module reuses the identical shared `CriterionDefinition`/
`parse_categorical_param`/`parse_numeric_param` kernel the Sail registry
already established, rather than a second ad hoc parser.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from hullq.domain.physical_boat_claims import (
    AssertionKind,
    PhysicalBoatClaimRevisionId,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    PowerEngineCountClaim,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.persistence.physical_boat_claims import CurrentPhysicalBoatClaimObservation
from hullq.search.criteria_registry import CriterionDefinition, CriterionKind
from hullq.search.power_criteria_registry import (
    CANONICAL_POWER_PARAM_KEY_ORDER,
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    POWER_DRIVE_PARAM_KEY,
    POWER_ENGINE_COUNT_DEFINITION,
    POWER_ENGINE_COUNT_PARAM_KEY,
    SEARCH_POWER_DRIVE_VALUES,
    SEARCH_POWER_ENGINE_COUNT_VALUES,
    active_power_definitions,
    parse_categorical_param,
    parse_numeric_param,
)

_POWER_SEARCH_API_TS_PATH = (
    Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "powerSearchApi.ts"
)


def _extract_ts_const_string_array(source_text: str, export_name: str) -> frozenset[str]:
    """Mirrors `test_criteria_registry_parity.py`'s identical extraction
    mechanism -- pure text read, never imports/executes TypeScript."""
    pattern = re.compile(
        rf"export const {re.escape(export_name)}\s*=\s*\[(?P<body>.*?)\]\s*as const;", re.DOTALL
    )
    match = pattern.search(source_text)
    if match is None:
        raise AssertionError(
            f"could not find `export const {export_name} = [...] as const;` in source"
        )
    return frozenset(re.findall(r'"([^"]*)"', match.group("body")))


def test_power_drive_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _POWER_SEARCH_API_TS_PATH.read_text(encoding="utf-8"), "SEARCH_POWER_DRIVE_VALUES"
    )
    assert ts_values == SEARCH_POWER_DRIVE_VALUES


def test_five_token_exact_whitelist() -> None:
    assert {"SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"} == SEARCH_POWER_DRIVE_VALUES


def test_mixed_other_unknown_are_not_public_filter_values() -> None:
    assert "MIXED" not in SEARCH_POWER_DRIVE_VALUES
    assert "OTHER" not in SEARCH_POWER_DRIVE_VALUES
    assert "UNKNOWN" not in SEARCH_POWER_DRIVE_VALUES


def test_definition_reuses_shared_criterion_definition_type() -> None:
    assert isinstance(POWER_DRIVE_CONFIGURATION_DEFINITION, CriterionDefinition)
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.kind is CriterionKind.CATEGORICAL
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.param_keys == (POWER_DRIVE_PARAM_KEY,)
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.allowed_values == SEARCH_POWER_DRIVE_VALUES


def test_active_power_definitions_is_exactly_two() -> None:
    """SLICE-0094: `active_power_definitions()` now reports both accepted
    Power criteria -- a caller evaluating only the unmodified SLICE-0093
    drive-only path builds its own narrower one-definition tuple directly
    rather than calling this function (see
    `hullq.application.power_inventory_query._ACTIVE_POWER_DEFINITIONS`)."""
    assert active_power_definitions() == (
        POWER_DRIVE_CONFIGURATION_DEFINITION,
        POWER_ENGINE_COUNT_DEFINITION,
    )


def test_parse_categorical_param_rejects_unsupported_value() -> None:
    assert (
        parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, ["DIESEL_ELECTRIC"]) is None
    )


def test_parse_categorical_param_accepts_every_whitelisted_token() -> None:
    for value in SEARCH_POWER_DRIVE_VALUES:
        result = parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, [value])
        assert result == (value, True)


def test_parse_categorical_param_empty_is_not_supplied() -> None:
    assert parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, []) == (None, True)


def _observation(
    power_drive_configuration: PowerDriveConfigurationClaim | None,
) -> CurrentPhysicalBoatClaimObservation:
    return CurrentPhysicalBoatClaimObservation(
        claiming_organization_id=MarketplaceOrganizationId("ORG-TEST"),
        revision_id=PhysicalBoatClaimRevisionId("REV-TEST"),
        recorded_by_account_id=AccountId("ACC-TEST"),
        recorded_at=datetime(2026, 1, 1, tzinfo=UTC),
        draft=None,
        keel_configuration=None,
        loa_length=None,
        rudder_configuration=None,
        hull_configuration=None,
        cockpit_position=None,
        deck_saloon=None,
        beam=None,
        hull_material=None,
        vessel_category=None,
        power_drive_configuration=power_drive_configuration,
        power_engine_count=None,
    )


# ---------------------------------------------------------------------------
# Review amendment Finding H (BLOCKER): `read_claim` is a plain passthrough
# for every value, including MIXED -- it must report exactly what the
# current claim asserts so the shared cross-Organization contradiction
# guard in `_qualify_claims_against_definitions` can see a genuine MIXED
# disagreement from another Organization, never silently masked at this
# boundary. "MIXED is not a confirmed exclusion" is applied as a
# result-level downgrade in
# `hullq.application.power_inventory_query
# ._downgrade_mixed_non_match_to_insufficient_data`, strictly after
# ordinary qualification -- see
# `tests/persistence/test_power_inventory_query_slice_0093.py` for the
# PostgreSQL-backed proof of that result-level behavior, including the
# cross-Organization contradiction cases this passthrough makes possible.
# ---------------------------------------------------------------------------


def test_read_claim_mixed_is_a_plain_passthrough_not_reinterpreted() -> None:
    observation = _observation(
        PowerDriveConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=PowerDriveConfiguration.MIXED
        )
    )
    result = POWER_DRIVE_CONFIGURATION_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.VALUE_ASSERTION, "MIXED")


def test_read_claim_other_is_an_ordinary_confirmed_value_not_reinterpreted() -> None:
    observation = _observation(
        PowerDriveConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=PowerDriveConfiguration.OTHER
        )
    )
    result = POWER_DRIVE_CONFIGURATION_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.VALUE_ASSERTION, "OTHER")


def test_read_claim_single_drive_value_is_an_ordinary_confirmed_value() -> None:
    observation = _observation(
        PowerDriveConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=PowerDriveConfiguration.SHAFT
        )
    )
    result = POWER_DRIVE_CONFIGURATION_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.VALUE_ASSERTION, "SHAFT")


def test_read_claim_explicit_unknown_is_unchanged() -> None:
    observation = _observation(PowerDriveConfigurationClaim(assertion_kind=AssertionKind.UNKNOWN))
    result = POWER_DRIVE_CONFIGURATION_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.UNKNOWN, None)


def test_read_claim_omitted_field_is_none() -> None:
    observation = _observation(None)
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.read_claim(observation) is None


# ---------------------------------------------------------------------------
# SLICE-0094: power_engine_count
# ---------------------------------------------------------------------------


def test_eight_token_exact_whitelist() -> None:
    assert {"1", "2", "3", "4", "5", "6", "7", "8"} == SEARCH_POWER_ENGINE_COUNT_VALUES


def test_nine_and_above_are_not_public_filter_values() -> None:
    assert "9" not in SEARCH_POWER_ENGINE_COUNT_VALUES
    assert "0" not in SEARCH_POWER_ENGINE_COUNT_VALUES


def test_power_engine_count_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _POWER_SEARCH_API_TS_PATH.read_text(encoding="utf-8"), "SEARCH_POWER_ENGINE_COUNT_VALUES"
    )
    assert ts_values == SEARCH_POWER_ENGINE_COUNT_VALUES


def test_count_definition_reuses_shared_criterion_definition_type() -> None:
    assert isinstance(POWER_ENGINE_COUNT_DEFINITION, CriterionDefinition)
    assert POWER_ENGINE_COUNT_DEFINITION.kind is CriterionKind.NUMERIC_EXACT
    assert POWER_ENGINE_COUNT_DEFINITION.param_keys == (POWER_ENGINE_COUNT_PARAM_KEY,)
    assert POWER_ENGINE_COUNT_DEFINITION.allowed_values is None


def test_canonical_power_param_key_order_is_drive_then_count() -> None:
    assert CANONICAL_POWER_PARAM_KEY_ORDER == (POWER_DRIVE_PARAM_KEY, POWER_ENGINE_COUNT_PARAM_KEY)


def test_parse_numeric_param_accepts_every_whitelisted_token() -> None:
    for value in SEARCH_POWER_ENGINE_COUNT_VALUES:
        result = parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, [value])
        assert result == (Decimal(value), True)


def test_parse_numeric_param_rejects_nine_and_above() -> None:
    assert parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, ["9"]) is None


def test_parse_numeric_param_rejects_leading_zero() -> None:
    assert parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, ["01"]) is None


def test_parse_numeric_param_rejects_decimal_spelling() -> None:
    assert parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, ["1.0"]) is None


def test_parse_numeric_param_empty_is_not_supplied() -> None:
    assert parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, []) == (None, True)


def _count_observation(
    power_engine_count: PowerEngineCountClaim | None,
) -> CurrentPhysicalBoatClaimObservation:
    return CurrentPhysicalBoatClaimObservation(
        claiming_organization_id=MarketplaceOrganizationId("ORG-TEST"),
        revision_id=PhysicalBoatClaimRevisionId("REV-TEST"),
        recorded_by_account_id=AccountId("ACC-TEST"),
        recorded_at=datetime(2026, 1, 1, tzinfo=UTC),
        draft=None,
        keel_configuration=None,
        loa_length=None,
        rudder_configuration=None,
        hull_configuration=None,
        cockpit_position=None,
        deck_saloon=None,
        beam=None,
        hull_material=None,
        vessel_category=None,
        power_drive_configuration=None,
        power_engine_count=power_engine_count,
    )


def test_count_read_claim_value_assertion_is_an_ordinary_confirmed_value() -> None:
    observation = _count_observation(
        PowerEngineCountClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2)
    )
    result = POWER_ENGINE_COUNT_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.VALUE_ASSERTION, 2)


def test_count_read_claim_truthful_claim_above_public_whitelist_is_unmasked() -> None:
    """A truthful current claim of 9-32 is real -- never masked at the
    claim-read boundary, exactly like `power_drive_configuration`'s own
    MIXED-passthrough discipline (Finding H)."""
    observation = _count_observation(
        PowerEngineCountClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=12)
    )
    result = POWER_ENGINE_COUNT_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.VALUE_ASSERTION, 12)


def test_count_read_claim_explicit_unknown() -> None:
    observation = _count_observation(PowerEngineCountClaim(assertion_kind=AssertionKind.UNKNOWN))
    result = POWER_ENGINE_COUNT_DEFINITION.read_claim(observation)
    assert result == (AssertionKind.UNKNOWN, None)


def test_count_read_claim_omitted_field_is_none() -> None:
    observation = _count_observation(None)
    assert POWER_ENGINE_COUNT_DEFINITION.read_claim(observation) is None
