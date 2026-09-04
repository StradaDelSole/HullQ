"""Unit tests for NativeListing offer persistence contract composition — SLICE-0045.

Tests input validation, result-type invariants and the "authorization before
any database touch" guarantee using a connection double that raises if
`cursor()`/`transaction()` is ever called. These tests do NOT prove
PostgreSQL SQL correctness — that is covered by
tests/persistence/test_native_listing_offer_persistence.py.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

import hullq.persistence.native_listing_offer as native_listing_offer_mod
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
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
from hullq.persistence.fingerprint import fingerprint_dict
from hullq.persistence.native_listing_offer import (
    NativeListingOfferTransactionOwnershipError,
    NativeListingOfferWriteResult,
    NativeListingOfferWriteStatus,
    write_native_listing_offer_revision,
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


def _offer(**overrides: object) -> NativeListingOfferSnapshot:
    kwargs: dict[str, object] = {
        "asking_price_mode": AskingPriceMode.AMOUNT,
        "location_country": "FR",
        "broker_description": "A well-maintained cruising sloop.",
        "asking_price_amount": Decimal("125000.00"),
        "currency": "EUR",
    }
    kwargs.update(overrides)
    return NativeListingOfferSnapshot(**kwargs)  # type: ignore[arg-type]


def _call(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    expected_current_revision_id: NativeListingOfferRevisionId | None = None,
) -> NativeListingOfferWriteResult:
    return write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-1"),
        revision_id=NativeListingOfferRevisionId("REV-1"),
        expected_current_revision_id=expected_current_revision_id,
        offer=_offer(),
    )


# ---------------------------------------------------------------------------
# Result-type invariants
# ---------------------------------------------------------------------------


def test_denied_result_requires_a_reason() -> None:
    with pytest.raises(ValueError, match="DENIED"):
        NativeListingOfferWriteResult(status=NativeListingOfferWriteStatus.DENIED)


def test_non_denied_result_rejects_a_reason() -> None:
    with pytest.raises(ValueError, match="DENIED"):
        NativeListingOfferWriteResult(
            status=NativeListingOfferWriteStatus.CREATED,
            denial_reason=PublishingEligibilityReason.NO_MEMBERSHIP,
            current_revision_id=NativeListingOfferRevisionId("REV-1"),
        )


@pytest.mark.parametrize(
    "status",
    [
        NativeListingOfferWriteStatus.CREATED,
        NativeListingOfferWriteStatus.REVISED,
        NativeListingOfferWriteStatus.ALREADY_EXISTS,
    ],
)
def test_statuses_requiring_a_current_revision_reject_a_missing_one(
    status: NativeListingOfferWriteStatus,
) -> None:
    with pytest.raises(ValueError, match="current_revision_id"):
        NativeListingOfferWriteResult(status=status)


@pytest.mark.parametrize(
    "status",
    [
        NativeListingOfferWriteStatus.CROSS_ORGANIZATION_DENIED,
        NativeListingOfferWriteStatus.NATIVE_LISTING_NOT_FOUND,
    ],
)
def test_statuses_without_a_current_revision_reject_one_being_supplied(
    status: NativeListingOfferWriteStatus,
) -> None:
    with pytest.raises(ValueError, match="current_revision_id"):
        NativeListingOfferWriteResult(
            status=status, current_revision_id=NativeListingOfferRevisionId("REV-1")
        )


def test_conflict_may_carry_no_current_revision() -> None:
    """CONFLICT can occur for a NativeListing that has no current revision at
    all yet -- e.g. a revision-id collision against a completely different
    NativeListing, or a stale expected_current_revision_id supplied for a
    listing that has never been written."""
    result = NativeListingOfferWriteResult(status=NativeListingOfferWriteStatus.CONFLICT)
    assert result.current_revision_id is None


def test_conflict_may_carry_a_current_revision() -> None:
    result = NativeListingOfferWriteResult(
        status=NativeListingOfferWriteStatus.CONFLICT,
        current_revision_id=NativeListingOfferRevisionId("REV-1"),
    )
    assert result.current_revision_id == NativeListingOfferRevisionId("REV-1")


# ---------------------------------------------------------------------------
# Typed-argument enforcement
# ---------------------------------------------------------------------------


def test_rejects_a_plain_string_native_listing_identity() -> None:
    with pytest.raises(TypeError, match="NativeListingId"):
        write_native_listing_offer_revision(
            _ConnectionMustNotBeTouched(),
            account_id=_account(),
            candidate_organization=_org(),
            membership=_publisher_membership(_account(), _org()),
            native_listing_id="NL-1",  # type: ignore[arg-type]
            revision_id=NativeListingOfferRevisionId("REV-1"),
            expected_current_revision_id=None,
            offer=_offer(),
        )


def test_rejects_a_plain_string_revision_identity() -> None:
    with pytest.raises(TypeError, match="NativeListingOfferRevisionId"):
        write_native_listing_offer_revision(
            _ConnectionMustNotBeTouched(),
            account_id=_account(),
            candidate_organization=_org(),
            membership=_publisher_membership(_account(), _org()),
            native_listing_id=NativeListingId("NL-1"),
            revision_id="REV-1",  # type: ignore[arg-type]
            expected_current_revision_id=None,
            offer=_offer(),
        )


def test_rejects_a_plain_string_expected_current_revision_identity() -> None:
    with pytest.raises(TypeError, match="NativeListingOfferRevisionId"):
        write_native_listing_offer_revision(
            _ConnectionMustNotBeTouched(),
            account_id=_account(),
            candidate_organization=_org(),
            membership=_publisher_membership(_account(), _org()),
            native_listing_id=NativeListingId("NL-1"),
            revision_id=NativeListingOfferRevisionId("REV-2"),
            expected_current_revision_id="REV-1",  # type: ignore[arg-type]
            offer=_offer(),
        )


def test_rejects_a_non_snapshot_offer() -> None:
    with pytest.raises(TypeError, match="NativeListingOfferSnapshot"):
        write_native_listing_offer_revision(
            _ConnectionMustNotBeTouched(),
            account_id=_account(),
            candidate_organization=_org(),
            membership=_publisher_membership(_account(), _org()),
            native_listing_id=NativeListingId("NL-1"),
            revision_id=NativeListingOfferRevisionId("REV-1"),
            expected_current_revision_id=None,
            offer={"asking_price_mode": "AMOUNT"},  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Authorization is evaluated before any database write
# ---------------------------------------------------------------------------


def test_denied_write_never_touches_the_connection() -> None:
    account = _account("ACC-1")
    org = _org("ORG-A")
    other_org = _org("ORG-B")
    membership = _publisher_membership(account, org)

    result = _call(
        _ConnectionMustNotBeTouched(), account=account, org=other_org, membership=membership
    )

    assert result.status is NativeListingOfferWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH


def test_no_membership_denies_without_touching_the_connection() -> None:
    account = _account("ACC-1")
    org = _org("ORG-A")

    result = _call(_ConnectionMustNotBeTouched(), account=account, org=org, membership=None)

    assert result.status is NativeListingOfferWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP


@pytest.mark.parametrize(
    "eligibility_reason",
    [
        OrganizationPublishingEligibility.UNVERIFIED,
        OrganizationPublishingEligibility.INELIGIBLE,
    ],
)
def test_organization_side_gate_denies_without_touching_the_connection(
    eligibility_reason: OrganizationPublishingEligibility,
) -> None:
    account = _account("ACC-1")
    org = _org("ORG-A", eligibility=eligibility_reason)
    membership = _publisher_membership(account, org)

    result = _call(_ConnectionMustNotBeTouched(), account=account, org=org, membership=membership)

    assert result.status is NativeListingOfferWriteStatus.DENIED
    assert result.denial_reason is not None


# ---------------------------------------------------------------------------
# Transaction ownership
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("non_idle_status", ["ACTIVE", "INTRANS", "INERROR"])
def test_allowed_write_rejects_a_non_idle_connection_before_any_write(
    non_idle_status: str,
) -> None:
    from psycopg.pq import TransactionStatus

    account = _account("ACC-1")
    org = _org("ORG-A")
    membership = _publisher_membership(account, org)
    conn = _NonIdleConnection(TransactionStatus[non_idle_status])

    with pytest.raises(NativeListingOfferTransactionOwnershipError):
        _call(conn, account=account, org=org, membership=membership)


def test_allowed_write_accepts_an_idle_connection_marker() -> None:
    """Sanity check that IDLE is the only status the ownership guard accepts
    -- reaching the real cursor()/transaction() calls (which
    _ConnectionMustNotBeTouched forbids) proves the guard let it through."""
    from psycopg.pq import TransactionStatus

    account = _account("ACC-1")
    org = _org("ORG-A")
    membership = _publisher_membership(account, org)
    conn = _NonIdleConnection(TransactionStatus.IDLE)

    with pytest.raises(AssertionError, match="transaction"):
        _call(conn, account=account, org=org, membership=membership)


# ---------------------------------------------------------------------------
# Decimal canonicalization: numerically-equal amounts must fingerprint equal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "equivalent_amount",
    [Decimal("125000.00"), Decimal("125000"), Decimal("1.25E+5"), Decimal("125000.000")],
)
def test_equivalent_decimal_representations_fingerprint_identically(
    equivalent_amount: Decimal,
) -> None:
    """Decimal('125000.00'), Decimal('125000') and Decimal('1.25E+5') all
    represent the same monetary value and must produce the same content
    hash, or an equivalent-content retry would be misdetected as CONFLICT
    instead of ALREADY_EXISTS. This is a pure function test (no DB);
    tests/persistence/test_native_listing_offer_persistence.py separately
    proves the real write_native_listing_offer_revision() outcome."""
    baseline = native_listing_offer_mod._offer_envelope_dict(
        "NL-1", "ACC-1", _offer(asking_price_amount=Decimal("125000.00"))
    )
    variant = native_listing_offer_mod._offer_envelope_dict(
        "NL-1", "ACC-1", _offer(asking_price_amount=equivalent_amount)
    )
    assert fingerprint_dict(baseline) == fingerprint_dict(variant)


def test_different_decimal_amounts_fingerprint_differently() -> None:
    baseline = native_listing_offer_mod._offer_envelope_dict(
        "NL-1", "ACC-1", _offer(asking_price_amount=Decimal("125000.00"))
    )
    different = native_listing_offer_mod._offer_envelope_dict(
        "NL-1", "ACC-1", _offer(asking_price_amount=Decimal("125000.01"))
    )
    assert fingerprint_dict(baseline) != fingerprint_dict(different)
