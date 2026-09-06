"""Structural/typed loading of the SLICE-0048 operator intake JSON file — §4.3.

One versioned JSON file is the accepted intake input. It is structurally and
typed validated (against
``fixtures/slice_0048/listing_intake_request.schema.v0.1.json``) before any
accepted domain object is constructed. Schema validation is deliberately
shallow: it only pins JSON shape/type/enum-membership. Cross-field domain
semantics -- a `VALUE_ASSERTION` requiring a non-null claim value, `AMOUNT`
requiring `asking_price_amount`/`currency`, a positive finite price -- are
enforced by the accepted `hullq.domain` constructors themselves, the same
constructors every other durable-creation path already uses; this loader
never re-implements or loosens that validation, and never invents a
placeholder value for a field the input omitted.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import jsonschema

from hullq.application.listing_intake import ListingIntakeRequest
from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisodeId,
    NativeListingId,
    PhysicalBoatId,
)
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
    "ListingIntakeRequestValidationError",
    "load_listing_intake_request",
    "parse_listing_intake_request",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "fixtures" / "slice_0048" / "listing_intake_request.schema.v0.1.json"


class ListingIntakeRequestValidationError(ValueError):
    """*input* failed structural/typed schema validation or domain construction.

    Raised before any persistence operation runs; the caller (the operator
    CLI) must report this and stop -- never guess a corrected value.
    """


def _load_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema


def _optional_location_region_claim(data: dict[str, Any] | None) -> LocationRegionClaim | None:
    if data is None:
        return None
    return LocationRegionClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]), value=data.get("value")
    )


def _optional_broker_summary_claim(data: dict[str, Any] | None) -> BrokerSummaryClaim | None:
    if data is None:
        return None
    return BrokerSummaryClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]), value=data.get("value")
    )


def _optional_known_history_claim(data: dict[str, Any] | None) -> KnownHistoryNarrativeClaim | None:
    if data is None:
        return None
    return KnownHistoryNarrativeClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]), value=data.get("value")
    )


def _optional_vat_claim(data: dict[str, Any] | None) -> VatTaxStatusClaim | None:
    if data is None:
        return None
    raw_value = data.get("value")
    return VatTaxStatusClaim(
        assertion_kind=AssertionKind(data["assertion_kind"]),
        value=VatTaxStatusValue(raw_value) if raw_value is not None else None,
    )


def _offer_snapshot(data: dict[str, Any]) -> NativeListingOfferSnapshot:
    raw_amount = data.get("asking_price_amount")
    try:
        amount = Decimal(raw_amount) if raw_amount is not None else None
    except InvalidOperation as exc:
        raise ListingIntakeRequestValidationError(
            f"offer.asking_price_amount is not a valid decimal string: {raw_amount!r}"
        ) from exc

    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode(data["asking_price_mode"]),
        location_country=data["location_country"],
        broker_description=data["broker_description"],
        asking_price_amount=amount,
        currency=data.get("currency"),
        location_region=_optional_location_region_claim(data.get("location_region")),
        broker_summary=_optional_broker_summary_claim(data.get("broker_summary")),
        known_history_narrative=_optional_known_history_claim(data.get("known_history_narrative")),
        vat_tax_status_claim=_optional_vat_claim(data.get("vat_tax_status_claim")),
    )


def parse_listing_intake_request(data: dict[str, Any]) -> ListingIntakeRequest:
    """Validate *data* against the accepted schema, then construct a `ListingIntakeRequest`.

    Raises `ListingIntakeRequestValidationError` for a schema violation or a
    domain-constructor rejection (e.g. an inconsistent assertion-kind/value
    pairing) -- never silently coerces or drops an offending field.
    """
    try:
        jsonschema.validate(instance=data, schema=_load_schema())
    except jsonschema.ValidationError as exc:
        raise ListingIntakeRequestValidationError(
            f"schema validation failed: {exc.message}"
        ) from exc

    org_data = data["organization"]
    membership_data = data["membership"]

    try:
        return ListingIntakeRequest(
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
            physical_boat_id=PhysicalBoatId(data["physical_boat_id"]),
            boat_design_ref=(
                BoatDesignRef(data["boat_design_ref"])
                if data.get("boat_design_ref") is not None
                else None
            ),
            market_episode_id=MarketEpisodeId(data["market_episode_id"]),
            native_listing_id=NativeListingId(data["native_listing_id"]),
            broker_listing_reference=data.get("broker_listing_reference"),
            offer_revision_id=NativeListingOfferRevisionId(data["offer_revision_id"]),
            offer=_offer_snapshot(data["offer"]),
        )
    except (TypeError, ValueError) as exc:
        raise ListingIntakeRequestValidationError(
            f"domain construction rejected input: {exc}"
        ) from exc


def load_listing_intake_request(path: str | Path) -> ListingIntakeRequest:
    """Read, schema-validate and construct one `ListingIntakeRequest` from *path*."""
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ListingIntakeRequestValidationError(
            f"could not read intake file {path!r}: {exc}"
        ) from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ListingIntakeRequestValidationError(
            f"intake file {path!r} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ListingIntakeRequestValidationError(
            f"intake file {path!r} must contain a single JSON object"
        )

    return parse_listing_intake_request(data)
