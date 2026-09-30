"""Pure unit tests for SLICE-0072's `hullq.domain.inventory_edit_request`
JSON request parsers -- no PostgreSQL/FastAPI dependency.

Covers `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md` §3/§4/§5's
bounded request shape: required vs. optional keys, unknown-key rejection,
the client-supplied `revision_id`/`expected_current_revision_id` idempotency
tokens, and the assertion-kind/value pairing rules each optional field
inherits from `hullq.domain.native_listing_offer`/
`hullq.domain.physical_boat_claims`.
"""

from __future__ import annotations

import pytest

from hullq.domain.inventory_edit_request import (
    InvalidInventoryEditRequestError,
    parse_native_listing_offer_edit_request,
    parse_physical_boat_claim_edit_request,
)
from hullq.domain.native_listing_offer import AskingPriceMode

_BASE_OFFER = {
    "revision_id": "REV-1",
    "expected_current_revision_id": "PREV-1",
    "listing_offer.asking_price_mode": "AMOUNT",
    "listing_offer.asking_price_amount": "125000.00",
    "listing_offer.currency": "EUR",
    "listing_offer.location_country": "FR",
    "listing_offer.broker_description": "A well-maintained cruising sloop.",
}

_BASE_CLAIM = {
    "revision_id": "CLAIM-1",
    "expected_current_revision_id": "PREV-CLAIM-1",
    "physical_boat.marketed_brand_claim": "Beneteau",
    "physical_boat.model_designation_claim": "Oceanis 30.1",
    "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2020},
}


class TestOfferEditRequest:
    def test_minimal_valid_request_parses(self) -> None:
        parsed = parse_native_listing_offer_edit_request(_BASE_OFFER)
        assert parsed.revision_id.value == "REV-1"
        assert parsed.expected_current_revision_id is not None
        assert parsed.expected_current_revision_id.value == "PREV-1"
        assert parsed.offer.asking_price_mode is AskingPriceMode.AMOUNT

    def test_null_expected_current_revision_id_means_first_revision(self) -> None:
        body = dict(_BASE_OFFER, expected_current_revision_id=None)
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.expected_current_revision_id is None

    def test_missing_revision_id_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_OFFER.items() if k != "revision_id"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_missing_expected_current_revision_id_key_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_OFFER.items() if k != "expected_current_revision_id"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_unknown_key_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.unknown_field": "x"})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_poa_mode_forbids_amount_and_currency(self) -> None:
        body = dict(_BASE_OFFER)
        body["listing_offer.asking_price_mode"] = "POA"
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_poa_mode_without_amount_or_currency_parses(self) -> None:
        body = {
            "revision_id": "REV-2",
            "expected_current_revision_id": None,
            "listing_offer.asking_price_mode": "POA",
            "listing_offer.location_country": "FR",
            "listing_offer.broker_description": "Contact for price.",
        }
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.asking_price_mode is AskingPriceMode.POA
        assert parsed.offer.asking_price_amount is None

    def test_not_a_json_object_is_invalid(self) -> None:
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(["not", "a", "dict"])

    def test_location_region_value_assertion_parses(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.location_region": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "Brittany",
                }
            },
        )
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.location_region is not None
        assert parsed.offer.location_region.value == "Brittany"

    def test_location_region_unknown_parses(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.location_region": {"assertion_kind": "UNKNOWN"}})
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.location_region is not None
        assert parsed.offer.location_region.value is None

    def test_location_region_disallowed_kind_is_invalid(self) -> None:
        # NOT_APPLICABLE is broker_summary's own allowed kind, not
        # location_region's -- must fail closed, never silently accepted.
        body = dict(
            _BASE_OFFER,
            **{"listing_offer.location_region": {"assertion_kind": "NOT_APPLICABLE"}},
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_vat_tax_status_claim_value_assertion_parses(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.vat_tax_status_claim": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "VAT_PAID",
                }
            },
        )
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.vat_tax_status_claim is not None

    def test_vat_tax_status_claim_unrecognized_value_is_invalid(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.vat_tax_status_claim": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "NOT_A_REAL_STATUS",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_assertion_object_with_extra_member_is_invalid(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.location_region": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "Brittany",
                    "extra": "nope",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_expected_current_revision_id_wrong_type_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, expected_current_revision_id=42)
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_expected_current_revision_id_empty_string_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, expected_current_revision_id="")
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_revision_id_empty_string_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, revision_id="")
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_revision_id_wrong_type_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, revision_id=123)
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_broker_description_non_string_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.broker_description": 123})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_broker_description_whitespace_only_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.broker_description": "   "})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_asking_price_mode_missing_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_OFFER.items() if k != "listing_offer.asking_price_mode"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_currency_invalid_format_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.currency": "eur"})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_location_country_missing_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_OFFER.items() if k != "listing_offer.location_country"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_location_country_invalid_format_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.location_country": "fra"})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_broker_description_missing_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_OFFER.items() if k != "listing_offer.broker_description"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_broker_summary_value_assertion_parses(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.broker_summary": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "Well maintained, single owner.",
                }
            },
        )
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.broker_summary is not None
        assert parsed.offer.broker_summary.value == "Well maintained, single owner."

    def test_broker_summary_not_applicable_parses(self) -> None:
        body = dict(
            _BASE_OFFER, **{"listing_offer.broker_summary": {"assertion_kind": "NOT_APPLICABLE"}}
        )
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.broker_summary is not None
        assert parsed.offer.broker_summary.value is None

    def test_known_history_narrative_value_assertion_parses(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.known_history_narrative": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "One prior owner, coastal use only.",
                }
            },
        )
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.known_history_narrative is not None

    def test_known_history_narrative_no_known_history_declared_parses(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.known_history_narrative": {
                    "assertion_kind": "NO_KNOWN_HISTORY_DECLARED"
                }
            },
        )
        parsed = parse_native_listing_offer_edit_request(body)
        assert parsed.offer.known_history_narrative is not None
        assert parsed.offer.known_history_narrative.value is None

    def test_vat_tax_status_claim_unknown_with_present_value_is_invalid(self) -> None:
        body = dict(
            _BASE_OFFER,
            **{
                "listing_offer.vat_tax_status_claim": {
                    "assertion_kind": "UNKNOWN",
                    "value": "VAT_PAID",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_assertion_object_not_a_dict_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.location_region": "Brittany"})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_assertion_object_missing_assertion_kind_is_invalid(self) -> None:
        body = dict(_BASE_OFFER, **{"listing_offer.location_region": {"value": "Brittany"}})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)

    def test_assertion_kind_unrecognized_string_is_invalid(self) -> None:
        body = dict(
            _BASE_OFFER, **{"listing_offer.location_region": {"assertion_kind": "BOGUS_KIND"}}
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_native_listing_offer_edit_request(body)


class TestClaimEditRequest:
    def test_minimal_valid_request_parses(self) -> None:
        parsed = parse_physical_boat_claim_edit_request(_BASE_CLAIM)
        assert parsed.revision_id.value == "CLAIM-1"
        assert parsed.claims.marketed_brand_claim == "Beneteau"
        assert parsed.claims.build_year.value == 2020

    def test_missing_revision_id_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_CLAIM.items() if k != "revision_id"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_missing_build_year_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_CLAIM.items() if k != "physical_boat.build_year"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_build_year_unknown_parses(self) -> None:
        body = dict(_BASE_CLAIM, **{"physical_boat.build_year": {"assertion_kind": "UNKNOWN"}})
        parsed = parse_physical_boat_claim_edit_request(body)
        assert parsed.claims.build_year.value is None

    def test_loa_length_value_assertion_parses_decimal_string(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{"physical_boat.loa_length": {"assertion_kind": "VALUE_ASSERTION", "value": "9.14"}},
        )
        parsed = parse_physical_boat_claim_edit_request(body)
        assert parsed.claims.loa_length is not None
        assert str(parsed.claims.loa_length.value) == "9.14"

    def test_loa_length_rejects_non_decimal_string(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{
                "physical_boat.loa_length": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "not-a-number",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_keel_configuration_value_assertion_parses(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{
                "physical_boat.keel_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "FIN",
                }
            },
        )
        parsed = parse_physical_boat_claim_edit_request(body)
        assert parsed.claims.keel_configuration is not None

    def test_keel_configuration_unrecognized_value_is_invalid(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{
                "physical_boat.keel_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "NOT_A_REAL_KEEL",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_boat_name_absent_parses(self) -> None:
        body = dict(_BASE_CLAIM, **{"physical_boat.boat_name": {"assertion_kind": "ABSENT"}})
        parsed = parse_physical_boat_claim_edit_request(body)
        assert parsed.claims.boat_name is not None
        assert parsed.claims.boat_name.value is None

    def test_boat_name_absent_with_disallowed_kind_for_other_field_is_invalid(self) -> None:
        # ABSENT is boat_name's own allowed kind, not build_year's -- must
        # fail closed, never silently accepted.
        body = dict(_BASE_CLAIM, **{"physical_boat.build_year": {"assertion_kind": "ABSENT"}})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_unknown_key_is_invalid(self) -> None:
        body = dict(_BASE_CLAIM, **{"physical_boat.unknown_field": "x"})
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_not_a_json_object_is_invalid(self) -> None:
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request("not a dict")

    def test_revision_id_empty_string_is_invalid(self) -> None:
        body = dict(_BASE_CLAIM, revision_id="")
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_marketed_brand_claim_missing_is_invalid(self) -> None:
        body = {k: v for k, v in _BASE_CLAIM.items() if k != "physical_boat.marketed_brand_claim"}
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_model_designation_claim_missing_is_invalid(self) -> None:
        body = {
            k: v for k, v in _BASE_CLAIM.items() if k != "physical_boat.model_designation_claim"
        }
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_draft_value_assertion_parses_decimal_string(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{"physical_boat.draft": {"assertion_kind": "VALUE_ASSERTION", "value": "1.45"}},
        )
        parsed = parse_physical_boat_claim_edit_request(body)
        assert parsed.claims.draft is not None
        assert str(parsed.claims.draft.value) == "1.45"

    def test_draft_unknown_with_present_value_is_invalid(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{"physical_boat.draft": {"assertion_kind": "UNKNOWN", "value": "1.45"}},
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_loa_length_unknown_with_present_value_is_invalid(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{"physical_boat.loa_length": {"assertion_kind": "UNKNOWN", "value": "9.14"}},
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_keel_configuration_unknown_with_present_value_is_invalid(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{"physical_boat.keel_configuration": {"assertion_kind": "UNKNOWN", "value": "FIN"}},
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_rudder_configuration_value_assertion_parses(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{
                "physical_boat.rudder_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "SPADE",
                }
            },
        )
        parsed = parse_physical_boat_claim_edit_request(body)
        assert parsed.claims.rudder_configuration is not None

    def test_rudder_configuration_unrecognized_value_is_invalid(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{
                "physical_boat.rudder_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "NOT_A_REAL_RUDDER",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)

    def test_rudder_configuration_unknown_with_present_value_is_invalid(self) -> None:
        body = dict(
            _BASE_CLAIM,
            **{
                "physical_boat.rudder_configuration": {
                    "assertion_kind": "UNKNOWN",
                    "value": "SPADE",
                }
            },
        )
        with pytest.raises(InvalidInventoryEditRequestError):
            parse_physical_boat_claim_edit_request(body)
