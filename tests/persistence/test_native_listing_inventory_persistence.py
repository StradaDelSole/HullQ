"""PostgreSQL-backed Organization inventory keyset-read tests — SLICE-0060.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0060 Alembic head, mirroring the existing
SLICE-0043/0049 integration test isolation pattern.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.market_identity import NativeListing, NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
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
from hullq.persistence.native_listing_inventory import (
    InventorySortKey,
    fetch_organization_inventory_page,
)


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
def inventory_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0060_{uuid.uuid4().hex[:16]}"
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
def inventory_conn(inventory_url: str) -> Generator[Any]:
    conn = psycopg.connect(inventory_url)
    try:
        yield conn
    finally:
        conn.close()


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    membership_id: str, account: AccountId, org: MarketplaceOrganization
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _create_listing(
    conn: Any,
    *,
    listing_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    result = create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId(listing_id)),
    )
    assert result.status.value in ("created", "already_exists"), result


def _set_created_at(conn: Any, *, listing_id: str, created_at: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE native_listings SET created_at = %s WHERE native_listing_id = %s",
            (created_at, listing_id),
        )


def test_empty_organization_returns_no_rows(inventory_conn: Any) -> None:
    rows = fetch_organization_inventory_page(
        inventory_conn, MarketplaceOrganizationId("ORG-INV-EMPTY"), limit=50, after=None
    )
    assert rows == []


def test_organization_isolation_never_leaks_other_organization_rows(inventory_conn: Any) -> None:
    account = AccountId("ACC-INV-ISO")
    org_a = _org("ORG-INV-ISO-A")
    org_b = _org("ORG-INV-ISO-B")
    membership_a = _membership("OM-INV-ISO-A", account, org_a)
    membership_b = _membership("OM-INV-ISO-B", account, org_b)
    _create_listing(
        inventory_conn,
        listing_id="NL-INV-ISO-A1",
        account=account,
        org=org_a,
        membership=membership_a,
    )
    _create_listing(
        inventory_conn,
        listing_id="NL-INV-ISO-B1",
        account=account,
        org=org_b,
        membership=membership_b,
    )
    inventory_conn.commit()

    rows = fetch_organization_inventory_page(inventory_conn, org_a.id, limit=50, after=None)
    assert [row.native_listing_id.value for row in rows] == ["NL-INV-ISO-A1"]


def test_deterministic_order_created_at_desc_then_id_asc(inventory_conn: Any) -> None:
    account = AccountId("ACC-INV-ORDER")
    org = _org("ORG-INV-ORDER")
    membership = _membership("OM-INV-ORDER", account, org)
    base = datetime(2026, 1, 1, tzinfo=UTC)

    # Two listings share the same created_at; two others have distinct times.
    _create_listing(
        inventory_conn,
        listing_id="NL-INV-ORDER-OLD",
        account=account,
        org=org,
        membership=membership,
    )
    _create_listing(
        inventory_conn,
        listing_id="NL-INV-ORDER-TIE-B",
        account=account,
        org=org,
        membership=membership,
    )
    _create_listing(
        inventory_conn,
        listing_id="NL-INV-ORDER-TIE-A",
        account=account,
        org=org,
        membership=membership,
    )
    _create_listing(
        inventory_conn,
        listing_id="NL-INV-ORDER-NEW",
        account=account,
        org=org,
        membership=membership,
    )
    inventory_conn.commit()

    _set_created_at(inventory_conn, listing_id="NL-INV-ORDER-OLD", created_at=base)
    _set_created_at(
        inventory_conn, listing_id="NL-INV-ORDER-TIE-B", created_at=base + timedelta(days=1)
    )
    _set_created_at(
        inventory_conn, listing_id="NL-INV-ORDER-TIE-A", created_at=base + timedelta(days=1)
    )
    _set_created_at(
        inventory_conn, listing_id="NL-INV-ORDER-NEW", created_at=base + timedelta(days=2)
    )
    inventory_conn.commit()

    rows = fetch_organization_inventory_page(inventory_conn, org.id, limit=50, after=None)
    assert [row.native_listing_id.value for row in rows] == [
        "NL-INV-ORDER-NEW",
        "NL-INV-ORDER-TIE-A",
        "NL-INV-ORDER-TIE-B",
        "NL-INV-ORDER-OLD",
    ]


def test_keyset_continuation_across_two_pages_has_no_overlap_or_gap(inventory_conn: Any) -> None:
    account = AccountId("ACC-INV-PAGE")
    org = _org("ORG-INV-PAGE")
    membership = _membership("OM-INV-PAGE", account, org)
    base = datetime(2026, 2, 1, tzinfo=UTC)
    ids = [f"NL-INV-PAGE-{i:02d}" for i in range(5)]
    for listing_id in ids:
        _create_listing(
            inventory_conn, listing_id=listing_id, account=account, org=org, membership=membership
        )
    inventory_conn.commit()
    for i, listing_id in enumerate(ids):
        _set_created_at(inventory_conn, listing_id=listing_id, created_at=base + timedelta(days=i))
    inventory_conn.commit()

    expected_order = list(reversed(ids))  # newest created_at first

    first_page = fetch_organization_inventory_page(inventory_conn, org.id, limit=2, after=None)
    assert [r.native_listing_id.value for r in first_page] == expected_order[:2]

    last_of_first = first_page[-1]
    second_page = fetch_organization_inventory_page(
        inventory_conn,
        org.id,
        limit=2,
        after=InventorySortKey(
            created_at=last_of_first.created_at, native_listing_id=last_of_first.native_listing_id
        ),
    )
    assert [r.native_listing_id.value for r in second_page] == expected_order[2:4]

    last_of_second = second_page[-1]
    third_page = fetch_organization_inventory_page(
        inventory_conn,
        org.id,
        limit=2,
        after=InventorySortKey(
            created_at=last_of_second.created_at, native_listing_id=last_of_second.native_listing_id
        ),
    )
    assert [r.native_listing_id.value for r in third_page] == expected_order[4:5]

    all_seen = (
        [r.native_listing_id.value for r in first_page]
        + [r.native_listing_id.value for r in second_page]
        + [r.native_listing_id.value for r in third_page]
    )
    assert all_seen == expected_order
    assert len(set(all_seen)) == len(all_seen)


def test_lifecycle_and_broker_reference_are_read_back_exactly(inventory_conn: Any) -> None:
    account = AccountId("ACC-INV-FACT")
    org = _org("ORG-INV-FACT")
    membership = _membership("OM-INV-FACT", account, org)
    result = create_native_listing(
        inventory_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId("NL-INV-FACT")),
        broker_listing_reference="REF-123",
    )
    assert result.status.value == "created"
    inventory_conn.commit()

    rows = fetch_organization_inventory_page(inventory_conn, org.id, limit=50, after=None)
    assert len(rows) == 1
    assert rows[0].lifecycle_state is NativeListingLifecycleState.DRAFT
    assert rows[0].broker_listing_reference == "REF-123"
