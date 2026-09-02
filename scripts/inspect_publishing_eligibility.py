"""SLICE-0041 professional publishing eligibility owner-inspection.

Deterministic, offline demonstration of the
evaluate_native_listing_publishing_eligibility decision boundary: consumer
denial, least-privilege PUBLISHER role behavior and cross-Organization
isolation. Uses synthetic domain objects only; no network, credentials or
persistence.

Run: uv run python scripts/inspect_publishing_eligibility.py
"""

from __future__ import annotations

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
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)

ACCOUNT_X = AccountId("ACC-X")
ACCOUNT_Y = AccountId("ACC-Y")

ORG_A_ELIGIBLE_BROKER = MarketplaceOrganization(
    id=MarketplaceOrganizationId("ORG-A"),
    professional_category=ProfessionalCategory.BROKER,
    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
)
ORG_B_ELIGIBLE_DEALER = MarketplaceOrganization(
    id=MarketplaceOrganizationId("ORG-B"),
    professional_category=ProfessionalCategory.DEALER,
    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
)
ORG_C_UNVERIFIED_BROKER = MarketplaceOrganization(
    id=MarketplaceOrganizationId("ORG-C"),
    professional_category=ProfessionalCategory.BROKER,
    publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
)
ORG_D_INELIGIBLE_OTHER = MarketplaceOrganization(
    id=MarketplaceOrganizationId("ORG-D"),
    professional_category=ProfessionalCategory.OTHER_PROFESSIONAL,
    publishing_eligibility=OrganizationPublishingEligibility.INELIGIBLE,
)


def _membership(
    membership_id: str,
    account_id: AccountId,
    organization_id: MarketplaceOrganizationId,
    roles: frozenset[MembershipRole],
    state: MembershipState = MembershipState.ACTIVE,
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account_id,
        organization_id=organization_id,
        roles=roles,
        state=state,
    )


def main() -> int:
    scenarios: list[
        tuple[str, AccountId, MarketplaceOrganization, OrganizationMembership | None]
    ] = [
        (
            "eligible broker PUBLISHER",
            ACCOUNT_X,
            ORG_A_ELIGIBLE_BROKER,
            _membership(
                "M-1", ACCOUNT_X, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.PUBLISHER})
            ),
        ),
        (
            "eligible broker OWNER only",
            ACCOUNT_X,
            ORG_A_ELIGIBLE_BROKER,
            _membership(
                "M-2", ACCOUNT_X, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.OWNER})
            ),
        ),
        (
            "eligible dealer ADMIN only",
            ACCOUNT_X,
            ORG_B_ELIGIBLE_DEALER,
            _membership(
                "M-3", ACCOUNT_X, ORG_B_ELIGIBLE_DEALER.id, frozenset({MembershipRole.ADMIN})
            ),
        ),
        (
            "eligible broker OWNER+PUBLISHER",
            ACCOUNT_X,
            ORG_A_ELIGIBLE_BROKER,
            _membership(
                "M-4",
                ACCOUNT_X,
                ORG_A_ELIGIBLE_BROKER.id,
                frozenset({MembershipRole.OWNER, MembershipRole.PUBLISHER}),
            ),
        ),
        (
            "eligible dealer ADMIN+PUBLISHER",
            ACCOUNT_X,
            ORG_B_ELIGIBLE_DEALER,
            _membership(
                "M-5",
                ACCOUNT_X,
                ORG_B_ELIGIBLE_DEALER.id,
                frozenset({MembershipRole.ADMIN, MembershipRole.PUBLISHER}),
            ),
        ),
        (
            "consumer with no membership",
            ACCOUNT_Y,
            ORG_A_ELIGIBLE_BROKER,
            None,
        ),
        (
            "inactive broker PUBLISHER membership",
            ACCOUNT_X,
            ORG_A_ELIGIBLE_BROKER,
            _membership(
                "M-6",
                ACCOUNT_X,
                ORG_A_ELIGIBLE_BROKER.id,
                frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.INACTIVE,
            ),
        ),
        (
            "unverified broker organization",
            ACCOUNT_X,
            ORG_C_UNVERIFIED_BROKER,
            _membership(
                "M-7", ACCOUNT_X, ORG_C_UNVERIFIED_BROKER.id, frozenset({MembershipRole.PUBLISHER})
            ),
        ),
        (
            "ineligible organization",
            ACCOUNT_X,
            ORG_D_INELIGIBLE_OTHER,
            _membership(
                "M-8", ACCOUNT_X, ORG_D_INELIGIBLE_OTHER.id, frozenset({MembershipRole.PUBLISHER})
            ),
        ),
        (
            "publisher in Org A acting for Org B",
            ACCOUNT_X,
            ORG_B_ELIGIBLE_DEALER,
            _membership(
                "M-1", ACCOUNT_X, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.PUBLISHER})
            ),
        ),
        (
            "membership for another Account",
            ACCOUNT_X,
            ORG_A_ELIGIBLE_BROKER,
            _membership(
                "M-9", ACCOUNT_Y, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.PUBLISHER})
            ),
        ),
    ]

    print("PROFESSIONAL PUBLISHING ELIGIBILITY\n")

    all_ok = True
    expected_results: dict[str, PublishingEligibilityReason | None] = {
        "eligible broker PUBLISHER": None,
        "eligible broker OWNER only": PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        "eligible dealer ADMIN only": PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        "eligible broker OWNER+PUBLISHER": None,
        "eligible dealer ADMIN+PUBLISHER": None,
        "consumer with no membership": PublishingEligibilityReason.NO_MEMBERSHIP,
        "inactive broker PUBLISHER membership": PublishingEligibilityReason.MEMBERSHIP_INACTIVE,
        "unverified broker organization": PublishingEligibilityReason.ORGANIZATION_UNVERIFIED,
        "ineligible organization": PublishingEligibilityReason.ORGANIZATION_INELIGIBLE,
        "publisher in Org A acting for Org B": PublishingEligibilityReason.ORGANIZATION_MISMATCH,
        "membership for another Account": PublishingEligibilityReason.ACCOUNT_MISMATCH,
    }

    for label, account_id, candidate_organization, membership in scenarios:
        decision = evaluate_native_listing_publishing_eligibility(
            account_id, candidate_organization, membership
        )
        expected_reason = expected_results[label]
        if expected_reason is None:
            scenario_ok = decision.status is PublishingEligibilityStatus.ALLOWED
            outcome = "ALLOWED"
        else:
            scenario_ok = (
                decision.status is PublishingEligibilityStatus.DENIED
                and decision.reason is expected_reason
            )
            outcome = f"DENIED: {decision.reason.value if decision.reason else '?'}"
        all_ok = all_ok and scenario_ok
        marker = "" if scenario_ok else "  <-- UNEXPECTED"
        print(f"{label:<38} -> {outcome}{marker}")

    print()

    # Private/consumer FSBO publishing must be denied.
    consumer_decision = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_Y, ORG_A_ELIGIBLE_BROKER, None
    )
    consumer_denied = (
        consumer_decision.status is PublishingEligibilityStatus.DENIED
        and consumer_decision.reason is PublishingEligibilityReason.NO_MEMBERSHIP
    )

    # Least-privilege: OWNER/ADMIN alone never satisfy the role gate.
    owner_only = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_X,
        ORG_A_ELIGIBLE_BROKER,
        _membership(
            "M-LP1", ACCOUNT_X, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.OWNER})
        ),
    )
    admin_only = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_X,
        ORG_A_ELIGIBLE_BROKER,
        _membership(
            "M-LP2", ACCOUNT_X, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.ADMIN})
        ),
    )
    owner_plus_publisher = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_X,
        ORG_A_ELIGIBLE_BROKER,
        _membership(
            "M-LP3",
            ACCOUNT_X,
            ORG_A_ELIGIBLE_BROKER.id,
            frozenset({MembershipRole.OWNER, MembershipRole.PUBLISHER}),
        ),
    )
    least_privilege_ok = (
        owner_only.reason is PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED
        and admin_only.reason is PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED
        and owner_plus_publisher.status is PublishingEligibilityStatus.ALLOWED
    )

    # Cross-Organization isolation: same Account, two eligible Organizations,
    # independent memberships must not leak into each other; a membership
    # in A must never authorize B.
    membership_in_a = _membership(
        "M-XA", ACCOUNT_X, ORG_A_ELIGIBLE_BROKER.id, frozenset({MembershipRole.PUBLISHER})
    )
    membership_in_b = _membership(
        "M-XB", ACCOUNT_X, ORG_B_ELIGIBLE_DEALER.id, frozenset({MembershipRole.PUBLISHER})
    )
    allowed_for_a = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_X, ORG_A_ELIGIBLE_BROKER, membership_in_a
    )
    allowed_for_b = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_X, ORG_B_ELIGIBLE_DEALER, membership_in_b
    )
    mismatch_a_for_b = evaluate_native_listing_publishing_eligibility(
        ACCOUNT_X, ORG_B_ELIGIBLE_DEALER, membership_in_a
    )
    isolation_ok = (
        allowed_for_a.status is PublishingEligibilityStatus.ALLOWED
        and allowed_for_b.status is PublishingEligibilityStatus.ALLOWED
        and mismatch_a_for_b.status is PublishingEligibilityStatus.DENIED
        and mismatch_a_for_b.reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH
    )

    all_ok = all_ok and consumer_denied and least_privilege_ok and isolation_ok

    print(f"PRIVATE/CONSUMER FSBO PUBLISHING: {'DENIED' if consumer_denied else 'FAIL'}")
    print(f"LEAST-PRIVILEGE PUBLISHER ROLE: {'PASS' if least_privilege_ok else 'FAIL'}")
    print(f"CROSS-ORGANIZATION ISOLATION: {'PASS' if isolation_ok else 'FAIL'}")
    print(f"ELIGIBILITY RESULT: {'PASS' if all_ok else 'FAIL'}")

    if not all_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
