"""Broker periodic performance report subscription + PeriodRun persistence —
SLICE-0089.

Implements the durable recurrence config, deterministic idempotent period
admission and bounded delivery-claim/retry mechanics described in
`docs/slices/SLICE-0089-broker-periodic-performance-reporting.md`'s
"Periodic delivery / operability" section.

This module performs no tenancy/role authorization itself -- callers
(`hullq.application.broker_report_subscription`,
`hullq.application.broker_report_dispatch`) must have already established
current authorized access before calling anything here. Deliberately a
fully independent table set from SLICE-0071's Lead-notification
outbox/config -- never shares identity, idempotency keys or retention with
it (existing code/reuse contract).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from hullq.domain.broker_report_subscription import (
    PeriodRunStatus,
    ReportDeliveryAttemptOutcome,
    ReportPeriodKind,
    SubscriptionStatus,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "PeriodRunRecord",
    "SetSubscriptionResult",
    "SubscriptionRecord",
    "claim_next_deliverable_period_run",
    "fetch_last_admitted_period_index",
    "fetch_period_run_for_organization",
    "fetch_subscription",
    "insert_period_run",
    "purge_expired_period_runs",
    "record_delivery_attempt",
    "set_subscription",
]


# ---------------------------------------------------------------------------
# Subscription configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubscriptionRecord:
    """Absence of a durable row is the implicit default: `INACTIVE`,
    `MONTHLY`, no recipient, `anchor_date=None`, `revision=0` -- the same
    default state a first-ever `set_subscription` call must target with
    `expected_revision=0`."""

    organization_id: MarketplaceOrganizationId
    status: SubscriptionStatus
    period_kind: ReportPeriodKind
    recipient_email: str | None
    anchor_date: date | None
    revision: int

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "period_kind": self.period_kind.value,
            "recipient_email": self.recipient_email,
            "revision": self.revision,
        }


_SELECT_SUBSCRIPTION = """
SELECT status, period_kind, recipient_email, anchor_date, revision
FROM organization_report_subscription WHERE organization_id = %s
"""

_BOOTSTRAP_SUBSCRIPTION = """
INSERT INTO organization_report_subscription (organization_id, anchor_date)
VALUES (%s, %s)
ON CONFLICT (organization_id) DO NOTHING
"""

_UPDATE_SUBSCRIPTION = """
UPDATE organization_report_subscription
SET status = %s, period_kind = %s, recipient_email = %s, updated_by_account_id = %s,
    updated_at = NOW(), revision = revision + 1
WHERE organization_id = %s AND revision = %s
RETURNING revision, anchor_date
"""


def fetch_subscription(
    conn: Any, organization_id: MarketplaceOrganizationId
) -> SubscriptionRecord:
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_SUBSCRIPTION, [organization_id.value])
        row = cur.fetchone()
    if row is None:
        return SubscriptionRecord(
            organization_id=organization_id,
            status=SubscriptionStatus.INACTIVE,
            period_kind=ReportPeriodKind.MONTHLY,
            recipient_email=None,
            anchor_date=None,
            revision=0,
        )
    return SubscriptionRecord(
        organization_id=organization_id,
        status=SubscriptionStatus(row[0]),
        period_kind=ReportPeriodKind(row[1]),
        recipient_email=row[2],
        anchor_date=row[3],
        revision=row[4],
    )


@dataclass(frozen=True)
class SetSubscriptionResult:
    """`updated=False` means *expected_revision* was stale; the caller must
    re-read current state before retrying -- no silent overwrite."""

    updated: bool
    current: SubscriptionRecord


def set_subscription(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    status: SubscriptionStatus,
    period_kind: ReportPeriodKind,
    recipient_email: str | None,
    updated_by_account_id: AccountId,
    expected_revision: int,
    bootstrap_anchor_date: date,
) -> SetSubscriptionResult:
    """Create/change the Organization's periodic report subscription.

    Authorization (current ACTIVE OWNER/ADMIN) is the application layer's
    responsibility. The row is bootstrapped into existence first
    (idempotent, `anchor_date` fixed forever at first bootstrap -- never
    recomputed by a later mutation, so period boundaries stay stable across
    status/period_kind/recipient changes), then updated only if
    *expected_revision* still matches the current durable revision.
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    if not isinstance(updated_by_account_id, AccountId):
        raise TypeError(
            f"updated_by_account_id must be an AccountId, got {type(updated_by_account_id).__name__}"
        )
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_BOOTSTRAP_SUBSCRIPTION, [organization_id.value, bootstrap_anchor_date])
        cur.execute(
            _UPDATE_SUBSCRIPTION,
            [
                status.value,
                period_kind.value,
                recipient_email,
                updated_by_account_id.value,
                organization_id.value,
                expected_revision,
            ],
        )
        updated_row = cur.fetchone()
        if updated_row is None:
            current = fetch_subscription(conn, organization_id)
            return SetSubscriptionResult(updated=False, current=current)
        return SetSubscriptionResult(
            updated=True,
            current=SubscriptionRecord(
                organization_id=organization_id,
                status=status,
                period_kind=period_kind,
                recipient_email=recipient_email,
                anchor_date=updated_row[1],
                revision=updated_row[0],
            ),
        )


# ---------------------------------------------------------------------------
# PeriodRun admission + delivery claim/retry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeriodRunRecord:
    period_run_id: str
    organization_id: MarketplaceOrganizationId
    period_index: int
    period_kind: ReportPeriodKind
    period_start: datetime
    period_end: datetime
    subscription_revision: int
    recipient_email: str
    status: PeriodRunStatus
    facts_json: str
    listings_truncated: bool
    generated_at: datetime
    attempt_count: int
    provider_message_id: str | None
    delivered_at: datetime | None


_SELECT_LAST_PERIOD_INDEX = """
SELECT MAX(period_index) FROM organization_report_period_run WHERE organization_id = %s
"""

_INSERT_PERIOD_RUN = """
INSERT INTO organization_report_period_run (
    period_run_id, organization_id, period_index, period_kind, period_start, period_end,
    subscription_revision, recipient_email, status, facts_json, listings_truncated, generated_at,
    next_attempt_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (organization_id, period_index) DO NOTHING
RETURNING period_run_id
"""


def fetch_last_admitted_period_index(
    conn: Any, organization_id: MarketplaceOrganizationId
) -> int | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT_LAST_PERIOD_INDEX, [organization_id.value])
        row = cur.fetchone()
    return row[0] if row is not None else None


def insert_period_run(
    conn: Any,
    *,
    organization_id: MarketplaceOrganizationId,
    period_index: int,
    period_kind: ReportPeriodKind,
    period_start: datetime,
    period_end: datetime,
    subscription_revision: int,
    recipient_email: str,
    facts: dict[str, Any],
    listings_truncated: bool,
    generated_at: datetime,
) -> str | None:
    """Admit exactly one new PeriodRun, generated/snapshotted in the same
    step (contract: "a consistent read-only DB snapshot").

    Returns the new `period_run_id`, or `None` if a row for this exact
    `(organization_id, period_index)` already exists -- the unique-key
    admission idempotency that makes repeated/concurrent worker ticks safe
    (`Repeated scheduler ticks do not double send`).
    """
    period_run_id = str(uuid.uuid4())
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_PERIOD_RUN,
            (
                period_run_id,
                organization_id.value,
                period_index,
                period_kind.value,
                period_start,
                period_end,
                subscription_revision,
                recipient_email,
                PeriodRunStatus.GENERATED.value,
                json.dumps(facts),
                listings_truncated,
                generated_at,
                generated_at,
            ),
        )
        row = cur.fetchone()
    return row[0] if row is not None else None


#: `FOR UPDATE SKIP LOCKED` (mirrors `hullq.persistence.lead_notification`'s
#: identical documented discipline): two concurrent claimers racing for the
#: same row while both transactions are open never both win; excluding rows
#: with a non-null `claimed_at` additionally prevents a *later* claim query
#: from re-selecting a row the first worker already claimed and committed.
_CLAIM_NEXT_PERIOD_RUN = """
SELECT period_run_id, organization_id, period_index, period_kind, period_start, period_end,
       subscription_revision, recipient_email, status, facts_json, listings_truncated,
       generated_at, attempt_count, provider_message_id, delivered_at
FROM organization_report_period_run
WHERE status IN ('GENERATED', 'FAILED_RETRYABLE') AND claimed_at IS NULL AND next_attempt_at <= %s
ORDER BY next_attempt_at ASC, period_run_id ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
"""

_MARK_CLAIMED = (
    "UPDATE organization_report_period_run SET claimed_by = %s, claimed_at = %s, updated_at = NOW() "
    "WHERE period_run_id = %s"
)

_INSERT_DELIVERY_ATTEMPT = (
    "INSERT INTO organization_report_delivery_attempts "
    "(attempt_id, period_run_id, attempted_at, outcome, provider_message_id, error_text) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)

_RECORD_DELIVERED = """
UPDATE organization_report_period_run
SET status = 'DELIVERED', attempt_count = attempt_count + 1, provider_message_id = %s,
    delivered_at = %s, updated_at = NOW(), version = version + 1
WHERE period_run_id = %s
"""

_RECORD_RETRYABLE_FAILURE = """
UPDATE organization_report_period_run
SET status = 'FAILED_RETRYABLE', attempt_count = attempt_count + 1, last_error = %s,
    next_attempt_at = %s, claimed_by = NULL, claimed_at = NULL, updated_at = NOW(),
    version = version + 1
WHERE period_run_id = %s
"""

_RECORD_TERMINAL_FAILURE = """
UPDATE organization_report_period_run
SET status = 'FAILED_TERMINAL', attempt_count = attempt_count + 1, last_error = %s,
    updated_at = NOW(), version = version + 1
WHERE period_run_id = %s
"""

_RECORD_SUPPRESSED = """
UPDATE organization_report_period_run
SET status = 'SUPPRESSED', attempt_count = attempt_count + 1, updated_at = NOW(),
    version = version + 1
WHERE period_run_id = %s
"""


def _row_to_period_run(row: Any) -> PeriodRunRecord:
    return PeriodRunRecord(
        period_run_id=row[0],
        organization_id=MarketplaceOrganizationId(row[1]),
        period_index=row[2],
        period_kind=ReportPeriodKind(row[3]),
        period_start=row[4],
        period_end=row[5],
        subscription_revision=row[6],
        recipient_email=row[7],
        status=PeriodRunStatus(row[8]),
        facts_json=row[9],
        listings_truncated=row[10],
        generated_at=row[11],
        attempt_count=row[12],
        provider_message_id=row[13],
        delivered_at=row[14],
    )


def claim_next_deliverable_period_run(
    conn: Any, *, worker_id: str, as_of: datetime
) -> PeriodRunRecord | None:
    """Claim (and commit the claim for) exactly one due claimable PeriodRun
    row, or `None` if none is currently claimable.

    The claim is committed immediately, separate from the eventual
    delivery-result commit performed by `record_delivery_attempt`, so a
    worker crash between claim and delivery-result leaves a recoverable
    row rather than a lost one -- v0.1 has no claim-staleness sweep (exact
    scheduling is implementation-local), mirroring the accepted SLICE-0071
    precedent.
    """
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_CLAIM_NEXT_PERIOD_RUN, [as_of])
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute(_MARK_CLAIMED, [worker_id, as_of, row[0]])
    return _row_to_period_run(row)


def record_delivery_attempt(
    conn: Any,
    period_run_id: str,
    *,
    outcome: ReportDeliveryAttemptOutcome,
    provider_message_id: str | None = None,
    error_text: str | None = None,
    next_attempt_at: datetime | None = None,
    as_of: datetime,
) -> None:
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_DELIVERY_ATTEMPT,
            (str(uuid.uuid4()), period_run_id, as_of, outcome.value, provider_message_id, error_text),
        )
        if outcome is ReportDeliveryAttemptOutcome.DELIVERED:
            cur.execute(_RECORD_DELIVERED, [provider_message_id, as_of, period_run_id])
        elif outcome is ReportDeliveryAttemptOutcome.RETRYABLE_FAILURE:
            if next_attempt_at is None:
                raise ValueError("next_attempt_at is required for a RETRYABLE_FAILURE outcome")
            cur.execute(_RECORD_RETRYABLE_FAILURE, [error_text, next_attempt_at, period_run_id])
        elif outcome is ReportDeliveryAttemptOutcome.TERMINAL_FAILURE:
            cur.execute(_RECORD_TERMINAL_FAILURE, [error_text, period_run_id])
        elif outcome is ReportDeliveryAttemptOutcome.SUPPRESSED:
            cur.execute(_RECORD_SUPPRESSED, [period_run_id])
        else:
            raise ValueError(f"unknown delivery attempt outcome: {outcome!r}")


_SELECT_PERIOD_RUN_FOR_ORG = """
SELECT period_run_id, organization_id, period_index, period_kind, period_start, period_end,
       subscription_revision, recipient_email, status, facts_json, listings_truncated,
       generated_at, attempt_count, provider_message_id, delivered_at
FROM organization_report_period_run
WHERE organization_id = %s AND period_run_id = %s
"""


def fetch_period_run_for_organization(
    conn: Any, organization_id: MarketplaceOrganizationId, period_run_id: str
) -> PeriodRunRecord | None:
    """Org-scoped lookup -- a `period_run_id` belonging to a different
    Organization returns `None`, identical to "never existed" (no report-ID
    enumeration oracle)."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_PERIOD_RUN_FOR_ORG, [organization_id.value, period_run_id])
        row = cur.fetchone()
    return _row_to_period_run(row) if row is not None else None


_DELETE_EXPIRED_PERIOD_RUNS = """
DELETE FROM organization_report_period_run WHERE created_at < %s
"""


def purge_expired_period_runs(conn: Any, *, older_than: timedelta, as_of: datetime) -> int:
    """Bounded archival/purge (failure-mode §"bounded archival/purge"):
    delete every PeriodRun (and, via cascade, its delivery-attempt history)
    created before `as_of - older_than`. Never called from request-serving
    code paths -- an explicit operator/retention-job action."""
    cutoff = as_of - older_than
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_DELETE_EXPIRED_PERIOD_RUNS, [cutoff])
        return int(cur.rowcount)
