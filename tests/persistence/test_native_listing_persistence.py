"""PostgreSQL-backed NativeListing persistence tests — SLICE-0043.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0043 Alembic head (SLICE-0042 baseline +
native_listing_persistence revision), mirroring the SLICE-0042 integration
test isolation pattern in tests/persistence/test_alembic_baseline_integration.py.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.errors import CheckViolation

from hullq.domain.market_identity import MarketEpisodeId, NativeListing, NativeListingId
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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.native_listing import (
    NativeListingCreationStatus,
    create_native_listing,
    fetch_native_listing,
)

# ---------------------------------------------------------------------------
# Disposable-schema fixture: genuinely-empty schema -> SLICE-0043 Alembic head
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
def listing_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0043_{uuid.uuid4().hex[:16]}"
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
def listing_conn(listing_url: str) -> Generator[Any]:
    conn = psycopg.connect(listing_url)
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


def _row_count(conn: Any, native_listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listings WHERE native_listing_id = %s",
            [native_listing_id],
        )
        return int(cur.fetchone()[0])


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


def _listing(value: str, *, market_episode_id: str | None = None) -> NativeListing:
    return NativeListing(
        id=NativeListingId(value),
        market_episode_id=MarketEpisodeId(market_episode_id) if market_episode_id else None,
    )


# ---------------------------------------------------------------------------
# Migration boundary
# ---------------------------------------------------------------------------


def test_migration_adds_only_native_listings_table(listing_conn: Any) -> None:
    tables = _table_names(listing_conn)
    assert "native_listings" in tables
    # Legacy 001/002 tables remain present and untouched by the new revision.
    assert {"research_bundles", "canonical_boat_designs"} <= tables


def test_repeated_upgrade_head_is_idempotent(listing_url: str) -> None:
    alembic_upgrade_head(listing_url)  # second call must not raise or duplicate DDL
    conn = psycopg.connect(listing_url)
    try:
        assert "native_listings" in _table_names(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Authorization before write
# ---------------------------------------------------------------------------


def test_eligible_publisher_can_create(listing_conn: Any) -> None:
    account = _account("ACC-A1")
    org = _org("ORG-A")
    membership = _membership("OM-A1", account, org, frozenset({MembershipRole.PUBLISHER}))

    result = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-AUTH-001"),
    )

    assert result.status is NativeListingCreationStatus.CREATED
    assert _row_count(listing_conn, "NL-AUTH-001") == 1


@pytest.mark.parametrize(
    ("roles", "state", "expected_reason"),
    [
        (
            frozenset({MembershipRole.OWNER}),
            MembershipState.ACTIVE,
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        ),
        (
            frozenset({MembershipRole.ADMIN}),
            MembershipState.ACTIVE,
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        ),
        (
            frozenset({MembershipRole.PUBLISHER}),
            MembershipState.INACTIVE,
            PublishingEligibilityReason.MEMBERSHIP_INACTIVE,
        ),
    ],
)
def test_ineligible_membership_shape_denies_and_writes_nothing(
    listing_conn: Any,
    roles: frozenset[MembershipRole],
    state: MembershipState,
    expected_reason: PublishingEligibilityReason,
) -> None:
    account = _account("ACC-A2")
    org = _org("ORG-A")
    membership = _membership("OM-A2", account, org, roles, state=state)

    result = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-AUTH-002"),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is expected_reason
    assert _row_count(listing_conn, "NL-AUTH-002") == 0


def test_no_membership_denies_and_writes_nothing(listing_conn: Any) -> None:
    result = create_native_listing(
        listing_conn,
        account_id=_account("ACC-A3"),
        candidate_organization=_org("ORG-A"),
        membership=None,
        listing=_listing("NL-AUTH-003"),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP
    assert _row_count(listing_conn, "NL-AUTH-003") == 0


def test_unverified_organization_denies_and_writes_nothing(listing_conn: Any) -> None:
    account = _account("ACC-A4")
    org = _org("ORG-A", eligibility=OrganizationPublishingEligibility.UNVERIFIED)
    membership = _membership("OM-A4", account, org, frozenset({MembershipRole.PUBLISHER}))

    result = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-AUTH-004"),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_UNVERIFIED
    assert _row_count(listing_conn, "NL-AUTH-004") == 0


def test_ineligible_organization_denies_and_writes_nothing(listing_conn: Any) -> None:
    account = _account("ACC-A5")
    org = _org("ORG-A", eligibility=OrganizationPublishingEligibility.INELIGIBLE)
    membership = _membership("OM-A5", account, org, frozenset({MembershipRole.PUBLISHER}))

    result = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-AUTH-005"),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_INELIGIBLE
    assert _row_count(listing_conn, "NL-AUTH-005") == 0


def test_membership_for_another_account_denies_and_writes_nothing(listing_conn: Any) -> None:
    org = _org("ORG-A")
    membership = _membership(
        "OM-A6", _account("ACC-OTHER"), org, frozenset({MembershipRole.PUBLISHER})
    )

    result = create_native_listing(
        listing_conn,
        account_id=_account("ACC-A6"),
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-AUTH-006"),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ACCOUNT_MISMATCH
    assert _row_count(listing_conn, "NL-AUTH-006") == 0


def test_publisher_for_org_a_cannot_create_on_behalf_of_org_b(listing_conn: Any) -> None:
    account = _account("ACC-A7")
    org_a = _org("ORG-A")
    org_b = _org("ORG-B")
    membership_in_a = _membership("OM-A7", account, org_a, frozenset({MembershipRole.PUBLISHER}))

    result = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org_b,
        membership=membership_in_a,
        listing=_listing("NL-AUTH-007"),
    )

    assert result.status is NativeListingCreationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_MISMATCH
    assert _row_count(listing_conn, "NL-AUTH-007") == 0


# ---------------------------------------------------------------------------
# Durable creation / exact readback
# ---------------------------------------------------------------------------


def test_readback_reconstructs_typed_identities(listing_conn: Any) -> None:
    account = _account("ACC-RB1")
    org = _org("ORG-RB1")
    membership = _membership("OM-RB1", account, org, frozenset({MembershipRole.PUBLISHER}))
    listing = _listing("NL-RB-001", market_episode_id="ME-RB-001")

    create_result = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
        broker_listing_reference="BROKER-REF-42",
    )
    assert create_result.status is NativeListingCreationStatus.CREATED

    record = fetch_native_listing(listing_conn, NativeListingId("NL-RB-001"))
    assert record is not None
    assert record.listing == listing
    assert record.listing.market_episode_id == MarketEpisodeId("ME-RB-001")
    assert record.publishing_organization_id == org.id
    assert record.created_by_account_id == account
    assert record.broker_listing_reference == "BROKER-REF-42"
    assert record.created_at is not None


def test_unresolved_listing_round_trips_with_no_market_episode(listing_conn: Any) -> None:
    account = _account("ACC-RB2")
    org = _org("ORG-RB2")
    membership = _membership("OM-RB2", account, org, frozenset({MembershipRole.PUBLISHER}))

    create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-RB-002"),
    )

    record = fetch_native_listing(listing_conn, NativeListingId("NL-RB-002"))
    assert record is not None
    assert record.listing.market_episode_id is None
    assert record.listing.is_resolved is False


def test_readback_of_missing_listing_returns_none(listing_conn: Any) -> None:
    assert fetch_native_listing(listing_conn, NativeListingId("NL-DOES-NOT-EXIST")) is None


def test_broker_listing_reference_round_trips_exactly(listing_conn: Any) -> None:
    account = _account("ACC-RB3")
    org = _org("ORG-RB3")
    membership = _membership("OM-RB3", account, org, frozenset({MembershipRole.PUBLISHER}))
    raw_reference = "  Broker/Ref-007 (do not normalize) "

    create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-RB-003"),
        broker_listing_reference=raw_reference,
    )

    record = fetch_native_listing(listing_conn, NativeListingId("NL-RB-003"))
    assert record is not None
    assert record.broker_listing_reference == raw_reference


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_identical_retry_is_idempotent_and_preserves_created_at(listing_conn: Any) -> None:
    account = _account("ACC-IDEM1")
    org = _org("ORG-IDEM1")
    membership = _membership("OM-IDEM1", account, org, frozenset({MembershipRole.PUBLISHER}))
    listing = _listing("NL-IDEM-001", market_episode_id="ME-IDEM-001")

    first = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
        broker_listing_reference="BROKER-REF-IDEM",
    )
    assert first.status is NativeListingCreationStatus.CREATED
    first_record = fetch_native_listing(listing_conn, listing.id)
    assert first_record is not None

    second = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
        broker_listing_reference="BROKER-REF-IDEM",
    )
    assert second.status is NativeListingCreationStatus.ALREADY_EXISTS
    assert second.denial_reason is None

    assert _row_count(listing_conn, "NL-IDEM-001") == 1
    second_record = fetch_native_listing(listing_conn, listing.id)
    assert second_record is not None
    assert second_record.created_at == first_record.created_at


# ---------------------------------------------------------------------------
# Conflict — fail closed, never overwrite
# ---------------------------------------------------------------------------


def test_same_id_different_broker_reference_conflicts(listing_conn: Any) -> None:
    account = _account("ACC-CONF1")
    org = _org("ORG-CONF1")
    membership = _membership("OM-CONF1", account, org, frozenset({MembershipRole.PUBLISHER}))
    listing = _listing("NL-CONF-001")

    create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
        broker_listing_reference="BROKER-REF-ORIGINAL",
    )
    original = fetch_native_listing(listing_conn, listing.id)
    assert original is not None

    conflict = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
        broker_listing_reference="BROKER-REF-CHANGED",
    )

    assert conflict.status is NativeListingCreationStatus.CONFLICT
    assert conflict.denial_reason is None
    assert _row_count(listing_conn, "NL-CONF-001") == 1
    after = fetch_native_listing(listing_conn, listing.id)
    assert after == original


def test_same_id_different_market_episode_conflicts(listing_conn: Any) -> None:
    account = _account("ACC-CONF2")
    org = _org("ORG-CONF2")
    membership = _membership("OM-CONF2", account, org, frozenset({MembershipRole.PUBLISHER}))

    create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-CONF-002", market_episode_id="ME-ORIGINAL"),
    )
    original = fetch_native_listing(listing_conn, NativeListingId("NL-CONF-002"))
    assert original is not None

    conflict = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-CONF-002", market_episode_id="ME-CHANGED"),
    )

    assert conflict.status is NativeListingCreationStatus.CONFLICT
    assert _row_count(listing_conn, "NL-CONF-002") == 1
    after = fetch_native_listing(listing_conn, NativeListingId("NL-CONF-002"))
    assert after == original


def test_same_id_under_another_organization_conflicts_rather_than_overwriting(
    listing_conn: Any,
) -> None:
    account = _account("ACC-CONF3")
    org_a = _org("ORG-CONF3A")
    org_c = _org("ORG-CONF3C")
    membership_a = _membership("OM-CONF3A", account, org_a, frozenset({MembershipRole.PUBLISHER}))
    membership_c = _membership("OM-CONF3C", account, org_c, frozenset({MembershipRole.PUBLISHER}))
    listing = _listing("NL-CONF-003")

    create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org_a,
        membership=membership_a,
        listing=listing,
    )
    original = fetch_native_listing(listing_conn, listing.id)
    assert original is not None
    assert original.publishing_organization_id == org_a.id

    conflict = create_native_listing(
        listing_conn,
        account_id=account,
        candidate_organization=org_c,
        membership=membership_c,
        listing=listing,
    )

    assert conflict.status is NativeListingCreationStatus.CONFLICT
    assert _row_count(listing_conn, "NL-CONF-003") == 1
    after = fetch_native_listing(listing_conn, listing.id)
    assert after == original
    assert after.publishing_organization_id == org_a.id


def test_same_id_by_another_account_conflicts_rather_than_overwriting_provenance(
    listing_conn: Any,
) -> None:
    org = _org("ORG-CONF4")
    account_a = _account("ACC-CONF4A")
    account_b = _account("ACC-CONF4B")
    membership_a = _membership("OM-CONF4A", account_a, org, frozenset({MembershipRole.PUBLISHER}))
    membership_b = _membership("OM-CONF4B", account_b, org, frozenset({MembershipRole.PUBLISHER}))
    listing = _listing("NL-CONF-004")

    create_native_listing(
        listing_conn,
        account_id=account_a,
        candidate_organization=org,
        membership=membership_a,
        listing=listing,
    )
    original = fetch_native_listing(listing_conn, listing.id)
    assert original is not None
    assert original.created_by_account_id == account_a

    conflict = create_native_listing(
        listing_conn,
        account_id=account_b,
        candidate_organization=org,
        membership=membership_b,
        listing=listing,
    )

    assert conflict.status is NativeListingCreationStatus.CONFLICT
    assert _row_count(listing_conn, "NL-CONF-004") == 1
    after = fetch_native_listing(listing_conn, listing.id)
    assert after == original
    assert after.created_by_account_id == account_a


# ---------------------------------------------------------------------------
# Persistence-exception rollback
# ---------------------------------------------------------------------------


def test_persistence_exception_leaves_no_partial_row(
    listing_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A DB-level rejection of the insert (here: the content_hash length CHECK
    constraint, forced by a corrupted fingerprint) must roll back the
    attempted row rather than leaving a partial write, and must leave the
    connection usable afterwards."""
    import hullq.persistence.native_listing as native_listing_mod

    monkeypatch.setattr(native_listing_mod, "_fingerprint_envelope", lambda *a, **k: "too-short")

    account = _account("ACC-ROLLBACK")
    org = _org("ORG-ROLLBACK")
    membership = _membership("OM-ROLLBACK", account, org, frozenset({MembershipRole.PUBLISHER}))

    with pytest.raises(CheckViolation):
        create_native_listing(
            listing_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=_listing("NL-ROLLBACK-001"),
        )

    listing_conn.rollback()
    assert _row_count(listing_conn, "NL-ROLLBACK-001") == 0
    assert fetch_native_listing(listing_conn, NativeListingId("NL-ROLLBACK-001")) is None


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency: race-safe creation under concurrent connections
# ---------------------------------------------------------------------------


def test_concurrent_identical_creation_resolves_deterministically(listing_url: str) -> None:
    """Two concurrent identical creation attempts must resolve as
    CREATED + ALREADY_EXISTS. No PostgreSQL unique-violation must leak to the
    caller, and exactly one row must exist afterwards."""
    account = _account("ACC-RACE1")
    org = _org("ORG-RACE1")
    membership = _membership("OM-RACE1", account, org, frozenset({MembershipRole.PUBLISHER}))
    listing = _listing("NL-RACE-001")

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(listing_url)
            try:
                barrier.wait(timeout=10)
                result = create_native_listing(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    listing=listing,
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = {r.status for r in results}
    assert statuses == {
        NativeListingCreationStatus.CREATED,
        NativeListingCreationStatus.ALREADY_EXISTS,
    }

    verify = psycopg.connect(listing_url)
    try:
        assert _row_count(verify, "NL-RACE-001") == 1
    finally:
        verify.close()


def test_concurrent_conflicting_creation_fails_closed(listing_url: str) -> None:
    """Two concurrent creations under the same NativeListingId but a
    different immutable envelope must resolve as exactly one CREATED and
    exactly one CONFLICT, never two successful writes."""
    account = _account("ACC-RACE2")
    org = _org("ORG-RACE2")
    membership = _membership("OM-RACE2", account, org, frozenset({MembershipRole.PUBLISHER}))
    listing_v1 = _listing("NL-RACE-002")
    listing_v1_ref_a = "BROKER-REF-A"
    listing_v1_ref_b = "BROKER-REF-B"

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(broker_reference: str) -> None:
        try:
            conn = psycopg.connect(listing_url)
            try:
                barrier.wait(timeout=10)
                result = create_native_listing(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    listing=listing_v1,
                    broker_listing_reference=broker_reference,
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(listing_v1_ref_a,)),
        threading.Thread(target=_worker, args=(listing_v1_ref_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(NativeListingCreationStatus.CREATED) == 1, statuses
    assert statuses.count(NativeListingCreationStatus.CONFLICT) == 1, statuses

    verify = psycopg.connect(listing_url)
    try:
        assert _row_count(verify, "NL-RACE-002") == 1
    finally:
        verify.close()
