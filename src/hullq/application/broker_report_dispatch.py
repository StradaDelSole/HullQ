"""Broker periodic performance report dispatch worker — SLICE-0089.

One deterministic worker-tick callable
(`run_report_dispatch_worker_once`) that:

1. admits at most one newly-due PeriodRun across a bounded batch of
   ACTIVE subscriptions (idempotent -- a repeated/concurrent tick that
   finds the period already admitted does nothing further for it);
2. claims and attempts delivery of at most one currently deliverable
   PeriodRun, re-checking the Organization's *current* subscription
   revision/status AND the configuring account's current authorization
   immediately before sending, so an opt-out/recipient change/
   deactivation/membership-revocation between generation and dispatch
   suppresses delivery rather than sending to a stale/unauthorized
   target.

Mirrors (but never shares identity/state with) the accepted SLICE-0071
`hullq.application.lead_notification_delivery` retry-worker pattern,
including its documented discipline: a read-only query sequence must be
explicitly `conn.commit()`-ed before any function that opens its own
`with conn.transaction():`, so that call performs a real top-level commit
rather than silently degrading to a nested SAVEPOINT that never reaches
other connections.

Amendment (independent review round 1):

Finding A -- claims carry a bounded lease and a fencing `claim_generation`
token (`hullq.persistence.broker_report_subscription`); a reclaimed row
gets an explicit audit entry before any new delivery attempt, and every
`send` call is given a durable `provider_idempotency_key` a future real
provider can use for its own dedup.

Finding B/C -- admission is a single explicit `REPEATABLE READ`
transaction per candidate Organization: it locks that Organization's
subscription row, reads a genuinely consistent snapshot of the SLICE-0075
facts, inserts the PeriodRun and advances the durable admission cursor
all atomically. The admission scan itself is bounded
(`MAX_ADMISSION_SCAN_ORGANIZATIONS`), and per-listing rows are bounded
and *honestly* disclosed as truncated in the stored `facts_json` itself
(not only in a separate, easily-forgotten column) -- aggregate totals are
never truncated.

Finding D -- dispatch re-verifies that the account which configured the
*current* subscription revision is still a currently ACTIVE OWNER/ADMIN
member of the Organization (and that the Organization itself still
exists) before sending -- offboarding/revocation during the window
between generation and dispatch suppresses delivery.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from psycopg.errors import SerializationFailure

from hullq.application.broker_report_rendering import render_report_html
from hullq.domain.broker_report_subscription import (
    DEFAULT_CLAIM_LEASE_SECONDS,
    MAX_ADMISSION_SCAN_ORGANIZATIONS,
    MAX_REPORT_LISTING_ROWS,
    ReportDeliveryAttemptOutcome,
    SubscriptionStatus,
    next_period_bounds,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
)
from hullq.persistence.broker_identity import (
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.broker_performance import fetch_organization_performance_facts
from hullq.persistence.broker_report_subscription import (
    advance_subscription_cursor,
    claim_next_deliverable_period_run,
    fetch_last_admitted_period_index,
    fetch_subscription,
    insert_period_run,
    record_delivery_attempt,
    record_reclaim_event,
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
    retention (existing code/reuse contract). *idempotency_key* (Finding
    A) is a durable per-PeriodRun identity a real provider should use for
    its own dedup; this module never claims its own send is exactly-once."""

    def send(
        self, *, to_email: str, subject: str, body: str, idempotency_key: str
    ) -> DeliverySendResult: ...


@dataclass(frozen=True)
class SentReport:
    to_email: str
    subject: str
    body: str
    idempotency_key: str


@dataclass
class DeterministicLocalReportDeliveryAdapter:
    """Deterministic local/test delivery adapter. No real email provider
    credentials are referenced anywhere in this module (contract: "0089
    does NOT claim production email activation")."""

    sent: list[SentReport] = field(default_factory=list)
    _queued_outcomes: list[DeliverySendResult] = field(default_factory=list)

    def queue_outcome(self, result: DeliverySendResult) -> None:
        self._queued_outcomes.append(result)

    def send(
        self, *, to_email: str, subject: str, body: str, idempotency_key: str
    ) -> DeliverySendResult:
        self.sent.append(
            SentReport(
                to_email=to_email, subject=subject, body=body, idempotency_key=idempotency_key
            )
        )
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
    RECIPIENT_UNAUTHORIZED = "RECIPIENT_UNAUTHORIZED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


@dataclass(frozen=True)
class ReportWorkerTickResult:
    admission: AdmissionOutcome
    admitted_period_run_id: str | None
    delivery: DeliveryOutcome
    delivered_period_run_id: str | None
    was_reclaimed: bool = False


_SELECT_ACTIVE_SUBSCRIPTIONS = """
SELECT organization_id, period_kind, next_period_start, revision, recipient_email
FROM organization_report_subscription
WHERE status = 'ACTIVE' AND recipient_email IS NOT NULL AND next_period_start IS NOT NULL
ORDER BY organization_id ASC
LIMIT %s
"""


def _admit_next_due_period(conn: Any, *, as_of: datetime) -> str | None:
    """Scan a bounded batch of ACTIVE subscriptions (deterministic order)
    and admit the first one with a newly-closed, not-yet-admitted period.

    Each candidate Organization's admission (Finding B/C) runs inside one
    explicit `REPEATABLE READ` transaction: it locks that Organization's
    own subscription row (`fetch_subscription(..., for_update=True)`),
    which (a) serializes a concurrent admission attempt for the *same*
    Organization against this one, and (b) means every statement from
    that point on sees one single consistent snapshot -- the SLICE-0075
    facts read is no longer a same-looking-but-unrelated sequence of
    separate reads. The PeriodRun insert and the cursor advance commit
    together with that same snapshot, atomically.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_ACTIVE_SUBSCRIPTIONS, [MAX_ADMISSION_SCAN_ORGANIZATIONS])
        candidate_org_ids = [MarketplaceOrganizationId(row[0]) for row in cur.fetchall()]
    conn.commit()  # end that read before any per-candidate explicit transaction below.

    for organization_id in candidate_org_ids:
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                subscription = fetch_subscription(conn, organization_id, for_update=True)
                if (
                    subscription.status is not SubscriptionStatus.ACTIVE
                    or subscription.recipient_email is None
                    or subscription.next_period_start is None
                ):
                    # Changed since the bounded scan above (e.g.
                    # deactivated concurrently) -- this transaction still
                    # committed nothing and holds no lock once it exits;
                    # move on.
                    continue

                candidate_start, candidate_end = next_period_bounds(
                    subscription.next_period_start, subscription.period_kind
                )
                if candidate_end > as_of:
                    continue  # not yet closed -- the outer `with` commits a no-op.

                facts = fetch_organization_performance_facts(
                    conn, organization_id, window_start=candidate_start, window_end=candidate_end
                )
                facts_dict = facts.to_public_dict()
                listings = facts_dict["listings"]
                listings_truncated = len(listings) > MAX_REPORT_LISTING_ROWS
                if listings_truncated:
                    listings = listings[:MAX_REPORT_LISTING_ROWS]
                # Finding C: the truncation flag must travel *inside* the
                # stored snapshot itself -- a sibling DB column alone is
                # not enough, because the renderer only ever sees
                # `facts_json`.
                facts_dict["listings"] = listings
                facts_dict["listings_truncated"] = listings_truncated

                next_index = (fetch_last_admitted_period_index(conn, organization_id) or -1) + 1
                with conn.cursor() as cur:
                    period_run_id = insert_period_run(
                        cur,
                        organization_id=organization_id,
                        period_index=next_index,
                        period_kind=subscription.period_kind,
                        period_start=candidate_start,
                        period_end=candidate_end,
                        subscription_revision=subscription.revision,
                        recipient_email=subscription.recipient_email,
                        facts=facts_dict,
                        listings_truncated=listings_truncated,
                        generated_at=as_of,
                    )
                    if period_run_id is not None:
                        advance_subscription_cursor(
                            cur, organization_id, next_period_start=candidate_end
                        )
                if period_run_id is not None:
                    return period_run_id
                # A concurrent tick already admitted this exact window
                # under a lock we could not have raced past (the FOR
                # UPDATE above serializes same-Organization admitters) --
                # defensive only.
                continue
        except SerializationFailure:
            # Postgres's expected REPEATABLE READ outcome when a
            # concurrent transaction committed a conflicting update to
            # this exact locked row while we were blocked on it -- this
            # candidate lost the race this tick; a later tick (by this or
            # another worker) will pick up whatever is actually still due.
            # The `with conn.transaction():` block's own `__exit__` has
            # already rolled back before this `except` runs.
            continue

    return None


def _recipient_authorization_ok(
    conn: Any, organization_id: MarketplaceOrganizationId, updated_by_account_id: AccountId | None
) -> bool:
    """Finding D: the account that configured the *current* subscription
    revision must still be a currently ACTIVE OWNER/ADMIN member, and the
    Organization itself must still exist. Re-checked fresh at dispatch
    time -- never trusted indefinitely from config-time alone, so
    offboarding/revocation between generation and dispatch is caught."""
    if updated_by_account_id is None:
        return False
    if fetch_marketplace_organization(conn, organization_id) is None:
        return False
    membership = fetch_membership_for_account_and_organization(
        conn, updated_by_account_id, organization_id
    )
    if membership is None or membership.state is not MembershipState.ACTIVE:
        return False
    return bool(membership.roles & {MembershipRole.OWNER, MembershipRole.ADMIN})


def run_report_dispatch_worker_once(
    conn: Any,
    *,
    adapter: ReportDeliveryPort,
    worker_id: str,
    as_of: datetime,
    retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
    lease_seconds: int = DEFAULT_CLAIM_LEASE_SECONDS,
) -> ReportWorkerTickResult:
    """Perform exactly one admission attempt and one delivery-claim attempt.

    Safe to call repeatedly/concurrently: admission is keyed by the unique
    `(organization_id, period_start, period_end)` PeriodRun constraint
    plus the per-Organization subscription-row lock, and the delivery
    claim uses `FOR UPDATE SKIP LOCKED` with a bounded lease -- two
    concurrent ticks never admit the same period twice or send the same
    PeriodRun twice, and a crashed claimer's row recovers automatically
    once its lease expires (Finding A) instead of staying stuck forever.
    """
    admitted_id = _admit_next_due_period(conn, as_of=as_of)
    admission = (
        AdmissionOutcome.ADMITTED if admitted_id is not None else AdmissionOutcome.NO_DUE_PERIOD
    )

    claim = claim_next_deliverable_period_run(
        conn, worker_id=worker_id, as_of=as_of, lease_seconds=lease_seconds
    )
    if claim is None:
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.NO_ITEM_CLAIMED,
            delivered_period_run_id=None,
        )
    item = claim.record

    if claim.was_reclaimed:
        # Finding A: the prior claimer's lease expired without recording
        # an outcome. Log this explicitly (audit trail for an ambiguous
        # prior attempt) before proceeding -- never silently assume the
        # prior attempt either succeeded or failed.
        record_reclaim_event(conn, item.period_run_id, as_of=as_of)

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
            conn,
            item.period_run_id,
            outcome=ReportDeliveryAttemptOutcome.SUPPRESSED,
            expected_claim_generation=claim.claim_generation,
            as_of=as_of,
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.SUPPRESSED,
            delivered_period_run_id=item.period_run_id,
            was_reclaimed=claim.was_reclaimed,
        )

    if not _recipient_authorization_ok(
        conn, item.organization_id, current_subscription.updated_by_account_id
    ):
        # Finding D: the configuring account's authorization (or the
        # Organization itself) has lapsed since generation -- mechanically
        # distinct from a stale-revision suppression, for a clear audit
        # trail of *why* delivery did not happen.
        record_delivery_attempt(
            conn,
            item.period_run_id,
            outcome=ReportDeliveryAttemptOutcome.RECIPIENT_UNAUTHORIZED,
            expected_claim_generation=claim.claim_generation,
            as_of=as_of,
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.RECIPIENT_UNAUTHORIZED,
            delivered_period_run_id=item.period_run_id,
            was_reclaimed=claim.was_reclaimed,
        )

    org = fetch_marketplace_organization(conn, item.organization_id)
    conn.commit()  # end that read before record_delivery_attempt's own transaction.
    org_display_name = (
        org.resolved_public_display_name if org is not None else item.organization_id.value
    )

    facts = json.loads(item.facts_json)
    body = render_report_html(
        organization_display_name=org_display_name,
        generated_at_iso=as_of.isoformat(),
        facts=facts,
    )
    send_result = adapter.send(
        to_email=item.recipient_email,
        subject="Your HullQ periodic performance report",
        body=body,
        idempotency_key=item.provider_idempotency_key,
    )

    if send_result.outcome is DeliverySendOutcome.SENT:
        record_delivery_attempt(
            conn,
            item.period_run_id,
            outcome=ReportDeliveryAttemptOutcome.DELIVERED,
            expected_claim_generation=claim.claim_generation,
            provider_message_id=send_result.provider_message_id,
            as_of=as_of,
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.DELIVERED,
            delivered_period_run_id=item.period_run_id,
            was_reclaimed=claim.was_reclaimed,
        )

    if (
        send_result.outcome is DeliverySendOutcome.RETRYABLE_ERROR
        and (item.attempt_count + 1) < MAX_DELIVERY_ATTEMPTS
    ):
        record_delivery_attempt(
            conn,
            item.period_run_id,
            outcome=ReportDeliveryAttemptOutcome.RETRYABLE_FAILURE,
            expected_claim_generation=claim.claim_generation,
            error_text=send_result.error_text,
            next_attempt_at=as_of + timedelta(seconds=retry_backoff_seconds),
            as_of=as_of,
        )
        return ReportWorkerTickResult(
            admission=admission,
            admitted_period_run_id=admitted_id,
            delivery=DeliveryOutcome.RETRYABLE_FAILURE,
            delivered_period_run_id=item.period_run_id,
            was_reclaimed=claim.was_reclaimed,
        )

    record_delivery_attempt(
        conn,
        item.period_run_id,
        outcome=ReportDeliveryAttemptOutcome.TERMINAL_FAILURE,
        expected_claim_generation=claim.claim_generation,
        error_text=send_result.error_text,
        as_of=as_of,
    )
    return ReportWorkerTickResult(
        admission=admission,
        admitted_period_run_id=admitted_id,
        delivery=DeliveryOutcome.TERMINAL_FAILURE,
        delivered_period_run_id=item.period_run_id,
        was_reclaimed=claim.was_reclaimed,
    )
