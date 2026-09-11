"""First-visible-listing preview read model — SLICE-0048 §6.

Resolves a bearer preview token into the bounded, previewable projection
defined by SLICE-0048 §6.2/§6.3: only the accepted public `LISTING_OFFER`
fields plus the minimal attribution/disclosure metadata required for VAT/tax
wording (§6.4). This module contains the previewable-read predicate and the
read-model projection; it performs no HTTP concerns (status codes, headers)
so it can be reused unchanged by both the FastAPI route and tests.

`PREVIEWABLE != PUBLISHED`: persisted NativeListing existence alone never
makes a listing previewable. A valid token proves only capability
possession; the full chain -- NativeListing -> non-null MarketEpisode ->
existing PhysicalBoat -> explicit current LISTING_OFFER head -- must also
resolve, or this collapses to `None`, the same as an invalid/tampered/
expired token. This endpoint is therefore never a NativeListingId existence
oracle: every failure reason -- bad token, missing listing, unresolved
MarketEpisode, missing PhysicalBoat, no current offer -- looks identical to
the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
from hullq.domain.native_listing_offer import (
    BrokerSummaryClaim,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.security.preview_token import InvalidPreviewTokenError, verify_and_decode_preview_token

__all__ = [
    "PreviewReadModel",
    "get_preview_read_model",
    "resolve_previewable_listing",
]


@dataclass(frozen=True)
class PreviewReadModel:
    """The bounded, previewable projection of one NativeListing's current offer.

    Carries no creator Account identity, no full revision history, no
    internal hashes/transaction metadata, no inferred PhysicalBoat fact and
    no BoatDesign baseline-as-yacht-fact -- only the accepted nine-field
    `LISTING_OFFER` public projection plus the minimal VAT/tax attribution
    metadata required by SLICE-0048 §6.4.
    """

    offer: NativeListingOfferSnapshot
    publishing_organization_id: MarketplaceOrganizationId
    offer_recorded_at: datetime
    preview_expires_at: datetime

    def to_public_dict(self) -> dict[str, Any]:
        """Render the exact accepted public projection as a JSON-safe dict.

        `asking_price_amount` is serialized as a decimal string, never a
        binary float. Each optional claim field renders `None` when omitted
        (distinct from an explicit assertion) or `{"assertion_kind": ...,
        "value": ...}` when present -- omission and explicit UNKNOWN/
        NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED never collapse to the same
        shape.
        """
        offer = self.offer
        return {
            "asking_price_mode": offer.asking_price_mode.value,
            "asking_price_amount": (
                str(offer.asking_price_amount) if offer.asking_price_amount is not None else None
            ),
            "currency": offer.currency,
            "location_country": offer.location_country,
            "location_region": _claim_dict(offer.location_region),
            "broker_summary": _claim_dict(offer.broker_summary),
            "broker_description": offer.broker_description,
            "known_history_narrative": _claim_dict(offer.known_history_narrative),
            "vat_tax_status_claim": _vat_claim_dict(offer.vat_tax_status_claim),
            "publishing_organization_id": self.publishing_organization_id.value,
            "offer_recorded_at": self.offer_recorded_at.isoformat(),
            "hullq_vat_verification_status": "NONE",
            "preview_expires_at": self.preview_expires_at.isoformat(),
        }


def _claim_dict(
    claim: LocationRegionClaim | BrokerSummaryClaim | KnownHistoryNarrativeClaim | None,
) -> dict[str, Any] | None:
    if claim is None:
        return None
    return {"assertion_kind": claim.assertion_kind.value, "value": claim.value}


def _vat_claim_dict(claim: VatTaxStatusClaim | None) -> dict[str, Any] | None:
    if claim is None:
        return None
    return {
        "assertion_kind": claim.assertion_kind.value,
        "value": claim.value.value if claim.value is not None else None,
    }


@dataclass(frozen=True)
class _ResolvedOffer:
    """Chain-resolved offer state, before the token's own expiry is known.

    `physical_boat_id` (SLICE-0050) is carried here -- not exposed by either
    `PreviewReadModel` or `PreviewReadModel.to_public_dict` -- purely so
    `hullq.application.public_listing_read.get_public_listing_read_model`
    can resolve the publishing Organization's current PhysicalBoat claim
    snapshot without re-running this same chain resolution a second time.
    """

    offer: NativeListingOfferSnapshot
    publishing_organization_id: MarketplaceOrganizationId
    offer_recorded_at: datetime
    physical_boat_id: PhysicalBoatId


def resolve_previewable_listing(
    conn: Any, native_listing_id: NativeListingId
) -> _ResolvedOffer | None:
    """Apply the SLICE-0048 §6.2 previewable-read predicate against durable state.

    Returns `None` -- never raises for an ordinary unresolved chain -- unless
    every element of the required chain resolves:

        NativeListing exists
        AND NativeListing.market_episode_id is non-null
        AND referenced MarketEpisode exists
        AND referenced PhysicalBoat exists
        AND explicit current LISTING_OFFER head exists

    The current offer is always read via the explicit head relationship
    (`fetch_current_native_listing_offer`), never inferred from timestamp or
    row-insertion ordering. The returned value has no `preview_expires_at`:
    only `get_preview_read_model` knows the verified token's expiry claim.
    """
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None or listing_record.listing.market_episode_id is None:
        return None

    market_episode_record = fetch_market_episode(conn, listing_record.listing.market_episode_id)
    if market_episode_record is None:
        return None

    physical_boat_record = fetch_physical_boat(
        conn, market_episode_record.market_episode.physical_boat_id
    )
    if physical_boat_record is None:
        return None

    offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
    if offer_record is None:
        return None

    return _ResolvedOffer(
        offer=offer_record.offer,
        publishing_organization_id=offer_record.publishing_organization_id,
        offer_recorded_at=offer_record.recorded_at,
        physical_boat_id=physical_boat_record.physical_boat.id,
    )


def get_preview_read_model(
    conn: Any,
    preview_token: str,
    *,
    secret: bytes,
    now: datetime | None = None,
) -> PreviewReadModel | None:
    """Verify *preview_token* and resolve its previewable read model, or `None`.

    Collapses an invalid/tampered/expired token and an incomplete durable
    chain to the identical `None` result -- the FastAPI route (SLICE-0048
    §6) must render both as the same ordinary external not-found response.
    """
    try:
        claims = verify_and_decode_preview_token(preview_token, secret=secret, now=now)
    except InvalidPreviewTokenError:
        return None

    resolved = resolve_previewable_listing(conn, claims.native_listing_id)
    if resolved is None:
        return None

    return PreviewReadModel(
        offer=resolved.offer,
        publishing_organization_id=resolved.publishing_organization_id,
        offer_recorded_at=resolved.offer_recorded_at,
        preview_expires_at=claims.expires_at,
    )
