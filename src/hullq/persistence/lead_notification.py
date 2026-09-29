"""Broker Lead notification recipient config + durable outbox — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§9/§10/§12: Organization-level primary Lead-notification email
administration (optimistic-concurrency, OWNER/ADMIN-gated at the
application layer -- this module enforces no role check itself) and the
durable per-Lead notification outbox, including the claim/attempt-record
functions the retry worker uses.

`insert_pending_notification_intent` is deliberately a bare cursor function
(not a `conn`-owning one): it exists to be called from *inside*
`hullq.persistence.buyer_lead.create_buyer_lead`'s own transaction
immediately after a Lead row is durably inserted, so Lead creation and its
required notification intent commit atomically or not at all (contract §10/
mandatory invariant 10). It must never open, commit or roll back a
transaction itself.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.buyer_lead import ContactEmailVerificationState, LeadId
from hullq.domain.lead_notification import NotificationDeliveryStatus
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "MAX_BUYER_MESSAGE_EXCERPT_LENGTH",
    "DeliveryAttemptOutcome",
    "NotificationConfigRecord",
    "NotificationOutboxRecord",
    "SetNotificationConfigResult",
    "claim_next_deliverable_outbox_item",
    "fetch_notification_outbox_by_lead",
    "fetch_organization_notification_config",
    "insert_pending_notification_intent",
    "record_delivery_attempt",
    "requeue_due_retryable_items",
    "set_organization_notification_email",
]

#: Bounded excerpt carried on the outbox row for rendering (contract §11:
#: "bounded message excerpt or full bounded message if safe"). The outbox
#: row is immutable rendering context, not a second buyer-message store, so
#: this stays well inside `buyer_lead.MAX_BUYER_MESSAGE_LENGTH`.
MAX_BUYER_MESSAGE_EXCERPT_LENGTH = 1000


# ---------------------------------------------------------------------------
# Notification recipient configuration (contract §9)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationConfigRecord:
    """Current Organization Lead-notification recipient configuration.

    Absence of a durable row is represented as `notification_email=None`,
    `version=0` -- the same default state a first-ever mutation must target
    with `expected_version=0`.
    """

    organization_id: MarketplaceOrganizationId
    notification_email: str | None
    version: int


class NotificationConfigConflictError(RuntimeError):
    """*expected_version* no longer matches the current durable version."""


_SELECT_NOTIFICATION_CONFIG = (
    "SELECT notification_email, version FROM organization_lead_notification_config "
    "WHERE organization_id = %s"
)

_BOOTSTRAP_NOTIFICATION_CONFIG = """
INSERT INTO organization_lead_notification_config (organization_id, version)
VALUES (%s, 0)
ON CONFLICT (organization_id) DO NOTHING
"""

_UPDATE_NOTIFICATION_CONFIG = """
UPDATE organization_lead_notification_config
SET notification_email = %s, updated_by_account_id = %s, updated_at = NOW(), version = version + 1
WHERE organization_id = %s AND version = %s
RETURNING version
"""


def fetch_organization_notification_config(
    conn: Any, organization_id: MarketplaceOrganizationId
) -> NotificationConfigRecord:
    """Read current notification-recipient configuration, or the implicit
    absent-config default (`notification_email=None`, `version=0`)."""
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "organization_id must be a MarketplaceOrganizationId, "
            f"got {type(organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_NOTIFICATION_CONFIG, [organization_id.value])
        row = cur.fetchone()
    if row is None:
        return NotificationConfigRecord(
            organization_id=organization_id, notification_email=None, version=0
        )
    return NotificationConfigRecord(
        organization_id=organization_id, notification_email=row[0], version=row[1]
    )


@dataclass(frozen=True)
class SetNotificationConfigResult:
    """`updated=False` means *expected_version* was stale; the caller must
    re-read current state before retrying -- no silent overwrite."""

    updated: bool
    current: NotificationConfigRecord


def set_organization_notification_email(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    notification_email: str | None,
    updated_by_account_id: AccountId,
    expected_version: int,
) -> SetNotificationConfigResult:
    """Create/change/clear the primary Lead-notification email.

    Authorization (current ACTIVE OWNER/ADMIN, contract §9) is the
    application layer's responsibility -- this function performs no role
    check. *notification_email* must already be normalized/validated by the
    caller (`hullq.domain.lead_notification.normalize_notification_recipient_email`)
    or explicitly `None` to clear it. Optimistic concurrency: the row is
    bootstrapped into existence first (idempotent), then updated only if
    *expected_version* still matches the current durable version.
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "organization_id must be a MarketplaceOrganizationId, "
            f"got {type(organization_id).__name__}"
        )
    if not isinstance(updated_by_account_id, AccountId):
        raise TypeError(
            f"updated_by_account_id must be an AccountId, got {type(updated_by_account_id).__name__}"
        )
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_BOOTSTRAP_NOTIFICATION_CONFIG, [organization_id.value])
        cur.execute(
            _UPDATE_NOTIFICATION_CONFIG,
            [notification_email, updated_by_account_id.value, organization_id.value, expected_version],
        )
        updated_row = cur.fetchone()
        if updated_row is None:
            current = fetch_organization_notification_config(conn, organization_id)
            return SetNotificationConfigResult(updated=False, current=current)
        return SetNotificationConfigResult(
            updated=True,
            current=NotificationConfigRecord(
                organization_id=organization_id,
                notification_email=notification_email,
                version=updated_row[0],
            ),
        )


# ---------------------------------------------------------------------------
# Durable outbox (contract §10/§12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationOutboxRecord:
    """Exact typed readback of one Lead's durable notification intent."""

    outbox_id: str
    lead_id: LeadId
    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    buyer_name: str
    buyer_email: str
    contact_email_verification_state: ContactEmailVerificationState
    buyer_message_excerpt: str
    status: NotificationDeliveryStatus
    attempt_count: int
    provider_message_id: str | None
    delivered_at: datetime | None


_INSERT_NOTIFICATION_INTENT = """
INSERT INTO lead_notification_outbox (
    outbox_id, lead_id, native_listing_id, publishing_organization_id,
    buyer_name, buyer_email, contact_email_verification_state, buyer_message_excerpt, status
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (lead_id) DO NOTHING
"""

_SELECT_OUTBOX_BY_LEAD = """
SELECT outbox_id, lead_id, native_listing_id, publishing_organization_id, buyer_name,
       buyer_email, contact_email_verification_state, buyer_message_excerpt, status,
       attempt_count, provider_message_id, delivered_at
FROM lead_notification_outbox WHERE lead_id = %s
"""


def insert_pending_notification_intent(
    cur: Any,
    *,
    lead_id: LeadId,
    native_listing_id: NativeListingId,
    publishing_organization_id: MarketplaceOrganizationId,
    buyer_name: str,
    buyer_email: str,
    contact_email_verification_state: ContactEmailVerificationState,
    buyer_message: str,
) -> None:
    """Insert one durable `PENDING` notification intent for a just-created
    Lead, using the caller's own open cursor/transaction.

    Called exactly once, from inside `create_buyer_lead`'s CREATED branch
    (contract §10's atomicity requirement) -- never given its own
    transaction here. `ON CONFLICT (lead_id) DO NOTHING` makes this safe to
    call defensively; the caller's own submission-operation-id idempotency
    check already ensures a genuinely new Lead calls this at most once.
    """
    excerpt = buyer_message[:MAX_BUYER_MESSAGE_EXCERPT_LENGTH]
    cur.execute(
        _INSERT_NOTIFICATION_INTENT,
        (
            str(uuid.uuid4()),
            lead_id.value,
            native_listing_id.value,
            publishing_organization_id.value,
            buyer_name,
            buyer_email,
            contact_email_verification_state.value,
            excerpt,
            NotificationDeliveryStatus.PENDING.value,
        ),
    )


def fetch_notification_outbox_by_lead(
    conn: Any, lead_id: LeadId
) -> NotificationOutboxRecord | None:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.cursor() as cur:
        cur.execute(_SELECT_OUTBOX_BY_LEAD, [lead_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return NotificationOutboxRecord(
        outbox_id=row[0],
        lead_id=LeadId(row[1]),
        native_listing_id=NativeListingId(row[2]),
        publishing_organization_id=MarketplaceOrganizationId(row[3]),
        buyer_name=row[4],
        buyer_email=row[5],
        contact_email_verification_state=ContactEmailVerificationState(row[6]),
        buyer_message_excerpt=row[7],
        status=NotificationDeliveryStatus(row[8]),
        attempt_count=row[9],
        provider_message_id=row[10],
        delivered_at=row[11],
    )


# ---------------------------------------------------------------------------
# Retry / claim worker support (contract §12)
# ---------------------------------------------------------------------------


class DeliveryAttemptOutcome:
    """Mechanically distinct worker-observed attempt outcomes."""

    DELIVERED = "DELIVERED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    NO_RECIPIENT_CONFIGURED = "NO_RECIPIENT_CONFIGURED"


#: `FOR UPDATE SKIP LOCKED` (contract §12: "concurrent workers cannot both
#: own/send the same attempt") handles two concurrent claimers racing for
#: the *same* row while both transactions are still open. That alone is not
#: sufficient: claiming does not change `status` away from `'PENDING'`, so
#: once the claiming transaction commits, a *later* claim query would
#: re-select the identical already-claimed row unless it also excludes rows
#: with a non-null `claimed_at` -- this is what actually prevents a second
#: worker from claiming a row the first worker already claimed and is still
#: (or has already finished) processing.
_CLAIM_NEXT_ITEM = """
SELECT outbox_id, lead_id, native_listing_id, publishing_organization_id, buyer_name,
       buyer_email, contact_email_verification_state, buyer_message_excerpt, status,
       attempt_count, provider_message_id, delivered_at
FROM lead_notification_outbox
WHERE status = 'PENDING' AND claimed_at IS NULL AND next_attempt_at <= %s
ORDER BY next_attempt_at ASC, outbox_id ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
"""

_MARK_CLAIMED = (
    "UPDATE lead_notification_outbox SET claimed_by = %s, claimed_at = %s, updated_at = NOW() "
    "WHERE outbox_id = %s"
)

_INSERT_DELIVERY_ATTEMPT = (
    "INSERT INTO lead_notification_delivery_attempts "
    "(attempt_id, outbox_id, attempted_at, outcome, provider_message_id, error_text) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)

_RECORD_DELIVERED = """
UPDATE lead_notification_outbox
SET status = 'DELIVERED', attempt_count = attempt_count + 1, provider_message_id = %s,
    delivered_at = %s, updated_at = NOW(), version = version + 1
WHERE outbox_id = %s
"""

_RECORD_NO_RECIPIENT = """
UPDATE lead_notification_outbox
SET status = 'NO_RECIPIENT_CONFIGURED', attempt_count = attempt_count + 1, updated_at = NOW(),
    version = version + 1
WHERE outbox_id = %s
"""

_RECORD_RETRYABLE_FAILURE = """
UPDATE lead_notification_outbox
SET status = 'FAILED_RETRYABLE', attempt_count = attempt_count + 1, last_error = %s,
    next_attempt_at = %s, updated_at = NOW(), version = version + 1
WHERE outbox_id = %s
"""

_RECORD_TERMINAL_FAILURE = """
UPDATE lead_notification_outbox
SET status = 'FAILED_TERMINAL', attempt_count = attempt_count + 1, last_error = %s,
    updated_at = NOW(), version = version + 1
WHERE outbox_id = %s
"""

_RETRY_FAILED_RETRYABLE = """
UPDATE lead_notification_outbox
SET status = 'PENDING', claimed_by = NULL, claimed_at = NULL, updated_at = NOW(), version = version + 1
WHERE status = 'FAILED_RETRYABLE' AND next_attempt_at <= %s
"""


def _row_to_record(row: Any) -> NotificationOutboxRecord:
    return NotificationOutboxRecord(
        outbox_id=row[0],
        lead_id=LeadId(row[1]),
        native_listing_id=NativeListingId(row[2]),
        publishing_organization_id=MarketplaceOrganizationId(row[3]),
        buyer_name=row[4],
        buyer_email=row[5],
        contact_email_verification_state=ContactEmailVerificationState(row[6]),
        buyer_message_excerpt=row[7],
        status=NotificationDeliveryStatus(row[8]),
        attempt_count=row[9],
        provider_message_id=row[10],
        delivered_at=row[11],
    )


def requeue_due_retryable_items(conn: Any, *, as_of: datetime) -> None:
    """Move every `FAILED_RETRYABLE` item whose `next_attempt_at` has
    elapsed back to `PENDING` so the claim query can pick it up again
    (contract §12: "FAILED_RETRYABLE may become PENDING/claimed again under
    bounded retry policy"). Safe to call repeatedly; touches only rows
    already due."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_RETRY_FAILED_RETRYABLE, [as_of])


def claim_next_deliverable_outbox_item(
    conn: Any, *, worker_id: str, as_of: datetime
) -> NotificationOutboxRecord | None:
    """Claim (and commit the claim for) exactly one due `PENDING` outbox
    row, or `None` if none is currently claimable.

    Uses `SELECT ... FOR UPDATE SKIP LOCKED` inside its own short
    transaction so two concurrent workers can never claim the same row
    (contract §12). The claim is committed immediately (separate from the
    eventual delivery-result commit performed by `record_delivery_attempt`)
    so a worker crash between claim and delivery-result leaves a
    recoverable row: it stays `PENDING`/claimed and can be claimed again by
    the same or another worker once its own crash-recovery policy revisits
    it (v0.1 has no claim-staleness sweep; exact scheduling is
    implementation-local per contract §12).
    """
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_CLAIM_NEXT_ITEM, [as_of])
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute(_MARK_CLAIMED, [worker_id, as_of, row[0]])
    return _row_to_record(row)


def record_delivery_attempt(
    conn: Any,
    outbox_id: str,
    *,
    outcome: str,
    provider_message_id: str | None = None,
    error_text: str | None = None,
    next_attempt_at: datetime | None = None,
    as_of: datetime,
) -> None:
    """Durably record one delivery attempt and transition the outbox row.

    `outcome` is one of `DeliveryAttemptOutcome`'s four values. `DELIVERED`
    is terminal/idempotent (contract §12); a `RETRYABLE_FAILURE` requires
    *next_attempt_at* for the next eligible retry.
    """
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_DELIVERY_ATTEMPT,
            (str(uuid.uuid4()), outbox_id, as_of, outcome, provider_message_id, error_text),
        )
        if outcome == DeliveryAttemptOutcome.DELIVERED:
            cur.execute(_RECORD_DELIVERED, [provider_message_id, as_of, outbox_id])
        elif outcome == DeliveryAttemptOutcome.NO_RECIPIENT_CONFIGURED:
            cur.execute(_RECORD_NO_RECIPIENT, [outbox_id])
        elif outcome == DeliveryAttemptOutcome.RETRYABLE_FAILURE:
            if next_attempt_at is None:
                raise ValueError("next_attempt_at is required for a RETRYABLE_FAILURE outcome")
            cur.execute(_RECORD_RETRYABLE_FAILURE, [error_text, next_attempt_at, outbox_id])
        elif outcome == DeliveryAttemptOutcome.TERMINAL_FAILURE:
            cur.execute(_RECORD_TERMINAL_FAILURE, [error_text, outbox_id])
        else:
            raise ValueError(f"unknown delivery attempt outcome: {outcome!r}")
