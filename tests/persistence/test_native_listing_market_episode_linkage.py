"""PostgreSQL-backed NativeListing <-> MarketEpisode linkage tests — SLICE-0047.

Covers the controlled linkage boundary the slice adds on top of the SLICE-
0043 immutable NativeListing creation envelope: PostgreSQL referential
integrity between ``native_listings.market_episode_id`` and the new durable
``market_episodes`` authority, the additional MARKET_EPISODE_NOT_FOUND typed
outcome and its priority against authorization/collision, and migration
governance against pre-existing data.

Each functional test runs against its own disposable PostgreSQL *schema*,
mirroring tests/persistence/test_native_listing_persistence.py and
tests/persistence/test_market_episode_persistence.py. The migration-
governance tests at the bottom instead upgrade a schema to the exact prior
accepted head (``7a3f0e5c1b6d``), seed data with raw SQL as SLICE-0043 could
have left it, and only then attempt the SLICE-0047 upgrade.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.errors import ForeignKeyViolation

from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoatId,
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
from hullq.persistence.alembic_baseline import (
    alembic_config,
    alembic_upgrade_head,
    prepare_alembic_baseline,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import (
    NativeListingCreationStatus,
    create_native_listing,
    fetch_native_listing,
)

# ---------------------------------------------------------------------------
# Disposable-schema fixture: genuinely-empty schema -> SLICE-0047 Alembic head
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
def link_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0047_link_{uuid.uuid4().hex[:16]}"
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
def link_conn(link_url: str) -> Generator[Any]:
    conn = psycopg.connect(link_url)
    try:
        yield conn
    finally:
        conn.close()


def _row_count(conn: Any, native_listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listings WHERE native_listing_id = %s",
            [native_listing_id],
        )
        return int(cur.fetchone()[0])


def _insert_physical_boat(conn: Any, physical_boat_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO physical_boats (physical_boat_id) VALUES (%s)", [physical_boat_id])
    conn.commit()


def _account(value: str) -> AccountId:
    return AccountId(value)


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    membership_id: str,
    account: AccountId,
    organization: MarketplaceOrganization,
    *,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
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
# NULL / linked creation -- adversarial cases 12-14
# ---------------------------------------------------------------------------


def test_native_listing_with_null_episode_remains_creatable(link_conn: Any) -> None:
    account = _account("ACC-LINK-1")
    org = _org("ORG-LINK-1")
    membership = _membership("OM-LINK-1", account, org)

    result = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-001"),
    )
    assert result.status is NativeListingCreationStatus.CREATED
    record = fetch_native_listing(link_conn, NativeListingId("NL-LINK-001"))
    assert record is not None
    assert record.listing.market_episode_id is None


def test_authorized_native_listing_with_existing_episode_link_created(link_conn: Any) -> None:
    _insert_physical_boat(link_conn, "PB-LINK-002")
    episode_result = create_market_episode(
        link_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-LINK-002"), physical_boat_id=PhysicalBoatId("PB-LINK-002")
        ),
    )
    assert episode_result.status.value == "created"

    account = _account("ACC-LINK-2")
    org = _org("ORG-LINK-2")
    membership = _membership("OM-LINK-2", account, org)

    result = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-002", market_episode_id="ME-LINK-002"),
    )
    assert result.status is NativeListingCreationStatus.CREATED


def test_typed_native_listing_readback_preserves_exact_market_episode_id(link_conn: Any) -> None:
    _insert_physical_boat(link_conn, "PB-LINK-003")
    create_market_episode(
        link_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-LINK-003"),
            physical_boat_id=PhysicalBoatId("PB-LINK-003"),
        ),
    )
    account = _account("ACC-LINK-3")
    org = _org("ORG-LINK-3")
    membership = _membership("OM-LINK-3", account, org)
    listing = _listing("NL-LINK-003", market_episode_id="ME-LINK-003")

    create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
    )

    record = fetch_native_listing(link_conn, listing.id)
    assert record is not None
    assert record.listing.market_episode_id == MarketEpisodeId("ME-LINK-003")


# ---------------------------------------------------------------------------
# Fail-closed unknown MarketEpisode for a genuinely new listing -- case 15
# ---------------------------------------------------------------------------


def test_new_native_listing_with_unknown_episode_fails_closed(link_conn: Any) -> None:
    account = _account("ACC-LINK-4")
    org = _org("ORG-LINK-4")
    membership = _membership("OM-LINK-4", account, org)

    result = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-004", market_episode_id="ME-UNKNOWN"),
    )
    assert result.status is NativeListingCreationStatus.MARKET_EPISODE_NOT_FOUND
    assert _row_count(link_conn, "NL-LINK-004") == 0
    assert fetch_native_listing(link_conn, NativeListingId("NL-LINK-004")) is None


def test_market_episode_not_found_leaves_connection_usable(link_conn: Any) -> None:
    account = _account("ACC-LINK-4B")
    org = _org("ORG-LINK-4B")
    membership = _membership("OM-LINK-4B", account, org)

    result = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-004B", market_episode_id="ME-UNKNOWN-B"),
    )
    assert result.status is NativeListingCreationStatus.MARKET_EPISODE_NOT_FOUND

    from psycopg.pq import TransactionStatus

    assert link_conn.info.transaction_status == TransactionStatus.IDLE

    retry = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-004B"),
    )
    assert retry.status is NativeListingCreationStatus.CREATED


# ---------------------------------------------------------------------------
# Existing-envelope precedence over MARKET_EPISODE_NOT_FOUND -- cases 16-18
# ---------------------------------------------------------------------------


def test_existing_listing_exact_original_envelope_already_exists(link_conn: Any) -> None:
    account = _account("ACC-LINK-5")
    org = _org("ORG-LINK-5")
    membership = _membership("OM-LINK-5", account, org)
    listing = _listing("NL-LINK-005")

    create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
    )
    link_conn.commit()

    retry = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
    )
    assert retry.status is NativeListingCreationStatus.ALREADY_EXISTS


def test_existing_listing_different_episode_envelope_conflicts(link_conn: Any) -> None:
    _insert_physical_boat(link_conn, "PB-LINK-006")

    create_market_episode(
        link_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-LINK-006"), physical_boat_id=PhysicalBoatId("PB-LINK-006")
        ),
    )
    account = _account("ACC-LINK-6")
    org = _org("ORG-LINK-6")
    membership = _membership("OM-LINK-6", account, org)
    listing = _listing("NL-LINK-006")

    create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
    )
    link_conn.commit()

    conflict = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-006", market_episode_id="ME-LINK-006"),
    )
    assert conflict.status is NativeListingCreationStatus.CONFLICT
    assert _row_count(link_conn, "NL-LINK-006") == 1


def test_existing_listing_different_unknown_episode_conflicts_not_not_found(
    link_conn: Any,
) -> None:
    """An unknown different MarketEpisodeId supplied against an already-
    occupied NativeListingId must not relabel that existing-envelope
    conflict as MARKET_EPISODE_NOT_FOUND."""
    account = _account("ACC-LINK-7")
    org = _org("ORG-LINK-7")
    membership = _membership("OM-LINK-7", account, org)
    listing = _listing("NL-LINK-007")

    create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=listing,
    )
    link_conn.commit()

    conflict = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=_listing("NL-LINK-007", market_episode_id="ME-COMPLETELY-UNKNOWN"),
    )
    assert conflict.status is NativeListingCreationStatus.CONFLICT
    assert conflict.status is not NativeListingCreationStatus.MARKET_EPISODE_NOT_FOUND
    assert _row_count(link_conn, "NL-LINK-007") == 1


# ---------------------------------------------------------------------------
# DENIED remains authoritative regardless of episode input -- case 19
# ---------------------------------------------------------------------------


def test_denied_authorization_remains_denied_and_writes_zero_rows_regardless_of_episode(
    link_conn: Any,
) -> None:
    account = _account("ACC-LINK-8")
    org = _org("ORG-LINK-8")
    owner_membership = _membership(
        "OM-LINK-8", account, org, roles=frozenset({MembershipRole.OWNER})
    )

    result = create_native_listing(
        link_conn,
        account_id=account,
        candidate_organization=org,
        membership=owner_membership,
        listing=_listing("NL-LINK-008", market_episode_id="ME-DOES-NOT-MATTER"),
    )
    assert result.status is NativeListingCreationStatus.DENIED
    assert result.status is not NativeListingCreationStatus.MARKET_EPISODE_NOT_FOUND
    assert _row_count(link_conn, "NL-LINK-008") == 0


# ---------------------------------------------------------------------------
# Raw PostgreSQL FK enforcement -- adversarial case 20
# ---------------------------------------------------------------------------


def test_raw_sql_cannot_persist_a_native_listing_episode_reference_violating_the_fk(
    link_conn: Any,
) -> None:
    with pytest.raises(ForeignKeyViolation), link_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO native_listings "
            "(native_listing_id, publishing_organization_id, created_by_account_id, "
            " market_episode_id, content_hash) "
            "VALUES (%s, %s, %s, %s, %s)",
            ["NL-RAW-FK", "ORG-RAW", "ACC-RAW", "ME-RAW-UNKNOWN", "0" * 64],
        )
    link_conn.rollback()


# ---------------------------------------------------------------------------
# Migration governance against pre-existing data -- adversarial cases 21-23
# ---------------------------------------------------------------------------

_PRIOR_HEAD = "7a3f0e5c1b6d"


@pytest.fixture()
def prior_head_url(db_url: str) -> Generator[str]:
    """A disposable schema pinned at the exact prior accepted Alembic head
    (SLICE-0046), one revision *before* the SLICE-0047 market_episode_linkage
    migration under test."""
    from alembic import command

    schema_name = f"hullq_s0047_prior_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        command.upgrade(alembic_config(url), _PRIOR_HEAD)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


def test_migration_preserves_existing_null_native_listing_episode_links(
    prior_head_url: str,
) -> None:
    conn = psycopg.connect(prior_head_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO native_listings "
                "(native_listing_id, publishing_organization_id, created_by_account_id, "
                " market_episode_id, content_hash) "
                "VALUES (%s, %s, %s, NULL, %s)",
                ["NL-MIG-NULL", "ORG-MIG", "ACC-MIG", "0" * 64],
            )
        conn.commit()
    finally:
        conn.close()

    alembic_upgrade_head(prior_head_url)

    conn = psycopg.connect(prior_head_url)
    try:
        record = fetch_native_listing(conn, NativeListingId("NL-MIG-NULL"))
    finally:
        conn.close()
    assert record is not None
    assert record.listing.market_episode_id is None


def test_migration_with_orphan_non_null_episode_reference_fails_closed(
    prior_head_url: str,
) -> None:
    """A pre-0047 non-null native_listings.market_episode_id with no
    corresponding durable MarketEpisode must not be fabricated, nulled or
    rewritten -- the upgrade itself must fail."""
    conn = psycopg.connect(prior_head_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO native_listings "
                "(native_listing_id, publishing_organization_id, created_by_account_id, "
                " market_episode_id, content_hash) "
                "VALUES (%s, %s, %s, %s, %s)",
                ["NL-MIG-ORPHAN", "ORG-MIG", "ACC-MIG", "ME-ORPHAN-NEVER-CREATED", "0" * 64],
            )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(Exception):  # noqa: B017 - real ForeignKeyViolation surfaced through Alembic
        alembic_upgrade_head(prior_head_url)

    # The orphaned row must remain exactly as written -- neither fabricated
    # MarketEpisode, nulled reference, nor rewritten envelope.
    conn = psycopg.connect(prior_head_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT market_episode_id FROM native_listings WHERE native_listing_id = %s",
                ["NL-MIG-ORPHAN"],
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "ME-ORPHAN-NEVER-CREATED"


def test_alembic_reports_exactly_one_head_after_upgrade(link_url: str) -> None:
    from hullq.persistence.alembic_baseline import alembic_heads

    assert alembic_heads(link_url) == ["4c9a0dcc98bb"]
