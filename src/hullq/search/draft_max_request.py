"""Exact-Decimal public `draft_max` request lexical grammar — SLICE-0051.

Implements the slice's "Readiness-derived implementation rules" bounded
`draft_max` lexical envelope and its canonical numeric serialization
(`docs/SLICE_0051_DRAFT_MAX_VERTICAL_DECISION_2026-09-11.md`): the public URL
value is parsed directly into an exact `decimal.Decimal` without an
intermediate binary-float conversion, and re-serialized to one canonical
ASCII form with no grouping, no exponent notation, no unnecessary leading/
trailing zeros and no semantic rounding.

This module is pure and persistence-neutral: it knows nothing about locales,
HTTP status codes or Search evaluation. `hullq.application.search_read`
consumes it to decide between canonical-state evaluation, a `308` canonical
redirect and a `400` invalid-request response.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Final

__all__ = ["DraftMaxSyntaxError", "canonical_draft_max_str", "parse_draft_max_decimal"]

# Deliberately narrow (slice Readiness-derived rule): digits and at most one
# ASCII '.' with at least one digit on each side of it when present. No sign,
# no comma, no exponent, no grouping separator, no leading/trailing
# whitespace, no terminal dot, never empty.
_DRAFT_MAX_PATTERN: Final = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")


class DraftMaxSyntaxError(ValueError):
    """Raised when a raw `draft_max` value fails the bounded 0051 lexical envelope."""


def parse_draft_max_decimal(raw: str) -> Decimal:
    """Parse *raw* into an exact positive finite `Decimal`, or raise.

    Rejects (rather than guesses) every broader spelling excluded by the
    slice's bounded lexical envelope: signs, comma decimals, exponents,
    grouping separators, whitespace, a terminal decimal dot and empty
    values. `Decimal(raw)` is called only after the regex already
    guarantees a plain fixed-point digit string, so no scientific-notation
    or locale-dependent string ever reaches the `Decimal` constructor.
    """
    if not isinstance(raw, str) or not _DRAFT_MAX_PATTERN.fullmatch(raw):
        raise DraftMaxSyntaxError(
            f"draft_max {raw!r} does not match the accepted bounded lexical envelope "
            f"{_DRAFT_MAX_PATTERN.pattern!r}"
        )
    value = Decimal(raw)
    if not value.is_finite() or value <= 0:
        raise DraftMaxSyntaxError(f"draft_max {raw!r} must be a positive finite decimal")
    return value


def canonical_draft_max_str(value: Decimal) -> str:
    """Render *value* as the one canonical ASCII decimal form.

    `value` must already be a positive finite `Decimal` (as returned by
    `parse_draft_max_decimal`). Strips unnecessary leading zeros in the
    integer part and trailing zeros in the fractional part, drops a now-empty
    fractional part entirely, and never introduces exponent notation or
    grouping — matching the accepted canonical examples exactly:
    ``1.600 -> 1.6``, ``01.60 -> 1.6``, ``10.0 -> 10``, ``10.000 -> 10``.
    """
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"canonical_draft_max_str requires a positive finite Decimal; got {value!r}")

    _sign, digits_tuple, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"canonical_draft_max_str requires a finite Decimal; got {value!r}")

    digits = list(digits_tuple)
    if exponent >= 0:
        # Never produced by parse_draft_max_decimal's plain fixed-point input,
        # but handled losslessly for any other well-formed positive Decimal.
        digits = digits + [0] * exponent
        exponent = 0

    frac_len = -exponent
    split_at = len(digits) - frac_len
    int_digits = digits[:split_at]
    frac_digits = digits[split_at:]

    while frac_digits and frac_digits[-1] == 0:
        frac_digits.pop()
    while len(int_digits) > 1 and int_digits[0] == 0:
        int_digits.pop(0)
    if not int_digits:
        int_digits = [0]

    int_str = "".join(str(d) for d in int_digits)
    if not frac_digits:
        return int_str
    frac_str = "".join(str(d) for d in frac_digits)
    return f"{int_str}.{frac_str}"
