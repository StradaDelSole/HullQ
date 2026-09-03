"""Durable NativeListing creation/persistence — SLICE-0043.

Implements the accepted NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1: given an
explicit HullQ Account, candidate professional Organization and relevant
OrganizationMembership, evaluate the real accepted SLICE-0041 publishing-
eligibility boundary and, only when ALLOWED, durably create one immutable
NativeListing creation envelope in PostgreSQL.

This is durable creation, not public publication: no lifecycle/status field
is introduced. The persisted publishing Organization / creator Account are
always derived from the exact authorization inputs — never from a separately
supplied field — so a listing payload cannot spoof its principal. A DENIED
authorization decision writes zero rows; identical retries are idempotent; a
reused NativeListingId with a different immutable envelope fails closed as
CONFLICT rather than being overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import MarketEpisodeId, NativeListing, NativeListingId
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.fingerprint import fingerprint_dict

__all__ = [
    "NativeListingCreationResult",
    "NativeListingCreationStatus",
    "NativeListingRecord",
    "create_native_listing",
    "fetch_native_listing",
]


_INSERT_NATIVE_LISTING = """
INSERT INTO native_listings
    (native_listing_id, publishing_organization_id, created_by_account_id,
     market_episode_id, broker_listing_reference, content_hash)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (native_listing_id) DO NOTHING
"""
_SELECT_NATIVE_LISTING_HASH = (
    "SELECT content_hash FROM native_listings WHERE native_listing_id = %s"
)
_SELECT_NATIVE_LISTING = (
    "SELECT native_listing_id, publishing_organization_id, created_by_account_id, "
    "market_episode_id, broker_listing_reference, created_at "
    "FROM native_listings WHERE native_listing_id = %s"
)


class NativeListingCreationStatus(StrEnum):
    """Mechanically distinct creation outcomes. Never a bare boolean."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    DENIED = "denied"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class NativeListingCreationResult:
    """Deterministic result of one create_native_listing call.

    DENIED always carries the underlying SLICE-0041 denial reason. CONFLICT
    is never mislabeled as authorization denial and never carries a denial
    reason. No probability/trust score and no lifecycle/visibility status is
    encoded here.
    """

    status: NativeListingCreationStatus
    denial_reason: PublishingEligibilityReason | None = None

    def __post_init__(self) -> None:
        if self.status is NativeListingCreationStatus.DENIED and self.denial_reason is None:
            raise ValueError("A DENIED creation result must carry an explicit denial reason")
        if self.status is not NativeListingCreationStatus.DENIED and self.denial_reason is not None:
            raise ValueError("Only a DENIED creation result may carry a denial reason")


@dataclass(frozen=True)
class NativeListingRecord:
    """Exact typed readback of one persisted NativeListing creation envelope."""

    listing: NativeListing
    publishing_organization_id: MarketplaceOrganizationId
    created_by_account_id: AccountId
    broker_listing_reference: str | None
    created_at: datetime


def _validate_broker_listing_reference(value: str | None) -> None:
    if value is not None and not value.strip():
        raise ValueError("broker_listing_reference must be non-empty when provided")


def _fingerprint_envelope(
    publishing_organization_id: str,
    created_by_account_id: str,
    market_episode_id: str | None,
    broker_listing_reference: str | None,
) -> str:
    return fingerprint_dict(
        {
            "publishing_organization_id": publishing_organization_id,
            "created_by_account_id": created_by_account_id,
            "market_episode_id": market_episode_id,
            "broker_listing_reference": broker_listing_reference,
        }
    )


def create_native_listing(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    listing: NativeListing,
    broker_listing_reference: str | None = None,
) -> NativeListingCreationResult:
    """Evaluate real SLICE-0041 eligibility, then durably create *listing* iff ALLOWED.

    The persisted publishing Organization / creator Account are always
    *candidate_organization.id* / *account_id* — the exact principal
    evaluated by the authorization boundary — never a value independently
    supplied elsewhere. A DENIED decision touches the database not at all
    and writes zero rows.

    Race-safe: uses INSERT ... ON CONFLICT DO NOTHING followed by an exact
    content-hash comparison, rather than a check-then-insert race. Same
    NativeListingId + identical immutable envelope -> ALREADY_EXISTS with the
    original row untouched. Same NativeListingId + a different immutable
    envelope (publishing Organization, creator Account, MarketEpisode link or
    broker reference) -> CONFLICT, and the original row is never overwritten.
    """
    if not isinstance(listing, NativeListing):
        raise TypeError(f"listing must be a NativeListing, got {type(listing).__name__}")
    _validate_broker_listing_reference(broker_listing_reference)

    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return NativeListingCreationResult(
            status=NativeListingCreationStatus.DENIED, denial_reason=decision.reason
        )

    market_episode_id = listing.market_episode_id.value if listing.market_episode_id else None
    content_hash = _fingerprint_envelope(
        candidate_organization.id.value,
        account_id.value,
        market_episode_id,
        broker_listing_reference,
    )

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_NATIVE_LISTING,
            (
                listing.id.value,
                candidate_organization.id.value,
                account_id.value,
                market_episode_id,
                broker_listing_reference,
                content_hash,
            ),
        )
        if cur.rowcount > 0:
            return NativeListingCreationResult(status=NativeListingCreationStatus.CREATED)
        cur.execute(_SELECT_NATIVE_LISTING_HASH, [listing.id.value])
        existing = cur.fetchone()

    if existing is not None and existing[0] == content_hash:
        return NativeListingCreationResult(status=NativeListingCreationStatus.ALREADY_EXISTS)
    return NativeListingCreationResult(status=NativeListingCreationStatus.CONFLICT)


def fetch_native_listing(
    conn: Any, native_listing_id: NativeListingId
) -> NativeListingRecord | None:
    """Exact typed readback by NativeListingId, or None if not found.

    Reconstructs runtime-distinct NativeListingId / MarketEpisodeId /
    MarketplaceOrganizationId / AccountId types without joining to any
    nonexistent actor/MarketEpisode table or inventing BoatDesign/
    PhysicalBoat truth.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_NATIVE_LISTING, [native_listing_id.value])
        row = cur.fetchone()
    if row is None:
        return None

    (
        listing_id_value,
        publishing_organization_id_value,
        created_by_account_id_value,
        market_episode_id_value,
        broker_listing_reference,
        created_at,
    ) = row
    return NativeListingRecord(
        listing=NativeListing(
            id=NativeListingId(listing_id_value),
            market_episode_id=(
                MarketEpisodeId(market_episode_id_value)
                if market_episode_id_value is not None
                else None
            ),
        ),
        publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id_value),
        created_by_account_id=AccountId(created_by_account_id_value),
        broker_listing_reference=broker_listing_reference,
        created_at=created_at,
    )
