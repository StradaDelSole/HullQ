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

Pure value objects/vocabulary/period-math only -- no persistence/network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

__all__ = [
    "MAX_REPORT_LISTING_ROWS",
    "PeriodRunStatus",
    "ReportDeliveryAttemptOutcome",
    "ReportPeriodKind",
    "SubscriptionStatus",
    "next_due_period_index",
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
    because the Organization's subscription revision had already moved past
    the revision captured at generation time (opt-out/recipient
    change/deactivation between generation and dispatch) -- never a
    disguised delivery failure.
    """

    DELIVERED = "DELIVERED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    SUPPRESSED = "SUPPRESSED"


#: Bounded per-report listing-row cap (failure-mode §"maximum listing
#: count/byte size"). Rows beyond this are never silently dropped without
#: disclosure -- the caller must record `listings_truncated=True` whenever
#: the source population exceeds this bound.
MAX_REPORT_LISTING_ROWS = 500


def _add_months(start: date, months: int) -> date:
    total = (start.month - 1) + months
    year = start.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def _iso_week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def period_bounds(
    anchor_date: date, period_kind: ReportPeriodKind, period_index: int
) -> tuple[datetime, datetime]:
    """Resolve one explicit, deterministic UTC `[start, end)` period.

    *anchor_date* is the subscription's fixed creation-date anchor (never
    recomputed from "now" -- contract: "period close and catch-up semantics
    precisely specified"). *period_index* `0` is the first period starting
    at or after the anchor; each later index is the next consecutive
    WEEKLY/MONTHLY period. Never raises for any non-negative index.
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


def next_due_period_index(
    anchor_date: date,
    period_kind: ReportPeriodKind,
    *,
    last_admitted_index: int | None,
    as_of: datetime,
) -> int | None:
    """The next period-index this subscription should admit, or `None` if
    none has fully closed yet.

    Always returns `last_admitted_index + 1` (or `0` if nothing has been
    admitted yet) when that period's `period_end <= as_of` -- never skips
    ahead, so a long-paused worker catches up one period per call (bounded
    worker batch), oldest first.
    """
    candidate_index = 0 if last_admitted_index is None else last_admitted_index + 1
    _, candidate_end = period_bounds(anchor_date, period_kind, candidate_index)
    if candidate_end <= as_of:
        return candidate_index
    return None
