"""Broker Lead operations orchestration — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§2/§3/§4/§6/§7/§8/§8A/§9: reuses the exact accepted SLICE-0053 Organization
workspace authorization/MFA boundary
(`hullq.application.broker_workspace_read.get_organization_workspace_result`)
for every read/mutation, then re-derives current membership truth fresh
before any tenant-scoped Lead access -- never trusting the session token for
Organization/role claims (mirrors
`hullq.application.broker_inventory_lifecycle`'s identical discipline).

Cross-Organization/unknown Lead access always collapses to the identical
`LEAD_NOT_FOUND` outcome (contract §2: "must collapse to the same
non-enumerating outcome"): a Lead that exists but belongs to a different
Organization is indistinguishable here from a Lead that does not exist at
all.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.buyer_lead import LeadId
from hullq.domain.lead_notification import normalize_notification_recipient_email
from hullq.domain.lead_operations import (
    LeadCloseReason,
    LeadContactAttemptChannel,
    LeadOperationalStatus,
    normalize_lead_note_text,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
)
from hullq.persistence.broker_identity import (
    fetch_active_members_for_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.lead_notification import (
    NotificationConfigRecord,
    fetch_notification_outbox_by_lead,
    set_organization_notification_email,
)
from hullq.persistence.lead_notification import (
    fetch_organization_notification_config as _fetch_notification_config,
)
from hullq.persistence.lead_operations import (
    LeadDetailRecord,
    LeadInboxRow,
    LeadInboxSortKey,
    LeadOperationalStateRecord,
    LeadOrganizationCounts,
    LeadTimelineEventRecord,
    append_lead_contact_attempt,
    append_lead_note,
    fetch_lead_detail,
    fetch_lead_timeline,
    fetch_organization_lead_counts,
    fetch_organization_lead_inbox_page,
    mark_lead_read,
    set_lead_assignment,
    set_lead_follow_up_due_at,
    set_lead_operational_status,
)
from hullq.persistence.lead_provenance import fetch_lead_acquisition_provenance
from hullq.security.session_token import SessionClaims

__all__ = [
    "DEFAULT_INBOX_PAGE_SIZE",
    "MAX_INBOX_PAGE_SIZE",
    "InvalidLeadInboxCursorError",
    "LeadAssignmentCandidate",
    "LeadAssignmentCandidatesResult",
    "LeadInboxFilters",
    "LeadMutationOutcome",
    "LeadMutationResultView",
    "LeadOperationOutcome",
    "LeadOrganizationCountsView",
    "NotificationConfigOutcome",
    "NotificationConfigResultView",
    "append_contact_attempt",
    "append_note",
    "close_lead",
    "get_lead_assignment_candidates",
    "get_lead_detail",
    "get_organization_lead_counts",
    "get_organization_lead_inbox_page",
    "get_organization_notification_config",
    "mark_read",
    "set_assignment",
    "set_follow_up",
    "set_notification_config",
    "set_status",
]

DEFAULT_INBOX_PAGE_SIZE = 50
MAX_INBOX_PAGE_SIZE = 100


class LeadOperationOutcome(StrEnum):
    """Mechanically distinct outcomes shared by every Lead read/mutation."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    LEAD_NOT_FOUND = "LEAD_NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    ASSIGNEE_NOT_ACTIVE_MEMBER = "ASSIGNEE_NOT_ACTIVE_MEMBER"
    INVALID_PAGE_SIZE = "INVALID_PAGE_SIZE"
    INVALID_CURSOR = "INVALID_CURSOR"
    OK = "OK"


# ---------------------------------------------------------------------------
# Shared tenancy re-check
# ---------------------------------------------------------------------------


def _authorize_lead(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId, lead_id: LeadId
) -> tuple[LeadOperationOutcome, LeadDetailRecord | None]:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return LeadOperationOutcome.ORG_NOT_FOUND_OR_DENIED, None
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return LeadOperationOutcome.MFA_REQUIRED, None

    lead = fetch_lead_detail(conn, lead_id)
    if lead is None or lead.publishing_organization_id != organization_id:
        # Contract §2: an existing Lead belonging to a foreign Organization
        # must be indistinguishable from an unknown lead_id.
        return LeadOperationOutcome.LEAD_NOT_FOUND, None
    return LeadOperationOutcome.OK, lead


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadMutationOutcome:
    outcome: LeadOperationOutcome
    state: LeadOperationalStateRecord | None = None

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"status": self.outcome.value}
        if self.state is not None:
            body["operational_state"] = _state_to_dict(self.state)
        return body


LeadMutationResultView = LeadMutationOutcome


def _state_to_dict(state: LeadOperationalStateRecord) -> dict[str, Any]:
    return {
        "operational_status": state.operational_status.value,
        "is_unread": state.is_unread,
        "assigned_account_id": (
            state.assigned_account_id.value if state.assigned_account_id is not None else None
        ),
        "follow_up_due_at": (
            state.follow_up_due_at.isoformat() if state.follow_up_due_at is not None else None
        ),
        "close_reason": state.close_reason.value if state.close_reason is not None else None,
        "version": state.version,
    }


def _timeline_event_to_dict(event: LeadTimelineEventRecord) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "actor_account_id": event.actor_account_id.value,
        "occurred_at": event.occurred_at.isoformat(),
        "note_text": event.note_text,
        "contact_channel": event.contact_channel.value
        if event.contact_channel is not None
        else None,
        "close_reason": event.close_reason.value if event.close_reason is not None else None,
    }


def _lead_detail_to_dict(lead: LeadDetailRecord, *, conn: Any) -> dict[str, Any]:
    outbox = fetch_notification_outbox_by_lead(conn, lead.lead_id)
    provenance = fetch_lead_acquisition_provenance(conn, lead.lead_id)
    timeline = fetch_lead_timeline(conn, lead.lead_id)
    return {
        "lead_id": lead.lead_id.value,
        "native_listing_id": lead.native_listing_id.value,
        "publishing_organization_id": lead.publishing_organization_id.value,
        "buyer_name": lead.buyer_name,
        "buyer_email": lead.buyer_email,
        "contact_email_verification_state": lead.contact_email_verification_state.value,
        "buyer_message": lead.buyer_message,
        "source_channel": lead.source_channel.value,
        "received_at": lead.received_at.isoformat(),
        "operational_state": _state_to_dict(lead.operational_state),
        "notification_delivery": (
            {
                "status": outbox.status.value,
                "attempt_count": outbox.attempt_count,
                "delivered_at": outbox.delivered_at.isoformat() if outbox.delivered_at else None,
            }
            if outbox is not None
            else None
        ),
        "acquisition_provenance": (
            {
                "acquisition_channel": provenance.acquisition_channel.value,
                "utm_source": provenance.utm_source,
                "utm_medium": provenance.utm_medium,
                "utm_campaign": provenance.utm_campaign,
                "utm_term": provenance.utm_term,
                "utm_content": provenance.utm_content,
                "discovery_surface": provenance.discovery_surface.value,
            }
            if provenance is not None
            else None
        ),
        "timeline": [_timeline_event_to_dict(event) for event in timeline],
    }


@dataclass(frozen=True)
class LeadDetailResult:
    outcome: LeadOperationOutcome
    lead: dict[str, Any] | None = None


def get_lead_detail(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId, lead_id: LeadId
) -> LeadDetailResult:
    outcome, lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadDetailResult(outcome=outcome)
    assert lead is not None
    return LeadDetailResult(
        outcome=LeadOperationOutcome.OK, lead=_lead_detail_to_dict(lead, conn=conn)
    )


# ---------------------------------------------------------------------------
# Assignment candidate projection (SLICE-0077 contract §3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadAssignmentCandidate:
    """One current ACTIVE Organization member offered as a Lead assignee.

    `label` is a deterministic, non-deceptive presentation string derived
    only from existing HullQ truth (`account_id` + current roles) --
    contract §3 forbids fabricating email/personal-name/provider-profile
    identity here. The submitted assignment value is always the exact
    `account_id`, never the label.
    """

    account_id: AccountId
    roles: tuple[str, ...]
    label: str

    def to_public_dict(self) -> dict[str, Any]:
        return {"account_id": self.account_id.value, "roles": list(self.roles), "label": self.label}


def _candidate_label(roles: tuple[str, ...], account_id: AccountId) -> str:
    return f"{account_id.value} ({', '.join(roles)})" if roles else account_id.value


@dataclass(frozen=True)
class LeadAssignmentCandidatesResult:
    outcome: LeadOperationOutcome
    candidates: tuple[LeadAssignmentCandidate, ...] | None = None

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"status": self.outcome.value}
        if self.candidates is not None:
            body["candidates"] = [candidate.to_public_dict() for candidate in self.candidates]
        return body


def get_lead_assignment_candidates(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> LeadAssignmentCandidatesResult:
    """Bounded current-ACTIVE-member read backing the Lead assignment picker.

    Reuses the exact Broker Workspace Organization authorization/MFA
    boundary (contract §4): unauthorized/unknown Organization access
    collapses to the identical non-enumerating outcome used everywhere else
    in this module. This projection is convenience/read state only --
    `set_assignment` re-derives current membership fresh at mutation time
    regardless of what this call returned, so a membership change between
    this read and a later assignment attempt still fails closed there.
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return LeadAssignmentCandidatesResult(outcome=LeadOperationOutcome.ORG_NOT_FOUND_OR_DENIED)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return LeadAssignmentCandidatesResult(outcome=LeadOperationOutcome.MFA_REQUIRED)

    memberships = fetch_active_members_for_organization(conn, organization_id)
    candidates = []
    for membership in memberships:
        roles = tuple(sorted(role.value for role in membership.roles))
        candidates.append(
            LeadAssignmentCandidate(
                account_id=membership.account_id,
                roles=roles,
                label=_candidate_label(roles, membership.account_id),
            )
        )
    return LeadAssignmentCandidatesResult(
        outcome=LeadOperationOutcome.OK, candidates=tuple(candidates)
    )


# ---------------------------------------------------------------------------
# Inbox — keyset pagination cursor
# ---------------------------------------------------------------------------


class InvalidLeadInboxCursorError(ValueError):
    """*cursor* is not a validly encoded inbox continuation cursor."""


_CURSOR_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _cursor_b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _cursor_b64url_decode(text: str) -> bytes:
    if not text or not _CURSOR_SEGMENT_RE.fullmatch(text):
        raise InvalidLeadInboxCursorError("cursor is not strict, canonical, unpadded base64url")
    padded = text + ("=" * ((-len(text)) % 4))
    try:
        decoded = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidLeadInboxCursorError("malformed cursor encoding") from exc
    if _cursor_b64url_encode(decoded) != text:
        raise InvalidLeadInboxCursorError(
            "cursor is not the canonical base64url encoding of its bytes"
        )
    return decoded


def _encode_cursor(key: LeadInboxSortKey) -> str:
    payload = {"received_at": key.received_at.isoformat(), "lead_id": key.lead_id.value}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _cursor_b64url_encode(raw)


def _decode_cursor(cursor: str) -> LeadInboxSortKey:
    raw = _cursor_b64url_decode(cursor)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidLeadInboxCursorError("malformed cursor payload") from exc
    if not isinstance(payload, dict):
        raise InvalidLeadInboxCursorError("malformed cursor payload")
    received_at_raw = payload.get("received_at")
    lead_id_raw = payload.get("lead_id")
    if not isinstance(received_at_raw, str) or not received_at_raw:
        raise InvalidLeadInboxCursorError("malformed cursor: received_at")
    if not isinstance(lead_id_raw, str) or not lead_id_raw:
        raise InvalidLeadInboxCursorError("malformed cursor: lead_id")
    try:
        received_at = datetime.fromisoformat(received_at_raw)
    except ValueError as exc:
        raise InvalidLeadInboxCursorError("malformed cursor: received_at") from exc
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise InvalidLeadInboxCursorError("malformed cursor: received_at must be timezone-aware")
    return LeadInboxSortKey(received_at=received_at, lead_id=LeadId(lead_id_raw))


@dataclass(frozen=True)
class LeadInboxFilters:
    status: LeadOperationalStatus | None = None
    assignee_account_id: AccountId | None = None
    unread_only: bool = False
    follow_up_due_before: datetime | None = None


@dataclass(frozen=True)
class LeadInboxPageResult:
    outcome: LeadOperationOutcome
    items: tuple[dict[str, Any], ...] | None = None
    next_cursor: str | None = None


def _inbox_row_to_dict(row: LeadInboxRow) -> dict[str, Any]:
    return {
        "lead_id": row.lead_id.value,
        "native_listing_id": row.native_listing_id.value,
        "buyer_name": row.buyer_name,
        "buyer_email": row.buyer_email,
        "contact_email_verification_state": row.contact_email_verification_state.value,
        "received_at": row.received_at.isoformat(),
        "source_channel": row.source_channel.value,
        "operational_state": _state_to_dict(row.operational_state),
    }


def get_organization_lead_inbox_page(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    page_size: int | None,
    cursor: str | None,
    filters: LeadInboxFilters | None = None,
) -> LeadInboxPageResult:
    filters = filters if filters is not None else LeadInboxFilters()
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return LeadInboxPageResult(outcome=LeadOperationOutcome.ORG_NOT_FOUND_OR_DENIED)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return LeadInboxPageResult(outcome=LeadOperationOutcome.MFA_REQUIRED)

    if page_size is not None and not (1 <= page_size <= MAX_INBOX_PAGE_SIZE):
        return LeadInboxPageResult(outcome=LeadOperationOutcome.INVALID_PAGE_SIZE)
    resolved_page_size = page_size if page_size is not None else DEFAULT_INBOX_PAGE_SIZE

    after: LeadInboxSortKey | None = None
    if cursor is not None:
        try:
            after = _decode_cursor(cursor)
        except InvalidLeadInboxCursorError:
            return LeadInboxPageResult(outcome=LeadOperationOutcome.INVALID_CURSOR)

    rows = fetch_organization_lead_inbox_page(
        conn,
        organization_id,
        limit=resolved_page_size + 1,
        after=after,
        status_filter=filters.status,
        assignee_filter=filters.assignee_account_id,
        unread_only=filters.unread_only,
        follow_up_due_before=filters.follow_up_due_before,
    )
    has_more = len(rows) > resolved_page_size
    page_rows = rows[:resolved_page_size]
    next_cursor = (
        _encode_cursor(
            LeadInboxSortKey(received_at=page_rows[-1].received_at, lead_id=page_rows[-1].lead_id)
        )
        if has_more and page_rows
        else None
    )
    return LeadInboxPageResult(
        outcome=LeadOperationOutcome.OK,
        items=tuple(_inbox_row_to_dict(row) for row in page_rows),
        next_cursor=next_cursor,
    )


@dataclass(frozen=True)
class LeadOrganizationCountsView:
    outcome: LeadOperationOutcome
    counts: LeadOrganizationCounts | None = None

    def to_public_dict(self) -> dict[str, Any]:
        if self.counts is None:
            return {"status": self.outcome.value}
        return {
            "status": self.outcome.value,
            "new_unread": self.counts.new_unread,
            "unassigned": self.counts.unassigned,
            "follow_up_due": self.counts.follow_up_due,
            "follow_up_overdue": self.counts.follow_up_overdue,
        }


def get_organization_lead_counts(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    as_of: datetime,
) -> LeadOrganizationCountsView:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return LeadOrganizationCountsView(outcome=LeadOperationOutcome.ORG_NOT_FOUND_OR_DENIED)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return LeadOrganizationCountsView(outcome=LeadOperationOutcome.MFA_REQUIRED)
    counts = fetch_organization_lead_counts(conn, organization_id, as_of=as_of)
    return LeadOrganizationCountsView(outcome=LeadOperationOutcome.OK, counts=counts)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def mark_read(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    as_of: datetime,
) -> LeadMutationOutcome:
    outcome, _lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadMutationOutcome(outcome=outcome)
    # The authorization reads above leave an implicit read transaction open
    # under psycopg's default autocommit=False; end it here so the
    # persistence mutator's own `with conn.transaction():` performs a real
    # top-level commit rather than silently degrading to a nested SAVEPOINT
    # (mirrors `hullq.application.broker_inventory_lifecycle`'s identical
    # documented discipline).
    conn.commit()
    mark_lead_read(conn, lead_id, actor_account_id=session.account_id, as_of=as_of)
    return LeadMutationOutcome(outcome=LeadOperationOutcome.OK)


def set_assignment(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    assignee_account_id: AccountId | None,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationOutcome:
    outcome, _lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadMutationOutcome(outcome=outcome)

    if assignee_account_id is not None:
        assignee_membership = fetch_membership_for_account_and_organization(
            conn, assignee_account_id, organization_id
        )
        if assignee_membership is None or assignee_membership.state is not MembershipState.ACTIVE:
            return LeadMutationOutcome(outcome=LeadOperationOutcome.ASSIGNEE_NOT_ACTIVE_MEMBER)

    conn.commit()  # end the reads' implicit transaction -- see mark_read's comment above.
    result = set_lead_assignment(
        conn,
        lead_id,
        assignee_account_id=assignee_account_id,
        actor_account_id=session.account_id,
        expected_version=expected_version,
        as_of=as_of,
    )
    if not result.updated:
        return LeadMutationOutcome(
            outcome=LeadOperationOutcome.VERSION_CONFLICT, state=result.current
        )
    return LeadMutationOutcome(outcome=LeadOperationOutcome.OK, state=result.current)


def set_status(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    new_status: LeadOperationalStatus,
    close_reason: LeadCloseReason | None,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationOutcome:
    outcome, _lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadMutationOutcome(outcome=outcome)

    if new_status is LeadOperationalStatus.CLOSED and close_reason is None:
        return LeadMutationOutcome(outcome=LeadOperationOutcome.INVALID_INPUT)
    if new_status is not LeadOperationalStatus.CLOSED and close_reason is not None:
        return LeadMutationOutcome(outcome=LeadOperationOutcome.INVALID_INPUT)

    conn.commit()  # end the reads' implicit transaction -- see mark_read's comment above.
    result = set_lead_operational_status(
        conn,
        lead_id,
        new_status=new_status,
        close_reason=close_reason,
        actor_account_id=session.account_id,
        expected_version=expected_version,
        as_of=as_of,
    )
    if not result.updated:
        return LeadMutationOutcome(
            outcome=LeadOperationOutcome.VERSION_CONFLICT, state=result.current
        )
    return LeadMutationOutcome(outcome=LeadOperationOutcome.OK, state=result.current)


def close_lead(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    close_reason: LeadCloseReason,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationOutcome:
    """Contract §8A: closing always requires a bounded close reason -- this
    is the dedicated close entrypoint FastAPI's close route calls, distinct
    from the general `set_status` so a route can never close without one."""
    return set_status(
        conn,
        session,
        organization_id,
        lead_id,
        new_status=LeadOperationalStatus.CLOSED,
        close_reason=close_reason,
        expected_version=expected_version,
        as_of=as_of,
    )


def set_follow_up(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    due_at: datetime | None,
    expected_version: int,
    as_of: datetime,
) -> LeadMutationOutcome:
    outcome, _lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadMutationOutcome(outcome=outcome)
    conn.commit()  # end the reads' implicit transaction -- see mark_read's comment above.
    result = set_lead_follow_up_due_at(
        conn,
        lead_id,
        due_at=due_at,
        actor_account_id=session.account_id,
        expected_version=expected_version,
        as_of=as_of,
    )
    if not result.updated:
        return LeadMutationOutcome(
            outcome=LeadOperationOutcome.VERSION_CONFLICT, state=result.current
        )
    return LeadMutationOutcome(outcome=LeadOperationOutcome.OK, state=result.current)


def append_note(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    raw_note_text: Any,
    as_of: datetime,
) -> LeadMutationOutcome:
    outcome, _lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadMutationOutcome(outcome=outcome)
    try:
        note_text = normalize_lead_note_text(raw_note_text)
    except TypeError, ValueError:
        return LeadMutationOutcome(outcome=LeadOperationOutcome.INVALID_INPUT)
    conn.commit()  # end the reads' implicit transaction -- see mark_read's comment above.
    append_lead_note(
        conn, lead_id, actor_account_id=session.account_id, note_text=note_text, as_of=as_of
    )
    return LeadMutationOutcome(outcome=LeadOperationOutcome.OK)


def append_contact_attempt(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    lead_id: LeadId,
    *,
    raw_channel: Any,
    raw_note_text: Any,
    as_of: datetime,
) -> LeadMutationOutcome:
    outcome, _lead = _authorize_lead(conn, session, organization_id, lead_id)
    if outcome is not LeadOperationOutcome.OK:
        return LeadMutationOutcome(outcome=outcome)
    try:
        channel = LeadContactAttemptChannel(raw_channel)
    except ValueError:
        return LeadMutationOutcome(outcome=LeadOperationOutcome.INVALID_INPUT)
    note_text: str | None = None
    if raw_note_text is not None:
        try:
            note_text = normalize_lead_note_text(raw_note_text)
        except TypeError, ValueError:
            return LeadMutationOutcome(outcome=LeadOperationOutcome.INVALID_INPUT)
    conn.commit()  # end the reads' implicit transaction -- see mark_read's comment above.
    append_lead_contact_attempt(
        conn,
        lead_id,
        actor_account_id=session.account_id,
        channel=channel,
        note_text=note_text,
        as_of=as_of,
    )
    return LeadMutationOutcome(outcome=LeadOperationOutcome.OK)


# ---------------------------------------------------------------------------
# Notification recipient configuration (contract §9) — OWNER/ADMIN-only write
# ---------------------------------------------------------------------------


class NotificationConfigOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    INVALID_INPUT = "INVALID_INPUT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    OK = "OK"


@dataclass(frozen=True)
class NotificationConfigResultView:
    outcome: NotificationConfigOutcome
    config: NotificationConfigRecord | None = None

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"status": self.outcome.value}
        if self.config is not None:
            body["notification_email"] = self.config.notification_email
            body["version"] = self.config.version
        return body


def get_organization_notification_config(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> NotificationConfigResultView:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return NotificationConfigResultView(
            outcome=NotificationConfigOutcome.ORG_NOT_FOUND_OR_DENIED
        )
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return NotificationConfigResultView(outcome=NotificationConfigOutcome.MFA_REQUIRED)
    config = _fetch_notification_config(conn, organization_id)
    return NotificationConfigResultView(outcome=NotificationConfigOutcome.OK, config=config)


def set_notification_config(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    raw_notification_email: Any,
    expected_version: int,
) -> NotificationConfigResultView:
    """Create/change/clear the Organization's primary Lead-notification
    email. *raw_notification_email* of `None` clears it (contract §9: "may
    be cleared"); any other non-`str` value is `INVALID_INPUT`.

    Contract §2: only a current ACTIVE `OWNER` or `ADMIN` may call this --
    re-derived fresh from persistence, never from the session token.
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return NotificationConfigResultView(
            outcome=NotificationConfigOutcome.ORG_NOT_FOUND_OR_DENIED
        )
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return NotificationConfigResultView(outcome=NotificationConfigOutcome.MFA_REQUIRED)

    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    if membership is None or not (membership.roles & {MembershipRole.OWNER, MembershipRole.ADMIN}):
        return NotificationConfigResultView(outcome=NotificationConfigOutcome.ROLE_REQUIRED)

    if raw_notification_email is None:
        normalized_email: str | None = None
    else:
        try:
            normalized_email = normalize_notification_recipient_email(raw_notification_email)
        except TypeError, ValueError:
            return NotificationConfigResultView(outcome=NotificationConfigOutcome.INVALID_INPUT)

    conn.commit()  # end the reads' implicit transaction -- see mark_read's comment above.
    result = set_organization_notification_email(
        conn,
        organization_id,
        notification_email=normalized_email,
        updated_by_account_id=session.account_id,
        expected_version=expected_version,
    )
    if not result.updated:
        return NotificationConfigResultView(
            outcome=NotificationConfigOutcome.VERSION_CONFLICT, config=result.current
        )
    return NotificationConfigResultView(outcome=NotificationConfigOutcome.OK, config=result.current)
