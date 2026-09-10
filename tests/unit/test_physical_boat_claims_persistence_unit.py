"""Unit tests for PhysicalBoat claim persistence contract composition — SLICE-0050.

Tests input-type enforcement, result-type invariants and the "authorization
before any database touch" guarantee using a connection double that raises
if `cursor()`/`transaction()` is ever called. These tests do NOT prove
PostgreSQL SQL correctness — that is covered by
tests/persistence/test_physical_boat_claims_persistence.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from hullq.domain.market_identity import NativeListingId
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
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
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimTransactionOwnershipError,
    PhysicalBoatClaimWriteResult,
    PhysicalBoatClaimWriteStatus,
    write_physical_boat_claim_revision,
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
    account: AccountId, org: MarketplaceOrganization, *, membership_id: str = "OM-1"
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _snapshot() -> PhysicalBoatClaimSnapshot:
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
    )


# ---------------------------------------------------------------------------
# Denied authorization never touches the database
# ---------------------------------------------------------------------------


def test_denied_authorization_never_touches_the_connection() -> None:
    """No membership -> DENIED before conn.cursor()/transaction() is reached."""
    result = write_physical_boat_claim_revision(
        _ConnectionMustNotBeTouched(),
        account_id=_account(),
        candidate_organization=_org(),
        membership=None,
        native_listing_id=NativeListingId("NL-1"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP


def test_ineligible_organization_denied_never_touches_the_connection() -> None:
    org = _org(eligibility=OrganizationPublishingEligibility.INELIGIBLE)
    account = _account()
    result = write_physical_boat_claim_revision(
        _ConnectionMustNotBeTouched(),
        account_id=account,
        candidate_organization=org,
        membership=_publisher_membership(account, org),
        native_listing_id=NativeListingId("NL-1"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_INELIGIBLE


# ---------------------------------------------------------------------------
# Input-type enforcement
# ---------------------------------------------------------------------------


def test_rejects_a_non_native_listing_id() -> None:
    account = _account()
    org = _org()
    with pytest.raises(TypeError, match="NativeListingId"):
        write_physical_boat_claim_revision(
            _ConnectionMustNotBeTouched(),
            account_id=account,
            candidate_organization=org,
            membership=_publisher_membership(account, org),
            native_listing_id="NL-1",  # type: ignore[arg-type]
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
            expected_current_revision_id=None,
            claims=_snapshot(),
        )


def test_rejects_a_non_revision_id() -> None:
    account = _account()
    org = _org()
    with pytest.raises(TypeError, match="PhysicalBoatClaimRevisionId"):
        write_physical_boat_claim_revision(
            _ConnectionMustNotBeTouched(),
            account_id=account,
            candidate_organization=org,
            membership=_publisher_membership(account, org),
            native_listing_id=NativeListingId("NL-1"),
            revision_id="PBCREV-1",  # type: ignore[arg-type]
            expected_current_revision_id=None,
            claims=_snapshot(),
        )


def test_rejects_a_non_snapshot_claims_value() -> None:
    account = _account()
    org = _org()
    with pytest.raises(TypeError, match="PhysicalBoatClaimSnapshot"):
        write_physical_boat_claim_revision(
            _ConnectionMustNotBeTouched(),
            account_id=account,
            candidate_organization=org,
            membership=_publisher_membership(account, org),
            native_listing_id=NativeListingId("NL-1"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
            expected_current_revision_id=None,
            claims={"marketed_brand_claim": "Beneteau"},  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Transaction ownership: an eligible write must refuse to touch a non-IDLE
# connection before any write.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("non_idle_status", ["ACTIVE", "INTRANS", "INERROR"])
def test_rejects_a_non_idle_connection_before_any_write(non_idle_status: str) -> None:
    from psycopg.pq import TransactionStatus

    account = _account()
    org = _org()
    conn = _NonIdleConnection(TransactionStatus[non_idle_status])

    with pytest.raises(PhysicalBoatClaimTransactionOwnershipError):
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=_publisher_membership(account, org),
            native_listing_id=NativeListingId("NL-1"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
            expected_current_revision_id=None,
            claims=_snapshot(),
        )


def test_accepts_an_idle_connection_marker() -> None:
    """Reaching the real cursor()/transaction() calls (forbidden by
    _ConnectionMustNotBeTouched) proves the ownership guard let it through."""
    from psycopg.pq import TransactionStatus

    account = _account()
    org = _org()
    conn = _NonIdleConnection(TransactionStatus.IDLE)

    with pytest.raises(AssertionError, match="transaction"):
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=_publisher_membership(account, org),
            native_listing_id=NativeListingId("NL-1"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
            expected_current_revision_id=None,
            claims=_snapshot(),
        )


# ---------------------------------------------------------------------------
# Result-type invariants
# ---------------------------------------------------------------------------


def test_denied_result_requires_a_denial_reason() -> None:
    with pytest.raises(ValueError, match="denial reason"):
        PhysicalBoatClaimWriteResult(status=PhysicalBoatClaimWriteStatus.DENIED)


def test_non_denied_result_must_not_carry_a_denial_reason() -> None:
    with pytest.raises(ValueError, match="Only a DENIED"):
        PhysicalBoatClaimWriteResult(
            status=PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE,
            denial_reason=PublishingEligibilityReason.NO_MEMBERSHIP,
        )


def test_created_result_requires_a_current_revision_id() -> None:
    with pytest.raises(ValueError, match="current_revision_id"):
        PhysicalBoatClaimWriteResult(status=PhysicalBoatClaimWriteStatus.CREATED)


def test_chain_incomplete_result_must_not_carry_a_current_revision_id() -> None:
    with pytest.raises(ValueError, match="must not carry current_revision_id"):
        PhysicalBoatClaimWriteResult(
            status=PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE,
            current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-1"),
        )
