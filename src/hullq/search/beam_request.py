"""Exact-Decimal public `beam_min`/`beam_max` request lexical grammar — SLICE-0087.

Mirrors `hullq.search.loa_request` byte-for-byte in grammar and
canonicalization rule (slice normative beam semantics: "Adopt existing `loa`
strict lexical, precision, duplicate-key, bound and canonical-redirect
policy rather than invent a separate numeric grammar"). Kept as its own small
module rather than importing `hullq.search.loa_request` directly so that
`beam_min`/`beam_max`'s own canonical serialization and error type stay
independent of SLICE-0085's accepted, unmodified module -- a future change to
one dimension's grammar can never silently ripple into the other's.

This module is pure and persistence-neutral: it knows nothing about locales,
HTTP status codes or Search evaluation, exactly like `hullq.search.loa_request`.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Final

__all__ = ["BeamSyntaxError", "canonical_beam_str", "parse_beam_decimal"]

# Identical bounded envelope to hullq.search.loa_request's _LOA_PATTERN:
# digits and at most one ASCII '.' with at least one digit on each side when
# present. No sign, no comma, no exponent, no grouping separator, no
# leading/trailing whitespace, no terminal dot, never empty.
_BEAM_PATTERN: Final = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")

#: Identical resource-length-cap rationale to `hullq.search.loa_request.
#: _MAX_LOA_RAW_LENGTH` -- no real vessel's overall beam needs anywhere near
#: this many digits.
_MAX_BEAM_RAW_LENGTH: Final = 20


class BeamSyntaxError(ValueError):
    """Raised when a raw `beam_min`/`beam_max` value fails the bounded lexical envelope."""


def parse_beam_decimal(raw: str) -> Decimal:
    """Parse *raw* into an exact positive finite `Decimal`, or raise.

    Identical bounded envelope to `hullq.search.loa_request.parse_loa_decimal`
    -- see that function's docstring for the excluded spellings -- plus this
    module's own `_MAX_BEAM_RAW_LENGTH` resource-length cap, checked before
    the lexical-envelope regex and before any `Decimal` construction so an
    arbitrarily long raw string is rejected as cheaply as possible.
    """
    if not isinstance(raw, str) or len(raw) > _MAX_BEAM_RAW_LENGTH:
        raise BeamSyntaxError(
            f"beam value exceeds the accepted maximum length of {_MAX_BEAM_RAW_LENGTH} characters"
        )
    if not _BEAM_PATTERN.fullmatch(raw):
        raise BeamSyntaxError(
            f"beam value {raw!r} does not match the accepted bounded lexical envelope "
            f"{_BEAM_PATTERN.pattern!r}"
        )
    value = Decimal(raw)
    if not value.is_finite() or value <= 0:
        raise BeamSyntaxError(f"beam value {raw!r} must be a positive finite decimal")
    return value


def canonical_beam_str(value: Decimal) -> str:
    """Render *value* as the one canonical ASCII decimal form.

    Identical canonicalization rule to
    `hullq.search.loa_request.canonical_loa_str` -- see that function's
    docstring for the exact canonical examples; this is the "one shared exact
    Decimal formatter" the slice requires for the beam dimension's own
    min/max pair.
    """
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"canonical_beam_str requires a positive finite Decimal; got {value!r}")

    _sign, digits_tuple, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"canonical_beam_str requires a finite Decimal; got {value!r}")

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
