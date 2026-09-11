"""Structural/typed loading of the SLICE-0050 operator claim-recording input.

One versioned JSON file is the accepted operator-assisted input (SLICE-0050
§13). It is structurally and typed validated (against
``fixtures/slice_0050/physical_boat_claim_request.schema.v0.1.json``) before
any accepted domain object is constructed. Schema validation is deliberately
shallow: it only pins JSON shape/type/enum-membership. Cross-field domain
semantics -- a `VALUE_ASSERTION` requiring a non-null claim value, a
positive finite `loa_length`/`draft`, brand/model non-blank -- are enforced
by the accepted `hullq.domain.physical_boat_claims` constructors themselves,
the same constructors `hullq.persistence.physical_boat_claims` uses; this
loader never re-implements or loosens that validation, and never invents a
placeholder value for a field the input omitted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import jsonschema

from hullq.domain.market_identity import NativeListingId
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
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)

__all__ = [
    "SCHEMA_PATH",
    "PhysicalBoatClaimRequest",
    "PhysicalBoatClaimRequestValidationError",
    "load_physical_boat_claim_request",
    "parse_physical_boat_claim_request",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "fixtures" / "slice_0050" / "physical_boat_claim_request.schema.v0.1.json"


class PhysicalBoatClaimRequestValidationError(ValueError):
    """*input* failed structural/typed schema validation or domain construction.

    Raised before any persistence operation runs; the caller (the operator
    CLI) must report this and stop -- never guess a corrected value.
    """


@dataclass(frozen=True)
class PhysicalBoatClaimRequest:
    """Exact, explicit operator-supplied inputs for one claim-write attempt."""

    account_id: AccountId
    organization: MarketplaceOrganization
    membership: OrganizationMembership
    native_listing_id: NativeListingId
    claim_revision_id: PhysicalBoatClaimRevisionId
    expected_current_claim_revision_id: PhysicalBoatClaimRevisionId | None
    claims: PhysicalBoatClaimSnapshot


def _load_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema


def _decimal_claim_value(data: dict[str, Any]) -> Decimal | None:
    raw_value = data.get("value")
    if raw_value is None:
        return None
    try:
        return Decimal(raw_value)
    except InvalidOperation as exc:
        raise PhysicalBoatClaimRequestValidationError(
            f"claim value is not a valid decimal string: {raw_value!r}"
        ) from exc


def _loa_length_claim(data: dict[str, Any] | None) -> LoaLengthClaim | None:
    if data is None:
        return None
    return LoaLengthClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]), value=_decimal_claim_value(data)
    )


def _draft_claim(data: dict[str, Any] | None) -> DraftClaim | None:
    if data is None:
        return None
    return DraftClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]), value=_decimal_claim_value(data)
    )


def _keel_configuration_claim(data: dict[str, Any] | None) -> KeelConfigurationClaim | None:
    if data is None:
        return None
    raw_value = data.get("value")
    return KeelConfigurationClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]),
        value=KeelConfiguration(raw_value) if raw_value is not None else None,
    )


def _rudder_configuration_claim(data: dict[str, Any] | None) -> RudderConfigurationClaim | None:
    if data is None:
        return None
    raw_value = data.get("value")
    return RudderConfigurationClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]),
        value=RudderConfiguration(raw_value) if raw_value is not None else None,
    )


def _claim_snapshot(data: dict[str, Any]) -> PhysicalBoatClaimSnapshot:
    build_year_data = data["build_year"]
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim=data["marketed_brand_claim"],
        model_designation_claim=data["model_designation_claim"],
        build_year=BuildYearClaim(
            assertion_kind=AssertionKind(build_year_data["assertion_kind"]),
            value=build_year_data.get("value"),
        ),
        loa_length=_loa_length_claim(data.get("loa_length")),
        draft=_draft_claim(data.get("draft")),
        keel_configuration=_keel_configuration_claim(data.get("keel_configuration")),
        rudder_configuration=_rudder_configuration_claim(data.get("rudder_configuration")),
    )


def parse_physical_boat_claim_request(data: dict[str, Any]) -> PhysicalBoatClaimRequest:
    """Validate *data* against the accepted schema, then construct a `PhysicalBoatClaimRequest`.

    Raises `PhysicalBoatClaimRequestValidationError` for a schema violation
    or a domain-constructor rejection (e.g. a non-positive `loa_length`) --
    never silently coerces or drops an offending field.
    """
    try:
        jsonschema.validate(instance=data, schema=_load_schema())
    except jsonschema.ValidationError as exc:
        raise PhysicalBoatClaimRequestValidationError(
            f"schema validation failed: {exc.message}"
        ) from exc

    org_data = data["organization"]
    membership_data = data["membership"]
    expected_current = data.get("expected_current_claim_revision_id")

    try:
        return PhysicalBoatClaimRequest(
            account_id=AccountId(data["account_id"]),
            organization=MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_data["id"]),
                professional_category=ProfessionalCategory(org_data["professional_category"]),
                publishing_eligibility=OrganizationPublishingEligibility(
                    org_data["publishing_eligibility"]
                ),
            ),
            membership=OrganizationMembership(
                id=OrganizationMembershipId(membership_data["id"]),
                account_id=AccountId(membership_data["account_id"]),
                organization_id=MarketplaceOrganizationId(membership_data["organization_id"]),
                roles=frozenset(MembershipRole(role) for role in membership_data["roles"]),
                state=MembershipState(membership_data["state"]),
            ),
            native_listing_id=NativeListingId(data["native_listing_id"]),
            claim_revision_id=PhysicalBoatClaimRevisionId(data["claim_revision_id"]),
            expected_current_claim_revision_id=(
                PhysicalBoatClaimRevisionId(expected_current)
                if expected_current is not None
                else None
            ),
            claims=_claim_snapshot(data["claims"]),
        )
    except (TypeError, ValueError) as exc:
        raise PhysicalBoatClaimRequestValidationError(
            f"domain construction rejected input: {exc}"
        ) from exc


def load_physical_boat_claim_request(path: str | Path) -> PhysicalBoatClaimRequest:
    """Read, schema-validate and construct one `PhysicalBoatClaimRequest` from *path*."""
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise PhysicalBoatClaimRequestValidationError(
            f"could not read claim request file {path!r}: {exc}"
        ) from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise PhysicalBoatClaimRequestValidationError(
            f"claim request file {path!r} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise PhysicalBoatClaimRequestValidationError(
            f"claim request file {path!r} must contain a single JSON object"
        )

    return parse_physical_boat_claim_request(data)
