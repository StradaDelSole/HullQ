"""Contract tests for SLICE-0006 provenance schema deliverables.

Verifies:
- PROVENANCE_SUBJECT_SCHEMA.v0.1 loads and validates correctly
- FIELD_EVIDENCE_SCHEMA.v0.2 loads, references the shared subject schema, and accepts
  all expanded subject kinds including those added by SLICE-0005
- FIELD_RESOLUTION_SCHEMA.v0.2 loads, references the shared subject schema
- v0.1 schemas remain loadable and unchanged (legacy compatibility)
- v0.2 fixtures validate against their respective schemas
- The shared subject schema is a single definition used by both v0.2 schemas (not copied)
"""

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


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Scenario 6 & 7 — v0.1 schemas remain loadable as historical schemas
# ---------------------------------------------------------------------------


def test_field_evidence_v01_schema_still_loadable() -> None:
    validator = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.1.json")
    assert validator is not None


def test_field_resolution_v01_schema_still_loadable() -> None:
    validator = _REGISTRY.validator_by_name("FIELD_RESOLUTION_SCHEMA.v0.1.json")
    assert validator is not None


def test_field_evidence_v01_accepts_existing_fixtures() -> None:
    fixture = _load(FIXTURES / "provenance" / "valid" / "evidence_imperial_to_si.json")
    _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.1.json").validate(fixture)


def test_field_resolution_v01_accepts_existing_fixtures() -> None:
    fixture = _load(FIXTURES / "provenance" / "valid" / "resolution_agreement.json")
    _REGISTRY.validator_by_name("FIELD_RESOLUTION_SCHEMA.v0.1.json").validate(fixture)


# ---------------------------------------------------------------------------
# Shared provenance subject schema
# ---------------------------------------------------------------------------


def test_provenance_subject_schema_loads() -> None:
    assert "PROVENANCE_SUBJECT_SCHEMA.v0.1.json" in _REGISTRY.schema_names


def test_provenance_subject_schema_rejects_unknown_kind() -> None:
    invalid_subject = {"kind": "resolved_configuration", "id": "RC_001"}
    with pytest.raises(ValidationError):
        _REGISTRY.validator_by_name("PROVENANCE_SUBJECT_SCHEMA.v0.1.json").validate(invalid_subject)


@pytest.mark.parametrize(
    "kind",
    [
        "boat_model",
        "boat_design",
        "named_variant",
        "design_option",
        "brand",
        "organization",
        "identity_alias",
        "brand_model_relationship",
        "organization_design_relationship",
    ],
)
def test_provenance_subject_schema_accepts_all_supported_kinds(kind: str) -> None:
    subject = {"kind": kind, "id": "TEST_001"}
    _REGISTRY.validator_by_name("PROVENANCE_SUBJECT_SCHEMA.v0.1.json").validate(subject)


# ---------------------------------------------------------------------------
# Scenario 8 — v0.2 schemas use the shared subject definition (not copies)
# ---------------------------------------------------------------------------


def test_field_evidence_v02_references_shared_provenance_subject() -> None:
    schema = _REGISTRY._by_name["FIELD_EVIDENCE_SCHEMA.v0.2.json"]
    subject_prop = schema["properties"]["subject"]  # type: ignore[index]
    assert "$ref" in subject_prop, (
        "FIELD_EVIDENCE_SCHEMA.v0.2 subject must use $ref to the shared "
        "provenance-subject schema, not an inline enum copy"
    )
    assert subject_prop["$ref"] == "https://hullq.local/schemas/provenance-subject/0.1"


def test_field_resolution_v02_references_shared_provenance_subject() -> None:
    schema = _REGISTRY._by_name["FIELD_RESOLUTION_SCHEMA.v0.2.json"]
    subject_prop = schema["properties"]["subject"]  # type: ignore[index]
    assert "$ref" in subject_prop, (
        "FIELD_RESOLUTION_SCHEMA.v0.2 subject must use $ref to the shared "
        "provenance-subject schema, not an inline enum copy"
    )
    assert subject_prop["$ref"] == "https://hullq.local/schemas/provenance-subject/0.1"


# ---------------------------------------------------------------------------
# v0.2 field-evidence fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "evidence_v02_brand.json",
        "evidence_v02_organization.json",
        "evidence_v02_identity_alias.json",
        "evidence_v02_brand_model_rel.json",
        "evidence_v02_org_design_rel.json",
        "evidence_v02_null_candidate.json",
    ],
)
def test_valid_v02_evidence_fixtures(fixture_name: str) -> None:
    fixture = _load(FIXTURES / "provenance" / "valid" / "v0.2" / fixture_name)
    _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.2.json").validate(fixture)


# ---------------------------------------------------------------------------
# v0.2 field-resolution fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "resolution_v02_brand.json",
        "resolution_v02_org_design_rel.json",
    ],
)
def test_valid_v02_resolution_fixtures(fixture_name: str) -> None:
    fixture = _load(FIXTURES / "provenance" / "valid" / "v0.2" / fixture_name)
    _REGISTRY.validator_by_name("FIELD_RESOLUTION_SCHEMA.v0.2.json").validate(fixture)


# ---------------------------------------------------------------------------
# Scenario 6 — v0.2 accepts expanded subject kinds that v0.1 rejects
# ---------------------------------------------------------------------------


def _make_evidence_v02(kind: str, evidence_id: str = "EVID_TEST") -> dict[str, object]:
    return {
        "schema_version": "0.2",
        "evidence_id": evidence_id,
        "subject": {"kind": kind, "id": "TEST_001"},
        "field_pointer": "/canonical_name",
        "source_id": "SRC_001",
        "source_locator": {
            "page": None,
            "section": None,
            "anchor": None,
            "table": None,
            "figure": None,
            "record_key": None,
        },
        "observation": {"raw": {"kind": "literal", "value": "test", "unit": None, "excerpt": None}},
        "evidence_type": "structured_dataset",
        "producer": {
            "kind": "human",
            "identifier": "tester",
            "version": None,
            "model": None,
            "prompt_or_rule_version": None,
        },
        "research_context": {"research_job_id": None, "activity_id": None},
        "observed_at": "2026-08-18T00:00:00Z",
        "confidence": "high",
        "supersedes_evidence_id": None,
        "notes": None,
    }


@pytest.mark.parametrize(
    "kind",
    [
        "brand",
        "organization",
        "identity_alias",
        "brand_model_relationship",
        "organization_design_relationship",
    ],
)
def test_v02_evidence_accepts_slice0005_subject_kinds(kind: str) -> None:
    data = _make_evidence_v02(kind)
    _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.2.json").validate(data)


@pytest.mark.parametrize(
    "kind",
    [
        "brand",
        "organization",
        "identity_alias",
        "brand_model_relationship",
        "organization_design_relationship",
    ],
)
def test_v01_evidence_rejects_slice0005_subject_kinds(kind: str) -> None:
    data = _make_evidence_v02(kind)
    data["schema_version"] = "0.1"
    with pytest.raises(ValidationError):
        _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.1.json").validate(data)


# ---------------------------------------------------------------------------
# v0.2 normalized_candidate is optional
# ---------------------------------------------------------------------------


def test_v02_evidence_accepts_missing_normalized_candidate() -> None:
    data = _make_evidence_v02("boat_design")
    assert "normalized_candidate" not in data["observation"]  # type: ignore[operator]
    _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.2.json").validate(data)


def test_v02_evidence_accepts_null_normalized_candidate() -> None:
    data = _make_evidence_v02("boat_design")
    data["observation"]["normalized_candidate"] = None  # type: ignore[index]
    _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.2.json").validate(data)


def test_v01_evidence_rejects_missing_normalized_candidate() -> None:
    data = _make_evidence_v02("boat_design")
    data["schema_version"] = "0.1"
    with pytest.raises(ValidationError):
        _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.1.json").validate(data)
