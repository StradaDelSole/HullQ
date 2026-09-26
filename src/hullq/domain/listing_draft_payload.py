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
    "BuildYearAssertionKind",
    "BuildYearResponse",
    "InvalidListingDraftPayloadError",
    "ListingDraftPayload",
    "parse_listing_draft_payload",
    "require_trimmed_nonempty_string",
]


class AskingPriceMode(StrEnum):
    AMOUNT = "AMOUNT"
    POA = "POA"


class BuildYearAssertionKind(StrEnum):
    """SLICE-0066: `physical_boat.build_year`'s draft-layer required-response
    kinds (`specs/LISTING_ASSERTION_RESPONSE_CONTRACT.v0.1.md` §3). Deliberately
    a small, field-local vocabulary rather than a reuse of the marketplace
    `hullq.domain.native_listing_offer.AssertionKind` -- the draft layer must
    stay independent of marketplace claim types (contract §6/§10: draft save
    creates zero PhysicalBoat/claim state)."""

    VALUE_ASSERTION = "VALUE_ASSERTION"
    UNKNOWN = "UNKNOWN"


class InvalidListingDraftPayloadError(ValueError):
    """Raised for an unknown key, an invalid value shape or a violated
    conditional rule. Callers must fail the whole request closed (400) with
    zero mutation -- never partially accept a payload.
    """


@dataclass(frozen=True)
class BuildYearResponse:
    """SLICE-0066: `physical_boat.build_year`'s canonical draft-layer
    required-response value (`LISTING_ASSERTION_RESPONSE_CONTRACT.v0.1.md`
    §3/§4). A `ListingDraftPayload.build_year` of `None` remains omission
    (contract §3.1) -- this type only ever exists for an explicit answer, so
    omitted/UNKNOWN/VALUE_ASSERTION stay three mechanically distinct states.
    """

    assertion_kind: BuildYearAssertionKind
    value: int | None = None

    def __post_init__(self) -> None:
        if self.assertion_kind is BuildYearAssertionKind.VALUE_ASSERTION:
            # bool is a subclass of int in Python; excluded explicitly, same
            # rule as the pre-0066 legacy bare-integer check below.
            if isinstance(self.value, bool) or not isinstance(self.value, int):
                raise InvalidListingDraftPayloadError(
                    "physical_boat.build_year.value must be an integer when "
                    f"assertion_kind is VALUE_ASSERTION, got {type(self.value).__name__}"
                )
        elif self.value is not None:
            raise InvalidListingDraftPayloadError(
                "physical_boat.build_year must not include a value when "
                f"assertion_kind is {self.assertion_kind.value}"
            )

    def to_wire_value(self) -> dict[str, Any]:
        """Canonical structured wire form (contract §5): always the object
        shape, even for a value ingested via the legacy bare-integer form."""
        if self.assertion_kind is BuildYearAssertionKind.VALUE_ASSERTION:
            return {"assertion_kind": self.assertion_kind.value, "value": self.value}
        return {"assertion_kind": self.assertion_kind.value}


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
    build_year: BuildYearResponse | None = None
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
            result["physical_boat.build_year"] = self.build_year.to_wire_value()
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


_BUILD_YEAR_OBJECT_MEMBERS = frozenset({"assertion_kind", "value"})


def _parse_build_year_object(raw: dict[str, Any]) -> BuildYearResponse:
    """Strict canonical structured shape (contract §4): unknown members,
    a missing/invalid `assertion_kind`, a missing `value` under
    VALUE_ASSERTION and a present `value` (including explicit `null`) under
    UNKNOWN all fail closed."""
    extra = set(raw) - _BUILD_YEAR_OBJECT_MEMBERS
    if extra:
        raise InvalidListingDraftPayloadError(
            f"physical_boat.build_year has unknown member(s): {sorted(extra)}"
        )
    if "assertion_kind" not in raw:
        raise InvalidListingDraftPayloadError("physical_boat.build_year.assertion_kind is required")
    raw_kind = raw["assertion_kind"]
    if not isinstance(raw_kind, str) or raw_kind not in {k.value for k in BuildYearAssertionKind}:
        raise InvalidListingDraftPayloadError(
            "physical_boat.build_year.assertion_kind must be exactly 'VALUE_ASSERTION' or 'UNKNOWN'"
        )
    kind = BuildYearAssertionKind(raw_kind)
    if kind is BuildYearAssertionKind.VALUE_ASSERTION:
        if "value" not in raw:
            raise InvalidListingDraftPayloadError(
                "physical_boat.build_year.value is required when assertion_kind is VALUE_ASSERTION"
            )
        return BuildYearResponse(kind, raw["value"])
    # UNKNOWN forbids `value`, including an explicit `"value": null` (contract §4).
    if "value" in raw:
        raise InvalidListingDraftPayloadError(
            "physical_boat.build_year must not include a value when assertion_kind is UNKNOWN"
        )
    return BuildYearResponse(kind)


def _parse_build_year(value: Any) -> BuildYearResponse:
    """Accepts either the canonical structured object or the legacy bare
    integer (contract §5), normalizing the legacy form to VALUE_ASSERTION.
    `bool`/`float`/`str`/`None` (including JSON null) all fail closed --
    omission is represented only by the wire key's absence, never by a
    present `null` value."""
    if isinstance(value, dict):
        return _parse_build_year_object(value)
    # bool is an int subclass in Python; explicitly excluded, same as the
    # canonical VALUE_ASSERTION.value rule.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidListingDraftPayloadError(
            "physical_boat.build_year must be an integer or a structured "
            f"assertion-response object, got {type(value).__name__}"
        )
    return BuildYearResponse(BuildYearAssertionKind.VALUE_ASSERTION, value)


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
