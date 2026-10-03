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
