"""Broker inventory portability export orchestration — SLICE-0088.

Implements the Owner-accepted (2026-10-16 seven-format amendment) broker
export workflow: given the current session, one explicit Organization and
an explicit broker-selected set of private draft / promoted listing ids,
evaluate authorization, assemble one bounded, deterministically ordered,
single-consistent-snapshot set of `hullq.domain.inventory_export
.ExportRow`, compute the per-row/per-format preflight, and dispatch to
exactly one of the seven accepted writer adapters. XLSB is not, and must
not become, an accepted format here (GitHub issue #362).

**Authorization** reuses the exact accepted SLICE-0053 Organization
workspace boundary (`hullq.application.broker_workspace_read
.get_organization_workspace_result`) -- never a second, independently
reimplemented membership/MFA check -- and additionally requires the
`PUBLISHER` role. Bulk export of a broker's complete listing data
(including private drafts) is a materially more sensitive action than the
read-only paginated inventory browsing `hullq.application
.broker_inventory_read` already allows any active member to perform, so it
is held to the same bar as publishing (`hullq.domain.publishing_eligibility
.MembershipRole.PUBLISHER`) rather than mere membership.

**Single consistent PostgreSQL observation** (Required Behavior: "Make a
single consistent PostgreSQL observation across draft/offer/current
PhysicalBoat claim/media/lifecycle states"): the whole snapshot read runs
inside one `REPEATABLE READ, READ ONLY` transaction opened once at the
start of `build_export_snapshot`, so every row this call produces reflects
the identical database instant, never a tear across a concurrent commit
between two of this call's own statements. The transaction is always
rolled back (never committed) -- a read-only export performs zero
mutation, by construction, not merely by convention.

**Bounded concurrency** (Post-0087 external review / mechanical
invariants: "no new single-worker event-loop blocking work"): a module-
level bounded semaphore limits how many *heavy* snapshot-assembly/
serialization calls may run concurrently, independent of FastAPI's own
thread-pool sizing for synchronous routes. A caller that cannot acquire it
promptly gets `ExportDownloadOutcome.BUSY` rather than queuing
indefinitely and risking starving the same shared thread pool that serves
ordinary Search/health/broker requests.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.application.public_listing_read import get_public_listing_read_model
from hullq.domain.inventory_export import (
    MAX_EXPORT_ROWS,
    ExportFormat,
    ExportRow,
    ExportSourceKind,
    ExportWriteError,
    RowPreflight,
    build_nautix_document,
    build_row_preflight,
    write_csv,
    write_json,
    write_ods,
    write_tsv,
    write_xls,
    write_xlsx,
)
from hullq.domain.listing_draft_payload import BuildYearAssertionKind
from hullq.domain.market_identity import MarketEpisodeId, NativeListingId
from hullq.domain.media_gallery import MediaPlacementKind
from hullq.domain.native_listing_offer import AssertionKind
from hullq.domain.professional_listing_draft import (
    ProfessionalDraftPromotionState,
    ProfessionalListingDraftId,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId, MembershipRole
from hullq.persistence.broker_identity import fetch_membership_for_account_and_organization
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.media_gallery import fetch_gallery_state
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim
from hullq.persistence.professional_listing_draft import fetch_professional_listing_draft
from hullq.security.session_token import SessionClaims

__all__ = [
    "MAX_EXPORT_SELECTION_ITEMS",
    "ExportAuthorizationOutcome",
    "ExportDownloadOutcome",
    "ExportDownloadResult",
    "ExportPreflightOutcome",
    "ExportPreflightResult",
    "ExportSelectionItem",
    "authorize_export",
    "build_export_snapshot",
    "get_export_download",
    "get_export_preflight",
]

#: Identical bound to the domain layer's own `MAX_EXPORT_ROWS` -- kept as a
#: separate named constant here only because this is the boundary that
#: rejects an oversized *request* (before any row is even read), while the
#: domain constant separately bounds what a writer will ever accept.
MAX_EXPORT_SELECTION_ITEMS = MAX_EXPORT_ROWS

#: Bounded concurrent heavy export jobs, independent of FastAPI/Starlette's
#: own sync-route thread-pool capacity -- so a burst of export requests
#: cannot itself starve that shared pool for ordinary Search/health/broker
#: traffic. Deliberately small and explicit rather than left to the
#: thread-pool's own much larger default limit.
_MAX_CONCURRENT_EXPORTS = 3
_export_concurrency_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_EXPORTS)
#: How long one caller waits to acquire a concurrency slot before the
#: request fails closed as BUSY rather than queuing indefinitely.
_EXPORT_ACQUIRE_TIMEOUT_SECONDS = 5.0


class ExportAuthorizationOutcome(StrEnum):
    """Mechanically distinct outcomes for one export authorization check.

    `NOT_FOUND_OR_DENIED` deliberately collapses "Organization does not
    exist" and "Organization exists but you have no/inactive membership"
    (mirrors `hullq.application.broker_workspace_read
    .OrganizationWorkspaceOutcome`). `PUBLISHER_ROLE_REQUIRED` is a
    separate, non-enumerating-safe outcome: the caller already proved
    active membership in *this* Organization (so disclosing that a
    stronger role is required leaks nothing about any other Organization).
    """

    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


def authorize_export(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> ExportAuthorizationOutcome:
    """The one safe authorization boundary every export entry point calls
    first and exactly once. Reads current membership truth fresh (never
    trusts the session token's own identity/MFA evidence to imply access)."""
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return ExportAuthorizationOutcome.NOT_FOUND_OR_DENIED
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return ExportAuthorizationOutcome.MFA_REQUIRED

    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    if membership is None or MembershipRole.PUBLISHER not in membership.roles:
        return ExportAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED
    return ExportAuthorizationOutcome.AUTHORIZED


@dataclass(frozen=True)
class ExportSelectionItem:
    """One explicit broker-chosen selection item -- exactly one of
    *draft_id*/*native_listing_id* is set."""

    draft_id: str | None = None
    native_listing_id: str | None = None

    def __post_init__(self) -> None:
        if (self.draft_id is None) == (self.native_listing_id is None):
            raise ValueError(
                "ExportSelectionItem must set exactly one of draft_id/native_listing_id"
            )


class _SnapshotOutcome(StrEnum):
    OK = "OK"
    EMPTY_SELECTION = "EMPTY_SELECTION"
    OVERSIZE_SELECTION = "OVERSIZE_SELECTION"
    UNKNOWN_ITEM = "UNKNOWN_ITEM"


@contextmanager
def _repeatable_read_only_snapshot(conn: Any) -> Any:
    """Open one `REPEATABLE READ, READ ONLY` transaction for the whole
    snapshot read, then always roll back -- the exact "single consistent
    PostgreSQL observation" the slice requires, with mutation structurally
    impossible (a READ ONLY transaction cannot write) rather than merely
    avoided by convention. Must be the very first statement on *conn*
    (mirrors `hullq.persistence.native_listing
    .NativeListingTransactionOwnershipError`'s identical IDLE-connection
    requirement for a top-level transaction)."""
    from psycopg.pq import TransactionStatus

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise RuntimeError(
            "conn already has an open transaction; the export snapshot read requires an IDLE "
            "connection so it can own one REPEATABLE READ, READ ONLY transaction for the whole "
            "read."
        )
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    try:
        yield conn
    finally:
        conn.rollback()


def _draft_build_year(payload_build_year: Any) -> tuple[int | None, bool]:
    if payload_build_year is None:
        return None, False
    if payload_build_year.assertion_kind is BuildYearAssertionKind.VALUE_ASSERTION:
        return payload_build_year.value, False
    return None, True


def _draft_to_export_row(draft: Any, *, organization_id: str) -> ExportRow:
    payload = draft.payload
    build_year, build_year_unknown = _draft_build_year(payload.build_year)
    return ExportRow(
        export_id=f"{organization_id}:draft:{draft.draft_id.value}",
        organization_id=organization_id,
        source_kind=ExportSourceKind.PRIVATE_DRAFT,
        status="PRIVATE_DRAFT",
        is_current_public=False,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        broker_listing_reference=draft.broker_listing_reference,
        marketed_brand_claim=payload.marketed_brand_claim,
        model_designation_claim=payload.model_designation_claim,
        build_year=build_year,
        build_year_unknown=build_year_unknown,
        boat_name=payload.boat_name,
        asking_price_mode=(
            payload.asking_price_mode.value if payload.asking_price_mode is not None else None
        ),
        asking_price_amount=payload.asking_price_amount,
        currency=payload.currency,
        location_country=payload.location_country,
        location_region=payload.location_region,
        broker_description=draft.broker_description,
    )


def _claim_physical_boat_facts(
    conn: Any,
    *,
    market_episode_id: MarketEpisodeId | None,
    organization_id: MarketplaceOrganizationId,
) -> dict[str, Any]:
    """This exact Organization's own current PhysicalBoat claim facts
    (never another Organization's claim, never canonical qualified
    BoatDesign-only Search facts)."""
    facts: dict[str, Any] = {
        "marketed_brand_claim": None,
        "model_designation_claim": None,
        "build_year": None,
        "build_year_unknown": False,
        "boat_name": None,
        "boat_name_unknown": False,
        "loa_meters": None,
        "loa_unknown": False,
    }
    if market_episode_id is None:
        return facts
    episode = fetch_market_episode(conn, market_episode_id)
    if episode is None:
        return facts
    claim_record = fetch_current_physical_boat_claim(
        conn, episode.market_episode.physical_boat_id, organization_id
    )
    if claim_record is None:
        return facts
    claims = claim_record.claims
    facts["marketed_brand_claim"] = claims.marketed_brand_claim
    facts["model_designation_claim"] = claims.model_designation_claim
    if claims.build_year.assertion_kind is AssertionKind.VALUE_ASSERTION:
        facts["build_year"] = claims.build_year.value
    else:
        facts["build_year_unknown"] = True
    if claims.boat_name is not None:
        if claims.boat_name.assertion_kind is AssertionKind.VALUE_ASSERTION:
            facts["boat_name"] = claims.boat_name.value
        elif claims.boat_name.assertion_kind is AssertionKind.UNKNOWN:
            facts["boat_name_unknown"] = True
        # ABSENT (the boat genuinely has no name) leaves boat_name=None,
        # boat_name_unknown=False -- distinct from both a value and UNKNOWN.
    if claims.loa_length is not None:
        if claims.loa_length.assertion_kind is AssertionKind.VALUE_ASSERTION:
            facts["loa_meters"] = claims.loa_length.value
        else:
            facts["loa_unknown"] = True
    return facts


def _promoted_media(
    conn: Any, native_listing_id: NativeListingId, *, is_public: bool, public_base_url: str | None
) -> tuple[tuple[str, ...], tuple[str | None, ...], tuple[str | None, ...]]:
    """Approved, rights-cleared media derivative URLs -- only ever for a
    listing that is *currently public* (Required Behavior: "approved
    rights-cleared media derivative URLs only when supported"), reusing the
    exact existing public media route
    (`GET /api/listings/{native_listing_id}/media/{media_placement_id}`) --
    never a new media-serving producer. A private draft or a non-public
    listing always gets an empty media set here, never a fabricated/private
    URL."""
    if not is_public or public_base_url is None:
        return (), (), ()
    gallery = fetch_gallery_state(conn, native_listing_id)
    urls: list[str] = []
    md5s: list[str | None] = []
    mimes: list[str | None] = []
    for placement in gallery.placements:
        if placement.kind is not MediaPlacementKind.IMAGE or placement.media_asset is None:
            continue
        if not placement.media_asset.is_public_usable:
            continue
        urls.append(
            f"{public_base_url.rstrip('/')}/api/listings/{native_listing_id.value}/media/"
            f"{placement.media_placement_id.value}"
        )
        md5s.append(placement.media_asset.content_hash)
        mimes.append(placement.media_asset.mime_type)
    return tuple(urls), tuple(md5s), tuple(mimes)


def _promoted_to_export_row(
    conn: Any,
    native_listing_id: NativeListingId,
    *,
    organization_id: MarketplaceOrganizationId,
    as_of: datetime,
    public_base_url: str | None,
) -> ExportRow | None:
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None or listing_record.publishing_organization_id != organization_id:
        # Unknown and foreign-Organization listing collapse to the identical
        # None result -- never a cross-tenant existence oracle.
        return None

    is_public = get_public_listing_read_model(conn, native_listing_id, as_of=as_of) is not None
    offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
    facts = _claim_physical_boat_facts(
        conn,
        market_episode_id=listing_record.listing.market_episode_id,
        organization_id=organization_id,
    )
    media_urls, media_md5s, media_mime_types = _promoted_media(
        conn, native_listing_id, is_public=is_public, public_base_url=public_base_url
    )

    asking_price_mode = asking_price_amount = currency = None
    location_country = location_region = broker_description = None
    location_region_unknown = False
    if offer_record is not None:
        offer = offer_record.offer
        asking_price_mode = offer.asking_price_mode.value
        asking_price_amount = offer.asking_price_amount
        currency = offer.currency
        location_country = offer.location_country
        broker_description = offer.broker_description
        if offer.location_region is not None:
            if offer.location_region.assertion_kind is AssertionKind.VALUE_ASSERTION:
                location_region = offer.location_region.value
            else:
                location_region_unknown = True

    # SLICE-0043/0045 do not track a separate offer-level updated_at this
    # read model can cheaply reuse; the listing's own created_at is the
    # safe, honest fallback (never a fabricated/guessed timestamp).
    updated_at = listing_record.created_at

    return ExportRow(
        export_id=f"{organization_id.value}:listing:{native_listing_id.value}",
        organization_id=organization_id.value,
        source_kind=ExportSourceKind.PROMOTED_LISTING,
        status=_resolve_lifecycle_state_text(conn, native_listing_id),
        is_current_public=is_public,
        created_at=listing_record.created_at,
        updated_at=updated_at,
        broker_listing_reference=listing_record.broker_listing_reference,
        marketed_brand_claim=facts["marketed_brand_claim"],
        model_designation_claim=facts["model_designation_claim"],
        build_year=facts["build_year"],
        build_year_unknown=facts["build_year_unknown"],
        boat_name=facts["boat_name"],
        boat_name_unknown=facts["boat_name_unknown"],
        loa_meters=facts["loa_meters"],
        loa_unknown=facts["loa_unknown"],
        asking_price_mode=asking_price_mode,
        asking_price_amount=asking_price_amount,
        currency=currency,
        location_country=location_country,
        location_region=location_region,
        location_region_unknown=location_region_unknown,
        broker_description=broker_description,
        media_urls=media_urls,
        media_md5s=media_md5s,
        media_mime_types=media_mime_types,
    )


def _resolve_lifecycle_state_text(conn: Any, native_listing_id: NativeListingId) -> str:
    from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state

    state = fetch_lifecycle_state(conn, native_listing_id)
    return state.value if state is not None else "DRAFT"


@dataclass(frozen=True)
class ExportSnapshot:
    organization_id: str
    rows: tuple[ExportRow, ...]


def build_export_snapshot(
    conn: Any,
    *,
    organization_id: MarketplaceOrganizationId,
    selection: list[ExportSelectionItem],
    as_of: datetime,
    public_base_url: str | None,
) -> tuple[_SnapshotOutcome, ExportSnapshot | None]:
    """Assemble one bounded, deterministically ordered, single-consistent-
    snapshot set of `ExportRow` for *selection*.

    Caller must have already called `authorize_export` and received
    `AUTHORIZED` for the exact same *organization_id* -- this function
    performs no authorization check of its own, only per-item ownership
    scoping (never trusting a caller-supplied id to belong to this
    Organization without checking).
    """
    if not selection:
        return _SnapshotOutcome.EMPTY_SELECTION, None
    if len(selection) > MAX_EXPORT_SELECTION_ITEMS:
        return _SnapshotOutcome.OVERSIZE_SELECTION, None

    # Deduplicate while preserving first-occurrence order -- deterministic
    # for a given request, never re-sorted by any other criterion.
    seen: set[tuple[str, str]] = set()
    deduped: list[ExportSelectionItem] = []
    for item in selection:
        key: tuple[str, str]
        if item.draft_id is not None:
            key = ("draft", item.draft_id)
        else:
            assert item.native_listing_id is not None
            key = ("listing", item.native_listing_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    rows: list[ExportRow] = []
    with _repeatable_read_only_snapshot(conn) as scoped_conn:
        for item in deduped:
            if item.draft_id is not None:
                draft = fetch_professional_listing_draft(
                    scoped_conn,
                    draft_id=ProfessionalListingDraftId(item.draft_id),
                    owner_organization_id=organization_id,
                )
                if (
                    draft is None
                    or draft.promotion_state is not ProfessionalDraftPromotionState.EDITABLE
                ):
                    # Unknown, foreign-Organization and already-promoted
                    # drafts are indistinguishable here -- a promoted draft
                    # is represented by its resulting NativeListing instead,
                    # never exported twice under two identities.
                    return _SnapshotOutcome.UNKNOWN_ITEM, None
                rows.append(_draft_to_export_row(draft, organization_id=organization_id.value))
            else:
                assert item.native_listing_id is not None
                row = _promoted_to_export_row(
                    scoped_conn,
                    NativeListingId(item.native_listing_id),
                    organization_id=organization_id,
                    as_of=as_of,
                    public_base_url=public_base_url,
                )
                if row is None:
                    return _SnapshotOutcome.UNKNOWN_ITEM, None
                rows.append(row)

    return _SnapshotOutcome.OK, ExportSnapshot(
        organization_id=organization_id.value, rows=tuple(rows)
    )


# ---------------------------------------------------------------------------
# Preflight entry point
# ---------------------------------------------------------------------------


class ExportPreflightOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    EMPTY_SELECTION = "EMPTY_SELECTION"
    OVERSIZE_SELECTION = "OVERSIZE_SELECTION"
    UNKNOWN_ITEM = "UNKNOWN_ITEM"
    OK = "OK"


@dataclass(frozen=True)
class ExportPreflightResult:
    outcome: ExportPreflightOutcome
    rows: tuple[RowPreflight, ...] | None = None

    def __post_init__(self) -> None:
        if self.outcome is ExportPreflightOutcome.OK and self.rows is None:
            raise ValueError("An OK preflight result must carry rows")
        if self.outcome is not ExportPreflightOutcome.OK and self.rows is not None:
            raise ValueError("Only an OK preflight result may carry rows")


_AUTH_TO_PREFLIGHT = {
    ExportAuthorizationOutcome.NOT_FOUND_OR_DENIED: ExportPreflightOutcome.NOT_FOUND_OR_DENIED,
    ExportAuthorizationOutcome.MFA_REQUIRED: ExportPreflightOutcome.MFA_REQUIRED,
    ExportAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED: ExportPreflightOutcome.PUBLISHER_ROLE_REQUIRED,
}
_SNAPSHOT_TO_PREFLIGHT = {
    _SnapshotOutcome.EMPTY_SELECTION: ExportPreflightOutcome.EMPTY_SELECTION,
    _SnapshotOutcome.OVERSIZE_SELECTION: ExportPreflightOutcome.OVERSIZE_SELECTION,
    _SnapshotOutcome.UNKNOWN_ITEM: ExportPreflightOutcome.UNKNOWN_ITEM,
}


def get_export_preflight(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    selection: list[ExportSelectionItem],
    as_of: datetime,
    public_base_url: str | None,
) -> ExportPreflightResult:
    """Authorize, then build the snapshot and its per-row/per-format
    preflight -- no file is ever written by this call."""
    auth = authorize_export(conn, session, organization_id)
    if auth is not ExportAuthorizationOutcome.AUTHORIZED:
        return ExportPreflightResult(outcome=_AUTH_TO_PREFLIGHT[auth])
    # authorize_export only read; return conn to IDLE so build_export_snapshot
    # can own one fresh REPEATABLE READ, READ ONLY transaction for the whole
    # snapshot read (never straddling the authorization check's own implicit
    # transaction).
    conn.rollback()

    outcome, snapshot = build_export_snapshot(
        conn,
        organization_id=organization_id,
        selection=selection,
        as_of=as_of,
        public_base_url=public_base_url,
    )
    if outcome is not _SnapshotOutcome.OK:
        return ExportPreflightResult(outcome=_SNAPSHOT_TO_PREFLIGHT[outcome])
    assert snapshot is not None
    return ExportPreflightResult(
        outcome=ExportPreflightOutcome.OK,
        rows=tuple(build_row_preflight(row) for row in snapshot.rows),
    )


# ---------------------------------------------------------------------------
# Download entry point
# ---------------------------------------------------------------------------


class ExportDownloadOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    EMPTY_SELECTION = "EMPTY_SELECTION"
    OVERSIZE_SELECTION = "OVERSIZE_SELECTION"
    UNKNOWN_ITEM = "UNKNOWN_ITEM"
    BUSY = "BUSY"
    WRITE_FAILED = "WRITE_FAILED"
    OK = "OK"


_FORMAT_CONTENT_TYPES = {
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.TSV: "text/tab-separated-values; charset=utf-8",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.XLS: "application/vnd.ms-excel",
    ExportFormat.ODS: "application/vnd.oasis.opendocument.spreadsheet",
    ExportFormat.JSON: "application/json; charset=utf-8",
    ExportFormat.NAUTIX: "application/xml; charset=utf-8",
}
_FORMAT_EXTENSIONS = {
    ExportFormat.CSV: "csv",
    ExportFormat.TSV: "tsv",
    ExportFormat.XLSX: "xlsx",
    ExportFormat.XLS: "xls",
    ExportFormat.ODS: "ods",
    ExportFormat.JSON: "json",
    ExportFormat.NAUTIX: "xml",
}


@dataclass(frozen=True)
class ExportDownloadResult:
    outcome: ExportDownloadOutcome
    content: bytes | None = None
    content_type: str | None = None
    filename: str | None = None

    def __post_init__(self) -> None:
        carries_content = (
            self.content is not None or self.content_type is not None or self.filename is not None
        )
        if self.outcome is ExportDownloadOutcome.OK:
            if self.content is None or self.content_type is None or self.filename is None:
                raise ValueError("An OK download result must carry content/content_type/filename")
        elif carries_content:
            raise ValueError("Only an OK download result may carry content/content_type/filename")


def _write_format(
    fmt: ExportFormat, rows: list[ExportRow], *, organization_id: str, generated_at: datetime
) -> bytes:
    if fmt is ExportFormat.CSV:
        return write_csv(rows)
    if fmt is ExportFormat.TSV:
        return write_tsv(rows)
    if fmt is ExportFormat.XLSX:
        return write_xlsx(rows)
    if fmt is ExportFormat.XLS:
        return write_xls(rows)
    if fmt is ExportFormat.ODS:
        return write_ods(rows)
    if fmt is ExportFormat.JSON:
        return write_json(rows)
    assert fmt is ExportFormat.NAUTIX
    return build_nautix_document(rows, organization_id=organization_id, generated_at=generated_at)


def get_export_download(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    selection: list[ExportSelectionItem],
    export_format: ExportFormat,
    as_of: datetime,
    public_base_url: str | None,
) -> ExportDownloadResult:
    """Authorize, build the snapshot, and serialize it as *export_format*.

    Never mutates any durable state and never has a durable side effect on
    failure or success alike -- repeating this call with an identical
    selection against an unchanged snapshot produces byte-identical
    canonical field content every time.
    """
    auth = authorize_export(conn, session, organization_id)
    if auth is not ExportAuthorizationOutcome.AUTHORIZED:
        return ExportDownloadResult(outcome=ExportDownloadOutcome(auth.value))
    # authorize_export only read; return conn to IDLE so build_export_snapshot
    # can own one fresh REPEATABLE READ, READ ONLY transaction for the whole
    # snapshot read (never straddling the authorization check's own implicit
    # transaction).
    conn.rollback()

    outcome, snapshot = build_export_snapshot(
        conn,
        organization_id=organization_id,
        selection=selection,
        as_of=as_of,
        public_base_url=public_base_url,
    )
    if outcome is not _SnapshotOutcome.OK:
        return ExportDownloadResult(outcome=ExportDownloadOutcome(outcome.value))
    assert snapshot is not None

    acquired = _export_concurrency_semaphore.acquire(timeout=_EXPORT_ACQUIRE_TIMEOUT_SECONDS)
    if not acquired:
        return ExportDownloadResult(outcome=ExportDownloadOutcome.BUSY)
    try:
        content = _write_format(
            export_format,
            list(snapshot.rows),
            organization_id=snapshot.organization_id,
            generated_at=as_of,
        )
    except ExportWriteError:
        return ExportDownloadResult(outcome=ExportDownloadOutcome.WRITE_FAILED)
    finally:
        _export_concurrency_semaphore.release()

    extension = _FORMAT_EXTENSIONS[export_format]
    filename = f"hullq-inventory-export.{extension}"
    return ExportDownloadResult(
        outcome=ExportDownloadOutcome.OK,
        content=content,
        content_type=_FORMAT_CONTENT_TYPES[export_format],
        filename=filename,
    )
