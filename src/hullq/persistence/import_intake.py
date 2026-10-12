"""Multi-format broker inventory import intake persistence — SLICE-0083.

Durable `ImportBatch`/`ImportRow`/`(Organization, ImportSource,
SourceRecordKey)` state (D26,
`docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`), scoped
server-side to `owner_organization_id` on every query -- mirroring
`hullq.persistence.professional_listing_draft`'s identical discipline.

`confirm_import_row` is the one atomic per-row identity-mapping primitive
(mechanical invariants: "Use durable unique Organization/source/sourcekey
constraints, safe transactional reservation/CAS/row locks and per-row
atomicity"). Each call owns and commits exactly one dedicated transaction
for exactly one row: a whole batch confirm is therefore a sequence of
independently committing row transactions, never one giant all-or-nothing
transaction -- a crash/restart mid-batch leaves every already-processed
row durably `CREATE_NEW_DRAFT`/`ALREADY_IMPORTED`/`CONFLICT_REVIEW`/
`INVALID` and every not-yet-processed row still `outcome IS NULL`, so a
retried confirm call simply resumes at the first unprocessed row (contract
"Partial success is truthful and safe to resume").

The `import_source_mappings` composite primary key
`(owner_organization_id, import_source, source_record_key)` is the actual
concurrency-safety mechanism for two simultaneous first-time confirms of
the same new key: both attempt the insert, the database allows exactly
one to succeed, and the loser's `UniqueViolation` is caught and
reinterpreted as "someone else just won this key" -- re-read the now
committed row and classify `ALREADY_IMPORTED`/`CONFLICT_REVIEW` from it,
exactly like an ordinary pre-existing-key confirm. This is the same
catch-the-constraint-violation discipline
`hullq.persistence.boat_design_association.associate_physical_boat_design_for_listing`
uses for `DESIGN_NOT_FOUND`.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.import_intake import (
    ImportBatchId,
    ImportFormat,
    ImportRowId,
    ImportRowOutcome,
    ImportSource,
    ParsedTable,
    RowPreviewClassification,
    SourceRecordKey,
    StagedRowPreview,
)
from hullq.domain.professional_listing_draft import ProfessionalListingDraftId
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "ApplyMappingOutcome",
    "ImportBatchRecord",
    "ImportBatchStatus",
    "ImportRowConfirmResult",
    "ImportRowRecord",
    "ImportSourceMappingRecord",
    "apply_import_batch_mapping",
    "confirm_import_row",
    "create_import_batch_awaiting_mapping",
    "create_import_batch_mapped",
    "fetch_import_batch",
    "fetch_import_source_mapping",
    "finalize_row_outcome_only",
    "has_confirmed_snapshot_batch_with_different_digest",
    "list_import_rows",
    "list_recent_import_batches",
    "mark_batch_confirmed",
    "mark_batch_confirming",
]


class ImportBatchStatus(StrEnum):
    AWAITING_MAPPING = "AWAITING_MAPPING"
    MAPPED = "MAPPED"
    CONFIRMING = "CONFIRMING"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ImportBatchRecord:
    batch_id: ImportBatchId
    owner_organization_id: MarketplaceOrganizationId
    created_by_account_id: AccountId
    import_format: ImportFormat
    import_source: ImportSource
    worksheet_name: str | None
    snapshot_mode: bool
    file_sha256: str
    file_byte_size: int
    column_mapping: dict[str, str] | None
    staged_table: ParsedTable | None
    status: ImportBatchStatus
    row_count: int
    created_at: datetime
    mapped_at: datetime | None
    confirmed_at: datetime | None
    expires_at: datetime


@dataclass(frozen=True)
class ImportRowRecord:
    row_id: ImportRowId
    batch_id: ImportBatchId
    row_ordinal: int
    raw_fields: dict[str, str | None]
    unmapped_headers: tuple[str, ...]
    preview_classification: RowPreviewClassification
    preview_reasons: tuple[str, ...]
    source_record_key: SourceRecordKey | None
    draft_request_wire: dict[str, Any] | None
    row_digest: str | None
    outcome: ImportRowOutcome | None
    created_professional_listing_draft_id: ProfessionalListingDraftId | None
    confirmed_at: datetime | None


@dataclass(frozen=True)
class ImportSourceMappingRecord:
    owner_organization_id: MarketplaceOrganizationId
    import_source: ImportSource
    source_record_key: SourceRecordKey
    row_digest: str
    professional_listing_draft_id: ProfessionalListingDraftId
    created_by_import_batch_id: ImportBatchId
    created_at: datetime


_BATCH_COLUMNS = (
    "import_batch_id, owner_organization_id, created_by_account_id, import_format, "
    "import_source, worksheet_name, snapshot_mode, file_sha256, file_byte_size, "
    "column_mapping, staged_table, status, row_count, created_at, mapped_at, confirmed_at, "
    "expires_at"
)

_INSERT_BATCH = f"""
INSERT INTO import_batches
    (import_batch_id, owner_organization_id, created_by_account_id, import_format,
     import_source, worksheet_name, snapshot_mode, file_sha256, file_byte_size,
     column_mapping, staged_table, status, row_count, expires_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, NOW() + INTERVAL '24 hours')
RETURNING {_BATCH_COLUMNS}
"""

_SELECT_BATCH_FOR_ORG = f"SELECT {_BATCH_COLUMNS} FROM import_batches WHERE import_batch_id = %s AND owner_organization_id = %s"

_SELECT_BATCH_FOR_UPDATE = f"{_SELECT_BATCH_FOR_ORG} FOR UPDATE"

_SELECT_RECENT_BATCHES = (
    f"SELECT {_BATCH_COLUMNS} FROM import_batches WHERE owner_organization_id = %s "
    "ORDER BY created_at DESC, import_batch_id ASC LIMIT %s"
)

_UPDATE_BATCH_MAPPED = """
UPDATE import_batches
SET column_mapping = %s::jsonb, snapshot_mode = %s, staged_table = NULL,
    status = 'MAPPED', row_count = %s, mapped_at = NOW()
WHERE import_batch_id = %s AND owner_organization_id = %s AND status = 'AWAITING_MAPPING'
RETURNING mapped_at
"""

_INSERT_ROW = """
INSERT INTO import_rows
    (import_row_id, import_batch_id, row_ordinal, raw_fields, unmapped_headers,
     preview_classification, preview_reasons, source_record_key, draft_request_wire, row_digest)
VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s)
"""

_ROW_COLUMNS = (
    "import_row_id, import_batch_id, row_ordinal, raw_fields, unmapped_headers, "
    "preview_classification, preview_reasons, source_record_key, draft_request_wire, "
    "row_digest, outcome, created_professional_listing_draft_id, confirmed_at"
)

_SELECT_ROWS_FOR_BATCH = (
    f"SELECT {_ROW_COLUMNS} FROM import_rows WHERE import_batch_id = %s ORDER BY row_ordinal ASC"
)

_SELECT_ROW_FOR_UPDATE = (
    f"SELECT {_ROW_COLUMNS} FROM import_rows WHERE import_row_id = %s AND import_batch_id = %s "
    "FOR UPDATE"
)

_MARK_ROW_OUTCOME = """
UPDATE import_rows
SET outcome = %s, created_professional_listing_draft_id = %s, confirmed_at = NOW()
WHERE import_row_id = %s
"""

_MAPPING_COLUMNS = (
    "owner_organization_id, import_source, source_record_key, row_digest, "
    "professional_listing_draft_id, created_by_import_batch_id, created_at"
)

_SELECT_MAPPING_FOR_UPDATE = (
    f"SELECT {_MAPPING_COLUMNS} FROM import_source_mappings "
    "WHERE owner_organization_id = %s AND import_source = %s AND source_record_key = %s FOR UPDATE"
)

_INSERT_MAPPING = """
INSERT INTO import_source_mappings
    (owner_organization_id, import_source, source_record_key, row_digest,
     professional_listing_draft_id, created_by_import_batch_id)
VALUES (%s, %s, %s, %s, %s, %s)
"""


def _row_to_batch(row: tuple[Any, ...]) -> ImportBatchRecord:
    (
        batch_id,
        owner_organization_id,
        created_by_account_id,
        import_format,
        import_source,
        worksheet_name,
        snapshot_mode,
        file_sha256,
        file_byte_size,
        column_mapping,
        staged_table,
        status,
        row_count,
        created_at,
        mapped_at,
        confirmed_at,
        expires_at,
    ) = row
    parsed_table: ParsedTable | None = None
    if staged_table is not None:
        parsed_table = ParsedTable(
            headers=tuple(staged_table["headers"]),
            rows=tuple(tuple(r) for r in staged_table["rows"]),
        )
    return ImportBatchRecord(
        batch_id=ImportBatchId(batch_id),
        owner_organization_id=MarketplaceOrganizationId(owner_organization_id),
        created_by_account_id=AccountId(created_by_account_id),
        import_format=ImportFormat(import_format),
        import_source=ImportSource(import_source),
        worksheet_name=worksheet_name,
        snapshot_mode=snapshot_mode,
        file_sha256=file_sha256,
        file_byte_size=file_byte_size,
        column_mapping=column_mapping,
        staged_table=parsed_table,
        status=ImportBatchStatus(status),
        row_count=row_count,
        created_at=created_at,
        mapped_at=mapped_at,
        confirmed_at=confirmed_at,
        expires_at=expires_at,
    )


def _row_to_import_row(row: tuple[Any, ...]) -> ImportRowRecord:
    (
        row_id,
        batch_id,
        row_ordinal,
        raw_fields,
        unmapped_headers,
        preview_classification,
        preview_reasons,
        source_record_key,
        draft_request_wire,
        row_digest,
        outcome,
        created_draft_id,
        confirmed_at,
    ) = row
    return ImportRowRecord(
        row_id=ImportRowId(row_id),
        batch_id=ImportBatchId(batch_id),
        row_ordinal=row_ordinal,
        raw_fields=raw_fields,
        unmapped_headers=tuple(unmapped_headers),
        preview_classification=RowPreviewClassification(preview_classification),
        preview_reasons=tuple(preview_reasons),
        source_record_key=SourceRecordKey(source_record_key)
        if source_record_key is not None
        else None,
        draft_request_wire=draft_request_wire,
        row_digest=row_digest,
        outcome=ImportRowOutcome(outcome) if outcome is not None else None,
        created_professional_listing_draft_id=ProfessionalListingDraftId(created_draft_id)
        if created_draft_id is not None
        else None,
        confirmed_at=confirmed_at,
    )


def _insert_rows(cur: Any, batch_id: ImportBatchId, rows: tuple[StagedRowPreview, ...]) -> None:
    for preview in rows:
        cur.execute(
            _INSERT_ROW,
            [
                str(uuid.uuid4()),
                batch_id.value,
                preview.row_ordinal,
                json.dumps(preview.raw_fields),
                json.dumps(list(preview.unmapped_headers)),
                preview.classification.value,
                json.dumps(list(preview.reasons)),
                preview.source_record_key.value if preview.source_record_key is not None else None,
                json.dumps(preview.draft_request_wire)
                if preview.draft_request_wire is not None
                else None,
                preview.row_digest,
            ],
        )


def create_import_batch_awaiting_mapping(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    created_by_account_id: AccountId,
    import_format: ImportFormat,
    import_source: ImportSource,
    worksheet_name: str | None,
    file_sha256: str,
    file_byte_size: int,
    staged_table: ParsedTable,
) -> ImportBatchRecord:
    """Durably create one new batch in `AWAITING_MAPPING`, holding the
    bounded parsed table until the broker explicitly sets the column
    mapping. The caller owns transaction commit."""
    batch_id = ImportBatchId(str(uuid.uuid4()))
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_BATCH,
            [
                batch_id.value,
                owner_organization_id.value,
                created_by_account_id.value,
                import_format.value,
                import_source.value,
                worksheet_name,
                False,
                file_sha256,
                file_byte_size,
                None,
                json.dumps(
                    {
                        "headers": list(staged_table.headers),
                        "rows": [list(r) for r in staged_table.rows],
                    }
                ),
                ImportBatchStatus.AWAITING_MAPPING.value,
                len(staged_table.rows),
            ],
        )
        row = cur.fetchone()
    assert row is not None
    return _row_to_batch(row)


def create_import_batch_mapped(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    created_by_account_id: AccountId,
    import_format: ImportFormat,
    import_source: ImportSource,
    file_sha256: str,
    file_byte_size: int,
    snapshot_mode: bool,
    rows: tuple[StagedRowPreview, ...],
) -> ImportBatchRecord:
    """Durably create one new batch already fully staged/classified in one
    step (NautiX: no manual column-mapping phase). The caller owns
    transaction commit."""
    batch_id = ImportBatchId(str(uuid.uuid4()))
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_BATCH,
            [
                batch_id.value,
                owner_organization_id.value,
                created_by_account_id.value,
                import_format.value,
                import_source.value,
                None,
                snapshot_mode,
                file_sha256,
                file_byte_size,
                None,
                None,
                ImportBatchStatus.MAPPED.value,
                len(rows),
            ],
        )
        row = cur.fetchone()
        assert row is not None
        _insert_rows(cur, batch_id, rows)
    return _row_to_batch(row)


class ApplyMappingOutcome(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    WRONG_STATE = "WRONG_STATE"
    OK = "OK"


def apply_import_batch_mapping(
    conn: Any,
    *,
    batch_id: ImportBatchId,
    owner_organization_id: MarketplaceOrganizationId,
    column_mapping: dict[str, str],
    snapshot_mode: bool,
    rows: tuple[StagedRowPreview, ...],
) -> ApplyMappingOutcome:
    """Atomically transition one batch from `AWAITING_MAPPING` to
    `MAPPED`, materializing *rows*. A batch not currently in
    `AWAITING_MAPPING` (including a foreign/unknown batch_id, both
    `NOT_FOUND`) writes zero rows. The caller owns transaction commit."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_BATCH_FOR_UPDATE, [batch_id.value, owner_organization_id.value])
        existing = cur.fetchone()
        if existing is None:
            return ApplyMappingOutcome.NOT_FOUND
        if ImportBatchStatus(existing[11]) is not ImportBatchStatus.AWAITING_MAPPING:
            return ApplyMappingOutcome.WRONG_STATE

        cur.execute(
            _UPDATE_BATCH_MAPPED,
            [
                json.dumps(column_mapping),
                snapshot_mode,
                len(rows),
                batch_id.value,
                owner_organization_id.value,
            ],
        )
        updated = cur.fetchone()
        if updated is None:
            return ApplyMappingOutcome.WRONG_STATE
        _insert_rows(cur, batch_id, rows)
    return ApplyMappingOutcome.OK


def fetch_import_batch(
    conn: Any, *, batch_id: ImportBatchId, owner_organization_id: MarketplaceOrganizationId
) -> ImportBatchRecord | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT_BATCH_FOR_ORG, [batch_id.value, owner_organization_id.value])
        row = cur.fetchone()
    return _row_to_batch(row) if row is not None else None


def list_recent_import_batches(
    conn: Any, *, owner_organization_id: MarketplaceOrganizationId, limit: int = 20
) -> tuple[ImportBatchRecord, ...]:
    bounded_limit = min(max(limit, 1), 100)
    with conn.cursor() as cur:
        cur.execute(_SELECT_RECENT_BATCHES, [owner_organization_id.value, bounded_limit])
        rows = cur.fetchall()
    return tuple(_row_to_batch(row) for row in rows)


def list_import_rows(conn: Any, *, batch_id: ImportBatchId) -> tuple[ImportRowRecord, ...]:
    with conn.cursor() as cur:
        cur.execute(_SELECT_ROWS_FOR_BATCH, [batch_id.value])
        rows = cur.fetchall()
    return tuple(_row_to_import_row(row) for row in rows)


def has_confirmed_snapshot_batch_with_different_digest(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    import_source: ImportSource,
    file_sha256: str,
) -> bool:
    """`True` iff this Organization/ImportSource already has at least one
    *other*, previously `CONFIRMED` one-time-snapshot batch whose exact
    uploaded-file digest differs from *file_sha256* (mechanical invariants/
    Required Behavior #4: "a further changed upload for the same
    Organization/ImportSource must be classified for explicit
    CONFLICT_REVIEW").

    Snapshot keys are namespaced by their own file digest
    (`SNAPSHOT:<digest>:<ordinal>`), so a changed file's rows never
    collide at the `import_source_mappings` primary-key level the way a
    stable-ID column's rows do -- this batch/source-level lineage check is
    what actually enforces "no silent duplicate drafts" for snapshot mode,
    one layer above the per-row identity-mapping primitive.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM import_batches "
            "WHERE owner_organization_id = %s AND import_source = %s AND snapshot_mode = TRUE "
            "AND status = 'CONFIRMED' AND file_sha256 != %s LIMIT 1",
            [owner_organization_id.value, import_source.value, file_sha256],
        )
        return cur.fetchone() is not None


def mark_batch_confirming(conn: Any, *, batch_id: ImportBatchId) -> None:
    """Idempotent observability-only status marker: a no-op once the batch
    has already moved past `MAPPED`. The caller owns transaction commit."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE import_batches SET status = 'CONFIRMING' "
            "WHERE import_batch_id = %s AND status = 'MAPPED'",
            [batch_id.value],
        )


def mark_batch_confirmed(conn: Any, *, batch_id: ImportBatchId) -> None:
    """Idempotent: a no-op once the batch is already `CONFIRMED`. The
    caller owns transaction commit."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE import_batches SET status = 'CONFIRMED', confirmed_at = NOW() "
            "WHERE import_batch_id = %s AND status IN ('MAPPED', 'CONFIRMING')",
            [batch_id.value],
        )


def finalize_row_outcome_only(conn: Any, *, row_id: ImportRowId, outcome: ImportRowOutcome) -> None:
    """Stamp a domain-decided (non-identity-mapping) outcome --
    `INVALID`/`CONFLICT_REVIEW` carried straight through from
    `RowPreviewClassification` -- onto exactly one row. Idempotent: a
    no-op once `outcome` is already set (Required Behavior: "retry after
    lost response"). The caller owns transaction commit."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE import_rows SET outcome = %s, confirmed_at = NOW() "
            "WHERE import_row_id = %s AND outcome IS NULL",
            [outcome.value, row_id.value],
        )


def fetch_import_source_mapping(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    import_source: ImportSource,
    source_record_key: SourceRecordKey,
) -> ImportSourceMappingRecord | None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_MAPPING_COLUMNS} FROM import_source_mappings "
            "WHERE owner_organization_id = %s AND import_source = %s AND source_record_key = %s",
            [owner_organization_id.value, import_source.value, source_record_key.value],
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _mapping_row_to_record(row)


def _mapping_row_to_record(row: tuple[Any, ...]) -> ImportSourceMappingRecord:
    (
        owner_organization_id,
        import_source,
        source_record_key,
        row_digest,
        professional_listing_draft_id,
        created_by_import_batch_id,
        created_at,
    ) = row
    return ImportSourceMappingRecord(
        owner_organization_id=MarketplaceOrganizationId(owner_organization_id),
        import_source=ImportSource(import_source),
        source_record_key=SourceRecordKey(source_record_key),
        row_digest=row_digest,
        professional_listing_draft_id=ProfessionalListingDraftId(professional_listing_draft_id),
        created_by_import_batch_id=ImportBatchId(created_by_import_batch_id),
        created_at=created_at,
    )


@dataclass(frozen=True)
class ImportRowConfirmResult:
    row_id: ImportRowId
    outcome: ImportRowOutcome
    professional_listing_draft_id: ProfessionalListingDraftId | None = None

    def __post_init__(self) -> None:
        carries_draft = self.outcome in (
            ImportRowOutcome.CREATE_NEW_DRAFT,
            ImportRowOutcome.ALREADY_IMPORTED,
        )
        if carries_draft and self.professional_listing_draft_id is None:
            raise ValueError(f"A {self.outcome.value} result must carry a draft id")
        if not carries_draft and self.professional_listing_draft_id is not None:
            raise ValueError(f"A {self.outcome.value} result must not carry a draft id")


class ImportRowTransactionOwnershipError(RuntimeError):
    """Mirrors every other identity-write module's identical guard: *conn*
    must be `IDLE` so a committed result is unconditionally durable."""


def confirm_import_row(
    conn: Any,
    *,
    row: ImportRowRecord,
    owner_organization_id: MarketplaceOrganizationId,
    import_source: ImportSource,
    batch_id: ImportBatchId,
    create_draft: Any,
) -> ImportRowConfirmResult:
    """Resolve and durably commit exactly one row's final D26 outcome, in
    one dedicated transaction.

    *row* must have `preview_classification is VALID` (callers must map an
    `INVALID`/`CONFLICT_REVIEW` `RowPreviewClassification` straight to the
    identically-named `ImportRowOutcome` without calling this function at
    all -- there is no mapping/source-identity work to do for those).

    *create_draft* is a zero-argument callable the caller supplies, which
    performs the actual `hullq.persistence.professional_listing_draft.
    create_professional_listing_draft` call using this same *conn*/
    transaction and returns the new `ProfessionalListingDraftId` -- kept as
    an injected callable so this module never imports the draft payload
    parsing it would otherwise need to reconstruct a `ListingDraftPayload`
    from `row.draft_request_wire`.

    Idempotent/resumable: if *row* already carries a non-`None` `outcome`,
    it is returned unchanged with zero further mutation (Required
    Behavior: "retry after lost response"). This is checked twice: once
    against the caller-supplied *row* (cheap, avoids opening a transaction
    at all for the common already-confirmed-resume case), and again
    against a fresh `FOR UPDATE`-locked re-read once the transaction is
    open -- closing the TOCTOU window a second concurrent confirm of this
    exact row could otherwise race through between those two points.
    """
    if row.outcome is not None:
        return ImportRowConfirmResult(
            row_id=row.row_id,
            outcome=row.outcome,
            professional_listing_draft_id=row.created_professional_listing_draft_id,
        )

    from psycopg.errors import UniqueViolation  # deferred: no module-level psycopg dependency
    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise ImportRowTransactionOwnershipError(
            "conn already has an open transaction; confirm_import_row() requires an IDLE "
            "connection so it can safely own and commit its own per-row transaction."
        )

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_SELECT_ROW_FOR_UPDATE, [row.row_id.value, batch_id.value])
        locked = cur.fetchone()
        assert locked is not None
        row = _row_to_import_row(locked)
        if row.outcome is not None:
            return ImportRowConfirmResult(
                row_id=row.row_id,
                outcome=row.outcome,
                professional_listing_draft_id=row.created_professional_listing_draft_id,
            )
        assert row.preview_classification is RowPreviewClassification.VALID
        assert row.source_record_key is not None
        assert row.row_digest is not None

        cur.execute(
            _SELECT_MAPPING_FOR_UPDATE,
            [owner_organization_id.value, import_source.value, row.source_record_key.value],
        )
        existing = cur.fetchone()
        if existing is not None:
            mapping = _mapping_row_to_record(existing)
            outcome = (
                ImportRowOutcome.ALREADY_IMPORTED
                if mapping.row_digest == row.row_digest
                else ImportRowOutcome.CONFLICT_REVIEW
            )
            draft_id = (
                mapping.professional_listing_draft_id
                if outcome is ImportRowOutcome.ALREADY_IMPORTED
                else None
            )
            cur.execute(
                _MARK_ROW_OUTCOME,
                [outcome.value, draft_id.value if draft_id is not None else None, row.row_id.value],
            )
            return ImportRowConfirmResult(
                row_id=row.row_id, outcome=outcome, professional_listing_draft_id=draft_id
            )

        try:
            # Nested `conn.transaction()` becomes a SAVEPOINT here (psycopg3
            # semantics): a UniqueViolation below rolls back only this
            # inner block, leaving the outer per-row transaction -- and the
            # cursor's subsequent re-read/UPDATE -- still usable.
            with conn.transaction():
                new_draft_id = create_draft()
                cur.execute(
                    _INSERT_MAPPING,
                    [
                        owner_organization_id.value,
                        import_source.value,
                        row.source_record_key.value,
                        row.row_digest,
                        new_draft_id.value,
                        batch_id.value,
                    ],
                )
        except UniqueViolation:
            # Lost the race for this key against a concurrent confirm:
            # re-read the now-committed row and classify from it exactly
            # like the pre-existing-key path above.
            cur.execute(
                _SELECT_MAPPING_FOR_UPDATE,
                [owner_organization_id.value, import_source.value, row.source_record_key.value],
            )
            winner_row = cur.fetchone()
            assert winner_row is not None
            mapping = _mapping_row_to_record(winner_row)
            outcome = (
                ImportRowOutcome.ALREADY_IMPORTED
                if mapping.row_digest == row.row_digest
                else ImportRowOutcome.CONFLICT_REVIEW
            )
            draft_id = (
                mapping.professional_listing_draft_id
                if outcome is ImportRowOutcome.ALREADY_IMPORTED
                else None
            )
            cur.execute(
                _MARK_ROW_OUTCOME,
                [outcome.value, draft_id.value if draft_id is not None else None, row.row_id.value],
            )
            return ImportRowConfirmResult(
                row_id=row.row_id, outcome=outcome, professional_listing_draft_id=draft_id
            )

        cur.execute(
            _MARK_ROW_OUTCOME,
            [ImportRowOutcome.CREATE_NEW_DRAFT.value, new_draft_id.value, row.row_id.value],
        )
        return ImportRowConfirmResult(
            row_id=row.row_id,
            outcome=ImportRowOutcome.CREATE_NEW_DRAFT,
            professional_listing_draft_id=new_draft_id,
        )
