"""Unit tests for hullq.search.loa_request — SLICE-0085.

Mirrors `tests/unit/test_search_draft_max_request.py`'s coverage exactly
(identical bounded lexical envelope and canonicalization rule), applied to
the `loa_min`/`loa_max` public parameters instead.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.search.loa_request import LoaSyntaxError, canonical_loa_str, parse_loa_decimal


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
def test_parse_loa_decimal_accepts_bounded_envelope(raw: str, expected: Decimal) -> None:
    value = parse_loa_decimal(raw)
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
def test_parse_loa_decimal_rejects_broader_spellings(raw: str) -> None:
    with pytest.raises(LoaSyntaxError):
        parse_loa_decimal(raw)


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
        ("0.01", "0.01"),
        ("0.001", "0.001"),
        ("0.0100", "0.01"),
        ("0.0010", "0.001"),
        ("0.00010", "0.0001"),
        ("0.0001234", "0.0001234"),
        ("00.01", "0.01"),
    ],
)
def test_canonical_loa_str_matches_accepted_examples(raw: str, expected_canonical: str) -> None:
    value = parse_loa_decimal(raw)
    assert canonical_loa_str(value) == expected_canonical


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
    original = parse_loa_decimal(raw)
    canonical = canonical_loa_str(original)
    reparsed = parse_loa_decimal(canonical)
    assert reparsed == original, (
        f"canonicalizing {raw!r} -> {canonical!r} changed the represented value: "
        f"{original!r} != {reparsed!r}"
    )
    assert canonical_loa_str(reparsed) == canonical


def test_canonical_loa_str_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        canonical_loa_str(Decimal("0"))
    with pytest.raises(ValueError):
        canonical_loa_str(Decimal("-1.6"))
