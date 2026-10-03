"""In-process bounded request-rate protection — SLICE-0078.

HullQ's accepted deployment baseline (ADR-0010) is a single application
process on one VPS with no distributed cache/broker. A fixed-window counter
keyed per-process is therefore sufficient as a defense-in-depth bound against
unbounded abuse (credential-stuffing attempts, buyer-contact/Lead spam,
upload-storage-cost abuse) ahead of whatever the edge/CDN layer eventually
adds; it intentionally does not attempt distributed/multi-instance accuracy.

Each protected route category gets its own `FixedWindowRateLimiter` instance,
created fresh inside `create_app()` so every test/app instance starts with an
empty window (no cross-test leakage) and so one route category's traffic can
never consume another's budget.
"""

from __future__ import annotations

import time
from collections.abc import Callable

__all__ = ["FixedWindowRateLimiter"]


class FixedWindowRateLimiter:
    """Fixed-window per-key request counter.

    `allow(key)` returns `True` while the caller identified by *key* remains
    at or under *limit* requests within the current *window_seconds* window,
    and `False` once that budget is exhausted; the window for a key resets
    once *window_seconds* have elapsed since that key's first request in the
    current window. Unknown/absent keys are the caller's responsibility to
    normalize (e.g. a fixed placeholder for a missing client address) —
    this class never special-cases `None`.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._windows: dict[str, tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        now = self._clock()
        window_start, count = self._windows.get(key, (now, 0))
        if now - window_start >= self._window_seconds:
            window_start, count = now, 0
        count += 1
        self._windows[key] = (window_start, count)
        return count <= self._limit
