"""Domain value-semantics tests for SLICE-0050 PhysicalBoat claims.

Proves the bounded seven-field runtime representation: exactly seven fields,
brand/model required non-blank, build_year required VALUE_ASSERTION|UNKNOWN,
optional technical fields preserve omitted|VALUE_ASSERTION|UNKNOWN,
categorical vocabularies reject unsupported values, and numeric values stay
lossless/non-float at the domain boundary.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    RudderConfiguration,
    RudderConfigurationClaim,
)


def _minimal_snapshot(**overrides: object) -> PhysicalBoatClaimSnapshot:
    defaults: dict[str, object] = {
        "marketed_brand_claim": "Beneteau",
        "model_designation_claim": "Oceanis 30.1",
        "build_year": BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
    }
    defaults.update(overrides)
    return PhysicalBoatClaimSnapshot(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Exactly seven fields
# ---------------------------------------------------------------------------


def test_snapshot_has_exactly_seven_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(PhysicalBoatClaimSnapshot)}
    assert field_names == {
        "marketed_brand_claim",
        "model_designation_claim",
        "build_year",
        "loa_length",
        "draft",
        "keel_configuration",
        "rudder_configuration",
    }


# ---------------------------------------------------------------------------
# Brand / model: required, non-blank, VALUE_ASSERTION-only (plain str)
# ---------------------------------------------------------------------------


def test_brand_and_model_round_trip() -> None:
    snapshot = _minimal_snapshot()
    assert snapshot.marketed_brand_claim == "Beneteau"
    assert snapshot.model_designation_claim == "Oceanis 30.1"


def test_blank_brand_is_rejected() -> None:
    with pytest.raises(ValueError, match="marketed_brand_claim"):
        _minimal_snapshot(marketed_brand_claim="   ")


def test_blank_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="model_designation_claim"):
        _minimal_snapshot(model_designation_claim="")


# ---------------------------------------------------------------------------
# build_year: required response, VALUE_ASSERTION(int) | UNKNOWN
# ---------------------------------------------------------------------------


def test_build_year_value_assertion_round_trips() -> None:
    snapshot = _minimal_snapshot(
        build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=1998)
    )
    assert snapshot.build_year.value == 1998


def test_build_year_explicit_unknown_round_trips() -> None:
    snapshot = _minimal_snapshot(build_year=BuildYearClaim(assertion_kind=AssertionKind.UNKNOWN))
    assert snapshot.build_year.assertion_kind is AssertionKind.UNKNOWN
    assert snapshot.build_year.value is None


def test_build_year_value_assertion_requires_a_value() -> None:
    with pytest.raises(ValueError, match="value is required"):
        BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=None)


def test_build_year_unknown_must_not_carry_a_value() -> None:
    with pytest.raises(ValueError, match="must be None"):
        BuildYearClaim(assertion_kind=AssertionKind.UNKNOWN, value=1998)


def test_build_year_rejects_not_applicable() -> None:
    with pytest.raises(ValueError, match="assertion_kind"):
        BuildYearClaim(assertion_kind=AssertionKind.NOT_APPLICABLE)


def test_build_year_rejects_a_bool_value() -> None:
    """bool is a subclass of int in Python; True/False must never masquerade
    as a calendar year."""
    with pytest.raises(TypeError, match="int"):
        BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=True)


# ---------------------------------------------------------------------------
# Optional technical fields: omitted (None) | VALUE_ASSERTION | UNKNOWN
# ---------------------------------------------------------------------------


def test_loa_length_omitted_by_default() -> None:
    snapshot = _minimal_snapshot()
    assert snapshot.loa_length is None


def test_loa_length_value_assertion_is_lossless_decimal() -> None:
    snapshot = _minimal_snapshot(
        loa_length=LoaLengthClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.14")
        )
    )
    assert snapshot.loa_length.value == Decimal("9.14")
    assert isinstance(snapshot.loa_length.value, Decimal)


def test_loa_length_explicit_unknown_is_distinct_from_omitted() -> None:
    snapshot_omitted = _minimal_snapshot()
    snapshot_unknown = _minimal_snapshot(
        loa_length=LoaLengthClaim(assertion_kind=AssertionKind.UNKNOWN)
    )
    assert snapshot_omitted.loa_length is None
    assert snapshot_unknown.loa_length is not None
    assert snapshot_unknown.loa_length.assertion_kind is AssertionKind.UNKNOWN


def test_loa_length_rejects_a_binary_float() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        LoaLengthClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=9.14)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_value", [Decimal("0"), Decimal("-1.5")])
def test_loa_length_rejects_non_positive_values(bad_value: Decimal) -> None:
    with pytest.raises(ValueError, match="positive"):
        LoaLengthClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=bad_value)


def test_draft_omitted_by_default() -> None:
    assert _minimal_snapshot().draft is None


def test_draft_value_assertion_is_lossless_decimal() -> None:
    snapshot = _minimal_snapshot(
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.65"))
    )
    assert snapshot.draft.value == Decimal("1.65")


def test_draft_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("0"))


# ---------------------------------------------------------------------------
# Categorical vocabularies: keel / rudder configuration
# ---------------------------------------------------------------------------


def test_keel_configuration_omitted_by_default() -> None:
    assert _minimal_snapshot().keel_configuration is None


def test_keel_configuration_value_assertion_round_trips() -> None:
    snapshot = _minimal_snapshot(
        keel_configuration=KeelConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
        )
    )
    assert snapshot.keel_configuration.value is KeelConfiguration.FIN


def test_keel_configuration_rejects_unsupported_categorical_value() -> None:
    with pytest.raises(ValueError):
        KeelConfiguration("SHOAL_DRAFT_BULB")  # not an accepted registry value


def test_keel_configuration_rejects_rudder_value_type() -> None:
    """Keel and rudder configuration are independent categorical vocabularies
    -- a rudder value must not be accepted where a keel value is required."""
    with pytest.raises(TypeError, match="KeelConfiguration"):
        KeelConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION,
            value=RudderConfiguration.SPADE,  # type: ignore[arg-type]
        )


def test_rudder_configuration_omitted_by_default() -> None:
    assert _minimal_snapshot().rudder_configuration is None


def test_rudder_configuration_value_assertion_round_trips() -> None:
    snapshot = _minimal_snapshot(
        rudder_configuration=RudderConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration.SPADE
        )
    )
    assert snapshot.rudder_configuration.value is RudderConfiguration.SPADE


def test_rudder_configuration_rejects_unsupported_categorical_value() -> None:
    with pytest.raises(ValueError):
        RudderConfiguration("BALANCED")  # not an accepted registry value


def test_keel_and_rudder_configuration_are_independent_dimensions() -> None:
    """A boat's keel and rudder configuration claims must be settable
    independently -- CLAUDE.md core guardrail."""
    snapshot = _minimal_snapshot(
        keel_configuration=KeelConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.TWIN_KEEL
        ),
        rudder_configuration=RudderConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration.TWIN
        ),
    )
    assert snapshot.keel_configuration.value is KeelConfiguration.TWIN_KEEL
    assert snapshot.rudder_configuration.value is RudderConfiguration.TWIN


# ---------------------------------------------------------------------------
# Identity kind
# ---------------------------------------------------------------------------


def test_claim_revision_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        PhysicalBoatClaimRevisionId("")


def test_claim_revision_id_not_interchangeable_with_plain_string() -> None:
    revision_id = PhysicalBoatClaimRevisionId("PBCREV-1")
    assert revision_id != "PBCREV-1"
