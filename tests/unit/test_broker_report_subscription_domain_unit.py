"""Unit tests for SLICE-0089 broker periodic report period-boundary math.

Pure domain tests, no database. Prove: explicit deterministic UTC
`[start, end)` boundaries for WEEKLY/MONTHLY periods, month-end/leap-year
correctness, and the cursor-based continuation (amendment, independent
review Finding B) that keeps period identity correct across a WEEKLY<->
MONTHLY schedule switch and across any number of chained periods, without
ever re-deriving from the original anchor date.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from hullq.domain.broker_report_subscription import (
    ReportPeriodKind,
    bootstrap_period_start,
    next_period_bounds,
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


def test_bootstrap_period_start_is_calendar_aligned() -> None:
    assert bootstrap_period_start(date(2026, 10, 25), ReportPeriodKind.MONTHLY) == datetime(
        2026, 10, 1, tzinfo=UTC
    )
    assert bootstrap_period_start(date(2026, 10, 25), ReportPeriodKind.WEEKLY) == datetime(
        2026, 10, 19, tzinfo=UTC
    )


def test_next_period_bounds_chains_monthly_across_month_end_and_leap_year() -> None:
    cursor = datetime(2026, 1, 1, tzinfo=UTC)
    start, end = next_period_bounds(cursor, ReportPeriodKind.MONTHLY)
    assert start == cursor
    assert end == datetime(2026, 2, 1, tzinfo=UTC)

    # Chain forward again from the returned end -- never re-derived from a
    # fixed anchor_date.
    start2, end2 = next_period_bounds(end, ReportPeriodKind.MONTHLY)
    assert start2 == datetime(2026, 2, 1, tzinfo=UTC)
    assert end2 == datetime(2026, 3, 1, tzinfo=UTC)  # 2026 is not a leap year

    _, leap_end = next_period_bounds(datetime(2024, 1, 1, tzinfo=UTC), ReportPeriodKind.MONTHLY)
    assert leap_end == datetime(2024, 2, 1, tzinfo=UTC)
    _, leap_end2 = next_period_bounds(leap_end, ReportPeriodKind.MONTHLY)
    assert leap_end2 == datetime(2024, 3, 1, tzinfo=UTC)  # Feb 2024 has 29 days


def test_next_period_bounds_clamps_day_of_month_at_month_end() -> None:
    # A cursor landing on the 31st (e.g. after a prior WEEKLY->MONTHLY
    # switch mid-cycle) must clamp into the next month's own last valid
    # day rather than overflowing into a third month.
    cursor = datetime(2026, 1, 31, tzinfo=UTC)
    _, end = next_period_bounds(cursor, ReportPeriodKind.MONTHLY)
    assert end == datetime(2026, 2, 28, tzinfo=UTC)


def test_next_period_bounds_weekly_is_a_plain_seven_day_window() -> None:
    cursor = datetime(2026, 3, 15, tzinfo=UTC)  # an arbitrary non-Monday cursor
    start, end = next_period_bounds(cursor, ReportPeriodKind.WEEKLY)
    assert start == cursor
    assert end == datetime(2026, 3, 22, tzinfo=UTC)


def test_schedule_switch_mid_chain_never_reuses_an_unrelated_calendar_window() -> None:
    """Finding B's exact scenario: MONTHLY for two periods, then a switch
    to WEEKLY -- the next period must be the textually next calendar
    window after the last MONTHLY period closed, never a window computed
    from the original anchor_date under the new WEEKLY cadence."""
    anchor = date(2026, 1, 15)
    cursor = bootstrap_period_start(anchor, ReportPeriodKind.MONTHLY)  # 2026-01-01
    _, cursor = next_period_bounds(cursor, ReportPeriodKind.MONTHLY)  # period 0 closes 2026-02-01
    assert cursor == datetime(2026, 2, 1, tzinfo=UTC)
    _, cursor = next_period_bounds(cursor, ReportPeriodKind.MONTHLY)  # period 1 closes 2026-03-01
    assert cursor == datetime(2026, 3, 1, tzinfo=UTC)

    # Now the subscription switches to WEEKLY -- the next period must
    # start exactly where the last MONTHLY period left off.
    next_start, next_end = next_period_bounds(cursor, ReportPeriodKind.WEEKLY)
    assert next_start == datetime(2026, 3, 1, tzinfo=UTC)
    assert next_end == datetime(2026, 3, 8, tzinfo=UTC)
    # This is NOT the same window `period_bounds(anchor, WEEKLY, 2)` would
    # have produced (a stale January week from the original anchor_date).
    stale_start, stale_end = period_bounds(anchor, ReportPeriodKind.WEEKLY, 2)
    assert (next_start, next_end) != (stale_start, stale_end)
