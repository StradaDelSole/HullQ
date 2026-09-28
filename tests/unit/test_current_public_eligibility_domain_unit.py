"""Unit tests for hullq.domain.current_public_eligibility — SLICE-0069.

Covers `specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` §11-§13:
ACTIVE + current freshness + every accepted condition -> eligible; each
condition's loss suppresses independently without any lifecycle rewrite
(suppression is a pure classification here -- this evaluator never mutates
anything); DRAFT/WITHDRAWN never eligible; and the canonical result shape's
invariants.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hullq.domain.current_public_eligibility import (
    CurrentPublicCoverState,
    CurrentPublicEligibilityFacts,
    CurrentPublicEligibilityResult,
    CurrentPublicEligibilityStatus,
    CurrentPublicSuppressionReason,
    evaluate_current_public_eligibility,
)
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.publishing_eligibility import OrganizationPublishingEligibility


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


def _eligible_facts() -> CurrentPublicEligibilityFacts:
    return CurrentPublicEligibilityFacts(
        native_listing_id_value="NL-1",
        lifecycle_state=NativeListingLifecycleState.ACTIVE,
        freshness_status=FreshnessStatus.CONFIRMED,
        organization_exists=True,
        organization_publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        market_episode_id_present=True,
        market_episode_exists=True,
        physical_boat_exists=True,
        offer=_ready_offer(),
        physical_boat_claim=_ready_claim(),
        has_public_usable_image=True,
        cover_state=CurrentPublicCoverState.VALID,
    )


class TestEligibleCase:
    def test_fully_eligible_facts_are_eligible_with_no_reasons(self) -> None:
        result = evaluate_current_public_eligibility(_eligible_facts())
        assert result.status is CurrentPublicEligibilityStatus.ELIGIBLE
        assert result.suppression_reasons == frozenset()
        assert result.is_eligible is True

    def test_due_for_confirmation_freshness_is_still_eligible(self) -> None:
        facts = replace(_eligible_facts(), freshness_status=FreshnessStatus.DUE_FOR_CONFIRMATION)
        result = evaluate_current_public_eligibility(facts)
        assert result.status is CurrentPublicEligibilityStatus.ELIGIBLE


class TestEachConditionSuppressesIndependently:
    def test_lifecycle_not_active_suppresses(self) -> None:
        for state in (NativeListingLifecycleState.DRAFT, NativeListingLifecycleState.WITHDRAWN):
            facts = replace(_eligible_facts(), lifecycle_state=state)
            result = evaluate_current_public_eligibility(facts)
            assert CurrentPublicSuppressionReason.LIFECYCLE_NOT_ACTIVE in result.suppression_reasons

    def test_stale_freshness_suppresses(self) -> None:
        facts = replace(_eligible_facts(), freshness_status=FreshnessStatus.STALE)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.FRESHNESS_NOT_CURRENT}
        )

    def test_unknown_freshness_suppresses(self) -> None:
        facts = replace(_eligible_facts(), freshness_status=FreshnessStatus.UNKNOWN)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.FRESHNESS_NOT_CURRENT}
        )

    def test_organization_missing_suppresses(self) -> None:
        facts = replace(
            _eligible_facts(), organization_exists=False, organization_publishing_eligibility=None
        )
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.ORGANIZATION_NOT_ELIGIBLE}
        )

    def test_organization_ineligible_suppresses_with_lifecycle_still_active(self) -> None:
        """Contract §22: Organization becomes INELIGIBLE/UNVERIFIED ->
        suppressed with lifecycle still ACTIVE (this evaluator never touches
        lifecycle; the fact itself asserts it stays ACTIVE)."""
        for eligibility in (
            OrganizationPublishingEligibility.INELIGIBLE,
            OrganizationPublishingEligibility.UNVERIFIED,
        ):
            facts = replace(_eligible_facts(), organization_publishing_eligibility=eligibility)
            result = evaluate_current_public_eligibility(facts)
            assert result.suppression_reasons == frozenset(
                {CurrentPublicSuppressionReason.ORGANIZATION_NOT_ELIGIBLE}
            )
            assert facts.lifecycle_state is NativeListingLifecycleState.ACTIVE

    def test_market_episode_unresolved_suppresses(self) -> None:
        facts = replace(
            _eligible_facts(),
            market_episode_id_present=False,
            market_episode_exists=False,
            physical_boat_exists=False,
        )
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.MARKET_EPISODE_UNRESOLVED}
        )

    def test_physical_boat_missing_suppresses_distinctly(self) -> None:
        facts = replace(_eligible_facts(), physical_boat_exists=False)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.PHYSICAL_BOAT_MISSING}
        )

    def test_offer_missing_suppresses(self) -> None:
        facts = replace(_eligible_facts(), offer=None)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.OFFER_MISSING}
        )

    def test_physical_boat_claim_missing_suppresses(self) -> None:
        facts = replace(_eligible_facts(), physical_boat_claim=None)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.PHYSICAL_BOAT_CLAIM_MISSING}
        )

    def test_no_public_usable_image_suppresses(self) -> None:
        facts = replace(
            _eligible_facts(),
            has_public_usable_image=False,
            cover_state=CurrentPublicCoverState.MISSING,
        )
        result = evaluate_current_public_eligibility(facts)
        assert CurrentPublicSuppressionReason.NO_PUBLIC_USABLE_IMAGE in result.suppression_reasons
        assert CurrentPublicSuppressionReason.COVER_MISSING in result.suppression_reasons

    def test_cover_missing_suppresses(self) -> None:
        facts = replace(_eligible_facts(), cover_state=CurrentPublicCoverState.MISSING)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.COVER_MISSING}
        )

    def test_cover_invalid_suppresses_distinctly_from_cover_missing(self) -> None:
        facts = replace(_eligible_facts(), cover_state=CurrentPublicCoverState.INVALID)
        result = evaluate_current_public_eligibility(facts)
        assert result.suppression_reasons == frozenset(
            {CurrentPublicSuppressionReason.COVER_INVALID}
        )


class TestMultipleReasonsCombine:
    def test_every_condition_broken_reports_every_reason(self) -> None:
        facts = CurrentPublicEligibilityFacts(
            native_listing_id_value="NL-BROKEN",
            lifecycle_state=NativeListingLifecycleState.WITHDRAWN,
            freshness_status=FreshnessStatus.STALE,
            organization_exists=False,
            organization_publishing_eligibility=None,
            market_episode_id_present=False,
            market_episode_exists=False,
            physical_boat_exists=False,
            offer=None,
            physical_boat_claim=None,
            has_public_usable_image=False,
            cover_state=CurrentPublicCoverState.MISSING,
        )
        result = evaluate_current_public_eligibility(facts)
        assert result.status is CurrentPublicEligibilityStatus.SUPPRESSED
        assert result.suppression_reasons == frozenset(
            {
                CurrentPublicSuppressionReason.LIFECYCLE_NOT_ACTIVE,
                CurrentPublicSuppressionReason.FRESHNESS_NOT_CURRENT,
                CurrentPublicSuppressionReason.ORGANIZATION_NOT_ELIGIBLE,
                CurrentPublicSuppressionReason.MARKET_EPISODE_UNRESOLVED,
                CurrentPublicSuppressionReason.OFFER_MISSING,
                CurrentPublicSuppressionReason.PHYSICAL_BOAT_CLAIM_MISSING,
                CurrentPublicSuppressionReason.NO_PUBLIC_USABLE_IMAGE,
                CurrentPublicSuppressionReason.COVER_MISSING,
            }
        )
        assert (
            CurrentPublicSuppressionReason.PHYSICAL_BOAT_MISSING not in result.suppression_reasons
        )


class TestResultShapeInvariants:
    def test_eligible_result_with_reasons_is_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="ELIGIBLE"):
            CurrentPublicEligibilityResult(
                native_listing_id_value="NL-1",
                status=CurrentPublicEligibilityStatus.ELIGIBLE,
                suppression_reasons=frozenset({CurrentPublicSuppressionReason.OFFER_MISSING}),
            )

    def test_suppressed_result_without_reasons_is_rejected(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="SUPPRESSED"):
            CurrentPublicEligibilityResult(
                native_listing_id_value="NL-1",
                status=CurrentPublicEligibilityStatus.SUPPRESSED,
                suppression_reasons=frozenset(),
            )
