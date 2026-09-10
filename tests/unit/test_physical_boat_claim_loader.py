"""Unit tests for SLICE-0050 operator claim-recording JSON structural/typed loading.

Covers the accepted example fixture, schema-shape violations and domain-
constructor rejections (e.g. a non-positive loa_length, an inconsistent
assertion-kind/value pairing) -- all of which must raise
`PhysicalBoatClaimRequestValidationError` before any persistence operation
could ever run.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from hullq.application.physical_boat_claim_loader import (
    SCHEMA_PATH,
    PhysicalBoatClaimRequestValidationError,
    load_physical_boat_claim_request,
    parse_physical_boat_claim_request,
)
from hullq.domain.physical_boat_claims import AssertionKind, KeelConfiguration
from hullq.domain.publishing_eligibility import MembershipRole, MembershipState

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_FIXTURE = REPO_ROOT / "fixtures" / "slice_0050" / "physical_boat_claim_example.v0.1.json"


def _example_data() -> dict[str, Any]:
    return json.loads(EXAMPLE_FIXTURE.read_text(encoding="utf-8"))


def test_schema_file_exists_and_is_valid_json() -> None:
    assert SCHEMA_PATH.exists()
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_example_fixture_loads_from_disk() -> None:
    request = load_physical_boat_claim_request(EXAMPLE_FIXTURE)
    assert request.native_listing_id.value == "NL-0050-DEMO-001"
    assert request.claims.marketed_brand_claim == "Beneteau"
    assert request.claims.build_year.value == 2021
    assert request.claims.loa_length is not None
    assert request.claims.loa_length.value == Decimal("9.14")
    assert request.claims.draft is not None
    assert request.claims.draft.assertion_kind is AssertionKind.UNKNOWN
    assert request.claims.keel_configuration is not None
    assert request.claims.keel_configuration.value is KeelConfiguration.FIN
    assert request.claims.rudder_configuration is None
    assert request.membership.state is MembershipState.ACTIVE
    assert MembershipRole.PUBLISHER in request.membership.roles
    assert request.expected_current_claim_revision_id is None


def test_example_fixture_parses_from_dict_directly() -> None:
    request = parse_physical_boat_claim_request(_example_data())
    assert request.account_id.value == "ACC-0050-DEMO"


def test_omitted_optional_claims_stay_none() -> None:
    data = _example_data()
    del data["claims"]["loa_length"]
    del data["claims"]["keel_configuration"]
    request = parse_physical_boat_claim_request(data)
    assert request.claims.loa_length is None
    assert request.claims.keel_configuration is None


def test_explicit_unknown_build_year_is_distinct_from_a_value_assertion() -> None:
    data = _example_data()
    data["claims"]["build_year"] = {"assertion_kind": "UNKNOWN"}
    request = parse_physical_boat_claim_request(data)
    assert request.claims.build_year.assertion_kind is AssertionKind.UNKNOWN
    assert request.claims.build_year.value is None


def test_expected_current_claim_revision_id_round_trips_when_present() -> None:
    data = _example_data()
    data["expected_current_claim_revision_id"] = "PBCREV-PREVIOUS-001"
    request = parse_physical_boat_claim_request(data)
    assert request.expected_current_claim_revision_id is not None
    assert request.expected_current_claim_revision_id.value == "PBCREV-PREVIOUS-001"


def test_missing_required_field_is_rejected() -> None:
    data = _example_data()
    del data["native_listing_id"]
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_unknown_additional_property_is_rejected() -> None:
    data = _example_data()
    data["unexpected_extra_field"] = "nope"
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_invalid_keel_configuration_enum_is_rejected() -> None:
    data = _example_data()
    data["claims"]["keel_configuration"] = {
        "assertion_kind": "VALUE_ASSERTION",
        "value": "NOT_A_REAL_KEEL_TYPE",
    }
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_blank_marketed_brand_claim_is_rejected_by_domain_constructor() -> None:
    """Schema alone permits a whitespace-only string; the domain constructor
    must still fail closed."""
    data = _example_data()
    data["claims"]["marketed_brand_claim"] = "   "
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_non_positive_loa_length_is_rejected_by_domain_constructor() -> None:
    data = _example_data()
    data["claims"]["loa_length"] = {"assertion_kind": "VALUE_ASSERTION", "value": "0"}
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_invalid_decimal_string_loa_length_is_rejected() -> None:
    data = _example_data()
    data["claims"]["loa_length"] = {"assertion_kind": "VALUE_ASSERTION", "value": "not-a-number"}
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_build_year_value_assertion_with_null_value_is_rejected_by_domain_constructor() -> None:
    data = _example_data()
    data["claims"]["build_year"] = {"assertion_kind": "VALUE_ASSERTION", "value": None}
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        parse_physical_boat_claim_request(data)


def test_missing_file_is_rejected() -> None:
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        load_physical_boat_claim_request("/does/not/exist.json")


def test_non_json_file_is_rejected(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json {{{", encoding="utf-8")
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        load_physical_boat_claim_request(bad_file)


def test_non_object_json_file_is_rejected(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(PhysicalBoatClaimRequestValidationError):
        load_physical_boat_claim_request(bad_file)
