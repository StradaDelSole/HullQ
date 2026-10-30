"""Public Power-only Search request-state boundary — SLICE-0093, extended
SLICE-0094.

The Power-domain counterpart of `hullq.application.search_read`, bounded to
the two accepted public keys `power_drive`
(`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`) and
`power_engine_count`
(`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md`, "Request, result and
canonical URL"). Decides among the identical four accepted request states
(Required Behavior parity with the Sail boundary), independent of any HTTP
framework:

    zero active criteria   -> BASE      (200, no Search evaluation)
    one canonical power_drive and/or power_engine_count -> RESULT
    valid but non-canonical/duplicate value(s)/order -> REDIRECT (308)
    invalid/unknown params -> INVALID   (400, no Search evaluation)

This module never accepts a Sail key, and the existing `hullq.application
.search_read` module never accepts `power_drive`/`power_engine_count` --
two entirely separate parsers (contract §3: "Do not widen Sail parser to
accept Power keys"). Locale support/routing stays `hullq.api.app`/the Astro
route tree's job, not decided here.

SLICE-0094 mirrors `hullq.application.search_read`'s own two-criterion
canonical-ordering/REDIRECT discipline exactly (`docs/
OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`/`docs/
OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md`, extended here
to the Power surface): active key order must be canonical
(`power_drive` before `power_engine_count`), and either criterion may be
supplied alone or combined. A pure `power_drive`-only request still reaches
the byte-for-byte unmodified SLICE-0093
`hullq.application.power_inventory_query.evaluate_power_drive_requirement`
via `evaluate_power_requirement`'s own internal dispatch -- never a second,
independently-timed equivalent for that case.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.power_inventory_query import (
    PowerSearchOutcome,
    evaluate_power_requirement,
)
from hullq.search.power_criteria_registry import (
    CANONICAL_POWER_PARAM_KEY_ORDER,
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    POWER_DRIVE_PARAM_KEY,
    POWER_ENGINE_COUNT_DEFINITION,
    POWER_ENGINE_COUNT_PARAM_KEY,
    SUPPORTED_POWER_PARAM_KEYS,
    parse_categorical_param,
    parse_numeric_param,
)

__all__ = [
    "PowerSearchOutcomeKind",
    "PowerSearchRequestOutcome",
    "PowerSearchRequestShape",
    "build_canonical_power_search_path",
    "decide_power_search_request_shape",
    "evaluate_power_search_request",
]

_ALLOWED_PARAM_KEYS = SUPPORTED_POWER_PARAM_KEYS


class PowerSearchOutcomeKind(StrEnum):
    """The exactly four accepted public Power Search request states --
    identical shape to `hullq.application.search_read.SearchOutcomeKind`."""

    BASE = "BASE"
    REDIRECT = "REDIRECT"
    INVALID = "INVALID"
    RESULT = "RESULT"


@dataclass(frozen=True, slots=True)
class PowerSearchRequestOutcome:
    """One evaluated public Power Search request. Exactly one payload
    matches `kind`.

    SLICE-0094: `power_drive`/`power_engine_count` are each independently
    optional on a `RESULT` -- at least one is present, but not necessarily
    both (mirrors `hullq.application.search_read.SearchRequestOutcome`'s
    identical multi-criterion shape).
    """

    kind: PowerSearchOutcomeKind
    canonical_path: str | None = None
    power_drive: str | None = None
    power_engine_count: Decimal | None = None
    search_outcome: PowerSearchOutcome | None = None

    def __post_init__(self) -> None:
        if self.kind is PowerSearchOutcomeKind.REDIRECT and self.canonical_path is None:
            raise ValueError("A REDIRECT outcome must carry canonical_path")
        if self.kind is not PowerSearchOutcomeKind.REDIRECT and self.canonical_path is not None:
            raise ValueError("Only a REDIRECT outcome may carry canonical_path")
        is_result = self.kind is PowerSearchOutcomeKind.RESULT
        active_values = (self.power_drive, self.power_engine_count)
        if is_result:
            if self.search_outcome is None:
                raise ValueError("A RESULT outcome must carry search_outcome")
            if all(value is None for value in active_values):
                raise ValueError("A RESULT outcome must carry at least one active criterion")
        elif any(value is not None for value in active_values) or self.search_outcome is not None:
            raise ValueError(
                "Only a RESULT outcome may carry power_drive/power_engine_count/search_outcome"
            )


@dataclass(frozen=True, slots=True)
class PowerSearchRequestShape:
    """SLICE-0096 (independent review Finding A): the decided request
    STATE/SHAPE only -- mirrors `hullq.application.search_read
    .SearchRequestShape`'s identical rationale for the Power surface. The
    public bounded-page Power route uses this directly, never
    `evaluate_power_requirement`'s complete unbounded evaluation.
    """

    kind: PowerSearchOutcomeKind
    canonical_path: str | None = None
    power_drive: str | None = None
    power_engine_count: Decimal | None = None

    def __post_init__(self) -> None:
        if self.kind is PowerSearchOutcomeKind.REDIRECT and self.canonical_path is None:
            raise ValueError("A REDIRECT shape must carry canonical_path")
        if self.kind is not PowerSearchOutcomeKind.REDIRECT and self.canonical_path is not None:
            raise ValueError("Only a REDIRECT shape may carry canonical_path")
        is_result = self.kind is PowerSearchOutcomeKind.RESULT
        active_values = (self.power_drive, self.power_engine_count)
        if is_result:
            if all(value is None for value in active_values):
                raise ValueError("A RESULT shape must carry at least one active criterion")
        elif any(value is not None for value in active_values):
            raise ValueError("Only a RESULT shape may carry power_drive/power_engine_count")


def build_canonical_power_search_path(
    locale: str, *, power_drive: str | None, power_engine_count: Decimal | None = None
) -> str:
    """Build the one canonical, sparse, lexicographically-ordered public
    Power Search path for *locale* -- only the active criteria are
    included, each rendered through its own canonicalization; the accepted
    canonical key order is `power_drive` then `power_engine_count`
    (`hullq.search.power_criteria_registry.CANONICAL_POWER_PARAM_KEY_ORDER`).
    """
    assert POWER_ENGINE_COUNT_DEFINITION.canonicalize_value is not None
    rendered: dict[str, str] = {}
    if power_drive is not None:
        rendered[POWER_DRIVE_PARAM_KEY] = power_drive
    if power_engine_count is not None:
        rendered[POWER_ENGINE_COUNT_PARAM_KEY] = POWER_ENGINE_COUNT_DEFINITION.canonicalize_value(
            power_engine_count
        )
    parts = [f"{key}={rendered[key]}" for key in CANONICAL_POWER_PARAM_KEY_ORDER if key in rendered]
    if not parts:
        return f"/{locale}/power/search"
    return f"/{locale}/power/search?{'&'.join(parts)}"


def decide_power_search_request_shape(
    *, locale: str, query_params: Mapping[str, Sequence[str]]
) -> PowerSearchRequestShape:
    """Decide the request STATE/SHAPE for one locale-prefixed Power Search
    request -- never touching the database and never running Search
    evaluation (SLICE-0096 independent review Finding A).

    *query_params* maps each raw query key to every raw value it carried
    (preserving duplicates) -- mirrors `hullq.application.search_read
    .decide_search_request_shape`'s identical contract.
    """
    if not isinstance(locale, str) or not locale:
        raise ValueError(f"locale must be a non-empty string; got {locale!r}")

    unknown_keys = set(query_params) - _ALLOWED_PARAM_KEYS
    if unknown_keys:
        return PowerSearchRequestShape(kind=PowerSearchOutcomeKind.INVALID)

    drive_raw_values = list(query_params.get(POWER_DRIVE_PARAM_KEY, ()))
    count_raw_values = list(query_params.get(POWER_ENGINE_COUNT_PARAM_KEY, ()))
    if not drive_raw_values and not count_raw_values:
        return PowerSearchRequestShape(kind=PowerSearchOutcomeKind.BASE)

    # Mirrors hullq.application.search_read's identical canonical-key-order
    # structural check: a semantically valid but non-canonically ordered
    # request (power_engine_count before power_drive) must 308-redirect,
    # never remain a second successful 200 identity.
    canonical_active_key_order = [
        key for key in CANONICAL_POWER_PARAM_KEY_ORDER if key in query_params
    ]
    actual_active_key_order = [key for key in query_params if key in _ALLOWED_PARAM_KEYS]
    order_is_canonical = actual_active_key_order == canonical_active_key_order

    drive_result = parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, drive_raw_values)
    if drive_result is None:
        return PowerSearchRequestShape(kind=PowerSearchOutcomeKind.INVALID)
    power_drive, drive_is_single_canonical = drive_result

    count_result = parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, count_raw_values)
    if count_result is None:
        return PowerSearchRequestShape(kind=PowerSearchOutcomeKind.INVALID)
    power_engine_count, count_is_single_canonical = count_result

    if not (drive_is_single_canonical and count_is_single_canonical and order_is_canonical):
        return PowerSearchRequestShape(
            kind=PowerSearchOutcomeKind.REDIRECT,
            canonical_path=build_canonical_power_search_path(
                locale, power_drive=power_drive, power_engine_count=power_engine_count
            ),
        )

    return PowerSearchRequestShape(
        kind=PowerSearchOutcomeKind.RESULT,
        power_drive=power_drive,
        power_engine_count=power_engine_count,
    )


def evaluate_power_search_request(
    conn: Any, *, locale: str, query_params: Mapping[str, Sequence[str]], as_of: datetime
) -> PowerSearchRequestOutcome:
    """Decide the request state for one locale-prefixed Power Search
    request AND, for a `RESULT`, run the complete unbounded
    `evaluate_power_requirement` evaluation -- externally unchanged behavior
    from before SLICE-0096, now composed from the pure
    `decide_power_search_request_shape` decision plus that evaluation. The
    public bounded-page Power route does NOT call this function (independent
    review Finding A) -- it calls `decide_power_search_request_shape`
    directly and then the SLICE-0096 bounded page evaluator instead.
    """
    shape = decide_power_search_request_shape(locale=locale, query_params=query_params)
    if shape.kind is not PowerSearchOutcomeKind.RESULT:
        return PowerSearchRequestOutcome(kind=shape.kind, canonical_path=shape.canonical_path)

    search_outcome = evaluate_power_requirement(
        conn,
        power_drive=shape.power_drive,
        power_engine_count=shape.power_engine_count,
        as_of=as_of,
    )
    return PowerSearchRequestOutcome(
        kind=PowerSearchOutcomeKind.RESULT,
        power_drive=shape.power_drive,
        power_engine_count=shape.power_engine_count,
        search_outcome=search_outcome,
    )
