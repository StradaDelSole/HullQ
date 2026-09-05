"""PostgreSQL-backed MarketEpisode identity persistence tests — SLICE-0047.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0047 Alembic head (SLICE-0042 baseline +
market_episode_linkage revision), mirroring the SLICE-0043/0045/0046
integration test isolation pattern in
tests/persistence/test_physical_boat_persistence.py.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.errors import ForeignKeyViolation
from psycopg.pq import TransactionStatus

from hullq.domain.market_identity import MarketEpisode, MarketEpisodeId, PhysicalBoatId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.market_episode import (
    MarketEpisodeCreationStatus,
    MarketEpisodeTransactionOwnershipError,
    create_market_episode,
    fetch_market_episode,
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
def episode_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0047_{uuid.uuid4().hex[:16]}"
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
def episode_conn(episode_url: str) -> Generator[Any]:
    conn = psycopg.connect(episode_url)
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


def _column_names(conn: Any, table_name: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s",
            [table_name],
        )
        return {row[0] for row in cur.fetchall()}


def _row_count(conn: Any, market_episode_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM market_episodes WHERE market_episode_id = %s",
            [market_episode_id],
        )
        return int(cur.fetchone()[0])


def _insert_physical_boat(conn: Any, physical_boat_id: str) -> None:
    """Minimal direct-SQL admission of one unresolved PhysicalBoat row --
    this test only needs an existing row in physical_boats for the FK
    authority MarketEpisode references, not to exercise PhysicalBoat
    creation semantics themselves."""
    with conn.cursor() as cur:
        cur.execute("INSERT INTO physical_boats (physical_boat_id) VALUES (%s)", [physical_boat_id])
    conn.commit()


# ---------------------------------------------------------------------------
# Migration boundary
# ---------------------------------------------------------------------------


def test_migration_adds_only_market_episodes_table(episode_conn: Any) -> None:
    tables = _table_names(episode_conn)
    assert "market_episodes" in tables
    assert {"research_bundles", "canonical_boat_designs", "physical_boats"} <= tables


def test_repeated_upgrade_head_is_idempotent(episode_url: str) -> None:
    alembic_upgrade_head(episode_url)  # second call must not raise or duplicate DDL
    conn = psycopg.connect(episode_url)
    try:
        assert "market_episodes" in _table_names(conn)
    finally:
        conn.close()


def test_market_episodes_columns_are_exactly_the_minimal_identity_envelope(
    episode_conn: Any,
) -> None:
    """Structural regression: no lifecycle/status/freshness/seller/price/
    observation/continuity/dedup column."""
    assert _column_names(episode_conn, "market_episodes") == {
        "market_episode_id",
        "physical_boat_id",
        "created_at",
    }


# ---------------------------------------------------------------------------
# Durable creation / exact readback -- adversarial cases 1-2
# ---------------------------------------------------------------------------


def test_create_for_existing_physical_boat_and_exact_readback(episode_conn: Any) -> None:
    _insert_physical_boat(episode_conn, "PB-ME-001")

    result = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-001"), physical_boat_id=PhysicalBoatId("PB-ME-001")
        ),
    )
    assert result.status is MarketEpisodeCreationStatus.CREATED

    record = fetch_market_episode(episode_conn, MarketEpisodeId("ME-001"))
    assert record is not None
    assert record.market_episode == MarketEpisode(
        id=MarketEpisodeId("ME-001"), physical_boat_id=PhysicalBoatId("PB-ME-001")
    )
    assert record.created_at is not None


def test_readback_of_missing_market_episode_returns_none(episode_conn: Any) -> None:
    assert fetch_market_episode(episode_conn, MarketEpisodeId("ME-DOES-NOT-EXIST")) is None


# ---------------------------------------------------------------------------
# Idempotency -- adversarial case 3
# ---------------------------------------------------------------------------


def test_identical_retry_is_idempotent_and_preserves_created_at(episode_conn: Any) -> None:
    _insert_physical_boat(episode_conn, "PB-ME-IDEM")
    episode = MarketEpisode(
        id=MarketEpisodeId("ME-IDEM"), physical_boat_id=PhysicalBoatId("PB-ME-IDEM")
    )

    first = create_market_episode(episode_conn, market_episode=episode)
    assert first.status is MarketEpisodeCreationStatus.CREATED
    first_record = fetch_market_episode(episode_conn, episode.id)
    assert first_record is not None
    episode_conn.commit()  # end the readback's implicit transaction

    second = create_market_episode(episode_conn, market_episode=episode)
    assert second.status is MarketEpisodeCreationStatus.ALREADY_EXISTS

    assert _row_count(episode_conn, "ME-IDEM") == 1
    second_record = fetch_market_episode(episode_conn, episode.id)
    assert second_record is not None
    assert second_record.created_at == first_record.created_at


# ---------------------------------------------------------------------------
# Conflict -- fail closed, never overwrite -- adversarial cases 4-5
# ---------------------------------------------------------------------------


def test_same_episode_id_different_existing_physical_boat_conflicts(episode_conn: Any) -> None:
    _insert_physical_boat(episode_conn, "PB-ME-CONF-X")
    _insert_physical_boat(episode_conn, "PB-ME-CONF-Y")
    episode_id = MarketEpisodeId("ME-CONF-001")

    create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=episode_id, physical_boat_id=PhysicalBoatId("PB-ME-CONF-X")
        ),
    )
    original = fetch_market_episode(episode_conn, episode_id)
    assert original is not None
    episode_conn.commit()

    conflict = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=episode_id, physical_boat_id=PhysicalBoatId("PB-ME-CONF-Y")
        ),
    )
    assert conflict.status is MarketEpisodeCreationStatus.CONFLICT

    after = fetch_market_episode(episode_conn, episode_id)
    assert after == original
    assert after.market_episode.physical_boat_id == PhysicalBoatId("PB-ME-CONF-X")
    assert _row_count(episode_conn, "ME-CONF-001") == 1


def test_same_episode_id_different_unknown_physical_boat_conflicts_not_not_found(
    episode_conn: Any,
) -> None:
    """Once a MarketEpisodeId is occupied, a retry with an unknown different
    PhysicalBoatId must classify as CONFLICT -- the identity-collision
    question -- never PHYSICAL_BOAT_NOT_FOUND, and must leave the existing
    row untouched."""
    _insert_physical_boat(episode_conn, "PB-ME-CONF2-X")
    episode_id = MarketEpisodeId("ME-CONF-002")

    create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=episode_id, physical_boat_id=PhysicalBoatId("PB-ME-CONF2-X")
        ),
    )
    original = fetch_market_episode(episode_conn, episode_id)
    assert original is not None
    episode_conn.commit()

    conflict = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=episode_id, physical_boat_id=PhysicalBoatId("PB-ME-CONF2-UNKNOWN")
        ),
    )
    assert conflict.status is MarketEpisodeCreationStatus.CONFLICT
    assert conflict.status is not MarketEpisodeCreationStatus.PHYSICAL_BOAT_NOT_FOUND

    after = fetch_market_episode(episode_conn, episode_id)
    assert after == original
    assert after.market_episode.physical_boat_id == PhysicalBoatId("PB-ME-CONF2-X")
    assert _row_count(episode_conn, "ME-CONF-002") == 1


# ---------------------------------------------------------------------------
# Fail-closed unknown PhysicalBoat for a genuinely new episode -- case 6
# ---------------------------------------------------------------------------


def test_new_episode_id_with_unknown_physical_boat_fails_closed_and_writes_no_row(
    episode_conn: Any,
) -> None:
    result = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-003"), physical_boat_id=PhysicalBoatId("PB-ME-UNKNOWN")
        ),
    )
    assert result.status is MarketEpisodeCreationStatus.PHYSICAL_BOAT_NOT_FOUND
    assert _row_count(episode_conn, "ME-003") == 0
    assert fetch_market_episode(episode_conn, MarketEpisodeId("ME-003")) is None


def test_physical_boat_not_found_leaves_connection_usable_for_a_subsequent_call(
    episode_conn: Any,
) -> None:
    """The internal ForeignKeyViolation catch must leave *conn* IDLE again so
    a caller can immediately reuse it, rather than leaking a failed
    transaction state."""
    result = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-004"), physical_boat_id=PhysicalBoatId("PB-ME-UNKNOWN-2")
        ),
    )
    assert result.status is MarketEpisodeCreationStatus.PHYSICAL_BOAT_NOT_FOUND
    assert episode_conn.info.transaction_status == TransactionStatus.IDLE

    _insert_physical_boat(episode_conn, "PB-ME-004")
    retry = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-004"), physical_boat_id=PhysicalBoatId("PB-ME-004")
        ),
    )
    assert retry.status is MarketEpisodeCreationStatus.CREATED


def test_raw_postgresql_rejects_unknown_physical_boat_id_via_foreign_key(episode_conn: Any) -> None:
    """Proves the database itself enforces referential integrity,
    independent of the Python persistence layer."""
    with pytest.raises(ForeignKeyViolation), episode_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO market_episodes (market_episode_id, physical_boat_id) VALUES (%s, %s)",
            ["ME-RAW-FK", "PB-DOES-NOT-EXIST"],
        )
    episode_conn.rollback()


# ---------------------------------------------------------------------------
# Multiple episodes for one PhysicalBoat -- adversarial case 7
# ---------------------------------------------------------------------------


def test_two_market_episodes_for_same_physical_boat_are_both_valid(episode_conn: Any) -> None:
    _insert_physical_boat(episode_conn, "PB-ME-MULTI")

    result_1 = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-MULTI-1"), physical_boat_id=PhysicalBoatId("PB-ME-MULTI")
        ),
    )
    episode_conn.commit()
    result_2 = create_market_episode(
        episode_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-MULTI-2"), physical_boat_id=PhysicalBoatId("PB-ME-MULTI")
        ),
    )

    assert result_1.status is MarketEpisodeCreationStatus.CREATED
    assert result_2.status is MarketEpisodeCreationStatus.CREATED

    record_1 = fetch_market_episode(episode_conn, MarketEpisodeId("ME-MULTI-1"))
    record_2 = fetch_market_episode(episode_conn, MarketEpisodeId("ME-MULTI-2"))
    assert record_1 is not None and record_2 is not None
    assert record_1.market_episode.physical_boat_id == PhysicalBoatId("PB-ME-MULTI")
    assert record_2.market_episode.physical_boat_id == PhysicalBoatId("PB-ME-MULTI")
    assert record_1.market_episode.id != record_2.market_episode.id


def test_no_uniqueness_constraint_on_physical_boat_id(episode_conn: Any) -> None:
    """Direct SQL proof: two rows sharing one non-null physical_boat_id must
    be permitted by the schema itself, not merely by application logic."""
    _insert_physical_boat(episode_conn, "PB-ME-NOUNIQ")
    with episode_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO market_episodes (market_episode_id, physical_boat_id) VALUES (%s, %s)",
            ["ME-NOUNIQ-1", "PB-ME-NOUNIQ"],
        )
        cur.execute(
            "INSERT INTO market_episodes (market_episode_id, physical_boat_id) VALUES (%s, %s)",
            ["ME-NOUNIQ-2", "PB-ME-NOUNIQ"],
        )
    episode_conn.commit()
    assert _row_count(episode_conn, "ME-NOUNIQ-1") == 1
    assert _row_count(episode_conn, "ME-NOUNIQ-2") == 1


# ---------------------------------------------------------------------------
# Transaction ownership -- CREATED must always mean durably committed
# ---------------------------------------------------------------------------


def test_create_on_a_connection_with_an_open_implicit_transaction_fails_closed(
    episode_conn: Any, episode_url: str
) -> None:
    """Regression guard mirroring the SLICE-0043/0046 material transaction-
    ownership finding: a connection with an already-open transaction (here:
    opened implicitly by a prior readback SELECT) must be rejected before
    any write is attempted."""
    episode_id = MarketEpisodeId("ME-TXN-001")

    pre_existing = fetch_market_episode(episode_conn, episode_id)
    assert pre_existing is None
    assert episode_conn.info.transaction_status != TransactionStatus.IDLE

    with pytest.raises(MarketEpisodeTransactionOwnershipError):
        create_market_episode(
            episode_conn,
            market_episode=MarketEpisode(id=episode_id, physical_boat_id=PhysicalBoatId("PB-X")),
        )

    episode_conn.rollback()
    assert _row_count(episode_conn, "ME-TXN-001") == 0

    verify = psycopg.connect(episode_url)
    try:
        assert fetch_market_episode(verify, episode_id) is None
    finally:
        verify.close()


def test_created_result_is_immediately_durable_from_a_separate_connection(episode_url: str) -> None:
    """The normal IDLE-connection path: create_market_episode() must own and
    commit its own top-level transaction, so a CREATED result is already
    durably visible from a completely separate, freshly opened connection —
    with no explicit commit() call by the original caller at all."""
    setup_conn = psycopg.connect(episode_url)
    try:
        _insert_physical_boat(setup_conn, "PB-ME-TXN-002")
    finally:
        setup_conn.close()

    episode = MarketEpisode(
        id=MarketEpisodeId("ME-TXN-002"), physical_boat_id=PhysicalBoatId("PB-ME-TXN-002")
    )

    writer_conn = psycopg.connect(episode_url)
    try:
        assert writer_conn.info.transaction_status == TransactionStatus.IDLE
        result = create_market_episode(writer_conn, market_episode=episode)
        assert result.status is MarketEpisodeCreationStatus.CREATED
        # No writer_conn.commit() call here — durability must not depend on it.
    finally:
        writer_conn.close()

    reader_conn = psycopg.connect(episode_url)
    try:
        record = fetch_market_episode(reader_conn, episode.id)
    finally:
        reader_conn.close()

    assert record is not None


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency: race-safe creation under concurrent connections
# -- adversarial cases 8-9
# ---------------------------------------------------------------------------


def test_concurrent_identical_creation_resolves_deterministically(episode_url: str) -> None:
    """Two concurrent identical creation attempts must resolve as
    CREATED + ALREADY_EXISTS. No PostgreSQL unique-violation must leak to the
    caller, and exactly one row must exist afterwards."""
    setup_conn = psycopg.connect(episode_url)
    try:
        _insert_physical_boat(setup_conn, "PB-ME-RACE-001")
    finally:
        setup_conn.close()

    episode = MarketEpisode(
        id=MarketEpisodeId("ME-RACE-001"), physical_boat_id=PhysicalBoatId("PB-ME-RACE-001")
    )

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(episode_url)
            try:
                barrier.wait(timeout=10)
                result = create_market_episode(conn, market_episode=episode)
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
        MarketEpisodeCreationStatus.CREATED,
        MarketEpisodeCreationStatus.ALREADY_EXISTS,
    }

    verify = psycopg.connect(episode_url)
    try:
        assert _row_count(verify, "ME-RACE-001") == 1
    finally:
        verify.close()


def test_concurrent_conflicting_creation_fails_closed(episode_url: str) -> None:
    """Two concurrent creations under the same MarketEpisodeId but a
    different existing PhysicalBoatId must resolve as exactly one CREATED
    and exactly one CONFLICT, never two successful writes."""
    setup_conn = psycopg.connect(episode_url)
    try:
        _insert_physical_boat(setup_conn, "PB-ME-RACE2-X")
        _insert_physical_boat(setup_conn, "PB-ME-RACE2-Y")
    finally:
        setup_conn.close()

    episode_id_value = "ME-RACE-002"

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(physical_boat_id_value: str) -> None:
        try:
            conn = psycopg.connect(episode_url)
            try:
                barrier.wait(timeout=10)
                result = create_market_episode(
                    conn,
                    market_episode=MarketEpisode(
                        id=MarketEpisodeId(episode_id_value),
                        physical_boat_id=PhysicalBoatId(physical_boat_id_value),
                    ),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("PB-ME-RACE2-X",)),
        threading.Thread(target=_worker, args=("PB-ME-RACE2-Y",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(MarketEpisodeCreationStatus.CREATED) == 1, statuses
    assert statuses.count(MarketEpisodeCreationStatus.CONFLICT) == 1, statuses

    verify = psycopg.connect(episode_url)
    try:
        assert _row_count(verify, "ME-RACE-002") == 1
    finally:
        verify.close()
