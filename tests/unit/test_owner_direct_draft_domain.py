"""Unit tests for hullq.domain.owner_direct_draft — SLICE-0054.

Covers the pure bounded v0.1 draft-payload validation boundary (contract
§6) independent of any persistence/network concern.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.domain.owner_direct_draft import (
    EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
    AskingPriceMode,
    BuildYearAssertionKind,
    BuildYearResponse,
    InvalidOwnerDirectDraftPayloadError,
    OwnerDirectListingDraftId,
    parse_owner_direct_draft_payload,
)


class TestOwnerDirectListingDraftId:
    def test_valid_value_constructs(self) -> None:
        assert OwnerDirectListingDraftId("draft-1").value == "draft-1"

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            OwnerDirectListingDraftId("")


class TestParseOwnerDirectDraftPayloadEmptyAndUnknown:
    def test_empty_dict_is_valid(self) -> None:
        payload = parse_owner_direct_draft_payload({})
        assert payload == EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD

    def test_non_dict_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(["not", "a", "dict"])

    def test_unknown_key_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.hull_material": "GRP"})

    def test_broker_narrative_field_not_reused(self) -> None:
        """Contract §6.2: no broker-specific narrative field is renamed or
        reused for a private seller in this slice."""
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"broker_summary": "Great boat"})


class TestParseOwnerDirectDraftPayloadStringFields:
    @pytest.mark.parametrize(
        "key",
        [
            "physical_boat.marketed_brand_claim",
            "physical_boat.model_designation_claim",
            "physical_boat.boat_name",
            "listing_offer.location_region",
        ],
    )
    def test_valid_string_accepted(self, key: str) -> None:
        """Contract §6.2: these fields are a "trimmed non-empty string" --
        the persisted/returned value is the stripped form, not the raw
        input verbatim."""
        payload = parse_owner_direct_draft_payload({key: "  Beneteau  "})
        assert getattr(payload, key.split(".", 1)[1]) == "Beneteau"

    @pytest.mark.parametrize(
        "key",
        [
            "physical_boat.marketed_brand_claim",
            "physical_boat.model_designation_claim",
            "physical_boat.boat_name",
            "listing_offer.location_region",
        ],
    )
    def test_whitespace_only_string_rejected(self, key: str) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({key: "   "})

    @pytest.mark.parametrize(
        "key",
        [
            "physical_boat.marketed_brand_claim",
            "physical_boat.model_designation_claim",
            "physical_boat.boat_name",
            "listing_offer.location_region",
        ],
    )
    def test_non_string_rejected(self, key: str) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({key: 123})


class TestParseOwnerDirectDraftPayloadBuildYear:
    """SLICE-0066: `physical_boat.build_year` accepts the legacy bare
    integer (compatibility) and the canonical structured VALUE_ASSERTION/
    UNKNOWN object, and preserves omission != UNKNOWN != VALUE_ASSERTION."""

    def test_legacy_int_accepted_and_normalizes_to_value_assertion(self) -> None:
        payload = parse_owner_direct_draft_payload({"physical_boat.build_year": 1998})
        assert payload.build_year == BuildYearResponse(BuildYearAssertionKind.VALUE_ASSERTION, 1998)

    def test_bool_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.build_year": True})

    def test_string_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.build_year": "1998"})

    def test_float_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.build_year": 1998.0})

    def test_null_rejected(self) -> None:
        """Contract §3.2/§4: JSON null is not omission and fails closed."""
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.build_year": None})

    def test_omitted_key_is_none_not_unknown(self) -> None:
        payload = parse_owner_direct_draft_payload({})
        assert payload.build_year is None

    def test_structured_value_assertion_accepted(self) -> None:
        payload = parse_owner_direct_draft_payload(
            {"physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 1987}}
        )
        assert payload.build_year == BuildYearResponse(BuildYearAssertionKind.VALUE_ASSERTION, 1987)

    def test_structured_unknown_accepted(self) -> None:
        payload = parse_owner_direct_draft_payload(
            {"physical_boat.build_year": {"assertion_kind": "UNKNOWN"}}
        )
        assert payload.build_year == BuildYearResponse(BuildYearAssertionKind.UNKNOWN)

    def test_omitted_unknown_and_value_assertion_are_mechanically_distinct(self) -> None:
        omitted = parse_owner_direct_draft_payload({}).build_year
        unknown = parse_owner_direct_draft_payload(
            {"physical_boat.build_year": {"assertion_kind": "UNKNOWN"}}
        ).build_year
        known = parse_owner_direct_draft_payload({"physical_boat.build_year": 1987}).build_year
        assert omitted is None
        assert unknown != known
        assert omitted != unknown
        assert omitted != known

    def test_unknown_with_value_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {"physical_boat.build_year": {"assertion_kind": "UNKNOWN", "value": 1987}}
            )

    def test_unknown_with_null_value_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {"physical_boat.build_year": {"assertion_kind": "UNKNOWN", "value": None}}
            )

    def test_value_assertion_missing_value_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {"physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION"}}
            )

    def test_value_assertion_bool_value_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {"physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": True}}
            )

    def test_invalid_assertion_kind_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {"physical_boat.build_year": {"assertion_kind": "ABSENT"}}
            )

    def test_missing_assertion_kind_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.build_year": {"value": 1987}})

    def test_extra_member_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {
                    "physical_boat.build_year": {
                        "assertion_kind": "VALUE_ASSERTION",
                        "value": 1987,
                        "extra": "nope",
                    }
                }
            )

    def test_empty_object_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"physical_boat.build_year": {}})


class TestParseOwnerDirectDraftPayloadAskingPriceMode:
    @pytest.mark.parametrize("value", ["AMOUNT", "POA"])
    def test_valid_value_accepted(self, value: str) -> None:
        payload = parse_owner_direct_draft_payload({"listing_offer.asking_price_mode": value})
        assert payload.asking_price_mode is AskingPriceMode(value)

    @pytest.mark.parametrize("value", ["amount", "poa", "OTHER", "", 1])
    def test_invalid_value_rejected(self, value: object) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"listing_offer.asking_price_mode": value})


class TestParseOwnerDirectDraftPayloadAskingPriceAmount:
    def test_valid_decimal_string_accepted(self) -> None:
        payload = parse_owner_direct_draft_payload(
            {
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "129000.50",
            }
        )
        assert payload.asking_price_amount == Decimal("129000.50")

    @pytest.mark.parametrize(
        "value", ["0", "-1", "1e5", "1,000", " 100", "100 ", "abc", 100, 100.0]
    )
    def test_invalid_value_rejected(self, value: object) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"listing_offer.asking_price_amount": value})

    def test_poa_with_amount_rejected(self) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload(
                {
                    "listing_offer.asking_price_mode": "POA",
                    "listing_offer.asking_price_amount": "100",
                }
            )

    def test_amount_mode_without_amount_is_valid(self) -> None:
        """Contract §6.2: amount/currency MAY still be absent under AMOUNT mode."""
        payload = parse_owner_direct_draft_payload({"listing_offer.asking_price_mode": "AMOUNT"})
        assert payload.asking_price_amount is None

    def test_poa_without_amount_is_valid(self) -> None:
        payload = parse_owner_direct_draft_payload({"listing_offer.asking_price_mode": "POA"})
        assert payload.asking_price_amount is None


class TestParseOwnerDirectDraftPayloadCurrencyAndCountry:
    def test_valid_currency_accepted(self) -> None:
        payload = parse_owner_direct_draft_payload({"listing_offer.currency": "EUR"})
        assert payload.currency == "EUR"

    @pytest.mark.parametrize("value", ["eur", "EU", "EURO", "", 1])
    def test_invalid_currency_rejected(self, value: object) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"listing_offer.currency": value})

    def test_valid_country_accepted(self) -> None:
        payload = parse_owner_direct_draft_payload({"listing_offer.location_country": "FR"})
        assert payload.location_country == "FR"

    @pytest.mark.parametrize("value", ["fr", "F", "FRA", "", 1])
    def test_invalid_country_rejected(self, value: object) -> None:
        with pytest.raises(InvalidOwnerDirectDraftPayloadError):
            parse_owner_direct_draft_payload({"listing_offer.location_country": value})


class TestOwnerDirectDraftPayloadToWireDict:
    def test_empty_payload_renders_empty_dict(self) -> None:
        assert EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD.to_wire_dict() == {}

    def test_roundtrip_preserves_values(self) -> None:
        """Contract §5/§7: a legacy bare-integer build year remains accepted
        as ingress, but the canonical API/readback serialization is always
        the structured VALUE_ASSERTION object, never the legacy bare integer."""
        raw = {
            "physical_boat.marketed_brand_claim": "Beneteau",
            "physical_boat.model_designation_claim": "Oceanis 40",
            "physical_boat.build_year": 2005,
            "physical_boat.boat_name": "Sea Breeze",
            "listing_offer.asking_price_mode": "AMOUNT",
            "listing_offer.asking_price_amount": "129000.50",
            "listing_offer.currency": "EUR",
            "listing_offer.location_country": "FR",
            "listing_offer.location_region": "Brittany",
        }
        payload = parse_owner_direct_draft_payload(raw)
        expected = dict(raw)
        expected["physical_boat.build_year"] = {"assertion_kind": "VALUE_ASSERTION", "value": 2005}
        assert payload.to_wire_dict() == expected

    def test_roundtrip_preserves_unknown_build_year(self) -> None:
        payload = parse_owner_direct_draft_payload(
            {"physical_boat.build_year": {"assertion_kind": "UNKNOWN"}}
        )
        assert payload.to_wire_dict() == {"physical_boat.build_year": {"assertion_kind": "UNKNOWN"}}

    def test_amount_serialized_as_string_not_float(self) -> None:
        payload = parse_owner_direct_draft_payload(
            {
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "100.10",
            }
        )
        wire = payload.to_wire_dict()
        assert isinstance(wire["listing_offer.asking_price_amount"], str)
        assert wire["listing_offer.asking_price_amount"] == "100.10"
