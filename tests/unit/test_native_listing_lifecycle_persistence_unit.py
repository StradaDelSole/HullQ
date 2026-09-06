"""Unit tests for NativeListing lifecycle persistence contract composition — SLICE-0049.

Tests result-type invariants and the "authorization before any database
touch" guarantee using a connection double that raises if
`cursor()`/`transaction()` is ever called. These tests do NOT prove
PostgreSQL SQL correctness -- that is covered by
tests/persistence/test_native_listing_lifecycle_persistence.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import PublicationTransitionId
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
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionResult,
    LifecycleTransitionStatus,
    NativeListingLifecycleTransactionOwnershipError,
    fetch_lifecycle_state,
    publish_native_listing,
    withdraw_native_listing,
)


class _ConnectionMustNotBeTouched:
    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("connection.cursor() must not be called")

    def transaction(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("connection.transaction() must not be called")


class _FakeConnectionInfo:
    def __init__(self, transaction_status: Any) -> None:
        self.transaction_status = transaction_status


class _NonIdleConnection(_ConnectionMustNotBeTouched):
    def __init__(self, transaction_status: Any) -> None:
        self.info = _FakeConnectionInfo(transaction_status)


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


# ---------------------------------------------------------------------------
# Result-type invariants
# ---------------------------------------------------------------------------


def test_denied_result_requires_a_reason() -> None:
    with pytest.raises(ValueError, match="DENIED"):
        LifecycleTransitionResult(status=LifecycleTransitionStatus.DENIED)


def test_non_denied_result_rejects_a_reason() -> None:
    with pytest.raises(ValueError, match="DENIED"):
        LifecycleTransitionResult(
            status=LifecycleTransitionStatus.TRANSITIONED,
            denial_reason=PublishingEligibilityReason.NO_MEMBERSHIP,
            transition_id=PublicationTransitionId("PTR-1"),
        )


def test_transitioned_result_requires_a_transition_id() -> None:
    with pytest.raises(ValueError, match="TRANSITIONED"):
        LifecycleTransitionResult(status=LifecycleTransitionStatus.TRANSITIONED)


def test_non_transitioned_result_rejects_a_transition_id() -> None:
    with pytest.raises(ValueError, match="TRANSITIONED"):
        LifecycleTransitionResult(
            status=LifecycleTransitionStatus.NATIVE_LISTING_NOT_FOUND,
            transition_id=PublicationTransitionId("PTR-1"),
        )


# ---------------------------------------------------------------------------
# Type guards
# ---------------------------------------------------------------------------


def test_readback_rejects_a_plain_string_listing_identity() -> None:
    with pytest.raises(TypeError, match="NativeListingId"):
        fetch_lifecycle_state(_ConnectionMustNotBeTouched(), "NL-1")  # type: ignore[arg-type]


def test_publish_rejects_a_plain_string_listing_identity_before_touching_the_connection() -> None:
    account = _account()
    org = _org()
    membership = _publisher_membership(account, org)
    with pytest.raises(TypeError, match="NativeListingId"):
        publish_native_listing(
            _ConnectionMustNotBeTouched(),
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id="NL-1",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Authorization is evaluated before any database write — DENIED touches
# nothing on the connection at all.
# ---------------------------------------------------------------------------


def test_denied_publish_never_touches_the_connection() -> None:
    account = _account("ACC-1")
    org = _org("ORG-A")
    other_org = _org("ORG-B")
    membership = _publisher_membership(account, org)

    result = publish_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=other_org,
        membership=membership,
        native_listing_id=NativeListingId("NL-1"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH


def test_denied_withdraw_never_touches_the_connection() -> None:
    account = _account("ACC-1")
    org = _org("ORG-A")

    result = withdraw_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=org,
        membership=None,
        native_listing_id=NativeListingId("NL-1"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP


@pytest.mark.parametrize(
    "eligibility",
    [OrganizationPublishingEligibility.UNVERIFIED, OrganizationPublishingEligibility.INELIGIBLE],
)
def test_organization_side_gate_denies_publish_without_touching_the_connection(
    eligibility: OrganizationPublishingEligibility,
) -> None:
    account = _account("ACC-1")
    org = _org("ORG-A", eligibility=eligibility)
    membership = _publisher_membership(account, org)

    result = publish_native_listing(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-1"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED


# ---------------------------------------------------------------------------
# Transaction ownership
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("non_idle_status", ["ACTIVE", "INTRANS", "INERROR"])
def test_allowed_publish_rejects_a_non_idle_connection_before_any_write(
    non_idle_status: str,
) -> None:
    from psycopg.pq import TransactionStatus

    account = _account("ACC-1")
    org = _org("ORG-A")
    membership = _publisher_membership(account, org)
    conn = _NonIdleConnection(TransactionStatus[non_idle_status])

    with pytest.raises(NativeListingLifecycleTransactionOwnershipError):
        publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-1"),
        )


def test_allowed_publish_proceeds_past_the_ownership_guard_on_an_idle_connection() -> None:
    """Sanity check that IDLE is the only status the ownership guard accepts
    -- reaching the real cursor()/transaction() calls (which
    _ConnectionMustNotBeTouched forbids) proves the guard let it through."""
    from psycopg.pq import TransactionStatus

    account = _account("ACC-1")
    org = _org("ORG-A")
    membership = _publisher_membership(account, org)
    conn = _NonIdleConnection(TransactionStatus.IDLE)

    with pytest.raises(AssertionError, match="transaction"):
        publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-1"),
        )
