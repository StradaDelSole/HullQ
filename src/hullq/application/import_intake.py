"""Multi-format broker inventory import intake orchestration — SLICE-0083.

Thin orchestration over the format parsers (`hullq.domain.import_parsers`,
`hullq.domain.import_spreadsheet`, `hullq.domain.import_nautix`), the
shared mapping/classification engine (`hullq.domain.import_intake`) and
the durable staging state (`hullq.persistence.import_intake`), translating
a signed `SessionClaims`, an explicit Organization selection and raw
upload bytes/mapping choices into one deterministic D26 outcome FastAPI
can render.

Authorization reuses the exact accepted SLICE-0053 Organization workspace
boundary plus the current-PUBLISHER-membership gate, identically to
`hullq.application.professional_listing_draft._authorize_draft_actor` --
duplicated here (not imported, since that name is module-private) rather
than widened into a shared/public helper neither module asked for.

Every confirmed row becomes an ordinary private `ProfessionalListingDraft`
via the exact accepted `hullq.persistence.professional_listing_draft.
create_professional_listing_draft` write path (mechanical invariants:
"Every confirmed import result is an existing Organization-owned private
ProfessionalListingDraft"). This module never promotes, publishes or
associates a BoatDesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.import_intake import (
    MAX_IMPORT_FILE_BYTES,
    ImportBatchId,
    ImportFormat,
    ImportParseError,
    ImportParseErrorKind,
    ImportRowOutcome,
    ImportSource,
    InvalidColumnMappingError,
    RowPreviewClassification,
    apply_mapping_to_rows,
    compute_file_sha256,
)
from hullq.domain.import_nautix import map_nautix_adverts_to_rows, parse_and_validate_nautix
from hullq.domain.import_parsers import parse_delimited_table, parse_json_table
from hullq.domain.import_spreadsheet import list_spreadsheet_worksheets, parse_spreadsheet_table
from hullq.domain.professional_listing_draft import parse_professional_listing_draft_request
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.import_intake import (
    ApplyMappingOutcome,
    ImportBatchRecord,
    ImportBatchStatus,
    ImportRowRecord,
    apply_import_batch_mapping,
    confirm_import_row,
    create_import_batch_awaiting_mapping,
    create_import_batch_mapped,
    fetch_import_batch,
    finalize_row_outcome_only,
    has_confirmed_snapshot_batch_with_different_digest,
    list_import_rows,
    list_recent_import_batches,
    mark_batch_confirmed,
    mark_batch_confirming,
)
from hullq.persistence.professional_listing_draft import create_professional_listing_draft
from hullq.security.session_token import SessionClaims

__all__ = [
    "ConfirmImportBatchOutcome",
    "ConfirmImportBatchResult",
    "GetImportBatchOutcome",
    "GetImportBatchResult",
    "ListImportBatchesOutcome",
    "ListImportBatchesResult",
    "RowConfirmSummary",
    "SetImportMappingOutcome",
    "SetImportMappingResult",
    "UploadImportOutcome",
    "UploadImportResult",
    "confirm_import_batch_for_organization",
    "get_import_batch_for_organization",
    "list_import_batches_for_organization",
    "set_import_mapping_for_organization",
    "upload_import_for_organization",
]


class _ImportActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


def _authorize_import_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> _ImportActorAuthorizationOutcome:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _ImportActorAuthorizationOutcome.NOT_FOUND_OR_DENIED
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _ImportActorAuthorizationOutcome.MFA_REQUIRED
    assert workspace_result.context is not None
    if "PUBLISHER" not in workspace_result.context.roles:
        return _ImportActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED
    return _ImportActorAuthorizationOutcome.AUTHORIZED


def _batch_to_public_dict(
    batch: ImportBatchRecord, rows: tuple[ImportRowRecord, ...]
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "import_batch_id": batch.batch_id.value,
        "import_format": batch.import_format.value,
        "import_source": batch.import_source.value,
        "worksheet_name": batch.worksheet_name,
        "snapshot_mode": batch.snapshot_mode,
        "status": batch.status.value,
        "row_count": batch.row_count,
        "created_at": batch.created_at.isoformat(),
        "expires_at": batch.expires_at.isoformat(),
    }
    if batch.staged_table is not None:
        body["headers"] = list(batch.staged_table.headers)
        body["preview_rows"] = [list(r) for r in batch.staged_table.rows[:20]]
    if batch.column_mapping is not None:
        body["column_mapping"] = batch.column_mapping
    if batch.mapped_at is not None:
        body["mapped_at"] = batch.mapped_at.isoformat()
    if batch.confirmed_at is not None:
        body["confirmed_at"] = batch.confirmed_at.isoformat()
    body["rows"] = [_row_to_public_dict(r) for r in rows]
    return body


def _row_to_public_dict(row: ImportRowRecord) -> dict[str, Any]:
    return {
        "row_ordinal": row.row_ordinal,
        "raw_fields": row.raw_fields,
        "unmapped_headers": list(row.unmapped_headers),
        "preview_classification": row.preview_classification.value,
        "preview_reasons": list(row.preview_reasons),
        "source_record_key": row.source_record_key.value if row.source_record_key else None,
        "outcome": row.outcome.value if row.outcome is not None else None,
        "created_professional_listing_draft_id": (
            row.created_professional_listing_draft_id.value
            if row.created_professional_listing_draft_id is not None
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class UploadImportOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INVALID_IMPORT_SOURCE = "INVALID_IMPORT_SOURCE"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    WORKSHEET_CHOICE_REQUIRED = "WORKSHEET_CHOICE_REQUIRED"
    PARSE_FAILED = "PARSE_FAILED"
    STAGED = "STAGED"


@dataclass(frozen=True)
class UploadImportResult:
    outcome: UploadImportOutcome
    batch: ImportBatchRecord | None = None
    rows: tuple[ImportRowRecord, ...] = ()
    available_worksheets: tuple[str, ...] = ()
    parse_error_kind: ImportParseErrorKind | None = None
    message: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        if self.outcome is UploadImportOutcome.STAGED:
            assert self.batch is not None
            return _batch_to_public_dict(self.batch, self.rows)
        if self.outcome is UploadImportOutcome.WORKSHEET_CHOICE_REQUIRED:
            return {
                "error": "worksheet_choice_required",
                "worksheets": list(self.available_worksheets),
            }
        return {
            "error": self.outcome.value.lower(),
            "kind": self.parse_error_kind.value if self.parse_error_kind else None,
            "message": self.message,
        }


_FORMAT_FROM_HEADER: dict[str, ImportFormat] = {f.value: f for f in ImportFormat}


def upload_import_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    *,
    raw_bytes: bytes,
    declared_format_value: str,
    import_source_value: str,
    worksheet_name: str | None,
    attested_account_tokens: frozenset[str],
) -> UploadImportResult:
    """Parse *raw_bytes* under the broker-declared *declared_format_value*
    and stage it as one new `ImportBatch` owned by the selected, authorized
    Organization.

    For a spreadsheet format without an explicit *worksheet_name*, returns
    `WORKSHEET_CHOICE_REQUIRED` with the real worksheet-name list and
    creates nothing (Required Behavior #1: explicit worksheet choice,
    never an implicit "first sheet" default).
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_import_actor(conn, session, organization_id)
    if auth is _ImportActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return UploadImportResult(outcome=UploadImportOutcome.NOT_FOUND_OR_DENIED)
    if auth is _ImportActorAuthorizationOutcome.MFA_REQUIRED:
        return UploadImportResult(outcome=UploadImportOutcome.MFA_REQUIRED)
    if auth is _ImportActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return UploadImportResult(outcome=UploadImportOutcome.PUBLISHER_ROLE_REQUIRED)

    fmt = _FORMAT_FROM_HEADER.get(declared_format_value)
    if fmt is None:
        return UploadImportResult(
            outcome=UploadImportOutcome.UNSUPPORTED_FORMAT,
            parse_error_kind=ImportParseErrorKind.UNSUPPORTED_FORMAT,
            message=f"unrecognized declared format {declared_format_value!r}",
        )
    if len(raw_bytes) > MAX_IMPORT_FILE_BYTES:
        return UploadImportResult(outcome=UploadImportOutcome.PAYLOAD_TOO_LARGE)

    try:
        import_source = ImportSource(import_source_value)
    except ValueError as exc:
        return UploadImportResult(
            outcome=UploadImportOutcome.INVALID_IMPORT_SOURCE, message=str(exc)
        )

    file_sha256 = compute_file_sha256(raw_bytes)

    try:
        if fmt is ImportFormat.CSV:
            table = parse_delimited_table(raw_bytes, delimiter=",")
        elif fmt is ImportFormat.TSV:
            table = parse_delimited_table(raw_bytes, delimiter="\t")
        elif fmt is ImportFormat.JSON:
            table = parse_json_table(raw_bytes)
        elif fmt in (ImportFormat.XLSX, ImportFormat.XLS, ImportFormat.XLSB, ImportFormat.ODS):
            if worksheet_name is None:
                worksheets = list_spreadsheet_worksheets(raw_bytes, fmt)
                return UploadImportResult(
                    outcome=UploadImportOutcome.WORKSHEET_CHOICE_REQUIRED,
                    available_worksheets=worksheets,
                )
            table = parse_spreadsheet_table(raw_bytes, fmt, worksheet_name=worksheet_name)
        else:
            assert fmt is ImportFormat.NAUTIX_XML
            root = parse_and_validate_nautix(raw_bytes)
            rows = map_nautix_adverts_to_rows(root, attested_account_tokens=attested_account_tokens)
            conn.commit()
            with conn.transaction():
                batch = create_import_batch_mapped(
                    conn,
                    owner_organization_id=organization_id,
                    created_by_account_id=session.account_id,
                    import_format=fmt,
                    import_source=import_source,
                    file_sha256=file_sha256,
                    file_byte_size=len(raw_bytes),
                    snapshot_mode=False,
                    rows=rows,
                )
            return UploadImportResult(
                outcome=UploadImportOutcome.STAGED,
                batch=batch,
                rows=list_import_rows(conn, batch_id=batch.batch_id),
            )
    except ImportParseError as exc:
        return UploadImportResult(
            outcome=UploadImportOutcome.PARSE_FAILED, parse_error_kind=exc.kind, message=exc.message
        )

    conn.commit()
    with conn.transaction():
        batch = create_import_batch_awaiting_mapping(
            conn,
            owner_organization_id=organization_id,
            created_by_account_id=session.account_id,
            import_format=fmt,
            import_source=import_source,
            worksheet_name=worksheet_name,
            file_sha256=file_sha256,
            file_byte_size=len(raw_bytes),
            staged_table=table,
        )
    return UploadImportResult(outcome=UploadImportOutcome.STAGED, batch=batch, rows=())


# ---------------------------------------------------------------------------
# Set mapping
# ---------------------------------------------------------------------------


class SetImportMappingOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    BATCH_NOT_FOUND = "BATCH_NOT_FOUND"
    WRONG_STATE = "WRONG_STATE"
    INVALID_MAPPING = "INVALID_MAPPING"
    MAPPED = "MAPPED"


@dataclass(frozen=True)
class SetImportMappingResult:
    outcome: SetImportMappingOutcome
    batch: ImportBatchRecord | None = None
    rows: tuple[ImportRowRecord, ...] = ()
    message: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        if self.outcome is SetImportMappingOutcome.MAPPED:
            assert self.batch is not None
            return _batch_to_public_dict(self.batch, self.rows)
        return {"error": self.outcome.value.lower(), "message": self.message}


def set_import_mapping_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    batch_id_value: str,
    *,
    column_mapping: dict[str, str],
    snapshot_mode: bool,
) -> SetImportMappingResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_import_actor(conn, session, organization_id)
    if auth is _ImportActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return SetImportMappingResult(outcome=SetImportMappingOutcome.NOT_FOUND_OR_DENIED)
    if auth is _ImportActorAuthorizationOutcome.MFA_REQUIRED:
        return SetImportMappingResult(outcome=SetImportMappingOutcome.MFA_REQUIRED)
    if auth is _ImportActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return SetImportMappingResult(outcome=SetImportMappingOutcome.PUBLISHER_ROLE_REQUIRED)

    batch_id = ImportBatchId(batch_id_value)
    batch = fetch_import_batch(conn, batch_id=batch_id, owner_organization_id=organization_id)
    if batch is None:
        return SetImportMappingResult(outcome=SetImportMappingOutcome.BATCH_NOT_FOUND)
    if batch.status is not ImportBatchStatus.AWAITING_MAPPING or batch.staged_table is None:
        return SetImportMappingResult(outcome=SetImportMappingOutcome.WRONG_STATE)

    try:
        rows = apply_mapping_to_rows(
            batch.staged_table,
            column_mapping,
            snapshot_mode=snapshot_mode,
            file_sha256=batch.file_sha256,
        )
    except InvalidColumnMappingError as exc:
        return SetImportMappingResult(
            outcome=SetImportMappingOutcome.INVALID_MAPPING, message=str(exc)
        )

    conn.commit()
    with conn.transaction():
        apply_outcome = apply_import_batch_mapping(
            conn,
            batch_id=batch_id,
            owner_organization_id=organization_id,
            column_mapping=column_mapping,
            snapshot_mode=snapshot_mode,
            rows=rows,
        )
    if apply_outcome is not ApplyMappingOutcome.OK:
        return SetImportMappingResult(outcome=SetImportMappingOutcome.WRONG_STATE)

    updated_batch = fetch_import_batch(
        conn, batch_id=batch_id, owner_organization_id=organization_id
    )
    assert updated_batch is not None
    return SetImportMappingResult(
        outcome=SetImportMappingOutcome.MAPPED,
        batch=updated_batch,
        rows=list_import_rows(conn, batch_id=batch_id),
    )


# ---------------------------------------------------------------------------
# Get / list
# ---------------------------------------------------------------------------


class GetImportBatchOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    BATCH_NOT_FOUND = "BATCH_NOT_FOUND"
    FOUND = "FOUND"


@dataclass(frozen=True)
class GetImportBatchResult:
    outcome: GetImportBatchOutcome
    batch: ImportBatchRecord | None = None
    rows: tuple[ImportRowRecord, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        if self.outcome is GetImportBatchOutcome.FOUND:
            assert self.batch is not None
            return _batch_to_public_dict(self.batch, self.rows)
        return {"error": self.outcome.value.lower()}


def get_import_batch_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str, batch_id_value: str
) -> GetImportBatchResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_import_actor(conn, session, organization_id)
    if auth is _ImportActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return GetImportBatchResult(outcome=GetImportBatchOutcome.NOT_FOUND_OR_DENIED)
    if auth is _ImportActorAuthorizationOutcome.MFA_REQUIRED:
        return GetImportBatchResult(outcome=GetImportBatchOutcome.MFA_REQUIRED)
    if auth is _ImportActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return GetImportBatchResult(outcome=GetImportBatchOutcome.PUBLISHER_ROLE_REQUIRED)

    batch_id = ImportBatchId(batch_id_value)
    batch = fetch_import_batch(conn, batch_id=batch_id, owner_organization_id=organization_id)
    if batch is None:
        return GetImportBatchResult(outcome=GetImportBatchOutcome.BATCH_NOT_FOUND)
    return GetImportBatchResult(
        outcome=GetImportBatchOutcome.FOUND,
        batch=batch,
        rows=list_import_rows(conn, batch_id=batch_id),
    )


class ListImportBatchesOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    OK = "OK"


@dataclass(frozen=True)
class ListImportBatchesResult:
    outcome: ListImportBatchesOutcome
    batches: tuple[ImportBatchRecord, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        if self.outcome is not ListImportBatchesOutcome.OK:
            return {"error": self.outcome.value.lower()}
        return {"batches": [_batch_to_public_dict(b, ()) for b in self.batches]}


def list_import_batches_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str
) -> ListImportBatchesResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_import_actor(conn, session, organization_id)
    if auth is _ImportActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ListImportBatchesResult(outcome=ListImportBatchesOutcome.NOT_FOUND_OR_DENIED)
    if auth is _ImportActorAuthorizationOutcome.MFA_REQUIRED:
        return ListImportBatchesResult(outcome=ListImportBatchesOutcome.MFA_REQUIRED)
    if auth is _ImportActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return ListImportBatchesResult(outcome=ListImportBatchesOutcome.PUBLISHER_ROLE_REQUIRED)

    batches = list_recent_import_batches(conn, owner_organization_id=organization_id)
    return ListImportBatchesResult(outcome=ListImportBatchesOutcome.OK, batches=batches)


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------


class ConfirmImportBatchOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    BATCH_NOT_FOUND = "BATCH_NOT_FOUND"
    WRONG_STATE = "WRONG_STATE"
    STAGING_EXPIRED = "STAGING_EXPIRED"
    CONFIRMED = "CONFIRMED"


@dataclass(frozen=True)
class RowConfirmSummary:
    create_new_draft: int = 0
    already_imported: int = 0
    conflict_review: int = 0
    invalid: int = 0

    def to_public_dict(self) -> dict[str, int]:
        return {
            "CREATE_NEW_DRAFT": self.create_new_draft,
            "ALREADY_IMPORTED": self.already_imported,
            "CONFLICT_REVIEW": self.conflict_review,
            "INVALID": self.invalid,
        }


@dataclass(frozen=True)
class ConfirmImportBatchResult:
    outcome: ConfirmImportBatchOutcome
    batch: ImportBatchRecord | None = None
    rows: tuple[ImportRowRecord, ...] = ()
    summary: RowConfirmSummary | None = None

    def to_public_dict(self) -> dict[str, Any]:
        if self.outcome is not ConfirmImportBatchOutcome.CONFIRMED:
            return {"error": self.outcome.value.lower()}
        assert self.batch is not None
        assert self.summary is not None
        body = _batch_to_public_dict(self.batch, self.rows)
        body["summary"] = self.summary.to_public_dict()
        return body


def _create_draft_for_row(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    session: SessionClaims,
    row: ImportRowRecord,
) -> Any:
    """`confirm_import_row`'s injected `create_draft` callable for one
    `VALID` row: reconstructs the already-once-validated
    `ProfessionalListingDraftRequest` from the staged wire dict and writes
    it via the exact accepted draft creation path."""
    assert row.draft_request_wire is not None
    request = parse_professional_listing_draft_request(row.draft_request_wire)
    record = create_professional_listing_draft(
        conn,
        owner_organization_id=organization_id,
        created_by_account_id=session.account_id,
        broker_listing_reference=request.broker_listing_reference,
        broker_description=request.broker_description,
        payload=request.common,
    )
    return record.draft_id


def confirm_import_batch_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str, batch_id_value: str
) -> ConfirmImportBatchResult:
    """Explicitly confirm one staged batch: resolve every row's final D26
    outcome and durably commit it.

    Resumable: a row that already carries an `outcome` (from a prior
    confirm call, including one whose HTTP response was lost) is read
    back unchanged, never reprocessed (Required Behavior: "retry after
    lost response").
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_import_actor(conn, session, organization_id)
    if auth is _ImportActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ConfirmImportBatchResult(outcome=ConfirmImportBatchOutcome.NOT_FOUND_OR_DENIED)
    if auth is _ImportActorAuthorizationOutcome.MFA_REQUIRED:
        return ConfirmImportBatchResult(outcome=ConfirmImportBatchOutcome.MFA_REQUIRED)
    if auth is _ImportActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return ConfirmImportBatchResult(outcome=ConfirmImportBatchOutcome.PUBLISHER_ROLE_REQUIRED)

    batch_id = ImportBatchId(batch_id_value)
    batch = fetch_import_batch(conn, batch_id=batch_id, owner_organization_id=organization_id)
    if batch is None:
        return ConfirmImportBatchResult(outcome=ConfirmImportBatchOutcome.BATCH_NOT_FOUND)
    if batch.status not in (
        ImportBatchStatus.MAPPED,
        ImportBatchStatus.CONFIRMING,
        ImportBatchStatus.CONFIRMED,
    ):
        return ConfirmImportBatchResult(outcome=ConfirmImportBatchOutcome.WRONG_STATE)
    if datetime.now(UTC) > batch.expires_at and batch.status is not ImportBatchStatus.CONFIRMED:
        return ConfirmImportBatchResult(outcome=ConfirmImportBatchOutcome.STAGING_EXPIRED)

    conn.commit()
    with conn.transaction():
        mark_batch_confirming(conn, batch_id=batch_id)

    # Required Behavior #4: a snapshot-mode batch whose exact file digest
    # differs from an earlier *confirmed* snapshot batch for this same
    # Organization/ImportSource can never establish row continuity with
    # it -- every would-be-VALID row is forced to CONFLICT_REVIEW rather
    # than silently creating a second batch of drafts for conceptually the
    # same rows (snapshot keys are namespaced by file digest, so they would
    # otherwise never collide at the identity-mapping-table level at all).
    force_snapshot_conflict = (
        batch.snapshot_mode
        and has_confirmed_snapshot_batch_with_different_digest(
            conn,
            owner_organization_id=organization_id,
            import_source=batch.import_source,
            file_sha256=batch.file_sha256,
        )
    )

    rows = list_import_rows(conn, batch_id=batch_id)
    summary = RowConfirmSummary()
    for row in rows:
        if row.preview_classification is RowPreviewClassification.INVALID:
            outcome = ImportRowOutcome.INVALID
            if row.outcome is None:
                conn.commit()
                with conn.transaction():
                    finalize_row_outcome_only(conn, row_id=row.row_id, outcome=outcome)
        elif (
            row.preview_classification is RowPreviewClassification.CONFLICT_REVIEW
            or force_snapshot_conflict
        ):
            outcome = ImportRowOutcome.CONFLICT_REVIEW
            if row.outcome is None:
                conn.commit()
                with conn.transaction():
                    finalize_row_outcome_only(conn, row_id=row.row_id, outcome=outcome)
        else:
            assert row.preview_classification is RowPreviewClassification.VALID

            # confirm_import_row requires an IDLE connection (it owns its
            # own per-row transaction) -- a prior branch's skipped
            # finalize_row_outcome_only call, or the read-only
            # list_import_rows() select above, may have left an implicit
            # transaction open.
            conn.commit()
            result = confirm_import_row(
                conn,
                row=row,
                owner_organization_id=organization_id,
                import_source=batch.import_source,
                batch_id=batch_id,
                create_draft=lambda row=row: _create_draft_for_row(
                    conn, organization_id, session, row
                ),
            )
            outcome = result.outcome

        if outcome is ImportRowOutcome.CREATE_NEW_DRAFT:
            summary = RowConfirmSummary(
                create_new_draft=summary.create_new_draft + 1,
                already_imported=summary.already_imported,
                conflict_review=summary.conflict_review,
                invalid=summary.invalid,
            )
        elif outcome is ImportRowOutcome.ALREADY_IMPORTED:
            summary = RowConfirmSummary(
                create_new_draft=summary.create_new_draft,
                already_imported=summary.already_imported + 1,
                conflict_review=summary.conflict_review,
                invalid=summary.invalid,
            )
        elif outcome is ImportRowOutcome.CONFLICT_REVIEW:
            summary = RowConfirmSummary(
                create_new_draft=summary.create_new_draft,
                already_imported=summary.already_imported,
                conflict_review=summary.conflict_review + 1,
                invalid=summary.invalid,
            )
        else:
            assert outcome is ImportRowOutcome.INVALID
            summary = RowConfirmSummary(
                create_new_draft=summary.create_new_draft,
                already_imported=summary.already_imported,
                conflict_review=summary.conflict_review,
                invalid=summary.invalid + 1,
            )

    conn.commit()
    with conn.transaction():
        mark_batch_confirmed(conn, batch_id=batch_id)

    final_batch = fetch_import_batch(conn, batch_id=batch_id, owner_organization_id=organization_id)
    assert final_batch is not None
    final_rows = list_import_rows(conn, batch_id=batch_id)
    return ConfirmImportBatchResult(
        outcome=ConfirmImportBatchOutcome.CONFIRMED,
        batch=final_batch,
        rows=final_rows,
        summary=summary,
    )
