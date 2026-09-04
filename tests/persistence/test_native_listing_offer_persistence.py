"""PostgreSQL-backed NativeListing offer-facts persistence tests — SLICE-0045.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0045 Alembic head (SLICE-0043 baseline +
native_listing_offer_facts revision), mirroring the SLICE-0043 integration
test isolation pattern in tests/persistence/test_native_listing_persistence.py.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.pq import TransactionStatus

from hullq.domain.market_identity import NativeListing, NativeListingId
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    AssertionKind,
    BrokerSummaryClaim,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
    VatTaxStatusValue,
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
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferTransactionOwnershipError,
    NativeListingOfferWriteStatus,
    fetch_current_native_listing_offer,
    fetch_native_listing_offer_revision,
    list_native_listing_offer_revisions,
    write_native_listing_offer_revision,
)

# ---------------------------------------------------------------------------
# Disposable-schema fixture: genuinely-empty schema -> SLICE-0045 Alembic head
# ---------------------------------------------------------------------------


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def offer_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0045_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def offer_conn(offer_url: str) -> Generator[Any]:
    conn = psycopg.connect(offer_url)
    try:
        yield conn
    finally:
        conn.close()


def _table_names(conn: Any) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        )
        return {row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------


def _account(value: str) -> AccountId:
    return AccountId(value)


def _org(
    value: str,
    *,
    category: ProfessionalCategory = ProfessionalCategory.BROKER,
    eligibility: OrganizationPublishingEligibility = OrganizationPublishingEligibility.ELIGIBLE,
) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=category,
        publishing_eligibility=eligibility,
    )


def _membership(
    membership_id: str,
    account: AccountId,
    organization: MarketplaceOrganization,
    roles: frozenset[MembershipRole],
    *,
    state: MembershipState = MembershipState.ACTIVE,
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=organization.id,
        roles=roles,
        state=state,
    )


def _amount_offer(**overrides: object) -> NativeListingOfferSnapshot:
    kwargs: dict[str, object] = {
        "asking_price_mode": AskingPriceMode.AMOUNT,
        "location_country": "FR",
        "broker_description": "A well-maintained cruising sloop.",
        "asking_price_amount": Decimal("125000.00"),
        "currency": "EUR",
    }
    kwargs.update(overrides)
    return NativeListingOfferSnapshot(**kwargs)  # type: ignore[arg-type]


def _create_listing(
    conn: Any,
    native_listing_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    result = create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId(native_listing_id)),
    )
    assert result.status.value == "created"
    conn.commit()


# ---------------------------------------------------------------------------
# Migration boundary
# ---------------------------------------------------------------------------


def test_migration_adds_only_the_expected_offer_tables(offer_conn: Any) -> None:
    tables = _table_names(offer_conn)
    assert {"native_listing_offer_revisions", "native_listing_offer_heads"} <= tables
    # SLICE-0043 / legacy tables remain present and untouched.
    assert {"native_listings", "research_bundles", "canonical_boat_designs"} <= tables


def test_repeated_upgrade_head_is_idempotent(offer_url: str) -> None:
    alembic_upgrade_head(offer_url)
    conn = psycopg.connect(offer_url)
    try:
        assert "native_listing_offer_revisions" in _table_names(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Authorization before write
# ---------------------------------------------------------------------------


def test_eligible_publisher_can_create_first_revision(offer_conn: Any) -> None:
    account = _account("ACC-A1")
    org = _org("ORG-A1")
    membership = _membership("OM-A1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-OFFER-001", account, org, membership)

    result = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OFFER-001"),
        revision_id=NativeListingOfferRevisionId("REV-001"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )

    assert result.status is NativeListingOfferWriteStatus.CREATED
    assert result.current_revision_id == NativeListingOfferRevisionId("REV-001")


def test_missing_native_listing_denies_and_writes_nothing(offer_conn: Any) -> None:
    account = _account("ACC-A2")
    org = _org("ORG-A2")
    membership = _membership("OM-A2", account, org, frozenset({MembershipRole.PUBLISHER}))

    result = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DOES-NOT-EXIST"),
        revision_id=NativeListingOfferRevisionId("REV-002"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )

    assert result.status is NativeListingOfferWriteStatus.NATIVE_LISTING_NOT_FOUND
    offer_conn.commit()
    assert (
        fetch_native_listing_offer_revision(offer_conn, NativeListingOfferRevisionId("REV-002"))
        is None
    )


def test_ineligible_membership_denies_and_writes_nothing(offer_conn: Any) -> None:
    account = _account("ACC-A3")
    org = _org("ORG-A3")
    membership = _membership("OM-A3", account, org, frozenset({MembershipRole.OWNER}))
    _create_listing(
        offer_conn,
        "NL-OFFER-003",
        account,
        org,
        _membership("OM-A3-PUB", account, org, frozenset({MembershipRole.PUBLISHER})),
    )

    result = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OFFER-003"),
        revision_id=NativeListingOfferRevisionId("REV-003"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )

    assert result.status is NativeListingOfferWriteStatus.DENIED
    offer_conn.commit()
    assert fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-OFFER-003")) is None


def test_eligible_org_b_cannot_write_org_a_listing(offer_conn: Any) -> None:
    account_a = _account("ACC-A4")
    org_a = _org("ORG-A4")
    membership_a = _membership("OM-A4", account_a, org_a, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-OFFER-004", account_a, org_a, membership_a)

    account_b = _account("ACC-B4")
    org_b = _org("ORG-B4")
    membership_b = _membership("OM-B4", account_b, org_b, frozenset({MembershipRole.PUBLISHER}))

    result = write_native_listing_offer_revision(
        offer_conn,
        account_id=account_b,
        candidate_organization=org_b,
        membership=membership_b,
        native_listing_id=NativeListingId("NL-OFFER-004"),
        revision_id=NativeListingOfferRevisionId("REV-004"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )

    assert result.status is NativeListingOfferWriteStatus.CROSS_ORGANIZATION_DENIED
    offer_conn.commit()
    assert fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-OFFER-004")) is None


# ---------------------------------------------------------------------------
# Exact readback
# ---------------------------------------------------------------------------


def test_readback_reconstructs_exact_offer_state(offer_conn: Any) -> None:
    account = _account("ACC-RB1")
    org = _org("ORG-RB1")
    membership = _membership("OM-RB1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-RB-001", account, org, membership)

    offer = _amount_offer(
        location_region=LocationRegionClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value="Brittany"
        ),
        broker_summary=BrokerSummaryClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value="Turnkey blue-water cruiser."
        ),
        known_history_narrative=KnownHistoryNarrativeClaim(
            assertion_kind=AssertionKind.NO_KNOWN_HISTORY_DECLARED
        ),
        vat_tax_status_claim=VatTaxStatusClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=VatTaxStatusValue.VAT_PAID
        ),
    )
    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-RB-001"),
        revision_id=NativeListingOfferRevisionId("REV-RB-001"),
        expected_current_revision_id=None,
        offer=offer,
    )
    offer_conn.commit()

    record = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-RB-001"))
    assert record is not None
    assert record.revision_id == NativeListingOfferRevisionId("REV-RB-001")
    assert record.native_listing_id == NativeListingId("NL-RB-001")
    assert record.publishing_organization_id == org.id
    assert record.recorded_by_account_id == account
    assert record.recorded_at is not None
    assert record.offer == offer


def test_omission_stays_distinct_from_explicit_unknown_on_readback(offer_conn: Any) -> None:
    account = _account("ACC-RB2")
    org = _org("ORG-RB2")
    membership = _membership("OM-RB2", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-RB-002", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-RB-002"),
        revision_id=NativeListingOfferRevisionId("REV-RB-002"),
        expected_current_revision_id=None,
        offer=_amount_offer(),  # all optional fields omitted
    )
    offer_conn.commit()

    record = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-RB-002"))
    assert record is not None
    assert record.offer.location_region is None
    assert record.offer.broker_summary is None
    assert record.offer.known_history_narrative is None
    assert record.offer.vat_tax_status_claim is None


def test_poa_revision_has_no_invented_price(offer_conn: Any) -> None:
    account = _account("ACC-RB3")
    org = _org("ORG-RB3")
    membership = _membership("OM-RB3", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-RB-003", account, org, membership)

    poa_offer = _amount_offer(
        asking_price_mode=AskingPriceMode.POA, asking_price_amount=None, currency=None
    )
    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-RB-003"),
        revision_id=NativeListingOfferRevisionId("REV-RB-003"),
        expected_current_revision_id=None,
        offer=poa_offer,
    )
    offer_conn.commit()

    record = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-RB-003"))
    assert record is not None
    assert record.offer.asking_price_mode is AskingPriceMode.POA
    assert record.offer.asking_price_amount is None
    assert record.offer.currency is None


def test_readback_of_missing_offer_returns_none(offer_conn: Any) -> None:
    assert (
        fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-DOES-NOT-EXIST")) is None
    )


# ---------------------------------------------------------------------------
# Optimistic concurrency
# ---------------------------------------------------------------------------


def test_second_revision_with_correct_expectation_updates_current_state(offer_conn: Any) -> None:
    account = _account("ACC-OCC1")
    org = _org("ORG-OCC1")
    membership = _membership("OM-OCC1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-OCC-001", account, org, membership)

    first = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OCC-001"),
        revision_id=NativeListingOfferRevisionId("REV-OCC-001-A"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("100000.00")),
    )
    assert first.status is NativeListingOfferWriteStatus.CREATED
    offer_conn.commit()

    second = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OCC-001"),
        revision_id=NativeListingOfferRevisionId("REV-OCC-001-B"),
        expected_current_revision_id=NativeListingOfferRevisionId("REV-OCC-001-A"),
        offer=_amount_offer(asking_price_amount=Decimal("95000.00")),
    )
    assert second.status is NativeListingOfferWriteStatus.REVISED
    offer_conn.commit()

    current = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-OCC-001"))
    assert current is not None
    assert current.revision_id == NativeListingOfferRevisionId("REV-OCC-001-B")
    assert current.offer.asking_price_amount == Decimal("95000.00")

    # The first revision remains retained/unchanged for audit.
    first_record = fetch_native_listing_offer_revision(
        offer_conn, NativeListingOfferRevisionId("REV-OCC-001-A")
    )
    assert first_record is not None
    assert first_record.offer.asking_price_amount == Decimal("100000.00")


def test_stale_expected_revision_conflicts_and_leaves_current_unchanged(offer_conn: Any) -> None:
    account = _account("ACC-OCC2")
    org = _org("ORG-OCC2")
    membership = _membership("OM-OCC2", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-OCC-002", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OCC-002"),
        revision_id=NativeListingOfferRevisionId("REV-OCC-002-A"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("100000.00")),
    )
    offer_conn.commit()

    stale = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OCC-002"),
        revision_id=NativeListingOfferRevisionId("REV-OCC-002-STALE"),
        expected_current_revision_id=NativeListingOfferRevisionId("REV-DOES-NOT-EXIST"),
        offer=_amount_offer(asking_price_amount=Decimal("50000.00")),
    )
    assert stale.status is NativeListingOfferWriteStatus.CONFLICT
    assert stale.current_revision_id == NativeListingOfferRevisionId("REV-OCC-002-A")
    offer_conn.commit()

    current = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-OCC-002"))
    assert current is not None
    assert current.revision_id == NativeListingOfferRevisionId("REV-OCC-002-A")
    assert current.offer.asking_price_amount == Decimal("100000.00")


def test_expecting_none_when_a_current_revision_already_exists_conflicts(offer_conn: Any) -> None:
    account = _account("ACC-OCC3")
    org = _org("ORG-OCC3")
    membership = _membership("OM-OCC3", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-OCC-003", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OCC-003"),
        revision_id=NativeListingOfferRevisionId("REV-OCC-003-A"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    offer_conn.commit()

    result = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-OCC-003"),
        revision_id=NativeListingOfferRevisionId("REV-OCC-003-B"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("999.00")),
    )
    assert result.status is NativeListingOfferWriteStatus.CONFLICT


# ---------------------------------------------------------------------------
# Retry / collision semantics
# ---------------------------------------------------------------------------


def test_identical_retry_is_idempotent(offer_conn: Any) -> None:
    account = _account("ACC-IDEM1")
    org = _org("ORG-IDEM1")
    membership = _membership("OM-IDEM1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-IDEM-001", account, org, membership)
    offer = _amount_offer()

    first = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-IDEM-001"),
        revision_id=NativeListingOfferRevisionId("REV-IDEM-001"),
        expected_current_revision_id=None,
        offer=offer,
    )
    assert first.status is NativeListingOfferWriteStatus.CREATED
    offer_conn.commit()

    retry = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-IDEM-001"),
        revision_id=NativeListingOfferRevisionId("REV-IDEM-001"),
        expected_current_revision_id=None,
        offer=offer,
    )
    assert retry.status is NativeListingOfferWriteStatus.ALREADY_EXISTS
    assert retry.current_revision_id == NativeListingOfferRevisionId("REV-IDEM-001")

    history = list_native_listing_offer_revisions(offer_conn, NativeListingId("NL-IDEM-001"))
    assert len(history) == 1


def test_same_revision_id_different_content_conflicts(offer_conn: Any) -> None:
    account = _account("ACC-CONF1")
    org = _org("ORG-CONF1")
    membership = _membership("OM-CONF1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-CONF-001", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-CONF-001"),
        revision_id=NativeListingOfferRevisionId("REV-CONF-001"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("100000.00")),
    )
    offer_conn.commit()

    conflict = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-CONF-001"),
        revision_id=NativeListingOfferRevisionId("REV-CONF-001"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("999999.00")),
    )
    assert conflict.status is NativeListingOfferWriteStatus.CONFLICT
    offer_conn.commit()

    current = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-CONF-001"))
    assert current is not None
    assert current.offer.asking_price_amount == Decimal("100000.00")


def test_retry_after_superseded_returns_already_exists_with_real_current_head(
    offer_conn: Any,
) -> None:
    """An idempotent retry of a revision that is no longer current must not
    silently recreate or re-promote it; ALREADY_EXISTS must surface the real
    current head."""
    account = _account("ACC-SUP1")
    org = _org("ORG-SUP1")
    membership = _membership("OM-SUP1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-SUP-001", account, org, membership)
    first_offer = _amount_offer(asking_price_amount=Decimal("100000.00"))

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-SUP-001"),
        revision_id=NativeListingOfferRevisionId("REV-SUP-001-A"),
        expected_current_revision_id=None,
        offer=first_offer,
    )
    offer_conn.commit()

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-SUP-001"),
        revision_id=NativeListingOfferRevisionId("REV-SUP-001-B"),
        expected_current_revision_id=NativeListingOfferRevisionId("REV-SUP-001-A"),
        offer=_amount_offer(asking_price_amount=Decimal("90000.00")),
    )
    offer_conn.commit()

    retry_of_first = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-SUP-001"),
        revision_id=NativeListingOfferRevisionId("REV-SUP-001-A"),
        expected_current_revision_id=None,
        offer=first_offer,
    )
    assert retry_of_first.status is NativeListingOfferWriteStatus.ALREADY_EXISTS
    assert retry_of_first.current_revision_id == NativeListingOfferRevisionId("REV-SUP-001-B")

    current = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-SUP-001"))
    assert current is not None
    assert current.revision_id == NativeListingOfferRevisionId("REV-SUP-001-B")


def test_same_revision_id_under_a_different_listing_conflicts(offer_conn: Any) -> None:
    account = _account("ACC-CONF2")
    org = _org("ORG-CONF2")
    membership = _membership("OM-CONF2", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-CONF-002A", account, org, membership)
    _create_listing(offer_conn, "NL-CONF-002B", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-CONF-002A"),
        revision_id=NativeListingOfferRevisionId("REV-CONF-002-SHARED"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    offer_conn.commit()

    conflict = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-CONF-002B"),
        revision_id=NativeListingOfferRevisionId("REV-CONF-002-SHARED"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    assert conflict.status is NativeListingOfferWriteStatus.CONFLICT
    offer_conn.commit()

    assert fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-CONF-002B")) is None


# ---------------------------------------------------------------------------
# Transaction ownership — CREATED/REVISED must always mean durable
# ---------------------------------------------------------------------------


def test_write_on_a_connection_with_an_open_implicit_transaction_fails_closed(
    offer_conn: Any, offer_url: str
) -> None:
    account = _account("ACC-TXN1")
    org = _org("ORG-TXN1")
    membership = _membership("OM-TXN1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-TXN-001", account, org, membership)

    pre_existing = fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-TXN-001"))
    assert pre_existing is None
    assert offer_conn.info.transaction_status != TransactionStatus.IDLE

    with pytest.raises(NativeListingOfferTransactionOwnershipError):
        write_native_listing_offer_revision(
            offer_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-TXN-001"),
            revision_id=NativeListingOfferRevisionId("REV-TXN-001"),
            expected_current_revision_id=None,
            offer=_amount_offer(),
        )

    offer_conn.rollback()
    verify = psycopg.connect(offer_url)
    try:
        assert fetch_current_native_listing_offer(verify, NativeListingId("NL-TXN-001")) is None
    finally:
        verify.close()


def test_created_result_is_immediately_durable_from_a_separate_connection(offer_url: str) -> None:
    writer_conn = psycopg.connect(offer_url)
    try:
        account = _account("ACC-TXN2")
        org = _org("ORG-TXN2")
        membership = _membership("OM-TXN2", account, org, frozenset({MembershipRole.PUBLISHER}))
        _create_listing(writer_conn, "NL-TXN-002", account, org, membership)

        assert writer_conn.info.transaction_status == TransactionStatus.IDLE
        result = write_native_listing_offer_revision(
            writer_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-TXN-002"),
            revision_id=NativeListingOfferRevisionId("REV-TXN-002"),
            expected_current_revision_id=None,
            offer=_amount_offer(),
        )
        assert result.status is NativeListingOfferWriteStatus.CREATED
        # No writer_conn.commit() call — durability must not depend on it.
    finally:
        writer_conn.close()

    reader_conn = psycopg.connect(offer_url)
    try:
        record = fetch_current_native_listing_offer(reader_conn, NativeListingId("NL-TXN-002"))
    finally:
        reader_conn.close()

    assert record is not None
    assert record.revision_id == NativeListingOfferRevisionId("REV-TXN-002")


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency
# ---------------------------------------------------------------------------


def test_concurrent_conflicting_revisions_resolve_deterministically(offer_url: str) -> None:
    """Two concurrent writers racing to become the first revision for the
    same NativeListing must resolve as exactly one CREATED and one CONFLICT,
    never two successful writes."""
    setup_conn = psycopg.connect(offer_url)
    try:
        account = _account("ACC-RACE1")
        org = _org("ORG-RACE1")
        membership = _membership("OM-RACE1", account, org, frozenset({MembershipRole.PUBLISHER}))
        _create_listing(setup_conn, "NL-RACE-001", account, org, membership)
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(revision_suffix: str) -> None:
        try:
            conn = psycopg.connect(offer_url)
            try:
                barrier.wait(timeout=10)
                result = write_native_listing_offer_revision(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-RACE-001"),
                    revision_id=NativeListingOfferRevisionId(f"REV-RACE-001-{revision_suffix}"),
                    expected_current_revision_id=None,
                    offer=_amount_offer(),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("A",)),
        threading.Thread(target=_worker, args=("B",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(NativeListingOfferWriteStatus.CREATED) == 1, statuses
    assert statuses.count(NativeListingOfferWriteStatus.CONFLICT) == 1, statuses

    verify = psycopg.connect(offer_url)
    try:
        history = list_native_listing_offer_revisions(verify, NativeListingId("NL-RACE-001"))
        assert len(history) == 1
    finally:
        verify.close()
