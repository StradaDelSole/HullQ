"""Canonical CurrentPublicEligibility evaluator — SLICE-0069.

Implements `specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` §11-§13:
the one canonical domain rule set deciding whether an already-ACTIVE
NativeListing belongs on current buyer-facing/public-market surfaces *now*.
`ACTIVE` lifecycle alone is never sufficient (contract §2) -- the exact public
listing read model and both accepted Direct Search paths must all consume
this identical evaluator rather than each re-deriving D29 admission (contract
§16).

This module is pure: it takes an already-resolved `CurrentPublicEligibilityFacts`
snapshot and returns a deterministic `CurrentPublicEligibilityResult`. It
performs no persistence/network access and evaluates no wall-clock time --
freshness is passed in as an already-classified
`hullq.domain.native_listing_freshness.FreshnessStatus` at the caller's own
explicit `as_of` boundary.

Suppression never rewrites lifecycle (contract §12): this evaluator only
*classifies* current-public admission; nothing here mutates any persisted
state.

See `hullq.domain.publication_readiness`'s module docstring for why an
existing offer/PhysicalBoat-claim record is always already valid by
construction, and therefore contributes only one "missing" blocker per
family here too.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import PhysicalBoatClaimSnapshot
from hullq.domain.publishing_eligibility import OrganizationPublishingEligibility

__all__ = [
    "CurrentPublicCoverState",
    "CurrentPublicEligibilityFacts",
    "CurrentPublicEligibilityResult",
    "CurrentPublicEligibilityStatus",
    "CurrentPublicSuppressionReason",
    "evaluate_current_public_eligibility",
]


class CurrentPublicEligibilityStatus(StrEnum):
    """Never a bare boolean (contract §2/§8)."""

    ELIGIBLE = "ELIGIBLE"
    SUPPRESSED = "SUPPRESSED"


class CurrentPublicSuppressionReason(StrEnum):
    """Stable, machine-readable, presentation-neutral suppression codes
    (contract §12/§17: "structured current-public suppression reasons")."""

    LIFECYCLE_NOT_ACTIVE = "LIFECYCLE_NOT_ACTIVE"
    FRESHNESS_NOT_CURRENT = "FRESHNESS_NOT_CURRENT"
    ORGANIZATION_NOT_ELIGIBLE = "ORGANIZATION_NOT_ELIGIBLE"
    MARKET_EPISODE_UNRESOLVED = "MARKET_EPISODE_UNRESOLVED"
    PHYSICAL_BOAT_MISSING = "PHYSICAL_BOAT_MISSING"
    OFFER_MISSING = "OFFER_MISSING"
    PHYSICAL_BOAT_CLAIM_MISSING = "PHYSICAL_BOAT_CLAIM_MISSING"
    NO_PUBLIC_USABLE_IMAGE = "NO_PUBLIC_USABLE_IMAGE"
    COVER_MISSING = "COVER_MISSING"
    COVER_INVALID = "COVER_INVALID"


class CurrentPublicCoverState(StrEnum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"


#: Contract §7: buyer surfaces admit exactly these two freshness statuses.
_CURRENT_FRESHNESS_STATUSES = frozenset(
    {FreshnessStatus.CONFIRMED, FreshnessStatus.DUE_FOR_CONFIRMATION}
)


@dataclass(frozen=True, slots=True)
class CurrentPublicEligibilityFacts:
    """Already-resolved current truth for one NativeListing's public admission.

    `organization_exists`/`organization_publishing_eligibility` are evaluated
    independently of actor/Membership/PUBLISHER-role state (contract §11:
    "Current actor membership/PUBLISHER role is NOT a buyer-public
    eligibility condition after publication ... Organization eligibility is a
    current-public condition") -- callers must never pass an actor-level
    `PublishingEligibilityDecision` here.
    """

    native_listing_id_value: str
    lifecycle_state: NativeListingLifecycleState
    freshness_status: FreshnessStatus
    organization_exists: bool
    organization_publishing_eligibility: OrganizationPublishingEligibility | None
    market_episode_id_present: bool
    market_episode_exists: bool
    physical_boat_exists: bool
    offer: NativeListingOfferSnapshot | None
    physical_boat_claim: PhysicalBoatClaimSnapshot | None
    has_public_usable_image: bool
    cover_state: CurrentPublicCoverState


@dataclass(frozen=True, slots=True)
class CurrentPublicEligibilityResult:
    """The canonical result (contract §12/§17): never one ambiguous boolean."""

    native_listing_id_value: str
    status: CurrentPublicEligibilityStatus
    suppression_reasons: frozenset[CurrentPublicSuppressionReason]

    def __post_init__(self) -> None:
        if self.status is CurrentPublicEligibilityStatus.ELIGIBLE and self.suppression_reasons:
            raise ValueError("An ELIGIBLE result must carry no suppression reasons")
        if (
            self.status is CurrentPublicEligibilityStatus.SUPPRESSED
            and not self.suppression_reasons
        ):
            raise ValueError("A SUPPRESSED result must carry at least one suppression reason")

    @property
    def is_eligible(self) -> bool:
        return self.status is CurrentPublicEligibilityStatus.ELIGIBLE


def evaluate_current_public_eligibility(
    facts: CurrentPublicEligibilityFacts,
) -> CurrentPublicEligibilityResult:
    """Deterministically decide CurrentPublicEligibility from already-resolved *facts*.

    Every applicable condition is evaluated independently (contract §22:
    "episode/offer/required claim/media/cover loss -> suppressed without
    lifecycle rewrite") so a caller can observe every concurrent suppression
    reason, not merely the first.
    """
    reasons: set[CurrentPublicSuppressionReason] = set()

    if facts.lifecycle_state is not NativeListingLifecycleState.ACTIVE:
        reasons.add(CurrentPublicSuppressionReason.LIFECYCLE_NOT_ACTIVE)

    if facts.freshness_status not in _CURRENT_FRESHNESS_STATUSES:
        reasons.add(CurrentPublicSuppressionReason.FRESHNESS_NOT_CURRENT)

    if (
        not facts.organization_exists
        or facts.organization_publishing_eligibility
        is not OrganizationPublishingEligibility.ELIGIBLE
    ):
        reasons.add(CurrentPublicSuppressionReason.ORGANIZATION_NOT_ELIGIBLE)

    if not facts.market_episode_id_present or not facts.market_episode_exists:
        reasons.add(CurrentPublicSuppressionReason.MARKET_EPISODE_UNRESOLVED)
    elif not facts.physical_boat_exists:
        reasons.add(CurrentPublicSuppressionReason.PHYSICAL_BOAT_MISSING)

    if facts.offer is None:
        reasons.add(CurrentPublicSuppressionReason.OFFER_MISSING)

    if facts.physical_boat_claim is None:
        reasons.add(CurrentPublicSuppressionReason.PHYSICAL_BOAT_CLAIM_MISSING)

    if not facts.has_public_usable_image:
        reasons.add(CurrentPublicSuppressionReason.NO_PUBLIC_USABLE_IMAGE)

    if facts.cover_state is CurrentPublicCoverState.MISSING:
        reasons.add(CurrentPublicSuppressionReason.COVER_MISSING)
    elif facts.cover_state is CurrentPublicCoverState.INVALID:
        reasons.add(CurrentPublicSuppressionReason.COVER_INVALID)

    status = (
        CurrentPublicEligibilityStatus.SUPPRESSED
        if reasons
        else CurrentPublicEligibilityStatus.ELIGIBLE
    )
    return CurrentPublicEligibilityResult(
        native_listing_id_value=facts.native_listing_id_value,
        status=status,
        suppression_reasons=frozenset(reasons),
    )
