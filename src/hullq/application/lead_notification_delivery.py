"""Broker Lead notification delivery port + retry worker — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§11/§12/§12A: HullQ-authored (never buyer-impersonating) email content
behind an application port/interface, plus the claim-and-deliver worker
step that owns retry/failure bookkeeping.

`DeterministicLocalNotificationAdapter` is the "deterministic local/test
adapter" contract §11/§12A accepts as sufficient for 0071 acceptance --
production-provider credentials/activation remain later Production
Readiness work (contract §18 non-goal) and are never referenced here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from hullq.persistence.lead_notification import (
    DeliveryAttemptOutcome,
    NotificationOutboxRecord,
    claim_next_deliverable_outbox_item,
    fetch_organization_notification_config,
    record_delivery_attempt,
    requeue_due_retryable_items,
)

__all__ = [
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "MAX_DELIVERY_ATTEMPTS",
    "DeliverySendOutcome",
    "DeliverySendResult",
    "DeterministicLocalNotificationAdapter",
    "NotificationDeliveryPort",
    "SentNotification",
    "WorkerRunOutcome",
    "WorkerRunResult",
    "render_lead_notification_message",
    "run_delivery_worker_once",
]

#: Contract §12: "Exact scheduling/backoff values are implementation-local."
DEFAULT_RETRY_BACKOFF_SECONDS = 300

#: Bounded retry policy (contract §12): after this many recorded attempts, a
#: would-be-retryable failure is instead recorded `FAILED_TERMINAL` so a
#: persistently failing recipient can never retry forever.
MAX_DELIVERY_ATTEMPTS = 5


class DeliverySendOutcome(StrEnum):
    SENT = "SENT"
    RETRYABLE_ERROR = "RETRYABLE_ERROR"
    TERMINAL_ERROR = "TERMINAL_ERROR"


@dataclass(frozen=True)
class DeliverySendResult:
    outcome: DeliverySendOutcome
    provider_message_id: str | None = None
    error_text: str | None = None


class NotificationDeliveryPort(Protocol):
    """Application port every delivery adapter (local/test or a later
    production-provider adapter) must implement."""

    def send(self, *, to_email: str, subject: str, body: str) -> DeliverySendResult: ...


@dataclass(frozen=True)
class SentNotification:
    to_email: str
    subject: str
    body: str


@dataclass
class DeterministicLocalNotificationAdapter:
    """Deterministic local/test delivery adapter (contract §11/§12A).

    Every "sent" message is recorded in `sent` for retained-proof/test
    inspection. Defaults to always succeeding; a test can push canned
    outcomes via `queue_outcome` to deterministically exercise retry/failure
    behavior without any real network/provider dependency.
    """

    sent: list[SentNotification] = field(default_factory=list)
    _queued_outcomes: list[DeliverySendResult] = field(default_factory=list)

    def queue_outcome(self, result: DeliverySendResult) -> None:
        self._queued_outcomes.append(result)

    def send(self, *, to_email: str, subject: str, body: str) -> DeliverySendResult:
        self.sent.append(SentNotification(to_email=to_email, subject=subject, body=body))
        if self._queued_outcomes:
            return self._queued_outcomes.pop(0)
        return DeliverySendResult(
            outcome=DeliverySendOutcome.SENT, provider_message_id=str(uuid.uuid4())
        )


def render_lead_notification_message(
    record: NotificationOutboxRecord, *, lead_detail_url: str
) -> tuple[str, str]:
    """Render the bounded HullQ-authored notification (contract §11).

    Never impersonates the buyer -- the message is unambiguously *about*
    the buyer, sent *by* HullQ. Carries the explicit VERIFIED/UNVERIFIED
    label (contract §11) and the direct authenticated Lead-detail link, no
    other internal IDs/secrets.
    """
    subject = "New HullQ lead"
    body = (
        "You have a new HullQ lead.\n\n"
        f"Listing: {record.native_listing_id.value}\n"
        f"Buyer: {record.buyer_name} <{record.buyer_email}> "
        f"({record.contact_email_verification_state.value})\n\n"
        f"Message:\n{record.buyer_message_excerpt}\n\n"
        f"View and respond in Broker Workspace: {lead_detail_url}\n"
    )
    return subject, body


class WorkerRunOutcome(StrEnum):
    NO_ITEM_CLAIMED = "NO_ITEM_CLAIMED"
    DELIVERED = "DELIVERED"
    NO_RECIPIENT_CONFIGURED = "NO_RECIPIENT_CONFIGURED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


@dataclass(frozen=True)
class WorkerRunResult:
    outcome: WorkerRunOutcome
    outbox_id: str | None = None


def _lead_detail_url(record: NotificationOutboxRecord, *, web_base_url: str) -> str:
    return (
        f"{web_base_url.rstrip('/')}/broker/organizations/"
        f"{record.publishing_organization_id.value}/leads/{record.lead_id.value}"
    )


def run_delivery_worker_once(
    conn,
    *,
    adapter: NotificationDeliveryPort,
    worker_id: str,
    as_of: datetime,
    web_base_url: str,
    retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
) -> WorkerRunResult:
    """Claim and attempt delivery of exactly one due outbox item.

    Requeues any elapsed `FAILED_RETRYABLE` items to `PENDING` first, then
    claims at most one row via
    `hullq.persistence.lead_notification.claim_next_deliverable_outbox_item`
    (contract §12: "Delivery claims one outbox item safely"). A no-recipient
    Organization records `NO_RECIPIENT_CONFIGURED` and never blocks/loses
    the underlying Lead (contract §10).
    """
    requeue_due_retryable_items(conn, as_of=as_of)
    item = claim_next_deliverable_outbox_item(conn, worker_id=worker_id, as_of=as_of)
    if item is None:
        return WorkerRunResult(outcome=WorkerRunOutcome.NO_ITEM_CLAIMED)

    config = fetch_organization_notification_config(conn, item.publishing_organization_id)
    # That read leaves an implicit transaction open under psycopg's default
    # autocommit=False; end it here so `record_delivery_attempt`'s own
    # `with conn.transaction():` performs a real top-level commit rather
    # than silently degrading to a nested SAVEPOINT (mirrors
    # `hullq.application.broker_inventory_lifecycle`'s identical documented
    # discipline).
    conn.commit()
    if config.notification_email is None:
        record_delivery_attempt(
            conn,
            item.outbox_id,
            outcome=DeliveryAttemptOutcome.NO_RECIPIENT_CONFIGURED,
            as_of=as_of,
        )
        return WorkerRunResult(outcome=WorkerRunOutcome.NO_RECIPIENT_CONFIGURED, outbox_id=item.outbox_id)

    subject, body = render_lead_notification_message(
        item, lead_detail_url=_lead_detail_url(item, web_base_url=web_base_url)
    )
    send_result = adapter.send(to_email=config.notification_email, subject=subject, body=body)

    if send_result.outcome is DeliverySendOutcome.SENT:
        record_delivery_attempt(
            conn,
            item.outbox_id,
            outcome=DeliveryAttemptOutcome.DELIVERED,
            provider_message_id=send_result.provider_message_id,
            as_of=as_of,
        )
        return WorkerRunResult(outcome=WorkerRunOutcome.DELIVERED, outbox_id=item.outbox_id)

    if send_result.outcome is DeliverySendOutcome.RETRYABLE_ERROR and (
        item.attempt_count + 1
    ) < MAX_DELIVERY_ATTEMPTS:
        record_delivery_attempt(
            conn,
            item.outbox_id,
            outcome=DeliveryAttemptOutcome.RETRYABLE_FAILURE,
            error_text=send_result.error_text,
            next_attempt_at=as_of + timedelta(seconds=retry_backoff_seconds),
            as_of=as_of,
        )
        return WorkerRunResult(outcome=WorkerRunOutcome.RETRYABLE_FAILURE, outbox_id=item.outbox_id)

    record_delivery_attempt(
        conn,
        item.outbox_id,
        outcome=DeliveryAttemptOutcome.TERMINAL_FAILURE,
        error_text=send_result.error_text,
        as_of=as_of,
    )
    return WorkerRunResult(outcome=WorkerRunOutcome.TERMINAL_FAILURE, outbox_id=item.outbox_id)
