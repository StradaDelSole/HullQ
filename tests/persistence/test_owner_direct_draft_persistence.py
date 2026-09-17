"""PostgreSQL integration tests for hullq.persistence.owner_direct_draft — SLICE-0054.

Covers durable create/list/read/update against a real PostgreSQL 18 schema
(mirroring the SLICE-0053 `test_broker_identity_persistence.py` disposable-
schema pattern): ownership scoping, foreign/unknown non-enumeration, and
atomic optimistic-concurrency version conflict.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.owner_direct_draft import (
    EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
    OwnerDirectListingDraftId,
    parse_owner_direct_draft_payload,
)
from hullq.domain.publishing_eligibility import AccountId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.owner_direct_draft import (
    OwnerDirectListingDraftUpdateOutcome,
    create_owner_direct_draft,
    fetch_owner_direct_draft,
    list_owner_direct_drafts,
    update_owner_direct_draft,
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
    schema_name = f"hullq_s0054_{uuid.uuid4().hex[:16]}"
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


class TestCreateOwnerDirectDraft:
    def test_create_empty_draft(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)

        record = create_owner_direct_draft(
            conn, owner_account_id=account_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        assert record.version == 1
        assert record.owner_account_id == account_id
        assert record.payload == EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD

    def test_create_partial_draft_persists_exact_values(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)
        payload = parse_owner_direct_draft_payload(
            {
                "physical_boat.boat_name": "Sea Breeze",
                "listing_offer.asking_price_mode": "POA",
            }
        )

        record = create_owner_direct_draft(conn, owner_account_id=account_id, payload=payload)
        conn.commit()

        fetched = fetch_owner_direct_draft(
            conn, draft_id=record.draft_id, owner_account_id=account_id
        )
        assert fetched is not None
        assert fetched.payload == payload

    def test_each_create_gets_a_distinct_draft_id(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)
        first = create_owner_direct_draft(
            conn, owner_account_id=account_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()
        second = create_owner_direct_draft(
            conn, owner_account_id=account_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()
        assert first.draft_id != second.draft_id


class TestFetchAndListOwnerDirectDraft:
    def test_fetch_unknown_draft_returns_none(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)
        result = fetch_owner_direct_draft(
            conn,
            draft_id=OwnerDirectListingDraftId(str(uuid.uuid4())),
            owner_account_id=account_id,
        )
        assert result is None

    def test_fetch_foreign_draft_returns_none(self, conn: Any) -> None:
        owner_id = AccountId(str(uuid.uuid4()))
        other_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, owner_id)
        _seed_account(conn, other_id)
        record = create_owner_direct_draft(
            conn, owner_account_id=owner_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        result = fetch_owner_direct_draft(conn, draft_id=record.draft_id, owner_account_id=other_id)
        assert result is None

    def test_unknown_and_foreign_draft_results_are_identical(self, conn: Any) -> None:
        owner_id = AccountId(str(uuid.uuid4()))
        other_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, owner_id)
        _seed_account(conn, other_id)
        record = create_owner_direct_draft(
            conn, owner_account_id=owner_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        foreign = fetch_owner_direct_draft(
            conn, draft_id=record.draft_id, owner_account_id=other_id
        )
        unknown = fetch_owner_direct_draft(
            conn,
            draft_id=OwnerDirectListingDraftId(str(uuid.uuid4())),
            owner_account_id=other_id,
        )
        assert foreign is None
        assert unknown is None

    def test_list_returns_only_own_drafts_newest_first(self, conn: Any) -> None:
        owner_id = AccountId(str(uuid.uuid4()))
        other_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, owner_id)
        _seed_account(conn, other_id)

        first = create_owner_direct_draft(
            conn, owner_account_id=owner_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()
        second = create_owner_direct_draft(
            conn, owner_account_id=owner_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()
        create_owner_direct_draft(
            conn, owner_account_id=other_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        # Advance `second`'s updated_at strictly past `first`'s so ordering
        # is deterministic even if both were created within the same
        # PostgreSQL clock tick.
        update_owner_direct_draft(
            conn,
            draft_id=second.draft_id,
            owner_account_id=owner_id,
            payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
            expected_version=1,
        )
        conn.commit()

        drafts = list_owner_direct_drafts(conn, owner_account_id=owner_id)
        assert [d.draft_id for d in drafts] == [second.draft_id, first.draft_id]


class TestUpdateOwnerDirectDraft:
    def test_update_with_current_version_advances_version(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)
        record = create_owner_direct_draft(
            conn, owner_account_id=account_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        new_payload = parse_owner_direct_draft_payload({"physical_boat.boat_name": "Renamed"})
        result = update_owner_direct_draft(
            conn,
            draft_id=record.draft_id,
            owner_account_id=account_id,
            payload=new_payload,
            expected_version=1,
        )
        conn.commit()

        assert result.outcome is OwnerDirectListingDraftUpdateOutcome.UPDATED
        assert result.record is not None
        assert result.record.version == 2
        assert result.record.payload == new_payload

    def test_stale_expected_version_returns_conflict_with_zero_mutation(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)
        record = create_owner_direct_draft(
            conn, owner_account_id=account_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        first_update_payload = parse_owner_direct_draft_payload(
            {"physical_boat.boat_name": "First update"}
        )
        update_owner_direct_draft(
            conn,
            draft_id=record.draft_id,
            owner_account_id=account_id,
            payload=first_update_payload,
            expected_version=1,
        )
        conn.commit()

        stale_payload = parse_owner_direct_draft_payload({"physical_boat.boat_name": "Stale"})
        result = update_owner_direct_draft(
            conn,
            draft_id=record.draft_id,
            owner_account_id=account_id,
            payload=stale_payload,
            expected_version=1,
        )
        conn.commit()

        assert result.outcome is OwnerDirectListingDraftUpdateOutcome.VERSION_CONFLICT
        assert result.record is None

        current = fetch_owner_direct_draft(
            conn, draft_id=record.draft_id, owner_account_id=account_id
        )
        assert current is not None
        assert current.version == 2
        assert current.payload == first_update_payload

    def test_update_unknown_draft_returns_not_found(self, conn: Any) -> None:
        account_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, account_id)
        result = update_owner_direct_draft(
            conn,
            draft_id=OwnerDirectListingDraftId(str(uuid.uuid4())),
            owner_account_id=account_id,
            payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
            expected_version=1,
        )
        assert result.outcome is OwnerDirectListingDraftUpdateOutcome.NOT_FOUND

    def test_update_foreign_draft_returns_not_found_with_zero_mutation(self, conn: Any) -> None:
        owner_id = AccountId(str(uuid.uuid4()))
        attacker_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, owner_id)
        _seed_account(conn, attacker_id)
        record = create_owner_direct_draft(
            conn, owner_account_id=owner_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        attack_payload = parse_owner_direct_draft_payload({"physical_boat.boat_name": "Hijacked"})
        result = update_owner_direct_draft(
            conn,
            draft_id=record.draft_id,
            owner_account_id=attacker_id,
            payload=attack_payload,
            expected_version=1,
        )
        conn.commit()

        assert result.outcome is OwnerDirectListingDraftUpdateOutcome.NOT_FOUND
        current = fetch_owner_direct_draft(
            conn, draft_id=record.draft_id, owner_account_id=owner_id
        )
        assert current is not None
        assert current.version == 1
        assert current.payload == EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD

    def test_not_found_and_conflict_are_mechanically_distinct(self, conn: Any) -> None:
        owner_id = AccountId(str(uuid.uuid4()))
        _seed_account(conn, owner_id)
        record = create_owner_direct_draft(
            conn, owner_account_id=owner_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()

        not_found = update_owner_direct_draft(
            conn,
            draft_id=OwnerDirectListingDraftId(str(uuid.uuid4())),
            owner_account_id=owner_id,
            payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
            expected_version=1,
        )
        conflict = update_owner_direct_draft(
            conn,
            draft_id=record.draft_id,
            owner_account_id=owner_id,
            payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
            expected_version=999,
        )
        assert not_found.outcome is OwnerDirectListingDraftUpdateOutcome.NOT_FOUND
        assert conflict.outcome is OwnerDirectListingDraftUpdateOutcome.VERSION_CONFLICT


class TestOwnerDirectDraftNonRegression:
    """Contract §2/§13.12: draft operations create zero rows in any
    marketplace identity/inventory table, zero rows in any NativeListing
    offer revision/fact table, and zero rows in the durable tables that
    determine public Search-affecting NativeListing state.

    2026-09-17 independent review (PR #201 comment #5701782264, finding 3):
    the original table set here (`physical_boats`, `market_episodes`,
    `native_listings`) proved the identity/inventory half of contract §2 but
    not the "NativeListing offer revision", "NativeListing lifecycle/
    freshness state" or "Search candidate/eligibility state" half. The four
    added tables are the actual current-schema tables that carry that
    remaining meaning (no table is invented):

    - ``native_listing_offer_revisions`` / ``native_listing_offer_heads``
      (`alembic/versions/4d8e1a72c9f0_native_listing_offer_facts.py`) --
      the NativeListing offer revision/fact persistence;
    - ``native_listing_publication_transitions``
      (`alembic/versions/8b6d3f0a2c17_native_listing_lifecycle.py``) --
      the immutable ledger of DRAFT->ACTIVE/ACTIVE->WITHDRAWN transitions
      that is the durable record of public Search-eligible ("ACTIVE")
      NativeListing state;
    - ``native_listing_freshness_confirmations``
      (`alembic/versions/7d4b1a9e3f26_native_listing_freshness.py`) --
      `hullq.application.inventory_search`'s SLICE-0052 STALE/DUE-FOR-
      CONFIRMATION exclusion, i.e. public Search-eligibility state derived
      from this table.

    There is no separate materialized/cached "Search index" table in the
    current schema: `hullq.persistence.inventory_search` reads
    `native_listings` (already covered) and the above tables live, so this
    set is the complete current-schema proof of contract §13.12.
    """

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
        account_id = AccountId(str(uuid.uuid4()))
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
        record = create_owner_direct_draft(
            conn, owner_account_id=account_id, payload=EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
        )
        conn.commit()
        update_owner_direct_draft(
            conn,
            draft_id=record.draft_id,
            owner_account_id=account_id,
            payload=parse_owner_direct_draft_payload({"physical_boat.boat_name": "Test"}),
            expected_version=1,
        )
        conn.commit()
        after = _counts()

        assert before == after
