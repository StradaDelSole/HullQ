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
    assert record.previous_revision_id is None


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
    assert current.previous_revision_id == NativeListingOfferRevisionId("REV-OCC-001-A")

    # The first revision remains retained/unchanged for audit.
    first_record = fetch_native_listing_offer_revision(
        offer_conn, NativeListingOfferRevisionId("REV-OCC-001-A")
    )
    assert first_record is not None
    assert first_record.offer.asking_price_amount == Decimal("100000.00")
    assert first_record.previous_revision_id is None


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
# Exact predecessor relationship (previous_offer_revision_id)
# ---------------------------------------------------------------------------


def test_previous_revision_id_chain_across_three_revisions(offer_conn: Any) -> None:
    """A -> B -> C: each revision's previous_revision_id is the exact
    durable head validated immediately before it was inserted, and every
    historical revision's previous_revision_id remains unchanged after later
    revisions are written."""
    account = _account("ACC-CHAIN1")
    org = _org("ORG-CHAIN1")
    membership = _membership("OM-CHAIN1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-CHAIN-001", account, org, membership)
    listing_id = NativeListingId("NL-CHAIN-001")
    rev_a = NativeListingOfferRevisionId("REV-CHAIN-001-A")
    rev_b = NativeListingOfferRevisionId("REV-CHAIN-001-B")
    rev_c = NativeListingOfferRevisionId("REV-CHAIN-001-C")

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=listing_id,
        revision_id=rev_a,
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("300000.00")),
    )
    offer_conn.commit()

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=listing_id,
        revision_id=rev_b,
        expected_current_revision_id=rev_a,
        offer=_amount_offer(asking_price_amount=Decimal("290000.00")),
    )
    offer_conn.commit()

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=listing_id,
        revision_id=rev_c,
        expected_current_revision_id=rev_b,
        offer=_amount_offer(asking_price_amount=Decimal("280000.00")),
    )
    offer_conn.commit()

    record_a = fetch_native_listing_offer_revision(offer_conn, rev_a)
    record_b = fetch_native_listing_offer_revision(offer_conn, rev_b)
    record_c = fetch_native_listing_offer_revision(offer_conn, rev_c)
    assert record_a is not None and record_a.previous_revision_id is None
    assert record_b is not None and record_b.previous_revision_id == rev_a
    assert record_c is not None and record_c.previous_revision_id == rev_b

    current = fetch_current_native_listing_offer(offer_conn, listing_id)
    assert current is not None
    assert current.revision_id == rev_c
    assert current.previous_revision_id == rev_b

    # Historical predecessor values are immutable: re-reading A and B after
    # C was written must return the exact same previous_revision_id as
    # observed right after each was created.
    record_a_again = fetch_native_listing_offer_revision(offer_conn, rev_a)
    record_b_again = fetch_native_listing_offer_revision(offer_conn, rev_b)
    assert record_a_again is not None and record_a_again.previous_revision_id is None
    assert record_b_again is not None and record_b_again.previous_revision_id == rev_a


# ---------------------------------------------------------------------------
# PostgreSQL-enforced same-NativeListing head/predecessor integrity
# ---------------------------------------------------------------------------


def test_db_rejects_a_head_row_pointing_at_a_different_listings_revision(offer_conn: Any) -> None:
    """heads.native_listing_id = A while
    heads.current_offer_revision_id = a revision belonging to listing B must
    be impossible in any DB-valid state -- proven here with a raw SQL
    attempt that bypasses write_native_listing_offer_revision() entirely."""
    from psycopg.errors import ForeignKeyViolation

    account = _account("ACC-FKINT1")
    org = _org("ORG-FKINT1")
    membership = _membership("OM-FKINT1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-FKINT-001A", account, org, membership)
    _create_listing(offer_conn, "NL-FKINT-001B", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-FKINT-001A"),
        revision_id=NativeListingOfferRevisionId("REV-FKINT-001A"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    offer_conn.commit()

    with pytest.raises(ForeignKeyViolation), offer_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO native_listing_offer_heads "
            "(native_listing_id, current_offer_revision_id) VALUES (%s, %s)",
            ["NL-FKINT-001B", "REV-FKINT-001A"],
        )
    offer_conn.rollback()

    assert fetch_current_native_listing_offer(offer_conn, NativeListingId("NL-FKINT-001B")) is None


def test_db_rejects_a_previous_revision_pointing_at_a_different_listing(offer_conn: Any) -> None:
    """previous_offer_revision_id must obey the same same-listing guarantee
    as the head pointer, proven with a raw SQL insert."""
    from psycopg.errors import ForeignKeyViolation

    account = _account("ACC-FKINT2")
    org = _org("ORG-FKINT2")
    membership = _membership("OM-FKINT2", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-FKINT-002A", account, org, membership)
    _create_listing(offer_conn, "NL-FKINT-002B", account, org, membership)

    write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-FKINT-002A"),
        revision_id=NativeListingOfferRevisionId("REV-FKINT-002A"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    offer_conn.commit()

    with pytest.raises(ForeignKeyViolation), offer_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO native_listing_offer_revisions "
            "(offer_revision_id, native_listing_id, publishing_organization_id, "
            " recorded_by_account_id, asking_price_mode, location_country, "
            " broker_description, previous_offer_revision_id, content_hash) "
            "VALUES (%s, %s, %s, %s, 'POA', 'FR', 'x', %s, %s)",
            [
                "REV-FKINT-002B",
                "NL-FKINT-002B",
                org.id.value,
                account.value,
                "REV-FKINT-002A",  # belongs to listing A, not B
                "0" * 64,
            ],
        )
    offer_conn.rollback()

    assert (
        fetch_native_listing_offer_revision(
            offer_conn, NativeListingOfferRevisionId("REV-FKINT-002B")
        )
        is None
    )


# ---------------------------------------------------------------------------
# SQL assertion-kind/value NULL-hole adversarial tests
# ---------------------------------------------------------------------------


def _raw_insert_revision(conn: Any, **overrides: Any) -> None:
    columns = {
        "offer_revision_id": "REV-RAW",
        "native_listing_id": "NL-RAW",
        "publishing_organization_id": "ORG-RAW",
        "recorded_by_account_id": "ACC-RAW",
        "asking_price_mode": "POA",
        "location_country": "FR",
        "broker_description": "x",
        "content_hash": "0" * 64,
    }
    columns.update(overrides)
    column_names = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO native_listing_offer_revisions ({column_names}) VALUES ({placeholders})",
            list(columns.values()),
        )


@pytest.mark.parametrize(
    ("kind_column", "value_column", "hidden_value"),
    [
        ("location_region_assertion_kind", "location_region_value", "hidden durable value"),
        ("broker_summary_assertion_kind", "broker_summary_value", "hidden durable value"),
        (
            "known_history_narrative_assertion_kind",
            "known_history_narrative_value",
            "hidden durable value",
        ),
        ("vat_tax_status_assertion_kind", "vat_tax_status_value", "VAT_PAID"),
    ],
)
def test_db_rejects_null_kind_with_a_non_null_value(
    offer_conn: Any, kind_column: str, value_column: str, hidden_value: str
) -> None:
    """kind IS NULL (omission) with a non-NULL value must be rejected --
    the `(kind = 'VALUE_ASSERTION') = (value IS NOT NULL)` equality form
    this replaces would have silently accepted this via SQL's NULL-
    propagating three-valued logic, letting a durable value hide behind an
    apparently-omitted field."""
    from psycopg.errors import CheckViolation

    account = _account("ACC-NULLHOLE1")
    org = _org("ORG-NULLHOLE1")
    membership = _membership("OM-NULLHOLE1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-NULLHOLE-001", account, org, membership)

    with pytest.raises(CheckViolation):
        _raw_insert_revision(
            offer_conn,
            native_listing_id="NL-NULLHOLE-001",
            publishing_organization_id=org.id.value,
            recorded_by_account_id=account.value,
            **{value_column: hidden_value},
        )
    offer_conn.rollback()


@pytest.mark.parametrize(
    ("kind_column", "value_column", "bad_kind"),
    [
        ("location_region_assertion_kind", "location_region_value", "NOT_APPLICABLE"),
        ("broker_summary_assertion_kind", "broker_summary_value", "UNKNOWN"),
        ("known_history_narrative_assertion_kind", "known_history_narrative_value", "PRESENT"),
        ("vat_tax_status_assertion_kind", "vat_tax_status_value", "NOT_APPLICABLE"),
    ],
)
def test_db_rejects_a_disallowed_assertion_kind_for_the_field(
    offer_conn: Any, kind_column: str, value_column: str, bad_kind: str
) -> None:
    from psycopg.errors import CheckViolation

    account = _account("ACC-NULLHOLE2")
    org = _org("ORG-NULLHOLE2")
    membership = _membership("OM-NULLHOLE2", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-NULLHOLE-002", account, org, membership)

    with pytest.raises(CheckViolation):
        _raw_insert_revision(
            offer_conn,
            native_listing_id="NL-NULLHOLE-002",
            publishing_organization_id=org.id.value,
            recorded_by_account_id=account.value,
            **{kind_column: bad_kind},
        )
    offer_conn.rollback()


def test_db_rejects_a_whitespace_only_value_assertion_text(offer_conn: Any) -> None:
    from psycopg.errors import CheckViolation

    account = _account("ACC-NULLHOLE3")
    org = _org("ORG-NULLHOLE3")
    membership = _membership("OM-NULLHOLE3", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-NULLHOLE-003", account, org, membership)

    with pytest.raises(CheckViolation):
        _raw_insert_revision(
            offer_conn,
            native_listing_id="NL-NULLHOLE-003",
            publishing_organization_id=org.id.value,
            recorded_by_account_id=account.value,
            location_region_assertion_kind="VALUE_ASSERTION",
            location_region_value="   ",
        )
    offer_conn.rollback()


def test_db_rejects_non_finite_asking_price_amount(offer_conn: Any) -> None:
    """Defense-in-depth: the DB CHECK constraint independently rejects
    NaN/Infinity/-Infinity even if a caller bypassed the domain-layer
    Decimal.is_finite() guard."""
    from psycopg.errors import CheckViolation

    account = _account("ACC-NULLHOLE4")
    org = _org("ORG-NULLHOLE4")
    membership = _membership("OM-NULLHOLE4", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-NULLHOLE-004", account, org, membership)

    with pytest.raises(CheckViolation):
        _raw_insert_revision(
            offer_conn,
            native_listing_id="NL-NULLHOLE-004",
            publishing_organization_id=org.id.value,
            recorded_by_account_id=account.value,
            asking_price_mode="AMOUNT",
            asking_price_amount="NaN",
            currency="EUR",
        )
    offer_conn.rollback()


# ---------------------------------------------------------------------------
# Decimal canonicalization: equivalent representations are ALREADY_EXISTS
# ---------------------------------------------------------------------------


def test_equivalent_decimal_amount_retry_is_already_exists_not_conflict(offer_conn: Any) -> None:
    account = _account("ACC-DECIMAL1")
    org = _org("ORG-DECIMAL1")
    membership = _membership("OM-DECIMAL1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_listing(offer_conn, "NL-DECIMAL-001", account, org, membership)

    first = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DECIMAL-001"),
        revision_id=NativeListingOfferRevisionId("REV-DECIMAL-001"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("125000.00")),
    )
    assert first.status is NativeListingOfferWriteStatus.CREATED
    offer_conn.commit()

    retry_with_equivalent_representation = write_native_listing_offer_revision(
        offer_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DECIMAL-001"),
        revision_id=NativeListingOfferRevisionId("REV-DECIMAL-001"),
        expected_current_revision_id=None,
        offer=_amount_offer(asking_price_amount=Decimal("125000")),
    )
    assert (
        retry_with_equivalent_representation.status is NativeListingOfferWriteStatus.ALREADY_EXISTS
    )

    history = list_native_listing_offer_revisions(offer_conn, NativeListingId("NL-DECIMAL-001"))
    assert len(history) == 1


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


def test_concurrent_cross_listing_revision_id_collision_resolves_to_conflict(
    offer_url: str,
) -> None:
    """Two DIFFERENT NativeListings racing to claim the SAME client-supplied
    offer_revision_id must resolve as exactly one CREATED and one CONFLICT,
    with no unhandled PostgreSQL exception escaping and neither listing
    ending up pointed at the wrong head. The FOR UPDATE lock taken in
    write_native_listing_offer_revision() only serializes writers for one
    NativeListingId; offer_revision_id is a global PRIMARY KEY shared across
    all listings, so two different listings' writers do not contend for the
    same row lock and can genuinely race at the database level."""
    setup_conn = psycopg.connect(offer_url)
    try:
        account = _account("ACC-RACE2")
        org = _org("ORG-RACE2")
        membership = _membership("OM-RACE2", account, org, frozenset({MembershipRole.PUBLISHER}))
        _create_listing(setup_conn, "NL-RACE-002A", account, org, membership)
        _create_listing(setup_conn, "NL-RACE-002B", account, org, membership)
    finally:
        setup_conn.close()

    shared_revision_id = "REV-RACE-002-SHARED"
    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(listing_suffix: str) -> None:
        try:
            conn = psycopg.connect(offer_url)
            try:
                barrier.wait(timeout=10)
                result = write_native_listing_offer_revision(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(f"NL-RACE-002{listing_suffix}"),
                    revision_id=NativeListingOfferRevisionId(shared_revision_id),
                    expected_current_revision_id=None,
                    offer=_amount_offer(),
                )
                results.append((listing_suffix, result))
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
    statuses = [result.status for _, result in results]
    assert statuses.count(NativeListingOfferWriteStatus.CREATED) == 1, statuses
    assert statuses.count(NativeListingOfferWriteStatus.CONFLICT) == 1, statuses

    winner_suffix = next(
        suffix for suffix, r in results if r.status is NativeListingOfferWriteStatus.CREATED
    )
    loser_suffix = "B" if winner_suffix == "A" else "A"

    verify = psycopg.connect(offer_url)
    try:
        winner_current = fetch_current_native_listing_offer(
            verify, NativeListingId(f"NL-RACE-002{winner_suffix}")
        )
        loser_current = fetch_current_native_listing_offer(
            verify, NativeListingId(f"NL-RACE-002{loser_suffix}")
        )
    finally:
        verify.close()

    assert winner_current is not None
    assert winner_current.revision_id == NativeListingOfferRevisionId(shared_revision_id)
    assert winner_current.native_listing_id == NativeListingId(f"NL-RACE-002{winner_suffix}")
    # The losing listing must never end up pointed at the winner's revision.
    assert loser_current is None
