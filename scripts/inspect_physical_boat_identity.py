"""SLICE-0046 PhysicalBoat identity persistence owner-inspection.

Executes real PostgreSQL/Alembic behavior to demonstrate the durable
PhysicalBoat identity capability required by SLICE-0046: creation with a
valid canonical BoatDesignRef, unresolved creation with no design link,
exact typed readback of both, idempotent retry, fail-closed collision
semantics (including an unknown different design ref against an already-
occupied identity), sister-ship design sharing, fail-closed DESIGN_NOT_FOUND
for a genuinely new identity with an unknown design, race-safe concurrent
creation, and the transaction-ownership guarantee behind "CREATED implies
durably committed" -- plus the absence of any MarketEpisode/NativeListing
attachment, Organization/broker ownership or PHYSICAL_BOAT marketplace fact
projection.

Run: uv run python scripts/inspect_physical_boat_identity.py

Requires HULLQ_TEST_DATABASE_URL to point at a local PostgreSQL 18 instance.
Runs against its own freshly created/dropped disposable PostgreSQL *schema*
(isolated via the connection ``options=-c search_path=...`` parameter), then
brings that schema from genuinely empty to the SLICE-0046 Alembic head
(SLICE-0042 baseline + the physical_boat_identity revision).
"""

from __future__ import annotations

import dataclasses
import sys
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg.pq import TransactionStatus

from hullq.domain.market_identity import BoatDesignRef, PhysicalBoat, PhysicalBoatId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.physical_boat import (
    PhysicalBoatCreationStatus,
    PhysicalBoatRecord,
    PhysicalBoatTransactionOwnershipError,
    create_physical_boat,
    fetch_physical_boat,
)

_DESIGN_X = "BD-0046-X"
_DESIGN_Y = "BD-0046-Y"
_DESIGN_UNKNOWN = "BD-0046-UNKNOWN"

# The exact minimal column set the SLICE-0046 contract authorizes. Any
# additional column (MarketEpisode/listing attachment, Organization/account
# ownership, or a PHYSICAL_BOAT marketplace fact) would fail this structural
# check.
_EXPECTED_COLUMNS = {"physical_boat_id", "boat_design_ref", "created_at"}


def _base_url() -> str:
    import os

    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL 18 instance, e.g.\n"
            f'  {HULLQ_TEST_DATABASE_URL_ENV}="postgresql://hullq_test:hullq_test@localhost:5432/hullq_test"',
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


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


def _row_count(conn: psycopg.Connection, physical_boat_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM physical_boats WHERE physical_boat_id = %s",
            [physical_boat_id],
        )
        return int(cur.fetchone()[0])


def _actual_columns(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'physical_boats'"
        )
        return {row[0] for row in cur.fetchall()}


def _seed_canonical_boat_design(conn: psycopg.Connection, design_id: str, model_id: str) -> None:
    """Minimal direct-SQL admission of one canonical BoatDesign row -- this
    inspection only needs an existing row in canonical_boat_designs for the
    FK authority PhysicalBoat references, not to exercise canonical
    admission semantics themselves."""
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


def _transaction_ownership_scenario(url: str) -> bool:
    """Demonstrates the "CREATED implies durably committed" guarantee."""
    rejected_id = "PB-0046-TXN-REJECTED"
    non_idle_conn = psycopg.connect(url)
    try:
        fetch_physical_boat(non_idle_conn, PhysicalBoatId(rejected_id))
        opened_implicit_txn = non_idle_conn.info.transaction_status != TransactionStatus.IDLE

        rejected = False
        try:
            create_physical_boat(
                non_idle_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(rejected_id))
            )
        except PhysicalBoatTransactionOwnershipError:
            rejected = True
        non_idle_conn.rollback()
        rows_written = _row_count(non_idle_conn, rejected_id)
    finally:
        non_idle_conn.close()

    fail_closed_ok = opened_implicit_txn and rejected and rows_written == 0
    print(
        "implicit-transaction connection create -> "
        f"{'REJECTED' if rejected else 'NOT REJECTED (unsafe)'}"
    )
    print(f"rows written by rejected attempt        -> {rows_written}")

    durable_id = "PB-0046-TXN-DURABLE"
    writer_conn = psycopg.connect(url)
    try:
        was_idle = writer_conn.info.transaction_status == TransactionStatus.IDLE
        result = create_physical_boat(
            writer_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(durable_id))
        )
        created_ok = result.status is PhysicalBoatCreationStatus.CREATED
        # No writer_conn.commit() call — durability must not depend on it.
    finally:
        writer_conn.close()

    reader_conn = psycopg.connect(url)
    try:
        visible_from_other_connection = (
            fetch_physical_boat(reader_conn, PhysicalBoatId(durable_id)) is not None
        )
    finally:
        reader_conn.close()

    durable_ok = was_idle and created_ok and visible_from_other_connection
    print(
        "durable creation visible from a separate connection -> "
        f"{'YES' if visible_from_other_connection else 'NO'}\n"
    )

    return fail_closed_ok and durable_ok


def _concurrency_scenario(url: str) -> bool:
    import threading

    # -- same ID, same envelope: one CREATED, one ALREADY_EXISTS -------------
    same_results: list[PhysicalBoatCreationStatus] = []
    barrier1 = threading.Barrier(2)

    def _worker_same() -> None:
        conn = psycopg.connect(url)
        try:
            barrier1.wait(timeout=10)
            result = create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0046-RACE-SAME"))
            )
            same_results.append(result.status)
        finally:
            conn.close()

    threads = [threading.Thread(target=_worker_same) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    same_ok = sorted(s.value for s in same_results) == sorted(
        [PhysicalBoatCreationStatus.CREATED.value, PhysicalBoatCreationStatus.ALREADY_EXISTS.value]
    )
    verify = psycopg.connect(url)
    try:
        same_row_ok = _row_count(verify, "PB-0046-RACE-SAME") == 1
    finally:
        verify.close()
    print(f"concurrent same-ID/same-envelope   -> {sorted(s.value for s in same_results)}")
    print(f"resulting row count                -> {'1' if same_row_ok else 'NOT 1'}")

    # -- same ID, different envelope: one CREATED, one CONFLICT --------------
    diff_results: list[PhysicalBoatCreationStatus] = []
    barrier2 = threading.Barrier(2)

    def _worker_diff(design_ref: BoatDesignRef | None) -> None:
        conn = psycopg.connect(url)
        try:
            barrier2.wait(timeout=10)
            result = create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(
                    id=PhysicalBoatId("PB-0046-RACE-DIFF"), boat_design_ref=design_ref
                ),
            )
            diff_results.append(result.status)
        finally:
            conn.close()

    threads = [
        threading.Thread(target=_worker_diff, args=(None,)),
        threading.Thread(target=_worker_diff, args=(BoatDesignRef(_DESIGN_X),)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    diff_ok = sorted(s.value for s in diff_results) == sorted(
        [PhysicalBoatCreationStatus.CREATED.value, PhysicalBoatCreationStatus.CONFLICT.value]
    )
    verify = psycopg.connect(url)
    try:
        diff_row_ok = _row_count(verify, "PB-0046-RACE-DIFF") == 1
    finally:
        verify.close()
    print(f"concurrent same-ID/different-envelope -> {sorted(s.value for s in diff_results)}")
    print(f"resulting row count                   -> {'1' if diff_row_ok else 'NOT 1'}\n")

    return same_ok and same_row_ok and diff_ok and diff_row_ok


def main() -> int:
    base_url = _base_url()
    schema_name = f"hullq_s0046_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    url = _with_search_path(base_url, schema_name)

    try:
        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)

        conn = psycopg.connect(url)
        try:
            print("PHYSICAL BOAT IDENTITY\n")
            ok = True

            _seed_canonical_boat_design(conn, _DESIGN_X, "BM-0046-X")
            _seed_canonical_boat_design(conn, _DESIGN_Y, "BM-0046-Y")

            # -- A: create with valid BoatDesignRef X + exact readback -------
            boat_a = PhysicalBoat(
                id=PhysicalBoatId("PB-0046-A"), boat_design_ref=BoatDesignRef(_DESIGN_X)
            )
            result_a = create_physical_boat(conn, physical_boat=boat_a)
            record_a = fetch_physical_boat(conn, boat_a.id)
            conn.commit()  # end the readback's implicit transaction
            readback_a_exact = record_a is not None and record_a.physical_boat == boat_a
            ok &= result_a.status is PhysicalBoatCreationStatus.CREATED and readback_a_exact
            print(f"PhysicalBoat A + BoatDesignRef X -> {result_a.status.value.upper()}")
            print(
                f"readback A                        -> {'EXACT' if readback_a_exact else 'MISMATCH'}\n"
            )

            # -- same A + same X: ALREADY_EXISTS, exactly one row -------------
            retry_a = create_physical_boat(conn, physical_boat=boat_a)
            row_count_a = _row_count(conn, "PB-0046-A")
            conn.commit()  # end the row-count readback's implicit transaction
            ok &= retry_a.status is PhysicalBoatCreationStatus.ALREADY_EXISTS and row_count_a == 1
            print(f"same A + same X                   -> {retry_a.status.value.upper()}")
            print(f"durable row count for A            -> {row_count_a}\n")

            # -- same A + different Y: CONFLICT, A still references X --------
            conflict_a_y = create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(id=boat_a.id, boat_design_ref=BoatDesignRef(_DESIGN_Y)),
            )
            after_conflict_a_y = fetch_physical_boat(conn, boat_a.id)
            conn.commit()
            a_unchanged_1 = (
                after_conflict_a_y is not None
                and after_conflict_a_y.physical_boat.boat_design_ref == BoatDesignRef(_DESIGN_X)
            )
            ok &= conflict_a_y.status is PhysicalBoatCreationStatus.CONFLICT and a_unchanged_1
            print(f"same A + different Y              -> {conflict_a_y.status.value.upper()}")
            print(f"A still references X               -> {'YES' if a_unchanged_1 else 'NO'}\n")

            # -- same A + unknown Z: CONFLICT, not DESIGN_NOT_FOUND -----------
            conflict_a_z = create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(
                    id=boat_a.id, boat_design_ref=BoatDesignRef(_DESIGN_UNKNOWN)
                ),
            )
            after_conflict_a_z = fetch_physical_boat(conn, boat_a.id)
            conn.commit()
            a_unchanged_2 = (
                after_conflict_a_z is not None
                and after_conflict_a_z.physical_boat.boat_design_ref == BoatDesignRef(_DESIGN_X)
            )
            ok &= (
                conflict_a_z.status is PhysicalBoatCreationStatus.CONFLICT
                and conflict_a_z.status is not PhysicalBoatCreationStatus.DESIGN_NOT_FOUND
                and a_unchanged_2
            )
            print(f"same A + unknown BoatDesignRef Z  -> {conflict_a_z.status.value.upper()}")
            print(f"A still references X               -> {'YES' if a_unchanged_2 else 'NO'}\n")

            # -- B: create unresolved, no BoatDesignRef -----------------------
            boat_b = PhysicalBoat(id=PhysicalBoatId("PB-0046-B"))
            result_b = create_physical_boat(conn, physical_boat=boat_b)
            record_b = fetch_physical_boat(conn, boat_b.id)
            conn.commit()
            readback_b_exact = (
                record_b is not None and record_b.physical_boat.boat_design_ref is None
            )
            ok &= result_b.status is PhysicalBoatCreationStatus.CREATED and readback_b_exact
            print(f"PhysicalBoat B, unresolved        -> {result_b.status.value.upper()}")
            print(f"readback B keeps NONE              -> {'YES' if readback_b_exact else 'NO'}\n")

            # -- retry B + X: CONFLICT, no silent unresolved->resolved --------
            retry_b_x = create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(id=boat_b.id, boat_design_ref=BoatDesignRef(_DESIGN_X)),
            )
            after_retry_b = fetch_physical_boat(conn, boat_b.id)
            conn.commit()
            b_still_unresolved = (
                after_retry_b is not None and after_retry_b.physical_boat.boat_design_ref is None
            )
            ok &= retry_b_x.status is PhysicalBoatCreationStatus.CONFLICT and b_still_unresolved
            print(f"retry B + BoatDesignRef X         -> {retry_b_x.status.value.upper()}")
            print(
                f"B still unresolved                 -> {'YES' if b_still_unresolved else 'NO'}\n"
            )

            # -- C: same BoatDesignRef X as A, sister ships -------------------
            boat_c = PhysicalBoat(
                id=PhysicalBoatId("PB-0046-C"), boat_design_ref=BoatDesignRef(_DESIGN_X)
            )
            result_c = create_physical_boat(conn, physical_boat=boat_c)
            record_c = fetch_physical_boat(conn, boat_c.id)
            conn.commit()
            sister_ships_ok = (
                record_c is not None
                and record_c.physical_boat.boat_design_ref == BoatDesignRef(_DESIGN_X)
                and record_a is not None
                and record_a.physical_boat.id != record_c.physical_boat.id
            )
            ok &= result_c.status is PhysicalBoatCreationStatus.CREATED and sister_ships_ok
            print(f"PhysicalBoat C + BoatDesignRef X  -> {result_c.status.value.upper()}")
            print(f"A and C coexist as sister ships    -> {'YES' if sister_ships_ok else 'NO'}\n")

            # -- D: new PhysicalBoatId + unknown design -----------------------
            result_d = create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(
                    id=PhysicalBoatId("PB-0046-D"), boat_design_ref=BoatDesignRef(_DESIGN_UNKNOWN)
                ),
            )
            row_count_d = _row_count(conn, "PB-0046-D")
            ok &= (
                result_d.status is PhysicalBoatCreationStatus.DESIGN_NOT_FOUND and row_count_d == 0
            )
            print(f"new PhysicalBoat D + unknown design -> {result_d.status.value.upper()}")
            print(f"row count for D                     -> {row_count_d}\n")

            # -- transaction ownership + concurrency --------------------------
            ok &= _transaction_ownership_scenario(url)
            ok &= _concurrency_scenario(url)

            # -- scope/truth regression: minimal envelope only ----------------
            record_fields = {f.name for f in dataclasses.fields(PhysicalBoatRecord)}
            no_extra_facts = record_fields == {"physical_boat", "created_at"}
            actual_columns = _actual_columns(conn)
            no_scope_creep_columns = actual_columns == _EXPECTED_COLUMNS
            ok &= no_extra_facts and no_scope_creep_columns
            print(f"RECORD TYPE MINIMAL ENVELOPE ONLY -> {'YES' if no_extra_facts else 'NO'}")
            print(
                f"NO MARKET_EPISODE/LISTING/ORG/FACT COLUMNS -> {'YES' if no_scope_creep_columns else 'NO'}"
            )
            print(f"PHYSICAL BOAT IDENTITY RESULT -> {'PASS' if ok else 'FAIL'}")

            return 0 if ok else 1
        finally:
            conn.close()
    finally:
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
