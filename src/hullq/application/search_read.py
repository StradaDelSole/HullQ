"""Public Search request-state boundary — SLICE-0051.

Implements Required Behavior §1 ("Request-state separation"): given a
locale-prefixed Search route's raw multi-valued query parameters, decide
among exactly the four accepted request states, independent of any HTTP
framework so it stays reusable by FastAPI route tests without spinning up a
`TestClient`:

    zero active criteria             -> BASE  (200, no Search evaluation)
    one canonical draft_max          -> RESULT (runs the bounded vertical)
    valid but non-canonical/duplicate -> REDIRECT (308 to the exact canonical URL)
    invalid/ambiguous/unknown params -> INVALID (400, no Search evaluation)

The accepted initial non-semantic query-parameter allowlist is empty
(`docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`): any key
other than `draft_max` -- including a well-known tracking parameter such as
`utm_source` -- is INVALID, never silently ignored.

This module never decides locale support/routing (`hullq.api.app` and the
Astro route tree own that) and never issues an HTTP response itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.inventory_search import DraftMaxSearchOutcome, evaluate_draft_max_requirement
from hullq.search.draft_max_request import (
    DraftMaxSyntaxError,
    canonical_draft_max_str,
    parse_draft_max_decimal,
)

__all__ = ["SearchOutcomeKind", "SearchRequestOutcome", "evaluate_search_request"]

_DRAFT_MAX_KEY = "draft_max"
_ALLOWED_PARAM_KEYS = frozenset({_DRAFT_MAX_KEY})


class SearchOutcomeKind(StrEnum):
    """The exactly four accepted public Search request states."""

    BASE = "BASE"
    REDIRECT = "REDIRECT"
    INVALID = "INVALID"
    RESULT = "RESULT"


@dataclass(frozen=True, slots=True)
class SearchRequestOutcome:
    """One evaluated public Search request. Exactly one payload matches `kind`.

    `canonical_path` is populated only for `REDIRECT` (server-relative,
    locale-prefixed, e.g. ``/de/search?draft_max=1.6``). `draft_max` and
    `search_outcome` are populated only for `RESULT`.
    """

    kind: SearchOutcomeKind
    canonical_path: str | None = None
    draft_max: Decimal | None = None
    search_outcome: DraftMaxSearchOutcome | None = None

    def __post_init__(self) -> None:
        if self.kind is SearchOutcomeKind.REDIRECT and self.canonical_path is None:
            raise ValueError("A REDIRECT outcome must carry canonical_path")
        if self.kind is not SearchOutcomeKind.REDIRECT and self.canonical_path is not None:
            raise ValueError("Only a REDIRECT outcome may carry canonical_path")
        is_result = self.kind is SearchOutcomeKind.RESULT
        if is_result and (self.draft_max is None or self.search_outcome is None):
            raise ValueError("A RESULT outcome must carry draft_max and search_outcome")
        if not is_result and (self.draft_max is not None or self.search_outcome is not None):
            raise ValueError("Only a RESULT outcome may carry draft_max/search_outcome")


def evaluate_search_request(
    conn: Any, *, locale: str, query_params: Mapping[str, Sequence[str]]
) -> SearchRequestOutcome:
    """Decide the request state for one locale-prefixed Search request.

    *query_params* maps each raw query key to every raw value it carried
    (preserving duplicates) -- callers must not pre-collapse duplicate keys
    before calling this, or the accepted duplicate-handling rules cannot be
    applied.
    """
    if not isinstance(locale, str) or not locale:
        raise ValueError(f"locale must be a non-empty string; got {locale!r}")

    unknown_keys = set(query_params) - _ALLOWED_PARAM_KEYS
    if unknown_keys:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)

    raw_values = list(query_params.get(_DRAFT_MAX_KEY, ()))
    if not raw_values:
        return SearchRequestOutcome(kind=SearchOutcomeKind.BASE)

    parsed_values: list[Decimal] = []
    for raw in raw_values:
        try:
            parsed_values.append(parse_draft_max_decimal(raw))
        except DraftMaxSyntaxError:
            return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)

    distinct_values = set(parsed_values)
    if len(distinct_values) > 1:
        # Conflicting duplicates (e.g. draft_max=1.6&draft_max=1.7) fail
        # closed as INVALID -- never silently pick one.
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)

    draft_max = parsed_values[0]
    canonical_value = canonical_draft_max_str(draft_max)
    is_single_canonical = len(raw_values) == 1 and raw_values[0] == canonical_value
    if not is_single_canonical:
        return SearchRequestOutcome(
            kind=SearchOutcomeKind.REDIRECT,
            canonical_path=f"/{locale}/search?{_DRAFT_MAX_KEY}={canonical_value}",
        )

    search_outcome = evaluate_draft_max_requirement(conn, draft_max)
    return SearchRequestOutcome(
        kind=SearchOutcomeKind.RESULT, draft_max=draft_max, search_outcome=search_outcome
    )
