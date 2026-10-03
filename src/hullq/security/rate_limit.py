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

SLICE-0078 independent review (finding A): the mitigation for unbounded
request abuse must not itself introduce attacker-controlled unbounded
in-memory state. An attacker who can generate many distinct keys (e.g. a
spoofed/rotating client address on the contact/login limiters) must never be
able to grow retained state past a fixed bound just by sending traffic that
is otherwise correctly rate-limited per key. `FixedWindowRateLimiter`
therefore retains at most `max_keys` entries at any time, via an LRU-ordered
`OrderedDict`: every `allow()` call first reclaims any entries whose window
has already fully expired (cheap and amortized, since expired/inactive keys
sit at the LRU-oldest end and a never-reused key is never touched again), and
only if a genuinely new key still can't fit does it evict the single
least-recently-touched entry to make room. A key that keeps being reused
(the normal case for a real abusive or legitimate caller) is always
most-recently-touched, so it is never the one evicted under cardinality
pressure — eviction pressure falls on cold/expired keys first.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable

__all__ = ["FixedWindowRateLimiter"]

#: Generous enough that no realistic single-process deployment legitimately
#: tracks this many simultaneously-active distinct keys (client addresses or
#: account ids) within one window, while still capping worst-case retained
#: memory to a small, fixed amount (each entry is one short string key plus
#: a `(float, int)` tuple — tens of thousands of entries is a few MB, not an
#: unbounded leak) regardless of how many distinct keys an attacker sends.
_DEFAULT_MAX_KEYS = 10_000


class FixedWindowRateLimiter:
    """Fixed-window per-key request counter with bounded retained state.

    `allow(key)` returns `True` while the caller identified by *key* remains
    at or under *limit* requests within the current *window_seconds* window,
    and `False` once that budget is exhausted; the window for a key resets
    once *window_seconds* have elapsed since that key's first request in the
    current window. Unknown/absent keys are the caller's responsibility to
    normalize (e.g. a fixed placeholder for a missing client address) —
    this class never special-cases `None`.

    Retained state never exceeds `max_keys` entries: every call first
    reclaims keys whose window has fully expired, and if a brand-new key
    still would not fit, the single least-recently-touched entry is evicted.
    A key that is actively being reused — the normal shape of a real
    sustained-abuse attempt against *that* key — is always most recently
    touched and therefore never the eviction target.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        max_keys: int = _DEFAULT_MAX_KEYS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if max_keys < 1:
            raise ValueError("max_keys must be >= 1")
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_keys = max_keys
        self._clock = clock
        # Insertion/access order == least-recently-touched -> most-recently-
        # touched. A key is moved to the most-recently-touched end on every
        # access (both a fresh insert and a re-touch of an existing key).
        self._windows: OrderedDict[str, tuple[float, int]] = OrderedDict()

    def allow(self, key: str) -> bool:
        now = self._clock()
        self._reclaim_expired(now)

        existing = self._windows.pop(key, None)
        if existing is not None:
            window_start, count = existing
            if now - window_start >= self._window_seconds:
                window_start, count = now, 0
        else:
            if len(self._windows) >= self._max_keys:
                # Hard cap reached by genuinely distinct keys even after
                # reclaiming every expired one: evict the single coldest
                # (least-recently-touched) entry rather than let retained
                # state grow past max_keys.
                self._windows.popitem(last=False)
            window_start, count = now, 0

        count += 1
        self._windows[key] = (window_start, count)
        return count <= self._limit

    def _reclaim_expired(self, now: float) -> None:
        """Evict every entry whose window has fully lapsed.

        Expired/inactive entries are, by construction, the
        least-recently-touched ones (a key that keeps getting traffic keeps
        getting moved to the recently-touched end), so this only ever needs
        to look at the front of the ordering and can stop at the first
        still-live entry.
        """
        while self._windows:
            _, (window_start, _count) = next(iter(self._windows.items()))
            if now - window_start < self._window_seconds:
                break
            self._windows.popitem(last=False)
