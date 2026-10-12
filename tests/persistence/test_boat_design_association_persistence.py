"""PostgreSQL-backed tests for SLICE-0082
`hullq.persistence.boat_design_association` -- the bounded candidate
projection and the atomic first-time PhysicalBoat -> BoatDesign association
write.

Mirrors `tests/persistence/test_physical_boat_persistence.py`'s disposable-
schema fixture/isolation pattern.

Amended per independent review Finding A (2026-10-12): every successful
association now requires a real seeded Organization + ACTIVE PUBLISHER
membership, because `associate_physical_boat_design_for_listing` re-
evaluates membership/eligibility/listing-ownership fresh *inside* its own
committing transaction rather than trusting values resolved earlier. The
new `test_concurrent_membership_revocation_cannot_produce_unauthorized_
association` test proves that invariant under real lock contention, not
only by code inspection.
"""

from __future__ import annotations

import threading
import time
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
from hullq.persistence.boat_design_association import (
    BoatDesignAssociationTransactionOwnershipError,
    DesignAssociationStatus,
    associate_physical_boat_design_for_listing,
    fetch_boat_design_candidate,
    search_boat_design_candidates,
)
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
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


def _seed_org_and_membership(
    conn: Any,
    *,
    organization_id: str,
    account_id: str,
    membership_id: str | None = None,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
    publishing_eligibility: OrganizationPublishingEligibility = (
        OrganizationPublishingEligibility.ELIGIBLE
    ),
) -> None:
    """Seed a real Organization + membership through the accepted
    persistence writers (never raw SQL) -- every successful
    `associate_physical_boat_design_for_listing` call now requires this,
    since it re-evaluates real SLICE-0041 eligibility fresh inside its own
    transaction."""
    _insert_account(conn, account_id)
    seed_marketplace_organization(
        conn,
        MarketplaceOrganization(
            id=MarketplaceOrganizationId(organization_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=publishing_eligibility,
        ),
    )
    seed_organization_membership(
        conn,
        OrganizationMembership(
            id=OrganizationMembershipId(membership_id or f"OM-{organization_id}"),
            account_id=AccountId(account_id),
            organization_id=MarketplaceOrganizationId(organization_id),
            roles=roles,
            state=state,
        ),
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
    seed_membership: bool = True,
) -> None:
    """One PhysicalBoat -> MarketEpisode -> NativeListing chain, unresolved
    design, owned by *organization_id*, with a real ACTIVE PUBLISHER
    membership seeded by default."""
    _insert_account(conn, account_id)
    if seed_membership:
        _seed_org_and_membership(conn, organization_id=organization_id, account_id=account_id)
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


def _backend_pid(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        pid = int(cur.fetchone()[0])
    conn.commit()  # end the implicit read transaction; leaves conn IDLE
    return pid


def _wait_until_blocked_on_lock(monitor_conn: Any, pid: int, *, timeout: float = 10.0) -> bool:
    """Poll `pg_locks` on a dedicated connection until *pid* is genuinely
    waiting (not granted) on a lock -- never a fixed sleep guessing at
    scheduling, so this proof cannot be flaky about *whether* contention
    actually happened."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with monitor_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid = %s AND NOT granted)", [pid]
            )
            (is_waiting,) = cur.fetchone()
        monitor_conn.commit()
        if is_waiting:
            return True
        time.sleep(0.05)
    return False


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

    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-A"),
        organization_id=MarketplaceOrganizationId("ORG-A"),
        native_listing_id=NativeListingId("NL-A1"),
        boat_design_ref=BoatDesignRef("BD-ASSOC1"),
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
        "account_id": AccountId("ACC-IDEM"),
        "organization_id": MarketplaceOrganizationId("ORG-IDEM"),
        "native_listing_id": NativeListingId("NL-IDEM"),
        "boat_design_ref": BoatDesignRef("BD-IDEM"),
    }
    first = associate_physical_boat_design_for_listing(conn, **kwargs)
    assert first.status is DesignAssociationStatus.LINKED

    second = associate_physical_boat_design_for_listing(conn, **kwargs)
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
    first = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-CONF"),
        organization_id=MarketplaceOrganizationId("ORG-CONF"),
        native_listing_id=NativeListingId("NL-CONF"),
        boat_design_ref=BoatDesignRef("BD-CX"),
    )
    assert first.status is DesignAssociationStatus.LINKED

    second = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-CONF"),
        organization_id=MarketplaceOrganizationId("ORG-CONF"),
        native_listing_id=NativeListingId("NL-CONF"),
        boat_design_ref=BoatDesignRef("BD-CY"),
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
    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-UNK"),
        organization_id=MarketplaceOrganizationId("ORG-UNK"),
        native_listing_id=NativeListingId("NL-UNK"),
        boat_design_ref=BoatDesignRef("BD-DOES-NOT-EXIST"),
    )
    assert result.status is DesignAssociationStatus.DESIGN_NOT_FOUND
    # Checked immediately, before any other cursor use: a plain SELECT under
    # psycopg's default autocommit=False opens its own implicit transaction,
    # which would otherwise mask whether the FK-violation rollback itself
    # left *conn* genuinely IDLE.
    assert conn.info.transaction_status == TransactionStatus.IDLE
    assert _stored_design_ref(conn, "PB-UNK") is None
    assert _audit_row_count(conn, "PB-UNK") == 0


def test_unknown_listing_fails_closed_as_listing_not_found(conn: Any) -> None:
    _seed_org_and_membership(conn, organization_id="ORG-NOLISTING", account_id="ACC-NOLISTING")
    _insert_canonical_boat_design(conn, "BD-NOLISTING", "BM-NOLISTING")
    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-NOLISTING"),
        organization_id=MarketplaceOrganizationId("ORG-NOLISTING"),
        native_listing_id=NativeListingId("NL-DOES-NOT-EXIST"),
        boat_design_ref=BoatDesignRef("BD-NOLISTING"),
    )
    assert result.status is DesignAssociationStatus.LISTING_NOT_FOUND


def test_foreign_organization_listing_fails_closed_as_listing_not_found(conn: Any) -> None:
    _insert_canonical_boat_design(conn, "BD-FOREIGN", "BM-FOREIGN")
    _setup_chain(
        conn,
        physical_boat_id="PB-FOREIGN",
        market_episode_id="ME-FOREIGN",
        listing_id="NL-FOREIGN",
        organization_id="ORG-FOREIGN-OWNER",
        account_id="ACC-FOREIGN-OWNER",
    )
    _seed_org_and_membership(
        conn, organization_id="ORG-FOREIGN-ATTACKER", account_id="ACC-FOREIGN-ATTACKER"
    )
    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-FOREIGN-ATTACKER"),
        organization_id=MarketplaceOrganizationId("ORG-FOREIGN-ATTACKER"),
        native_listing_id=NativeListingId("NL-FOREIGN"),
        boat_design_ref=BoatDesignRef("BD-FOREIGN"),
    )
    assert result.status is DesignAssociationStatus.LISTING_NOT_FOUND
    assert _stored_design_ref(conn, "PB-FOREIGN") is None


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

    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-OWN"),
        organization_id=MarketplaceOrganizationId("ORG-OWN"),
        native_listing_id=NativeListingId("NL-SHARED-OWN"),
        boat_design_ref=BoatDesignRef("BD-SHARED"),
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

    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-SAME"),
        organization_id=MarketplaceOrganizationId("ORG-SAME"),
        native_listing_id=NativeListingId("NL-SAMEORG-1"),
        boat_design_ref=BoatDesignRef("BD-SAMEORG"),
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
        associate_physical_boat_design_for_listing(
            conn,
            account_id=AccountId("ACC-TXN"),
            organization_id=MarketplaceOrganizationId("ORG-TXN"),
            native_listing_id=NativeListingId("NL-TXN"),
            boat_design_ref=BoatDesignRef("BD-TXN"),
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
                result = associate_physical_boat_design_for_listing(
                    worker_conn,
                    account_id=AccountId("ACC-RACE"),
                    organization_id=MarketplaceOrganizationId("ORG-RACE"),
                    native_listing_id=NativeListingId("NL-RACE"),
                    boat_design_ref=BoatDesignRef(design_ref_value),
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


# ---------------------------------------------------------------------------
# Finding A: transaction-time authorization re-validation
# ---------------------------------------------------------------------------


def test_membership_revoked_before_call_is_denied_with_zero_mutation(conn: Any) -> None:
    """Stale identity context: if membership was already revoked by the
    time this call happens, the fresh in-transaction re-read must see it --
    never the ACTIVE state a caller might have resolved earlier."""
    _insert_canonical_boat_design(conn, "BD-STALE", "BM-STALE")
    _setup_chain(
        conn,
        physical_boat_id="PB-STALE",
        market_episode_id="ME-STALE",
        listing_id="NL-STALE",
        organization_id="ORG-STALE",
        account_id="ACC-STALE",
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE organization_memberships SET state = 'INACTIVE' "
            "WHERE account_id = %s AND organization_id = %s",
            ["ACC-STALE", "ORG-STALE"],
        )
    conn.commit()

    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-STALE"),
        organization_id=MarketplaceOrganizationId("ORG-STALE"),
        native_listing_id=NativeListingId("NL-STALE"),
        boat_design_ref=BoatDesignRef("BD-STALE"),
    )
    assert result.status is DesignAssociationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.MEMBERSHIP_INACTIVE
    assert _stored_design_ref(conn, "PB-STALE") is None
    assert _audit_row_count(conn, "PB-STALE") == 0


def test_organization_ineligible_at_write_time_is_denied(conn: Any) -> None:
    """Fresh re-evaluation covers Organization-side eligibility too, not
    only membership state."""
    _insert_canonical_boat_design(conn, "BD-INELIG", "BM-INELIG")
    _setup_chain(
        conn,
        physical_boat_id="PB-INELIG",
        market_episode_id="ME-INELIG",
        listing_id="NL-INELIG",
        organization_id="ORG-INELIG",
        account_id="ACC-INELIG",
    )
    # Re-seed the identical Organization as no longer eligible.
    seed_marketplace_organization(
        conn,
        MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-INELIG"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
        ),
    )
    conn.commit()

    result = associate_physical_boat_design_for_listing(
        conn,
        account_id=AccountId("ACC-INELIG"),
        organization_id=MarketplaceOrganizationId("ORG-INELIG"),
        native_listing_id=NativeListingId("NL-INELIG"),
        boat_design_ref=BoatDesignRef("BD-INELIG"),
    )
    assert result.status is DesignAssociationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_UNVERIFIED
    assert _stored_design_ref(conn, "PB-INELIG") is None


def test_concurrent_membership_revocation_cannot_produce_unauthorized_association(
    design_assoc_url: str,
) -> None:
    """The exact Finding A race: a membership revocation and an association
    attempt contend for the identical membership row under real PostgreSQL
    lock contention (confirmed via `pg_locks`, never a timing guess). The
    revocation is only allowed to commit once the association attempt is
    genuinely blocked behind this transaction's own lock -- proving the
    association re-reads membership state fresh *after* the revocation,
    never from a value resolved earlier, and is denied with zero mutation."""
    setup_conn = psycopg.connect(design_assoc_url)
    try:
        _insert_canonical_boat_design(setup_conn, "BD-RACE-REVOKE", "BM-RACE-REVOKE")
        _setup_chain(
            setup_conn,
            physical_boat_id="PB-RACE-REVOKE",
            market_episode_id="ME-RACE-REVOKE",
            listing_id="NL-RACE-REVOKE",
            organization_id="ORG-RACE-REVOKE",
            account_id="ACC-RACE-REVOKE",
        )
    finally:
        setup_conn.close()

    revoker_conn = psycopg.connect(design_assoc_url)
    monitor_conn = psycopg.connect(design_assoc_url)
    assoc_conn = psycopg.connect(design_assoc_url)
    assoc_pid = _backend_pid(assoc_conn)

    errors: list[BaseException] = []
    association_results: list[Any] = []
    membership_locked = threading.Event()

    def _hold_lock_then_revoke() -> None:
        try:
            with revoker_conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM organization_memberships "
                    "WHERE account_id = %s AND organization_id = %s FOR UPDATE",
                    ["ACC-RACE-REVOKE", "ORG-RACE-REVOKE"],
                )
            membership_locked.set()
            blocked = _wait_until_blocked_on_lock(monitor_conn, assoc_pid)
            assert blocked, "association attempt never blocked on the membership row lock"
            with revoker_conn.cursor() as cur:
                cur.execute(
                    "UPDATE organization_memberships SET state = 'INACTIVE' "
                    "WHERE account_id = %s AND organization_id = %s",
                    ["ACC-RACE-REVOKE", "ORG-RACE-REVOKE"],
                )
            revoker_conn.commit()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    def _attempt_association() -> None:
        try:
            membership_locked.wait(timeout=10)
            result = associate_physical_boat_design_for_listing(
                assoc_conn,
                account_id=AccountId("ACC-RACE-REVOKE"),
                organization_id=MarketplaceOrganizationId("ORG-RACE-REVOKE"),
                native_listing_id=NativeListingId("NL-RACE-REVOKE"),
                boat_design_ref=BoatDesignRef("BD-RACE-REVOKE"),
            )
            association_results.append(result)
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_hold_lock_then_revoke),
        threading.Thread(target=_attempt_association),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    revoker_conn.close()
    monitor_conn.close()
    assoc_conn.close()

    assert not errors, f"Thread errors: {errors}"
    assert len(association_results) == 1
    result = association_results[0]
    assert result.status is DesignAssociationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.MEMBERSHIP_INACTIVE

    verify_conn = psycopg.connect(design_assoc_url)
    try:
        assert _stored_design_ref(verify_conn, "PB-RACE-REVOKE") is None
        assert _audit_row_count(verify_conn, "PB-RACE-REVOKE") == 0
    finally:
        verify_conn.close()
