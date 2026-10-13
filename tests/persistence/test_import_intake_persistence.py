"""PostgreSQL integration tests for SLICE-0083 `hullq.persistence.import_intake`.

Covers the durable staging/mapping lifecycle and the atomic per-row D26
identity-mapping primitive `confirm_import_row`: new-key create, exact
replay (ALREADY_IMPORTED), changed-payload-same-key (CONFLICT_REVIEW),
idempotent resume of an already-confirmed row, and a simulated concurrent
first-confirm race over the same key resolved by the real unique
constraint.
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

from hullq.domain.import_intake import (
    ImportFormat,
    ImportRowOutcome,
    ImportSource,
    ParsedTable,
    RowPreviewClassification,
    SourceRecordKey,
    StagedRowPreview,
    apply_mapping_to_rows,
    compute_file_sha256,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.import_intake import (
    MAX_PENDING_BATCHES_PER_ORGANIZATION,
    ApplyMappingOutcome,
    ImportBatchStatus,
    apply_import_batch_mapping,
    claim_or_check_snapshot_lineage,
    confirm_import_row,
    count_pending_batches_for_organization,
    create_import_batch_awaiting_mapping,
    fetch_import_batch,
    fetch_import_source_mapping,
    list_import_rows,
    lock_organization_import_batch_admission,
    purge_all_expired_unconfirmed_batches,
)
from hullq.persistence.professional_listing_draft import create_professional_listing_draft


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
def import_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0083_{uuid.uuid4().hex[:16]}"
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
def conn(import_url: str) -> Generator[Any]:
    connection = psycopg.connect(import_url)
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
            "(organization_id, professional_category, publishing_eligibility, public_display_name) "
            "VALUES (%s, %s, %s, %s)",
            [organization_id.value, "BROKER", "ELIGIBLE", organization_id.value],
        )
    conn.commit()


_HEADERS = ("Boat Name", "Build Year", "Price", "Ref")
_MAPPING = {
    "Boat Name": "physical_boat.boat_name",
    "Build Year": "physical_boat.build_year",
    "Price": "listing_offer.asking_price_amount",
    "Ref": "__source_record_key__",
}


def _staged_rows(data_rows: tuple[tuple[str | None, ...], ...]) -> tuple[StagedRowPreview, ...]:
    table = ParsedTable(headers=_HEADERS, rows=data_rows)
    digest = compute_file_sha256(b"irrelevant-for-non-snapshot-mode")
    return apply_mapping_to_rows(table, _MAPPING, snapshot_mode=False, file_sha256=digest)


def _create_draft_closure(
    conn: Any, org_id: MarketplaceOrganizationId, account_id: AccountId
) -> Any:
    from hullq.domain.professional_listing_draft import parse_professional_listing_draft_request

    def _create(wire: dict[str, Any]) -> Any:
        request = parse_professional_listing_draft_request(wire)
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account_id,
            broker_listing_reference=request.broker_listing_reference,
            broker_description=request.broker_description,
            payload=request.common,
        )
        return record.draft_id

    return _create


class TestImportBatchLifecycle:
    def test_create_and_apply_mapping(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)

        table = ParsedTable(headers=_HEADERS, rows=(("Aria", "1998", "125000", "REF-1"),))
        digest = compute_file_sha256(b"abc")
        with conn.transaction():
            batch = create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("Feed1"),
                worksheet_name=None,
                file_sha256=digest,
                file_byte_size=100,
                staged_table=table,
            )
        assert batch.status is ImportBatchStatus.AWAITING_MAPPING
        assert batch.staged_table == table

        rows = apply_mapping_to_rows(table, _MAPPING, snapshot_mode=False, file_sha256=digest)
        with conn.transaction():
            outcome = apply_import_batch_mapping(
                conn,
                batch_id=batch.batch_id,
                owner_organization_id=org_id,
                column_mapping=_MAPPING,
                snapshot_mode=False,
                rows=rows,
            )
        assert outcome is ApplyMappingOutcome.OK

        refetched = fetch_import_batch(conn, batch_id=batch.batch_id, owner_organization_id=org_id)
        assert refetched is not None
        assert refetched.status is ImportBatchStatus.MAPPED
        assert refetched.staged_table is None
        assert refetched.row_count == 1

        imported_rows = list_import_rows(conn, batch_id=batch.batch_id)
        assert len(imported_rows) == 1
        assert imported_rows[0].preview_classification is RowPreviewClassification.VALID

    def test_apply_mapping_twice_is_wrong_state(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        table = ParsedTable(headers=_HEADERS, rows=(("Aria", "1998", "125000", "REF-1"),))
        digest = compute_file_sha256(b"abc")
        with conn.transaction():
            batch = create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("Feed1"),
                worksheet_name=None,
                file_sha256=digest,
                file_byte_size=100,
                staged_table=table,
            )
        rows = apply_mapping_to_rows(table, _MAPPING, snapshot_mode=False, file_sha256=digest)
        with conn.transaction():
            first = apply_import_batch_mapping(
                conn,
                batch_id=batch.batch_id,
                owner_organization_id=org_id,
                column_mapping=_MAPPING,
                snapshot_mode=False,
                rows=rows,
            )
        assert first is ApplyMappingOutcome.OK
        with conn.transaction():
            second = apply_import_batch_mapping(
                conn,
                batch_id=batch.batch_id,
                owner_organization_id=org_id,
                column_mapping=_MAPPING,
                snapshot_mode=False,
                rows=rows,
            )
        assert second is ApplyMappingOutcome.WRONG_STATE

    def test_foreign_organization_cannot_see_or_map_batch(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        foreign_org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_organization(conn, foreign_org_id)
        _seed_account(conn, account_id)
        table = ParsedTable(headers=_HEADERS, rows=(("Aria", "1998", "125000", "REF-1"),))
        digest = compute_file_sha256(b"abc")
        with conn.transaction():
            batch = create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("Feed1"),
                worksheet_name=None,
                file_sha256=digest,
                file_byte_size=100,
                staged_table=table,
            )
        assert (
            fetch_import_batch(conn, batch_id=batch.batch_id, owner_organization_id=foreign_org_id)
            is None
        )


class TestConfirmImportRow:
    def _mapped_batch_and_rows(
        self,
        conn: Any,
        org_id: MarketplaceOrganizationId,
        account_id: AccountId,
        import_source: str,
        data_rows: tuple[tuple[str | None, ...], ...],
    ) -> tuple[Any, tuple[Any, ...]]:
        table = ParsedTable(headers=_HEADERS, rows=data_rows)
        digest = compute_file_sha256(f"{import_source}-{uuid.uuid4()}".encode())
        with conn.transaction():
            batch = create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource(import_source),
                worksheet_name=None,
                file_sha256=digest,
                file_byte_size=100,
                staged_table=table,
            )
        rows = apply_mapping_to_rows(table, _MAPPING, snapshot_mode=False, file_sha256=digest)
        with conn.transaction():
            apply_import_batch_mapping(
                conn,
                batch_id=batch.batch_id,
                owner_organization_id=org_id,
                column_mapping=_MAPPING,
                snapshot_mode=False,
                rows=rows,
            )
        imported_rows = list_import_rows(conn, batch_id=batch.batch_id)
        # confirm_import_row requires an IDLE connection; the read-only
        # list_import_rows() select above leaves an implicit transaction
        # open, exactly like the application layer's own discipline.
        conn.commit()
        return batch, imported_rows

    def test_new_key_creates_draft(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        batch, rows = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "125000", "REF-1"),)
        )
        create_draft = _create_draft_closure(conn, org_id, account_id)
        result = confirm_import_row(
            conn,
            row=rows[0],
            owner_organization_id=org_id,
            import_source=batch.import_source,
            batch_id=batch.batch_id,
            create_draft=lambda: create_draft(rows[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )
        assert result.outcome is ImportRowOutcome.CREATE_NEW_DRAFT
        assert result.professional_listing_draft_id is not None

        mapping = fetch_import_source_mapping(
            conn,
            owner_organization_id=org_id,
            import_source=batch.import_source,
            source_record_key=SourceRecordKey("REF-1"),
        )
        assert mapping is not None
        assert mapping.professional_listing_draft_id == result.professional_listing_draft_id

    def test_exact_replay_is_already_imported_same_draft(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        batch, rows = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "125000", "REF-1"),)
        )
        create_draft = _create_draft_closure(conn, org_id, account_id)
        first = confirm_import_row(
            conn,
            row=rows[0],
            owner_organization_id=org_id,
            import_source=batch.import_source,
            batch_id=batch.batch_id,
            create_draft=lambda: create_draft(rows[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )
        assert first.outcome is ImportRowOutcome.CREATE_NEW_DRAFT

        # Re-confirming the *same already-outcome-stamped* row is the
        # idempotent-resume path and must not call create_draft again.
        resumed = confirm_import_row(
            conn,
            row=list_import_rows(conn, batch_id=batch.batch_id)[0],
            owner_organization_id=org_id,
            import_source=batch.import_source,
            batch_id=batch.batch_id,
            create_draft=lambda: (_ for _ in ()).throw(AssertionError("must not be called")),
            recheck_authorization=lambda: None,
        )
        assert resumed.outcome is ImportRowOutcome.CREATE_NEW_DRAFT
        assert resumed.professional_listing_draft_id == first.professional_listing_draft_id

    def test_second_batch_exact_same_mapped_payload_is_already_imported(self, conn: Any) -> None:
        """A genuinely new confirm attempt (fresh row, outcome not yet
        stamped) against an existing key with an unchanged digest ->
        ALREADY_IMPORTED, reusing the existing draft, zero new draft rows."""
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        batch1, rows1 = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "125000", "REF-1"),)
        )
        create_draft = _create_draft_closure(conn, org_id, account_id)
        first = confirm_import_row(
            conn,
            row=rows1[0],
            owner_organization_id=org_id,
            import_source=batch1.import_source,
            batch_id=batch1.batch_id,
            create_draft=lambda: create_draft(rows1[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )

        # Same ImportSource, same mapped payload, different batch (e.g. the
        # broker re-uploaded the identical export).
        batch2, rows2 = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "125000", "REF-1"),)
        )
        assert rows2[0].row_digest == rows1[0].row_digest
        second = confirm_import_row(
            conn,
            row=rows2[0],
            owner_organization_id=org_id,
            import_source=batch2.import_source,
            batch_id=batch2.batch_id,
            create_draft=lambda: (_ for _ in ()).throw(AssertionError("must not be called")),
            recheck_authorization=lambda: None,
        )
        assert second.outcome is ImportRowOutcome.ALREADY_IMPORTED
        assert second.professional_listing_draft_id == first.professional_listing_draft_id

    def test_changed_payload_same_key_is_conflict_review_never_overwrites(self, conn: Any) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        batch1, rows1 = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "125000", "REF-1"),)
        )
        create_draft = _create_draft_closure(conn, org_id, account_id)
        first = confirm_import_row(
            conn,
            row=rows1[0],
            owner_organization_id=org_id,
            import_source=batch1.import_source,
            batch_id=batch1.batch_id,
            create_draft=lambda: create_draft(rows1[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )
        assert first.outcome is ImportRowOutcome.CREATE_NEW_DRAFT

        # Same key, changed price -> different digest.
        batch2, rows2 = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "999999", "REF-1"),)
        )
        assert rows2[0].row_digest != rows1[0].row_digest
        second = confirm_import_row(
            conn,
            row=rows2[0],
            owner_organization_id=org_id,
            import_source=batch2.import_source,
            batch_id=batch2.batch_id,
            create_draft=lambda: (_ for _ in ()).throw(AssertionError("must not be called")),
            recheck_authorization=lambda: None,
        )
        assert second.outcome is ImportRowOutcome.CONFLICT_REVIEW
        assert second.professional_listing_draft_id is None

        mapping = fetch_import_source_mapping(
            conn,
            owner_organization_id=org_id,
            import_source=batch1.import_source,
            source_record_key=SourceRecordKey("REF-1"),
        )
        assert mapping is not None
        assert mapping.professional_listing_draft_id == first.professional_listing_draft_id
        assert mapping.row_digest == rows1[0].row_digest

    def test_two_distinct_organizations_same_source_key_do_not_collide(self, conn: Any) -> None:
        org_a = MarketplaceOrganizationId(str(uuid.uuid4()))
        org_b = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_a)
        _seed_organization(conn, org_b)
        _seed_account(conn, account_id)

        batch_a, rows_a = self._mapped_batch_and_rows(
            conn, org_a, account_id, "SharedFeedName", (("Aria", "1998", "125000", "REF-1"),)
        )
        batch_b, rows_b = self._mapped_batch_and_rows(
            conn, org_b, account_id, "SharedFeedName", (("Aria", "1998", "125000", "REF-1"),)
        )
        create_draft_a = _create_draft_closure(conn, org_a, account_id)
        create_draft_b = _create_draft_closure(conn, org_b, account_id)

        result_a = confirm_import_row(
            conn,
            row=rows_a[0],
            owner_organization_id=org_a,
            import_source=batch_a.import_source,
            batch_id=batch_a.batch_id,
            create_draft=lambda: create_draft_a(rows_a[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )
        result_b = confirm_import_row(
            conn,
            row=rows_b[0],
            owner_organization_id=org_b,
            import_source=batch_b.import_source,
            batch_id=batch_b.batch_id,
            create_draft=lambda: create_draft_b(rows_b[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )
        assert result_a.outcome is ImportRowOutcome.CREATE_NEW_DRAFT
        assert result_b.outcome is ImportRowOutcome.CREATE_NEW_DRAFT
        assert result_a.professional_listing_draft_id != result_b.professional_listing_draft_id

    def test_concurrent_first_confirm_same_key_only_one_draft_created(
        self, conn: Any, import_url: str
    ) -> None:
        """Simulates the real race `confirm_import_row` defends against: a
        second connection commits an insert into `import_source_mappings`
        for the exact same key between this connection's `FOR UPDATE`
        lookup (sees nothing) and its own insert attempt -- proven via a
        real `UniqueViolation`, not a mocked outcome."""
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        _seed_organization(conn, org_id)
        _seed_account(conn, account_id)
        batch, rows = self._mapped_batch_and_rows(
            conn, org_id, account_id, "Feed1", (("Aria", "1998", "125000", "REF-1"),)
        )

        # A second, independent connection wins the race first and commits
        # a mapping row + its own draft for the identical key.
        other_conn = psycopg.connect(import_url)
        try:
            other_create_draft = _create_draft_closure(other_conn, org_id, account_id)
            winner_draft_id = other_create_draft(rows[0].draft_request_wire)
            with other_conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO import_source_mappings "
                    "(owner_organization_id, import_source, source_record_key, row_digest, "
                    " professional_listing_draft_id, created_by_import_batch_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    [
                        org_id.value,
                        batch.import_source.value,
                        "REF-1",
                        rows[0].row_digest,
                        winner_draft_id.value,
                        batch.batch_id.value,
                    ],
                )
            other_conn.commit()
        finally:
            other_conn.close()

        create_draft = _create_draft_closure(conn, org_id, account_id)
        result = confirm_import_row(
            conn,
            row=rows[0],
            owner_organization_id=org_id,
            import_source=batch.import_source,
            batch_id=batch.batch_id,
            create_draft=lambda: create_draft(rows[0].draft_request_wire),
            recheck_authorization=lambda: None,
        )
        # This connection lost the race: it must report the winner's draft
        # (same digest -> ALREADY_IMPORTED), never create a second one.
        assert result.outcome is ImportRowOutcome.ALREADY_IMPORTED
        assert result.professional_listing_draft_id == winner_draft_id

        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM professional_listing_drafts WHERE owner_organization_id = %s",
                [org_id.value],
            )
            (count,) = cur.fetchone()
        assert count == 1


def _wait_until_blocked_on_lock(monitor_conn: Any, pid: int, *, timeout: float = 10.0) -> bool:
    """Poll `pg_locks` on a dedicated connection until *pid* is genuinely
    waiting (not granted) on a lock -- never a fixed sleep guessing at
    scheduling, mirroring
    `test_boat_design_association_persistence.py`'s identical SLICE-0082
    Finding A proof technique."""
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


def _backend_pid(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        pid = int(cur.fetchone()[0])
    conn.commit()
    return pid


class TestConcurrentSnapshotLineage:
    def test_two_concurrent_different_digest_snapshot_claims_exactly_one_wins(
        self, import_url: str
    ) -> None:
        """Independent review amendment Finding B: two genuinely concurrent
        first-time snapshot-lineage claims for the same Organization/
        ImportSource with *different* file digests contend for the real
        `(owner_organization_id, import_source)` primary key under actual
        PostgreSQL lock contention (confirmed via `pg_locks`, never a
        timing guess) -- exactly one may durably become the lineage;
        the other is deterministically told it conflicts.
        """
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        conn0 = psycopg.connect(import_url)
        try:
            with conn0.cursor() as cur:
                cur.execute(
                    "INSERT INTO marketplace_organizations "
                    "(organization_id, professional_category, publishing_eligibility, "
                    " public_display_name) VALUES (%s, %s, %s, %s)",
                    [org_id.value, "BROKER", "ELIGIBLE", org_id.value],
                )
                cur.execute("INSERT INTO accounts (account_id) VALUES (%s)", [account_id.value])
            conn0.commit()

            table = ParsedTable(headers=("a",), rows=(("1",),))
            batch_a = create_import_batch_awaiting_mapping(
                conn0,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("ConcurrentSnap"),
                worksheet_name=None,
                file_sha256=compute_file_sha256(b"digest-a-payload"),
                file_byte_size=10,
                staged_table=table,
            )
            conn0.commit()
            batch_b = create_import_batch_awaiting_mapping(
                conn0,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("ConcurrentSnap"),
                worksheet_name=None,
                file_sha256=compute_file_sha256(b"digest-b-payload"),
                file_byte_size=10,
                staged_table=table,
            )
            conn0.commit()
        finally:
            conn0.close()

        digest_a = compute_file_sha256(b"digest-a-payload")
        digest_b = compute_file_sha256(b"digest-b-payload")

        conn_a = psycopg.connect(import_url)
        conn_b = psycopg.connect(import_url)
        monitor_conn = psycopg.connect(import_url)
        conn_b_pid = _backend_pid(conn_b)

        errors: list[BaseException] = []
        results: dict[str, bool] = {}
        a_inserted = threading.Event()

        def _claim_a_then_delay_commit() -> None:
            try:
                with conn_a.transaction():
                    conflict = claim_or_check_snapshot_lineage(
                        conn_a,
                        owner_organization_id=org_id,
                        import_source=ImportSource("ConcurrentSnap"),
                        file_sha256=digest_a,
                        batch_id=batch_a.batch_id,
                    )
                    results["a"] = conflict
                    a_inserted.set()
                    blocked = _wait_until_blocked_on_lock(monitor_conn, conn_b_pid)
                    assert blocked, "conn_b never blocked on conn_a's uncommitted lineage insert"
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        def _claim_b_concurrently() -> None:
            try:
                a_inserted.wait(timeout=10)
                with conn_b.transaction():
                    conflict = claim_or_check_snapshot_lineage(
                        conn_b,
                        owner_organization_id=org_id,
                        import_source=ImportSource("ConcurrentSnap"),
                        file_sha256=digest_b,
                        batch_id=batch_b.batch_id,
                    )
                    results["b"] = conflict
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        threads = [
            threading.Thread(target=_claim_a_then_delay_commit),
            threading.Thread(target=_claim_b_concurrently),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        conn_a.close()
        conn_b.close()
        monitor_conn.close()

        assert not errors, f"Thread errors: {errors}"
        # `a` established the lineage first (no conflict); `b`, blocked
        # behind `a`'s uncommitted insert and only unblocked once `a`
        # committed, must see the real winning digest and report conflict.
        assert results["a"] is False
        assert results["b"] is True

        verify_conn = psycopg.connect(import_url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT file_sha256 FROM import_snapshot_lineages "
                    "WHERE owner_organization_id = %s AND import_source = %s",
                    [org_id.value, "ConcurrentSnap"],
                )
                rows = cur.fetchall()
        finally:
            verify_conn.close()
        assert len(rows) == 1
        assert rows[0][0] == digest_a


class TestConcurrentPendingBatchAdmission:
    def test_two_concurrent_uploads_at_the_limit_exactly_one_is_admitted(
        self, import_url: str
    ) -> None:
        """Independent review amendment Finding 3: the prior separate
        count-then-insert allowed two concurrent uploads for the same
        Organization, both already at MAX_PENDING_BATCHES_PER_ORGANIZATION
        - 1, to each observe a count below the limit before either had
        inserted its new batch row -- exceeding the limit. Proven here
        under genuine PostgreSQL lock contention (confirmed via
        `pg_locks`, never a timing guess): connection A holds the real
        `pg_advisory_xact_lock` admission lock mid-transaction while
        connection B is shown to be genuinely blocked on it; only once A
        commits does B proceed, see the now-at-limit count, and
        correctly decline to insert a 21st batch."""
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        table = ParsedTable(headers=("a",), rows=(("1",),))
        conn0 = psycopg.connect(import_url)
        try:
            _seed_organization(conn0, org_id)
            _seed_account(conn0, account_id)
            for i in range(MAX_PENDING_BATCHES_PER_ORGANIZATION - 1):
                create_import_batch_awaiting_mapping(
                    conn0,
                    owner_organization_id=org_id,
                    created_by_account_id=account_id,
                    import_format=ImportFormat.CSV,
                    import_source=ImportSource(f"PreexistingFeed{i}"),
                    worksheet_name=None,
                    file_sha256=compute_file_sha256(f"pre-{i}".encode()),
                    file_byte_size=10,
                    staged_table=table,
                )
                conn0.commit()
        finally:
            conn0.close()

        conn_a = psycopg.connect(import_url)
        conn_b = psycopg.connect(import_url)
        monitor_conn = psycopg.connect(import_url)
        conn_b_pid = _backend_pid(conn_b)

        errors: list[BaseException] = []
        results: dict[str, str] = {}
        a_locked = threading.Event()

        def _admit(conn: Any, source: str, digest_payload: bytes) -> str:
            lock_organization_import_batch_admission(conn, owner_organization_id=org_id)
            count = count_pending_batches_for_organization(conn, owner_organization_id=org_id)
            if count >= MAX_PENDING_BATCHES_PER_ORGANIZATION:
                return "rejected"
            create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource(source),
                worksheet_name=None,
                file_sha256=compute_file_sha256(digest_payload),
                file_byte_size=10,
                staged_table=table,
            )
            return "admitted"

        def _admit_a_then_delay_commit() -> None:
            try:
                with conn_a.transaction():
                    results["a"] = _admit(conn_a, "RaceFeedA", b"race-a")
                    a_locked.set()
                    blocked = _wait_until_blocked_on_lock(monitor_conn, conn_b_pid)
                    assert blocked, "conn_b never blocked on conn_a's held admission lock"
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        def _admit_b_concurrently() -> None:
            try:
                a_locked.wait(timeout=10)
                with conn_b.transaction():
                    results["b"] = _admit(conn_b, "RaceFeedB", b"race-b")
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        threads = [
            threading.Thread(target=_admit_a_then_delay_commit),
            threading.Thread(target=_admit_b_concurrently),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        conn_a.close()
        conn_b.close()
        monitor_conn.close()

        assert not errors, f"Thread errors: {errors}"
        # A, already holding the lock while at exactly MAX - 1, is
        # admitted. B, genuinely blocked behind A's uncommitted insert and
        # only unblocked once A committed, must see the now-at-limit count
        # and decline -- never exceeding the bound.
        assert results["a"] == "admitted"
        assert results["b"] == "rejected"

        verify_conn = psycopg.connect(import_url)
        try:
            final_count = count_pending_batches_for_organization(
                verify_conn, owner_organization_id=org_id
            )
        finally:
            verify_conn.close()
        assert final_count == MAX_PENDING_BATCHES_PER_ORGANIZATION


class TestGlobalExpiredBatchPurgeIndependentOfUpload:
    """Independent review amendment Finding 3: the real 24-hour retention
    guarantee must not depend on the owning Organization ever uploading
    again. `purge_all_expired_unconfirmed_batches` -- the function
    `scripts/ops/purge_expired_import_batches.py` runs as a standalone
    scheduled sweep -- is exercised here directly against real
    PostgreSQL with zero further activity from the batch's Organization
    at all (no second upload, no list, no view)."""

    def test_expired_idle_batch_is_purged_with_no_further_activity_from_its_organization(
        self, import_url: str
    ) -> None:
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        conn = psycopg.connect(import_url)
        try:
            _seed_organization(conn, org_id)
            _seed_account(conn, account_id)
            table = ParsedTable(headers=("a",), rows=(("1",),))
            batch = create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("IdleFeed"),
                worksheet_name=None,
                file_sha256=compute_file_sha256(b"idle-payload"),
                file_byte_size=10,
                staged_table=table,
            )
            conn.commit()

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE import_batches SET expires_at = NOW() - INTERVAL '1 hour' "
                    "WHERE import_batch_id = %s",
                    [batch.batch_id.value],
                )
            conn.commit()

            with conn.transaction():
                purged = purge_all_expired_unconfirmed_batches(conn)
            assert purged >= 1

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM import_batches WHERE import_batch_id = %s",
                    [batch.batch_id.value],
                )
                (remaining_batches,) = cur.fetchone()
                cur.execute(
                    "SELECT count(*) FROM import_rows WHERE import_batch_id = %s",
                    [batch.batch_id.value],
                )
                (remaining_rows,) = cur.fetchone()
            conn.commit()
            assert remaining_batches == 0
            assert remaining_rows == 0
        finally:
            conn.close()

    def test_confirming_batch_is_never_purged_by_the_global_sweep_even_once_expired(
        self, import_url: str
    ) -> None:
        """A `CONFIRMING` batch may hold real committed drafts/mappings
        from a crashed/interrupted confirm call -- the global sweep must
        never delete it, identical to the per-Organization fast path's
        own rule."""
        org_id = MarketplaceOrganizationId(str(uuid.uuid4()))
        account_id = AccountId(str(uuid.uuid4()))
        conn = psycopg.connect(import_url)
        try:
            _seed_organization(conn, org_id)
            _seed_account(conn, account_id)
            table = ParsedTable(headers=("a",), rows=(("1",),))
            batch = create_import_batch_awaiting_mapping(
                conn,
                owner_organization_id=org_id,
                created_by_account_id=account_id,
                import_format=ImportFormat.CSV,
                import_source=ImportSource("StuckFeed"),
                worksheet_name=None,
                file_sha256=compute_file_sha256(b"stuck-payload"),
                file_byte_size=10,
                staged_table=table,
            )
            conn.commit()

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE import_batches SET status = 'CONFIRMING', "
                    "expires_at = NOW() - INTERVAL '1 hour' WHERE import_batch_id = %s",
                    [batch.batch_id.value],
                )
            conn.commit()

            with conn.transaction():
                purge_all_expired_unconfirmed_batches(conn)

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM import_batches WHERE import_batch_id = %s",
                    [batch.batch_id.value],
                )
                (remaining,) = cur.fetchone()
            conn.commit()
            assert remaining == 1
        finally:
            conn.close()
