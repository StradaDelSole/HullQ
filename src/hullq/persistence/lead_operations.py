"""Broker Lead operational workflow persistence — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§3/§4/§6/§7/§8/§8A: the Organization-scoped Lead inbox/detail read
projections and the authorized mutations (assignment/status/read/notes/
follow-up/contact-attempts/close) layered on the SLICE-0070 immutable
`buyer_leads` envelope.

This module performs no tenancy/role authorization itself -- the caller
(`hullq.application.lead_operations`) must have already established that
the requesting Account currently holds the required Organization membership
for the exact `publishing_organization_id` a given `lead_id` belongs to
before calling any mutation here. Every read/mutation here is scoped by an
explicit `lead_id`/`organization_id` the caller supplies; no function here
searches across Organizations to find a matching row.

`lead_operational_state` rows are created lazily (bootstrapped on first
mutation, never at Lead-creation time): absence of a row is exactly
equivalent to the default `NEW`/unread/unassigned/no-follow-up state
(contract §5/§6), and every read function here returns that same default
shape rather than `None` for a Lead with no operational-state row yet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.buyer_lead import (
    ContactEmailVerificationState,
    LeadId,
    LeadSourceChannel,
)
from hullq.domain.lead_operations import (
    LeadCloseReason,
    LeadContactAttemptChannel,
    LeadOperationalStatus,
    LeadTimelineEventType,
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "MAX_TIMELINE_EVENTS_PER_READ",
    "LeadDetailRecord",
    "LeadInboxRow",
    "LeadInboxSortKey",
    "LeadMutationResult",
    "LeadOperationalStateRecord",
    "LeadOrganizationCounts",
    "LeadTimelineEventRecord",
    "append_lead_contact_attempt",
    "append_lead_note",
    "fetch_lead_detail",
    "fetch_lead_operational_state",
    "fetch_lead_timeline",
    "fetch_organization_lead_counts",
    "fetch_organization_lead_inbox_page",
    "mark_lead_read",
    "set_lead_assignment",
    "set_lead_follow_up_due_at",
    "set_lead_operational_status",
]

MAX_TIMELINE_EVENTS_PER_READ = 200


# ---------------------------------------------------------------------------
# Operational state — lazily-bootstrapped, optimistic-concurrency row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadOperationalStateRecord:
    lead_id: LeadId
    operational_status: LeadOperationalStatus
    is_unread: bool
    assigned_account_id: AccountId | None
    follow_up_due_at: datetime | None
    close_reason: LeadCloseReason | None
    version: int


@dataclass(frozen=True)
class LeadMutationResult:
    """`updated=False` means *expected_version* was stale -- the caller must
    re-read current state before retrying; nothing was silently overwritten."""

    updated: bool
    current: LeadOperationalStateRecord


_SELECT_OPERATIONAL_STATE = (
    "SELECT operational_status, is_unread, assigned_account_id, follow_up_due_at, close_reason, "
    "version FROM lead_operational_state WHERE lead_id = %s"
)

_BOOTSTRAP_OPERATIONAL_STATE = """
INSERT INTO lead_operational_state (lead_id, operational_status, is_unread, version)
VALUES (%s, 'NEW', TRUE, 0)
ON CONFLICT (lead_id) DO NOTHING
"""


def fetch_lead_operational_state(conn: Any, lead_id: LeadId) -> LeadOperationalStateRecord:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.cursor() as cur:
        cur.execute(_SELECT_OPERATIONAL_STATE, [lead_id.value])
        row = cur.fetchone()
    if row is None:
        return LeadOperationalStateRecord(
            lead_id=lead_id,
            operational_status=LeadOperationalStatus.NEW,
            is_unread=True,
            assigned_account_id=None,
            follow_up_due_at=None,
            close_reason=None,
            version=0,
        )
    return _row_to_operational_state(lead_id, row)


def _row_to_operational_state(lead_id: LeadId, row: Any) -> LeadOperationalStateRecord:
    status, is_unread, assigned_account_id_value, follow_up_due_at, close_reason_value, version = row
    return LeadOperationalStateRecord(
        lead_id=lead_id,
        operational_status=LeadOperationalStatus(status),
        is_unread=is_unread,
        assigned_account_id=(
            AccountId(assigned_account_id_value) if assigned_account_id_value is not None else None
        ),
        follow_up_due_at=follow_up_due_at,
        close_reason=LeadCloseReason(close_reason_value) if close_reason_value is not None else None,
        version=version,
    )


def _insert_timeline_event(
    cur: Any,
    *,
    lead_id: LeadId,
    event_type: LeadTimelineEventType,
    actor_account_id: AccountId,
    occurred_at: datetime,
    note_text: str | None = None,
    contact_channel: LeadContactAttemptChannel | None = None,
    close_reason: LeadCloseReason | None = None,
) -> None:
    cur.execute(
        "INSERT INTO lead_timeline_events "
        "(event_id, lead_id, event_type, actor_account_id, occurred_at, note_text, "
        "contact_channel, close_reason) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            str(uuid.uuid4()),
            lead_id.value,
            event_type.value,
            actor_account_id.value,
            occurred_at,
            note_text,
            contact_channel.value if contact_channel is not None else None,
            close_reason.value if close_reason is not None else None,
        ),
    )


# ---------------------------------------------------------------------------
# Mark read (contract §6) — monotonic one-way transition, no lost update
# possible: UPDATE ... WHERE is_unread = TRUE naturally serializes concurrent
# callers via Postgres row-level locking, so at most one caller ever
# observes rowcount > 0 and logs the MARKED_READ event.
# ---------------------------------------------------------------------------

_MARK_READ = "UPDATE lead_operational_state SET is_unread = FALSE WHERE lead_id = %s AND is_unread = TRUE"


def mark_lead_read(conn: Any, lead_id: LeadId, *, actor_account_id: AccountId, as_of: datetime) -> None:
    """Idempotently transition *lead_id* to read.

    Safe to call repeatedly and safe under concurrent callers: only the
    caller that actually flips `is_unread` records a `MARKED_READ` timeline
    event; a retry or a losing concurrent caller changes nothing and logs
    nothing.
    """
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_BOOTSTRAP_OPERATIONAL_STATE, [lead_id.value])
        cur.execute(_MARK_READ, [lead_id.value])
        if cur.rowcount > 0:
            _insert_timeline_event(
                cur,
                lead_id=lead_id,
                event_type=LeadTimelineEventType.MARKED_READ,
                actor_account_id=actor_account_id,
                occurred_at=as_of,
            )


# ---------------------------------------------------------------------------
# Assignment (contract §7)
# ---------------------------------------------------------------------------

_UPDATE_ASSIGNMENT = """
UPDATE lead_operational_state
SET assigned_account_id = %s, version = version + 1, updated_at = %s
WHERE lead_id = %s AND version = %s
RETURNING operational_status, is_unread, assigned_account_id, follow_up_due_at, close_reason, version
"""


def set_lead_assignment(
    conn: Any,
    lead_id: LeadId,
    *,
    assignee_account_id: AccountId | None,
    actor_account_id: AccountId,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationResult:
    """Set/change/clear the current assignee (contract §7).

    Whether *assignee_account_id* is a current ACTIVE member of the Lead's
    own Organization is the application layer's responsibility to verify
    before calling here -- this function only performs the optimistic-
    concurrency write and timeline record.
    """
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_BOOTSTRAP_OPERATIONAL_STATE, [lead_id.value])
        cur.execute(
            _UPDATE_ASSIGNMENT,
            [
                assignee_account_id.value if assignee_account_id is not None else None,
                as_of,
                lead_id.value,
                expected_version,
            ],
        )
        row = cur.fetchone()
        if row is None:
            current = fetch_lead_operational_state(conn, lead_id)
            return LeadMutationResult(updated=False, current=current)
        _insert_timeline_event(
            cur,
            lead_id=lead_id,
            event_type=(
                LeadTimelineEventType.ASSIGNED
                if assignee_account_id is not None
                else LeadTimelineEventType.UNASSIGNED
            ),
            actor_account_id=actor_account_id,
            occurred_at=as_of,
        )
        return LeadMutationResult(updated=True, current=_row_to_operational_state(lead_id, row))


# ---------------------------------------------------------------------------
# Operational status / close reason (contract §5/§8A)
# ---------------------------------------------------------------------------

_UPDATE_STATUS = """
UPDATE lead_operational_state
SET operational_status = %s, close_reason = %s, version = version + 1, updated_at = %s
WHERE lead_id = %s AND version = %s
RETURNING operational_status, is_unread, assigned_account_id, follow_up_due_at, close_reason, version
"""


def set_lead_operational_status(
    conn: Any,
    lead_id: LeadId,
    *,
    new_status: LeadOperationalStatus,
    close_reason: LeadCloseReason | None,
    actor_account_id: AccountId,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationResult:
    """Transition operational status (contract §5).

    *close_reason* must be supplied exactly when *new_status* is `CLOSED`
    (contract §8A) -- callers must validate this before calling; this
    function asserts it as a precondition rather than silently coercing it.
    """
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    if new_status is LeadOperationalStatus.CLOSED and close_reason is None:
        raise ValueError("close_reason is required when new_status is CLOSED")
    if new_status is not LeadOperationalStatus.CLOSED and close_reason is not None:
        raise ValueError("close_reason must be None unless new_status is CLOSED")
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_BOOTSTRAP_OPERATIONAL_STATE, [lead_id.value])
        cur.execute(
            _UPDATE_STATUS,
            [
                new_status.value,
                close_reason.value if close_reason is not None else None,
                as_of,
                lead_id.value,
                expected_version,
            ],
        )
        row = cur.fetchone()
        if row is None:
            current = fetch_lead_operational_state(conn, lead_id)
            return LeadMutationResult(updated=False, current=current)
        event_type = (
            LeadTimelineEventType.CLOSED
            if new_status is LeadOperationalStatus.CLOSED
            else LeadTimelineEventType.STATUS_CHANGED
        )
        _insert_timeline_event(
            cur,
            lead_id=lead_id,
            event_type=event_type,
            actor_account_id=actor_account_id,
            occurred_at=as_of,
            close_reason=close_reason,
        )
        return LeadMutationResult(updated=True, current=_row_to_operational_state(lead_id, row))


# ---------------------------------------------------------------------------
# Follow-up (contract §8A)
# ---------------------------------------------------------------------------

_UPDATE_FOLLOW_UP = """
UPDATE lead_operational_state
SET follow_up_due_at = %s, version = version + 1, updated_at = %s
WHERE lead_id = %s AND version = %s
RETURNING operational_status, is_unread, assigned_account_id, follow_up_due_at, close_reason, version
"""


def set_lead_follow_up_due_at(
    conn: Any,
    lead_id: LeadId,
    *,
    due_at: datetime | None,
    actor_account_id: AccountId,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationResult:
    """Set/change/clear the current follow-up due date/time (contract §8A)."""
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_BOOTSTRAP_OPERATIONAL_STATE, [lead_id.value])
        cur.execute(_UPDATE_FOLLOW_UP, [due_at, as_of, lead_id.value, expected_version])
        row = cur.fetchone()
        if row is None:
            current = fetch_lead_operational_state(conn, lead_id)
            return LeadMutationResult(updated=False, current=current)
        _insert_timeline_event(
            cur,
            lead_id=lead_id,
            event_type=(
                LeadTimelineEventType.FOLLOW_UP_SET
                if due_at is not None
                else LeadTimelineEventType.FOLLOW_UP_CLEARED
            ),
            actor_account_id=actor_account_id,
            occurred_at=as_of,
        )
        return LeadMutationResult(updated=True, current=_row_to_operational_state(lead_id, row))


# ---------------------------------------------------------------------------
# Notes / contact attempts (contract §8/§8A) — append-only, no read-modify-
# write, so no concurrency token is needed.
# ---------------------------------------------------------------------------


def append_lead_note(
    conn: Any, lead_id: LeadId, *, actor_account_id: AccountId, note_text: str, as_of: datetime
) -> None:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.transaction(), conn.cursor() as cur:
        _insert_timeline_event(
            cur,
            lead_id=lead_id,
            event_type=LeadTimelineEventType.NOTE,
            actor_account_id=actor_account_id,
            occurred_at=as_of,
            note_text=note_text,
        )


def append_lead_contact_attempt(
    conn: Any,
    lead_id: LeadId,
    *,
    actor_account_id: AccountId,
    channel: LeadContactAttemptChannel,
    note_text: str | None,
    as_of: datetime,
) -> None:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.transaction(), conn.cursor() as cur:
        _insert_timeline_event(
            cur,
            lead_id=lead_id,
            event_type=LeadTimelineEventType.CONTACT_ATTEMPT,
            actor_account_id=actor_account_id,
            occurred_at=as_of,
            note_text=note_text,
            contact_channel=channel,
        )


# ---------------------------------------------------------------------------
# Timeline read (contract §8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadTimelineEventRecord:
    event_id: str
    lead_id: LeadId
    event_type: LeadTimelineEventType
    actor_account_id: AccountId
    occurred_at: datetime
    note_text: str | None
    contact_channel: LeadContactAttemptChannel | None
    close_reason: LeadCloseReason | None


_SELECT_TIMELINE = """
SELECT event_id, lead_id, event_type, actor_account_id, occurred_at, note_text, contact_channel,
       close_reason
FROM lead_timeline_events
WHERE lead_id = %s
ORDER BY occurred_at DESC, event_id DESC
LIMIT %s
"""


def fetch_lead_timeline(
    conn: Any, lead_id: LeadId, *, limit: int = MAX_TIMELINE_EVENTS_PER_READ
) -> list[LeadTimelineEventRecord]:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    bounded_limit = min(max(limit, 1), MAX_TIMELINE_EVENTS_PER_READ)
    with conn.cursor() as cur:
        cur.execute(_SELECT_TIMELINE, [lead_id.value, bounded_limit])
        rows = cur.fetchall()
    return [
        LeadTimelineEventRecord(
            event_id=row[0],
            lead_id=LeadId(row[1]),
            event_type=LeadTimelineEventType(row[2]),
            actor_account_id=AccountId(row[3]),
            occurred_at=row[4],
            note_text=row[5],
            contact_channel=LeadContactAttemptChannel(row[6]) if row[6] is not None else None,
            close_reason=LeadCloseReason(row[7]) if row[7] is not None else None,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Lead detail (contract §4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadDetailRecord:
    """Immutable envelope fields plus current operational state, joined in
    one query. `None` publishing_organization_id/etc. never occurs -- a
    missing `lead_id` simply yields no `LeadDetailRecord` at all."""

    lead_id: LeadId
    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    account_id: AccountId | None
    buyer_name: str
    buyer_email: str
    contact_email_verification_state: ContactEmailVerificationState
    buyer_message: str
    source_channel: LeadSourceChannel
    received_at: datetime
    operational_state: LeadOperationalStateRecord


_SELECT_LEAD_DETAIL = """
SELECT bl.lead_id, bl.native_listing_id, bl.publishing_organization_id, bl.account_id,
       bl.buyer_name, bl.buyer_email, bl.contact_email_verification_state, bl.buyer_message,
       bl.source_channel, bl.received_at,
       los.operational_status, los.is_unread, los.assigned_account_id, los.follow_up_due_at,
       los.close_reason, los.version
FROM buyer_leads bl
LEFT JOIN lead_operational_state los ON los.lead_id = bl.lead_id
WHERE bl.lead_id = %s
"""


def fetch_lead_detail(conn: Any, lead_id: LeadId) -> LeadDetailRecord | None:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.cursor() as cur:
        cur.execute(_SELECT_LEAD_DETAIL, [lead_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    (
        lead_id_value,
        native_listing_id_value,
        publishing_organization_id_value,
        account_id_value,
        buyer_name,
        buyer_email,
        verification_state_value,
        buyer_message,
        source_channel_value,
        received_at,
        status_value,
        is_unread,
        assigned_account_id_value,
        follow_up_due_at,
        close_reason_value,
        version,
    ) = row
    resolved_lead_id = LeadId(lead_id_value)
    operational_state = (
        LeadOperationalStateRecord(
            lead_id=resolved_lead_id,
            operational_status=LeadOperationalStatus.NEW,
            is_unread=True,
            assigned_account_id=None,
            follow_up_due_at=None,
            close_reason=None,
            version=0,
        )
        if status_value is None
        else LeadOperationalStateRecord(
            lead_id=resolved_lead_id,
            operational_status=LeadOperationalStatus(status_value),
            is_unread=is_unread,
            assigned_account_id=(
                AccountId(assigned_account_id_value)
                if assigned_account_id_value is not None
                else None
            ),
            follow_up_due_at=follow_up_due_at,
            close_reason=(
                LeadCloseReason(close_reason_value) if close_reason_value is not None else None
            ),
            version=version,
        )
    )
    return LeadDetailRecord(
        lead_id=resolved_lead_id,
        native_listing_id=NativeListingId(native_listing_id_value),
        publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id_value),
        account_id=AccountId(account_id_value) if account_id_value is not None else None,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        contact_email_verification_state=ContactEmailVerificationState(verification_state_value),
        buyer_message=buyer_message,
        source_channel=LeadSourceChannel(source_channel_value),
        received_at=received_at,
        operational_state=operational_state,
    )


# ---------------------------------------------------------------------------
# Organization-scoped inbox (contract §3) — keyset pagination mirrors
# `hullq.persistence.native_listing_inventory`'s accepted pattern.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadInboxSortKey:
    received_at: datetime
    lead_id: LeadId


@dataclass(frozen=True)
class LeadInboxRow:
    lead_id: LeadId
    native_listing_id: NativeListingId
    buyer_name: str
    buyer_email: str
    contact_email_verification_state: ContactEmailVerificationState
    received_at: datetime
    source_channel: LeadSourceChannel
    operational_state: LeadOperationalStateRecord


_INBOX_BASE_SELECT = """
SELECT bl.lead_id, bl.native_listing_id, bl.buyer_name, bl.buyer_email,
       bl.contact_email_verification_state, bl.received_at, bl.source_channel,
       COALESCE(los.operational_status, 'NEW') AS operational_status,
       COALESCE(los.is_unread, TRUE) AS is_unread,
       los.assigned_account_id, los.follow_up_due_at, los.close_reason,
       COALESCE(los.version, 0) AS version
FROM buyer_leads bl
LEFT JOIN lead_operational_state los ON los.lead_id = bl.lead_id
WHERE bl.publishing_organization_id = %s
"""

_INBOX_ORDER_LIMIT = "ORDER BY bl.received_at DESC, bl.lead_id ASC LIMIT %s"


def fetch_organization_lead_inbox_page(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    limit: int,
    after: LeadInboxSortKey | None,
    status_filter: LeadOperationalStatus | None = None,
    assignee_filter: AccountId | None = None,
    unread_only: bool = False,
    follow_up_due_before: datetime | None = None,
) -> list[LeadInboxRow]:
    """Fetch up to *limit* rows for *organization_id*, deterministically
    ordered `received_at DESC, lead_id ASC`, continuing strictly after
    *after* when supplied.

    *follow_up_due_before* filters to Leads with a non-null
    `follow_up_due_at` at or before that instant -- pass the current
    instant for "due" (includes overdue), or leave `None` for no filter;
    "strictly overdue" is the same filter evaluated with `as_of` as the
    caller's own current time and compared client-side, or the caller may
    pass an earlier instant explicitly.
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    if after is not None and not isinstance(after, LeadInboxSortKey):
        raise TypeError(f"after must be a LeadInboxSortKey or None, got {type(after).__name__}")
    if limit <= 0:
        raise ValueError("limit must be positive")

    conditions: list[str] = []
    params: list[Any] = [organization_id.value]

    if after is not None:
        conditions.append("(bl.received_at < %s OR (bl.received_at = %s AND bl.lead_id > %s))")
        params.extend([after.received_at, after.received_at, after.lead_id.value])
    if status_filter is not None:
        conditions.append("COALESCE(los.operational_status, 'NEW') = %s")
        params.append(status_filter.value)
    if assignee_filter is not None:
        conditions.append("los.assigned_account_id = %s")
        params.append(assignee_filter.value)
    if unread_only:
        conditions.append("COALESCE(los.is_unread, TRUE) = TRUE")
    if follow_up_due_before is not None:
        conditions.append("los.follow_up_due_at IS NOT NULL AND los.follow_up_due_at <= %s")
        params.append(follow_up_due_before)

    query = _INBOX_BASE_SELECT
    if conditions:
        query += " AND " + " AND ".join(conditions)
    query += " " + _INBOX_ORDER_LIMIT
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    results = []
    for row in rows:
        (
            lead_id_value,
            native_listing_id_value,
            buyer_name,
            buyer_email,
            verification_state_value,
            received_at,
            source_channel_value,
            status_value,
            is_unread,
            assigned_account_id_value,
            follow_up_due_at,
            close_reason_value,
            version,
        ) = row
        resolved_lead_id = LeadId(lead_id_value)
        results.append(
            LeadInboxRow(
                lead_id=resolved_lead_id,
                native_listing_id=NativeListingId(native_listing_id_value),
                buyer_name=buyer_name,
                buyer_email=buyer_email,
                contact_email_verification_state=ContactEmailVerificationState(
                    verification_state_value
                ),
                received_at=received_at,
                source_channel=LeadSourceChannel(source_channel_value),
                operational_state=LeadOperationalStateRecord(
                    lead_id=resolved_lead_id,
                    operational_status=LeadOperationalStatus(status_value),
                    is_unread=is_unread,
                    assigned_account_id=(
                        AccountId(assigned_account_id_value)
                        if assigned_account_id_value is not None
                        else None
                    ),
                    follow_up_due_at=follow_up_due_at,
                    close_reason=(
                        LeadCloseReason(close_reason_value)
                        if close_reason_value is not None
                        else None
                    ),
                    version=version,
                ),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Factual dashboard/work-queue counts (contract §5/§8A "factual counts")
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadOrganizationCounts:
    new_unread: int
    unassigned: int
    follow_up_due: int
    follow_up_overdue: int


_SELECT_COUNTS = """
SELECT
    COUNT(*) FILTER (
        WHERE COALESCE(los.operational_status, 'NEW') = 'NEW'
          AND COALESCE(los.is_unread, TRUE) = TRUE
    ) AS new_unread,
    COUNT(*) FILTER (WHERE los.assigned_account_id IS NULL) AS unassigned,
    COUNT(*) FILTER (
        WHERE los.follow_up_due_at IS NOT NULL AND los.follow_up_due_at <= %(as_of)s
    ) AS follow_up_due,
    COUNT(*) FILTER (
        WHERE los.follow_up_due_at IS NOT NULL AND los.follow_up_due_at < %(as_of)s
    ) AS follow_up_overdue
FROM buyer_leads bl
LEFT JOIN lead_operational_state los ON los.lead_id = bl.lead_id
WHERE bl.publishing_organization_id = %(organization_id)s
"""


def fetch_organization_lead_counts(
    conn: Any, organization_id: MarketplaceOrganizationId, *, as_of: datetime
) -> LeadOrganizationCounts:
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_COUNTS, {"organization_id": organization_id.value, "as_of": as_of})
        row = cur.fetchone()
    assert row is not None
    return LeadOrganizationCounts(
        new_unread=row[0], unassigned=row[1], follow_up_due=row[2], follow_up_overdue=row[3]
    )
