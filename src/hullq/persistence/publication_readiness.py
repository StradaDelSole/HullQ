"""Canonical PublicationReadiness fact-gathering — SLICE-0069.

Given an already-known NativeListing identity/lifecycle/episode-link plus the
caller-resolved actor eligibility decision, resolve every remaining fact
`hullq.domain.publication_readiness.evaluate_publication_readiness` needs from
current persisted truth, using only the already-accepted persistence fetch
functions -- never a second parallel completeness query.

Reused by both the advisory Broker Workspace preflight read (a plain,
unlocked `conn`) and the authoritative in-transaction publish re-evaluation
(`hullq.persistence.native_listing_lifecycle.publish_native_listing`, called
after that module has already locked the target `native_listings` row `FOR
UPDATE`) -- contract §9's "same result vocabulary and requirement rules" is a
literal single-function-call fact, not merely a documented intent.

Concurrency (contract §18): every fact this module reads -- current offer
head, current PhysicalBoat claim head, gallery placements/cover -- is written
only by a mutation that itself first locks the *same* `native_listings` row
this module's publish caller already holds `FOR UPDATE`
(`hullq.persistence.native_listing_offer.write_native_listing_offer_revision_row`,
`hullq.persistence.physical_boat_claims.write_physical_boat_claim_revision_row`,
and every `hullq.persistence.media_gallery` mutation that can affect
readiness -- `remove_placement`/`set_cover`/`retire_media_asset` all lock
`native_listings` via `_lock_listing_lifecycle`, even for a `DRAFT` listing,
since `retire_media_asset` locks every affected listing's row regardless of
its current lifecycle state before deciding whether the ACTIVE-only
invariant even applies). So the single already-held `native_listings` row
lock is sufficient to serialize every concurrent readiness-changing writer
against the reads below -- no second lock is required or taken here.
"""

from __future__ import annotations

from typing import Any

from hullq.domain.market_identity import MarketEpisodeId, NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publication_readiness import (
    CoverState,
    PublicationReadinessFacts,
    PublicationReadinessResult,
    evaluate_publication_readiness,
)
from hullq.domain.publishing_eligibility import (
    MarketplaceOrganizationId,
    PublishingEligibilityDecision,
)
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.media_gallery import fetch_gallery_state
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim

__all__ = ["resolve_cover_state_and_image_presence", "resolve_publication_readiness"]


def resolve_cover_state_and_image_presence(
    conn: Any, native_listing_id: NativeListingId
) -> tuple[bool, CoverState]:
    """Return `(has_public_usable_image, cover_state)` from current gallery truth
    (contract §7: media-eligibility rules shared identically by PublicationReadiness
    and CurrentPublicEligibility).
    """
    gallery = fetch_gallery_state(conn, native_listing_id)
    has_public_usable_image = any(
        placement.kind.value == "IMAGE"
        and placement.media_asset is not None
        and placement.media_asset.is_public_usable
        for placement in gallery.placements
    )
    if gallery.cover_placement_id is None:
        return has_public_usable_image, CoverState.MISSING

    cover_placement = next(
        (p for p in gallery.placements if p.media_placement_id == gallery.cover_placement_id),
        None,
    )
    if (
        cover_placement is None
        or cover_placement.kind.value != "IMAGE"
        or cover_placement.media_asset is None
        or not cover_placement.media_asset.is_public_usable
    ):
        return has_public_usable_image, CoverState.INVALID
    return has_public_usable_image, CoverState.VALID


def resolve_publication_readiness(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    publishing_organization_id: MarketplaceOrganizationId,
    publishing_eligibility: PublishingEligibilityDecision,
    lifecycle_state: NativeListingLifecycleState,
    market_episode_id_value: str | None,
) -> PublicationReadinessResult:
    """Resolve every remaining PublicationReadiness fact and evaluate.

    *lifecycle_state*, *market_episode_id_value* and *publishing_organization_id*
    are supplied by the caller (already read, typically under an existing row
    lock) rather than re-fetched here, so this module never issues a second,
    potentially inconsistent read of the exact row the caller already locked.
    """
    market_episode_exists = False
    physical_boat_exists = False
    physical_boat_id = None
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
            conn, physical_boat_id, publishing_organization_id
        )
        physical_boat_claim = claim_record.claims if claim_record is not None else None

    has_public_usable_image, cover_state = resolve_cover_state_and_image_presence(
        conn, native_listing_id
    )

    facts = PublicationReadinessFacts(
        native_listing_id_value=native_listing_id.value,
        publishing_eligibility=publishing_eligibility,
        lifecycle_state=lifecycle_state,
        market_episode_id_present=market_episode_id_value is not None,
        market_episode_exists=market_episode_exists,
        physical_boat_exists=physical_boat_exists,
        offer=offer,
        physical_boat_claim=physical_boat_claim,
        has_public_usable_image=has_public_usable_image,
        cover_state=cover_state,
    )
    return evaluate_publication_readiness(facts)
