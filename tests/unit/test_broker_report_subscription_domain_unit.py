"""Unit tests for SLICE-0089 broker periodic report period-boundary math.

Pure domain tests, no database. Prove: explicit deterministic UTC
`[start, end)` boundaries for WEEKLY/MONTHLY periods, month-end/leap-year
correctness, anchor-based catch-up semantics (oldest-missing-period-first,
one period per call), and that a not-yet-closed period is never admitted.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from hullq.domain.broker_report_subscription import (
    ReportPeriodKind,
    next_due_period_index,
    period_bounds,
)


def test_weekly_period_bounds_align_to_monday() -> None:
    # 2026-10-25 is a Sunday -- the anchor Monday is 2026-10-19.
    anchor = date(2026, 10, 25)
    start, end = period_bounds(anchor, ReportPeriodKind.WEEKLY, 0)
    assert start == datetime(2026, 10, 19, tzinfo=UTC)
    assert end == datetime(2026, 10, 26, tzinfo=UTC)

    start1, end1 = period_bounds(anchor, ReportPeriodKind.WEEKLY, 1)
    assert start1 == end
    assert end1 == datetime(2026, 11, 2, tzinfo=UTC)


def test_monthly_period_bounds_handle_month_end_and_leap_year() -> None:
    anchor = date(2026, 1, 31)
    start, end = period_bounds(anchor, ReportPeriodKind.MONTHLY, 0)
    assert start == datetime(2026, 1, 1, tzinfo=UTC)
    assert end == datetime(2026, 2, 1, tzinfo=UTC)

    # February index crosses into a non-leap year's 28-day month boundary
    # cleanly, and December -> January correctly rolls the year forward.
    start1, end1 = period_bounds(anchor, ReportPeriodKind.MONTHLY, 1)
    assert start1 == datetime(2026, 2, 1, tzinfo=UTC)
    assert end1 == datetime(2026, 3, 1, tzinfo=UTC)

    start11, end11 = period_bounds(anchor, ReportPeriodKind.MONTHLY, 11)
    assert start11 == datetime(2026, 12, 1, tzinfo=UTC)
    assert end11 == datetime(2027, 1, 1, tzinfo=UTC)

    # 2024 is a leap year -- the Feb->Mar boundary must land on the 29th.
    leap_anchor = date(2024, 1, 1)
    feb_start, feb_end = period_bounds(leap_anchor, ReportPeriodKind.MONTHLY, 1)
    assert feb_start == datetime(2024, 2, 1, tzinfo=UTC)
    assert feb_end == datetime(2024, 3, 1, tzinfo=UTC)


def test_period_bounds_rejects_negative_index() -> None:
    with pytest.raises(ValueError):
        period_bounds(date(2026, 1, 1), ReportPeriodKind.MONTHLY, -1)


def test_next_due_period_index_none_when_not_yet_closed() -> None:
    anchor = date(2026, 1, 1)
    # The first MONTHLY period [2026-01-01, 2026-02-01) has not closed yet
    # as of 2026-01-15.
    as_of = datetime(2026, 1, 15, tzinfo=UTC)
    assert (
        next_due_period_index(
            anchor, ReportPeriodKind.MONTHLY, last_admitted_index=None, as_of=as_of
        )
        is None
    )


def test_next_due_period_index_admits_oldest_missing_first() -> None:
    anchor = date(2026, 1, 1)
    # Three MONTHLY periods have fully closed by 2026-04-02 (Jan, Feb, Mar).
    as_of = datetime(2026, 4, 2, tzinfo=UTC)
    assert (
        next_due_period_index(
            anchor, ReportPeriodKind.MONTHLY, last_admitted_index=None, as_of=as_of
        )
        == 0
    )
    # Catch-up proceeds one period per call, oldest first -- never skips
    # ahead to the latest closed period.
    assert (
        next_due_period_index(
            anchor, ReportPeriodKind.MONTHLY, last_admitted_index=0, as_of=as_of
        )
        == 1
    )
    assert (
        next_due_period_index(
            anchor, ReportPeriodKind.MONTHLY, last_admitted_index=2, as_of=as_of
        )
        is None
    )
