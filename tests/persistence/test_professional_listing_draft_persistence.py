"""PostgreSQL integration tests for hullq.persistence.professional_listing_draft — SLICE-0061.

Covers durable create/list/read/update against a real PostgreSQL 18 schema
(mirroring the SLICE-0054 `test_owner_direct_draft_persistence.py`
disposable-schema pattern): Organization ownership scoping, foreign/unknown
non-enumeration, atomic optimistic-concurrency version conflict, and
deterministic bounded keyset list ordering.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.listing_draft_payload import (
    EMPTY_LISTING_DRAFT_PAYLOAD,
    parse_listing_draft_payload,
)
from hullq.domain.professional_listing_draft import ProfessionalListingDraftId
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.professional_listing_draft import (
    ProfessionalListingDraftSortKey,
    ProfessionalListingDraftUpdateOutcome,
    create_professional_listing_draft,
    fetch_professional_listing_draft,
    list_professional_listing_drafts_page,
    update_professional_listing_draft,
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
def draft_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0061_{uuid.uuid4().hex[:16]}"
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
def conn(draft_url: str) -> Generator[Any]:
    connection = psycopg.connect(draft_url)
    try:
        yield connection
    finally:
        connection.close()


def _seed_account(conn: Any, account_id: AccountId) -> None:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO accounts (account_id) VALUES (%s)", [account_id.value])
    conn.commit()


def _seed_organization(conn: Any, organization_id: MarketplaceOrganizationId) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO marketplace_organizations "
            "(organization_id, professional_category, publishing_eligibility) "
            "VALUES (%s, %s, %s)",
            [organization_id.value, "BROKER", "ELIGIBLE"],
        )
    conn.commit()


class TestCreateProfessionalListingDraft:
    def test_create_empty_draft(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)

        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        assert record.version == 1
        assert record.owner_organization_id == org_id
        assert record.created_by_account_id == account_id
        assert record.broker_listing_reference is None
        assert record.payload == EMPTY_LISTING_DRAFT_PAYLOAD

    def test_create_partial_draft_with_broker_reference_persists_exact_values(
        self, conn: Any
    ) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        payload = parse_listing_draft_payload(
            {
                "physical_boat.boat_name": "Sea Breeze",
                "listing_offer.asking_price_mode": "POA",
            }
        )

        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference="REF-001",
            payload=payload,
        )
        conn.commit()

        fetched = fetch_professional_listing_draft(
            conn, draft_id=record.draft_id, owner_organization_id=org_id
        )
        assert fetched is not None
        assert fetched.payload == payload
        assert fetched.broker_listing_reference == "REF-001"

    def test_each_create_gets_a_distinct_draft_id(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        first = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()
        second = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()
        assert first.draft_id != second.draft_id


class TestFetchAndListProfessionalListingDraft:
    def test_fetch_unknown_draft_returns_none(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        result = fetch_professional_listing_draft(
            conn,
            draft_id=ProfessionalListingDraftId(str(uuid.uuid4())),
            owner_organization_id=org_id,
        )
        assert result is None

    def test_fetch_foreign_organization_draft_returns_none(self, conn: Any) -> None:
        owner_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        other_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, owner_org)
        _seed_organization(conn, other_org)
        _seed_account(conn, account_id)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=owner_org,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        result = fetch_professional_listing_draft(
            conn, draft_id=record.draft_id, owner_organization_id=other_org
        )
        assert result is None

    def test_unknown_and_foreign_draft_results_are_identical(self, conn: Any) -> None:
        owner_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        other_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, owner_org)
        _seed_organization(conn, other_org)
        _seed_account(conn, account_id)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=owner_org,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        foreign = fetch_professional_listing_draft(
            conn, draft_id=record.draft_id, owner_organization_id=other_org
        )
        unknown = fetch_professional_listing_draft(
            conn,
            draft_id=ProfessionalListingDraftId(str(uuid.uuid4())),
            owner_organization_id=other_org,
        )
        assert foreign is None
        assert unknown is None

    def test_list_returns_only_own_organization_drafts_newest_first(self, conn: Any) -> None:
        owner_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        other_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, owner_org)
        _seed_organization(conn, other_org)
        _seed_account(conn, account_id)

        first = create_professional_listing_draft(
            conn,
            owner_organization_id=owner_org,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()
        second = create_professional_listing_draft(
            conn,
            owner_organization_id=owner_org,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()
        create_professional_listing_draft(
            conn,
            owner_organization_id=other_org,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        # Advance `second`'s updated_at strictly past `first`'s so ordering
        # is deterministic even if both were created within the same
        # PostgreSQL clock tick.
        update_professional_listing_draft(
            conn,
            draft_id=second.draft_id,
            owner_organization_id=owner_org,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
            expected_version=1,
        )
        conn.commit()

        page = list_professional_listing_drafts_page(
            conn, owner_organization_id=owner_org, limit=50, after=None
        )
        assert [d.draft_id for d in page] == [second.draft_id, first.draft_id]

    def test_list_is_bounded_by_limit(self, conn: Any) -> None:
        owner_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, owner_org)
        _seed_account(conn, account_id)
        for _ in range(3):
            create_professional_listing_draft(
                conn,
                owner_organization_id=owner_org,
                created_by_account_id=account_id,
                broker_listing_reference=None,
                payload=EMPTY_LISTING_DRAFT_PAYLOAD,
            )
            conn.commit()

        page = list_professional_listing_drafts_page(
            conn, owner_organization_id=owner_org, limit=2, after=None
        )
        assert len(page) == 2

    def test_keyset_continuation_returns_remaining_rows_without_duplication(
        self, conn: Any
    ) -> None:
        owner_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, owner_org)
        _seed_account(conn, account_id)
        created = []
        for _ in range(3):
            record = create_professional_listing_draft(
                conn,
                owner_organization_id=owner_org,
                created_by_account_id=account_id,
                broker_listing_reference=None,
                payload=EMPTY_LISTING_DRAFT_PAYLOAD,
            )
            conn.commit()
            created.append(record)
            update_professional_listing_draft(
                conn,
                draft_id=record.draft_id,
                owner_organization_id=owner_org,
                broker_listing_reference=None,
                payload=EMPTY_LISTING_DRAFT_PAYLOAD,
                expected_version=1,
            )
            conn.commit()

        page1 = list_professional_listing_drafts_page(
            conn, owner_organization_id=owner_org, limit=2, after=None
        )
        assert len(page1) == 2
        after = ProfessionalListingDraftSortKey(
            updated_at=page1[-1].updated_at, draft_id=page1[-1].draft_id
        )
        page2 = list_professional_listing_drafts_page(
            conn, owner_organization_id=owner_org, limit=2, after=after
        )
        assert len(page2) == 1

        all_ids = [d.draft_id for d in page1] + [d.draft_id for d in page2]
        assert len(all_ids) == len(set(all_ids)) == 3


class TestUpdateProfessionalListingDraft:
    def test_update_with_current_version_advances_version(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        new_payload = parse_listing_draft_payload({"physical_boat.boat_name": "Renamed"})
        result = update_professional_listing_draft(
            conn,
            draft_id=record.draft_id,
            owner_organization_id=org_id,
            broker_listing_reference="REF-UPDATED",
            payload=new_payload,
            expected_version=1,
        )
        conn.commit()

        assert result.outcome is ProfessionalListingDraftUpdateOutcome.UPDATED
        assert result.record is not None
        assert result.record.version == 2
        assert result.record.payload == new_payload
        assert result.record.broker_listing_reference == "REF-UPDATED"
        assert result.record.created_by_account_id == account_id

    def test_stale_expected_version_returns_conflict_with_zero_mutation(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        first_update_payload = parse_listing_draft_payload(
            {"physical_boat.boat_name": "First update"}
        )
        update_professional_listing_draft(
            conn,
            draft_id=record.draft_id,
            owner_organization_id=org_id,
            broker_listing_reference=None,
            payload=first_update_payload,
            expected_version=1,
        )
        conn.commit()

        stale_payload = parse_listing_draft_payload({"physical_boat.boat_name": "Stale"})
        result = update_professional_listing_draft(
            conn,
            draft_id=record.draft_id,
            owner_organization_id=org_id,
            broker_listing_reference=None,
            payload=stale_payload,
            expected_version=1,
        )
        conn.commit()

        assert result.outcome is ProfessionalListingDraftUpdateOutcome.VERSION_CONFLICT
        assert result.record is None

        current = fetch_professional_listing_draft(
            conn, draft_id=record.draft_id, owner_organization_id=org_id
        )
        assert current is not None
        assert current.version == 2
        assert current.payload == first_update_payload

    def test_update_unknown_draft_returns_not_found(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        result = update_professional_listing_draft(
            conn,
            draft_id=ProfessionalListingDraftId(str(uuid.uuid4())),
            owner_organization_id=org_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
            expected_version=1,
        )
        assert result.outcome is ProfessionalListingDraftUpdateOutcome.NOT_FOUND

    def test_update_foreign_organization_draft_returns_not_found_with_zero_mutation(
        self, conn: Any
    ) -> None:
        owner_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        attacker_org = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, owner_org)
        _seed_organization(conn, attacker_org)
        _seed_account(conn, account_id)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=owner_org,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        attack_payload = parse_listing_draft_payload({"physical_boat.boat_name": "Hijacked"})
        result = update_professional_listing_draft(
            conn,
            draft_id=record.draft_id,
            owner_organization_id=attacker_org,
            broker_listing_reference="HIJACKED-REF",
            payload=attack_payload,
            expected_version=1,
        )
        conn.commit()

        assert result.outcome is ProfessionalListingDraftUpdateOutcome.NOT_FOUND
        current = fetch_professional_listing_draft(
            conn, draft_id=record.draft_id, owner_organization_id=owner_org
        )
        assert current is not None
        assert current.version == 1
        assert current.payload == EMPTY_LISTING_DRAFT_PAYLOAD
        assert current.broker_listing_reference is None

    def test_not_found_and_conflict_are_mechanically_distinct(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()

        not_found = update_professional_listing_draft(
            conn,
            draft_id=ProfessionalListingDraftId(str(uuid.uuid4())),
            owner_organization_id=org_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
            expected_version=1,
        )
        conflict = update_professional_listing_draft(
            conn,
            draft_id=record.draft_id,
            owner_organization_id=org_id,
            broker_listing_reference=None,
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
            expected_version=999,
        )
        assert not_found.outcome is ProfessionalListingDraftUpdateOutcome.NOT_FOUND
        assert conflict.outcome is ProfessionalListingDraftUpdateOutcome.VERSION_CONFLICT


class TestProfessionalListingDraftNonRegression:
    """Contract §11: draft operations create zero rows in any marketplace
    identity/inventory table, zero rows in any NativeListing offer revision/
    fact table, and zero rows in the durable tables that determine public
    Search-affecting NativeListing state (mirrors the identical SLICE-0054
    owner-direct proof and its current-schema table-set rationale)."""

    _NON_PROMOTION_TABLES = (
        "physical_boats",
        "market_episodes",
        "native_listings",
        "native_listing_offer_revisions",
        "native_listing_offer_heads",
        "native_listing_publication_transitions",
        "native_listing_freshness_confirmations",
    )

    def test_create_and_update_touch_no_marketplace_table(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)

        def _counts() -> dict[str, int]:
            counts = {}
            with conn.cursor() as cur:
                for table in self._NON_PROMOTION_TABLES:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    row = cur.fetchone()
                    assert row is not None
                    counts[table] = row[0]
            return counts

        before = _counts()
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference="REF-NP",
            payload=EMPTY_LISTING_DRAFT_PAYLOAD,
        )
        conn.commit()
        update_professional_listing_draft(
            conn,
            draft_id=record.draft_id,
            owner_organization_id=org_id,
            broker_listing_reference="REF-NP",
            payload=parse_listing_draft_payload({"physical_boat.boat_name": "Test"}),
            expected_version=1,
        )
        conn.commit()
        after = _counts()

        assert before == after
