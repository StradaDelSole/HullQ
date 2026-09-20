"""Channel-neutral common listing-draft payload — SLICE-0054/0061.

The nine accepted draft-input keys (`specs/OWNER_DIRECT_LISTING_WORKSPACE_
CONTRACT.v0.1.md` §6, `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`
§4) are channel-neutral: owner-direct and professional Organization drafts
both use the exact identical bounded key set, value shapes and conditional
POA/amount rule. This module is the one shared parser/serializer both
channels import, so the semantics can never drift into two inconsistent
copies (professional contract §4.1).

This module is pure and persistence-neutral -- no database, no FastAPI, no
Account/Organization/session lookup, and no opinion about which identity
kind (`OwnerDirectListingDraftId` vs `ProfessionalListingDraftId`) owns a
given payload.

The nine keys are *draft input keys only*: a value accepted here is never
treated as resolved/canonical marketplace truth.

`asking_price_amount` is accepted and re-serialized as a decimal-literal
*string*, never a JSON number: mirrors the accepted
`hullq.search.draft_max_request` technique of parsing straight into
`decimal.Decimal` from a narrow regex-validated string so no binary-float
conversion ever touches a price value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

__all__ = [
    "ACCEPTED_DRAFT_PAYLOAD_KEYS",
    "EMPTY_LISTING_DRAFT_PAYLOAD",
    "AskingPriceMode",
    "InvalidListingDraftPayloadError",
    "ListingDraftPayload",
    "parse_listing_draft_payload",
    "require_trimmed_nonempty_string",
]


class AskingPriceMode(StrEnum):
    AMOUNT = "AMOUNT"
    POA = "POA"


class InvalidListingDraftPayloadError(ValueError):
    """Raised for an unknown key, an invalid value shape or a violated
    conditional rule. Callers must fail the whole request closed (400) with
    zero mutation -- never partially accept a payload.
    """


#: The finite accepted draft-input key set. Any other key fails closed;
#: there is no forward-compatible "ignore unknown key" mode.
ACCEPTED_DRAFT_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "physical_boat.marketed_brand_claim",
        "physical_boat.model_designation_claim",
        "physical_boat.build_year",
        "physical_boat.boat_name",
        "listing_offer.asking_price_mode",
        "listing_offer.asking_price_amount",
        "listing_offer.currency",
        "listing_offer.location_country",
        "listing_offer.location_region",
    }
)

# Mirrors hullq.search.draft_max_request's narrow lexical envelope: plain
# fixed-point digits only, no sign/comma/exponent/whitespace, so no
# scientific-notation or locale-dependent string ever reaches Decimal().
_PRICE_AMOUNT_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")


@dataclass(frozen=True)
class ListingDraftPayload:
    """The bounded v0.1 draft payload. Every field is optional."""

    marketed_brand_claim: str | None = None
    model_designation_claim: str | None = None
    build_year: int | None = None
    boat_name: str | None = None
    asking_price_mode: AskingPriceMode | None = None
    asking_price_amount: Decimal | None = None
    currency: str | None = None
    location_country: str | None = None
    location_region: str | None = None

    def to_wire_dict(self) -> dict[str, Any]:
        """Render only the present fields, keyed by their dotted names."""
        result: dict[str, Any] = {}
        if self.marketed_brand_claim is not None:
            result["physical_boat.marketed_brand_claim"] = self.marketed_brand_claim
        if self.model_designation_claim is not None:
            result["physical_boat.model_designation_claim"] = self.model_designation_claim
        if self.build_year is not None:
            result["physical_boat.build_year"] = self.build_year
        if self.boat_name is not None:
            result["physical_boat.boat_name"] = self.boat_name
        if self.asking_price_mode is not None:
            result["listing_offer.asking_price_mode"] = self.asking_price_mode.value
        if self.asking_price_amount is not None:
            result["listing_offer.asking_price_amount"] = str(self.asking_price_amount)
        if self.currency is not None:
            result["listing_offer.currency"] = self.currency
        if self.location_country is not None:
            result["listing_offer.location_country"] = self.location_country
        if self.location_region is not None:
            result["listing_offer.location_region"] = self.location_region
        return result


EMPTY_LISTING_DRAFT_PAYLOAD = ListingDraftPayload()


def require_trimmed_nonempty_string(value: Any, field_label: str) -> str:
    """A "trimmed non-empty string" field -- the accepted *value*, not merely
    the non-emptiness check, so the returned (and therefore persisted/
    serialized) string is always the stripped form.

    Exported so a caller adding its own channel-specific string field (e.g.
    professional `broker_listing_reference`) reuses the identical trim/
    non-empty rule rather than a second inconsistent copy of it.
    """
    if not isinstance(value, str):
        raise InvalidListingDraftPayloadError(
            f"{field_label} must be a string, got {type(value).__name__}"
        )
    trimmed = value.strip()
    if not trimmed:
        raise InvalidListingDraftPayloadError(f"{field_label} must be non-empty when provided")
    return trimmed


def _parse_build_year(value: Any) -> int:
    # bool is an int subclass in Python; explicitly excluded.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidListingDraftPayloadError(
            f"physical_boat.build_year must be an integer, got {type(value).__name__}"
        )
    return value


def _parse_asking_price_mode(value: Any) -> AskingPriceMode:
    if not isinstance(value, str) or value not in {m.value for m in AskingPriceMode}:
        raise InvalidListingDraftPayloadError(
            "listing_offer.asking_price_mode must be exactly 'AMOUNT' or 'POA'"
        )
    return AskingPriceMode(value)


def _parse_asking_price_amount(value: Any) -> Decimal:
    if not isinstance(value, str) or not _PRICE_AMOUNT_PATTERN.fullmatch(value):
        raise InvalidListingDraftPayloadError(
            "listing_offer.asking_price_amount must be a plain positive decimal string"
        )
    amount = Decimal(value)
    if not amount.is_finite() or amount <= 0:
        raise InvalidListingDraftPayloadError(
            "listing_offer.asking_price_amount must be a positive finite decimal"
        )
    return amount


def _parse_currency(value: Any) -> str:
    if not isinstance(value, str) or not _CURRENCY_PATTERN.fullmatch(value):
        raise InvalidListingDraftPayloadError(
            "listing_offer.currency must be exactly three uppercase ASCII letters"
        )
    return value


def _parse_country(value: Any) -> str:
    if not isinstance(value, str) or not _COUNTRY_PATTERN.fullmatch(value):
        raise InvalidListingDraftPayloadError(
            "listing_offer.location_country must be exactly two uppercase ASCII letters"
        )
    return value


def parse_listing_draft_payload(raw: Any) -> ListingDraftPayload:
    """Validate *raw* against the bounded common-key shape, or raise.

    An empty dict is valid (an empty newly-created draft is valid). Unknown
    keys fail closed -- there is no lenient/ignore mode.
    """
    if not isinstance(raw, dict):
        raise InvalidListingDraftPayloadError(
            f"draft payload must be a JSON object, got {type(raw).__name__}"
        )
    unknown = set(raw) - ACCEPTED_DRAFT_PAYLOAD_KEYS
    if unknown:
        raise InvalidListingDraftPayloadError(f"unknown draft payload key(s): {sorted(unknown)}")

    marketed_brand_claim = (
        require_trimmed_nonempty_string(
            raw["physical_boat.marketed_brand_claim"], "physical_boat.marketed_brand_claim"
        )
        if "physical_boat.marketed_brand_claim" in raw
        else None
    )
    model_designation_claim = (
        require_trimmed_nonempty_string(
            raw["physical_boat.model_designation_claim"], "physical_boat.model_designation_claim"
        )
        if "physical_boat.model_designation_claim" in raw
        else None
    )
    build_year = (
        _parse_build_year(raw["physical_boat.build_year"])
        if "physical_boat.build_year" in raw
        else None
    )
    boat_name = (
        require_trimmed_nonempty_string(raw["physical_boat.boat_name"], "physical_boat.boat_name")
        if "physical_boat.boat_name" in raw
        else None
    )
    asking_price_mode = (
        _parse_asking_price_mode(raw["listing_offer.asking_price_mode"])
        if "listing_offer.asking_price_mode" in raw
        else None
    )
    asking_price_amount = (
        _parse_asking_price_amount(raw["listing_offer.asking_price_amount"])
        if "listing_offer.asking_price_amount" in raw
        else None
    )
    currency = (
        _parse_currency(raw["listing_offer.currency"]) if "listing_offer.currency" in raw else None
    )
    location_country = (
        _parse_country(raw["listing_offer.location_country"])
        if "listing_offer.location_country" in raw
        else None
    )
    location_region = (
        require_trimmed_nonempty_string(
            raw["listing_offer.location_region"], "listing_offer.location_region"
        )
        if "listing_offer.location_region" in raw
        else None
    )

    if asking_price_mode is AskingPriceMode.POA and asking_price_amount is not None:
        raise InvalidListingDraftPayloadError(
            "listing_offer.asking_price_amount must be absent when asking_price_mode is 'POA'"
        )

    return ListingDraftPayload(
        marketed_brand_claim=marketed_brand_claim,
        model_designation_claim=model_designation_claim,
        build_year=build_year,
        boat_name=boat_name,
        asking_price_mode=asking_price_mode,
        asking_price_amount=asking_price_amount,
        currency=currency,
        location_country=location_country,
        location_region=location_region,
    )
