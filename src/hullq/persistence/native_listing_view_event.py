"""Durable public-listing-view telemetry persistence — SLICE-0075.

Implements `specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md`
§5/§12: one durable, idempotent `PUBLIC_LISTING_VIEW` event per successfully
served public listing read. Mirrors the SLICE-0070
`hullq.persistence.buyer_lead.create_buyer_lead` idempotency discipline --
`INSERT ... ON CONFLICT (operation_id) DO NOTHING` plus an exact
fingerprint comparison -- rather than a check-then-insert race: a retry of
the same *operation_id* with the identical `(native_listing_id,
publishing_organization_id)` payload resolves to `ALREADY_RECORDED` without
a second row; a reused *operation_id* with a conflicting payload fails
closed as `CONFLICT` (contract §5) rather than silently overwriting or
double-counting.

The caller (the public FastAPI listing route, never
`hullq.application.public_listing_read.get_public_listing_read_model`
itself) is the sole authority on *when* a view genuinely occurred -- this
module performs no eligibility/visibility re-evaluation of its own. Wiring
this call only into the public route's own success path is what keeps a
broker/private preview read, an authenticated broker inventory/edit read or
a suppressed/not-public read from ever producing a `PUBLIC_LISTING_VIEW`
fact (contract §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.listing_telemetry import ListingTelemetryEventKind, ListingViewOperationId
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.fingerprint import fingerprint_dict

__all__ = [
    "RecordListingViewResult",
    "RecordListingViewStatus",
    "fetch_listing_view_count",
    "fetch_organization_listing_view_counts",
    "fetch_organization_listing_view_total",
    "record_public_listing_view",
]


class RecordListingViewStatus(StrEnum):
    """Mechanically distinct outcomes. Never a bare boolean."""

    RECORDED = "RECORDED"
    ALREADY_RECORDED = "ALREADY_RECORDED"
    #: contract §5: "A reused operation identity with conflicting payload
    #: must fail closed."
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class RecordListingViewResult:
    status: RecordListingViewStatus


def _payload_fingerprint(
    native_listing_id: NativeListingId, publishing_organization_id: MarketplaceOrganizationId
) -> str:
    return fingerprint_dict(
        {
            "native_listing_id": native_listing_id.value,
            "publishing_organization_id": publishing_organization_id.value,
        }
    )


_INSERT_VIEW_EVENT = """
INSERT INTO native_listing_view_events (
    operation_id, native_listing_id, publishing_organization_id, event_kind,
    payload_fingerprint, occurred_at
) VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (operation_id) DO NOTHING
"""

_SELECT_EXISTING_BY_OPERATION_ID = (
    "SELECT payload_fingerprint FROM native_listing_view_events WHERE operation_id = %s"
)


def record_public_listing_view(
    conn: Any,
    *,
    operation_id: ListingViewOperationId,
    native_listing_id: NativeListingId,
    publishing_organization_id: MarketplaceOrganizationId,
    occurred_at: datetime,
) -> RecordListingViewResult:
    """Durably record one `PUBLIC_LISTING_VIEW` event, idempotent on
    *operation_id* (contract §5).

    *occurred_at* must already be the server-resolved current instant --
    never a caller-supplied/request-derived timestamp (mirrors every other
    accepted write-time clock boundary in this codebase).
    """
    if not isinstance(operation_id, ListingViewOperationId):
        raise TypeError(
            f"operation_id must be a ListingViewOperationId, got {type(operation_id).__name__}"
        )
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if not isinstance(publishing_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "publishing_organization_id must be a MarketplaceOrganizationId, got "
            f"{type(publishing_organization_id).__name__}"
        )

    fingerprint = _payload_fingerprint(native_listing_id, publishing_organization_id)

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_VIEW_EVENT,
            (
                operation_id.value,
                native_listing_id.value,
                publishing_organization_id.value,
                ListingTelemetryEventKind.PUBLIC_LISTING_VIEW.value,
                fingerprint,
                occurred_at,
            ),
        )
        if cur.rowcount == 1:
            return RecordListingViewResult(status=RecordListingViewStatus.RECORDED)

        cur.execute(_SELECT_EXISTING_BY_OPERATION_ID, [operation_id.value])
        row = cur.fetchone()
        assert row is not None, "ON CONFLICT target row must exist"
        existing_fingerprint = row[0]

    if existing_fingerprint == fingerprint:
        return RecordListingViewResult(status=RecordListingViewStatus.ALREADY_RECORDED)
    return RecordListingViewResult(status=RecordListingViewStatus.CONFLICT)


# ---------------------------------------------------------------------------
# Reads — bounded, Organization/listing-scoped only (contract §10/§11)
# ---------------------------------------------------------------------------

_SELECT_LISTING_VIEW_COUNT = """
SELECT COUNT(*) FROM native_listing_view_events
WHERE native_listing_id = %s AND occurred_at >= %s AND occurred_at < %s
"""


def fetch_listing_view_count(
    conn: Any, native_listing_id: NativeListingId, *, window_start: datetime, window_end: datetime
) -> int:
    """Exact observed `PUBLIC_LISTING_VIEW` count for one NativeListing within
    `[window_start, window_end)`."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_LISTING_VIEW_COUNT, [native_listing_id.value, window_start, window_end])
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


_SELECT_ORG_VIEW_COUNTS_BY_LISTING = """
SELECT native_listing_id, COUNT(*) FROM native_listing_view_events
WHERE publishing_organization_id = %s AND occurred_at >= %s AND occurred_at < %s
GROUP BY native_listing_id
"""


def fetch_organization_listing_view_counts(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, int]:
    """Exact observed per-listing `PUBLIC_LISTING_VIEW` counts for one
    Organization within `[window_start, window_end)`. A listing with zero
    observed views in the window is simply absent from the returned mapping
    -- never a fabricated zero entry (callers default absent keys to 0)."""
    with conn.cursor() as cur:
        cur.execute(
            _SELECT_ORG_VIEW_COUNTS_BY_LISTING, [organization_id.value, window_start, window_end]
        )
        rows = cur.fetchall()
    return {row[0]: int(row[1]) for row in rows}


def fetch_organization_listing_view_total(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Exact observed total `PUBLIC_LISTING_VIEW` count across every one of
    this Organization's listings within `[window_start, window_end)`."""
    return sum(
        fetch_organization_listing_view_counts(
            conn, organization_id, window_start=window_start, window_end=window_end
        ).values()
    )
