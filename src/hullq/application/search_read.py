"""Public Search request-state boundary — SLICE-0051 (+ SLICE-0055 criterion #2).

Implements Required Behavior §1 ("Request-state separation"): given a
locale-prefixed Search route's raw multi-valued query parameters, decide
among exactly the four accepted request states, independent of any HTTP
framework so it stays reusable by FastAPI route tests without spinning up a
`TestClient`:

    zero active criteria                     -> BASE  (200, no Search evaluation)
    one canonical draft_max and/or keel_configuration -> RESULT (runs the bounded vertical)
    valid but non-canonical/duplicate value(s) -> REDIRECT (308 to the exact canonical URL)
    invalid/ambiguous/unknown params           -> INVALID (400, no Search evaluation)

The accepted initial non-semantic query-parameter allowlist is empty
(`docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`): any key
other than `draft_max`/`keel_configuration` -- including a well-known
tracking parameter such as `utm_source` -- is INVALID, never silently
ignored.

SLICE-0055 adds `keel_configuration` (contract §2/§8): each criterion MAY be
used alone; when both are supplied they are MUST leaves combined by the
existing deterministic AND semantics. A pure `draft_max` request keeps
calling the unmodified SLICE-0051 `evaluate_draft_max_requirement` (contract
§8: "A request containing only draft_max MUST retain accepted SLICE-0051
behavior"); a request involving `keel_configuration` (alone or with
`draft_max`) uses the SLICE-0055
`hullq.application.native_inventory_query.evaluate_native_inventory_requirements`
funnel instead. Unlike `draft_max`'s arbitrary-precision decimal
canonicalization, `keel_configuration`'s accepted v0.1 values are already
exact canonical spellings -- no redigitting occurs, only exact-set
membership validation.

This module never decides locale support/routing (`hullq.api.app` and the
Astro route tree own that) and never issues an HTTP response itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.inventory_search import DraftMaxSearchOutcome, evaluate_draft_max_requirement
from hullq.application.native_inventory_query import (
    NativeInventorySearchOutcome,
    evaluate_native_inventory_requirements,
)
from hullq.search.draft_max_request import (
    DraftMaxSyntaxError,
    canonical_draft_max_str,
    parse_draft_max_decimal,
)
from hullq.search.keel_design_bridge import SEARCH_KEEL_CONFIGURATION_VALUES

__all__ = ["SearchOutcomeKind", "SearchRequestOutcome", "evaluate_search_request"]

_DRAFT_MAX_KEY = "draft_max"
_KEEL_CONFIGURATION_KEY = "keel_configuration"
_ALLOWED_PARAM_KEYS = frozenset({_DRAFT_MAX_KEY, _KEEL_CONFIGURATION_KEY})


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
    locale-prefixed, e.g. ``/de/search?draft_max=1.6``). `draft_max`/
    `keel_configuration`/`search_outcome` are populated only for `RESULT`;
    exactly one of `draft_max`/`keel_configuration` may still be `None` on a
    `RESULT` (whichever criterion was not supplied), but not both.
    `search_outcome` is a `DraftMaxSearchOutcome` for a pure `draft_max`
    request (SLICE-0051, unchanged) or a `NativeInventorySearchOutcome` for
    any request involving `keel_configuration` (SLICE-0055).
    """

    kind: SearchOutcomeKind
    canonical_path: str | None = None
    draft_max: Decimal | None = None
    keel_configuration: str | None = None
    search_outcome: DraftMaxSearchOutcome | NativeInventorySearchOutcome | None = None

    def __post_init__(self) -> None:
        if self.kind is SearchOutcomeKind.REDIRECT and self.canonical_path is None:
            raise ValueError("A REDIRECT outcome must carry canonical_path")
        if self.kind is not SearchOutcomeKind.REDIRECT and self.canonical_path is not None:
            raise ValueError("Only a REDIRECT outcome may carry canonical_path")
        is_result = self.kind is SearchOutcomeKind.RESULT
        if is_result:
            if self.search_outcome is None:
                raise ValueError("A RESULT outcome must carry search_outcome")
            if self.draft_max is None and self.keel_configuration is None:
                raise ValueError("A RESULT outcome must carry draft_max and/or keel_configuration")
        elif (
            self.draft_max is not None
            or self.keel_configuration is not None
            or self.search_outcome is not None
        ):
            raise ValueError(
                "Only a RESULT outcome may carry draft_max/keel_configuration/search_outcome"
            )


def evaluate_search_request(
    conn: Any, *, locale: str, query_params: Mapping[str, Sequence[str]], as_of: datetime
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

    draft_raw_values = list(query_params.get(_DRAFT_MAX_KEY, ()))
    keel_raw_values = list(query_params.get(_KEEL_CONFIGURATION_KEY, ()))

    if not draft_raw_values and not keel_raw_values:
        return SearchRequestOutcome(kind=SearchOutcomeKind.BASE)

    draft_max: Decimal | None = None
    draft_canonical: str | None = None
    draft_is_single_canonical = True
    if draft_raw_values:
        parsed_values: list[Decimal] = []
        for raw in draft_raw_values:
            try:
                parsed_values.append(parse_draft_max_decimal(raw))
            except DraftMaxSyntaxError:
                return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
        if len(set(parsed_values)) > 1:
            # Conflicting duplicates (e.g. draft_max=1.6&draft_max=1.7) fail
            # closed as INVALID -- never silently pick one.
            return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
        draft_max = parsed_values[0]
        draft_canonical = canonical_draft_max_str(draft_max)
        draft_is_single_canonical = (
            len(draft_raw_values) == 1 and draft_raw_values[0] == draft_canonical
        )

    keel_configuration: str | None = None
    keel_is_single_canonical = True
    if keel_raw_values:
        for raw in keel_raw_values:
            if raw not in SEARCH_KEEL_CONFIGURATION_VALUES:
                # Unsupported/unknown value fails closed as INVALID -- never
                # fuzzy-matched or silently normalized (contract §A/§8).
                return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
        if len(set(keel_raw_values)) > 1:
            # Conflicting duplicates fail closed as INVALID, mirroring
            # draft_max -- never silently pick one.
            return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
        keel_configuration = keel_raw_values[0]
        # Every accepted v0.1 value is already its own canonical spelling
        # (no redigitting like draft_max) -- only duplication itself (even
        # of an identical value) is non-canonical.
        keel_is_single_canonical = len(keel_raw_values) == 1

    if not (draft_is_single_canonical and keel_is_single_canonical):
        parts = []
        if draft_max is not None:
            assert draft_canonical is not None
            parts.append(f"{_DRAFT_MAX_KEY}={draft_canonical}")
        if keel_configuration is not None:
            parts.append(f"{_KEEL_CONFIGURATION_KEY}={keel_configuration}")
        return SearchRequestOutcome(
            kind=SearchOutcomeKind.REDIRECT,
            canonical_path=f"/{locale}/search?{'&'.join(parts)}",
        )

    search_outcome: DraftMaxSearchOutcome | NativeInventorySearchOutcome
    if keel_configuration is None:
        assert draft_max is not None
        search_outcome = evaluate_draft_max_requirement(conn, draft_max, as_of=as_of)
    else:
        search_outcome = evaluate_native_inventory_requirements(
            conn, draft_max=draft_max, keel_configuration=keel_configuration, as_of=as_of
        )
    return SearchRequestOutcome(
        kind=SearchOutcomeKind.RESULT,
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        search_outcome=search_outcome,
    )
