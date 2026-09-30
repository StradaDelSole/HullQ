"""Pure JSON request parsing for SLICE-0072 broker inventory offer/claim edits.

Parses one flat JSON object into the exact bounded
`hullq.domain.native_listing_offer.NativeListingOfferSnapshot` /
`hullq.domain.physical_boat_claims.PhysicalBoatClaimSnapshot` shape those
modules already accept, plus the caller-supplied
`expected_current_revision_id` optimistic-concurrency token
(`specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md` §5). Every field key
mirrors the identical dotted `listing_offer.*`/`physical_boat.*` wire naming
already accepted by `hullq.domain.listing_draft_payload`/
`hullq.domain.professional_listing_draft`, extended here to the complete
marketplace offer/claim field sets those pre-market draft parsers
deliberately only cover a subset of.

This module is pure and persistence-neutral -- no database, no FastAPI, no
Account/Organization/session lookup. It never accepts a caller-supplied
Organization/NativeListing/PhysicalBoat identity, actor authorization or
current-public truth (contract §14); those remain the caller's concern.
Every malformed input -- an unknown key, a wrong-shaped value or a rejected
domain-level assertion-kind/value pairing -- raises
`InvalidInventoryEditRequestError`, never a partial/best-effort parse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

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
from hullq.domain.physical_boat_claims import (
    BoatNameClaim,
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

__all__ = [
    "ClaimEditRequest",
    "InvalidInventoryEditRequestError",
    "OfferEditRequest",
    "parse_native_listing_offer_edit_request",
    "parse_physical_boat_claim_edit_request",
]


class InvalidInventoryEditRequestError(ValueError):
    """Raised for an unknown key, an invalid value shape or a rejected
    domain-level assertion-kind/value pairing. Callers must fail the whole
    request closed (400) with zero mutation -- never a partial accept.
    """


_DECIMAL_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")

_EXPECTED_REVISION_KEY = "expected_current_revision_id"
_REVISION_ID_KEY = "revision_id"


def _require_expected_revision_id(raw_body: dict[str, Any]) -> str | None:
    if _EXPECTED_REVISION_KEY not in raw_body:
        raise InvalidInventoryEditRequestError(f"{_EXPECTED_REVISION_KEY} is required")
    raw = raw_body[_EXPECTED_REVISION_KEY]
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw:
        raise InvalidInventoryEditRequestError(
            f"{_EXPECTED_REVISION_KEY} must be a non-empty string or null"
        )
    return raw


def _require_revision_id(raw_body: dict[str, Any]) -> str:
    # Contract §5: "a retry-safe client/server operation/revision identity
    # must preserve the existing persistence semantics" -- mirrors
    # `hullq.application.broker_inventory_lifecycle`'s identical
    # client-supplied `confirmation_id` pattern for SLICE-0064 reconfirm.
    # This new revision's own identity is minted by the browser, not this
    # server, so a genuine network-level retry of the identical request
    # resolves deterministically (ALREADY_EXISTS for identical content,
    # CONFLICT for a collision with different content) instead of always
    # minting a fresh id that can never be recognized as the same attempt.
    if _REVISION_ID_KEY not in raw_body:
        raise InvalidInventoryEditRequestError(f"{_REVISION_ID_KEY} is required")
    raw = raw_body[_REVISION_ID_KEY]
    if not isinstance(raw, str) or not raw:
        raise InvalidInventoryEditRequestError(f"{_REVISION_ID_KEY} must be a non-empty string")
    return raw


def _require_trimmed_nonempty_string(value: Any, field_label: str) -> str:
    if not isinstance(value, str):
        raise InvalidInventoryEditRequestError(f"{field_label} must be a string, got {type(value).__name__}")
    trimmed = value.strip()
    if not trimmed:
        raise InvalidInventoryEditRequestError(f"{field_label} must be non-empty when provided")
    return trimmed


def _assertion_object(raw: Any, label: str) -> tuple[str, Any]:
    if not isinstance(raw, dict):
        raise InvalidInventoryEditRequestError(
            f"{label} must be an object with an assertion_kind member"
        )
    extra = set(raw) - {"assertion_kind", "value"}
    if extra:
        raise InvalidInventoryEditRequestError(f"{label} has unknown member(s): {sorted(extra)}")
    if "assertion_kind" not in raw or not isinstance(raw["assertion_kind"], str):
        raise InvalidInventoryEditRequestError(
            f"{label}.assertion_kind is required and must be a string"
        )
    return raw["assertion_kind"], raw.get("value")


def _assertion_kind(raw_kind: str, label: str) -> AssertionKind:
    try:
        return AssertionKind(raw_kind)
    except ValueError as exc:
        raise InvalidInventoryEditRequestError(
            f"{label}.assertion_kind is not a recognized assertion kind"
        ) from exc


def _decimal_meters_value(raw_value: Any, label: str) -> Decimal:
    if not isinstance(raw_value, str) or not _DECIMAL_PATTERN.fullmatch(raw_value):
        raise InvalidInventoryEditRequestError(f"{label}.value must be a plain positive decimal string")
    return Decimal(raw_value)


def _construct(ctor: Any, label: str) -> Any:
    try:
        return ctor()
    except (ValueError, TypeError) as exc:
        raise InvalidInventoryEditRequestError(f"{label}: {exc}") from exc


# ---------------------------------------------------------------------------
# NativeListing offer edit
# ---------------------------------------------------------------------------

_OFFER_KEYS = frozenset(
    {
        _EXPECTED_REVISION_KEY,
        _REVISION_ID_KEY,
        "listing_offer.asking_price_mode",
        "listing_offer.asking_price_amount",
        "listing_offer.currency",
        "listing_offer.location_country",
        "listing_offer.broker_description",
        "listing_offer.location_region",
        "listing_offer.broker_summary",
        "listing_offer.known_history_narrative",
        "listing_offer.vat_tax_status_claim",
    }
)


@dataclass(frozen=True)
class OfferEditRequest:
    """One parsed NativeListing offer edit request (contract §3/§4)."""

    revision_id: NativeListingOfferRevisionId
    expected_current_revision_id: NativeListingOfferRevisionId | None
    offer: NativeListingOfferSnapshot


def _parse_location_region(raw: Any) -> LocationRegionClaim:
    raw_kind, raw_value = _assertion_object(raw, "listing_offer.location_region")
    kind = _assertion_kind(raw_kind, "listing_offer.location_region")
    return _construct(
        lambda: LocationRegionClaim(assertion_kind=kind, value=raw_value),
        "listing_offer.location_region",
    )


def _parse_broker_summary(raw: Any) -> BrokerSummaryClaim:
    raw_kind, raw_value = _assertion_object(raw, "listing_offer.broker_summary")
    kind = _assertion_kind(raw_kind, "listing_offer.broker_summary")
    return _construct(
        lambda: BrokerSummaryClaim(assertion_kind=kind, value=raw_value),
        "listing_offer.broker_summary",
    )


def _parse_known_history_narrative(raw: Any) -> KnownHistoryNarrativeClaim:
    raw_kind, raw_value = _assertion_object(raw, "listing_offer.known_history_narrative")
    kind = _assertion_kind(raw_kind, "listing_offer.known_history_narrative")
    return _construct(
        lambda: KnownHistoryNarrativeClaim(assertion_kind=kind, value=raw_value),
        "listing_offer.known_history_narrative",
    )


def _parse_vat_tax_status_claim(raw: Any) -> VatTaxStatusClaim:
    raw_kind, raw_value = _assertion_object(raw, "listing_offer.vat_tax_status_claim")
    kind = _assertion_kind(raw_kind, "listing_offer.vat_tax_status_claim")
    value: VatTaxStatusValue | None = None
    if kind is AssertionKind.VALUE_ASSERTION:
        if not isinstance(raw_value, str) or raw_value not in {v.value for v in VatTaxStatusValue}:
            raise InvalidInventoryEditRequestError(
                "listing_offer.vat_tax_status_claim.value must be a recognized VAT/tax status value"
            )
        value = VatTaxStatusValue(raw_value)
    elif raw_value is not None:
        raise InvalidInventoryEditRequestError(
            "listing_offer.vat_tax_status_claim.value must be omitted/null when assertion_kind "
            f"is {kind.value}"
        )
    return _construct(
        lambda: VatTaxStatusClaim(assertion_kind=kind, value=value),
        "listing_offer.vat_tax_status_claim",
    )


def parse_native_listing_offer_edit_request(raw: Any) -> OfferEditRequest:
    """Validate *raw* against the bounded NativeListing offer edit request shape.

    `listing_offer.asking_price_mode`/`listing_offer.location_country`/
    `listing_offer.broker_description` are required -- mirroring
    `NativeListingOfferSnapshot`'s own required fields -- every other offer
    key is optional and, when present, an object carrying an explicit
    `assertion_kind`. Unknown keys fail closed.
    """
    if not isinstance(raw, dict):
        raise InvalidInventoryEditRequestError(
            f"offer edit request must be a JSON object, got {type(raw).__name__}"
        )
    unknown = set(raw) - _OFFER_KEYS
    if unknown:
        raise InvalidInventoryEditRequestError(f"unknown offer edit request key(s): {sorted(unknown)}")

    revision_id = NativeListingOfferRevisionId(_require_revision_id(raw))
    expected_raw = _require_expected_revision_id(raw)
    expected_current_revision_id = (
        NativeListingOfferRevisionId(expected_raw) if expected_raw is not None else None
    )

    if "listing_offer.asking_price_mode" not in raw:
        raise InvalidInventoryEditRequestError("listing_offer.asking_price_mode is required")
    raw_mode = raw["listing_offer.asking_price_mode"]
    if not isinstance(raw_mode, str) or raw_mode not in {m.value for m in AskingPriceMode}:
        raise InvalidInventoryEditRequestError(
            "listing_offer.asking_price_mode must be exactly 'AMOUNT' or 'POA'"
        )
    mode = AskingPriceMode(raw_mode)

    asking_price_amount: Decimal | None = None
    if "listing_offer.asking_price_amount" in raw:
        asking_price_amount = _decimal_meters_value(
            raw["listing_offer.asking_price_amount"], "listing_offer.asking_price_amount"
        )
    currency: str | None = None
    if "listing_offer.currency" in raw:
        raw_currency = raw["listing_offer.currency"]
        if not isinstance(raw_currency, str) or not _CURRENCY_PATTERN.fullmatch(raw_currency):
            raise InvalidInventoryEditRequestError(
                "listing_offer.currency must be exactly three uppercase ASCII letters"
            )
        currency = raw_currency

    if "listing_offer.location_country" not in raw:
        raise InvalidInventoryEditRequestError("listing_offer.location_country is required")
    raw_country = raw["listing_offer.location_country"]
    if not isinstance(raw_country, str) or not _COUNTRY_PATTERN.fullmatch(raw_country):
        raise InvalidInventoryEditRequestError(
            "listing_offer.location_country must be exactly two uppercase ASCII letters"
        )

    if "listing_offer.broker_description" not in raw:
        raise InvalidInventoryEditRequestError("listing_offer.broker_description is required")
    broker_description = _require_trimmed_nonempty_string(
        raw["listing_offer.broker_description"], "listing_offer.broker_description"
    )

    location_region = (
        _parse_location_region(raw["listing_offer.location_region"])
        if "listing_offer.location_region" in raw
        else None
    )
    broker_summary = (
        _parse_broker_summary(raw["listing_offer.broker_summary"])
        if "listing_offer.broker_summary" in raw
        else None
    )
    known_history_narrative = (
        _parse_known_history_narrative(raw["listing_offer.known_history_narrative"])
        if "listing_offer.known_history_narrative" in raw
        else None
    )
    vat_tax_status_claim = (
        _parse_vat_tax_status_claim(raw["listing_offer.vat_tax_status_claim"])
        if "listing_offer.vat_tax_status_claim" in raw
        else None
    )

    offer = _construct(
        lambda: NativeListingOfferSnapshot(
            asking_price_mode=mode,
            location_country=raw_country,
            broker_description=broker_description,
            asking_price_amount=asking_price_amount,
            currency=currency,
            location_region=location_region,
            broker_summary=broker_summary,
            known_history_narrative=known_history_narrative,
            vat_tax_status_claim=vat_tax_status_claim,
        ),
        "listing_offer",
    )
    return OfferEditRequest(
        revision_id=revision_id, expected_current_revision_id=expected_current_revision_id, offer=offer
    )


# ---------------------------------------------------------------------------
# PhysicalBoat claim edit
# ---------------------------------------------------------------------------

_CLAIM_KEYS = frozenset(
    {
        _EXPECTED_REVISION_KEY,
        _REVISION_ID_KEY,
        "physical_boat.marketed_brand_claim",
        "physical_boat.model_designation_claim",
        "physical_boat.build_year",
        "physical_boat.loa_length",
        "physical_boat.draft",
        "physical_boat.keel_configuration",
        "physical_boat.rudder_configuration",
        "physical_boat.boat_name",
    }
)


@dataclass(frozen=True)
class ClaimEditRequest:
    """One parsed Organization PhysicalBoat claim edit request (contract §3/§4)."""

    revision_id: PhysicalBoatClaimRevisionId
    expected_current_revision_id: PhysicalBoatClaimRevisionId | None
    claims: PhysicalBoatClaimSnapshot


def _parse_build_year(raw: Any) -> BuildYearClaim:
    raw_kind, raw_value = _assertion_object(raw, "physical_boat.build_year")
    kind = _assertion_kind(raw_kind, "physical_boat.build_year")
    return _construct(
        lambda: BuildYearClaim(assertion_kind=kind, value=raw_value), "physical_boat.build_year"
    )


def _parse_loa_length(raw: Any) -> LoaLengthClaim:
    raw_kind, raw_value = _assertion_object(raw, "physical_boat.loa_length")
    kind = _assertion_kind(raw_kind, "physical_boat.loa_length")
    value: Decimal | None = None
    if kind is AssertionKind.VALUE_ASSERTION:
        value = _decimal_meters_value(raw_value, "physical_boat.loa_length")
    elif raw_value is not None:
        raise InvalidInventoryEditRequestError(
            f"physical_boat.loa_length.value must be omitted/null when assertion_kind is {kind.value}"
        )
    return _construct(
        lambda: LoaLengthClaim(assertion_kind=kind, value=value), "physical_boat.loa_length"
    )


def _parse_draft(raw: Any) -> DraftClaim:
    raw_kind, raw_value = _assertion_object(raw, "physical_boat.draft")
    kind = _assertion_kind(raw_kind, "physical_boat.draft")
    value: Decimal | None = None
    if kind is AssertionKind.VALUE_ASSERTION:
        value = _decimal_meters_value(raw_value, "physical_boat.draft")
    elif raw_value is not None:
        raise InvalidInventoryEditRequestError(
            f"physical_boat.draft.value must be omitted/null when assertion_kind is {kind.value}"
        )
    return _construct(lambda: DraftClaim(assertion_kind=kind, value=value), "physical_boat.draft")


def _parse_keel_configuration(raw: Any) -> KeelConfigurationClaim:
    raw_kind, raw_value = _assertion_object(raw, "physical_boat.keel_configuration")
    kind = _assertion_kind(raw_kind, "physical_boat.keel_configuration")
    value: KeelConfiguration | None = None
    if kind is AssertionKind.VALUE_ASSERTION:
        if not isinstance(raw_value, str) or raw_value not in {k.value for k in KeelConfiguration}:
            raise InvalidInventoryEditRequestError(
                "physical_boat.keel_configuration.value must be a recognized keel configuration"
            )
        value = KeelConfiguration(raw_value)
    elif raw_value is not None:
        raise InvalidInventoryEditRequestError(
            "physical_boat.keel_configuration.value must be omitted/null when assertion_kind is "
            f"{kind.value}"
        )
    return _construct(
        lambda: KeelConfigurationClaim(assertion_kind=kind, value=value),
        "physical_boat.keel_configuration",
    )


def _parse_rudder_configuration(raw: Any) -> RudderConfigurationClaim:
    raw_kind, raw_value = _assertion_object(raw, "physical_boat.rudder_configuration")
    kind = _assertion_kind(raw_kind, "physical_boat.rudder_configuration")
    value: RudderConfiguration | None = None
    if kind is AssertionKind.VALUE_ASSERTION:
        if not isinstance(raw_value, str) or raw_value not in {k.value for k in RudderConfiguration}:
            raise InvalidInventoryEditRequestError(
                "physical_boat.rudder_configuration.value must be a recognized rudder configuration"
            )
        value = RudderConfiguration(raw_value)
    elif raw_value is not None:
        raise InvalidInventoryEditRequestError(
            "physical_boat.rudder_configuration.value must be omitted/null when assertion_kind is "
            f"{kind.value}"
        )
    return _construct(
        lambda: RudderConfigurationClaim(assertion_kind=kind, value=value),
        "physical_boat.rudder_configuration",
    )


def _parse_boat_name(raw: Any) -> BoatNameClaim:
    raw_kind, raw_value = _assertion_object(raw, "physical_boat.boat_name")
    kind = _assertion_kind(raw_kind, "physical_boat.boat_name")
    return _construct(
        lambda: BoatNameClaim(assertion_kind=kind, value=raw_value), "physical_boat.boat_name"
    )


def parse_physical_boat_claim_edit_request(raw: Any) -> ClaimEditRequest:
    """Validate *raw* against the bounded PhysicalBoat claim edit request shape.

    `physical_boat.marketed_brand_claim`/`physical_boat.model_designation_claim`/
    `physical_boat.build_year` are required -- mirroring
    `PhysicalBoatClaimSnapshot`'s own required fields -- every other claim key
    is optional and, when present, an object carrying an explicit
    `assertion_kind`. Unknown keys fail closed. No BoatDesign/reference
    baseline value is ever consulted here (contract §3: "No design/
    configuration baseline value may silently become a concrete-yacht
    assertion") -- every field comes only from the caller-supplied request
    body.
    """
    if not isinstance(raw, dict):
        raise InvalidInventoryEditRequestError(
            f"claim edit request must be a JSON object, got {type(raw).__name__}"
        )
    unknown = set(raw) - _CLAIM_KEYS
    if unknown:
        raise InvalidInventoryEditRequestError(f"unknown claim edit request key(s): {sorted(unknown)}")

    revision_id = PhysicalBoatClaimRevisionId(_require_revision_id(raw))
    expected_raw = _require_expected_revision_id(raw)
    expected_current_revision_id = (
        PhysicalBoatClaimRevisionId(expected_raw) if expected_raw is not None else None
    )

    if "physical_boat.marketed_brand_claim" not in raw:
        raise InvalidInventoryEditRequestError("physical_boat.marketed_brand_claim is required")
    marketed_brand_claim = _require_trimmed_nonempty_string(
        raw["physical_boat.marketed_brand_claim"], "physical_boat.marketed_brand_claim"
    )

    if "physical_boat.model_designation_claim" not in raw:
        raise InvalidInventoryEditRequestError("physical_boat.model_designation_claim is required")
    model_designation_claim = _require_trimmed_nonempty_string(
        raw["physical_boat.model_designation_claim"], "physical_boat.model_designation_claim"
    )

    if "physical_boat.build_year" not in raw:
        raise InvalidInventoryEditRequestError("physical_boat.build_year is required")
    build_year = _parse_build_year(raw["physical_boat.build_year"])

    loa_length = (
        _parse_loa_length(raw["physical_boat.loa_length"])
        if "physical_boat.loa_length" in raw
        else None
    )
    draft = _parse_draft(raw["physical_boat.draft"]) if "physical_boat.draft" in raw else None
    keel_configuration = (
        _parse_keel_configuration(raw["physical_boat.keel_configuration"])
        if "physical_boat.keel_configuration" in raw
        else None
    )
    rudder_configuration = (
        _parse_rudder_configuration(raw["physical_boat.rudder_configuration"])
        if "physical_boat.rudder_configuration" in raw
        else None
    )
    boat_name = (
        _parse_boat_name(raw["physical_boat.boat_name"])
        if "physical_boat.boat_name" in raw
        else None
    )

    claims = _construct(
        lambda: PhysicalBoatClaimSnapshot(
            marketed_brand_claim=marketed_brand_claim,
            model_designation_claim=model_designation_claim,
            build_year=build_year,
            loa_length=loa_length,
            draft=draft,
            keel_configuration=keel_configuration,
            rudder_configuration=rudder_configuration,
            boat_name=boat_name,
        ),
        "physical_boat",
    )
    return ClaimEditRequest(
        revision_id=revision_id,
        expected_current_revision_id=expected_current_revision_id,
        claims=claims,
    )
