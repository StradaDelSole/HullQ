"""Unit tests for hullq.domain.publishing_eligibility — SLICE-0041.

Covers the required test scenarios from
docs/slices/SLICE-0041-professional-publishing-eligibility.md and the
locked semantics in
specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
    PublishingEligibilityDecision,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)

ROOT = Path(__file__).resolve().parents[2]

IDENTITY_KINDS = [AccountId, MarketplaceOrganizationId, OrganizationMembershipId]

DEFAULT_ACCOUNT_ID = AccountId("ACC-X")
DEFAULT_ORGANIZATION_ID = MarketplaceOrganizationId("ORG-A")


def _org(
    org_id: str = "ORG-A",
    category: ProfessionalCategory = ProfessionalCategory.BROKER,
    eligibility: OrganizationPublishingEligibility = OrganizationPublishingEligibility.ELIGIBLE,
) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=category,
        publishing_eligibility=eligibility,
    )


def _membership(
    membership_id: str = "M-1",
    account_id: AccountId = DEFAULT_ACCOUNT_ID,
    organization_id: MarketplaceOrganizationId = DEFAULT_ORGANIZATION_ID,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account_id,
        organization_id=organization_id,
        roles=roles,
        state=state,
    )


# ---------------------------------------------------------------------------
# Identity kinds reject empty identifiers and remain runtime-distinct
# ---------------------------------------------------------------------------


class TestEmptyIdentifiersRejected:
    @pytest.mark.parametrize("kind", IDENTITY_KINDS)
    def test_empty_value_raises(self, kind: type) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            kind("")


class TestActorIdentityKindsRuntimeDistinct:
    def test_equal_raw_text_different_kinds_are_not_equal(self) -> None:
        token = "COLLIDING-TOKEN"
        account_id = AccountId(token)
        org_id = MarketplaceOrganizationId(token)
        membership_id = OrganizationMembershipId(token)
        assert account_id != org_id
        assert account_id != membership_id
        assert org_id != membership_id

    def test_membership_rejects_wrong_kind_account_id(self) -> None:
        with pytest.raises(TypeError, match="AccountId"):
            OrganizationMembership(
                id=OrganizationMembershipId("M-1"),
                account_id=MarketplaceOrganizationId("ORG-A"),  # type: ignore[arg-type]
                organization_id=MarketplaceOrganizationId("ORG-A"),
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

    def test_membership_rejects_wrong_kind_organization_id(self) -> None:
        with pytest.raises(TypeError, match="MarketplaceOrganizationId"):
            OrganizationMembership(
                id=OrganizationMembershipId("M-1"),
                account_id=AccountId("ACC-X"),
                organization_id=AccountId("ACC-X"),  # type: ignore[arg-type]
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

    def test_organization_rejects_wrong_kind_id(self) -> None:
        with pytest.raises(TypeError, match="MarketplaceOrganizationId"):
            MarketplaceOrganization(
                id=AccountId("ACC-X"),  # type: ignore[arg-type]
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )

    def test_membership_rejects_non_frozenset_roles(self) -> None:
        with pytest.raises(TypeError, match="frozenset"):
            OrganizationMembership(
                id=OrganizationMembershipId("M-1"),
                account_id=AccountId("ACC-X"),
                organization_id=MarketplaceOrganizationId("ORG-A"),
                roles={MembershipRole.PUBLISHER},  # type: ignore[arg-type]
                state=MembershipState.ACTIVE,
            )


# ---------------------------------------------------------------------------
# Explicit vocabularies — not inferred from strings
# ---------------------------------------------------------------------------


class TestExplicitVocabularies:
    def test_accepted_professional_categories_are_explicit(self) -> None:
        assert {c.value for c in ProfessionalCategory} == {"BROKER", "DEALER", "OTHER_PROFESSIONAL"}

    def test_eligibility_states_remain_distinct(self) -> None:
        assert (
            OrganizationPublishingEligibility.ELIGIBLE
            != OrganizationPublishingEligibility.INELIGIBLE
            != OrganizationPublishingEligibility.UNVERIFIED
        )
        assert len(set(OrganizationPublishingEligibility)) == 3

    def test_category_not_inferred_from_name_or_string(self) -> None:
        # The domain object only accepts explicit enum members; a broker-like
        # name string cannot be substituted for an actual category value.
        with pytest.raises((TypeError, AttributeError)):
            MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-A"),
                professional_category="BROKER",  # type: ignore[arg-type]
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )


# ---------------------------------------------------------------------------
# Core decision scenarios
# ---------------------------------------------------------------------------


class TestConsumerDenied:
    def test_consumer_with_no_membership_is_denied(self) -> None:
        decision = evaluate_native_listing_publishing_eligibility(
            AccountId("ACC-CONSUMER"), _org(), None
        )
        assert decision.status is PublishingEligibilityStatus.DENIED
        assert decision.reason is PublishingEligibilityReason.NO_MEMBERSHIP
        assert decision.is_allowed is False


class TestPublisherRoleGate:
    def test_active_publisher_in_eligible_organization_is_allowed(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(account_id=account_id, organization_id=org.id)
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.status is PublishingEligibilityStatus.ALLOWED
        assert decision.reason is None
        assert decision.is_allowed is True

    def test_owner_without_publisher_is_denied(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(
            account_id=account_id, organization_id=org.id, roles=frozenset({MembershipRole.OWNER})
        )
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.status is PublishingEligibilityStatus.DENIED
        assert decision.reason is PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED

    def test_admin_without_publisher_is_denied(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(
            account_id=account_id, organization_id=org.id, roles=frozenset({MembershipRole.ADMIN})
        )
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.reason is PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED

    def test_member_without_publisher_is_denied(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(
            account_id=account_id, organization_id=org.id, roles=frozenset({MembershipRole.MEMBER})
        )
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.reason is PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED

    def test_owner_plus_publisher_is_allowed(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(
            account_id=account_id,
            organization_id=org.id,
            roles=frozenset({MembershipRole.OWNER, MembershipRole.PUBLISHER}),
        )
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.status is PublishingEligibilityStatus.ALLOWED

    def test_admin_plus_publisher_is_allowed(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(
            account_id=account_id,
            organization_id=org.id,
            roles=frozenset({MembershipRole.ADMIN, MembershipRole.PUBLISHER}),
        )
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.status is PublishingEligibilityStatus.ALLOWED


class TestMembershipState:
    def test_inactive_membership_with_publisher_is_denied(self) -> None:
        org = _org()
        account_id = AccountId("ACC-X")
        membership = _membership(
            account_id=account_id, organization_id=org.id, state=MembershipState.INACTIVE
        )
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.reason is PublishingEligibilityReason.MEMBERSHIP_INACTIVE


class TestOrganizationEligibilityState:
    def test_unverified_organization_is_denied(self) -> None:
        org = _org(eligibility=OrganizationPublishingEligibility.UNVERIFIED)
        account_id = AccountId("ACC-X")
        membership = _membership(account_id=account_id, organization_id=org.id)
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.reason is PublishingEligibilityReason.ORGANIZATION_UNVERIFIED

    def test_ineligible_organization_is_denied(self) -> None:
        org = _org(eligibility=OrganizationPublishingEligibility.INELIGIBLE)
        account_id = AccountId("ACC-X")
        membership = _membership(account_id=account_id, organization_id=org.id)
        decision = evaluate_native_listing_publishing_eligibility(account_id, org, membership)
        assert decision.reason is PublishingEligibilityReason.ORGANIZATION_INELIGIBLE


class TestAccountAndOrganizationMismatch:
    def test_wrong_account_on_membership_is_denied(self) -> None:
        org = _org()
        membership = _membership(account_id=AccountId("ACC-Y"), organization_id=org.id)
        decision = evaluate_native_listing_publishing_eligibility(
            AccountId("ACC-X"), org, membership
        )
        assert decision.reason is PublishingEligibilityReason.ACCOUNT_MISMATCH

    def test_membership_for_organization_a_cannot_authorize_organization_b(self) -> None:
        org_a = _org(org_id="ORG-A")
        org_b = _org(org_id="ORG-B")
        account_id = AccountId("ACC-X")
        membership_in_a = _membership(account_id=account_id, organization_id=org_a.id)
        decision = evaluate_native_listing_publishing_eligibility(
            account_id, org_b, membership_in_a
        )
        assert decision.status is PublishingEligibilityStatus.DENIED
        assert decision.reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH

    def test_publisher_in_eligible_organization_a_is_allowed_for_a(self) -> None:
        org_a = _org(org_id="ORG-A")
        account_id = AccountId("ACC-X")
        membership_in_a = _membership(account_id=account_id, organization_id=org_a.id)
        decision = evaluate_native_listing_publishing_eligibility(
            account_id, org_a, membership_in_a
        )
        assert decision.status is PublishingEligibilityStatus.ALLOWED


class TestCrossTenantIsolationAcrossTwoOrganizations:
    def test_one_account_independently_evaluates_two_eligible_organizations(self) -> None:
        account_id = AccountId("ACC-X")
        org_a = _org(org_id="ORG-A")
        org_b = _org(org_id="ORG-B")
        membership_a = _membership(
            membership_id="M-A", account_id=account_id, organization_id=org_a.id
        )
        membership_b = _membership(
            membership_id="M-B", account_id=account_id, organization_id=org_b.id
        )

        decision_a = evaluate_native_listing_publishing_eligibility(account_id, org_a, membership_a)
        decision_b = evaluate_native_listing_publishing_eligibility(account_id, org_b, membership_b)

        assert decision_a.status is PublishingEligibilityStatus.ALLOWED
        assert decision_b.status is PublishingEligibilityStatus.ALLOWED

        # membership_a must not leak into authorizing org_b, and vice versa.
        cross_decision = evaluate_native_listing_publishing_eligibility(
            account_id, org_b, membership_a
        )
        assert cross_decision.status is PublishingEligibilityStatus.DENIED
        assert cross_decision.reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH


# ---------------------------------------------------------------------------
# Decision result is not a bare boolean
# ---------------------------------------------------------------------------


class TestDecisionResultShape:
    def test_denial_exposes_deterministic_reason(self) -> None:
        decision = evaluate_native_listing_publishing_eligibility(
            AccountId("ACC-CONSUMER"), _org(), None
        )
        assert isinstance(decision, PublishingEligibilityDecision)
        assert isinstance(decision.reason, PublishingEligibilityReason)

    def test_allowed_decision_cannot_carry_a_reason(self) -> None:
        with pytest.raises(ValueError, match="ALLOWED"):
            PublishingEligibilityDecision(
                status=PublishingEligibilityStatus.ALLOWED,
                reason=PublishingEligibilityReason.NO_MEMBERSHIP,
            )

    def test_denied_decision_requires_a_reason(self) -> None:
        with pytest.raises(ValueError, match="DENIED"):
            PublishingEligibilityDecision(status=PublishingEligibilityStatus.DENIED, reason=None)


# ---------------------------------------------------------------------------
# No Auth0/email/name-string inference
# ---------------------------------------------------------------------------


class TestNoOutOfBandInference:
    def test_evaluator_signature_takes_only_explicit_domain_objects(self) -> None:
        import inspect

        signature = inspect.signature(evaluate_native_listing_publishing_eligibility)
        assert list(signature.parameters) == [
            "account_id",
            "candidate_organization",
            "membership",
        ]

    def test_organization_has_no_email_or_name_field(self) -> None:
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(MarketplaceOrganization)}
        assert field_names == {"id", "professional_category", "publishing_eligibility"}


# ---------------------------------------------------------------------------
# No listing/persistence/BrokerageRequest fallback exists in this module
# ---------------------------------------------------------------------------


class TestNoOutOfScopeFallback:
    def test_module_exposes_no_listing_or_persistence_symbols(self) -> None:
        import hullq.domain.publishing_eligibility as module

        forbidden_substrings = ["Listing", "Persist", "BrokerageRequest", "Auth0"]
        for name in module.__all__:
            for forbidden in forbidden_substrings:
                assert forbidden not in name, f"{name} suggests out-of-scope surface"


# ---------------------------------------------------------------------------
# Owner-test output is deterministic/offline
# ---------------------------------------------------------------------------


class TestOwnerScriptDeterministicOffline:
    def test_owner_script_passes_and_is_deterministic(self) -> None:
        script = ROOT / "scripts" / "inspect_publishing_eligibility.py"
        first = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            timeout=30,
        )
        second = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            timeout=30,
        )

        assert first.returncode == 0, first.stderr
        assert second.returncode == 0, second.stderr
        assert first.stdout == second.stdout
        assert "ELIGIBILITY RESULT: PASS" in first.stdout
        assert "PRIVATE/CONSUMER FSBO PUBLISHING: DENIED" in first.stdout
        assert "LEAST-PRIVILEGE PUBLISHER ROLE: PASS" in first.stdout
        assert "CROSS-ORGANIZATION ISOLATION: PASS" in first.stdout
