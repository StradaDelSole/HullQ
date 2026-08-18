"""Tests for hullq.domain.measurements — SLICE-0004.

Covers all 15 required scenarios from docs/slices/SLICE-0004-measurement-normalization.md
plus Hypothesis property tests for conversion invariants.
"""

from __future__ import annotations

import decimal
import json
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hullq.domain.measurements import (
    AreaUnit,
    DisplacementBasis,
    LengthUnit,
    MassUnit,
    MeasurementObservation,
    NormalizedMeasurement,
    Quantity,
    SailAreaBasis,
    _exact_multiply,
    normalize_measurement,
)

_SPECS = Path(__file__).parent.parent.parent / "specs"
_BASIS_SCHEMA = _SPECS / "RATIO_INPUT_BASIS_SCHEMA.v0.1.json"

# ---------------------------------------------------------------------------
# Scenario 1: metre/centimetre/millimetre identity and conversion
# ---------------------------------------------------------------------------


def test_length_metre_identity() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("10"), unit=LengthUnit.METRE
    )
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("10")
    assert result.canonical_unit == "m"


def test_length_centimetre_to_metre() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("150"), unit=LengthUnit.CENTIMETRE
    )
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("1.50")
    assert result.canonical_unit == "m"


def test_length_millimetre_to_metre() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("2000"), unit=LengthUnit.MILLIMETRE
    )
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("2")
    assert result.canonical_unit == "m"


# ---------------------------------------------------------------------------
# Scenario 2: foot and inch to metre exactness
# ---------------------------------------------------------------------------


def test_length_foot_to_metre_exactness() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("12"), unit=LengthUnit.FOOT
    )
    result = normalize_measurement(obs)
    # 12 x 0.3048 = 3.6576 exactly
    assert result.canonical_value == Decimal("3.6576")
    assert result.canonical_unit == "m"


def test_length_inch_to_metre_exactness() -> None:
    obs = MeasurementObservation(quantity=Quantity.LENGTH, value=Decimal("1"), unit=LengthUnit.INCH)
    result = normalize_measurement(obs)
    # 1 x 0.0254 = 0.0254 exactly
    assert result.canonical_value == Decimal("0.0254")
    assert result.canonical_unit == "m"


# ---------------------------------------------------------------------------
# Scenario 3: kilogram/gram/metric-tonne conversion
# ---------------------------------------------------------------------------


def test_mass_kilogram_identity() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.MASS, value=Decimal("5000"), unit=MassUnit.KILOGRAM
    )
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("5000")
    assert result.canonical_unit == "kg"


def test_mass_gram_to_kilogram() -> None:
    obs = MeasurementObservation(quantity=Quantity.MASS, value=Decimal("1000"), unit=MassUnit.GRAM)
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("1")
    assert result.canonical_unit == "kg"


def test_mass_metric_tonne_to_kilogram() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.MASS, value=Decimal("5"), unit=MassUnit.METRIC_TONNE
    )
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("5000")
    assert result.canonical_unit == "kg"


# ---------------------------------------------------------------------------
# Scenario 4: pound to kilogram exactness
# ---------------------------------------------------------------------------


def test_mass_pound_to_kilogram_exactness() -> None:
    obs = MeasurementObservation(quantity=Quantity.MASS, value=Decimal("1"), unit=MassUnit.POUND)
    result = normalize_measurement(obs)
    # Exact international avoirdupois pound
    assert result.canonical_value == Decimal("0.45359237")
    assert result.canonical_unit == "kg"


# ---------------------------------------------------------------------------
# Scenario 5: long-ton to kilogram exactness
# ---------------------------------------------------------------------------


def test_mass_long_ton_to_kilogram_exactness() -> None:
    obs = MeasurementObservation(quantity=Quantity.MASS, value=Decimal("1"), unit=MassUnit.LONG_TON)
    result = normalize_measurement(obs)
    # 2240 x 0.45359237 = 1016.0469088 exactly
    assert result.canonical_value == Decimal("1016.0469088")
    assert result.canonical_unit == "kg"


def test_mass_long_ton_derivation_matches_2240_pounds() -> None:
    """1 long_ton == 2240 x 1 lb: constants must be consistent."""
    long_ton_kg = Decimal("2240") * Decimal("0.45359237")
    assert long_ton_kg == Decimal("1016.0469088")


# ---------------------------------------------------------------------------
# Scenario 6: square-foot to square-metre exactness
# ---------------------------------------------------------------------------


def test_area_square_metre_identity() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.AREA, value=Decimal("50"), unit=AreaUnit.SQUARE_METRE
    )
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("50")
    assert result.canonical_unit == "m2"


def test_area_square_foot_to_square_metre_exactness() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.AREA, value=Decimal("100"), unit=AreaUnit.SQUARE_FOOT
    )
    result = normalize_measurement(obs)
    # 100 x 0.09290304 = 9.290304 exactly
    assert result.canonical_value == Decimal("9.290304")
    assert result.canonical_unit == "m2"


# ---------------------------------------------------------------------------
# Scenario 7: raw text/source semantic label preserved unchanged
# ---------------------------------------------------------------------------


def test_raw_text_preserved_unchanged() -> None:
    raw = "LOA: 36' 4\""
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH,
        value=Decimal("11.07"),
        unit=LengthUnit.METRE,
        raw_text=raw,
        semantic_label="LOA",
    )
    result = normalize_measurement(obs)
    assert result.raw_text is raw  # exact identity
    assert result.semantic_label == "LOA"


def test_raw_text_none_when_not_supplied() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.MASS, value=Decimal("3000"), unit=MassUnit.KILOGRAM
    )
    result = normalize_measurement(obs)
    assert result.raw_text is None
    assert result.semantic_label is None


def test_source_value_and_unit_preserved() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("36.5"), unit=LengthUnit.FOOT
    )
    result = normalize_measurement(obs)
    assert result.source_value == Decimal("36.5")
    assert result.source_unit is LengthUnit.FOOT


# ---------------------------------------------------------------------------
# Scenario 8: quantity/unit mismatch rejected explicitly
# ---------------------------------------------------------------------------


def test_mismatch_length_quantity_with_mass_unit_raises() -> None:
    with pytest.raises(ValueError, match="LengthUnit"):
        MeasurementObservation(quantity=Quantity.LENGTH, value=Decimal("5"), unit=MassUnit.KILOGRAM)


def test_mismatch_mass_quantity_with_area_unit_raises() -> None:
    with pytest.raises(ValueError, match="MassUnit"):
        MeasurementObservation(
            quantity=Quantity.MASS, value=Decimal("5"), unit=AreaUnit.SQUARE_METRE
        )


def test_mismatch_area_quantity_with_length_unit_raises() -> None:
    with pytest.raises(ValueError, match="AreaUnit"):
        MeasurementObservation(quantity=Quantity.AREA, value=Decimal("5"), unit=LengthUnit.METRE)


# ---------------------------------------------------------------------------
# Scenario 9: unsupported unit rejected explicitly
# (Python enums make this impossible at the type level; API surface test)
# ---------------------------------------------------------------------------


def test_all_length_units_are_explicitly_enumerated() -> None:
    supported = {u.value for u in LengthUnit}
    assert supported == {"m", "cm", "mm", "ft", "in"}


def test_all_mass_units_are_explicitly_enumerated() -> None:
    supported = {u.value for u in MassUnit}
    assert supported == {"kg", "g", "t", "lb", "long_ton"}


def test_all_area_units_are_explicitly_enumerated() -> None:
    supported = {u.value for u in AreaUnit}
    assert supported == {"m2", "ft2"}


# ---------------------------------------------------------------------------
# Scenario 10: NaN/infinite/non-finite input rejected
# ---------------------------------------------------------------------------


def test_nan_decimal_rejected() -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        MeasurementObservation(
            quantity=Quantity.LENGTH, value=Decimal("NaN"), unit=LengthUnit.METRE
        )


def test_positive_infinity_decimal_rejected() -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        MeasurementObservation(
            quantity=Quantity.LENGTH, value=Decimal("Infinity"), unit=LengthUnit.METRE
        )


def test_negative_infinity_decimal_rejected() -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        MeasurementObservation(
            quantity=Quantity.LENGTH, value=Decimal("-Infinity"), unit=LengthUnit.METRE
        )


def test_snan_decimal_rejected() -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        MeasurementObservation(
            quantity=Quantity.LENGTH, value=Decimal("sNaN"), unit=LengthUnit.METRE
        )


# ---------------------------------------------------------------------------
# Scenario 11: explicit unknown and source_unspecified bases remain distinct
# ---------------------------------------------------------------------------


def test_displacement_basis_unknown_distinct_from_source_unspecified() -> None:
    assert DisplacementBasis.UNKNOWN != DisplacementBasis.SOURCE_UNSPECIFIED
    assert DisplacementBasis.UNKNOWN.value == "unknown"
    assert DisplacementBasis.SOURCE_UNSPECIFIED.value == "source_unspecified"


def test_sail_area_basis_unknown_distinct_from_source_unspecified() -> None:
    assert SailAreaBasis.UNKNOWN != SailAreaBasis.SOURCE_UNSPECIFIED
    assert SailAreaBasis.UNKNOWN.value == "unknown"
    assert SailAreaBasis.SOURCE_UNSPECIFIED.value == "source_unspecified"


# ---------------------------------------------------------------------------
# Scenario 12: Python DisplacementBasis exactly equals normative schema enum
# ---------------------------------------------------------------------------


def test_displacement_basis_values_match_normative_schema() -> None:
    schema = json.loads(_BASIS_SCHEMA.read_text(encoding="utf-8"))
    schema_values: list[str] = schema["properties"]["displacement_basis"]["enum"]
    python_values = {b.value for b in DisplacementBasis}
    assert python_values == set(schema_values), (
        f"DisplacementBasis drift: schema={schema_values}, python={sorted(python_values)}"
    )


def test_displacement_basis_cardinality_matches_schema() -> None:
    schema = json.loads(_BASIS_SCHEMA.read_text(encoding="utf-8"))
    schema_values: list[str] = schema["properties"]["displacement_basis"]["enum"]
    assert len(list(DisplacementBasis)) == len(schema_values)


# ---------------------------------------------------------------------------
# Scenario 13: Python SailAreaBasis exactly equals normative schema enum
# ---------------------------------------------------------------------------


def test_sail_area_basis_values_match_normative_schema() -> None:
    schema = json.loads(_BASIS_SCHEMA.read_text(encoding="utf-8"))
    schema_values: list[str] = schema["properties"]["sail_area_basis"]["enum"]
    python_values = {b.value for b in SailAreaBasis}
    assert python_values == set(schema_values), (
        f"SailAreaBasis drift: schema={schema_values}, python={sorted(python_values)}"
    )


def test_sail_area_basis_cardinality_matches_schema() -> None:
    schema = json.loads(_BASIS_SCHEMA.read_text(encoding="utf-8"))
    schema_values: list[str] = schema["properties"]["sail_area_basis"]["enum"]
    assert len(list(SailAreaBasis)) == len(schema_values)


# ---------------------------------------------------------------------------
# Scenario 14: no source-label text causes automatic basis inference
# ---------------------------------------------------------------------------


def test_normalized_measurement_carries_no_inferred_basis() -> None:
    """NormalizedMeasurement must never carry a basis field inferred from semantic_label.

    Basis values are accepted only when supplied explicitly by the caller.
    The normalization layer has no inference path from raw text or labels to basis values.
    """
    obs = MeasurementObservation(
        quantity=Quantity.MASS,
        value=Decimal("5000"),
        unit=MassUnit.KILOGRAM,
        semantic_label="lightship displacement",
    )
    result = normalize_measurement(obs)
    assert not hasattr(result, "displacement_basis")
    assert not hasattr(result, "sail_area_basis")
    assert not hasattr(result, "basis")


def test_raw_label_cannot_trigger_basis_side_effect() -> None:
    """Supplying a source label must not alter canonical_value or canonical_unit."""
    obs_with_label = MeasurementObservation(
        quantity=Quantity.MASS,
        value=Decimal("5000"),
        unit=MassUnit.KILOGRAM,
        raw_text="5000 kg (half-load)",
        semantic_label="half-load displacement",
    )
    obs_without_label = MeasurementObservation(
        quantity=Quantity.MASS,
        value=Decimal("5000"),
        unit=MassUnit.KILOGRAM,
    )
    r1 = normalize_measurement(obs_with_label)
    r2 = normalize_measurement(obs_without_label)
    assert r1.canonical_value == r2.canonical_value
    assert r1.canonical_unit == r2.canonical_unit


# ---------------------------------------------------------------------------
# Scenario 15: conversion does not apply derived-metric six-decimal rounding
# ---------------------------------------------------------------------------


def test_no_six_decimal_rounding_on_foot_to_metre() -> None:
    """normalize_measurement must not truncate to 6 decimals."""
    # 7 x 0.3048 = 2.1336 — this has 4 decimals, but the exact product
    # must survive without rounding to 6dp (i.e. we just verify precision is not lost).
    obs = MeasurementObservation(quantity=Quantity.LENGTH, value=Decimal("7"), unit=LengthUnit.FOOT)
    result = normalize_measurement(obs)
    assert result.canonical_value == Decimal("7") * Decimal("0.3048")


def test_no_six_decimal_rounding_on_pound_to_kg() -> None:
    """1 lb → 0.45359237 kg — not 0.453592 (six-decimal form)."""
    obs = MeasurementObservation(quantity=Quantity.MASS, value=Decimal("1"), unit=MassUnit.POUND)
    result = normalize_measurement(obs)
    # Must not be rounded to six places
    assert result.canonical_value != Decimal("0.453592")
    assert result.canonical_value == Decimal("0.45359237")


# ---------------------------------------------------------------------------
# Return type is a NormalizedMeasurement (structural check)
# ---------------------------------------------------------------------------


def test_normalize_returns_normalized_measurement_instance() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("5"), unit=LengthUnit.METRE
    )
    result = normalize_measurement(obs)
    assert isinstance(result, NormalizedMeasurement)


def test_normalized_measurement_is_immutable() -> None:
    obs = MeasurementObservation(
        quantity=Quantity.AREA, value=Decimal("20"), unit=AreaUnit.SQUARE_FOOT
    )
    result = normalize_measurement(obs)
    with pytest.raises((AttributeError, TypeError)):
        result.canonical_value = Decimal("999")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Context independence: ambient Decimal precision must not affect results
# ---------------------------------------------------------------------------


def test_conversion_independent_of_low_ambient_precision() -> None:
    """Same finite input must produce the same canonical value at any ambient Decimal precision."""
    obs = MeasurementObservation(
        quantity=Quantity.LENGTH, value=Decimal("36.5"), unit=LengthUnit.FOOT
    )
    with decimal.localcontext() as ctx:
        ctx.prec = 5  # far below default (28) — would corrupt unguarded multiplication
        result_low = normalize_measurement(obs)

    result_default = normalize_measurement(obs)
    assert result_low.canonical_value == result_default.canonical_value


def test_conversion_independent_of_high_ambient_precision() -> None:
    """Raising ambient precision beyond 50 must not change the canonical value."""
    obs = MeasurementObservation(quantity=Quantity.MASS, value=Decimal("1"), unit=MassUnit.POUND)
    with decimal.localcontext() as ctx:
        ctx.prec = 100
        result_high = normalize_measurement(obs)

    result_default = normalize_measurement(obs)
    assert result_high.canonical_value == result_default.canonical_value


def test_conversion_exact_for_value_exceeding_50_significant_digits() -> None:
    """A value with >50 significant digits must normalize without rounding.

    The previous Context(prec=50) implementation rounded inputs whose coefficient
    exceeded 50 digits. _exact_multiply derives precision from the actual operand
    digit counts, so no rounding can occur. The exact product is verified
    independently via fractions.Fraction (exact rational arithmetic).
    """
    from fractions import Fraction

    # 60 significant digits — exceeds the old fixed prec=50 ceiling
    value = Decimal("1" * 60)  # 111...1 (60 ones) as an integer Decimal
    obs = MeasurementObservation(quantity=Quantity.LENGTH, value=value, unit=LengthUnit.FOOT)
    result = normalize_measurement(obs)

    # Fraction arithmetic is exact; no precision limit applies
    exact = Fraction(value) * Fraction(Decimal("0.3048"))
    assert Fraction(result.canonical_value) == exact

    # Confirm the result was NOT silently rounded to <=50 significant digits
    assert len(result.canonical_value.as_tuple().digits) > 50


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@given(
    st.decimals(
        allow_nan=False, allow_infinity=False, min_value=Decimal("-1e15"), max_value=Decimal("1e15")
    )
)
@settings(max_examples=200)
def test_hypothesis_foot_metre_round_trip_proportional(value: Decimal) -> None:
    """Canonical value must be the exact product of value and the conversion factor."""
    obs = MeasurementObservation(quantity=Quantity.LENGTH, value=value, unit=LengthUnit.FOOT)
    result = normalize_measurement(obs)
    assert result.canonical_value == _exact_multiply(value, Decimal("0.3048"))


@given(
    st.decimals(
        allow_nan=False, allow_infinity=False, min_value=Decimal("-1e15"), max_value=Decimal("1e15")
    )
)
@settings(max_examples=200)
def test_hypothesis_pound_kg_proportional(value: Decimal) -> None:
    obs = MeasurementObservation(quantity=Quantity.MASS, value=value, unit=MassUnit.POUND)
    result = normalize_measurement(obs)
    assert result.canonical_value == _exact_multiply(value, Decimal("0.45359237"))


@given(
    st.one_of(
        st.just(Decimal("NaN")),
        st.just(Decimal("Infinity")),
        st.just(Decimal("-Infinity")),
        st.just(Decimal("sNaN")),
    )
)
def test_hypothesis_non_finite_always_rejected(value: Decimal) -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        MeasurementObservation(quantity=Quantity.LENGTH, value=value, unit=LengthUnit.METRE)


@given(
    st.decimals(
        allow_nan=False, allow_infinity=False, min_value=Decimal("-1e12"), max_value=Decimal("1e12")
    )
)
@settings(max_examples=100)
def test_hypothesis_metre_identity(value: Decimal) -> None:
    """Metre-to-metre conversion is the exact product of value and 1."""
    obs = MeasurementObservation(quantity=Quantity.LENGTH, value=value, unit=LengthUnit.METRE)
    result = normalize_measurement(obs)
    assert result.canonical_value == _exact_multiply(value, Decimal("1"))


@given(
    st.decimals(
        allow_nan=False, allow_infinity=False, min_value=Decimal("-1e12"), max_value=Decimal("1e12")
    ),
    st.integers(min_value=1, max_value=6),
)
@settings(max_examples=200)
def test_hypothesis_context_independence_foot(value: Decimal, prec: int) -> None:
    """normalize_measurement must give the same result regardless of ambient Decimal precision."""
    obs = MeasurementObservation(quantity=Quantity.LENGTH, value=value, unit=LengthUnit.FOOT)
    with decimal.localcontext() as ctx:
        ctx.prec = prec
        result_ambient = normalize_measurement(obs)
    result_default = normalize_measurement(obs)
    assert result_ambient.canonical_value == result_default.canonical_value
