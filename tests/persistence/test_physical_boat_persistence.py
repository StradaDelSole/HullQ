"""PostgreSQL-backed PhysicalBoat identity persistence tests — SLICE-0046.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0046 Alembic head (SLICE-0042 baseline +
physical_boat_identity revision), mirroring the SLICE-0043/0045 integration
test isolation pattern in tests/persistence/test_native_listing_persistence.py.
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

from hullq.domain.market_identity import BoatDesignRef, PhysicalBoat, PhysicalBoatId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.physical_boat import (
    PhysicalBoatCreationStatus,
    PhysicalBoatTransactionOwnershipError,
    create_physical_boat,
    fetch_physical_boat,
)

# ---------------------------------------------------------------------------
# Disposable-schema fixture: genuinely-empty schema -> SLICE-0046 Alembic head
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
def boat_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0046_{uuid.uuid4().hex[:16]}"
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
def boat_conn(boat_url: str) -> Generator[Any]:
    conn = psycopg.connect(boat_url)
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


def _row_count(conn: Any, physical_boat_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM physical_boats WHERE physical_boat_id = %s",
            [physical_boat_id],
        )
        return int(cur.fetchone()[0])


def _insert_canonical_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    """Minimal direct-SQL admission of one canonical BoatDesign row, bypassing
    the real admission pipeline -- this test only needs an existing row in
    ``canonical_boat_designs`` for the FK authority PhysicalBoat references,
    not to exercise canonical admission semantics themselves."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", "{}", "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Migration boundary
# ---------------------------------------------------------------------------


def test_migration_adds_only_physical_boats_table(boat_conn: Any) -> None:
    tables = _table_names(boat_conn)
    assert "physical_boats" in tables
    # Legacy 001/002 tables remain present and untouched by the new revision.
    assert {"research_bundles", "canonical_boat_designs"} <= tables


def test_repeated_upgrade_head_is_idempotent(boat_url: str) -> None:
    alembic_upgrade_head(boat_url)  # second call must not raise or duplicate DDL
    conn = psycopg.connect(boat_url)
    try:
        assert "physical_boats" in _table_names(conn)
    finally:
        conn.close()


def test_physical_boats_columns_are_exactly_the_minimal_identity_envelope(boat_conn: Any) -> None:
    """Structural regression: no MarketEpisode/listing attachment, no
    Organization/account ownership and no PHYSICAL_BOAT marketplace fact
    column, and -- since no content_hash column exists at all here -- a
    stored hash can never be the sole authority for retry/collision
    classification (there is nothing to authorize from)."""
    assert _column_names(boat_conn, "physical_boats") == {
        "physical_boat_id",
        "boat_design_ref",
        "created_at",
    }


# ---------------------------------------------------------------------------
# Durable creation / exact readback
# ---------------------------------------------------------------------------


def test_create_with_valid_design_ref_and_exact_readback(boat_conn: Any) -> None:
    _insert_canonical_boat_design(boat_conn, "BD-001", "BM-001")

    result = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-001"), boat_design_ref=BoatDesignRef("BD-001")
        ),
    )
    assert result.status is PhysicalBoatCreationStatus.CREATED

    record = fetch_physical_boat(boat_conn, PhysicalBoatId("PB-001"))
    assert record is not None
    assert record.physical_boat == PhysicalBoat(
        id=PhysicalBoatId("PB-001"), boat_design_ref=BoatDesignRef("BD-001")
    )
    assert record.created_at is not None


def test_create_unresolved_with_no_design_ref_and_exact_readback(boat_conn: Any) -> None:
    result = create_physical_boat(
        boat_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-002"))
    )
    assert result.status is PhysicalBoatCreationStatus.CREATED

    record = fetch_physical_boat(boat_conn, PhysicalBoatId("PB-002"))
    assert record is not None
    assert record.physical_boat.boat_design_ref is None


def test_readback_of_missing_physical_boat_returns_none(boat_conn: Any) -> None:
    assert fetch_physical_boat(boat_conn, PhysicalBoatId("PB-DOES-NOT-EXIST")) is None


# ---------------------------------------------------------------------------
# Canonical BoatDesignRef FK integrity
# ---------------------------------------------------------------------------


def test_new_id_with_unknown_design_ref_fails_closed_and_writes_no_row(boat_conn: Any) -> None:
    result = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-003"), boat_design_ref=BoatDesignRef("BD-UNKNOWN")
        ),
    )
    assert result.status is PhysicalBoatCreationStatus.DESIGN_NOT_FOUND
    assert _row_count(boat_conn, "PB-003") == 0
    assert fetch_physical_boat(boat_conn, PhysicalBoatId("PB-003")) is None


def test_raw_postgresql_rejects_unknown_design_ref_via_foreign_key(boat_conn: Any) -> None:
    """Proves the database itself enforces referential integrity,
    independent of the Python persistence layer."""
    with pytest.raises(ForeignKeyViolation), boat_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boats (physical_boat_id, boat_design_ref) VALUES (%s, %s)",
            ["PB-RAW-FK", "BD-DOES-NOT-EXIST"],
        )
    boat_conn.rollback()


def test_design_not_found_leaves_connection_usable_for_a_subsequent_call(boat_conn: Any) -> None:
    """The internal ForeignKeyViolation catch must leave *conn* IDLE again so
    a caller can immediately reuse it, rather than leaking a failed
    transaction state."""
    result = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-004"), boat_design_ref=BoatDesignRef("BD-UNKNOWN")
        ),
    )
    assert result.status is PhysicalBoatCreationStatus.DESIGN_NOT_FOUND
    assert boat_conn.info.transaction_status == TransactionStatus.IDLE

    retry = create_physical_boat(boat_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-004")))
    assert retry.status is PhysicalBoatCreationStatus.CREATED


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_identical_retry_is_idempotent_and_preserves_created_at(boat_conn: Any) -> None:
    _insert_canonical_boat_design(boat_conn, "BD-IDEM", "BM-IDEM")
    boat = PhysicalBoat(id=PhysicalBoatId("PB-IDEM-001"), boat_design_ref=BoatDesignRef("BD-IDEM"))

    first = create_physical_boat(boat_conn, physical_boat=boat)
    assert first.status is PhysicalBoatCreationStatus.CREATED
    first_record = fetch_physical_boat(boat_conn, boat.id)
    assert first_record is not None
    boat_conn.commit()  # end the readback's implicit transaction

    second = create_physical_boat(boat_conn, physical_boat=boat)
    assert second.status is PhysicalBoatCreationStatus.ALREADY_EXISTS

    assert _row_count(boat_conn, "PB-IDEM-001") == 1
    second_record = fetch_physical_boat(boat_conn, boat.id)
    assert second_record is not None
    assert second_record.created_at == first_record.created_at


def test_unresolved_retry_is_idempotent(boat_conn: Any) -> None:
    boat = PhysicalBoat(id=PhysicalBoatId("PB-IDEM-002"))

    create_physical_boat(boat_conn, physical_boat=boat)
    boat_conn.commit()

    second = create_physical_boat(boat_conn, physical_boat=boat)
    assert second.status is PhysicalBoatCreationStatus.ALREADY_EXISTS
    assert _row_count(boat_conn, "PB-IDEM-002") == 1


# ---------------------------------------------------------------------------
# Conflict — fail closed, never overwrite, never silently resolve
# ---------------------------------------------------------------------------


def test_same_id_none_vs_design_conflicts_and_stays_unresolved(boat_conn: Any) -> None:
    _insert_canonical_boat_design(boat_conn, "BD-CONF1", "BM-CONF1")
    boat_id = PhysicalBoatId("PB-CONF-001")

    create_physical_boat(boat_conn, physical_boat=PhysicalBoat(id=boat_id))
    original = fetch_physical_boat(boat_conn, boat_id)
    assert original is not None
    assert original.physical_boat.boat_design_ref is None
    boat_conn.commit()

    conflict = create_physical_boat(
        boat_conn, physical_boat=PhysicalBoat(id=boat_id, boat_design_ref=BoatDesignRef("BD-CONF1"))
    )
    assert conflict.status is PhysicalBoatCreationStatus.CONFLICT

    after = fetch_physical_boat(boat_conn, boat_id)
    assert after == original
    assert after.physical_boat.boat_design_ref is None
    assert _row_count(boat_conn, "PB-CONF-001") == 1


def test_same_id_design_x_vs_design_y_conflicts(boat_conn: Any) -> None:
    _insert_canonical_boat_design(boat_conn, "BD-CONF2X", "BM-CONF2X")
    _insert_canonical_boat_design(boat_conn, "BD-CONF2Y", "BM-CONF2Y")
    boat_id = PhysicalBoatId("PB-CONF-002")

    create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(id=boat_id, boat_design_ref=BoatDesignRef("BD-CONF2X")),
    )
    original = fetch_physical_boat(boat_conn, boat_id)
    assert original is not None
    boat_conn.commit()

    conflict = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(id=boat_id, boat_design_ref=BoatDesignRef("BD-CONF2Y")),
    )
    assert conflict.status is PhysicalBoatCreationStatus.CONFLICT

    after = fetch_physical_boat(boat_conn, boat_id)
    assert after == original
    assert after.physical_boat.boat_design_ref == BoatDesignRef("BD-CONF2X")
    assert _row_count(boat_conn, "PB-CONF-002") == 1


def test_existing_id_with_different_unknown_design_conflicts_not_design_not_found(
    boat_conn: Any,
) -> None:
    """Once a PhysicalBoatId is occupied, a retry with an unknown different
    BoatDesignRef must classify as CONFLICT -- the identity-collision
    question -- never DESIGN_NOT_FOUND, and must leave the existing row
    untouched."""
    _insert_canonical_boat_design(boat_conn, "BD-CONF3", "BM-CONF3")
    boat_id = PhysicalBoatId("PB-CONF-003")

    create_physical_boat(
        boat_conn, physical_boat=PhysicalBoat(id=boat_id, boat_design_ref=BoatDesignRef("BD-CONF3"))
    )
    original = fetch_physical_boat(boat_conn, boat_id)
    assert original is not None
    boat_conn.commit()

    conflict = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(id=boat_id, boat_design_ref=BoatDesignRef("BD-CONF3-UNKNOWN")),
    )
    assert conflict.status is PhysicalBoatCreationStatus.CONFLICT
    assert conflict.status is not PhysicalBoatCreationStatus.DESIGN_NOT_FOUND

    after = fetch_physical_boat(boat_conn, boat_id)
    assert after == original
    assert after.physical_boat.boat_design_ref == BoatDesignRef("BD-CONF3")
    assert _row_count(boat_conn, "PB-CONF-003") == 1


# ---------------------------------------------------------------------------
# Sister-ship semantics — many PhysicalBoats to one BoatDesign
# ---------------------------------------------------------------------------


def test_two_physical_boats_share_one_design_and_both_persist(boat_conn: Any) -> None:
    _insert_canonical_boat_design(boat_conn, "BD-SISTER", "BM-SISTER")

    result_a = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-SISTER-A"), boat_design_ref=BoatDesignRef("BD-SISTER")
        ),
    )
    boat_conn.commit()
    result_c = create_physical_boat(
        boat_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-SISTER-C"), boat_design_ref=BoatDesignRef("BD-SISTER")
        ),
    )

    assert result_a.status is PhysicalBoatCreationStatus.CREATED
    assert result_c.status is PhysicalBoatCreationStatus.CREATED

    record_a = fetch_physical_boat(boat_conn, PhysicalBoatId("PB-SISTER-A"))
    record_c = fetch_physical_boat(boat_conn, PhysicalBoatId("PB-SISTER-C"))
    assert record_a is not None and record_c is not None
    assert record_a.physical_boat.boat_design_ref == BoatDesignRef("BD-SISTER")
    assert record_c.physical_boat.boat_design_ref == BoatDesignRef("BD-SISTER")
    assert record_a.physical_boat.id != record_c.physical_boat.id


def test_no_uniqueness_constraint_on_boat_design_ref(boat_conn: Any) -> None:
    """Direct SQL proof: two rows sharing one non-null boat_design_ref must
    be permitted by the schema itself, not merely by application logic."""
    _insert_canonical_boat_design(boat_conn, "BD-NOUNIQ", "BM-NOUNIQ")
    with boat_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boats (physical_boat_id, boat_design_ref) VALUES (%s, %s)",
            ["PB-NOUNIQ-1", "BD-NOUNIQ"],
        )
        cur.execute(
            "INSERT INTO physical_boats (physical_boat_id, boat_design_ref) VALUES (%s, %s)",
            ["PB-NOUNIQ-2", "BD-NOUNIQ"],
        )
    boat_conn.commit()
    assert _row_count(boat_conn, "PB-NOUNIQ-1") == 1
    assert _row_count(boat_conn, "PB-NOUNIQ-2") == 1


# ---------------------------------------------------------------------------
# Transaction ownership — CREATED must always mean durably committed
# ---------------------------------------------------------------------------


def test_create_on_a_connection_with_an_open_implicit_transaction_fails_closed(
    boat_conn: Any, boat_url: str
) -> None:
    """Regression guard mirroring the SLICE-0043 material transaction-
    ownership finding: a connection with an already-open transaction (here:
    opened implicitly by a prior readback SELECT) must be rejected before
    any write is attempted."""
    boat_id = PhysicalBoatId("PB-TXN-001")

    pre_existing = fetch_physical_boat(boat_conn, boat_id)
    assert pre_existing is None
    assert boat_conn.info.transaction_status != TransactionStatus.IDLE

    with pytest.raises(PhysicalBoatTransactionOwnershipError):
        create_physical_boat(boat_conn, physical_boat=PhysicalBoat(id=boat_id))

    boat_conn.rollback()
    assert _row_count(boat_conn, "PB-TXN-001") == 0

    verify = psycopg.connect(boat_url)
    try:
        assert fetch_physical_boat(verify, boat_id) is None
    finally:
        verify.close()


def test_created_result_is_immediately_durable_from_a_separate_connection(boat_url: str) -> None:
    """The normal IDLE-connection path: create_physical_boat() must own and
    commit its own top-level transaction, so a CREATED result is already
    durably visible from a completely separate, freshly opened connection —
    with no explicit commit() call by the original caller at all."""
    boat = PhysicalBoat(id=PhysicalBoatId("PB-TXN-002"))

    writer_conn = psycopg.connect(boat_url)
    try:
        assert writer_conn.info.transaction_status == TransactionStatus.IDLE
        result = create_physical_boat(writer_conn, physical_boat=boat)
        assert result.status is PhysicalBoatCreationStatus.CREATED
        # No writer_conn.commit() call here — durability must not depend on it.
    finally:
        writer_conn.close()

    reader_conn = psycopg.connect(boat_url)
    try:
        record = fetch_physical_boat(reader_conn, boat.id)
    finally:
        reader_conn.close()

    assert record is not None


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency: race-safe creation under concurrent connections
# ---------------------------------------------------------------------------


def test_concurrent_identical_creation_resolves_deterministically(boat_url: str) -> None:
    """Two concurrent identical creation attempts must resolve as
    CREATED + ALREADY_EXISTS. No PostgreSQL unique-violation must leak to the
    caller, and exactly one row must exist afterwards."""
    boat = PhysicalBoat(id=PhysicalBoatId("PB-RACE-001"))

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(boat_url)
            try:
                barrier.wait(timeout=10)
                result = create_physical_boat(conn, physical_boat=boat)
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
        PhysicalBoatCreationStatus.CREATED,
        PhysicalBoatCreationStatus.ALREADY_EXISTS,
    }

    verify = psycopg.connect(boat_url)
    try:
        assert _row_count(verify, "PB-RACE-001") == 1
    finally:
        verify.close()


def test_concurrent_conflicting_creation_fails_closed(boat_url: str) -> None:
    """Two concurrent creations under the same PhysicalBoatId but a
    different immutable envelope (NONE vs a real BoatDesignRef) must resolve
    as exactly one CREATED and exactly one CONFLICT, never two successful
    writes."""
    setup_conn = psycopg.connect(boat_url)
    try:
        _insert_canonical_boat_design(setup_conn, "BD-RACE2", "BM-RACE2")
    finally:
        setup_conn.close()

    boat_id_value = "PB-RACE-002"

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(design_ref: BoatDesignRef | None) -> None:
        try:
            conn = psycopg.connect(boat_url)
            try:
                barrier.wait(timeout=10)
                result = create_physical_boat(
                    conn,
                    physical_boat=PhysicalBoat(
                        id=PhysicalBoatId(boat_id_value), boat_design_ref=design_ref
                    ),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(None,)),
        threading.Thread(target=_worker, args=(BoatDesignRef("BD-RACE2"),)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(PhysicalBoatCreationStatus.CREATED) == 1, statuses
    assert statuses.count(PhysicalBoatCreationStatus.CONFLICT) == 1, statuses

    verify = psycopg.connect(boat_url)
    try:
        assert _row_count(verify, "PB-RACE-002") == 1
    finally:
        verify.close()
