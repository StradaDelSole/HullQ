"""Canonical CurrentPublicEligibility resolution — SLICE-0069.

The one production application entry point resolving
`hullq.domain.current_public_eligibility.evaluate_current_public_eligibility`
against real persisted state for one exact NativeListing, at an explicit
*as_of* freshness boundary.

Reused identically by the public exact-listing read model
(`hullq.application.public_listing_read`) and both accepted Direct Search
paths (`hullq.application.inventory_search`,
`hullq.application.native_inventory_query`) so "ACTIVE != current-public" and
D29 admission can never silently diverge between those surfaces (contract
§16: "must reuse one current-public eligibility function/service"). Also
reused by the Broker Workspace inventory read
(`hullq.application.broker_inventory_read`) to render structured ACTIVE-but-
suppressed reasons (contract §17) without a second, independently
maintained definition of current-public truth.

This module never mutates lifecycle/freshness/offer/claim/media state --
resolving eligibility here is always a pure read, and a SUPPRESSED result
never implies any lifecycle rewrite (contract §12).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hullq.application.native_listing_freshness import resolve_current_freshness
from hullq.domain.current_public_eligibility import (
    CurrentPublicCoverState,
    CurrentPublicEligibilityFacts,
    CurrentPublicEligibilityResult,
    evaluate_current_public_eligibility,
)
from hullq.domain.market_identity import MarketEpisodeId, NativeListingId, PhysicalBoatId
from hullq.domain.publication_readiness import CoverState
from hullq.persistence.broker_identity import fetch_marketplace_organization
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim
from hullq.persistence.publication_readiness import resolve_cover_state_and_image_presence

__all__ = ["resolve_current_public_eligibility"]

_COVER_STATE_MAP: dict[CoverState, CurrentPublicCoverState] = {
    CoverState.VALID: CurrentPublicCoverState.VALID,
    CoverState.MISSING: CurrentPublicCoverState.MISSING,
    CoverState.INVALID: CurrentPublicCoverState.INVALID,
}


def resolve_current_public_eligibility(
    conn: Any, native_listing_id: NativeListingId, *, as_of: datetime
) -> CurrentPublicEligibilityResult | None:
    """Resolve canonical CurrentPublicEligibility for *native_listing_id*, or
    `None` when the NativeListing itself does not exist.

    `None` is a distinct "no such listing" outcome -- every caller deciding
    public/current-market readability already has a real NativeListingId
    candidate before reaching this function (contract §13: a genuinely
    missing listing is a caller-level non-enumerating concern, decided
    exactly like the existing `fetch_lifecycle_state`-first pattern in
    `hullq.application.public_listing_read.get_public_listing_read_model`).
    """
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None:
        return None

    lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    assert lifecycle_state is not None

    freshness = resolve_current_freshness(conn, native_listing_id, as_of=as_of)

    organization = fetch_marketplace_organization(conn, listing_record.publishing_organization_id)

    market_episode_id_value: str | None = (
        listing_record.listing.market_episode_id.value
        if listing_record.listing.market_episode_id is not None
        else None
    )
    market_episode_exists = False
    physical_boat_exists = False
    physical_boat_id: PhysicalBoatId | None = None
    if market_episode_id_value is not None:
        market_episode_record = fetch_market_episode(conn, MarketEpisodeId(market_episode_id_value))
        if market_episode_record is not None:
            market_episode_exists = True
            physical_boat_id = market_episode_record.market_episode.physical_boat_id
            physical_boat_exists = fetch_physical_boat(conn, physical_boat_id) is not None

    offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
    offer = offer_record.offer if offer_record is not None else None

    physical_boat_claim = None
    if physical_boat_exists:
        assert physical_boat_id is not None
        claim_record = fetch_current_physical_boat_claim(
            conn, physical_boat_id, listing_record.publishing_organization_id
        )
        physical_boat_claim = claim_record.claims if claim_record is not None else None

    has_public_usable_image, cover_state = resolve_cover_state_and_image_presence(
        conn, native_listing_id
    )

    facts = CurrentPublicEligibilityFacts(
        native_listing_id_value=native_listing_id.value,
        lifecycle_state=lifecycle_state,
        freshness_status=freshness.status,
        organization_exists=organization is not None,
        organization_publishing_eligibility=(
            organization.publishing_eligibility if organization is not None else None
        ),
        market_episode_id_present=market_episode_id_value is not None,
        market_episode_exists=market_episode_exists,
        physical_boat_exists=physical_boat_exists,
        offer=offer,
        physical_boat_claim=physical_boat_claim,
        has_public_usable_image=has_public_usable_image,
        cover_state=_COVER_STATE_MAP[cover_state],
    )
    return evaluate_current_public_eligibility(facts)
