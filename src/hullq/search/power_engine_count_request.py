"""Exact public `power_engine_count` request lexical grammar — SLICE-0094.

`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` ("One field, one
meaning"): the public Power-only hard-filter parameter `power_engine_count`
accepts exactly the canonical tokens `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8` --
one ASCII digit, no leading `0`/plus sign, whitespace, exponent, decimal
point, sign, JSON-encoded number, empty value, or `9`/higher. This is
deliberately a *narrower* public grammar than the 1-32 current-claim
storage/authoring envelope (`hullq.domain.physical_boat_claims
.PowerEngineCountClaim`) -- a truthful current claim of 9-32 is valid and
may support an evidenced non-match to a requested token, never an
affirmative match.

Mirrors `hullq.search.loa_request`/`hullq.search.draft_max_request` in
structure and in using `decimal.Decimal` as the one canonical in-process
representation (never a bare `int`), so this criterion's
`hullq.search.criteria_registry.CriterionDefinition.parse_value`/
`canonicalize_value` pair has the identical `Callable[[str], Decimal]`/
`Callable[[Decimal], str]` shape every other numeric criterion already uses
-- no second numeric-token representation.

This module is pure and persistence-neutral: it knows nothing about
locales, HTTP status codes, claim authoring or Search evaluation.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Final

__all__ = [
    "PowerEngineCountSyntaxError",
    "canonical_power_engine_count_str",
    "parse_power_engine_count_decimal",
]

#: Exactly one ASCII digit 1-8 -- no sign, no leading zero, no decimal point,
#: no exponent, no whitespace, never empty, never `0`/`9`/higher.
_POWER_ENGINE_COUNT_PATTERN: Final = re.compile(r"^[1-8]$")


class PowerEngineCountSyntaxError(ValueError):
    """Raised when a raw `power_engine_count` value fails the bounded
    lexical envelope."""


def parse_power_engine_count_decimal(raw: str) -> Decimal:
    """Parse *raw* into an exact `Decimal` in `{1, ..., 8}`, or raise.

    Rejects every spelling the contract explicitly excludes: `"01"`, `"+1"`,
    `"1.0"`, `"1e0"`, `" 1"`, `"1 "`, `""`, `"0"`, `"9"` and anything longer
    than one character.
    """
    if not isinstance(raw, str) or not _POWER_ENGINE_COUNT_PATTERN.fullmatch(raw):
        raise PowerEngineCountSyntaxError(
            f"power_engine_count value {raw!r} must be exactly one ASCII digit 1-8"
        )
    return Decimal(raw)


def canonical_power_engine_count_str(value: Decimal) -> str:
    """Render *value* as the one canonical ASCII decimal digit, or raise.

    Requires an exact integral `Decimal` in `{1, ..., 8}` -- the same bounded
    envelope `parse_power_engine_count_decimal` accepts, so this function is
    always the left inverse of that one.
    """
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(
            f"canonical_power_engine_count_str requires a finite Decimal; got {value!r}"
        )
    as_int = int(value)
    if Decimal(as_int) != value or not (1 <= as_int <= 8):
        raise ValueError(
            f"canonical_power_engine_count_str requires an exact integer 1-8; got {value!r}"
        )
    return str(as_int)
