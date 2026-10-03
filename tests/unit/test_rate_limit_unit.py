"""Unit tests for `hullq.security.rate_limit.FixedWindowRateLimiter` — SLICE-0078."""

from __future__ import annotations

import pytest

from hullq.security.rate_limit import FixedWindowRateLimiter


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestConstruction:
    def test_rejects_non_positive_limit(self) -> None:
        with pytest.raises(ValueError):
            FixedWindowRateLimiter(limit=0, window_seconds=60.0)

    def test_rejects_non_positive_window(self) -> None:
        with pytest.raises(ValueError):
            FixedWindowRateLimiter(limit=5, window_seconds=0.0)

    def test_rejects_non_positive_max_keys(self) -> None:
        with pytest.raises(ValueError):
            FixedWindowRateLimiter(limit=5, window_seconds=60.0, max_keys=0)


class TestAllow:
    def test_allows_up_to_the_limit_then_blocks(self) -> None:
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=3, window_seconds=60.0, clock=clock)
        assert [limiter.allow("k") for _ in range(3)] == [True, True, True]
        assert limiter.allow("k") is False
        assert limiter.allow("k") is False

    def test_window_resets_after_elapsed_seconds(self) -> None:
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=2, window_seconds=10.0, clock=clock)
        assert limiter.allow("k") is True
        assert limiter.allow("k") is True
        assert limiter.allow("k") is False
        clock.advance(10.0)
        assert limiter.allow("k") is True

    def test_window_does_not_reset_before_elapsed_seconds(self) -> None:
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=1, window_seconds=10.0, clock=clock)
        assert limiter.allow("k") is True
        clock.advance(9.999)
        assert limiter.allow("k") is False

    def test_keys_are_independent(self) -> None:
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=1, window_seconds=60.0, clock=clock)
        assert limiter.allow("alice") is True
        assert limiter.allow("alice") is False
        assert limiter.allow("bob") is True

    def test_default_clock_is_monotonic_time(self) -> None:
        # No injected clock: must not raise, and must behave consistently
        # with real wall-clock progression (smoke-level only).
        limiter = FixedWindowRateLimiter(limit=2, window_seconds=60.0)
        assert limiter.allow("k") is True
        assert limiter.allow("k") is True
        assert limiter.allow("k") is False


class TestBoundedRetainedState:
    """SLICE-0078 independent-review finding A: an attacker able to generate
    many distinct keys must never grow retained state without bound, and
    stale/expired keys must actually be reclaimed rather than only capped.
    """

    def test_ordinary_within_window_counting_is_unchanged(self) -> None:
        # Requirement 1: the bounded-state mechanism must not alter the
        # plain fixed-window semantics proven by TestAllow above.
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=3, window_seconds=60.0, max_keys=100, clock=clock)
        assert [limiter.allow("k") for _ in range(3)] == [True, True, True]
        assert limiter.allow("k") is False
        clock.advance(60.0)
        assert limiter.allow("k") is True

    def test_expired_inactive_keys_are_reclaimed(self) -> None:
        # Requirement 2: a realistic cardinality-explosion shape -- many
        # distinct keys, each used once and never reused -- must actually
        # shrink retained state back down once their window has lapsed,
        # not merely stay capped at max_keys forever.
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=5, window_seconds=10.0, max_keys=1_000, clock=clock)
        for i in range(200):
            limiter.allow(f"burst-{i}")
        assert len(limiter._windows) == 200

        clock.advance(10.0)
        # A single call for one brand-new key must trigger reclaim of every
        # now-expired entry, not just make room for the one new key.
        limiter.allow("after-the-burst")
        assert len(limiter._windows) == 1
        assert "after-the-burst" in limiter._windows

    def test_hard_cap_bounds_retained_state_under_unique_key_flood(self) -> None:
        # Requirement 3: even when every single request uses a never-before-
        # seen key *within the same window* (so nothing has expired yet to
        # reclaim), retained state must never exceed max_keys.
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=5, window_seconds=60.0, max_keys=50, clock=clock)
        for i in range(5_000):
            limiter.allow(f"attacker-key-{i}")
            assert len(limiter._windows) <= 50

        assert len(limiter._windows) == 50

    def test_active_key_survives_eviction_pressure_from_a_key_flood(self) -> None:
        # Requirement 4: a legitimate, actively-reused key must keep
        # receiving deterministic bounded behavior even while a flood of
        # distinct brand-new keys is forcing continuous cleanup/eviction --
        # eviction pressure must fall on the cold/never-reused flood keys,
        # never on the key that keeps actually being used.
        clock = _FakeClock()
        limiter = FixedWindowRateLimiter(limit=3, window_seconds=60.0, max_keys=10, clock=clock)
        assert limiter.allow("legit") is True

        for i in range(500):
            limiter.allow(f"flood-{i}")
            # "legit" is touched between every flood key, keeping it the
            # most-recently-used entry and therefore never the eviction
            # target.
            limiter.allow("legit")

        assert len(limiter._windows) <= 10
        assert "legit" in limiter._windows
        # "legit" has now been called 502 times total (1 + 500*1, since
        # the loop above calls it once per iteration) well past its
        # limit=3 -- its own counting must still be deterministic and
        # bounded exactly like any ordinary key, unaffected by the
        # surrounding cleanup/eviction traffic.
        assert limiter.allow("legit") is False

    def test_route_category_independence_preserved_with_bounded_state(self) -> None:
        # Requirement 5: bounded-state eviction in one route category's
        # limiter instance must never observe or affect another's, exactly
        # like the unbounded-state version's independence guarantee.
        clock = _FakeClock()
        contact_limiter = FixedWindowRateLimiter(
            limit=5, window_seconds=60.0, max_keys=3, clock=clock
        )
        login_limiter = FixedWindowRateLimiter(
            limit=20, window_seconds=60.0, max_keys=3, clock=clock
        )
        for i in range(50):
            contact_limiter.allow(f"flood-{i}")
        assert len(contact_limiter._windows) <= 3
        assert len(login_limiter._windows) == 0

        assert login_limiter.allow("same-shaped-key") is True
        assert len(login_limiter._windows) == 1
