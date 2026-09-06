"""Unit tests for SLICE-0048 operator intake JSON structural/typed loading.

Covers the accepted example fixture, schema-shape violations and domain-
constructor rejections (e.g. an inconsistent assertion-kind/value pairing) --
all of which must raise `ListingIntakeRequestValidationError` before any
persistence operation could ever run.
"""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from hullq.application.listing_intake_loader import (
    SCHEMA_PATH,
    ListingIntakeRequestValidationError,
    load_listing_intake_request,
    parse_listing_intake_request,
)
from hullq.domain.native_listing_offer import AskingPriceMode, AssertionKind
from hullq.domain.publishing_eligibility import MembershipRole, MembershipState

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_FIXTURE = REPO_ROOT / "fixtures" / "slice_0048" / "listing_intake_example.v0.1.json"


def _example_data() -> dict[str, Any]:
    return json.loads(EXAMPLE_FIXTURE.read_text(encoding="utf-8"))


def test_schema_file_exists_and_is_valid_json() -> None:
    assert SCHEMA_PATH.exists()
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_example_fixture_loads_from_disk() -> None:
    request = load_listing_intake_request(EXAMPLE_FIXTURE)
    assert request.native_listing_id.value == "NL-0048-DEMO-001"
    assert request.offer.asking_price_mode is AskingPriceMode.AMOUNT
    assert request.offer.asking_price_amount == Decimal("125000.00")
    assert request.membership.state is MembershipState.ACTIVE
    assert MembershipRole.PUBLISHER in request.membership.roles


def test_example_fixture_parses_from_dict_directly() -> None:
    request = parse_listing_intake_request(_example_data())
    assert request.account_id.value == "ACC-0048-DEMO"


def test_omitted_optional_claims_stay_none() -> None:
    data = _example_data()
    del data["offer"]["location_region"]
    del data["offer"]["broker_summary"]
    request = parse_listing_intake_request(data)
    assert request.offer.location_region is None
    assert request.offer.broker_summary is None


def test_explicit_unknown_claim_is_distinct_from_omission() -> None:
    data = _example_data()
    data["offer"]["location_region"] = {"assertion_kind": "UNKNOWN"}
    request = parse_listing_intake_request(data)
    assert request.offer.location_region is not None
    assert request.offer.location_region.assertion_kind is AssertionKind.UNKNOWN


def test_missing_required_field_is_rejected() -> None:
    data = _example_data()
    del data["native_listing_id"]
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_unknown_additional_property_is_rejected() -> None:
    data = _example_data()
    data["unexpected_extra_field"] = "nope"
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_invalid_professional_category_enum_is_rejected() -> None:
    data = _example_data()
    data["organization"]["professional_category"] = "NOT_A_REAL_CATEGORY"
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_invalid_country_code_shape_is_rejected() -> None:
    data = _example_data()
    data["offer"]["location_country"] = "France"
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_value_assertion_with_null_value_is_rejected_by_domain_constructor() -> None:
    """Schema alone permits this shape; the domain claim constructor must still fail closed."""
    data = _example_data()
    data["offer"]["location_region"] = {"assertion_kind": "VALUE_ASSERTION", "value": None}
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_amount_mode_without_currency_is_rejected_by_domain_constructor() -> None:
    data = _example_data()
    del data["offer"]["currency"]
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_poa_mode_with_amount_present_is_rejected_by_domain_constructor() -> None:
    data = _example_data()
    data["offer"]["asking_price_mode"] = "POA"
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_invalid_decimal_string_amount_is_rejected() -> None:
    data = _example_data()
    data["offer"]["asking_price_amount"] = "not-a-number"
    with pytest.raises(ListingIntakeRequestValidationError):
        parse_listing_intake_request(data)


def test_missing_file_is_rejected() -> None:
    with pytest.raises(ListingIntakeRequestValidationError):
        load_listing_intake_request(REPO_ROOT / "fixtures" / "slice_0048" / "does_not_exist.json")


def test_non_json_file_is_rejected(tmp_path: Path) -> None:
    bad_file = tmp_path / "not_json.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ListingIntakeRequestValidationError):
        load_listing_intake_request(bad_file)


def test_json_array_instead_of_object_is_rejected(tmp_path: Path) -> None:
    array_file = tmp_path / "array.json"
    array_file.write_text("[]", encoding="utf-8")
    with pytest.raises(ListingIntakeRequestValidationError):
        load_listing_intake_request(array_file)


def test_deep_copy_of_example_is_independent_between_tests() -> None:
    # Guards against accidental cross-test mutation of the shared fixture dict.
    a = _example_data()
    b = copy.deepcopy(a)
    a["offer"]["broker_description"] = "mutated"
    assert b["offer"]["broker_description"] != "mutated"
