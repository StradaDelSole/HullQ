"""Operator-assisted first-visible-listing intake orchestration — SLICE-0048.

Drives the accepted SLICE-0043/0045/0046/0047 persistence operations in the
fixed order required by SLICE-0048 §4.1:

    1. create/reuse PhysicalBoat
    2. create/reuse MarketEpisode bound to that PhysicalBoat
    3. create/reuse authorized NativeListing already linked to that MarketEpisode
    4. create/reuse first offer revision with expected_current_revision_id = NONE
    5. only after all four stages succeed/idempotently match, emit a preview capability

This module does not wrap those self-committing persistence operations in a
fake aggregate transaction: each accepted operation already durably commits
its own outcome, so interruption after stage 1/2/3 may leave valid partial
durable state, and retrying the exact same input safely continues from it
(`CREATED`/`ALREADY_EXISTS` on each stage is reused, never re-derived from
scratch). It also never bypasses the real SLICE-0041 evaluator: stage 3/4
call the accepted persistence functions, which themselves call
`evaluate_native_listing_publishing_eligibility` -- no `authorized=true` or
equivalent shortcut exists here.

A different current offer head, a stale expectation, an identity conflict,
authorization denial or a missing referenced identity stops the
orchestration at that stage; no later stage runs and no preview token is
minted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_offer import (
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    OrganizationMembership,
)
from hullq.persistence.market_episode import (
    MarketEpisodeCreationResult,
    MarketEpisodeCreationStatus,
    create_market_episode,
)
from hullq.persistence.native_listing import (
    NativeListingCreationResult,
    NativeListingCreationStatus,
    create_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferWriteResult,
    NativeListingOfferWriteStatus,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import (
    PhysicalBoatCreationResult,
    PhysicalBoatCreationStatus,
    create_physical_boat,
)
from hullq.security.preview_token import DEFAULT_PREVIEW_TTL_SECONDS, mint_preview_token

__all__ = [
    "ListingIntakeOutcome",
    "ListingIntakeRequest",
    "ListingIntakeResult",
    "run_listing_intake",
]

_PHYSICAL_BOAT_SUCCESS = frozenset(
    {PhysicalBoatCreationStatus.CREATED, PhysicalBoatCreationStatus.ALREADY_EXISTS}
)
_MARKET_EPISODE_SUCCESS = frozenset(
    {MarketEpisodeCreationStatus.CREATED, MarketEpisodeCreationStatus.ALREADY_EXISTS}
)
_NATIVE_LISTING_SUCCESS = frozenset(
    {NativeListingCreationStatus.CREATED, NativeListingCreationStatus.ALREADY_EXISTS}
)


def _offer_stage_succeeded(
    offer_result: NativeListingOfferWriteResult,
    requested_revision_id: NativeListingOfferRevisionId,
) -> bool:
    """True iff stage 4 durably left *requested_revision_id* as the current head.

    `CREATED` always means exactly that. `ALREADY_EXISTS` is the accepted
    SLICE-0045 writer's response whenever *requested_revision_id* already
    exists with identical content, *regardless of whether it is still the
    current head* -- its `current_revision_id` then names the actual current
    head, which may since have advanced to a different, later revision (a
    concurrent accepted write can always do this between this intake's
    attempts). Treating that case as first-revision-only success would let a
    stale retry silently mint a preview token for a listing whose current
    offer is no longer the one this request describes, contradicting
    SLICE-0048 §4.1's requirement that a different current head stop the
    intake. Any other status (`REVISED`, `CONFLICT`, `DENIED`,
    `CROSS_ORGANIZATION_DENIED`, `NATIVE_LISTING_NOT_FOUND`) is never success
    here.
    """
    if offer_result.status is NativeListingOfferWriteStatus.CREATED:
        return True
    if offer_result.status is NativeListingOfferWriteStatus.ALREADY_EXISTS:
        return offer_result.current_revision_id == requested_revision_id
    return False


@dataclass(frozen=True)
class ListingIntakeRequest:
    """Exact, explicit operator-supplied inputs for one intake attempt.

    Every identity ID and the offer revision ID are caller-supplied and
    stable across retries -- this orchestration never mints a replacement
    identity on retry. `organization` and `membership` are the same
    explicit SLICE-0041 principal used for both stage 3 (NativeListing
    creation) and stage 4 (offer revision write).
    """

    account_id: AccountId
    organization: MarketplaceOrganization
    membership: OrganizationMembership
    physical_boat_id: PhysicalBoatId
    boat_design_ref: BoatDesignRef | None
    market_episode_id: MarketEpisodeId
    native_listing_id: NativeListingId
    broker_listing_reference: str | None
    offer_revision_id: NativeListingOfferRevisionId
    offer: NativeListingOfferSnapshot


class ListingIntakeOutcome(StrEnum):
    """Mechanically distinct overall outcomes. Never a bare boolean."""

    SUCCEEDED = "succeeded"
    PHYSICAL_BOAT_FAILED = "physical_boat_failed"
    MARKET_EPISODE_FAILED = "market_episode_failed"
    NATIVE_LISTING_FAILED = "native_listing_failed"
    OFFER_FAILED = "offer_failed"


@dataclass(frozen=True)
class ListingIntakeResult:
    """Stage-by-stage report of one intake attempt.

    Never claims an all-or-nothing rollback: each populated stage result
    reflects durably committed state (or a durably-nothing-written
    authorization/conflict outcome) independent of whether a later stage
    ran at all. `preview_token`/`preview_token_expires_at` are populated
    only when `outcome` is `SUCCEEDED`.
    """

    outcome: ListingIntakeOutcome
    physical_boat: PhysicalBoatCreationResult
    market_episode: MarketEpisodeCreationResult | None = None
    native_listing: NativeListingCreationResult | None = None
    offer: NativeListingOfferWriteResult | None = None
    preview_token: str | None = None
    preview_token_expires_at: datetime | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome is ListingIntakeOutcome.SUCCEEDED


def run_listing_intake(
    conn: Any,
    *,
    request: ListingIntakeRequest,
    preview_signing_secret: bytes,
    preview_ttl_seconds: int = DEFAULT_PREVIEW_TTL_SECONDS,
) -> ListingIntakeResult:
    """Run the fixed four-stage orchestration, then mint a preview token iff all succeed.

    Each stage calls the real accepted persistence operation on *conn*; no
    stage is skipped, reordered or short-circuited by a caller-supplied
    authorization flag. Retrying with the exact same *request* is safe: a
    already-durably-committed stage resolves as its accepted `ALREADY_EXISTS`
    case and the orchestration continues from there.
    """
    physical_boat_result = create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=request.physical_boat_id, boat_design_ref=request.boat_design_ref
        ),
    )
    if physical_boat_result.status not in _PHYSICAL_BOAT_SUCCESS:
        return ListingIntakeResult(
            outcome=ListingIntakeOutcome.PHYSICAL_BOAT_FAILED,
            physical_boat=physical_boat_result,
        )

    market_episode_result = create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=request.market_episode_id, physical_boat_id=request.physical_boat_id
        ),
    )
    if market_episode_result.status not in _MARKET_EPISODE_SUCCESS:
        return ListingIntakeResult(
            outcome=ListingIntakeOutcome.MARKET_EPISODE_FAILED,
            physical_boat=physical_boat_result,
            market_episode=market_episode_result,
        )

    native_listing_result = create_native_listing(
        conn,
        account_id=request.account_id,
        candidate_organization=request.organization,
        membership=request.membership,
        listing=NativeListing(
            id=request.native_listing_id, market_episode_id=request.market_episode_id
        ),
        broker_listing_reference=request.broker_listing_reference,
    )
    if native_listing_result.status not in _NATIVE_LISTING_SUCCESS:
        return ListingIntakeResult(
            outcome=ListingIntakeOutcome.NATIVE_LISTING_FAILED,
            physical_boat=physical_boat_result,
            market_episode=market_episode_result,
            native_listing=native_listing_result,
        )

    offer_result = write_native_listing_offer_revision(
        conn,
        account_id=request.account_id,
        candidate_organization=request.organization,
        membership=request.membership,
        native_listing_id=request.native_listing_id,
        revision_id=request.offer_revision_id,
        expected_current_revision_id=None,
        offer=request.offer,
    )
    if not _offer_stage_succeeded(offer_result, request.offer_revision_id):
        return ListingIntakeResult(
            outcome=ListingIntakeOutcome.OFFER_FAILED,
            physical_boat=physical_boat_result,
            market_episode=market_episode_result,
            native_listing=native_listing_result,
            offer=offer_result,
        )

    minted = mint_preview_token(
        request.native_listing_id,
        secret=preview_signing_secret,
        ttl_seconds=preview_ttl_seconds,
    )
    return ListingIntakeResult(
        outcome=ListingIntakeOutcome.SUCCEEDED,
        physical_boat=physical_boat_result,
        market_episode=market_episode_result,
        native_listing=native_listing_result,
        offer=offer_result,
        preview_token=minted.token,
        preview_token_expires_at=minted.expires_at,
    )
