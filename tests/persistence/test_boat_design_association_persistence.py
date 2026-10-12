"""PostgreSQL-backed tests for SLICE-0082
`hullq.persistence.boat_design_association` -- the bounded candidate
projection and the atomic first-time PhysicalBoat -> BoatDesign association
write.

Mirrors `tests/persistence/test_physical_boat_persistence.py`'s disposable-
schema fixture/isolation pattern.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.pq import TransactionStatus

from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.boat_design_association import (
    BoatDesignAssociationTransactionOwnershipError,
    DesignAssociationStatus,
    associate_physical_boat_design,
    fetch_boat_design_candidate,
    search_boat_design_candidates,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.physical_boat import create_physical_boat

# ---------------------------------------------------------------------------
# Disposable-schema fixture
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
def design_assoc_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0082_{uuid.uuid4().hex[:16]}"
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
def conn(design_assoc_url: str) -> Generator[Any]:
    connection = psycopg.connect(design_assoc_url)
    try:
        yield connection
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _insert_account(conn: Any, account_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )
    conn.commit()


def _insert_canonical_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    brand_id: str | None = None,
    model_name: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, first_built, last_built, content_hash) "
            "VALUES (%s, %s, %s, %s, %s)",
            [model_id, model_name or f"Model {model_id}", 2000, 2010, "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", "{}", "[]", "[]", "{}", "1" * 64],
        )
        if brand_id is not None:
            cur.execute(
                "INSERT INTO canonical_brands (id, canonical_name, content_hash) "
                "VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                [brand_id, brand_id, "2" * 64],
            )
            cur.execute(
                "INSERT INTO canonical_brand_model_relationships "
                "(id, brand_id, boat_model_id, content_hash) VALUES (%s, %s, %s, %s)",
                [f"rel-{design_id}", brand_id, model_id, "3" * 64],
            )
    conn.commit()


def _insert_native_listing(
    conn: Any,
    listing_id: str,
    organization_id: str,
    account_id: str,
    market_episode_id: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO native_listings "
            "(native_listing_id, publishing_organization_id, created_by_account_id, "
            " market_episode_id, content_hash) VALUES (%s, %s, %s, %s, %s)",
            [listing_id, organization_id, account_id, market_episode_id, "4" * 64],
        )
    conn.commit()


def _setup_chain(
    conn: Any,
    *,
    physical_boat_id: str,
    market_episode_id: str,
    listing_id: str,
    organization_id: str,
    account_id: str,
) -> None:
    """One PhysicalBoat -> MarketEpisode -> NativeListing chain, unresolved
    design, owned by *organization_id*."""
    _insert_account(conn, account_id)
    result = create_physical_boat(
        conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id))
    )
    assert result.status.value == "created"
    episode_result = create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    assert episode_result.status.value == "created"
    _insert_native_listing(conn, listing_id, organization_id, account_id, market_episode_id)


def _audit_row_count(conn: Any, physical_boat_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM boat_design_association_events WHERE physical_boat_id = %s",
            [physical_boat_id],
        )
        return int(cur.fetchone()[0])


def _stored_design_ref(conn: Any, physical_boat_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT boat_design_ref FROM physical_boats WHERE physical_boat_id = %s",
            [physical_boat_id],
        )
        row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Candidate projection
# ---------------------------------------------------------------------------


def test_search_empty_query_returns_bounded_deterministic_candidates(conn: Any) -> None:
    for i in range(3):
        _insert_canonical_boat_design(
            conn, f"BD-S{i}", f"BM-S{i}", brand_id=f"BR-S{i}", model_name=f"Zephyr {i}"
        )
    candidates = search_boat_design_candidates(conn, "")
    assert len(candidates) == 3
    # Deterministic: repeated call returns the identical order.
    repeat = search_boat_design_candidates(conn, "")
    assert [c.boat_design_ref.value for c in repeat] == [
        c.boat_design_ref.value for c in candidates
    ]


def test_search_matches_brand_or_model_name_case_insensitively(conn: Any) -> None:
    _insert_canonical_boat_design(
        conn, "BD-M1", "BM-M1", brand_id="Beneteau", model_name="Oceanis 46.1"
    )
    _insert_canonical_boat_design(conn, "BD-M2", "BM-M2", brand_id="Lagoon", model_name="42")

    by_model = search_boat_design_candidates(conn, "oceanis")
    assert [c.boat_design_ref.value for c in by_model] == ["BD-M1"]

    by_brand = search_boat_design_candidates(conn, "lagoon")
    assert [c.boat_design_ref.value for c in by_brand] == ["BD-M2"]


def test_search_with_no_match_returns_empty_list(conn: Any) -> None:
    _insert_canonical_boat_design(
        conn, "BD-NM", "BM-NM", brand_id="Beneteau", model_name="Oceanis 46.1"
    )
    assert search_boat_design_candidates(conn, "nonexistent-design-xyz") == []


def test_search_escapes_like_wildcards_literally(conn: Any) -> None:
    _insert_canonical_boat_design(
        conn, "BD-ESC", "BM-ESC", brand_id="Beneteau", model_name="Model_46%"
    )
    # A literal "%" in the query must not act as a wildcard match-everything.
    assert [c.boat_design_ref.value for c in search_boat_design_candidates(conn, "46%")] == [
        "BD-ESC"
    ]
    assert search_boat_design_candidates(conn, "99%") == []


def test_search_limit_is_clamped_to_twenty(conn: Any) -> None:
    for i in range(25):
        _insert_canonical_boat_design(
            conn, f"BD-L{i:02d}", f"BM-L{i:02d}", model_name=f"Hull {i:02d}"
        )
    assert len(search_boat_design_candidates(conn, "", limit=1000)) == 20


def test_fetch_single_candidate_by_ref(conn: Any) -> None:
    _insert_canonical_boat_design(conn, "BD-ONE", "BM-ONE", brand_id="Lagoon", model_name="42")
    candidate = fetch_boat_design_candidate(conn, BoatDesignRef("BD-ONE"))
    assert candidate is not None
    assert candidate.canonical_model_name == "42"
    assert candidate.brand_names == ("Lagoon",)


def test_fetch_unknown_candidate_returns_none(conn: Any) -> None:
    assert fetch_boat_design_candidate(conn, BoatDesignRef("BD-DOES-NOT-EXIST")) is None


# ---------------------------------------------------------------------------
# Atomic first association
# ---------------------------------------------------------------------------


def test_first_association_links_and_records_exactly_one_audit_event(conn: Any) -> None:
    _insert_canonical_boat_design(conn, "BD-ASSOC1", "BM-ASSOC1")
    _setup_chain(
        conn,
        physical_boat_id="PB-A1",
        market_episode_id="ME-A1",
        listing_id="NL-A1",
        organization_id="ORG-A",
        account_id="ACC-A",
    )

    result = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-A1"),
        boat_design_ref=BoatDesignRef("BD-ASSOC1"),
        native_listing_id=NativeListingId("NL-A1"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-A"),
        recorded_by_account_id=AccountId("ACC-A"),
    )
    assert result.status is DesignAssociationStatus.LINKED
    assert result.stored_boat_design_ref == BoatDesignRef("BD-ASSOC1")
    assert _stored_design_ref(conn, "PB-A1") == "BD-ASSOC1"
    assert _audit_row_count(conn, "PB-A1") == 1


def test_exact_retry_is_idempotent_with_no_second_audit_event(conn: Any) -> None:
    _insert_canonical_boat_design(conn, "BD-IDEM", "BM-IDEM")
    _setup_chain(
        conn,
        physical_boat_id="PB-IDEM",
        market_episode_id="ME-IDEM",
        listing_id="NL-IDEM",
        organization_id="ORG-IDEM",
        account_id="ACC-IDEM",
    )
    kwargs = {
        "physical_boat_id": PhysicalBoatId("PB-IDEM"),
        "boat_design_ref": BoatDesignRef("BD-IDEM"),
        "native_listing_id": NativeListingId("NL-IDEM"),
        "confirming_organization_id": MarketplaceOrganizationId("ORG-IDEM"),
        "recorded_by_account_id": AccountId("ACC-IDEM"),
    }
    first = associate_physical_boat_design(conn, **kwargs)
    assert first.status is DesignAssociationStatus.LINKED

    second = associate_physical_boat_design(conn, **kwargs)
    assert second.status is DesignAssociationStatus.ALREADY_LINKED
    assert second.stored_boat_design_ref == BoatDesignRef("BD-IDEM")
    assert _audit_row_count(conn, "PB-IDEM") == 1


def test_different_target_conflicts_and_does_not_overwrite(conn: Any) -> None:
    _insert_canonical_boat_design(conn, "BD-CX", "BM-CX")
    _insert_canonical_boat_design(conn, "BD-CY", "BM-CY")
    _setup_chain(
        conn,
        physical_boat_id="PB-CONF",
        market_episode_id="ME-CONF",
        listing_id="NL-CONF",
        organization_id="ORG-CONF",
        account_id="ACC-CONF",
    )
    first = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-CONF"),
        boat_design_ref=BoatDesignRef("BD-CX"),
        native_listing_id=NativeListingId("NL-CONF"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-CONF"),
        recorded_by_account_id=AccountId("ACC-CONF"),
    )
    assert first.status is DesignAssociationStatus.LINKED

    second = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-CONF"),
        boat_design_ref=BoatDesignRef("BD-CY"),
        native_listing_id=NativeListingId("NL-CONF"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-CONF"),
        recorded_by_account_id=AccountId("ACC-CONF"),
    )
    assert second.status is DesignAssociationStatus.CONFLICT
    assert second.stored_boat_design_ref == BoatDesignRef("BD-CX")
    assert _stored_design_ref(conn, "PB-CONF") == "BD-CX"
    assert _audit_row_count(conn, "PB-CONF") == 1


def test_unknown_design_ref_fails_closed_and_writes_no_row(conn: Any) -> None:
    _setup_chain(
        conn,
        physical_boat_id="PB-UNK",
        market_episode_id="ME-UNK",
        listing_id="NL-UNK",
        organization_id="ORG-UNK",
        account_id="ACC-UNK",
    )
    result = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-UNK"),
        boat_design_ref=BoatDesignRef("BD-DOES-NOT-EXIST"),
        native_listing_id=NativeListingId("NL-UNK"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-UNK"),
        recorded_by_account_id=AccountId("ACC-UNK"),
    )
    assert result.status is DesignAssociationStatus.DESIGN_NOT_FOUND
    # Checked immediately, before any other cursor use: a plain SELECT under
    # psycopg's default autocommit=False opens its own implicit transaction,
    # which would otherwise mask whether the FK-violation rollback itself
    # left *conn* genuinely IDLE.
    assert conn.info.transaction_status == TransactionStatus.IDLE
    assert _stored_design_ref(conn, "PB-UNK") is None
    assert _audit_row_count(conn, "PB-UNK") == 0


def test_physical_boat_not_found(conn: Any) -> None:
    _insert_canonical_boat_design(conn, "BD-NOBOAT", "BM-NOBOAT")
    _insert_account(conn, "ACC-NOBOAT")
    result = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-DOES-NOT-EXIST"),
        boat_design_ref=BoatDesignRef("BD-NOBOAT"),
        native_listing_id=NativeListingId("NL-DOES-NOT-EXIST"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-NOBOAT"),
        recorded_by_account_id=AccountId("ACC-NOBOAT"),
    )
    assert result.status is DesignAssociationStatus.PHYSICAL_BOAT_NOT_FOUND


def test_shared_boat_with_foreign_organization_denies_without_mutation(conn: Any) -> None:
    """A second Organization's own NativeListing already resolves to the
    identical MarketEpisode/PhysicalBoat (SLICE-0040 contract §4 permits
    this) -- the first Organization's unilateral confirmation must be
    denied, not silently decide shared identity truth."""
    _insert_canonical_boat_design(conn, "BD-SHARED", "BM-SHARED")
    _setup_chain(
        conn,
        physical_boat_id="PB-SHARED",
        market_episode_id="ME-SHARED",
        listing_id="NL-SHARED-OWN",
        organization_id="ORG-OWN",
        account_id="ACC-OWN",
    )
    # A foreign Organization's own NativeListing resolved to the same
    # MarketEpisode.
    _insert_native_listing(conn, "NL-SHARED-FOREIGN", "ORG-FOREIGN", "ACC-OWN", "ME-SHARED")

    result = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-SHARED"),
        boat_design_ref=BoatDesignRef("BD-SHARED"),
        native_listing_id=NativeListingId("NL-SHARED-OWN"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-OWN"),
        recorded_by_account_id=AccountId("ACC-OWN"),
    )
    assert result.status is DesignAssociationStatus.SHARED_BOAT_CONFLICT
    assert _stored_design_ref(conn, "PB-SHARED") is None
    assert _audit_row_count(conn, "PB-SHARED") == 0


def test_same_organization_multiple_listings_is_not_a_shared_boat_conflict(conn: Any) -> None:
    """Two NativeListings of the *same* Organization, resolved to two
    *different* MarketEpisodes of the identical PhysicalBoat (SLICE-0040
    contract §3.1: "One PhysicalBoat MAY participate in multiple
    MarketEpisodes over time") must never trigger the cross-Organization
    shared-boat denial. A single Organization holding two NativeListings for
    the identical *same* MarketEpisode is itself impossible
    (`ux_native_listings_org_episode`, D09), so that degenerate variant is
    not a reachable case to construct here."""
    _insert_canonical_boat_design(conn, "BD-SAMEORG", "BM-SAMEORG")
    _setup_chain(
        conn,
        physical_boat_id="PB-SAMEORG",
        market_episode_id="ME-SAMEORG-1",
        listing_id="NL-SAMEORG-1",
        organization_id="ORG-SAME",
        account_id="ACC-SAME",
    )
    second_episode = create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-SAMEORG-2"), physical_boat_id=PhysicalBoatId("PB-SAMEORG")
        ),
    )
    assert second_episode.status.value == "created"
    _insert_native_listing(conn, "NL-SAMEORG-2", "ORG-SAME", "ACC-SAME", "ME-SAMEORG-2")

    result = associate_physical_boat_design(
        conn,
        physical_boat_id=PhysicalBoatId("PB-SAMEORG"),
        boat_design_ref=BoatDesignRef("BD-SAMEORG"),
        native_listing_id=NativeListingId("NL-SAMEORG-1"),
        confirming_organization_id=MarketplaceOrganizationId("ORG-SAME"),
        recorded_by_account_id=AccountId("ACC-SAME"),
    )
    assert result.status is DesignAssociationStatus.LINKED


def test_transaction_ownership_error_on_already_open_transaction(
    conn: Any, design_assoc_url: str
) -> None:
    _insert_canonical_boat_design(conn, "BD-TXN", "BM-TXN")
    _setup_chain(
        conn,
        physical_boat_id="PB-TXN",
        market_episode_id="ME-TXN",
        listing_id="NL-TXN",
        organization_id="ORG-TXN",
        account_id="ACC-TXN",
    )
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
    assert conn.info.transaction_status != TransactionStatus.IDLE

    with pytest.raises(BoatDesignAssociationTransactionOwnershipError):
        associate_physical_boat_design(
            conn,
            physical_boat_id=PhysicalBoatId("PB-TXN"),
            boat_design_ref=BoatDesignRef("BD-TXN"),
            native_listing_id=NativeListingId("NL-TXN"),
            confirming_organization_id=MarketplaceOrganizationId("ORG-TXN"),
            recorded_by_account_id=AccountId("ACC-TXN"),
        )
    conn.rollback()
    assert _stored_design_ref(conn, "PB-TXN") is None


def test_concurrent_identical_and_different_target_attempts_resolve_deterministically(
    design_assoc_url: str,
) -> None:
    setup_conn = psycopg.connect(design_assoc_url)
    try:
        _insert_canonical_boat_design(setup_conn, "BD-RACE-X", "BM-RACE-X")
        _insert_canonical_boat_design(setup_conn, "BD-RACE-Y", "BM-RACE-Y")
        _setup_chain(
            setup_conn,
            physical_boat_id="PB-RACE",
            market_episode_id="ME-RACE",
            listing_id="NL-RACE",
            organization_id="ORG-RACE",
            account_id="ACC-RACE",
        )
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(design_ref_value: str) -> None:
        try:
            worker_conn = psycopg.connect(design_assoc_url)
            try:
                barrier.wait(timeout=10)
                result = associate_physical_boat_design(
                    worker_conn,
                    physical_boat_id=PhysicalBoatId("PB-RACE"),
                    boat_design_ref=BoatDesignRef(design_ref_value),
                    native_listing_id=NativeListingId("NL-RACE"),
                    confirming_organization_id=MarketplaceOrganizationId("ORG-RACE"),
                    recorded_by_account_id=AccountId("ACC-RACE"),
                )
                results.append(result)
            finally:
                worker_conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("BD-RACE-X",)),
        threading.Thread(target=_worker, args=("BD-RACE-Y",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(DesignAssociationStatus.LINKED) == 1, statuses
    assert statuses.count(DesignAssociationStatus.CONFLICT) == 1, statuses

    verify_conn = psycopg.connect(design_assoc_url)
    try:
        assert _audit_row_count(verify_conn, "PB-RACE") == 1
    finally:
        verify_conn.close()
