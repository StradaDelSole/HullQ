"""Unit tests for hullq.domain.publication_readiness — SLICE-0069.

Covers `specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` §3-§8: every
D22 required condition blocks independently when absent/invalid,
BoatDesignRef/Search-fit/multiple-photo quality never block publication (by
construction -- this evaluator has no facts field for any of them at all),
YouTube-only/rights-invalid/retired media never satisfies the image/cover
requirement, and the canonical result shape's invariants (READY carries no
blockers, BLOCKED always carries at least one).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.publication_readiness import (
    CoverState,
    PublicationBlockerReason,
    PublicationReadinessFacts,
    PublicationReadinessResult,
    PublicationReadinessStatus,
    evaluate_publication_readiness,
)
from hullq.domain.publishing_eligibility import (
    PublishingEligibilityDecision,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
)

_ALLOWED = PublishingEligibilityDecision(status=PublishingEligibilityStatus.ALLOWED)


def _ready_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal("125000.00"),
        currency="EUR",
    )


def _ready_claim() -> PhysicalBoatClaimSnapshot:
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2020),
    )


def _ready_facts() -> PublicationReadinessFacts:
    return PublicationReadinessFacts(
        native_listing_id_value="NL-1",
        publishing_eligibility=_ALLOWED,
        lifecycle_state=NativeListingLifecycleState.DRAFT,
        market_episode_id_present=True,
        market_episode_exists=True,
        physical_boat_exists=True,
        offer=_ready_offer(),
        physical_boat_claim=_ready_claim(),
        has_public_usable_image=True,
        cover_state=CoverState.VALID,
    )


class TestReadyCase:
    def test_fully_ready_facts_are_ready_with_no_blockers(self) -> None:
        result = evaluate_publication_readiness(_ready_facts())
        assert result.status is PublicationReadinessStatus.READY
        assert result.blockers == frozenset()
        assert result.is_ready is True

    def test_build_year_unknown_is_still_ready(self) -> None:
        """Contract §5: explicit UNKNOWN build_year is an accepted response,
        never a blocker distinct from a valid year."""
        claim = PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.UNKNOWN),
        )
        facts = replace(_ready_facts(), physical_boat_claim=claim)
        result = evaluate_publication_readiness(facts)
        assert result.status is PublicationReadinessStatus.READY

    def test_poa_offer_is_ready(self) -> None:
        offer = NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.POA,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
        )
        facts = replace(_ready_facts(), offer=offer)
        result = evaluate_publication_readiness(facts)
        assert result.status is PublicationReadinessStatus.READY


class TestEachConditionBlocksIndependently:
    def test_lifecycle_not_draft_blocks(self) -> None:
        facts = replace(_ready_facts(), lifecycle_state=NativeListingLifecycleState.ACTIVE)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.LIFECYCLE_NOT_DRAFT})

    def test_market_episode_id_absent_blocks_as_unresolved(self) -> None:
        facts = replace(
            _ready_facts(),
            market_episode_id_present=False,
            market_episode_exists=False,
            physical_boat_exists=False,
        )
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.MARKET_EPISODE_UNRESOLVED})

    def test_market_episode_missing_despite_id_present_blocks_as_unresolved(self) -> None:
        facts = replace(_ready_facts(), market_episode_exists=False, physical_boat_exists=False)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.MARKET_EPISODE_UNRESOLVED})

    def test_physical_boat_missing_blocks_distinctly_from_episode_unresolved(self) -> None:
        facts = replace(_ready_facts(), physical_boat_exists=False)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.PHYSICAL_BOAT_MISSING})

    def test_offer_missing_blocks(self) -> None:
        facts = replace(_ready_facts(), offer=None)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.OFFER_MISSING})

    def test_physical_boat_claim_missing_blocks(self) -> None:
        facts = replace(_ready_facts(), physical_boat_claim=None)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.PHYSICAL_BOAT_CLAIM_MISSING})

    def test_no_public_usable_image_blocks(self) -> None:
        facts = replace(
            _ready_facts(), has_public_usable_image=False, cover_state=CoverState.MISSING
        )
        result = evaluate_publication_readiness(facts)
        assert PublicationBlockerReason.NO_PUBLIC_USABLE_IMAGE in result.blockers
        assert PublicationBlockerReason.COVER_MISSING in result.blockers

    def test_cover_missing_blocks_even_with_a_public_usable_image(self) -> None:
        """A YouTube-only or otherwise cover-less gallery never satisfies the
        explicit-cover requirement even when a public-usable image exists
        elsewhere in the gallery."""
        facts = replace(_ready_facts(), cover_state=CoverState.MISSING)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.COVER_MISSING})

    def test_cover_invalid_blocks_distinctly_from_cover_missing(self) -> None:
        """A cover pointer referencing a retired/rights-invalid asset is
        COVER_INVALID, never silently treated as COVER_MISSING."""
        facts = replace(_ready_facts(), cover_state=CoverState.INVALID)
        result = evaluate_publication_readiness(facts)
        assert result.blockers == frozenset({PublicationBlockerReason.COVER_INVALID})


class TestActorAuthorizationDenialBlocks:
    def test_each_publishing_eligibility_denial_reason_maps_through(self) -> None:
        for reason in (
            PublishingEligibilityReason.NO_MEMBERSHIP,
            PublishingEligibilityReason.ACCOUNT_MISMATCH,
            PublishingEligibilityReason.ORGANIZATION_MISMATCH,
            PublishingEligibilityReason.MEMBERSHIP_INACTIVE,
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
            PublishingEligibilityReason.ORGANIZATION_INELIGIBLE,
            PublishingEligibilityReason.ORGANIZATION_UNVERIFIED,
        ):
            decision = PublishingEligibilityDecision(
                status=PublishingEligibilityStatus.DENIED, reason=reason
            )
            facts = replace(_ready_facts(), publishing_eligibility=decision)
            result = evaluate_publication_readiness(facts)
            assert result.blockers == frozenset({PublicationBlockerReason(reason.value)})


class TestMultipleBlockersCombine:
    def test_every_condition_broken_reports_every_blocker(self) -> None:
        facts = PublicationReadinessFacts(
            native_listing_id_value="NL-BROKEN",
            publishing_eligibility=PublishingEligibilityDecision(
                status=PublishingEligibilityStatus.DENIED,
                reason=PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
            ),
            lifecycle_state=NativeListingLifecycleState.WITHDRAWN,
            market_episode_id_present=False,
            market_episode_exists=False,
            physical_boat_exists=False,
            offer=None,
            physical_boat_claim=None,
            has_public_usable_image=False,
            cover_state=CoverState.MISSING,
        )
        result = evaluate_publication_readiness(facts)
        assert result.status is PublicationReadinessStatus.BLOCKED
        assert result.blockers == frozenset(
            {
                PublicationBlockerReason.PUBLISHER_ROLE_REQUIRED,
                PublicationBlockerReason.LIFECYCLE_NOT_DRAFT,
                PublicationBlockerReason.MARKET_EPISODE_UNRESOLVED,
                PublicationBlockerReason.OFFER_MISSING,
                PublicationBlockerReason.PHYSICAL_BOAT_CLAIM_MISSING,
                PublicationBlockerReason.NO_PUBLIC_USABLE_IMAGE,
                PublicationBlockerReason.COVER_MISSING,
            }
        )
        # PHYSICAL_BOAT_MISSING must never co-occur with MARKET_EPISODE_UNRESOLVED.
        assert PublicationBlockerReason.PHYSICAL_BOAT_MISSING not in result.blockers


class TestResultShapeInvariants:
    def test_ready_result_with_blockers_is_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="READY"):
            PublicationReadinessResult(
                native_listing_id_value="NL-1",
                lifecycle_state=NativeListingLifecycleState.DRAFT,
                status=PublicationReadinessStatus.READY,
                blockers=frozenset({PublicationBlockerReason.OFFER_MISSING}),
            )

    def test_blocked_result_without_blockers_is_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="BLOCKED"):
            PublicationReadinessResult(
                native_listing_id_value="NL-1",
                lifecycle_state=NativeListingLifecycleState.DRAFT,
                status=PublicationReadinessStatus.BLOCKED,
                blockers=frozenset(),
            )
