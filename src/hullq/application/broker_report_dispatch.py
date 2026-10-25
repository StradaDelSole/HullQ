"""Broker periodic performance report dispatch worker — SLICE-0089.

One deterministic worker-tick callable
(`run_report_dispatch_worker_once`) that:

1. admits at most one newly-due PeriodRun across all ACTIVE subscriptions
   (idempotent -- a repeated/concurrent tick that finds the period already
   admitted does nothing further for it);
2. claims and attempts delivery of at most one currently deliverable
   PeriodRun, re-checking the Organization's *current* subscription
   revision/status immediately before sending so an opt-out/recipient
   change/deactivation between generation and dispatch suppresses delivery
   rather than sending to a stale target.

Mirrors (but never shares identity/state with) the accepted SLICE-0071
`hullq.application.lead_notification_delivery` retry-worker pattern,
including its documented discipline: a read-only query sequence must be
explicitly `conn.commit()`-ed before any function that opens its own
`with conn.transaction():`, so that call performs a real top-level commit
rather than silently degrading to a nested SAVEPOINT that never reaches
other connections.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from hullq.application.broker_report_rendering import render_report_html
from hullq.domain.broker_report_subscription import (
    MAX_REPORT_LISTING_ROWS,
    ReportDeliveryAttemptOutcome,
    ReportPeriodKind,
    SubscriptionStatus,
    next_due_period_index,
    period_bounds,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.broker_identity import fetch_marketplace_organization
from hullq.persistence.broker_performance import fetch_organization_performance_facts
from hullq.persistence.broker_report_subscription import (
    claim_next_deliverable_period_run,
    fetch_last_admitted_period_index,
    fetch_subscription,
    insert_period_run,
    record_delivery_attempt,
)

__all__ = [
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "MAX_DELIVERY_ATTEMPTS",
    "AdmissionOutcome",
    "DeliveryOutcome",
    "DeliverySendOutcome",
    "DeliverySendResult",
    "DeterministicLocalReportDeliveryAdapter",
    "ReportDeliveryPort",
    "ReportWorkerTickResult",
    "SentReport",
    "run_report_dispatch_worker_once",
]

#: Exact scheduling/backoff values are implementation-local (mirrors
#: SLICE-0071 contract §12).
DEFAULT_RETRY_BACKOFF_SECONDS = 300

#: Bounded retry policy: after this many recorded attempts, a would-be-
#: retryable failure is instead recorded `FAILED_TERMINAL`.
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


class ReportDeliveryPort(Protocol):
    """Application port every delivery adapter (local/test or a later
    production-provider adapter) must implement. Independent from
    `hullq.application.lead_notification_delivery.NotificationDeliveryPort`
    -- a report delivery job must have its own idempotency key, state and
    retention (existing code/reuse contract)."""

    def send(self, *, to_email: str, subject: str, body: str) -> DeliverySendResult: ...


@dataclass(frozen=True)
class SentReport:
    to_email: str
    subject: str
    body: str


@dataclass
class DeterministicLocalReportDeliveryAdapter:
    """Deterministic local/test delivery adapter. No real email provider
    credentials are referenced anywhere in this module (contract: "0089
    does NOT claim production email activation")."""

    sent: list[SentReport] = field(default_factory=list)
    _queued_outcomes: list[DeliverySendResult] = field(default_factory=list)

    def queue_outcome(self, result: DeliverySendResult) -> None:
        self._queued_outcomes.append(result)

    def send(self, *, to_email: str, subject: str, body: str) -> DeliverySendResult:
        self.sent.append(SentReport(to_email=to_email, subject=subject, body=body))
        if self._queued_outcomes:
            return self._queued_outcomes.pop(0)
        return DeliverySendResult(
            outcome=DeliverySendOutcome.SENT, provider_message_id=str(uuid.uuid4())
        )


class AdmissionOutcome(StrEnum):
    ADMITTED = "ADMITTED"
    NO_DUE_PERIOD = "NO_DUE_PERIOD"


class DeliveryOutcome(StrEnum):
    NO_ITEM_CLAIMED = "NO_ITEM_CLAIMED"
    DELIVERED = "DELIVERED"
    SUPPRESSED = "SUPPRESSED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


@dataclass(frozen=True)
class ReportWorkerTickResult:
    admission: AdmissionOutcome
    admitted_period_run_id: str | None
    delivery: DeliveryOutcome
    delivered_period_run_id: str | None


_SELECT_ACTIVE_SUBSCRIPTIONS = """
SELECT organization_id, period_kind, anchor_date, revision, recipient_email
FROM organization_report_subscription
WHERE status = 'ACTIVE'
ORDER BY organization_id ASC
"""


def _admit_next_due_period(conn: Any, *, as_of: datetime) -> str | None:
    """Scan every ACTIVE subscription (deterministic order) and admit the
    first one with a newly-closed, not-yet-admitted period.

    Always leaves the connection with no open transaction before
    returning -- either by committing the plain reads below, or by
    delegating to `insert_period_run`'s own top-level
    `with conn.transaction():` after an explicit prior commit.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_ACTIVE_SUBSCRIPTIONS)
        rows = cur.fetchall()

    for organization_id_value, period_kind_value, anchor_date, revision, recipient_email in rows:
        if recipient_email is None:
            continue
        organization_id = MarketplaceOrganizationId(organization_id_value)
        period_kind = ReportPeriodKind(period_kind_value)
        last_index = fetch_last_admitted_period_index(conn, organization_id)
        due_index = next_due_period_index(
            anchor_date, period_kind, last_admitted_index=last_index, as_of=as_of
        )
        if due_index is None:
            continue

        period_start, period_end = period_bounds(anchor_date, period_kind, due_index)
        facts = fetch_organization_performance_facts(
            conn, organization_id, window_start=period_start, window_end=period_end
        )
        facts_dict = facts.to_public_dict()
        listings = facts_dict["listings"]
        listings_truncated = len(listings) > MAX_REPORT_LISTING_ROWS
        if listings_truncated:
            facts_dict["listings"] = listings[:MAX_REPORT_LISTING_ROWS]

        conn.commit()  # end the reads above before insert_period_run's own transaction.
        return insert_period_run(
            conn,
            organization_id=organization_id,
            period_index=due_index,
            period_kind=period_kind,
            period_start=period_start,
            period_end=period_end,
            subscription_revision=revision,
            recipient_email=recipient_email,
            facts=facts_dict,
            listings_truncated=listings_truncated,
            generated_at=as_of,
        )

    conn.commit()  # end the subscriptions read above -- no candidate found this tick.
    return None


def run_report_dispatch_worker_once(
    conn: Any,
    *,
    adapter: ReportDeliveryPort,
    worker_id: str,
    as_of: datetime,
    retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
) -> ReportWorkerTickResult:
    """Perform exactly one admission attempt and one delivery-claim attempt.

    Safe to call repeatedly/concurrently: admission is keyed by the unique
    `(organization_id, period_index)` PeriodRun constraint, and the
    delivery claim uses `FOR UPDATE SKIP LOCKED` -- two concurrent ticks
    never admit the same period twice or send the same PeriodRun twice.
    """
    admitted_id = _admit_next_due_period(conn, as_of=as_of)
    admission = (
        AdmissionOutcome.ADMITTED if admitted_id is not None else AdmissionOutcome.NO_DUE_PERIOD
    )

    item = claim_next_deliverable_period_run(conn, worker_id=worker_id, as_of=as_of)
    if item is None:
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.NO_ITEM_CLAIMED,
            delivered_period_run_id=None,
        )

    current_subscription = fetch_subscription(conn, item.organization_id)
    conn.commit()  # end that read before record_delivery_attempt's own transaction.

    if (
        current_subscription.status is not SubscriptionStatus.ACTIVE
        or current_subscription.revision != item.subscription_revision
    ):
        # Opt-out/recipient change/deactivation between generation and
        # dispatch suppresses delivery (contract) -- never sent to a
        # stale/unauthorized recipient, never silently redirected either.
        record_delivery_attempt(
            conn, item.period_run_id, outcome=ReportDeliveryAttemptOutcome.SUPPRESSED, as_of=as_of
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.SUPPRESSED,
            delivered_period_run_id=item.period_run_id,
        )

    org = fetch_marketplace_organization(conn, item.organization_id)
    conn.commit()  # end that read before record_delivery_attempt's own transaction.
    org_display_name = org.resolved_public_display_name if org is not None else item.organization_id.value

    facts = json.loads(item.facts_json)
    body = render_report_html(
        organization_display_name=org_display_name,
        generated_at_iso=as_of.isoformat(),
        facts=facts,
    )
    send_result = adapter.send(
        to_email=item.recipient_email, subject="Your HullQ periodic performance report", body=body
    )

    if send_result.outcome is DeliverySendOutcome.SENT:
        record_delivery_attempt(
            conn,
            item.period_run_id,
            outcome=ReportDeliveryAttemptOutcome.DELIVERED,
            provider_message_id=send_result.provider_message_id,
            as_of=as_of,
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.DELIVERED,
            delivered_period_run_id=item.period_run_id,
        )

    if (
        send_result.outcome is DeliverySendOutcome.RETRYABLE_ERROR
        and (item.attempt_count + 1) < MAX_DELIVERY_ATTEMPTS
    ):
        record_delivery_attempt(
            conn,
            item.period_run_id,
            outcome=ReportDeliveryAttemptOutcome.RETRYABLE_FAILURE,
            error_text=send_result.error_text,
            next_attempt_at=as_of + timedelta(seconds=retry_backoff_seconds),
            as_of=as_of,
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.RETRYABLE_FAILURE,
            delivered_period_run_id=item.period_run_id,
        )

    record_delivery_attempt(
        conn,
        item.period_run_id,
        outcome=ReportDeliveryAttemptOutcome.TERMINAL_FAILURE,
        error_text=send_result.error_text,
        as_of=as_of,
    )
    return ReportWorkerTickResult(
        admission=admission,
        admitted_period_run_id=admitted_id,
        delivery=DeliveryOutcome.TERMINAL_FAILURE,
        delivered_period_run_id=item.period_run_id,
    )
