"""Deterministic derived yacht metrics engine — SLICE-0010 / hullq-derived-1.0.0.

Implements the six accepted derived metrics under methodology hullq-derived-1.0.0
(OQ-001 / ADR-0008 / DERIVED_METRICS_SPEC.v1.0.md):

  sa_displ                  HQR-SAD-1.0.0
  ballast_displ_pct         HQR-BD-1.0.0
  displ_length              HQR-DL-1.0.0
  comfort_ratio             HQR-CR-1.0.0
  capsize_screening_formula HQR-CSF-1.0.0
  hull_speed_kn             HQM-HS-1.0.0

Inputs are supplied as an explicit immutable EffectiveInputSnapshot; the engine
never chooses between conflicting source observations.  Derivation IDs and
timestamps are supplied by the caller so the formula core is deterministic.

Does not implement: full ResolvedConfiguration resolution, source-conflict
resolution, authority ranking, persistence, API, search semantics, safety
scoring, or any formula not in the accepted methodology.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum
from typing import Any, Final

__all__ = [
    "FORMULA_BALLAST_DISPL_PCT",
    "FORMULA_CAPSIZE_SCREENING",
    "FORMULA_COMFORT_RATIO",
    "FORMULA_DISPL_LENGTH",
    "FORMULA_HULL_SPEED",
    "FORMULA_SA_DISPL",
    "KG_PER_POUND",
    "LEGACY_SEAWATER_LB_PER_FT3",
    "METHODOLOGY_VERSION",
    "METRES_PER_FOOT",
    "POUNDS_PER_LONG_TON",
    "DerivationInput",
    "DerivationRecord",
    "DerivedMetrics",
    "EffectiveInputSnapshot",
    "MetricResult",
    "MetricStatus",
    "compute_derived_metrics",
]

# ---------------------------------------------------------------------------
# Methodology and formula identifiers
# ---------------------------------------------------------------------------

METHODOLOGY_VERSION: Final[str] = "hullq-derived-1.0.0"

FORMULA_SA_DISPL: Final[str] = "HQR-SAD-1.0.0"
FORMULA_BALLAST_DISPL_PCT: Final[str] = "HQR-BD-1.0.0"
FORMULA_DISPL_LENGTH: Final[str] = "HQR-DL-1.0.0"
FORMULA_COMFORT_RATIO: Final[str] = "HQR-CR-1.0.0"
FORMULA_CAPSIZE_SCREENING: Final[str] = "HQR-CSF-1.0.0"
FORMULA_HULL_SPEED: Final[str] = "HQM-HS-1.0.0"

# ---------------------------------------------------------------------------
# Accepted unit conversion constants (DERIVED_METRICS_SPEC.v1.0.md §4)
# ---------------------------------------------------------------------------

METRES_PER_FOOT: Final[float] = 0.3048
KG_PER_POUND: Final[float] = 0.45359237
POUNDS_PER_LONG_TON: Final[int] = 2240
LEGACY_SEAWATER_LB_PER_FT3: Final[int] = 64

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_SIX_DP: Final[Decimal] = Decimal("0.000001")

# Canonical metric keys — match DERIVED_METRICS_SCHEMA.v1.0.json
_K_SA: Final[str] = "sa_displ"
_K_BD: Final[str] = "ballast_displ_pct"
_K_DL: Final[str] = "displ_length"
_K_CR: Final[str] = "comfort_ratio"
_K_CSF: Final[str] = "capsize_screening_formula"
_K_HS: Final[str] = "hull_speed_kn"

# Canonical field pointers (RESOLVED_CONFIGURATION_SCHEMA.v0.2)
_FP_LOA: Final[str] = "/effective/dimensions/loa_m"
_FP_LWL: Final[str] = "/effective/dimensions/lwl_m"
_FP_BEAM: Final[str] = "/effective/dimensions/beam_m"
_FP_DISPL: Final[str] = "/effective/dimensions/displacement_kg"
_FP_BALLAST: Final[str] = "/effective/dimensions/ballast_kg"
_FP_SAIL: Final[str] = "/effective/dimensions/sail_area_m2"
_FP_HULL: Final[str] = "/effective/configuration/hull_configuration"
_FP_DISPL_BASIS: Final[str] = "/effective/ratio_input_basis/displacement_basis"
_FP_SAIL_BASIS: Final[str] = "/effective/ratio_input_basis/sail_area_basis"

# Displacement basis sets
_DISPL_STANDARD: Final[frozenset[str]] = frozenset({"design", "lightship"})
_DISPL_PROVISIONAL: Final[frozenset[str]] = frozenset({"source_unspecified", "unknown"})
_DISPL_NONSTANDARD: Final[frozenset[str]] = frozenset({"normal_sailing", "full_load"})

# Sail-area basis sets
_SAIL_STANDARD: Final[frozenset[str]] = frozenset(
    {"nominal_main_plus_foretriangle", "upwind_100pct"}
)
_SAIL_PROVISIONAL: Final[frozenset[str]] = frozenset({"source_unspecified", "unknown"})
_SAIL_NONSTANDARD: Final[frozenset[str]] = frozenset({"working_sails_actual", "downwind"})

# Hull configuration sets
_MONO_CAT_TRI: Final[frozenset[str]] = frozenset({"monohull", "catamaran", "trimaran"})
_MONO_ONLY: Final[frozenset[str]] = frozenset({"monohull"})
_AMBIGUOUS_HULL: Final[frozenset[str]] = frozenset({"other", "unknown"})


# ---------------------------------------------------------------------------
# MetricStatus vocabulary
# ---------------------------------------------------------------------------


class MetricStatus(StrEnum):
    """Result status vocabulary matching DERIVED_METRICS_SCHEMA.v1.0.json exactly."""

    COMPUTED = "computed"
    COMPUTED_PROVISIONAL = "computed_provisional"
    MISSING_INPUT = "missing_input"
    UNRESOLVED_INPUT = "unresolved_input"
    INVALID_INPUT = "invalid_input"
    NOT_APPLICABLE = "not_applicable"
    APPLICABILITY_UNKNOWN = "applicability_unknown"
    NONSTANDARD_INPUT = "nonstandard_input"


# Status precedence — lower index wins (DERIVED_METRICS_SPEC.v1.0.md §6.1)
_PRECEDENCE: Final[tuple[MetricStatus, ...]] = (
    MetricStatus.INVALID_INPUT,  # 0 — highest priority
    MetricStatus.UNRESOLVED_INPUT,  # 1
    MetricStatus.NOT_APPLICABLE,  # 2
    MetricStatus.APPLICABILITY_UNKNOWN,  # 3
    MetricStatus.MISSING_INPUT,  # 4
    MetricStatus.NONSTANDARD_INPUT,  # 5
    MetricStatus.COMPUTED_PROVISIONAL,  # 6
    MetricStatus.COMPUTED,  # 7 — lowest priority
)

_PRIORITY: Final[dict[MetricStatus, int]] = {s: i for i, s in enumerate(_PRECEDENCE)}


def _merge(*statuses: MetricStatus) -> MetricStatus:
    """Return the highest-priority (lowest index) status from the given statuses."""
    return min(statuses, key=lambda s: _PRIORITY[s])


# ---------------------------------------------------------------------------
# EffectiveInputSnapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectiveInputSnapshot:
    """Immutable snapshot of effective configuration inputs for metric computation.

    Snapshot-safe: ``resolution_ids`` is deep-copied on construction so that
    later mutation of a caller-owned dict cannot alter an already-created
    snapshot.  ``unresolved_fields`` is a ``frozenset`` and is therefore
    intrinsically immutable.

    Use :meth:`create` to convert from ordinary mutable collections.
    """

    resolved_configuration_id: str
    hull_configuration: str
    loa_m: float | None
    lwl_m: float | None
    beam_m: float | None
    displacement_kg: float | None
    ballast_kg: float | None
    sail_area_m2: float | None
    displacement_basis: str
    sail_area_basis: str
    # RFC 6901 pointer strings for fields whose values are marked unresolved
    unresolved_fields: frozenset[str]
    # optional FieldResolution IDs keyed by effective-field pointer
    resolution_ids: dict[str, str]

    def __post_init__(self) -> None:
        if not self.resolved_configuration_id:
            raise ValueError("resolved_configuration_id must be non-empty")
        object.__setattr__(self, "resolution_ids", copy.deepcopy(self.resolution_ids))

    @classmethod
    def create(
        cls,
        *,
        resolved_configuration_id: str,
        hull_configuration: str,
        loa_m: float | None = None,
        lwl_m: float | None = None,
        beam_m: float | None = None,
        displacement_kg: float | None = None,
        ballast_kg: float | None = None,
        sail_area_m2: float | None = None,
        displacement_basis: str,
        sail_area_basis: str,
        unresolved_fields: frozenset[str] | set[str] | list[str] | None = None,
        resolution_ids: dict[str, str] | None = None,
    ) -> EffectiveInputSnapshot:
        """Construct from arbitrary collection types; converts to immutable forms."""
        return cls(
            resolved_configuration_id=resolved_configuration_id,
            hull_configuration=hull_configuration,
            loa_m=loa_m,
            lwl_m=lwl_m,
            beam_m=beam_m,
            displacement_kg=displacement_kg,
            ballast_kg=ballast_kg,
            sail_area_m2=sail_area_m2,
            displacement_basis=displacement_basis,
            sail_area_basis=sail_area_basis,
            unresolved_fields=frozenset(unresolved_fields or ()),
            resolution_ids=dict(resolution_ids or {}),
        )


# ---------------------------------------------------------------------------
# MetricResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricResult:
    """Per-metric computation result including diagnostic context.

    ``problems`` retains all independently detectable input problems
    (not just the highest-priority one) for audit / test use.
    Only ``value`` and ``status`` are canonical outputs.
    """

    metric_key: str
    formula_id: str
    value: float | None
    status: MetricStatus
    problems: tuple[str, ...]


# ---------------------------------------------------------------------------
# DerivedMetrics canonical projection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DerivedMetrics:
    """Canonical projection matching DERIVED_METRICS_SCHEMA.v1.0.json."""

    methodology_version: str
    sa_displ: float | None
    ballast_displ_pct: float | None
    displ_length: float | None
    comfort_ratio: float | None
    capsize_screening_formula: float | None
    hull_speed_kn: float | None
    status: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict matching DERIVED_METRICS_SCHEMA.v1.0.json."""
        return {
            "methodology_version": self.methodology_version,
            "sa_displ": self.sa_displ,
            "ballast_displ_pct": self.ballast_displ_pct,
            "displ_length": self.displ_length,
            "comfort_ratio": self.comfort_ratio,
            "capsize_screening_formula": self.capsize_screening_formula,
            "hull_speed_kn": self.hull_speed_kn,
            "status": dict(self.status),
        }


# ---------------------------------------------------------------------------
# DerivationRecord lineage
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DerivationInput:
    """One input entry in a DerivationRecord, matching DERIVATION_RECORD_SCHEMA.v0.1."""

    subject_kind: str
    subject_id: str
    field_pointer: str
    field_resolution_id: str | None
    value_snapshot: object

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": {"kind": self.subject_kind, "id": self.subject_id},
            "field_pointer": self.field_pointer,
            "field_resolution_id": self.field_resolution_id,
            "value_snapshot": self.value_snapshot,
        }


@dataclass(frozen=True)
class DerivationRecord:
    """Lineage record for one derived metric, matching DERIVATION_RECORD_SCHEMA.v0.1.

    Timestamps and IDs are supplied by the caller so the engine remains
    deterministic and testable without hidden clock / UUID calls.
    """

    schema_version: str
    derivation_id: str
    target_kind: str
    target_id: str
    target_field_pointer: str
    method_id: str
    method_version: str
    inputs: tuple[DerivationInput, ...]
    output_value_snapshot: object
    producer_kind: str
    producer_identifier: str
    producer_version: str | None
    generated_at: str
    notes: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "derivation_id": self.derivation_id,
            "target": {
                "kind": self.target_kind,
                "id": self.target_id,
                "field_pointer": self.target_field_pointer,
            },
            "method": {
                "id": self.method_id,
                "version": self.method_version,
            },
            "inputs": [inp.as_dict() for inp in self.inputs],
            "output_value_snapshot": self.output_value_snapshot,
            "producer": {
                "kind": self.producer_kind,
                "identifier": self.producer_identifier,
                "version": self.producer_version,
            },
            "generated_at": self.generated_at,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _quantize(value: float) -> float:
    """Quantize a float to 6 decimal places using decimal round-half-even."""
    d = Decimal(repr(value))
    return float(d.quantize(_SIX_DP, rounding=ROUND_HALF_EVEN))


def _is_valid_positive(v: object) -> bool:
    """True iff v is a finite, non-bool real number strictly greater than zero."""
    return (
        not isinstance(v, bool)
        and isinstance(v, (int, float))
        and math.isfinite(float(v))
        and float(v) > 0.0
    )


def _is_valid_nonneg(v: object) -> bool:
    """True iff v is a finite, non-bool real number >= 0."""
    return (
        not isinstance(v, bool)
        and isinstance(v, (int, float))
        and math.isfinite(float(v))
        and float(v) >= 0.0
    )


def _field_problems(
    pointer: str,
    value: object,
    unresolved: frozenset[str],
    *,
    require_positive: bool = False,
    require_nonneg: bool = False,
) -> list[MetricStatus]:
    """Collect all independently detectable problems for one field value."""
    problems: list[MetricStatus] = []

    if pointer in unresolved:
        problems.append(MetricStatus.UNRESOLVED_INPUT)

    if isinstance(value, bool):
        problems.append(MetricStatus.INVALID_INPUT)
    elif value is None:
        problems.append(MetricStatus.MISSING_INPUT)
    elif (
        not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or (require_positive and float(value) <= 0.0)
        or (require_nonneg and float(value) < 0.0)
    ):
        problems.append(MetricStatus.INVALID_INPUT)

    return problems


def _hull_problem(hull: str, applicable: frozenset[str]) -> MetricStatus | None:
    """Return a hull-applicability problem status, or None if applicable."""
    if hull in applicable:
        return None
    if hull in _AMBIGUOUS_HULL:
        return MetricStatus.APPLICABILITY_UNKNOWN
    return MetricStatus.NOT_APPLICABLE


def _displ_basis_flag(basis: str) -> tuple[bool, bool]:
    """Return (is_nonstandard, is_provisional) for a displacement basis value."""
    if basis in _DISPL_NONSTANDARD:
        return True, False
    if basis in _DISPL_PROVISIONAL:
        return False, True
    return False, False  # standard


def _sail_basis_flag(basis: str) -> tuple[bool, bool]:
    """Return (is_nonstandard, is_provisional) for a sail-area basis value."""
    if basis in _SAIL_NONSTANDARD:
        return True, False
    if basis in _SAIL_PROVISIONAL:
        return False, True
    return False, False  # standard


def _make_result(
    metric_key: str,
    formula_id: str,
    problems: list[MetricStatus],
    provisional: bool,
    computed_value: float | None,
) -> MetricResult:
    """Produce a MetricResult from the collected problem set and computed value."""
    if problems:
        status = _merge(*problems)
        return MetricResult(
            metric_key=metric_key,
            formula_id=formula_id,
            value=None,
            status=status,
            problems=tuple(str(p) for p in problems),
        )
    status = MetricStatus.COMPUTED_PROVISIONAL if provisional else MetricStatus.COMPUTED
    return MetricResult(
        metric_key=metric_key,
        formula_id=formula_id,
        value=computed_value,
        status=status,
        problems=(),
    )


# ---------------------------------------------------------------------------
# Per-metric evaluators
# ---------------------------------------------------------------------------


def _eval_sa_displ(snap: EffectiveInputSnapshot) -> MetricResult:
    """HQR-SAD-1.0.0 — Sail Area / Displacement."""
    problems: list[MetricStatus] = []
    provisional = False

    hull_p = _hull_problem(snap.hull_configuration, _MONO_CAT_TRI)
    if hull_p is not None:
        problems.append(hull_p)

    problems.extend(
        _field_problems(_FP_SAIL, snap.sail_area_m2, snap.unresolved_fields, require_positive=True)
    )
    problems.extend(
        _field_problems(
            _FP_DISPL, snap.displacement_kg, snap.unresolved_fields, require_positive=True
        )
    )

    displ_ns, displ_prov = _displ_basis_flag(snap.displacement_basis)
    sail_ns, sail_prov = _sail_basis_flag(snap.sail_area_basis)
    if displ_ns:
        problems.append(MetricStatus.NONSTANDARD_INPUT)
    if sail_ns:
        problems.append(MetricStatus.NONSTANDARD_INPUT)
    if displ_prov or sail_prov:
        provisional = True

    if problems:
        return _make_result(_K_SA, FORMULA_SA_DISPL, problems, False, None)

    sail_ft2 = float(snap.sail_area_m2) / (METRES_PER_FOOT**2)  # type: ignore[arg-type]
    displ_lb = float(snap.displacement_kg) / KG_PER_POUND  # type: ignore[arg-type]
    value = _quantize(sail_ft2 / ((displ_lb / LEGACY_SEAWATER_LB_PER_FT3) ** (2.0 / 3.0)))
    return _make_result(_K_SA, FORMULA_SA_DISPL, [], provisional, value)


def _eval_ballast_displ_pct(snap: EffectiveInputSnapshot) -> MetricResult:
    """HQR-BD-1.0.0 — Ballast / Displacement %."""
    problems: list[MetricStatus] = []
    provisional = False

    hull_p = _hull_problem(snap.hull_configuration, _MONO_ONLY)
    if hull_p is not None:
        problems.append(hull_p)

    problems.extend(
        _field_problems(_FP_BALLAST, snap.ballast_kg, snap.unresolved_fields, require_nonneg=True)
    )
    problems.extend(
        _field_problems(
            _FP_DISPL, snap.displacement_kg, snap.unresolved_fields, require_positive=True
        )
    )

    # Cross-field: ballast > displacement is invalid (checked only when both are individually valid)
    if (
        _is_valid_nonneg(snap.ballast_kg)
        and _is_valid_positive(snap.displacement_kg)
        and float(snap.ballast_kg) > float(snap.displacement_kg)  # type: ignore[arg-type]
    ):
        problems.append(MetricStatus.INVALID_INPUT)

    displ_ns, displ_prov = _displ_basis_flag(snap.displacement_basis)
    if displ_ns:
        problems.append(MetricStatus.NONSTANDARD_INPUT)
    if displ_prov:
        provisional = True

    if problems:
        return _make_result(_K_BD, FORMULA_BALLAST_DISPL_PCT, problems, False, None)

    value = _quantize(100.0 * float(snap.ballast_kg) / float(snap.displacement_kg))  # type: ignore[arg-type]
    return _make_result(_K_BD, FORMULA_BALLAST_DISPL_PCT, [], provisional, value)


def _eval_displ_length(snap: EffectiveInputSnapshot) -> MetricResult:
    """HQR-DL-1.0.0 — Displacement / Length."""
    problems: list[MetricStatus] = []
    provisional = False

    hull_p = _hull_problem(snap.hull_configuration, _MONO_CAT_TRI)
    if hull_p is not None:
        problems.append(hull_p)

    problems.extend(
        _field_problems(
            _FP_DISPL, snap.displacement_kg, snap.unresolved_fields, require_positive=True
        )
    )
    problems.extend(
        _field_problems(_FP_LWL, snap.lwl_m, snap.unresolved_fields, require_positive=True)
    )

    displ_ns, displ_prov = _displ_basis_flag(snap.displacement_basis)
    if displ_ns:
        problems.append(MetricStatus.NONSTANDARD_INPUT)
    if displ_prov:
        provisional = True

    if problems:
        return _make_result(_K_DL, FORMULA_DISPL_LENGTH, problems, False, None)

    displ_lb = float(snap.displacement_kg) / KG_PER_POUND  # type: ignore[arg-type]
    lwl_ft = float(snap.lwl_m) / METRES_PER_FOOT  # type: ignore[arg-type]
    value = _quantize((displ_lb / POUNDS_PER_LONG_TON) / ((0.01 * lwl_ft) ** 3))
    return _make_result(_K_DL, FORMULA_DISPL_LENGTH, [], provisional, value)


def _eval_comfort_ratio(snap: EffectiveInputSnapshot) -> MetricResult:
    """HQR-CR-1.0.0 — Brewer Comfort Ratio (exponent = literal 1.333)."""
    problems: list[MetricStatus] = []
    provisional = False

    hull_p = _hull_problem(snap.hull_configuration, _MONO_ONLY)
    if hull_p is not None:
        problems.append(hull_p)

    problems.extend(
        _field_problems(
            _FP_DISPL, snap.displacement_kg, snap.unresolved_fields, require_positive=True
        )
    )
    problems.extend(
        _field_problems(_FP_LWL, snap.lwl_m, snap.unresolved_fields, require_positive=True)
    )
    problems.extend(
        _field_problems(_FP_LOA, snap.loa_m, snap.unresolved_fields, require_positive=True)
    )
    problems.extend(
        _field_problems(_FP_BEAM, snap.beam_m, snap.unresolved_fields, require_positive=True)
    )

    displ_ns, displ_prov = _displ_basis_flag(snap.displacement_basis)
    if displ_ns:
        problems.append(MetricStatus.NONSTANDARD_INPUT)
    if displ_prov:
        provisional = True

    if problems:
        return _make_result(_K_CR, FORMULA_COMFORT_RATIO, problems, False, None)

    displ_lb = float(snap.displacement_kg) / KG_PER_POUND  # type: ignore[arg-type]
    lwl_ft = float(snap.lwl_m) / METRES_PER_FOOT  # type: ignore[arg-type]
    loa_ft = float(snap.loa_m) / METRES_PER_FOOT  # type: ignore[arg-type]
    beam_ft = float(snap.beam_m) / METRES_PER_FOOT  # type: ignore[arg-type]
    # Exponent MUST be the literal decimal 1.333 (Brewer's published expression)
    value = _quantize(displ_lb / (0.65 * (0.7 * lwl_ft + 0.3 * loa_ft) * (beam_ft**1.333)))
    return _make_result(_K_CR, FORMULA_COMFORT_RATIO, [], provisional, value)


def _eval_capsize_screening(snap: EffectiveInputSnapshot) -> MetricResult:
    """HQR-CSF-1.0.0 — Capsize Screening Formula."""
    problems: list[MetricStatus] = []
    provisional = False

    hull_p = _hull_problem(snap.hull_configuration, _MONO_ONLY)
    if hull_p is not None:
        problems.append(hull_p)

    problems.extend(
        _field_problems(
            _FP_DISPL, snap.displacement_kg, snap.unresolved_fields, require_positive=True
        )
    )
    problems.extend(
        _field_problems(_FP_BEAM, snap.beam_m, snap.unresolved_fields, require_positive=True)
    )

    displ_ns, displ_prov = _displ_basis_flag(snap.displacement_basis)
    if displ_ns:
        problems.append(MetricStatus.NONSTANDARD_INPUT)
    if displ_prov:
        provisional = True

    if problems:
        return _make_result(_K_CSF, FORMULA_CAPSIZE_SCREENING, problems, False, None)

    displ_lb = float(snap.displacement_kg) / KG_PER_POUND  # type: ignore[arg-type]
    beam_ft = float(snap.beam_m) / METRES_PER_FOOT  # type: ignore[arg-type]
    value = _quantize(beam_ft / ((displ_lb / LEGACY_SEAWATER_LB_PER_FT3) ** (1.0 / 3.0)))
    return _make_result(_K_CSF, FORMULA_CAPSIZE_SCREENING, [], provisional, value)


def _eval_hull_speed(snap: EffectiveInputSnapshot) -> MetricResult:
    """HQM-HS-1.0.0 — Legacy/theoretical Hull Speed (knots)."""
    problems: list[MetricStatus] = []

    hull_p = _hull_problem(snap.hull_configuration, _MONO_ONLY)
    if hull_p is not None:
        problems.append(hull_p)

    problems.extend(
        _field_problems(_FP_LWL, snap.lwl_m, snap.unresolved_fields, require_positive=True)
    )

    # Hull Speed has no displacement or sail-area basis dependency
    if problems:
        return _make_result(_K_HS, FORMULA_HULL_SPEED, problems, False, None)

    lwl_ft = float(snap.lwl_m) / METRES_PER_FOOT  # type: ignore[arg-type]
    value = _quantize(1.34 * math.sqrt(lwl_ft))
    return _make_result(_K_HS, FORMULA_HULL_SPEED, [], False, value)


# ---------------------------------------------------------------------------
# Lineage builder
# ---------------------------------------------------------------------------


def _build_lineage_inputs(
    snap: EffectiveInputSnapshot,
    pointers: list[str],
) -> tuple[DerivationInput, ...]:
    """Build DerivationInput entries for the listed field pointers."""
    field_values: dict[str, object] = {
        _FP_LOA: snap.loa_m,
        _FP_LWL: snap.lwl_m,
        _FP_BEAM: snap.beam_m,
        _FP_DISPL: snap.displacement_kg,
        _FP_BALLAST: snap.ballast_kg,
        _FP_SAIL: snap.sail_area_m2,
        _FP_HULL: snap.hull_configuration,
        _FP_DISPL_BASIS: snap.displacement_basis,
        _FP_SAIL_BASIS: snap.sail_area_basis,
    }
    return tuple(
        DerivationInput(
            subject_kind="resolved_configuration",
            subject_id=snap.resolved_configuration_id,
            field_pointer=ptr,
            field_resolution_id=snap.resolution_ids.get(ptr),
            value_snapshot=field_values.get(ptr),
        )
        for ptr in pointers
    )


# Input pointer lists per metric
_SA_DISPL_INPUTS: Final[list[str]] = [
    _FP_SAIL,
    _FP_DISPL,
    _FP_HULL,
    _FP_DISPL_BASIS,
    _FP_SAIL_BASIS,
]
_BD_INPUTS: Final[list[str]] = [_FP_BALLAST, _FP_DISPL, _FP_HULL, _FP_DISPL_BASIS]
_DL_INPUTS: Final[list[str]] = [_FP_DISPL, _FP_LWL, _FP_HULL, _FP_DISPL_BASIS]
_CR_INPUTS: Final[list[str]] = [_FP_DISPL, _FP_LWL, _FP_LOA, _FP_BEAM, _FP_HULL, _FP_DISPL_BASIS]
_CSF_INPUTS: Final[list[str]] = [_FP_DISPL, _FP_BEAM, _FP_HULL, _FP_DISPL_BASIS]
_HS_INPUTS: Final[list[str]] = [_FP_LWL, _FP_HULL]

_METRIC_INPUTS: Final[dict[str, list[str]]] = {
    _K_SA: _SA_DISPL_INPUTS,
    _K_BD: _BD_INPUTS,
    _K_DL: _DL_INPUTS,
    _K_CR: _CR_INPUTS,
    _K_CSF: _CSF_INPUTS,
    _K_HS: _HS_INPUTS,
}

_METRIC_FIELD: Final[dict[str, str]] = {
    _K_SA: f"/derived_metrics/{_K_SA}",
    _K_BD: f"/derived_metrics/{_K_BD}",
    _K_DL: f"/derived_metrics/{_K_DL}",
    _K_CR: f"/derived_metrics/{_K_CR}",
    _K_CSF: f"/derived_metrics/{_K_CSF}",
    _K_HS: f"/derived_metrics/{_K_HS}",
}

_METRIC_FORMULA: Final[dict[str, str]] = {
    _K_SA: FORMULA_SA_DISPL,
    _K_BD: FORMULA_BALLAST_DISPL_PCT,
    _K_DL: FORMULA_DISPL_LENGTH,
    _K_CR: FORMULA_COMFORT_RATIO,
    _K_CSF: FORMULA_CAPSIZE_SCREENING,
    _K_HS: FORMULA_HULL_SPEED,
}

_COMPUTED_STATUSES: Final[frozenset[MetricStatus]] = frozenset(
    {MetricStatus.COMPUTED, MetricStatus.COMPUTED_PROVISIONAL}
)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_derived_metrics(
    snapshot: EffectiveInputSnapshot,
    *,
    derivation_id_factory: Callable[[], str],
    generated_at: str,
    producer_identifier: str = "hullq-derived-metrics-engine",
    producer_version: str | None = METHODOLOGY_VERSION,
    notes: str | None = None,
) -> tuple[DerivedMetrics, list[DerivationRecord]]:
    """Compute all six derived metrics from an effective configuration snapshot.

    Returns:
        (DerivedMetrics, list[DerivationRecord]) — the canonical projection and
        one DerivationRecord per computed/computed_provisional metric.

    Caller supplies derivation IDs and timestamp so the formula core is
    deterministic and testable without hidden clock/UUID calls.

    Does not:
    - modify the input snapshot;
    - create FieldEvidence for derived outputs;
    - implement search semantics, safety scoring, or persistence.
    """
    results: list[MetricResult] = [
        _eval_sa_displ(snapshot),
        _eval_ballast_displ_pct(snapshot),
        _eval_displ_length(snapshot),
        _eval_comfort_ratio(snapshot),
        _eval_capsize_screening(snapshot),
        _eval_hull_speed(snapshot),
    ]

    by_key: dict[str, MetricResult] = {r.metric_key: r for r in results}

    projection = DerivedMetrics(
        methodology_version=METHODOLOGY_VERSION,
        sa_displ=by_key[_K_SA].value,
        ballast_displ_pct=by_key[_K_BD].value,
        displ_length=by_key[_K_DL].value,
        comfort_ratio=by_key[_K_CR].value,
        capsize_screening_formula=by_key[_K_CSF].value,
        hull_speed_kn=by_key[_K_HS].value,
        status={r.metric_key: str(r.status) for r in results},
    )

    derivation_records: list[DerivationRecord] = []
    for result in results:
        if result.status not in _COMPUTED_STATUSES:
            continue
        rec = DerivationRecord(
            schema_version="0.1",
            derivation_id=derivation_id_factory(),
            target_kind="resolved_configuration",
            target_id=snapshot.resolved_configuration_id,
            target_field_pointer=_METRIC_FIELD[result.metric_key],
            method_id=_METRIC_FORMULA[result.metric_key],
            method_version=METHODOLOGY_VERSION,
            inputs=_build_lineage_inputs(snapshot, _METRIC_INPUTS[result.metric_key]),
            output_value_snapshot=result.value,
            producer_kind="deterministic_tool",
            producer_identifier=producer_identifier,
            producer_version=producer_version,
            generated_at=generated_at,
            notes=notes,
        )
        derivation_records.append(rec)

    return projection, derivation_records
