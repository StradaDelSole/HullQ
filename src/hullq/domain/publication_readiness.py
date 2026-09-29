"""Canonical PublicationReadiness evaluator — SLICE-0069.

Implements `specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` §3-§8:
the one canonical domain rule set deciding whether the current authorized
publisher may transition an exact DRAFT NativeListing to ACTIVE now. Both the
advisory Broker Workspace preflight and the authoritative in-transaction
publish re-evaluation call this identical pure function (contract §9: "the
same result vocabulary and requirement rules") -- there is no second,
independently maintained definition of publication completeness anywhere in
this codebase after this slice (contract §10 supersedes the SLICE-0049
`_publication_completeness_satisfied` shortcut).

This module is pure: it takes an already-resolved `PublicationReadinessFacts`
snapshot and returns a deterministic `PublicationReadinessResult`. It performs
no persistence/network access and evaluates no wall-clock time.

## Why several contract §8 "material distinctions" collapse to one blocker code

`hullq.domain.native_listing_offer.NativeListingOfferSnapshot` and
`hullq.domain.physical_boat_claims.PhysicalBoatClaimSnapshot` each already
enforce every accepted required-field validity rule at construction time --
an `asking_price_mode`/`location_country`/non-blank `broker_description`
offer (contract §6) or a non-blank `marketed_brand_claim`/
`model_designation_claim` plus present `build_year` (VALUE_ASSERTION or
explicit UNKNOWN -- both accepted, contract §5) PhysicalBoat claim (contract
§5) simply cannot exist as a Python object otherwise. So once
`PublicationReadinessFacts.offer`/`.physical_boat_claim` is not `None`, it is
already known-valid by construction; there is no reachable "exists but
invalid" state to distinguish from "missing" for those two families, and this
module does not add unreachable defensive branches for it (mirrors this
codebase's "don't validate what can't happen" discipline). `OFFER_MISSING`
and `PHYSICAL_BOAT_CLAIM_MISSING` therefore each cover both the "missing" and
"required response invalid" contract §8 bullets for their family.

The explicit cover is different: `has_public_usable_image`/`cover_state` are
computed here from *current* gallery truth (contract §9's authoritative
re-evaluation, not a write-time guarantee) precisely because a public-usable
image or cover can become invalid *after* it was set (e.g. a later asset
retirement) without any NativeListingOfferSnapshot-style construction-time
guard protecting it -- so `COVER_MISSING`/`COVER_INVALID` are both genuinely
reachable, independent conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import PhysicalBoatClaimSnapshot
from hullq.domain.publishing_eligibility import (
    PublishingEligibilityDecision,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
)

__all__ = [
    "CoverState",
    "PublicationBlockerReason",
    "PublicationReadinessFacts",
    "PublicationReadinessResult",
    "PublicationReadinessStatus",
    "evaluate_publication_readiness",
]


class PublicationReadinessStatus(StrEnum):
    """Never a bare boolean (contract §8)."""

    READY = "READY"
    BLOCKED = "BLOCKED"


class PublicationBlockerReason(StrEnum):
    """Stable, machine-readable, presentation-neutral blocker codes (contract §8).

    Preserves every material distinction contract §8 requires "at least":
    the five actor-authorization denial reasons and the two Organization-
    eligibility denial reasons are carried through unchanged from
    `hullq.domain.publishing_eligibility.PublishingEligibilityReason` (one
    canonical actor/Organization eligibility vocabulary, never a second one);
    the remaining members are readiness-specific.
    """

    NO_MEMBERSHIP = "NO_MEMBERSHIP"
    ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
    ORGANIZATION_MISMATCH = "ORGANIZATION_MISMATCH"
    MEMBERSHIP_INACTIVE = "MEMBERSHIP_INACTIVE"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    ORGANIZATION_INELIGIBLE = "ORGANIZATION_INELIGIBLE"
    ORGANIZATION_UNVERIFIED = "ORGANIZATION_UNVERIFIED"
    LIFECYCLE_NOT_DRAFT = "LIFECYCLE_NOT_DRAFT"
    MARKET_EPISODE_UNRESOLVED = "MARKET_EPISODE_UNRESOLVED"
    PHYSICAL_BOAT_MISSING = "PHYSICAL_BOAT_MISSING"
    OFFER_MISSING = "OFFER_MISSING"
    PHYSICAL_BOAT_CLAIM_MISSING = "PHYSICAL_BOAT_CLAIM_MISSING"
    NO_PUBLIC_USABLE_IMAGE = "NO_PUBLIC_USABLE_IMAGE"
    COVER_MISSING = "COVER_MISSING"
    COVER_INVALID = "COVER_INVALID"


#: Maps a denied `PublishingEligibilityReason` onto the identically-named
#: `PublicationBlockerReason` -- one canonical vocabulary, never re-decided.
_ELIGIBILITY_REASON_TO_BLOCKER: dict[PublishingEligibilityReason, PublicationBlockerReason] = {
    PublishingEligibilityReason.NO_MEMBERSHIP: PublicationBlockerReason.NO_MEMBERSHIP,
    PublishingEligibilityReason.ACCOUNT_MISMATCH: PublicationBlockerReason.ACCOUNT_MISMATCH,
    PublishingEligibilityReason.ORGANIZATION_MISMATCH: (
        PublicationBlockerReason.ORGANIZATION_MISMATCH
    ),
    PublishingEligibilityReason.MEMBERSHIP_INACTIVE: PublicationBlockerReason.MEMBERSHIP_INACTIVE,
    PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED: (
        PublicationBlockerReason.PUBLISHER_ROLE_REQUIRED
    ),
    PublishingEligibilityReason.ORGANIZATION_INELIGIBLE: (
        PublicationBlockerReason.ORGANIZATION_INELIGIBLE
    ),
    PublishingEligibilityReason.ORGANIZATION_UNVERIFIED: (
        PublicationBlockerReason.ORGANIZATION_UNVERIFIED
    ),
}


class CoverState(StrEnum):
    """Mechanically distinct explicit-cover states (contract §7)."""

    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class PublicationReadinessFacts:
    """Already-resolved current truth for one DRAFT NativeListing publish attempt.

    `market_episode_id_present`/`market_episode_exists`/`physical_boat_exists`
    together encode the pre-D20 §4 resolution boundary: a listing is only
    ever evaluated against `physical_boat_exists` once its MarketEpisode link
    itself already resolves (contract §4 defines RESOLVED as requiring both
    together) -- `evaluate_publication_readiness` never reports
    `PHYSICAL_BOAT_MISSING` and `MARKET_EPISODE_UNRESOLVED` simultaneously.
    """

    native_listing_id_value: str
    publishing_eligibility: PublishingEligibilityDecision
    lifecycle_state: NativeListingLifecycleState
    market_episode_id_present: bool
    market_episode_exists: bool
    physical_boat_exists: bool
    offer: NativeListingOfferSnapshot | None
    physical_boat_claim: PhysicalBoatClaimSnapshot | None
    has_public_usable_image: bool
    cover_state: CoverState


@dataclass(frozen=True, slots=True)
class PublicationReadinessResult:
    """The canonical result (contract §8): never one ambiguous boolean."""

    native_listing_id_value: str
    lifecycle_state: NativeListingLifecycleState
    status: PublicationReadinessStatus
    blockers: frozenset[PublicationBlockerReason]

    def __post_init__(self) -> None:
        if self.status is PublicationReadinessStatus.READY and self.blockers:
            raise ValueError("A READY result must carry no blockers")
        if self.status is PublicationReadinessStatus.BLOCKED and not self.blockers:
            raise ValueError("A BLOCKED result must carry at least one blocker")

    @property
    def is_ready(self) -> bool:
        return self.status is PublicationReadinessStatus.READY


def evaluate_publication_readiness(
    facts: PublicationReadinessFacts,
) -> PublicationReadinessResult:
    """Deterministically decide PublicationReadiness from already-resolved *facts*.

    Every applicable condition is evaluated independently and every resulting
    blocker is collected -- callers see the full deterministic blocker set,
    not merely the first failure (contract §8).
    """
    blockers: set[PublicationBlockerReason] = set()

    if facts.publishing_eligibility.status is PublishingEligibilityStatus.DENIED:
        reason = facts.publishing_eligibility.reason
        assert reason is not None
        blockers.add(_ELIGIBILITY_REASON_TO_BLOCKER[reason])

    if facts.lifecycle_state is not NativeListingLifecycleState.DRAFT:
        blockers.add(PublicationBlockerReason.LIFECYCLE_NOT_DRAFT)

    if not facts.market_episode_id_present or not facts.market_episode_exists:
        blockers.add(PublicationBlockerReason.MARKET_EPISODE_UNRESOLVED)
    elif not facts.physical_boat_exists:
        blockers.add(PublicationBlockerReason.PHYSICAL_BOAT_MISSING)

    if facts.offer is None:
        blockers.add(PublicationBlockerReason.OFFER_MISSING)

    if facts.physical_boat_claim is None:
        blockers.add(PublicationBlockerReason.PHYSICAL_BOAT_CLAIM_MISSING)

    if not facts.has_public_usable_image:
        blockers.add(PublicationBlockerReason.NO_PUBLIC_USABLE_IMAGE)

    if facts.cover_state is CoverState.MISSING:
        blockers.add(PublicationBlockerReason.COVER_MISSING)
    elif facts.cover_state is CoverState.INVALID:
        blockers.add(PublicationBlockerReason.COVER_INVALID)

    status = PublicationReadinessStatus.BLOCKED if blockers else PublicationReadinessStatus.READY
    return PublicationReadinessResult(
        native_listing_id_value=facts.native_listing_id_value,
        lifecycle_state=facts.lifecycle_state,
        status=status,
        blockers=frozenset(blockers),
    )
