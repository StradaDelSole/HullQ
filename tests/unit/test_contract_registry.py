"""Unit tests for hullq.contracts.ContractRegistry.

Required coverage (per SLICE-0003):
  1. repository schemas load deterministically from specs/
  2. every discovered schema passes Draft 2020-12 meta-schema validation
  3. accepted fixtures validate through the runtime (identity, ratio, provenance)
  4. existing invalid provenance fixtures remain rejected
  5. unknown schema-name lookup fails explicitly
  6. duplicate $id registration fails explicitly
  7. malformed JSON / non-object schema input fails explicitly
  8. synthetic local cross-schema $ref resolves without network access
  9. missing referenced local resource fails without HTTP retrieval
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from referencing.exceptions import Unresolvable

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES = ROOT / "fixtures"


# ---------------------------------------------------------------------------
# 1 & 2: repository schemas load and are Draft 2020-12 valid
# ---------------------------------------------------------------------------


def test_repository_schemas_load_from_specs() -> None:
    registry = ContractRegistry.from_directory(SPECS)
    assert registry.schema_names, "Expected at least one schema in specs/"


def test_all_loaded_schemas_are_deterministic() -> None:
    r1 = ContractRegistry.from_directory(SPECS)
    r2 = ContractRegistry.from_directory(SPECS)
    assert r1.schema_names == r2.schema_names


def test_all_repository_schemas_pass_draft_2020_12() -> None:
    # from_directory calls Draft202012Validator.check_schema internally;
    # if any schema fails meta-validation, from_directory raises.
    ContractRegistry.from_directory(SPECS)


# ---------------------------------------------------------------------------
# 3: accepted fixtures validate through the runtime
# ---------------------------------------------------------------------------


def _registry() -> ContractRegistry:
    return ContractRegistry.from_directory(SPECS)


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_identity_fixture_validates_via_runtime() -> None:
    reg = _registry()
    fixture = _load(FIXTURES / "identity" / "identity_contract_examples.v0.2.json")
    assert isinstance(fixture, dict)
    reg.validator_by_name("BOAT_MODEL_SCHEMA.v0.1.json").validate(fixture["boat_model"])
    reg.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json").validate(fixture["boat_design"])
    reg.validator_by_name("RESOLVED_CONFIGURATION_SCHEMA.v0.2.json").validate(
        fixture["resolved_configuration"]
    )


def test_ratio_fixture_validates_via_runtime() -> None:
    reg = _registry()
    fixture = _load(FIXTURES / "ratios" / "schema_contract_example.v0.1.json")
    assert isinstance(fixture, dict)
    reg.validator_by_name("BOAT_MODEL_SCHEMA.v0.1.json").validate(fixture["boat_model"])
    reg.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json").validate(fixture["boat_design"])
    reg.validator_by_name("RESOLVED_CONFIGURATION_SCHEMA.v0.2.json").validate(
        fixture["resolved_configuration"]
    )


def test_source_rights_fixture_validates_via_runtime() -> None:
    reg = _registry()
    fixture = _load(FIXTURES / "sources" / "source_rights_cases.v0.1.json")
    assert isinstance(fixture, dict)
    for case in fixture["cases"]:
        reg.validator_by_name("SOURCE_SCHEMA.v0.2.json").validate(case["source"])


@pytest.mark.parametrize(
    ("directory", "schema_name"),
    [
        ("evidence", "FIELD_EVIDENCE_SCHEMA.v0.1.json"),
        ("resolution", "FIELD_RESOLUTION_SCHEMA.v0.1.json"),
        ("derivation", "DERIVATION_RECORD_SCHEMA.v0.1.json"),
    ],
)
def test_valid_provenance_fixtures_via_runtime(directory: str, schema_name: str) -> None:
    reg = _registry()
    matching = sorted((FIXTURES / "provenance" / "valid").glob(f"{directory}_*.json"))
    assert matching
    for path in matching:
        reg.validator_by_name(schema_name).validate(_load(path))


# ---------------------------------------------------------------------------
# 4: invalid provenance fixtures remain rejected
# ---------------------------------------------------------------------------


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
def test_invalid_provenance_fixtures_rejected_via_runtime(file_name: str, schema_name: str) -> None:
    reg = _registry()
    with pytest.raises(ValidationError):
        reg.validator_by_name(schema_name).validate(
            _load(FIXTURES / "provenance" / "invalid" / file_name)
        )


# ---------------------------------------------------------------------------
# 5: unknown schema lookup fails explicitly
# ---------------------------------------------------------------------------


def test_unknown_schema_name_raises_key_error() -> None:
    reg = ContractRegistry.from_directory(SPECS)
    with pytest.raises(KeyError, match=r"NONEXISTENT_SCHEMA\.json"):
        reg.validator_by_name("NONEXISTENT_SCHEMA.json")


# ---------------------------------------------------------------------------
# 6: duplicate $id registration fails explicitly (synthetic schemas)
# ---------------------------------------------------------------------------


def test_duplicate_schema_id_raises_value_error(tmp_path: Path) -> None:
    schema_a = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://hullq.local/test/duplicate",
        "type": "object",
    }
    schema_b = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://hullq.local/test/duplicate",
        "type": "string",
    }
    (tmp_path / "A_SCHEMA_a.json").write_text(json.dumps(schema_a), encoding="utf-8")
    (tmp_path / "A_SCHEMA_b.json").write_text(json.dumps(schema_b), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate schema"):
        ContractRegistry.from_directory(tmp_path)


# ---------------------------------------------------------------------------
# 7: malformed JSON and non-object schema root fail explicitly
# ---------------------------------------------------------------------------


def test_malformed_json_raises_value_error(tmp_path: Path) -> None:
    (tmp_path / "BAD_SCHEMA.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        ContractRegistry.from_directory(tmp_path)


def test_non_object_schema_raises_type_error(tmp_path: Path) -> None:
    (tmp_path / "ARRAY_SCHEMA.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(TypeError, match="JSON object"):
        ContractRegistry.from_directory(tmp_path)


# ---------------------------------------------------------------------------
# 8: synthetic cross-schema $ref resolves from in-memory registry
# ---------------------------------------------------------------------------


def test_local_ref_resolves_without_network(tmp_path: Path) -> None:
    target_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://hullq.local/test/target",
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    }
    referencing_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://hullq.local/test/referencing",
        "type": "object",
        "properties": {
            "nested": {"$ref": "https://hullq.local/test/target"},
        },
        "required": ["nested"],
    }
    (tmp_path / "TARGET_SCHEMA.json").write_text(json.dumps(target_schema), encoding="utf-8")
    (tmp_path / "REFERENCING_SCHEMA.json").write_text(
        json.dumps(referencing_schema), encoding="utf-8"
    )

    reg = ContractRegistry.from_directory(tmp_path)
    # valid instance: nested matches the target schema
    reg.validator_by_name("REFERENCING_SCHEMA.json").validate({"nested": {"value": 42}})
    # invalid instance: nested does not match the target schema
    with pytest.raises(ValidationError):
        reg.validator_by_name("REFERENCING_SCHEMA.json").validate({"nested": {"value": "x"}})


# ---------------------------------------------------------------------------
# 9: missing referenced local resource fails without HTTP retrieval
# ---------------------------------------------------------------------------


def test_missing_local_ref_fails_not_http_fetch(tmp_path: Path) -> None:
    schema_with_dangling_ref = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://hullq.local/test/dangling",
        "type": "object",
        "properties": {
            "x": {"$ref": "https://hullq.local/test/does-not-exist"},
        },
        "required": ["x"],
    }
    (tmp_path / "DANGLING_SCHEMA.json").write_text(
        json.dumps(schema_with_dangling_ref), encoding="utf-8"
    )

    reg = ContractRegistry.from_directory(tmp_path)
    # The $ref points to a resource not present in the registry.
    # validation must raise Unresolvable (or a jsonschema wrapper of it)
    # rather than attempting an HTTP fetch.
    with pytest.raises(Unresolvable):
        reg.validator_by_name("DANGLING_SCHEMA.json").validate({"x": 1})
