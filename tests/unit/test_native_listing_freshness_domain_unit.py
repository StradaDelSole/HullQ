"""Pure domain unit tests — SLICE-0052 `MANUAL_NATIVE_V1` boundary semantics.

Covers contract §3/§8 and REQ-MARKET-009: exact 30-day/37-day boundaries,
no admissible evidence -> UNKNOWN, and a future confirmation timestamp
relative to `as_of` fails closed to UNKNOWN rather than manufacturing a
negative age.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hullq.domain.native_listing_freshness import (
    MANUAL_NATIVE_V1,
    FreshnessConfirmationId,
    FreshnessPolicy,
    FreshnessStatus,
    evaluate_freshness_status,
)

_T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_manual_native_v1_is_exactly_30_day_ttl_plus_7_day_grace() -> None:
    assert MANUAL_NATIVE_V1.policy_id == "MANUAL_NATIVE_V1"
    assert MANUAL_NATIVE_V1.confirmation_ttl == timedelta(days=30)
    assert MANUAL_NATIVE_V1.grace_period == timedelta(days=7)
    assert MANUAL_NATIVE_V1.stale_boundary == timedelta(days=37)


def test_no_admissible_evidence_is_unknown() -> None:
    assert evaluate_freshness_status(confirmed_at=None, as_of=_T0) is FreshnessStatus.UNKNOWN


def test_just_confirmed_is_confirmed() -> None:
    assert evaluate_freshness_status(confirmed_at=_T0, as_of=_T0) is FreshnessStatus.CONFIRMED


def test_one_second_before_exact_30_days_is_still_confirmed() -> None:
    as_of = _T0 + timedelta(days=30) - timedelta(seconds=1)
    assert evaluate_freshness_status(confirmed_at=_T0, as_of=as_of) is FreshnessStatus.CONFIRMED


def test_exact_30_days_is_due_for_confirmation() -> None:
    as_of = _T0 + timedelta(days=30)
    assert (
        evaluate_freshness_status(confirmed_at=_T0, as_of=as_of)
        is FreshnessStatus.DUE_FOR_CONFIRMATION
    )


def test_one_second_before_exact_37_days_is_still_due_for_confirmation() -> None:
    as_of = _T0 + timedelta(days=37) - timedelta(seconds=1)
    assert (
        evaluate_freshness_status(confirmed_at=_T0, as_of=as_of)
        is FreshnessStatus.DUE_FOR_CONFIRMATION
    )


def test_exact_37_days_is_stale() -> None:
    as_of = _T0 + timedelta(days=37)
    assert evaluate_freshness_status(confirmed_at=_T0, as_of=as_of) is FreshnessStatus.STALE


def test_well_past_37_days_is_stale() -> None:
    as_of = _T0 + timedelta(days=365)
    assert evaluate_freshness_status(confirmed_at=_T0, as_of=as_of) is FreshnessStatus.STALE


def test_future_confirmed_at_relative_to_as_of_fails_closed_to_unknown() -> None:
    as_of = _T0
    confirmed_at = _T0 + timedelta(seconds=1)
    assert (
        evaluate_freshness_status(confirmed_at=confirmed_at, as_of=as_of) is FreshnessStatus.UNKNOWN
    )


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_freshness_status(confirmed_at=None, as_of=datetime(2026, 1, 1))  # noqa: DTZ001


def test_naive_confirmed_at_is_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_freshness_status(confirmed_at=datetime(2026, 1, 1), as_of=_T0)  # noqa: DTZ001


def test_freshness_confirmation_id_requires_non_empty_value() -> None:
    with pytest.raises(ValueError):
        FreshnessConfirmationId("")


def test_freshness_confirmation_id_is_runtime_distinct_from_plain_string() -> None:
    fcid = FreshnessConfirmationId("FC-1")
    assert fcid.value == "FC-1"
    assert fcid != "FC-1"  # type: ignore[comparison-overlap]


def test_freshness_policy_rejects_non_positive_ttl_or_grace() -> None:
    with pytest.raises(ValueError):
        FreshnessPolicy(
            policy_id="X", confirmation_ttl=timedelta(0), grace_period=timedelta(days=1)
        )
    with pytest.raises(ValueError):
        FreshnessPolicy(
            policy_id="X", confirmation_ttl=timedelta(days=1), grace_period=timedelta(0)
        )


def test_a_different_named_policy_never_mutates_manual_native_v1() -> None:
    other = FreshnessPolicy(
        policy_id="HYPOTHETICAL_V2",
        confirmation_ttl=timedelta(days=14),
        grace_period=timedelta(days=3),
    )
    assert MANUAL_NATIVE_V1.confirmation_ttl == timedelta(days=30)
    assert MANUAL_NATIVE_V1.grace_period == timedelta(days=7)
    assert other.policy_id != MANUAL_NATIVE_V1.policy_id
