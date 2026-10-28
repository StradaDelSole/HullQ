"""Public Power-only Search request-state boundary — SLICE-0093.

The Power-domain counterpart of `hullq.application.search_read`, bounded to
the one accepted public key `power_drive`
(`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`, "Request / query
contract"). Decides among the identical four accepted request states
(Required Behavior parity with the Sail boundary), independent of any HTTP
framework:

    zero active criteria   -> BASE      (200, no Search evaluation)
    one canonical power_drive -> RESULT (runs the bounded Power vertical)
    valid but non-canonical/duplicate value -> REDIRECT (308 to canonical URL)
    invalid/unknown params -> INVALID   (400, no Search evaluation)

This module never accepts a Sail key, and the existing `hullq.application
.search_read` module never accepts `power_drive` -- two entirely separate
parsers (contract §3: "Do not widen Sail parser to accept Power keys").
Locale support/routing stays `hullq.api.app`/the Astro route tree's job, not
decided here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.power_inventory_query import (
    PowerSearchOutcome,
    evaluate_power_drive_requirement,
)
from hullq.search.power_criteria_registry import (
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    POWER_DRIVE_PARAM_KEY,
    parse_categorical_param,
)

__all__ = [
    "PowerSearchOutcomeKind",
    "PowerSearchRequestOutcome",
    "build_canonical_power_search_path",
    "evaluate_power_search_request",
]

_ALLOWED_PARAM_KEYS = frozenset({POWER_DRIVE_PARAM_KEY})


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
    matches `kind`."""

    kind: PowerSearchOutcomeKind
    canonical_path: str | None = None
    power_drive: str | None = None
    search_outcome: PowerSearchOutcome | None = None

    def __post_init__(self) -> None:
        if self.kind is PowerSearchOutcomeKind.REDIRECT and self.canonical_path is None:
            raise ValueError("A REDIRECT outcome must carry canonical_path")
        if self.kind is not PowerSearchOutcomeKind.REDIRECT and self.canonical_path is not None:
            raise ValueError("Only a REDIRECT outcome may carry canonical_path")
        is_result = self.kind is PowerSearchOutcomeKind.RESULT
        if is_result:
            if self.power_drive is None:
                raise ValueError("A RESULT outcome must carry power_drive")
            if self.search_outcome is None:
                raise ValueError("A RESULT outcome must carry search_outcome")
        elif self.power_drive is not None or self.search_outcome is not None:
            raise ValueError("Only a RESULT outcome may carry power_drive/search_outcome")


def build_canonical_power_search_path(locale: str, *, power_drive: str | None) -> str:
    """Build the one canonical Power Search path for *locale* -- the sole
    accepted key means there is no multi-key ordering concern (unlike the
    Sail boundary's `CANONICAL_PARAM_KEY_ORDER`)."""
    if power_drive is None:
        return f"/{locale}/power/search"
    return f"/{locale}/power/search?{POWER_DRIVE_PARAM_KEY}={power_drive}"


def evaluate_power_search_request(
    conn: Any, *, locale: str, query_params: Mapping[str, Sequence[str]], as_of: datetime
) -> PowerSearchRequestOutcome:
    """Decide the request state for one locale-prefixed Power Search
    request.

    *query_params* maps each raw query key to every raw value it carried
    (preserving duplicates) -- mirrors `hullq.application.search_read
    .evaluate_search_request`'s identical contract.
    """
    if not isinstance(locale, str) or not locale:
        raise ValueError(f"locale must be a non-empty string; got {locale!r}")

    unknown_keys = set(query_params) - _ALLOWED_PARAM_KEYS
    if unknown_keys:
        return PowerSearchRequestOutcome(kind=PowerSearchOutcomeKind.INVALID)

    raw_values = list(query_params.get(POWER_DRIVE_PARAM_KEY, ()))
    if not raw_values:
        return PowerSearchRequestOutcome(kind=PowerSearchOutcomeKind.BASE)

    result = parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, raw_values)
    if result is None:
        return PowerSearchRequestOutcome(kind=PowerSearchOutcomeKind.INVALID)
    power_drive, is_single_canonical = result
    assert (
        power_drive is not None
    )  # raw_values is non-empty, so result cannot be the (None, True) shape

    if not is_single_canonical:
        return PowerSearchRequestOutcome(
            kind=PowerSearchOutcomeKind.REDIRECT,
            canonical_path=build_canonical_power_search_path(locale, power_drive=power_drive),
        )

    search_outcome = evaluate_power_drive_requirement(conn, power_drive=power_drive, as_of=as_of)
    return PowerSearchRequestOutcome(
        kind=PowerSearchOutcomeKind.RESULT,
        power_drive=power_drive,
        search_outcome=search_outcome,
    )
