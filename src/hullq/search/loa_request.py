"""Exact-Decimal public `loa_min`/`loa_max` request lexical grammar — SLICE-0085.

Mirrors `hullq.search.draft_max_request` byte-for-byte in grammar and
canonicalization rule (slice §"LOA" normative semantics: "positive finite
plain-decimal metres, compatible with the accepted draft maximum lexical
grammar ... Canonicalize with one shared exact Decimal formatter; no
implicit epsilon or floating point tolerance"). Kept as its own small module
rather than importing `hullq.search.draft_max_request` directly so that
`loa_min`/`loa_max`'s own canonical serialization and error type stay
independent of SLICE-0051's accepted, unmodified module -- a future change to
one dimension's grammar can never silently ripple into the other's.

This module is pure and persistence-neutral: it knows nothing about locales,
HTTP status codes or Search evaluation, exactly like
`hullq.search.draft_max_request`.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Final

__all__ = ["LoaSyntaxError", "canonical_loa_str", "parse_loa_decimal"]

# Identical bounded envelope to hullq.search.draft_max_request's
# _DRAFT_MAX_PATTERN: digits and at most one ASCII '.' with at least one
# digit on each side when present. No sign, no comma, no exponent, no
# grouping separator, no leading/trailing whitespace, no terminal dot, never
# empty.
_LOA_PATTERN: Final = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")

#: Review amendment (Finding B): a justified, narrowly scoped resource-length
#: cap enforced BEFORE any `Decimal(raw)` construction -- the READY contract
#: explicitly requires rejecting "unreasonable resource-length input before
#: Decimal conversion". No real vessel's length overall needs anywhere near
#: this many digits: the largest vessels ever built are on the order of a
#: few hundred metres, so even a grossly generous integer part of up to
#: 999,999 m (6 digits) plus up to 6 fractional digits plus the decimal
#: point (13 characters) already covers every physically plausible LOA many
#: orders of magnitude over. 20 characters leaves a further safety margin
#: for that generous envelope while still bounding `Decimal` construction
#: and `canonical_loa_str`'s digit-list materialization against an
#: arbitrarily long digit string submitted as a query parameter. This is a
#: new, LOA-specific bound -- `hullq.search.draft_max_request`'s own
#: accepted grammar is deliberately left unchanged (a separate compatibility
#: decision would be required to retrofit a cap there).
_MAX_LOA_RAW_LENGTH: Final = 20


class LoaSyntaxError(ValueError):
    """Raised when a raw `loa_min`/`loa_max` value fails the bounded lexical envelope."""


def parse_loa_decimal(raw: str) -> Decimal:
    """Parse *raw* into an exact positive finite `Decimal`, or raise.

    Identical bounded envelope to
    `hullq.search.draft_max_request.parse_draft_max_decimal` -- see that
    function's docstring for the excluded spellings -- plus this module's
    own `_MAX_LOA_RAW_LENGTH` resource-length cap (Finding B), checked
    before the lexical-envelope regex and before any `Decimal` construction
    so an arbitrarily long raw string is rejected as cheaply as possible.
    """
    if not isinstance(raw, str) or len(raw) > _MAX_LOA_RAW_LENGTH:
        raise LoaSyntaxError(
            f"loa value exceeds the accepted maximum length of {_MAX_LOA_RAW_LENGTH} characters"
        )
    if not _LOA_PATTERN.fullmatch(raw):
        raise LoaSyntaxError(
            f"loa value {raw!r} does not match the accepted bounded lexical envelope "
            f"{_LOA_PATTERN.pattern!r}"
        )
    value = Decimal(raw)
    if not value.is_finite() or value <= 0:
        raise LoaSyntaxError(f"loa value {raw!r} must be a positive finite decimal")
    return value


def canonical_loa_str(value: Decimal) -> str:
    """Render *value* as the one canonical ASCII decimal form.

    Identical canonicalization rule to
    `hullq.search.draft_max_request.canonical_draft_max_str` -- see that
    function's docstring for the exact canonical examples; this is the "one
    shared exact Decimal formatter" the slice requires for the LOA
    dimension's own min/max pair.
    """
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"canonical_loa_str requires a positive finite Decimal; got {value!r}")

    _sign, digits_tuple, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"canonical_loa_str requires a finite Decimal; got {value!r}")

    digits = list(digits_tuple)
    if exponent >= 0:
        digits = digits + [0] * exponent
        exponent = 0

    frac_len = -exponent
    if frac_len > len(digits):
        int_digits: list[int] = [0]
        frac_digits = [0] * (frac_len - len(digits)) + digits
    else:
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
