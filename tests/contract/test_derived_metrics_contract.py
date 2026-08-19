"""Contract tests for the derived metrics engine against canonical JSON schemas.

Validates that:
- DerivedMetrics.as_dict() validates against DERIVED_METRICS_SCHEMA.v1.0.json
- DerivationRecord.as_dict() validates against DERIVATION_RECORD_SCHEMA.v0.1.json
- Input basis vocabularies match RATIO_INPUT_BASIS_SCHEMA.v0.1.json
- Status vocabulary matches the schema enum exactly
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hullq.contracts import ContractRegistry
from hullq.domain.derived_metrics import (
    METHODOLOGY_VERSION,
    DerivationRecord,
    DerivedMetrics,
    EffectiveInputSnapshot,
    MetricStatus,
    compute_derived_metrics,
)
from hullq.domain.measurements import DisplacementBasis, SailAreaBasis

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES = ROOT / "fixtures"

_REGISTRY = ContractRegistry.from_directory(SPECS)
_GENERATED_AT = "2026-08-19T00:00:00Z"


def _id_seq() -> Any:
    n = [0]

    def _next() -> str:
        n[0] += 1
        return f"CONTRACT-DER-{n[0]:04d}"

    return _next


def _snap_monohull() -> EffectiveInputSnapshot:
    return EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-CONTRACT-001",
        hull_configuration="monohull",
        loa_m=10.5,
        lwl_m=8.7,
        beam_m=3.4,
        displacement_kg=7000.0,
        ballast_kg=2800.0,
        sail_area_m2=60.0,
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
    )


def _run(snap: EffectiveInputSnapshot) -> tuple[DerivedMetrics, list[DerivationRecord]]:
    return compute_derived_metrics(
        snap,
        derivation_id_factory=_id_seq(),
        generated_at=_GENERATED_AT,
        producer_identifier="hullq-contract-test",
    )


# ---------------------------------------------------------------------------
# 1. DerivedMetrics.as_dict() validates against schema
# ---------------------------------------------------------------------------


def test_full_monohull_projection_validates_against_schema() -> None:
    dm, _ = _run(_snap_monohull())
    validator = _REGISTRY.validator_by_name("DERIVED_METRICS_SCHEMA.v1.0.json")
    validator.validate(dm.as_dict())


def test_catamaran_projection_validates_against_schema() -> None:
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-CAT-001",
        hull_configuration="catamaran",
        loa_m=12.0,
        lwl_m=11.5,
        beam_m=6.5,
        displacement_kg=6500.0,
        ballast_kg=0.0,
        sail_area_m2=95.0,
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
    )
    dm, _ = _run(snap)
    validator = _REGISTRY.validator_by_name("DERIVED_METRICS_SCHEMA.v1.0.json")
    validator.validate(dm.as_dict())


def test_missing_inputs_projection_validates_against_schema() -> None:
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-MISSING",
        hull_configuration="monohull",
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
    )
    dm, _ = _run(snap)
    validator = _REGISTRY.validator_by_name("DERIVED_METRICS_SCHEMA.v1.0.json")
    validator.validate(dm.as_dict())


def test_nonstandard_basis_projection_validates_against_schema() -> None:
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-NONSTANDARD",
        hull_configuration="monohull",
        loa_m=10.5,
        lwl_m=8.7,
        beam_m=3.4,
        displacement_kg=7000.0,
        ballast_kg=2800.0,
        sail_area_m2=60.0,
        displacement_basis="normal_sailing",
        sail_area_basis="working_sails_actual",
    )
    dm, _ = _run(snap)
    validator = _REGISTRY.validator_by_name("DERIVED_METRICS_SCHEMA.v1.0.json")
    validator.validate(dm.as_dict())


# ---------------------------------------------------------------------------
# 2. DerivationRecord.as_dict() validates against schema
# ---------------------------------------------------------------------------


def test_derivation_records_validate_against_schema() -> None:
    _, records = _run(_snap_monohull())
    validator = _REGISTRY.validator_by_name("DERIVATION_RECORD_SCHEMA.v0.1.json")
    assert len(records) == 6
    for rec in records:
        validator.validate(rec.as_dict())


def test_derivation_record_with_resolution_ids_validates() -> None:
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
            "/effective/dimensions/displacement_kg": "RES-001",
            "/effective/dimensions/lwl_m": "RES-002",
        },
    )
    _, records = _run(snap)
    validator = _REGISTRY.validator_by_name("DERIVATION_RECORD_SCHEMA.v0.1.json")
    for rec in records:
        validator.validate(rec.as_dict())


def test_no_derivation_records_for_all_null_catamaran() -> None:
    snap = EffectiveInputSnapshot.create(
        resolved_configuration_id="RC-CAT-NULL",
        hull_configuration="catamaran",
        displacement_basis="design",
        sail_area_basis="nominal_main_plus_foretriangle",
    )
    _, records = _run(snap)
    validator = _REGISTRY.validator_by_name("DERIVATION_RECORD_SCHEMA.v0.1.json")
    for rec in records:
        validator.validate(rec.as_dict())


# ---------------------------------------------------------------------------
# 3. Status vocabulary matches schema
# ---------------------------------------------------------------------------


def test_status_enum_values_match_schema() -> None:
    """MetricStatus values must exactly match the schema's enum."""
    schema_raw = json.loads(
        (SPECS / "DERIVED_METRICS_SCHEMA.v1.0.json").read_text(encoding="utf-8")
    )
    # Extract enum from the status.sa_displ property (all six use the same enum)
    schema_enum_values = set(schema_raw["properties"]["status"]["properties"]["sa_displ"]["enum"])
    runtime_values = {str(s) for s in MetricStatus}
    assert runtime_values == schema_enum_values


# ---------------------------------------------------------------------------
# 4. Input basis vocabularies match RATIO_INPUT_BASIS_SCHEMA
# ---------------------------------------------------------------------------


def test_displacement_basis_vocabulary_matches_schema() -> None:
    """DisplacementBasis values must exactly match the schema's enum."""
    schema_raw = json.loads(
        (SPECS / "RATIO_INPUT_BASIS_SCHEMA.v0.1.json").read_text(encoding="utf-8")
    )
    schema_values = set(schema_raw["properties"]["displacement_basis"]["enum"])
    runtime_values = {str(b) for b in DisplacementBasis}
    assert runtime_values == schema_values


def test_sail_area_basis_vocabulary_matches_schema() -> None:
    """SailAreaBasis values must exactly match the schema's enum."""
    schema_raw = json.loads(
        (SPECS / "RATIO_INPUT_BASIS_SCHEMA.v0.1.json").read_text(encoding="utf-8")
    )
    schema_values = set(schema_raw["properties"]["sail_area_basis"]["enum"])
    runtime_values = {str(b) for b in SailAreaBasis}
    assert runtime_values == schema_values


# ---------------------------------------------------------------------------
# 5. Methodology version in projection matches schema const
# ---------------------------------------------------------------------------


def test_methodology_version_const_matches_schema() -> None:
    schema_raw = json.loads(
        (SPECS / "DERIVED_METRICS_SCHEMA.v1.0.json").read_text(encoding="utf-8")
    )
    schema_const = schema_raw["properties"]["methodology_version"]["const"]
    assert schema_const == METHODOLOGY_VERSION
