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

Amendment (independent review round 1):

Finding A -- `claim_next_deliverable_period_run` now binds a bounded lease
(`lease_expires_at`) to every claim, and a fencing `claim_generation` token
so a superseded (lease-expired, later-reclaimed) claim's late write can
never silently overwrite a newer claim's own outcome. `record_delivery_
attempt` requires the caller's own `expected_claim_generation` and raises
rather than silently dropping a write that lost its fence.

Finding B -- subscription admission now tracks a durable `next_period_
start` cursor on the subscription row itself (`select_subscription_for_
admission`/`advance_subscription_cursor`), never derived from retained
PeriodRun history (which `purge_expired_period_runs` may delete) and never
re-derived from the original `anchor_date` by index arithmetic (which
produced the wrong calendar window after a WEEKLY<->MONTHLY switch). The
PeriodRun admission idempotency key is now the actual calendar window
`(organization_id, period_start, period_end)`, not a bare sequence number.

Finding C -- `insert_period_run` takes a bare `cur` (not its own `conn`)
so the caller (`hullq.application.broker_report_dispatch`) can perform the
entire admission -- cursor lock, facts read, row insert, cursor advance --
inside one explicit `REPEATABLE READ` transaction: a genuinely consistent
snapshot, not merely a same-looking-but-unrelated set of separate reads.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from hullq.domain.broker_report_subscription import (
    DEFAULT_CLAIM_LEASE_SECONDS,
    PeriodRunStatus,
    ReportDeliveryAttemptOutcome,
    ReportPeriodKind,
    SubscriptionStatus,
    bootstrap_period_start,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "ClaimOutcome",
    "PeriodRunRecord",
    "SetSubscriptionResult",
    "SubscriptionRecord",
    "advance_subscription_cursor",
    "claim_next_deliverable_period_run",
    "fetch_last_admitted_period_index",
    "fetch_period_run_for_organization",
    "fetch_subscription",
    "insert_period_run",
    "purge_expired_period_runs",
    "record_delivery_attempt",
    "record_reclaim_event",
    "set_subscription",
]


# ---------------------------------------------------------------------------
# Subscription configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubscriptionRecord:
    """Absence of a durable row is the implicit default: `INACTIVE`,
    `MONTHLY`, no recipient, `anchor_date=None`, `next_period_start=None`,
    `revision=0` -- the same default state a first-ever `set_subscription`
    call must target with `expected_revision=0`.

    `updated_by_account_id` (amendment, Finding D) is the account that
    last configured this exact revision -- re-checked for current ACTIVE
    OWNER/ADMIN membership at dispatch time, never trusted indefinitely."""

    organization_id: MarketplaceOrganizationId
    status: SubscriptionStatus
    period_kind: ReportPeriodKind
    recipient_email: str | None
    anchor_date: date | None
    next_period_start: datetime | None
    updated_by_account_id: AccountId | None
    revision: int

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "period_kind": self.period_kind.value,
            "recipient_email": self.recipient_email,
            "revision": self.revision,
        }


_SUBSCRIPTION_COLUMNS = (
    "status, period_kind, recipient_email, anchor_date, next_period_start, "
    "updated_by_account_id, revision"
)

_SELECT_SUBSCRIPTION = f"""
SELECT {_SUBSCRIPTION_COLUMNS} FROM organization_report_subscription WHERE organization_id = %s
"""

_SELECT_SUBSCRIPTION_FOR_UPDATE = _SELECT_SUBSCRIPTION + " FOR UPDATE"

_BOOTSTRAP_SUBSCRIPTION = """
INSERT INTO organization_report_subscription (organization_id, anchor_date, next_period_start)
VALUES (%s, %s, %s)
ON CONFLICT (organization_id) DO NOTHING
"""

_UPDATE_SUBSCRIPTION = """
UPDATE organization_report_subscription
SET status = %s, period_kind = %s, recipient_email = %s, updated_by_account_id = %s,
    updated_at = NOW(), revision = revision + 1
WHERE organization_id = %s AND revision = %s
RETURNING revision, anchor_date, next_period_start
"""

_ADVANCE_SUBSCRIPTION_CURSOR = """
UPDATE organization_report_subscription SET next_period_start = %s, updated_at = NOW()
WHERE organization_id = %s
"""


def _row_to_subscription(
    organization_id: MarketplaceOrganizationId, row: tuple[Any, ...]
) -> SubscriptionRecord:
    return SubscriptionRecord(
        organization_id=organization_id,
        status=SubscriptionStatus(row[0]),
        period_kind=ReportPeriodKind(row[1]),
        recipient_email=row[2],
        anchor_date=row[3],
        next_period_start=row[4],
        updated_by_account_id=AccountId(row[5]) if row[5] is not None else None,
        revision=row[6],
    )


def fetch_subscription(
    conn: Any, organization_id: MarketplaceOrganizationId, *, for_update: bool = False
) -> SubscriptionRecord:
    """Read current subscription state.

    *for_update* (Finding B/C) locks the row `FOR UPDATE` inside the
    caller's own open transaction -- used only by admission, so a
    concurrent admission attempt for the *same* Organization serializes
    against this read+cursor-advance instead of racing it. Never use
    `for_update=True` outside an explicit `with conn.transaction():`.
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    query = _SELECT_SUBSCRIPTION_FOR_UPDATE if for_update else _SELECT_SUBSCRIPTION
    with conn.cursor() as cur:
        cur.execute(query, [organization_id.value])
        row = cur.fetchone()
    if row is None:
        return SubscriptionRecord(
            organization_id=organization_id,
            status=SubscriptionStatus.INACTIVE,
            period_kind=ReportPeriodKind.MONTHLY,
            recipient_email=None,
            anchor_date=None,
            next_period_start=None,
            updated_by_account_id=None,
            revision=0,
        )
    return _row_to_subscription(organization_id, row)


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
    bootstrap_initial_period_kind: ReportPeriodKind,
) -> SetSubscriptionResult:
    """Create/change the Organization's periodic report subscription.

    Authorization (current ACTIVE OWNER/ADMIN) is the application layer's
    responsibility. The row is bootstrapped into existence first
    (idempotent, `anchor_date`/`next_period_start` fixed forever at first
    bootstrap -- never recomputed by a later mutation, including a later
    `period_kind` change, so period boundaries stay stable; see
    `hullq.domain.broker_report_subscription.next_period_bounds` for how
    continuation periods after a schedule switch are computed instead),
    then updated only if *expected_revision* still matches the current
    durable revision.
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    if not isinstance(updated_by_account_id, AccountId):
        raise TypeError(
            f"updated_by_account_id must be an AccountId, got {type(updated_by_account_id).__name__}"
        )
    initial_next_period_start = bootstrap_period_start(
        bootstrap_anchor_date, bootstrap_initial_period_kind
    )
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _BOOTSTRAP_SUBSCRIPTION,
            [organization_id.value, bootstrap_anchor_date, initial_next_period_start],
        )
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
                next_period_start=updated_row[2],
                updated_by_account_id=updated_by_account_id,
                revision=updated_row[0],
            ),
        )


def advance_subscription_cursor(
    cur: Any, organization_id: MarketplaceOrganizationId, *, next_period_start: datetime
) -> None:
    """Advance the Organization's durable admission cursor.

    A bare-cursor function (mirrors `hullq.persistence.lead_notification.
    insert_pending_notification_intent`'s documented discipline) -- must be
    called inside the caller's own open transaction, in the same
    transaction as the PeriodRun it admitted, after first reading the
    current row with `fetch_subscription(..., for_update=True)` (Finding
    B/C: the read-lock, the facts snapshot, the PeriodRun insert and this
    cursor advance are all one atomic, consistent unit)."""
    cur.execute(_ADVANCE_SUBSCRIPTION_CURSOR, [next_period_start, organization_id.value])


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
    provider_idempotency_key: str
    generated_at: datetime
    attempt_count: int
    provider_message_id: str | None
    delivered_at: datetime | None


#: Canonical column order for every SELECT that feeds `_row_to_period_run`.
_PERIOD_RUN_COLUMNS = (
    "period_run_id, organization_id, period_index, period_kind, period_start, period_end, "
    "subscription_revision, recipient_email, status, facts_json, listings_truncated, "
    "provider_idempotency_key, generated_at, attempt_count, provider_message_id, delivered_at"
)

_SELECT_LAST_PERIOD_INDEX = """
SELECT MAX(period_index) FROM organization_report_period_run WHERE organization_id = %s
"""

_INSERT_PERIOD_RUN = """
INSERT INTO organization_report_period_run (
    period_run_id, organization_id, period_index, period_kind, period_start, period_end,
    subscription_revision, recipient_email, status, facts_json, listings_truncated,
    provider_idempotency_key, generated_at, next_attempt_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (organization_id, period_start, period_end) DO NOTHING
RETURNING period_run_id
"""


def fetch_last_admitted_period_index(
    conn: Any, organization_id: MarketplaceOrganizationId
) -> int | None:
    """The highest `period_index` ever admitted for this Organization --
    audit/display ordering only. Admission continuity itself is governed
    by the subscription's own `next_period_start` cursor (Finding B), not
    by this value, so purging historical PeriodRun rows can never reset
    where the worker resumes."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_LAST_PERIOD_INDEX, [organization_id.value])
        row = cur.fetchone()
    return row[0] if row is not None else None


def insert_period_run(
    cur: Any,
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
    """Admit exactly one new PeriodRun.

    A bare-cursor function -- the caller owns the transaction (Finding C:
    this must run inside the same explicit, consistent-snapshot
    transaction as the facts read and the cursor advance, never its own
    separate transaction).

    Returns the new `period_run_id`, or `None` if a row for this exact
    `(organization_id, period_start, period_end)` calendar window already
    exists -- the unique-key admission idempotency that makes repeated/
    concurrent worker ticks safe, keyed by the actual window identity
    rather than a bare sequence number that meant different things under
    different `period_kind`s (Finding B).
    """
    period_run_id = str(uuid.uuid4())
    provider_idempotency_key = f"hullq-report:{organization_id.value}:{period_start.isoformat()}"
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
            provider_idempotency_key,
            generated_at,
            generated_at,
        ),
    )
    row = cur.fetchone()
    return row[0] if row is not None else None


#: `FOR UPDATE SKIP LOCKED` (mirrors `hullq.persistence.lead_notification`'s
#: identical documented discipline): two concurrent claimers racing for the
#: same row while both transactions are open never both win. Amendment
#: (Finding A): a row is also claimable again once its own bounded lease
#: has expired (`lease_expires_at <= as_of`) -- a crashed worker's claim no
#: longer blocks recovery forever.
_CLAIM_NEXT_PERIOD_RUN = f"""
SELECT {_PERIOD_RUN_COLUMNS}, claimed_at, claim_generation
FROM organization_report_period_run
WHERE status IN ('GENERATED', 'FAILED_RETRYABLE') AND next_attempt_at <= %s
  AND (claimed_at IS NULL OR lease_expires_at <= %s)
ORDER BY next_attempt_at ASC, period_run_id ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
"""

#: The fencing token: `claim_generation` increments on every claim
#: (fresh or reclaim). `record_delivery_attempt` only ever writes against
#: the exact generation it was handed, so a superseded claim's late write
#: can never silently overwrite a newer claim's own outcome.
_MARK_CLAIMED = """
UPDATE organization_report_period_run
SET claimed_by = %s, claimed_at = %s, lease_expires_at = %s, claim_generation = claim_generation + 1,
    updated_at = NOW()
WHERE period_run_id = %s
RETURNING claim_generation
"""

_INSERT_DELIVERY_ATTEMPT = (
    "INSERT INTO organization_report_delivery_attempts "
    "(attempt_id, period_run_id, attempted_at, outcome, provider_message_id, error_text) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)

_RECORD_DELIVERED = """
UPDATE organization_report_period_run
SET status = 'DELIVERED', attempt_count = attempt_count + 1, provider_message_id = %s,
    delivered_at = %s, updated_at = NOW(), version = version + 1
WHERE period_run_id = %s AND claim_generation = %s
"""

_RECORD_RETRYABLE_FAILURE = """
UPDATE organization_report_period_run
SET status = 'FAILED_RETRYABLE', attempt_count = attempt_count + 1, last_error = %s,
    next_attempt_at = %s, claimed_by = NULL, claimed_at = NULL, lease_expires_at = NULL,
    updated_at = NOW(), version = version + 1
WHERE period_run_id = %s AND claim_generation = %s
"""

_RECORD_TERMINAL_FAILURE = """
UPDATE organization_report_period_run
SET status = 'FAILED_TERMINAL', attempt_count = attempt_count + 1, last_error = %s,
    updated_at = NOW(), version = version + 1
WHERE period_run_id = %s AND claim_generation = %s
"""

_RECORD_SUPPRESSED = """
UPDATE organization_report_period_run
SET status = 'SUPPRESSED', attempt_count = attempt_count + 1, updated_at = NOW(),
    version = version + 1
WHERE period_run_id = %s AND claim_generation = %s
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
        provider_idempotency_key=row[11],
        generated_at=row[12],
        attempt_count=row[13],
        provider_message_id=row[14],
        delivered_at=row[15],
    )


@dataclass(frozen=True)
class ClaimOutcome:
    """`was_reclaimed=True` means a *different* worker's claim lease had
    already expired without recording an outcome -- the caller must log a
    `record_reclaim_event` audit entry and treat the prior attempt as
    ambiguous (never silently assume it failed, and never silently assume
    it already succeeded)."""

    record: PeriodRunRecord
    claim_generation: int
    was_reclaimed: bool


def claim_next_deliverable_period_run(
    conn: Any,
    *,
    worker_id: str,
    as_of: datetime,
    lease_seconds: int = DEFAULT_CLAIM_LEASE_SECONDS,
) -> ClaimOutcome | None:
    """Claim (and commit the claim for) exactly one due claimable PeriodRun
    row, or `None` if none is currently claimable.

    The claim is committed immediately, separate from the eventual
    delivery-result commit performed by `record_delivery_attempt`, so a
    worker crash between claim and delivery-result leaves a recoverable
    row: once `lease_seconds` elapses, a later tick (by this or another
    worker) may reclaim it (Finding A) -- bounded, deterministic recovery,
    never immediate (which would race an in-flight send) and never
    permanent (which was the original defect).
    """
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_CLAIM_NEXT_PERIOD_RUN, [as_of, as_of])
        row = cur.fetchone()
        if row is None:
            return None
        previous_claimed_at = row[16]
        lease_expires_at = as_of + timedelta(seconds=lease_seconds)
        cur.execute(_MARK_CLAIMED, [worker_id, as_of, lease_expires_at, row[0]])
        (new_generation,) = cur.fetchone()
    return ClaimOutcome(
        record=_row_to_period_run(row),
        claim_generation=new_generation,
        was_reclaimed=previous_claimed_at is not None,
    )


def record_reclaim_event(conn: Any, period_run_id: str, *, as_of: datetime) -> None:
    """Audit-only entry (Finding A): records that a claim's bounded lease
    had expired and this tick recovered it. Never transitions the
    PeriodRun's own `status` -- the subsequent real delivery attempt
    (`record_delivery_attempt`) does that."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_DELIVERY_ATTEMPT,
            (
                str(uuid.uuid4()),
                period_run_id,
                as_of,
                ReportDeliveryAttemptOutcome.RECLAIMED_AFTER_LEASE_EXPIRY.value,
                None,
                None,
            ),
        )


def record_delivery_attempt(
    conn: Any,
    period_run_id: str,
    *,
    outcome: ReportDeliveryAttemptOutcome,
    expected_claim_generation: int,
    provider_message_id: str | None = None,
    error_text: str | None = None,
    next_attempt_at: datetime | None = None,
    as_of: datetime,
) -> None:
    """Durably record one delivery attempt and transition the PeriodRun.

    *expected_claim_generation* (Finding A) is the fencing token the
    caller received from `claim_next_deliverable_period_run`. If the
    current row's `claim_generation` has since moved on (a `RuntimeError`
    -- this must never happen under this module's own single-claimer-per-
    tick design, but failing loudly here is strictly safer than silently
    discarding a write that lost its fence), the write is rejected rather
    than corrupting a newer claim's own outcome.
    """
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            _INSERT_DELIVERY_ATTEMPT,
            (
                str(uuid.uuid4()),
                period_run_id,
                as_of,
                outcome.value,
                provider_message_id,
                error_text,
            ),
        )
        if outcome is ReportDeliveryAttemptOutcome.DELIVERED:
            cur.execute(
                _RECORD_DELIVERED,
                [provider_message_id, as_of, period_run_id, expected_claim_generation],
            )
        elif outcome is ReportDeliveryAttemptOutcome.RETRYABLE_FAILURE:
            if next_attempt_at is None:
                raise ValueError("next_attempt_at is required for a RETRYABLE_FAILURE outcome")
            cur.execute(
                _RECORD_RETRYABLE_FAILURE,
                [error_text, next_attempt_at, period_run_id, expected_claim_generation],
            )
        elif outcome is ReportDeliveryAttemptOutcome.TERMINAL_FAILURE:
            cur.execute(
                _RECORD_TERMINAL_FAILURE, [error_text, period_run_id, expected_claim_generation]
            )
        elif outcome in (
            ReportDeliveryAttemptOutcome.SUPPRESSED,
            ReportDeliveryAttemptOutcome.RECIPIENT_UNAUTHORIZED,
        ):
            cur.execute(_RECORD_SUPPRESSED, [period_run_id, expected_claim_generation])
        else:
            raise ValueError(f"unknown delivery attempt outcome: {outcome!r}")
        if cur.rowcount != 1:
            raise RuntimeError(
                f"record_delivery_attempt lost its claim fence for {period_run_id} "
                f"(expected_claim_generation={expected_claim_generation}); refusing to silently "
                "apply a write that may no longer belong to the current claim"
            )


_SELECT_PERIOD_RUN_FOR_ORG = f"""
SELECT {_PERIOD_RUN_COLUMNS}
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
    code paths -- an explicit operator/retention-job action.

    Safe by construction (Finding B): admission continuity is governed by
    the subscription's own durable `next_period_start` cursor, never by
    `MAX(period_index)` over retained rows, so purging every historical
    row can never reset or regress the worker's resume point."""
    cutoff = as_of - older_than
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_DELETE_EXPIRED_PERIOD_RUNS, [cutoff])
        return int(cur.rowcount)
