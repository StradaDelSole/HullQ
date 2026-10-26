"""Broker periodic performance report subscription vocabulary — SLICE-0089.

Implements `docs/slices/SLICE-0089-broker-periodic-performance-reporting.md`'s
"Periodic delivery / operability" section: bounded WEEKLY/MONTHLY recurrence
over the accepted SLICE-0075 funnel snapshot, with explicit, deterministic
`[period_start, period_end)` boundaries (mandatory invariant 4).

Scope decision: periods are anchored and computed in UTC civil-calendar
terms only (Monday-aligned ISO weeks; calendar months). This is "timezone-
aware" in the sense the contract requires -- explicit, deterministic,
clearly labeled (truth contract item 1 allows "UTC or clearly labeled") --
without introducing per-Organization IANA timezone/DST configuration, which
would multiply this HIGH_RISK slice's adversarial surface without an
accepted product requirement for broker-local wall-clock delivery times.

Amendment (independent review round 1, Finding B): period continuation is
cursor-based, not anchor+index based. `next_due_period_index`'s raw integer
`period_index` used to mean different calendar windows depending on
whichever `period_kind` happened to be active *at admission time* --
switching WEEKLY<->MONTHLY (or resuming after a long pause/full purge)
could silently reuse an unrelated prior calendar window. `next_period_bounds`
instead always chains directly from the Organization's own durable
admission cursor (the previous period's exact end, or the bootstrap start
for the very first period) -- the next period is always the textually next
one in time, under whichever cadence is currently configured, with no
re-derivation from the original `anchor_date` and no reliance on retained
historical rows (which may have been purged).

Pure value objects/vocabulary/period-math only -- no persistence/network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

__all__ = [
    "DEFAULT_CLAIM_LEASE_SECONDS",
    "MAX_ADMISSION_SCAN_ORGANIZATIONS",
    "MAX_REPORT_LISTING_ROWS",
    "PeriodRunStatus",
    "ReportDeliveryAttemptOutcome",
    "ReportPeriodKind",
    "SubscriptionStatus",
    "bootstrap_period_start",
    "next_period_bounds",
    "period_bounds",
]


class ReportPeriodKind(StrEnum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PeriodRunStatus(StrEnum):
    """Mechanically distinct PeriodRun lifecycle states.

    `GENERATED` is the only claimable-for-delivery state alongside
    `FAILED_RETRYABLE`; `DELIVERED`/`FAILED_TERMINAL`/`SUPPRESSED` are all
    terminal and never retried.
    """

    GENERATED = "GENERATED"
    DELIVERED = "DELIVERED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    SUPPRESSED = "SUPPRESSED"


class ReportDeliveryAttemptOutcome(StrEnum):
    """Append-only delivery-attempt outcome vocabulary.

    `SUPPRESSED` records that a due PeriodRun was intentionally *not* sent
    because the Organization's subscription revision had already moved
    past the revision captured at generation time (opt-out/recipient
    change/deactivation between generation and dispatch). `RECIPIENT_
    UNAUTHORIZED` (amendment, Finding D) is the mechanically distinct case
    where the revision still matches but the account that configured this
    exact recipient is no longer a currently ACTIVE OWNER/ADMIN member (or
    the Organization itself no longer exists) -- offboarding/revocation,
    never a disguised delivery failure. `RECLAIMED_AFTER_LEASE_EXPIRY`
    (amendment, Finding A) is an audit-only entry recorded when a claim's
    bounded lease expired and a later worker tick recovered the row; it
    never itself transitions the PeriodRun's own status.
    """

    DELIVERED = "DELIVERED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    SUPPRESSED = "SUPPRESSED"
    RECIPIENT_UNAUTHORIZED = "RECIPIENT_UNAUTHORIZED"
    RECLAIMED_AFTER_LEASE_EXPIRY = "RECLAIMED_AFTER_LEASE_EXPIRY"


#: Bounded per-report listing-row cap (failure-mode §"maximum listing
#: count/byte size"). Rows beyond this are never silently dropped without
#: disclosure -- the caller must record `listings_truncated=True` whenever
#: the source population exceeds this bound. Aggregate totals (views,
#: Leads, SOLD counts) are never truncated -- only the enumerated
#: per-listing breakdown rows are bounded; truncating the aggregates
#: themselves would misreport the factual population (truth contract).
MAX_REPORT_LISTING_ROWS = 500

#: Bounded admission-scan batch (amendment, Finding C): one worker tick
#: examines at most this many ACTIVE subscriptions when looking for a
#: single newly-due period -- never an unbounded "every Organization"
#: scan in one call, regardless of how many Organizations exist.
MAX_ADMISSION_SCAN_ORGANIZATIONS = 50

#: Bounded claim lease (amendment, Finding A): a claimed-but-never-recorded
#: PeriodRun (worker crash between claim-commit and delivery-result-commit)
#: becomes reclaimable again once its lease expires -- "v0.1 has no
#: claim-staleness sweep" is no longer true; recovery is bounded and
#: deterministic, never immediate (which would defeat the point of a
#: lease) and never permanent (which is the defect this amendment fixes).
DEFAULT_CLAIM_LEASE_SECONDS = 900


def _add_months(start: date, months: int) -> date:
    total = (start.month - 1) + months
    year = start.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return (date(year + 1, 1, 1) - date(year, 12, 1)).days
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def _add_one_calendar_month(start: date) -> date:
    """One calendar month after *start*, clamped to the resulting month's
    own last valid day (e.g. 2026-01-31 -> 2026-02-28) -- never silently
    overflowing into a third month."""
    total = start.month  # (start.month - 1) + 1
    year = start.year + total // 12
    month = total % 12 + 1
    day = min(start.day, _days_in_month(year, month))
    return date(year, month, day)


def _iso_week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def period_bounds(
    anchor_date: date, period_kind: ReportPeriodKind, period_index: int
) -> tuple[datetime, datetime]:
    """Resolve one explicit, deterministic UTC `[start, end)` period
    relative to a fixed *anchor_date*, assuming *period_kind* has been
    constant for every period from `0` to *period_index*.

    Used only for the very first period (`bootstrap_period_start`) and for
    pure calendar-math testing -- live admission beyond the first period
    always uses `next_period_bounds`'s cursor-chaining instead, which
    remains correct across a WEEKLY<->MONTHLY schedule switch (Finding B).
    Never raises for any non-negative index.
    """
    if period_index < 0:
        raise ValueError(f"period_index must be >= 0, got {period_index}")
    if period_kind is ReportPeriodKind.WEEKLY:
        anchor_monday = _iso_week_monday(anchor_date)
        start_date = anchor_monday + timedelta(days=7 * period_index)
        end_date = start_date + timedelta(days=7)
    else:
        anchor_month_start = date(anchor_date.year, anchor_date.month, 1)
        start_date = _add_months(anchor_month_start, period_index)
        end_date = _add_months(start_date, 1)
    start = datetime.combine(start_date, time.min, tzinfo=UTC)
    end = datetime.combine(end_date, time.min, tzinfo=UTC)
    return start, end


def bootstrap_period_start(anchor_date: date, initial_period_kind: ReportPeriodKind) -> datetime:
    """The very first period's calendar-aligned start (Monday-of-week or
    1st-of-month containing *anchor_date*), fixed once at subscription
    bootstrap and durably stored as the Organization's admission cursor.
    Every later period chains forward from this value via
    `next_period_bounds`, never recomputed from *anchor_date* again."""
    start, _ = period_bounds(anchor_date, initial_period_kind, 0)
    return start


def next_period_bounds(
    cursor_start: datetime, period_kind: ReportPeriodKind
) -> tuple[datetime, datetime]:
    """The next bounded period starting exactly at *cursor_start* (the
    Organization's durable admission cursor -- either `bootstrap_period_
    start`'s value or a prior period's own `period_end`), using the
    *current* `period_kind` as its cadence.

    Chains directly from the prior admitted period's own end -- never
    re-derived from the original `anchor_date` by index arithmetic, and
    never dependent on any retained historical PeriodRun row (which may
    since have been purged). This is what makes a WEEKLY<->MONTHLY
    schedule switch, or catch-up after a long deactivation, produce the
    textually next correct period instead of colliding with an unrelated
    period from a different cadence that happened to share the same raw
    sequence number (contract: "period close and catch-up semantics
    precisely specified").
    """
    start_date = cursor_start.date()
    if period_kind is ReportPeriodKind.WEEKLY:
        end_date = start_date + timedelta(days=7)
    else:
        end_date = _add_one_calendar_month(start_date)
    end = datetime.combine(end_date, time.min, tzinfo=UTC)
    return cursor_start, end
