"""Unit tests for the SLICE-0045 NativeListing offer value representation.

Pure domain tests, no database. Prove: price AMOUNT/POA conditionality with
no synthetic price, normalized country/currency code shape, and that each
optional/conditional field's assertion-kind wrapper accepts exactly the
allowed_assertion_kinds subset locked by
`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` -- no collapse between
UNKNOWN / NOT_APPLICABLE / NO_KNOWN_HISTORY_DECLARED, and omission (Python
None) stays distinct from an explicit assertion.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    AssertionKind,
    BrokerSummaryClaim,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
    VatTaxStatusValue,
)


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "asking_price_mode": AskingPriceMode.AMOUNT,
        "location_country": "FR",
        "broker_description": "A well-maintained cruising sloop.",
        "asking_price_amount": Decimal("125000.00"),
        "currency": "EUR",
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# NativeListingOfferRevisionId
# ---------------------------------------------------------------------------


def test_offer_revision_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        NativeListingOfferRevisionId("")


def test_offer_revision_id_is_not_interchangeable_with_a_plain_string() -> None:
    assert NativeListingOfferRevisionId("REV-1") != "REV-1"


# ---------------------------------------------------------------------------
# Price AMOUNT / POA conditionality
# ---------------------------------------------------------------------------


def test_amount_mode_requires_amount_and_currency() -> None:
    snapshot = NativeListingOfferSnapshot(**_base_kwargs())
    assert snapshot.asking_price_amount == Decimal("125000.00")
    assert snapshot.currency == "EUR"


def test_amount_mode_missing_amount_is_rejected() -> None:
    with pytest.raises(ValueError, match="asking_price_amount is required"):
        NativeListingOfferSnapshot(**_base_kwargs(asking_price_amount=None))


def test_amount_mode_missing_currency_is_rejected() -> None:
    with pytest.raises(ValueError, match="currency is required"):
        NativeListingOfferSnapshot(**_base_kwargs(currency=None))


def test_amount_mode_rejects_non_positive_amount() -> None:
    with pytest.raises(ValueError, match="positive"):
        NativeListingOfferSnapshot(**_base_kwargs(asking_price_amount=Decimal("0")))
    with pytest.raises(ValueError, match="positive"):
        NativeListingOfferSnapshot(**_base_kwargs(asking_price_amount=Decimal("-1")))


@pytest.mark.parametrize("non_finite", [Decimal("Infinity"), Decimal("-Infinity"), Decimal("NaN")])
def test_amount_mode_rejects_non_finite_amount(non_finite: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        NativeListingOfferSnapshot(**_base_kwargs(asking_price_amount=non_finite))


def test_poa_mode_forbids_a_synthetic_amount() -> None:
    with pytest.raises(ValueError, match="no synthetic price"):
        NativeListingOfferSnapshot(
            **_base_kwargs(asking_price_mode=AskingPriceMode.POA, currency=None)
        )


def test_poa_mode_forbids_a_populated_currency() -> None:
    with pytest.raises(ValueError, match="currency must not be populated"):
        NativeListingOfferSnapshot(
            **_base_kwargs(
                asking_price_mode=AskingPriceMode.POA,
                asking_price_amount=None,
            )
        )


def test_poa_mode_with_no_price_fields_is_valid() -> None:
    snapshot = NativeListingOfferSnapshot(
        **_base_kwargs(
            asking_price_mode=AskingPriceMode.POA,
            asking_price_amount=None,
            currency=None,
        )
    )
    assert snapshot.asking_price_amount is None
    assert snapshot.currency is None


# ---------------------------------------------------------------------------
# Normalized country / currency code shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_currency", ["eur", "EURO", "EU", "123", "E1R"])
def test_invalid_currency_code_shape_is_rejected(bad_currency: str) -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        NativeListingOfferSnapshot(**_base_kwargs(currency=bad_currency))


@pytest.mark.parametrize("bad_country", ["fr", "FRA", "F", "12"])
def test_invalid_country_code_shape_is_rejected(bad_country: str) -> None:
    with pytest.raises(ValueError, match="ISO 3166"):
        NativeListingOfferSnapshot(**_base_kwargs(location_country=bad_country))


# ---------------------------------------------------------------------------
# broker_description: REQUIRED_RESPONSE, VALUE_ASSERTION only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_broker_description_rejects_blank_text(blank: str) -> None:
    with pytest.raises(ValueError, match="broker_description"):
        NativeListingOfferSnapshot(**_base_kwargs(broker_description=blank))


# ---------------------------------------------------------------------------
# LocationRegionClaim: VALUE_ASSERTION | UNKNOWN
# ---------------------------------------------------------------------------


def test_location_region_value_assertion_requires_a_value() -> None:
    with pytest.raises(ValueError, match="value is required"):
        LocationRegionClaim(assertion_kind=AssertionKind.VALUE_ASSERTION)


def test_location_region_unknown_forbids_a_value() -> None:
    with pytest.raises(ValueError, match="value must be None"):
        LocationRegionClaim(assertion_kind=AssertionKind.UNKNOWN, value="Brittany")


def test_location_region_unknown_is_valid() -> None:
    claim = LocationRegionClaim(assertion_kind=AssertionKind.UNKNOWN)
    assert claim.value is None


def test_location_region_value_assertion_with_text_is_valid() -> None:
    claim = LocationRegionClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value="Brittany")
    assert claim.value == "Brittany"


def test_location_region_rejects_not_applicable() -> None:
    """NOT_APPLICABLE is not in this field's allowed_assertion_kinds; it must
    not collapse into UNKNOWN's slot."""
    with pytest.raises(ValueError, match="assertion_kind must be one of"):
        LocationRegionClaim(assertion_kind=AssertionKind.NOT_APPLICABLE)


def test_location_region_omission_is_distinct_from_explicit_unknown() -> None:
    omitted = NativeListingOfferSnapshot(**_base_kwargs(location_region=None))
    explicit_unknown = NativeListingOfferSnapshot(
        **_base_kwargs(location_region=LocationRegionClaim(assertion_kind=AssertionKind.UNKNOWN))
    )
    assert omitted.location_region is None
    assert explicit_unknown.location_region is not None
    assert explicit_unknown.location_region.assertion_kind is AssertionKind.UNKNOWN


# ---------------------------------------------------------------------------
# BrokerSummaryClaim: VALUE_ASSERTION | NOT_APPLICABLE
# ---------------------------------------------------------------------------


def test_broker_summary_not_applicable_is_valid() -> None:
    claim = BrokerSummaryClaim(assertion_kind=AssertionKind.NOT_APPLICABLE)
    assert claim.value is None


def test_broker_summary_rejects_unknown() -> None:
    """UNKNOWN is not in this field's allowed_assertion_kinds
    (allows_unknown_response=false in the registry)."""
    with pytest.raises(ValueError, match="assertion_kind must be one of"):
        BrokerSummaryClaim(assertion_kind=AssertionKind.UNKNOWN)


def test_broker_summary_value_assertion_rejects_blank_text() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        BrokerSummaryClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value="   ")


def test_broker_summary_value_assertion_with_text_is_valid() -> None:
    claim = BrokerSummaryClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value="Turnkey cruiser."
    )
    assert claim.value == "Turnkey cruiser."


# ---------------------------------------------------------------------------
# KnownHistoryNarrativeClaim: VALUE_ASSERTION | NO_KNOWN_HISTORY_DECLARED | UNKNOWN
# ---------------------------------------------------------------------------


def test_known_history_narrative_no_known_history_declared_is_valid_and_distinct_from_unknown() -> (
    None
):
    declared = KnownHistoryNarrativeClaim(assertion_kind=AssertionKind.NO_KNOWN_HISTORY_DECLARED)
    unknown = KnownHistoryNarrativeClaim(assertion_kind=AssertionKind.UNKNOWN)
    assert declared != unknown
    assert declared.assertion_kind is not unknown.assertion_kind


def test_known_history_narrative_rejects_not_applicable() -> None:
    with pytest.raises(ValueError, match="assertion_kind must be one of"):
        KnownHistoryNarrativeClaim(assertion_kind=AssertionKind.NOT_APPLICABLE)


def test_known_history_narrative_value_assertion_requires_text() -> None:
    with pytest.raises(ValueError, match="value is required"):
        KnownHistoryNarrativeClaim(assertion_kind=AssertionKind.VALUE_ASSERTION)


def test_known_history_narrative_value_assertion_with_text_is_valid() -> None:
    claim = KnownHistoryNarrativeClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value="Replaced standing rigging in 2021."
    )
    assert claim.value == "Replaced standing rigging in 2021."


# ---------------------------------------------------------------------------
# VatTaxStatusClaim: VALUE_ASSERTION(VatTaxStatusValue) | UNKNOWN, SENSITIVE
# ---------------------------------------------------------------------------


def test_vat_tax_status_value_assertion_requires_the_enum_type() -> None:
    with pytest.raises(TypeError, match="VatTaxStatusValue"):
        VatTaxStatusClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value="VAT_PAID")  # type: ignore[arg-type]


def test_vat_tax_status_value_assertion_accepts_the_enum() -> None:
    claim = VatTaxStatusClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=VatTaxStatusValue.VAT_PAID
    )
    assert claim.value is VatTaxStatusValue.VAT_PAID


def test_vat_tax_status_rejects_no_known_history_declared() -> None:
    with pytest.raises(ValueError, match="assertion_kind must be one of"):
        VatTaxStatusClaim(assertion_kind=AssertionKind.NO_KNOWN_HISTORY_DECLARED)


def test_vat_tax_status_unknown_forbids_a_value() -> None:
    with pytest.raises(ValueError, match="value must be None"):
        VatTaxStatusClaim(assertion_kind=AssertionKind.UNKNOWN, value=VatTaxStatusValue.VAT_PAID)


def test_vat_tax_status_unknown_is_valid() -> None:
    claim = VatTaxStatusClaim(assertion_kind=AssertionKind.UNKNOWN)
    assert claim.value is None


# ---------------------------------------------------------------------------
# Type-safety: wrapper types are not interchangeable with each other
# ---------------------------------------------------------------------------


def test_snapshot_rejects_a_wrapper_of_the_wrong_field_shape() -> None:
    with pytest.raises(TypeError, match="LocationRegionClaim"):
        NativeListingOfferSnapshot(
            **_base_kwargs(
                location_region=BrokerSummaryClaim(assertion_kind=AssertionKind.NOT_APPLICABLE)  # type: ignore[arg-type]
            )
        )


def test_snapshot_accepts_all_optional_claims_populated() -> None:
    snapshot = NativeListingOfferSnapshot(
        **_base_kwargs(
            location_region=LocationRegionClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value="Brittany"
            ),
            broker_summary=BrokerSummaryClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value="Turnkey cruiser."
            ),
            known_history_narrative=KnownHistoryNarrativeClaim(
                assertion_kind=AssertionKind.NO_KNOWN_HISTORY_DECLARED
            ),
            vat_tax_status_claim=VatTaxStatusClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=VatTaxStatusValue.VAT_PAID
            ),
        )
    )
    assert snapshot.location_region is not None
    assert snapshot.broker_summary is not None
    assert snapshot.known_history_narrative is not None
    assert snapshot.vat_tax_status_claim is not None


def test_snapshot_rejects_a_wrong_shape_broker_summary() -> None:
    with pytest.raises(TypeError, match="BrokerSummaryClaim"):
        NativeListingOfferSnapshot(
            **_base_kwargs(
                broker_summary=LocationRegionClaim(assertion_kind=AssertionKind.UNKNOWN)  # type: ignore[arg-type]
            )
        )


def test_snapshot_rejects_a_wrong_shape_known_history_narrative() -> None:
    with pytest.raises(TypeError, match="KnownHistoryNarrativeClaim"):
        NativeListingOfferSnapshot(
            **_base_kwargs(
                known_history_narrative=LocationRegionClaim(assertion_kind=AssertionKind.UNKNOWN)  # type: ignore[arg-type]
            )
        )


def test_snapshot_rejects_a_wrong_shape_vat_tax_status_claim() -> None:
    with pytest.raises(TypeError, match="VatTaxStatusClaim"):
        NativeListingOfferSnapshot(
            **_base_kwargs(
                vat_tax_status_claim=LocationRegionClaim(assertion_kind=AssertionKind.UNKNOWN)  # type: ignore[arg-type]
            )
        )
