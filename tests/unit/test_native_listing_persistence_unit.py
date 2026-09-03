"""Unit tests for NativeListing persistence contract composition — SLICE-0043.

Tests input validation, result-type invariants and the "authorization before
any database touch" guarantee using a connection double that raises if
`cursor()`/`transaction()` is ever called. These tests do NOT prove
PostgreSQL SQL correctness — that is covered by
tests/persistence/test_native_listing_persistence.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from hullq.domain.market_identity import NativeListing, NativeListingId
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
)
from hullq.persistence.native_listing import (
    NativeListingCreationResult,
    NativeListingCreationStatus,
    create_native_listing,
    fetch_native_listing,
)


class _ConnectionMustNotBeTouched:
    """Fails the test if any database-facing method is invoked on it."""

    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("connection.cursor() must not be called")

    def transaction(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("connection.transaction() must not be called")


def _account(value: str = "ACC-1") -> AccountId:
    return AccountId(value)


def _org(
    value: str = "ORG-1",
    *,
    category: ProfessionalCategory = ProfessionalCategory.BROKER,
    eligibility: OrganizationPublishingEligibility = OrganizationPublishingEligibility.ELIGIBLE,
) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=category,
        publishing_eligibility=eligibility,
    )


def _publisher_membership(
    account: AccountId, organization: MarketplaceOrganization
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId("OM-1"),
        account_id=account,
        organization_id=organization.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _listing(value: str = "NL-1") -> NativeListing:
    return NativeListing(id=NativeListingId(value))


# ---------------------------------------------------------------------------
# Result-type invariants
# ---------------------------------------------------------------------------


def test_denied_result_requires_a_reason() -> None:
    with pytest.raises(ValueError, match="DENIED"):
        NativeListingCreationResult(status=NativeListingCreationStatus.DENIED)


def test_non_denied_result_rejects_a_reason() -> None:
    with pytest.raises(ValueError, match="DENIED"):
        NativeListingCreationResult(
            status=NativeListingCreationStatus.CREATED,
            denial_reason=PublishingEligibilityReason.NO_MEMBERSHIP,
        )


# ---------------------------------------------------------------------------
# Creation accepts only the accepted SLICE-0040 identity types
# ---------------------------------------------------------------------------


def test_create_rejects_a_plain_string_listing_identity() -> None:
    """A competing string-typed listing identity must not be interchangeable
    with the accepted NativeListing domain object."""
    with pytest.raises(TypeError, match="NativeListing"):
        create_native_listing(
            _ConnectionMustNotBeTouched(),
            account_id=_account(),
            candidate_organization=_org(),
            membership=_publisher_membership(_account(), _org()),
            listing="NL-1",  # type: ignore[arg-type]
        )


def test_market_episode_link_accepts_only_the_accepted_market_episode_id_type() -> None:
    """The optional MarketEpisode link is enforced by the SLICE-0040
    NativeListing domain object itself, not reinvented here."""
    with pytest.raises(TypeError):
        NativeListing(id=NativeListingId("NL-1"), market_episode_id="ME-1")  # type: ignore[arg-type]


def test_readback_rejects_a_plain_string_listing_identity() -> None:
    with pytest.raises(TypeError, match="NativeListingId"):
        fetch_native_listing(_ConnectionMustNotBeTouched(), "NL-1")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Optional broker listing reference validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_reference", ["", "   ", "\t\n"])
def test_broker_listing_reference_rejects_empty_value(bad_reference: str) -> None:
    with pytest.raises(ValueError, match="broker_listing_reference"):
        create_native_listing(
            _ConnectionMustNotBeTouched(),
            account_id=_account(),
            candidate_organization=_org(),
            membership=_publisher_membership(_account(), _org()),
            listing=_listing(),
            broker_listing_reference=bad_reference,
        )


def test_broker_listing_reference_none_is_valid_and_does_not_raise() -> None:
    """None must be accepted; the DENIED path below proves this without a DB
    connection by pairing it with a deterministic no-membership denial."""
    result = create_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=_account(),
        candidate_organization=_org(),
        membership=None,
        listing=_listing(),
        broker_listing_reference=None,
    )
    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP


# ---------------------------------------------------------------------------
# Authorization is evaluated before any database write — DENIED touches
# nothing on the connection at all.
# ---------------------------------------------------------------------------


def test_denied_creation_never_touches_the_connection() -> None:
    account = _account("ACC-1")
    org = _org("ORG-A")
    other_org = _org("ORG-B")
    # PUBLISHER membership for ORG-A attempting to publish for ORG-B.
    membership = _publisher_membership(account, org)

    result = create_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=other_org,
        membership=membership,
        listing=_listing(),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH


@pytest.mark.parametrize(
    ("membership_factory", "expected_reason"),
    [
        (lambda acc, org: None, PublishingEligibilityReason.NO_MEMBERSHIP),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-OWNER"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.OWNER}),
                state=MembershipState.ACTIVE,
            ),
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        ),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-ADMIN"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.ADMIN}),
                state=MembershipState.ACTIVE,
            ),
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        ),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-INACTIVE"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.INACTIVE,
            ),
            PublishingEligibilityReason.MEMBERSHIP_INACTIVE,
        ),
    ],
)
def test_ineligible_membership_shapes_deny_without_touching_the_connection(
    membership_factory: Any, expected_reason: PublishingEligibilityReason
) -> None:
    account = _account("ACC-1")
    org = _org("ORG-A")
    membership = membership_factory(account, org)

    result = create_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing(),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is expected_reason


@pytest.mark.parametrize(
    ("eligibility", "expected_reason"),
    [
        (
            OrganizationPublishingEligibility.UNVERIFIED,
            PublishingEligibilityReason.ORGANIZATION_UNVERIFIED,
        ),
        (
            OrganizationPublishingEligibility.INELIGIBLE,
            PublishingEligibilityReason.ORGANIZATION_INELIGIBLE,
        ),
    ],
)
def test_organization_side_gate_denies_without_touching_the_connection(
    eligibility: OrganizationPublishingEligibility, expected_reason: PublishingEligibilityReason
) -> None:
    account = _account("ACC-1")
    org = _org("ORG-A", eligibility=eligibility)
    membership = _publisher_membership(account, org)

    result = create_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing(),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is expected_reason
