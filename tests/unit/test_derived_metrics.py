"""Unit tests for the derived metrics engine — SLICE-0010.

Covers:
- methodology/formula/constant identity tests
- golden fixture compatibility (golden_metrics.v0.1.json)
- status fixture compatibility (status_cases.v0.2.json)
- hull applicability (mono/cat/tri/other/unknown)
- basis handling (standard/provisional/nonstandard for displacement and sail area)
- numeric validation (zero, negative, NaN, inf, bool)
- ballast > displacement cross-field check
- missing/unresolved input propagation (metric-local)
- status precedence (invalid > unresolved > not_applicable > ...)
- six-decimal round-half-even quantization
- snapshot safety (mutable caller collections)
- DerivationRecord lineage for computed metrics only
- no FieldEvidence created, no safety/search semantics
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hullq.domain.derived_metrics import (
    FORMULA_BALLAST_DISPL_PCT,
    FORMULA_CAPSIZE_SCREENING,
    FORMULA_COMFORT_RATIO,
    FORMULA_DISPL_LENGTH,
    FORMULA_HULL_SPEED,
    FORMULA_SA_DISPL,
    KG_PER_POUND,
    LEGACY_SEAWATER_LB_PER_FT3,
    METHODOLOGY_VERSION,
    METRES_PER_FOOT,
    POUNDS_PER_LONG_TON,
    DerivationRecord,
    DerivedMetrics,
    EffectiveInputSnapshot,
    MetricStatus,
    compute_derived_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "ratios"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GENERATED_AT = "2026-08-19T00:00:00Z"
_PRODUCER_ID = "hullq-test-engine"


def _id_factory() -> Any:
    counter = [0]

    def _next() -> str:
        counter[0] += 1
        return f"DER-TEST-{counter[0]:04d}"

    return _next


def _snap(**kwargs: Any) -> EffectiveInputSnapshot:
    """Build a snapshot from keyword args, with sensible test defaults."""
    defaults: dict[str, Any] = {
        "resolved_configuration_id": "RC-TEST",
        "hull_configuration": "monohull",
        "loa_m": 10.5,
        "lwl_m": 8.7,
        "beam_m": 3.4,
        "displacement_kg": 7000.0,
        "ballast_kg": 2800.0,
        "sail_area_m2": 60.0,
        "displacement_basis": "design",
        "sail_area_basis": "nominal_main_plus_foretriangle",
        "unresolved_fields": None,
        "resolution_ids": None,
    }
    defaults.update(kwargs)
    return EffectiveInputSnapshot.create(**defaults)


def _run(snap: EffectiveInputSnapshot) -> tuple[DerivedMetrics, list[DerivationRecord]]:
    return compute_derived_metrics(
        snap,
        derivation_id_factory=_id_factory(),
        generated_at=_GENERATED_AT,
        producer_identifier=_PRODUCER_ID,
    )


def _metrics(snap: EffectiveInputSnapshot) -> DerivedMetrics:
    return _run(snap)[0]


def _records(snap: EffectiveInputSnapshot) -> list[DerivationRecord]:
    return _run(snap)[1]


# ---------------------------------------------------------------------------
# 1. Identity / constants
# ---------------------------------------------------------------------------


def test_methodology_version() -> None:
    assert METHODOLOGY_VERSION == "hullq-derived-1.0.0"


def test_formula_ids() -> None:
    assert FORMULA_SA_DISPL == "HQR-SAD-1.0.0"
    assert FORMULA_BALLAST_DISPL_PCT == "HQR-BD-1.0.0"
    assert FORMULA_DISPL_LENGTH == "HQR-DL-1.0.0"
    assert FORMULA_COMFORT_RATIO == "HQR-CR-1.0.0"
    assert FORMULA_CAPSIZE_SCREENING == "HQR-CSF-1.0.0"
    assert FORMULA_HULL_SPEED == "HQM-HS-1.0.0"


def test_conversion_constants() -> None:
    assert METRES_PER_FOOT == 0.3048
    assert KG_PER_POUND == 0.45359237
    assert POUNDS_PER_LONG_TON == 2240
    assert LEGACY_SEAWATER_LB_PER_FT3 == 64


def test_status_vocabulary() -> None:
    expected = {
        "computed",
        "computed_provisional",
        "missing_input",
        "unresolved_input",
        "invalid_input",
        "not_applicable",
        "applicability_unknown",
        "nonstandard_input",
    }
    actual = {str(s) for s in MetricStatus}
    assert actual == expected


def test_projection_methodology_version() -> None:
    dm = _metrics(_snap())
    assert dm.methodology_version == METHODOLOGY_VERSION


# ---------------------------------------------------------------------------
# 2. Golden fixture compatibility
# ---------------------------------------------------------------------------


def _load_golden() -> Any:
    return json.loads((FIXTURES / "golden_metrics.v0.1.json").read_text(encoding="utf-8"))


def _load_status_cases() -> Any:
    return json.loads((FIXTURES / "status_cases.v0.2.json").read_text(encoding="utf-8"))


class TestGoldenFixtures:
    """golden_metrics.v0.1.json must reproduce exactly."""

    def _run_case(self, case: dict[str, Any]) -> DerivedMetrics:
        inp = case["input"]
        snap = EffectiveInputSnapshot.create(
            resolved_configuration_id=case.get("id", "GOLD"),
            hull_configuration=inp["hull_configuration"],
            loa_m=inp.get("loa_m"),
            lwl_m=inp.get("lwl_m"),
            beam_m=inp.get("beam_m"),
            displacement_kg=inp.get("displacement_kg"),
            ballast_kg=inp.get("ballast_kg"),
            sail_area_m2=inp.get("sail_area_m2"),
            displacement_basis=inp["displacement_basis"],
            sail_area_basis=inp["sail_area_basis"],
        )
        return _metrics(snap)

    def test_gold_001_standard_monohull(self) -> None:
        data = _load_golden()
        case = next(c for c in data["cases"] if c["id"] == "RATIO-GOLD-001")
        dm = self._run_case(case)
        exp = case["expected"]

        assert dm.sa_displ == pytest.approx(exp["sa_displ"], abs=1e-6)
        assert dm.ballast_displ_pct == pytest.approx(exp["ballast_displ_pct"], abs=1e-6)
        assert dm.displ_length == pytest.approx(exp["displ_length"], abs=1e-6)
        assert dm.comfort_ratio == pytest.approx(exp["comfort_ratio"], abs=1e-6)
        assert dm.capsize_screening_formula == pytest.approx(
            exp["capsize_screening_formula"], abs=1e-6
        )
        assert dm.hull_speed_kn == pytest.approx(exp["hull_speed_kn"], abs=1e-6)

        for key, expected_status in exp["status"].items():
            assert dm.status[key] == expected_status, f"{key}: got {dm.status[key]!r}"

    def test_gold_002_catamaran_applicability_split(self) -> None:
        data = _load_golden()
        case = next(c for c in data["cases"] if c["id"] == "RATIO-GOLD-002")
        dm = self._run_case(case)
        exp = case["expected"]

        # Computed metrics
        assert dm.sa_displ == pytest.approx(exp["sa_displ"], abs=1e-6)
        assert dm.displ_length == pytest.approx(exp["displ_length"], abs=1e-6)

        # Null metrics
        assert dm.ballast_displ_pct is None
        assert dm.comfort_ratio is None
        assert dm.capsize_screening_formula is None
        assert dm.hull_speed_kn is None

        # Statuses
        for key, expected_status in exp["status"].items():
            assert dm.status[key] == expected_status

    def test_gold_003_provisional_basis(self) -> None:
        data = _load_golden()
        case = next(c for c in data["cases"] if c["id"] == "RATIO-GOLD-003")
        dm = self._run_case(case)
        exp = case["expected"]

        # Values same as GOLD-001 (same inputs, only basis differs)
        assert dm.sa_displ == pytest.approx(exp["sa_displ"], abs=1e-6)
        assert dm.ballast_displ_pct == pytest.approx(exp["ballast_displ_pct"], abs=1e-6)
        assert dm.displ_length == pytest.approx(exp["displ_length"], abs=1e-6)
        assert dm.comfort_ratio == pytest.approx(exp["comfort_ratio"], abs=1e-6)
        assert dm.capsize_screening_formula == pytest.approx(
            exp["capsize_screening_formula"], abs=1e-6
        )
        assert dm.hull_speed_kn == pytest.approx(exp["hull_speed_kn"], abs=1e-6)

        # Statuses — hull speed should be computed, others computed_provisional
        for key, expected_status in exp["status"].items():
            assert dm.status[key] == expected_status

    def test_compat_001_rustler_dl(self) -> None:
        data = _load_golden()
        case = next(c for c in data["cases"] if c["id"] == "RATIO-COMPAT-001")
        dm = self._run_case(case)
        exp = case["expected"]

        assert dm.displ_length == pytest.approx(exp["displ_length"], abs=1e-6)


# ---------------------------------------------------------------------------
# 3. Status fixture compatibility
# ---------------------------------------------------------------------------


class TestStatusFixtures:
    """status_cases.v0.2.json must reproduce expected statuses/values exactly."""

    def _run_case(self, case: dict[str, Any]) -> DerivedMetrics:
        inp = case["input"]
        unresolved = case.get("unresolved_fields", [])
        snap = EffectiveInputSnapshot.create(
            resolved_configuration_id=case.get("id", "STATUS"),
            hull_configuration=inp["hull_configuration"],
            loa_m=inp.get("loa_m"),
            lwl_m=inp.get("lwl_m"),
            beam_m=inp.get("beam_m"),
            displacement_kg=inp.get("displacement_kg"),
            ballast_kg=inp.get("ballast_kg"),
            sail_area_m2=inp.get("sail_area_m2"),
            displacement_basis=inp["displacement_basis"],
            sail_area_basis=inp["sail_area_basis"],
            unresolved_fields=unresolved,
        )
        return _metrics(snap)

    @pytest.mark.parametrize(
        "case_id",
        [
            "RATIO-STATUS-001",
            "RATIO-STATUS-002",
            "RATIO-STATUS-003",
            "RATIO-STATUS-004",
            "RATIO-STATUS-005",
            "RATIO-STATUS-006",
            "RATIO-STATUS-007",
            "RATIO-STATUS-008",
        ],
    )
    def test_status_case(self, case_id: str) -> None:
        data = _load_status_cases()
        case = next(c for c in data["cases"] if c["id"] == case_id)
        dm = self._run_case(case)

        values = {
            "sa_displ": dm.sa_displ,
            "ballast_displ_pct": dm.ballast_displ_pct,
            "displ_length": dm.displ_length,
            "comfort_ratio": dm.comfort_ratio,
            "capsize_screening_formula": dm.capsize_screening_formula,
            "hull_speed_kn": dm.hull_speed_kn,
        }

        for metric_key, expected in case["expected"].items():
            expected_value = expected["value"]
            expected_status = expected["status"]
            actual_status = dm.status[metric_key]
            actual_value = values[metric_key]

            assert actual_status == expected_status, (
                f"[{case_id}] {metric_key}: status={actual_status!r}, expected={expected_status!r}"
            )
            if expected_value is None:
                assert actual_value is None, (
                    f"[{case_id}] {metric_key}: expected null value, got {actual_value!r}"
                )
            else:
                assert actual_value == pytest.approx(expected_value, abs=1e-6), (
                    f"[{case_id}] {metric_key}: value={actual_value!r}, expected={expected_value!r}"
                )


# ---------------------------------------------------------------------------
# 4. Monohull full computation
# ---------------------------------------------------------------------------


def test_monohull_computes_all_six() -> None:
    dm = _metrics(_snap())
    assert dm.sa_displ is not None
    assert dm.ballast_displ_pct is not None
    assert dm.displ_length is not None
    assert dm.comfort_ratio is not None
    assert dm.capsize_screening_formula is not None
    assert dm.hull_speed_kn is not None
    for status in dm.status.values():
        assert status == "computed"


# ---------------------------------------------------------------------------
# 5. Hull applicability
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("hull", ["catamaran", "trimaran"])
def test_multihull_monohull_only_metrics_not_applicable(hull: str) -> None:
    dm = _metrics(_snap(hull_configuration=hull, beam_m=6.0, ballast_kg=0))
    assert dm.ballast_displ_pct is None
    assert dm.comfort_ratio is None
    assert dm.capsize_screening_formula is None
    assert dm.hull_speed_kn is None
    assert dm.status["ballast_displ_pct"] == "not_applicable"
    assert dm.status["comfort_ratio"] == "not_applicable"
    assert dm.status["capsize_screening_formula"] == "not_applicable"
    assert dm.status["hull_speed_kn"] == "not_applicable"


@pytest.mark.parametrize("hull", ["catamaran", "trimaran"])
def test_multihull_computes_sa_and_dl(hull: str) -> None:
    dm = _metrics(_snap(hull_configuration=hull, beam_m=6.0, ballast_kg=0))
    assert dm.sa_displ is not None
    assert dm.displ_length is not None
    assert dm.status["sa_displ"] == "computed"
    assert dm.status["displ_length"] == "computed"


@pytest.mark.parametrize("hull", ["other", "unknown"])
def test_ambiguous_hull_all_applicability_unknown(hull: str) -> None:
    dm = _metrics(_snap(hull_configuration=hull))
    for key in [
        "sa_displ",
        "ballast_displ_pct",
        "displ_length",
        "comfort_ratio",
        "capsize_screening_formula",
        "hull_speed_kn",
    ]:
        assert dm.status[key] == "applicability_unknown", f"{key}"
        assert getattr(dm, key) is None or key not in ("sa_displ", "displ_length")


def test_unknown_hull_produces_applicability_unknown_for_sa_and_dl() -> None:
    dm = _metrics(_snap(hull_configuration="unknown"))
    assert dm.status["sa_displ"] == "applicability_unknown"
    assert dm.status["displ_length"] == "applicability_unknown"
    assert dm.sa_displ is None
    assert dm.displ_length is None


# ---------------------------------------------------------------------------
# 6. Displacement basis handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("basis", ["design", "lightship"])
def test_standard_displacement_basis_computed(basis: str) -> None:
    dm = _metrics(_snap(displacement_basis=basis))
    for key in ["ballast_displ_pct", "displ_length", "comfort_ratio", "capsize_screening_formula"]:
        assert dm.status[key] == "computed", f"{key}"
    assert dm.status["hull_speed_kn"] == "computed"


@pytest.mark.parametrize("basis", ["source_unspecified", "unknown"])
def test_provisional_displacement_basis_makes_displacement_metrics_provisional(basis: str) -> None:
    dm = _metrics(_snap(displacement_basis=basis))
    for key in ["ballast_displ_pct", "displ_length", "comfort_ratio", "capsize_screening_formula"]:
        assert dm.status[key] == "computed_provisional", f"{key}"
    # Hull speed has no displacement dependency
    assert dm.status["hull_speed_kn"] == "computed"


@pytest.mark.parametrize("basis", ["normal_sailing", "full_load"])
def test_nonstandard_displacement_basis_nulls_displacement_metrics(basis: str) -> None:
    dm = _metrics(_snap(displacement_basis=basis))
    for key in ["ballast_displ_pct", "displ_length", "comfort_ratio", "capsize_screening_formula"]:
        assert dm.status[key] == "nonstandard_input", f"{key}"
        assert getattr(dm, key) is None
    # Hull speed unaffected
    assert dm.status["hull_speed_kn"] == "computed"
    assert dm.hull_speed_kn is not None


# ---------------------------------------------------------------------------
# 7. Sail-area basis handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("basis", ["nominal_main_plus_foretriangle", "upwind_100pct"])
def test_standard_sail_basis_computes_sa_displ(basis: str) -> None:
    dm = _metrics(_snap(sail_area_basis=basis))
    assert dm.status["sa_displ"] == "computed"
    assert dm.sa_displ is not None


@pytest.mark.parametrize("basis", ["source_unspecified", "unknown"])
def test_provisional_sail_basis_makes_sa_displ_provisional(basis: str) -> None:
    dm = _metrics(_snap(sail_area_basis=basis))
    assert dm.status["sa_displ"] == "computed_provisional"
    assert dm.sa_displ is not None


@pytest.mark.parametrize("basis", ["working_sails_actual", "downwind"])
def test_nonstandard_sail_basis_nulls_sa_displ_only(basis: str) -> None:
    dm = _metrics(_snap(sail_area_basis=basis))
    assert dm.status["sa_displ"] == "nonstandard_input"
    assert dm.sa_displ is None
    # Other displacement-based metrics are unaffected by sail-area basis
    assert dm.status["displ_length"] == "computed"
    assert dm.status["hull_speed_kn"] == "computed"


def test_hull_speed_independent_of_both_bases() -> None:
    dm = _metrics(_snap(displacement_basis="normal_sailing", sail_area_basis="downwind"))
    assert dm.status["hull_speed_kn"] == "computed"
    assert dm.hull_speed_kn is not None


# ---------------------------------------------------------------------------
# 8. Missing input (metric-local)
# ---------------------------------------------------------------------------


def test_missing_sail_area_blocks_only_sa_displ() -> None:
    dm = _metrics(_snap(sail_area_m2=None))
    assert dm.status["sa_displ"] == "missing_input"
    assert dm.sa_displ is None
    assert dm.status["hull_speed_kn"] == "computed"
    assert dm.hull_speed_kn is not None
    assert dm.status["displ_length"] == "computed"


def test_missing_displacement_blocks_displacement_metrics() -> None:
    dm = _metrics(_snap(displacement_kg=None))
    for key in [
        "sa_displ",
        "ballast_displ_pct",
        "displ_length",
        "comfort_ratio",
        "capsize_screening_formula",
    ]:
        assert dm.status[key] == "missing_input", f"{key}"
    # Hull speed unaffected
    assert dm.status["hull_speed_kn"] == "computed"


def test_missing_lwl_blocks_relevant_metrics() -> None:
    dm = _metrics(_snap(lwl_m=None))
    for key in ["displ_length", "comfort_ratio", "hull_speed_kn"]:
        assert dm.status[key] == "missing_input", f"{key}"
    # CSF doesn't need LWL; B/D doesn't; SA/D doesn't
    assert dm.status["capsize_screening_formula"] == "computed"
    assert dm.status["ballast_displ_pct"] == "computed"
    assert dm.status["sa_displ"] == "computed"


def test_missing_ballast_blocks_only_bd() -> None:
    dm = _metrics(_snap(ballast_kg=None))
    assert dm.status["ballast_displ_pct"] == "missing_input"
    assert dm.ballast_displ_pct is None
    # Other metrics unaffected
    assert dm.status["sa_displ"] == "computed"
    assert dm.status["hull_speed_kn"] == "computed"


def test_missing_loa_blocks_only_comfort_ratio() -> None:
    dm = _metrics(_snap(loa_m=None))
    assert dm.status["comfort_ratio"] == "missing_input"
    assert dm.comfort_ratio is None
    assert dm.status["sa_displ"] == "computed"
    assert dm.status["hull_speed_kn"] == "computed"


def test_missing_beam_blocks_comfort_ratio_and_csf() -> None:
    dm = _metrics(_snap(beam_m=None))
    assert dm.status["comfort_ratio"] == "missing_input"
    assert dm.status["capsize_screening_formula"] == "missing_input"
    assert dm.status["sa_displ"] == "computed"


def test_missing_lwl_blocks_hull_speed() -> None:
    dm = _metrics(_snap(lwl_m=None))
    assert dm.status["hull_speed_kn"] == "missing_input"
    assert dm.hull_speed_kn is None


# ---------------------------------------------------------------------------
# 9. Unresolved input (metric-local)
# ---------------------------------------------------------------------------


def test_unresolved_displacement_blocks_displacement_metrics() -> None:
    dm = _metrics(_snap(unresolved_fields=["/effective/dimensions/displacement_kg"]))
    for key in [
        "sa_displ",
        "ballast_displ_pct",
        "displ_length",
        "comfort_ratio",
        "capsize_screening_formula",
    ]:
        assert dm.status[key] == "unresolved_input", f"{key}"
    # Hull speed has no displacement dependency
    assert dm.status["hull_speed_kn"] == "computed"


def test_unresolved_lwl_blocks_lwl_dependent_only() -> None:
    dm = _metrics(_snap(unresolved_fields=["/effective/dimensions/lwl_m"]))
    for key in ["displ_length", "comfort_ratio", "hull_speed_kn"]:
        assert dm.status[key] == "unresolved_input", f"{key}"
    assert dm.status["sa_displ"] == "computed"
    assert dm.status["capsize_screening_formula"] == "computed"
    assert dm.status["ballast_displ_pct"] == "computed"


def test_unresolved_sail_area_blocks_only_sa_displ() -> None:
    dm = _metrics(_snap(unresolved_fields=["/effective/dimensions/sail_area_m2"]))
    assert dm.status["sa_displ"] == "unresolved_input"
    assert dm.status["hull_speed_kn"] == "computed"
    assert dm.status["displ_length"] == "computed"


# ---------------------------------------------------------------------------
# 10. Status precedence
# ---------------------------------------------------------------------------


def test_invalid_outranks_unresolved() -> None:
    # displacement is both 0 (invalid) and marked unresolved
    dm = _metrics(
        _snap(
            displacement_kg=0,
            unresolved_fields=["/effective/dimensions/displacement_kg"],
        )
    )
    assert dm.status["sa_displ"] == "invalid_input"
    assert dm.status["displ_length"] == "invalid_input"


def test_invalid_outranks_not_applicable_for_cat() -> None:
    # catamaran + zero displacement → invalid beats not_applicable for BD/CR/CSF/HS
    dm = _metrics(_snap(hull_configuration="catamaran", displacement_kg=0, ballast_kg=0))
    assert dm.status["ballast_displ_pct"] == "invalid_input"
    assert dm.status["comfort_ratio"] == "invalid_input"
    assert dm.status["capsize_screening_formula"] == "invalid_input"
    assert dm.status["hull_speed_kn"] == "not_applicable"  # hull speed doesn't use displacement


def test_not_applicable_outranks_missing_input() -> None:
    # catamaran + missing ballast: not_applicable wins over missing_input for BD
    dm = _metrics(_snap(hull_configuration="catamaran", ballast_kg=None, beam_m=6.0))
    assert dm.status["ballast_displ_pct"] == "not_applicable"


def test_not_applicable_outranks_nonstandard_input() -> None:
    # catamaran + nonstandard basis: not_applicable wins for BD (monohull-only)
    dm = _metrics(
        _snap(
            hull_configuration="catamaran",
            displacement_basis="normal_sailing",
            ballast_kg=0,
            beam_m=6.0,
        )
    )
    assert dm.status["ballast_displ_pct"] == "not_applicable"


def test_applicability_unknown_outranks_missing_input() -> None:
    dm = _metrics(_snap(hull_configuration="unknown", lwl_m=None))
    # hull_speed_kn: applicability_unknown (3) > missing_input (4)
    assert dm.status["hull_speed_kn"] == "applicability_unknown"


def test_nonstandard_outranks_provisional() -> None:
    # SA/D: nonstandard sail basis + provisional displacement basis → nonstandard wins
    dm = _metrics(
        _snap(displacement_basis="source_unspecified", sail_area_basis="working_sails_actual")
    )
    assert dm.status["sa_displ"] == "nonstandard_input"
    assert dm.sa_displ is None


def test_ballast_gt_displacement_is_invalid_only_for_bd() -> None:
    dm = _metrics(_snap(ballast_kg=8000, displacement_kg=7000))
    assert dm.status["ballast_displ_pct"] == "invalid_input"
    assert dm.ballast_displ_pct is None
    # Other metrics that don't use ballast are still computable
    assert dm.status["sa_displ"] == "computed"
    assert dm.status["displ_length"] == "computed"
    assert dm.status["hull_speed_kn"] == "computed"


# ---------------------------------------------------------------------------
# 11. Numeric validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("displacement_kg", 0),
        ("displacement_kg", -100),
        ("sail_area_m2", 0),
        ("sail_area_m2", -1),
        ("lwl_m", 0),
        ("lwl_m", -0.1),
        ("loa_m", 0),
        ("beam_m", -1),
    ],
)
def test_zero_or_negative_required_value_is_invalid(field: str, value: float) -> None:
    dm = _metrics(_snap(**{field: value}))
    # Find metrics that depend on this field
    if field == "displacement_kg":
        for key in [
            "sa_displ",
            "ballast_displ_pct",
            "displ_length",
            "comfort_ratio",
            "capsize_screening_formula",
        ]:
            assert dm.status[key] == "invalid_input", f"{key}"
    elif field == "sail_area_m2":
        assert dm.status["sa_displ"] == "invalid_input"
    elif field in ("lwl_m",):
        for key in ["displ_length", "comfort_ratio", "hull_speed_kn"]:
            assert dm.status[key] == "invalid_input", f"{key}"
    elif field == "loa_m":
        assert dm.status["comfort_ratio"] == "invalid_input"
    elif field == "beam_m":
        assert dm.status["comfort_ratio"] == "invalid_input"
        assert dm.status["capsize_screening_formula"] == "invalid_input"


@pytest.mark.parametrize(
    "field",
    [
        "displacement_kg",
        "sail_area_m2",
        "lwl_m",
        "loa_m",
        "beam_m",
        "ballast_kg",
    ],
)
def test_nan_is_invalid(field: str) -> None:
    dm = _metrics(_snap(**{field: float("nan")}))
    # Every metric that depends on this field should be invalid
    expected_invalid = {
        "displacement_kg": [
            "sa_displ",
            "ballast_displ_pct",
            "displ_length",
            "comfort_ratio",
            "capsize_screening_formula",
        ],
        "sail_area_m2": ["sa_displ"],
        "lwl_m": ["displ_length", "comfort_ratio", "hull_speed_kn"],
        "loa_m": ["comfort_ratio"],
        "beam_m": ["comfort_ratio", "capsize_screening_formula"],
        "ballast_kg": ["ballast_displ_pct"],
    }
    for key in expected_invalid[field]:
        assert dm.status[key] == "invalid_input", f"{field} nan → {key}"


@pytest.mark.parametrize("field", ["displacement_kg", "lwl_m", "sail_area_m2"])
def test_inf_is_invalid(field: str) -> None:
    dm = _metrics(_snap(**{field: float("inf")}))
    if field == "displacement_kg":
        assert dm.status["sa_displ"] == "invalid_input"
    elif field == "lwl_m":
        assert dm.status["hull_speed_kn"] == "invalid_input"
    elif field == "sail_area_m2":
        assert dm.status["sa_displ"] == "invalid_input"


@pytest.mark.parametrize(
    "field",
    [
        "displacement_kg",
        "lwl_m",
        "loa_m",
        "beam_m",
        "sail_area_m2",
        "ballast_kg",
    ],
)
def test_bool_not_accepted_as_numeric_input(field: str) -> None:
    dm = _metrics(_snap(**{field: True}))
    expected_invalid = {
        "displacement_kg": [
            "sa_displ",
            "ballast_displ_pct",
            "displ_length",
            "comfort_ratio",
            "capsize_screening_formula",
        ],
        "lwl_m": ["displ_length", "comfort_ratio", "hull_speed_kn"],
        "loa_m": ["comfort_ratio"],
        "beam_m": ["comfort_ratio", "capsize_screening_formula"],
        "sail_area_m2": ["sa_displ"],
        "ballast_kg": ["ballast_displ_pct"],
    }
    for key in expected_invalid[field]:
        assert dm.status[key] == "invalid_input", f"bool {field} → {key}"


def test_negative_ballast_is_invalid_for_bd() -> None:
    dm = _metrics(_snap(ballast_kg=-1.0))
    assert dm.status["ballast_displ_pct"] == "invalid_input"


# ---------------------------------------------------------------------------
# 12. Six-decimal round-half-even quantization
# ---------------------------------------------------------------------------


def test_canonical_values_have_six_decimals() -> None:
    dm = _metrics(_snap())
    for key in [
        "sa_displ",
        "ballast_displ_pct",
        "displ_length",
        "comfort_ratio",
        "capsize_screening_formula",
        "hull_speed_kn",
    ]:
        v = getattr(dm, key)
        assert v is not None
        # Verify rounding to 6 decimal places: round-trip through decimal must be identical
        from decimal import ROUND_HALF_EVEN, Decimal

        quantized = float(Decimal(repr(v)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))
        assert v == quantized, f"{key}: {v!r} is not 6-decimal quantized"


def test_repeated_computation_is_identical() -> None:
    snap = _snap()
    dm1 = _metrics(snap)
    dm2 = _metrics(snap)
    assert dm1.sa_displ == dm2.sa_displ
    assert dm1.hull_speed_kn == dm2.hull_speed_kn
    assert dm1.status == dm2.status


# ---------------------------------------------------------------------------
# 13. Null for noncomputed statuses
# ---------------------------------------------------------------------------


def test_null_when_missing() -> None:
    dm = _metrics(_snap(sail_area_m2=None))
    assert dm.sa_displ is None
    assert dm.status["sa_displ"] == "missing_input"


def test_null_when_not_applicable() -> None:
    dm = _metrics(_snap(hull_configuration="catamaran", ballast_kg=0, beam_m=6.0))
    assert dm.ballast_displ_pct is None
    assert dm.hull_speed_kn is None


def test_null_when_nonstandard() -> None:
    dm = _metrics(_snap(sail_area_basis="working_sails_actual"))
    assert dm.sa_displ is None


def test_null_when_invalid() -> None:
    dm = _metrics(_snap(displacement_kg=0))
    assert dm.sa_displ is None
    assert dm.ballast_displ_pct is None


# ---------------------------------------------------------------------------
# 14. DerivationRecord lineage
# ---------------------------------------------------------------------------


def test_derivation_record_produced_for_each_computed_metric() -> None:
    snap = _snap()
    _, records = _run(snap)
    # Full monohull standard case → all 6 metrics computed
    assert len(records) == 6
    keys = {r.target_field_pointer.split("/")[-1] for r in records}
    expected_keys = {
        "sa_displ",
        "ballast_displ_pct",
        "displ_length",
        "comfort_ratio",
        "capsize_screening_formula",
        "hull_speed_kn",
    }
    assert keys == expected_keys


def test_no_derivation_record_for_null_metrics() -> None:
    snap = _snap(hull_configuration="catamaran", ballast_kg=0, beam_m=6.0)
    _, records = _run(snap)
    # Only sa_displ and displ_length are computed
    target_metrics = {r.target_field_pointer.split("/")[-1] for r in records}
    assert "ballast_displ_pct" not in target_metrics
    assert "hull_speed_kn" not in target_metrics
    assert "sa_displ" in target_metrics
    assert "displ_length" in target_metrics


def test_derivation_target_kind_resolved_configuration() -> None:
    _, records = _run(_snap())
    for rec in records:
        assert rec.target_kind == "resolved_configuration"


def test_derivation_target_id_matches_snapshot() -> None:
    snap = _snap(resolved_configuration_id="RC-SPECIFIC-001")
    _, records = _run(snap)
    for rec in records:
        assert rec.target_id == "RC-SPECIFIC-001"


def test_derivation_target_field_pointer_valid() -> None:
    _, records = _run(_snap())
    for rec in records:
        assert rec.target_field_pointer.startswith("/derived_metrics/")


def test_derivation_method_ids_correct() -> None:
    _, records = _run(_snap())
    expected_by_metric = {
        "sa_displ": "HQR-SAD-1.0.0",
        "ballast_displ_pct": "HQR-BD-1.0.0",
        "displ_length": "HQR-DL-1.0.0",
        "comfort_ratio": "HQR-CR-1.0.0",
        "capsize_screening_formula": "HQR-CSF-1.0.0",
        "hull_speed_kn": "HQM-HS-1.0.0",
    }
    for rec in records:
        metric = rec.target_field_pointer.split("/")[-1]
        assert rec.method_id == expected_by_metric[metric]


def test_derivation_method_version_matches_methodology() -> None:
    _, records = _run(_snap())
    for rec in records:
        assert rec.method_version == METHODOLOGY_VERSION


def test_derivation_output_snapshot_equals_metric_value() -> None:
    dm, records = _run(_snap())
    value_by_metric = {
        "sa_displ": dm.sa_displ,
        "ballast_displ_pct": dm.ballast_displ_pct,
        "displ_length": dm.displ_length,
        "comfort_ratio": dm.comfort_ratio,
        "capsize_screening_formula": dm.capsize_screening_formula,
        "hull_speed_kn": dm.hull_speed_kn,
    }
    for rec in records:
        metric = rec.target_field_pointer.split("/")[-1]
        assert rec.output_value_snapshot == value_by_metric[metric]


def test_derivation_inputs_include_relevant_fields() -> None:
    _, records = _run(_snap())
    by_metric = {r.target_field_pointer.split("/")[-1]: r for r in records}

    # SA/D must include sail area, displacement, hull config, displacement basis, sail basis
    sa_rec = by_metric["sa_displ"]
    sa_ptrs = {inp.field_pointer for inp in sa_rec.inputs}
    assert "/effective/dimensions/sail_area_m2" in sa_ptrs
    assert "/effective/dimensions/displacement_kg" in sa_ptrs
    assert "/effective/configuration/hull_configuration" in sa_ptrs
    assert "/effective/ratio_input_basis/displacement_basis" in sa_ptrs
    assert "/effective/ratio_input_basis/sail_area_basis" in sa_ptrs

    # Hull speed must include lwl and hull config
    hs_rec = by_metric["hull_speed_kn"]
    hs_ptrs = {inp.field_pointer for inp in hs_rec.inputs}
    assert "/effective/dimensions/lwl_m" in hs_ptrs
    assert "/effective/configuration/hull_configuration" in hs_ptrs
    # Hull speed does NOT depend on displacement or sail area basis
    assert "/effective/ratio_input_basis/displacement_basis" not in hs_ptrs


def test_derivation_input_value_snapshots_preserved() -> None:
    snap = _snap(lwl_m=8.7)
    _, records = _run(snap)
    for rec in records:
        for inp in rec.inputs:
            if inp.field_pointer == "/effective/dimensions/lwl_m":
                assert inp.value_snapshot == 8.7


def test_derivation_resolution_id_included_when_supplied() -> None:
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-WITH-RES",
        hull_configuration="monohull",
        loa_m=10.5,
        lwl_m=8.7,
        beam_m=3.4,
        displacement_kg=7000.0,
        ballast_kg=2800.0,
        sail_area_m2=60.0,
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
        resolution_ids={
            "/effective/dimensions/displacement_kg": "RES-DISPL-001",
        },
    )
    _, records = _run(snap)
    for rec in records:
        for inp in rec.inputs:
            if inp.field_pointer == "/effective/dimensions/displacement_kg":
                assert inp.field_resolution_id == "RES-DISPL-001"
            elif inp.field_pointer == "/effective/dimensions/lwl_m":
                assert inp.field_resolution_id is None


def test_derivation_resolution_id_null_when_not_supplied() -> None:
    snap = _snap()
    _, records = _run(snap)
    for rec in records:
        for inp in rec.inputs:
            assert inp.field_resolution_id is None


def test_derivation_producer_kind_deterministic_tool() -> None:
    _, records = _run(_snap())
    for rec in records:
        assert rec.producer_kind == "deterministic_tool"


def test_derivation_generated_at_passed_through() -> None:
    ts = "2026-01-01T12:00:00Z"
    snap = _snap()
    _, records = compute_derived_metrics(
        snap,
        derivation_id_factory=_id_factory(),
        generated_at=ts,
    )
    for rec in records:
        assert rec.generated_at == ts


def test_derivation_ids_from_factory() -> None:
    ids_issued: list[str] = []

    def factory() -> str:
        uid = f"TEST-{len(ids_issued):04d}"
        ids_issued.append(uid)
        return uid

    _, records = compute_derived_metrics(
        _snap(),
        derivation_id_factory=factory,
        generated_at=_GENERATED_AT,
    )
    assert len(records) == 6
    issued_set = set(ids_issued)
    record_ids = {r.derivation_id for r in records}
    assert record_ids == issued_set


def test_schema_version_is_0_1() -> None:
    _, records = _run(_snap())
    for rec in records:
        assert rec.schema_version == "0.1"


# ---------------------------------------------------------------------------
# 15. No FieldEvidence created
# ---------------------------------------------------------------------------


def test_no_field_evidence_in_output() -> None:
    """compute_derived_metrics returns only DerivedMetrics + DerivationRecords."""
    result = _run(_snap())
    # Just verify the return types — no FieldEvidence type possible
    dm, records = result
    assert isinstance(dm, DerivedMetrics)
    for rec in records:
        assert isinstance(rec, DerivationRecord)
    # Derivation records must not carry field_evidence attributes
    for rec in records:
        assert not hasattr(rec, "evidence_id")
        assert not hasattr(rec, "source_id")


# ---------------------------------------------------------------------------
# 16. Snapshot safety
# ---------------------------------------------------------------------------


def test_mutable_unresolved_fields_cannot_mutate_snapshot() -> None:
    unresolved: list[str] = []
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-SNAP",
        hull_configuration="monohull",
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
        unresolved_fields=unresolved,
        displacement_kg=7000.0,
        lwl_m=8.7,
        loa_m=10.5,
        beam_m=3.4,
        ballast_kg=2800.0,
        sail_area_m2=60.0,
    )
    dm_before = _metrics(snap)
    # Mutate the original list after snapshot creation
    unresolved.append("/effective/dimensions/displacement_kg")
    dm_after = _metrics(snap)
    assert dm_before.status["sa_displ"] == dm_after.status["sa_displ"]
    assert dm_before.status["hull_speed_kn"] == dm_after.status["hull_speed_kn"]


def test_mutable_resolution_ids_cannot_mutate_snapshot() -> None:
    resolution_ids: dict[str, str] = {}
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-SNAP2",
        hull_configuration="monohull",
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
        resolution_ids=resolution_ids,
        displacement_kg=7000.0,
        lwl_m=8.7,
        loa_m=10.5,
        beam_m=3.4,
        ballast_kg=2800.0,
        sail_area_m2=60.0,
    )
    _, records_before = _run(snap)
    resolution_ids["/effective/dimensions/displacement_kg"] = "LATE-RES-001"
    _, records_after = _run(snap)
    # Both runs should have no resolution_ids in inputs since dict was empty at create time
    for rec in records_before:
        for inp in rec.inputs:
            if inp.field_pointer == "/effective/dimensions/displacement_kg":
                assert inp.field_resolution_id is None
    for rec in records_after:
        for inp in rec.inputs:
            if inp.field_pointer == "/effective/dimensions/displacement_kg":
                assert inp.field_resolution_id is None


# ---------------------------------------------------------------------------
# 17. DerivedMetrics.as_dict() matches schema shape
# ---------------------------------------------------------------------------


def test_as_dict_has_required_keys() -> None:
    dm = _metrics(_snap())
    d = dm.as_dict()
    required = {
        "methodology_version",
        "sa_displ",
        "ballast_displ_pct",
        "displ_length",
        "comfort_ratio",
        "capsize_screening_formula",
        "hull_speed_kn",
        "status",
    }
    assert set(d.keys()) == required


def test_as_dict_methodology_version() -> None:
    dm = _metrics(_snap())
    assert dm.as_dict()["methodology_version"] == "hullq-derived-1.0.0"


def test_as_dict_status_is_string_dict() -> None:
    dm = _metrics(_snap())
    status = dm.as_dict()["status"]
    assert isinstance(status, dict)
    for v in status.values():
        assert isinstance(v, str)


# ---------------------------------------------------------------------------
# 18. EffectiveInputSnapshot validation
# ---------------------------------------------------------------------------


def test_empty_resolved_configuration_id_raises() -> None:
    with pytest.raises(ValueError, match="resolved_configuration_id"):
        EffectiveInputSnapshot.create(
            resolved_configuration_id="",
            hull_configuration="monohull",
            displacement_basis="design",
            sail_area_basis="nominal_main_plus_foretriangle",
        )


def test_snapshot_create_defaults_optional_fields() -> None:
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-MIN",
        hull_configuration="monohull",
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
    )
    assert snap.loa_m is None
    assert snap.lwl_m is None
    assert snap.unresolved_fields == frozenset()
    assert snap.resolution_ids == {}


# ---------------------------------------------------------------------------
# 19. DerivationRecord.as_dict() matches DERIVATION_RECORD_SCHEMA shape
# ---------------------------------------------------------------------------


def test_derivation_as_dict_structure() -> None:
    _, records = _run(_snap())
    for rec in records:
        d = rec.as_dict()
        assert "schema_version" in d
        assert "derivation_id" in d
        assert "target" in d
        assert "method" in d
        assert "inputs" in d
        assert "output_value_snapshot" in d
        assert "producer" in d
        assert "generated_at" in d
        assert "notes" in d
        assert d["target"]["kind"] == "resolved_configuration"
        assert isinstance(d["inputs"], list)
        for inp in d["inputs"]:
            assert "subject" in inp
            assert "field_pointer" in inp
            assert "field_resolution_id" in inp
            assert "value_snapshot" in inp


# ---------------------------------------------------------------------------
# 20. Provisional catamaran case
# ---------------------------------------------------------------------------


def test_catamaran_provisional_sa_and_dl() -> None:
    dm = _metrics(
        _snap(
            hull_configuration="catamaran",
            displacement_basis="source_unspecified",
            sail_area_basis="source_unspecified",
            beam_m=6.0,
            ballast_kg=0,
        )
    )
    assert dm.status["sa_displ"] == "computed_provisional"
    assert dm.sa_displ is not None
    assert dm.status["displ_length"] == "computed_provisional"
    assert dm.displ_length is not None


# ---------------------------------------------------------------------------
# 21. ballast_kg = 0 is valid for B/D% (zero ballast is allowed)
# ---------------------------------------------------------------------------


def test_zero_ballast_is_valid_bd_zero_percent() -> None:
    dm = _metrics(_snap(ballast_kg=0))
    assert dm.status["ballast_displ_pct"] == "computed"
    assert dm.ballast_displ_pct == pytest.approx(0.0, abs=1e-6)
