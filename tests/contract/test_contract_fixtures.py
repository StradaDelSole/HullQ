from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES = ROOT / "fixtures"


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def schemas() -> tuple[dict[str, dict[str, object]], Registry]:
    by_name: dict[str, dict[str, object]] = {}
    registry = Registry()
    for path in sorted(SPECS.glob("*_SCHEMA*.json")):
        schema = load(path)
        assert isinstance(schema, dict)
        Draft202012Validator.check_schema(schema)
        by_name[path.name] = schema
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return by_name, registry


def validator(name: str) -> Draft202012Validator:
    by_name, registry = schemas()
    return Draft202012Validator(by_name[name], registry=registry)


def test_identity_current_contract_fixture() -> None:
    fixture = load(FIXTURES / "identity" / "identity_contract_examples.v0.2.json")
    assert isinstance(fixture, dict)
    validator("BOAT_MODEL_SCHEMA.v0.1.json").validate(fixture["boat_model"])
    validator("BOAT_DESIGN_SCHEMA.v0.4.json").validate(fixture["boat_design"])
    validator("RESOLVED_CONFIGURATION_SCHEMA.v0.2.json").validate(fixture["resolved_configuration"])


def test_ratio_schema_contract_fixture() -> None:
    fixture = load(FIXTURES / "ratios" / "schema_contract_example.v0.1.json")
    assert isinstance(fixture, dict)
    validator("BOAT_MODEL_SCHEMA.v0.1.json").validate(fixture["boat_model"])
    validator("BOAT_DESIGN_SCHEMA.v0.4.json").validate(fixture["boat_design"])
    validator("RESOLVED_CONFIGURATION_SCHEMA.v0.2.json").validate(fixture["resolved_configuration"])


def test_source_rights_fixtures() -> None:
    fixture = load(FIXTURES / "sources" / "source_rights_cases.v0.1.json")
    assert isinstance(fixture, dict)
    for case in fixture["cases"]:
        validator("SOURCE_SCHEMA.v0.2.json").validate(case["source"])


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
        validator(schema_name).validate(load(path))


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
        validator(schema_name).validate(load(FIXTURES / "provenance" / "invalid" / file_name))
