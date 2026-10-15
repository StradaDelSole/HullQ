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

SLICE-0056 independent-review Finding 2: with two public criteria, incoming
key *order* is itself now an observable non-canonicalization defect --
`docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md` requires
active technical parameters to be lexicographically ordered (`draft_max`
before `keel_configuration`), and `docs/
OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md` requires a
semantically valid but non-canonically ordered request to 308-redirect
rather than remain a second successful `200` identity. A request whose
active keys arrive in a different order (e.g.
`?keel_configuration=FIN&draft_max=1.6`) is therefore folded into the same
REDIRECT path as a non-canonical *value* (e.g. `draft_max=1.600`), using the
caller's preserved raw key order (see *query_params* below) -- this is a
structural key-order comparison, not a second URL parser, and never
overrides INVALID precedence for malformed/ambiguous/unknown content.

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
from hullq.search.criteria_registry import (
    CANONICAL_PARAM_KEY_ORDER,
    COCKPIT_POSITION_DEFINITION,
    COCKPIT_POSITION_PARAM_KEY,
    DECK_SALOON_DEFINITION,
    DECK_SALOON_PARAM_KEY,
    DRAFT_MAX_DEFINITION,
    DRAFT_MAX_PARAM_KEY,
    HULL_CONFIGURATION_DEFINITION,
    HULL_CONFIGURATION_PARAM_KEY,
    KEEL_CONFIGURATION_DEFINITION,
    KEEL_CONFIGURATION_PARAM_KEY,
    LOA_DEFINITION,
    LOA_MAX_PARAM_KEY,
    LOA_MIN_PARAM_KEY,
    RUDDER_CONFIGURATION_DEFINITION,
    RUDDER_CONFIGURATION_PARAM_KEY,
    SUPPORTED_PARAM_KEYS,
    parse_categorical_param,
    parse_numeric_param,
)

__all__ = [
    "SearchOutcomeKind",
    "SearchRequestOutcome",
    "build_canonical_search_path",
    "evaluate_requirement_search_outcome",
    "evaluate_search_request",
]

_DRAFT_MAX_KEY = DRAFT_MAX_PARAM_KEY
_KEEL_CONFIGURATION_KEY = KEEL_CONFIGURATION_PARAM_KEY
_LOA_MIN_KEY = LOA_MIN_PARAM_KEY
_LOA_MAX_KEY = LOA_MAX_PARAM_KEY
_RUDDER_CONFIGURATION_KEY = RUDDER_CONFIGURATION_PARAM_KEY
_HULL_CONFIGURATION_KEY = HULL_CONFIGURATION_PARAM_KEY
_COCKPIT_POSITION_KEY = COCKPIT_POSITION_PARAM_KEY
_DECK_SALOON_KEY = DECK_SALOON_PARAM_KEY
_ALLOWED_PARAM_KEYS = SUPPORTED_PARAM_KEYS


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
    loa_min: Decimal | None = None
    loa_max: Decimal | None = None
    rudder_configuration: str | None = None
    hull_configuration: str | None = None
    cockpit_position: str | None = None
    deck_saloon: str | None = None
    search_outcome: DraftMaxSearchOutcome | NativeInventorySearchOutcome | None = None

    def __post_init__(self) -> None:
        if self.kind is SearchOutcomeKind.REDIRECT and self.canonical_path is None:
            raise ValueError("A REDIRECT outcome must carry canonical_path")
        if self.kind is not SearchOutcomeKind.REDIRECT and self.canonical_path is not None:
            raise ValueError("Only a REDIRECT outcome may carry canonical_path")
        is_result = self.kind is SearchOutcomeKind.RESULT
        active_values = (
            self.draft_max,
            self.keel_configuration,
            self.loa_min,
            self.loa_max,
            self.rudder_configuration,
            self.hull_configuration,
            self.cockpit_position,
            self.deck_saloon,
        )
        if is_result:
            if self.search_outcome is None:
                raise ValueError("A RESULT outcome must carry search_outcome")
            if all(value is None for value in active_values):
                raise ValueError("A RESULT outcome must carry at least one active criterion")
        elif any(value is not None for value in active_values) or self.search_outcome is not None:
            raise ValueError(
                "Only a RESULT outcome may carry an active criterion value/search_outcome"
            )


def build_canonical_search_path(
    locale: str,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
) -> str:
    """Build the one canonical, sparse, lexicographically-ordered public
    Direct Search path for *locale* (`docs/
    OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`, extended
    SLICE-0085 to all five accepted keys via
    `hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER`): only the
    active criteria are included, each rendered through its own
    canonicalization (`canonical_draft_max_str`/`canonical_loa_str`; `keel_configuration`/
    `rudder_configuration` are already their own canonical spelling).

    Shared by this module's own REDIRECT canonicalization and SLICE-0057's
    buyer-requirement-sensitivity `alternative_search_path` (contract §9:
    "The canonical path MUST be built/owned by the Python/FastAPI Search
    boundary") -- the only place the exact canonical-URL construction rule
    is expressed.
    """
    assert DRAFT_MAX_DEFINITION.canonicalize_value is not None
    assert LOA_DEFINITION.canonicalize_value is not None
    rendered: dict[str, str] = {}
    if draft_max is not None:
        rendered[_DRAFT_MAX_KEY] = DRAFT_MAX_DEFINITION.canonicalize_value(draft_max)
    if keel_configuration is not None:
        rendered[_KEEL_CONFIGURATION_KEY] = keel_configuration
    if loa_max is not None:
        rendered[_LOA_MAX_KEY] = LOA_DEFINITION.canonicalize_value(loa_max)
    if loa_min is not None:
        rendered[_LOA_MIN_KEY] = LOA_DEFINITION.canonicalize_value(loa_min)
    if rudder_configuration is not None:
        rendered[_RUDDER_CONFIGURATION_KEY] = rudder_configuration
    if hull_configuration is not None:
        rendered[_HULL_CONFIGURATION_KEY] = hull_configuration
    if cockpit_position is not None:
        rendered[_COCKPIT_POSITION_KEY] = cockpit_position
    if deck_saloon is not None:
        rendered[_DECK_SALOON_KEY] = deck_saloon
    parts = [f"{key}={rendered[key]}" for key in CANONICAL_PARAM_KEY_ORDER if key in rendered]
    if not parts:
        return f"/{locale}/search"
    return f"/{locale}/search?{'&'.join(parts)}"


def evaluate_requirement_search_outcome(
    conn: Any,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    as_of: datetime,
) -> DraftMaxSearchOutcome | NativeInventorySearchOutcome:
    """Evaluate one already-canonical requirement through the accepted Search
    truth: a pure `draft_max` requirement keeps the unmodified SLICE-0051
    `evaluate_draft_max_requirement`; any requirement involving
    `keel_configuration`/`loa_min`/`loa_max`/`rudder_configuration` uses the
    SLICE-0055 (extended SLICE-0085) `evaluate_native_inventory_requirements`
    funnel instead (this module's docstring explains why).

    Shared by `evaluate_search_request` (below) and SLICE-0057's buyer-
    requirement-sensitivity application service, so "one Search truth,
    evaluated twice" (contract §6) is a literal call-site fact, not merely a
    documented intent -- there is exactly one dispatch point between the two
    accepted Search outcome types.
    """
    if (
        keel_configuration is None
        and loa_min is None
        and loa_max is None
        and rudder_configuration is None
        and hull_configuration is None
        and cockpit_position is None
        and deck_saloon is None
    ):
        assert draft_max is not None
        return evaluate_draft_max_requirement(conn, draft_max, as_of=as_of)
    return evaluate_native_inventory_requirements(
        conn,
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        as_of=as_of,
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
    loa_min_raw_values = list(query_params.get(_LOA_MIN_KEY, ()))
    loa_max_raw_values = list(query_params.get(_LOA_MAX_KEY, ()))
    rudder_raw_values = list(query_params.get(_RUDDER_CONFIGURATION_KEY, ()))
    hull_raw_values = list(query_params.get(_HULL_CONFIGURATION_KEY, ()))
    cockpit_raw_values = list(query_params.get(_COCKPIT_POSITION_KEY, ()))
    deck_saloon_raw_values = list(query_params.get(_DECK_SALOON_KEY, ()))

    if not (
        draft_raw_values
        or keel_raw_values
        or loa_min_raw_values
        or loa_max_raw_values
        or rudder_raw_values
        or hull_raw_values
        or cockpit_raw_values
        or deck_saloon_raw_values
    ):
        return SearchRequestOutcome(kind=SearchOutcomeKind.BASE)

    # Independent review Finding 2: `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`
    # requires the canonical URL to order active technical parameters
    # lexicographically (`hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER`,
    # extended SLICE-0085 to all five accepted criteria); `docs/
    # OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md` requires a
    # semantically valid but non-canonically ordered request to 308-redirect
    # rather than remain a second successful 200 identity. `query_params`
    # already preserves the caller's raw incoming key order (its docstring
    # above) -- comparing that order against the fixed canonical order below
    # is a structural check independent of value validity, so it is safe to
    # compute unconditionally here and combine with the existing per-value
    # canonicalization flags before deciding REDIRECT vs RESULT.
    canonical_active_key_order = [key for key in CANONICAL_PARAM_KEY_ORDER if key in query_params]
    actual_active_key_order = [key for key in query_params if key in _ALLOWED_PARAM_KEYS]
    order_is_canonical = actual_active_key_order == canonical_active_key_order

    # Review amendment Finding C: every criterion's own raw-value parsing/
    # validation now goes through `hullq.search.criteria_registry.
    # parse_numeric_param`/`parse_categorical_param`, driven by each
    # `CriterionDefinition`'s own `parse_value`/`canonicalize_value`/
    # `allowed_values` -- replacing four previously hand-duplicated
    # per-criterion blocks. Both helpers share this exact convention: `None`
    # means genuinely INVALID (unsupported value, or conflicting differing
    # duplicates); otherwise `(value, is_single_canonical)`, where
    # `is_single_canonical` is `False` for ANY duplicate (even of an
    # identical value) or non-canonical spelling -- exactly the REDIRECT
    # trigger this function already required.
    draft_result = parse_numeric_param(DRAFT_MAX_DEFINITION, draft_raw_values)
    if draft_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    draft_max, draft_is_single_canonical = draft_result

    keel_result = parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, keel_raw_values)
    if keel_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    keel_configuration, keel_is_single_canonical = keel_result

    loa_min_result = parse_numeric_param(LOA_DEFINITION, loa_min_raw_values)
    if loa_min_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    loa_min, loa_min_is_single_canonical = loa_min_result

    loa_max_result = parse_numeric_param(LOA_DEFINITION, loa_max_raw_values)
    if loa_max_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    loa_max, loa_max_is_single_canonical = loa_max_result

    if loa_min is not None and loa_max is not None and loa_min > loa_max:
        # Slice normative LOA semantics: "Require loa_min <= loa_max
        # whenever both supplied" -- never silently swapped or clamped.
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)

    rudder_result = parse_categorical_param(RUDDER_CONFIGURATION_DEFINITION, rudder_raw_values)
    if rudder_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    rudder_configuration, rudder_is_single_canonical = rudder_result

    hull_result = parse_categorical_param(HULL_CONFIGURATION_DEFINITION, hull_raw_values)
    if hull_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    hull_configuration, hull_is_single_canonical = hull_result

    cockpit_result = parse_categorical_param(COCKPIT_POSITION_DEFINITION, cockpit_raw_values)
    if cockpit_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    cockpit_position, cockpit_is_single_canonical = cockpit_result

    deck_saloon_result = parse_categorical_param(DECK_SALOON_DEFINITION, deck_saloon_raw_values)
    if deck_saloon_result is None:
        return SearchRequestOutcome(kind=SearchOutcomeKind.INVALID)
    deck_saloon, deck_saloon_is_single_canonical = deck_saloon_result

    if not (
        draft_is_single_canonical
        and keel_is_single_canonical
        and loa_min_is_single_canonical
        and loa_max_is_single_canonical
        and rudder_is_single_canonical
        and hull_is_single_canonical
        and cockpit_is_single_canonical
        and deck_saloon_is_single_canonical
        and order_is_canonical
    ):
        return SearchRequestOutcome(
            kind=SearchOutcomeKind.REDIRECT,
            canonical_path=build_canonical_search_path(
                locale,
                draft_max=draft_max,
                keel_configuration=keel_configuration,
                loa_min=loa_min,
                loa_max=loa_max,
                rudder_configuration=rudder_configuration,
                hull_configuration=hull_configuration,
                cockpit_position=cockpit_position,
                deck_saloon=deck_saloon,
            ),
        )

    search_outcome = evaluate_requirement_search_outcome(
        conn,
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        as_of=as_of,
    )
    return SearchRequestOutcome(
        kind=SearchOutcomeKind.RESULT,
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        search_outcome=search_outcome,
    )
