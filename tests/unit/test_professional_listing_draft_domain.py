"""Unit tests for hullq.domain.professional_listing_draft — SLICE-0061.

Covers the pure `ProfessionalListingDraftId` identity boundary, the
professional-only `broker_listing_reference` field, and that the shared
nine-common-key validator is the identical primitive owner-direct uses (no
second inconsistent copy, contract §4.1) -- independent of any persistence/
network concern.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.domain import owner_direct_draft, professional_listing_draft
from hullq.domain.listing_draft_payload import InvalidListingDraftPayloadError
from hullq.domain.owner_direct_draft import OwnerDirectListingDraftId
from hullq.domain.professional_listing_draft import (
    ProfessionalListingDraftId,
    parse_professional_listing_draft_request,
)

_owner_direct_parse = owner_direct_draft.parse_owner_direct_draft_payload
_professional_common_parse = professional_listing_draft.parse_listing_draft_payload


class TestProfessionalListingDraftId:
    def test_valid_value_constructs(self) -> None:
        assert ProfessionalListingDraftId("draft-1").value == "draft-1"

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            ProfessionalListingDraftId("")

    def test_distinct_type_from_owner_direct_id_despite_equal_raw_text(self) -> None:
        """Contract §2: equal raw text across identity kinds must not make
        them interchangeable."""
        professional = ProfessionalListingDraftId("same-value")
        owner_direct = OwnerDirectListingDraftId("same-value")
        assert professional.value == owner_direct.value
        assert type(professional) is not type(owner_direct)
        assert professional != owner_direct


class TestSharedCommonFieldParserIsOneImplementation:
    def test_professional_and_owner_direct_import_the_identical_parser(self) -> None:
        """Contract §4.1: no second inconsistent copy of the nine common
        field validators -- both channels call the exact same function
        object."""
        assert _professional_common_parse is _owner_direct_parse


class TestParseProfessionalListingDraftRequestEmptyAndUnknown:
    def test_empty_dict_is_valid(self) -> None:
        request = parse_professional_listing_draft_request({})
        assert request.common.to_wire_dict() == {}
        assert request.broker_listing_reference is None

    def test_non_dict_rejected(self) -> None:
        with pytest.raises(InvalidListingDraftPayloadError):
            parse_professional_listing_draft_request(["not", "a", "dict"])

    def test_unknown_key_rejected(self) -> None:
        with pytest.raises(InvalidListingDraftPayloadError):
            parse_professional_listing_draft_request({"physical_boat.hull_material": "GRP"})


class TestParseProfessionalListingDraftRequestBrokerListingReference:
    def test_absent_is_none(self) -> None:
        request = parse_professional_listing_draft_request({})
        assert request.broker_listing_reference is None

    def test_valid_trimmed_string_accepted(self) -> None:
        request = parse_professional_listing_draft_request(
            {"broker_listing_reference": "  REF-001  "}
        )
        assert request.broker_listing_reference == "REF-001"

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(InvalidListingDraftPayloadError):
            parse_professional_listing_draft_request({"broker_listing_reference": "   "})

    def test_non_string_rejected(self) -> None:
        with pytest.raises(InvalidListingDraftPayloadError):
            parse_professional_listing_draft_request({"broker_listing_reference": 123})

    def test_never_part_of_the_nine_common_keys(self) -> None:
        """Contract §5: broker_listing_reference is professional-only
        metadata, not one of the nine channel-neutral common draft keys."""
        with pytest.raises(InvalidListingDraftPayloadError):
            _professional_common_parse({"broker_listing_reference": "REF-001"})


class TestParseProfessionalListingDraftRequestCommonFieldsUnchanged:
    def test_all_nine_common_fields_accepted_alongside_broker_reference(self) -> None:
        raw = {
            "broker_listing_reference": "REF-002",
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
        request = parse_professional_listing_draft_request(raw)
        assert request.broker_listing_reference == "REF-002"
        assert request.common.marketed_brand_claim == "Beneteau"
        assert request.common.asking_price_amount == Decimal("129000.50")
        expected_common = dict(raw)
        expected_common.pop("broker_listing_reference")
        assert request.common.to_wire_dict() == expected_common

    def test_poa_with_amount_still_rejected(self) -> None:
        with pytest.raises(InvalidListingDraftPayloadError):
            parse_professional_listing_draft_request(
                {
                    "listing_offer.asking_price_mode": "POA",
                    "listing_offer.asking_price_amount": "100",
                }
            )
