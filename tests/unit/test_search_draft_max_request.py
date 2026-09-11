"""Unit tests for hullq.search.draft_max_request — SLICE-0051.

Covers the bounded `draft_max` lexical envelope (accepted spellings and every
explicitly excluded broader spelling), exact-Decimal parsing with no
binary-float intermediate, and canonical serialization for the accepted
examples plus round-trip idempotence.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.search.draft_max_request import (
    DraftMaxSyntaxError,
    canonical_draft_max_str,
    parse_draft_max_decimal,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.6", Decimal("1.6")),
        ("1.600", Decimal("1.600")),
        ("01.60", Decimal("01.60")),
        ("10.0", Decimal("10.0")),
        ("10.000", Decimal("10.000")),
        ("5", Decimal("5")),
        ("0.1", Decimal("0.1")),
    ],
)
def test_parse_draft_max_decimal_accepts_bounded_envelope(raw: str, expected: Decimal) -> None:
    value = parse_draft_max_decimal(raw)
    assert value == expected
    assert isinstance(value, Decimal)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " 1.6",
        "1.6 ",
        "+1.6",
        "-1.6",
        "1,6",
        "1e0",
        "1E0",
        "1.6e1",
        "1_000",
        "1,000.6",
        "1.",
        ".6",
        "0",
        "-0",
        "0.0",
        "abc",
        "1.6.1",
        "NaN",
        "Infinity",
        "1.6\n",
    ],
)
def test_parse_draft_max_decimal_rejects_broader_spellings(raw: str) -> None:
    with pytest.raises(DraftMaxSyntaxError):
        parse_draft_max_decimal(raw)


@pytest.mark.parametrize(
    ("raw", "expected_canonical"),
    [
        ("1.6", "1.6"),
        ("1.600", "1.6"),
        ("01.60", "1.6"),
        ("10.0", "10"),
        ("10.000", "10"),
        ("5", "5"),
        ("0.1", "0.1"),
        ("100", "100"),
        ("00100", "100"),
        ("0.100", "0.1"),
        # Amendment review Finding 1: significant leading fractional zeros
        # must survive canonicalization losslessly -- `Decimal.as_tuple()`
        # strips them from its own coefficient, so the serializer must
        # reintroduce them rather than silently changing the value's
        # magnitude (e.g. "0.01" must never canonicalize to "0.1").
        ("0.01", "0.01"),
        ("0.001", "0.001"),
        ("0.0100", "0.01"),
        ("0.0010", "0.001"),
        ("0.00010", "0.0001"),
        ("0.0001234", "0.0001234"),
        ("00.01", "0.01"),
    ],
)
def test_canonical_draft_max_str_matches_accepted_examples(
    raw: str, expected_canonical: str
) -> None:
    value = parse_draft_max_decimal(raw)
    assert canonical_draft_max_str(value) == expected_canonical


@pytest.mark.parametrize(
    "raw",
    [
        "0.01",
        "0.001",
        "0.0001",
        "0.00001234567890123456789",
        "0.0100",
        "0.0010000",
        "1.10000000000000000000001",
        "99999999999999999999999999999999.6",
        "0.0000000000000000000000000000001",
        "1",
        "0.5",
    ],
)
def test_canonicalization_preserves_exact_value_on_round_trip(raw: str) -> None:
    """Adversarial round trip: parse -> canonicalize -> parse must never
    change the represented numeric value, for values spanning many
    magnitudes of leading/trailing fractional zeros."""
    original = parse_draft_max_decimal(raw)
    canonical = canonical_draft_max_str(original)
    reparsed = parse_draft_max_decimal(canonical)
    assert reparsed == original, (
        f"canonicalizing {raw!r} -> {canonical!r} changed the represented value: "
        f"{original!r} != {reparsed!r}"
    )
    # Canonicalizing the canonical form again must be a no-op (idempotence).
    assert canonical_draft_max_str(reparsed) == canonical


def test_canonicalization_introduces_no_binary_float_conversion() -> None:
    # A value that is not exactly representable in binary floating point
    # must still canonicalize losslessly -- if this function ever routed
    # through `float`, this would silently drift.
    value = parse_draft_max_decimal("1.10000000000000000000001")
    assert canonical_draft_max_str(value) == "1.10000000000000000000001"


def test_canonical_form_is_idempotent() -> None:
    value = parse_draft_max_decimal("1.600")
    once = canonical_draft_max_str(value)
    twice = canonical_draft_max_str(parse_draft_max_decimal(once))
    assert once == twice == "1.6"


def test_canonical_draft_max_str_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        canonical_draft_max_str(Decimal("0"))
    with pytest.raises(ValueError):
        canonical_draft_max_str(Decimal("-1.6"))
