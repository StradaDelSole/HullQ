"""Deterministic unit/basis normalization for explicit measurement observations.

Converts explicit numeric values in explicit units to canonical SI values while
preserving the source representation and semantic label. Does not parse arbitrary
strings, infer basis from free-text labels, or apply derived-metric rounding.
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, StrEnum
from typing import assert_never

__all__ = [
    "AreaUnit",
    "DisplacementBasis",
    "LengthUnit",
    "MassUnit",
    "MeasurementObservation",
    "NormalizedMeasurement",
    "Quantity",
    "SailAreaBasis",
    "Unit",
    "normalize_measurement",
]


# ---------------------------------------------------------------------------
# Quantity kinds
# ---------------------------------------------------------------------------


class Quantity(Enum):
    LENGTH = "length"
    MASS = "mass"
    AREA = "area"


# ---------------------------------------------------------------------------
# Explicit unit tokens
# ---------------------------------------------------------------------------


class LengthUnit(Enum):
    METRE = "m"
    CENTIMETRE = "cm"
    MILLIMETRE = "mm"
    FOOT = "ft"
    INCH = "in"


class MassUnit(Enum):
    KILOGRAM = "kg"
    GRAM = "g"
    METRIC_TONNE = "t"
    POUND = "lb"
    LONG_TON = "long_ton"


class AreaUnit(Enum):
    SQUARE_METRE = "m2"
    SQUARE_FOOT = "ft2"


type Unit = LengthUnit | MassUnit | AreaUnit


# ---------------------------------------------------------------------------
# Exact SI conversion factors (source_value x factor = SI value)
# Constants are defined per accepted HullQ methodology.
# ---------------------------------------------------------------------------

_LENGTH_TO_M: dict[LengthUnit, Decimal] = {
    LengthUnit.METRE: Decimal("1"),
    LengthUnit.CENTIMETRE: Decimal("0.01"),
    LengthUnit.MILLIMETRE: Decimal("0.001"),
    LengthUnit.FOOT: Decimal("0.3048"),  # exact international foot
    LengthUnit.INCH: Decimal("0.0254"),  # exact: 1 ft / 12 * 0.3048
}

_MASS_TO_KG: dict[MassUnit, Decimal] = {
    MassUnit.KILOGRAM: Decimal("1"),
    MassUnit.GRAM: Decimal("0.001"),
    MassUnit.METRIC_TONNE: Decimal("1000"),
    MassUnit.POUND: Decimal("0.45359237"),  # exact international avoirdupois pound
    MassUnit.LONG_TON: Decimal("1016.0469088"),  # 2240 x 0.45359237 exactly
}

_AREA_TO_M2: dict[AreaUnit, Decimal] = {
    AreaUnit.SQUARE_METRE: Decimal("1"),
    AreaUnit.SQUARE_FOOT: Decimal("0.09290304"),  # 0.3048² exactly
}

_CANONICAL_UNIT: dict[Quantity, str] = {
    Quantity.LENGTH: "m",
    Quantity.MASS: "kg",
    Quantity.AREA: "m2",
}

# Fixed-precision context used for all unit multiplication so that results are
# independent of whatever ambient/global Decimal context the caller has set.
# 50 significant digits is sufficient for any realistic measurement value paired
# with our conversion constants (max 10 significant digits).
_CONVERSION_CTX = decimal.Context(prec=50, rounding=decimal.ROUND_HALF_EVEN)


# ---------------------------------------------------------------------------
# Accepted basis vocabularies (mirrors RATIO_INPUT_BASIS_SCHEMA.v0.1.json)
# ---------------------------------------------------------------------------


class DisplacementBasis(StrEnum):
    """Normative displacement basis vocabulary.

    Values must exactly match the ``displacement_basis`` enum in
    ``RATIO_INPUT_BASIS_SCHEMA.v0.1.json``. Tests enforce this invariant.
    """

    DESIGN = "design"
    LIGHTSHIP = "lightship"
    NORMAL_SAILING = "normal_sailing"
    FULL_LOAD = "full_load"
    SOURCE_UNSPECIFIED = "source_unspecified"
    UNKNOWN = "unknown"


class SailAreaBasis(StrEnum):
    """Normative sail-area basis vocabulary.

    Values must exactly match the ``sail_area_basis`` enum in
    ``RATIO_INPUT_BASIS_SCHEMA.v0.1.json``. Tests enforce this invariant.
    """

    NOMINAL_MAIN_PLUS_FORETRIANGLE = "nominal_main_plus_foretriangle"
    UPWIND_100PCT = "upwind_100pct"
    WORKING_SAILS_ACTUAL = "working_sails_actual"
    DOWNWIND = "downwind"
    SOURCE_UNSPECIFIED = "source_unspecified"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeasurementObservation:
    """An explicit measurement as observed in a source.

    Not a provenance record — holds no FieldEvidence IDs or resolution state.
    ``raw_text`` and ``semantic_label`` are preserved byte-for-byte; the
    normalization layer never rewrites them.
    """

    quantity: Quantity
    value: Decimal
    unit: Unit
    raw_text: str | None = None
    semantic_label: str | None = None

    def __post_init__(self) -> None:
        if not self.value.is_finite():
            raise ValueError(f"Non-finite measurement value: {self.value!r}")
        _check_unit_for_quantity(self.quantity, self.unit)


@dataclass(frozen=True)
class NormalizedMeasurement:
    """SI-normalized form of a ``MeasurementObservation``.

    No rounding is applied. ``raw_text`` and ``semantic_label`` are forwarded
    unchanged from the source observation.
    """

    quantity: Quantity
    canonical_value: Decimal
    canonical_unit: str
    source_value: Decimal
    source_unit: Unit
    raw_text: str | None
    semantic_label: str | None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_unit_for_quantity(quantity: Quantity, unit: Unit) -> None:
    """Raise ``ValueError`` if *unit* does not match *quantity*."""
    if quantity is Quantity.LENGTH:
        if not isinstance(unit, LengthUnit):
            raise ValueError(
                f"Length quantity requires a LengthUnit, got {type(unit).__name__}: {unit!r}"
            )
    elif quantity is Quantity.MASS:
        if not isinstance(unit, MassUnit):
            raise ValueError(
                f"Mass quantity requires a MassUnit, got {type(unit).__name__}: {unit!r}"
            )
    elif quantity is Quantity.AREA:
        if not isinstance(unit, AreaUnit):
            raise ValueError(
                f"Area quantity requires an AreaUnit, got {type(unit).__name__}: {unit!r}"
            )
    else:  # pragma: no cover
        assert_never(quantity)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_measurement(observation: MeasurementObservation) -> NormalizedMeasurement:
    """Convert *observation* to its canonical SI value.

    Multiplication is performed inside a fixed-precision Decimal context
    (``_CONVERSION_CTX``, prec=50) so results are independent of any ambient
    context the caller has set. No rounding is applied; the caller is responsible
    for projection-level rounding (e.g. the six-decimal policy in
    ``hullq-derived-1.0.0``).
    """
    unit = observation.unit
    value = observation.value

    with decimal.localcontext(_CONVERSION_CTX):
        if isinstance(unit, LengthUnit):
            canonical_value = value * _LENGTH_TO_M[unit]
        elif isinstance(unit, MassUnit):
            canonical_value = value * _MASS_TO_KG[unit]
        elif isinstance(unit, AreaUnit):
            canonical_value = value * _AREA_TO_M2[unit]
        else:  # pragma: no cover
            assert_never(unit)

    return NormalizedMeasurement(
        quantity=observation.quantity,
        canonical_value=canonical_value,
        canonical_unit=_CANONICAL_UNIT[observation.quantity],
        source_value=value,
        source_unit=unit,
        raw_text=observation.raw_text,
        semantic_label=observation.semantic_label,
    )
