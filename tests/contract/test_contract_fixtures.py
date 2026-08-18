from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES = ROOT / "fixtures"

_REGISTRY = ContractRegistry.from_directory(SPECS)


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_identity_current_contract_fixture() -> None:
    fixture = load(FIXTURES / "identity" / "identity_contract_examples.v0.2.json")
    assert isinstance(fixture, dict)
    _REGISTRY.validator_by_name("BOAT_MODEL_SCHEMA.v0.1.json").validate(fixture["boat_model"])
    _REGISTRY.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json").validate(fixture["boat_design"])
    _REGISTRY.validator_by_name("RESOLVED_CONFIGURATION_SCHEMA.v0.2.json").validate(
        fixture["resolved_configuration"]
    )


def test_ratio_schema_contract_fixture() -> None:
    fixture = load(FIXTURES / "ratios" / "schema_contract_example.v0.1.json")
    assert isinstance(fixture, dict)
    _REGISTRY.validator_by_name("BOAT_MODEL_SCHEMA.v0.1.json").validate(fixture["boat_model"])
    _REGISTRY.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json").validate(fixture["boat_design"])
    _REGISTRY.validator_by_name("RESOLVED_CONFIGURATION_SCHEMA.v0.2.json").validate(
        fixture["resolved_configuration"]
    )


def test_source_rights_fixtures() -> None:
    fixture = load(FIXTURES / "sources" / "source_rights_cases.v0.1.json")
    assert isinstance(fixture, dict)
    for case in fixture["cases"]:
        _REGISTRY.validator_by_name("SOURCE_SCHEMA.v0.2.json").validate(case["source"])


@pytest.mark.parametrize(
    ("directory", "schema_name"),
    [
        ("evidence", "FIELD_EVIDENCE_SCHEMA.v0.1.json"),
        ("resolution", "FIELD_RESOLUTION_SCHEMA.v0.1.json"),
        ("derivation", "DERIVATION_RECORD_SCHEMA.v0.1.json"),
    ],
)
def test_valid_provenance_fixtures(directory: str, schema_name: str) -> None:
    matching = sorted((FIXTURES / "provenance" / "valid").glob(f"{directory}_*.json"))
    assert matching
    for path in matching:
        _REGISTRY.validator_by_name(schema_name).validate(load(path))


@pytest.mark.parametrize(
    ("file_name", "schema_name"),
    [
        ("evidence_dot_path.json", "FIELD_EVIDENCE_SCHEMA.v0.1.json"),
        ("evidence_missing_source.json", "FIELD_EVIDENCE_SCHEMA.v0.1.json"),
        ("resolution_conflict_with_value.json", "FIELD_RESOLUTION_SCHEMA.v0.1.json"),
        (
            "resolution_resolved_conflict_without_contradiction.json",
            "FIELD_RESOLUTION_SCHEMA.v0.1.json",
        ),
        ("resolution_resolved_without_support.json", "FIELD_RESOLUTION_SCHEMA.v0.1.json"),
        ("derivation_no_inputs.json", "DERIVATION_RECORD_SCHEMA.v0.1.json"),
    ],
)
def test_invalid_provenance_fixtures_are_rejected(file_name: str, schema_name: str) -> None:
    with pytest.raises(ValidationError):
        _REGISTRY.validator_by_name(schema_name).validate(
            load(FIXTURES / "provenance" / "invalid" / file_name)
        )
