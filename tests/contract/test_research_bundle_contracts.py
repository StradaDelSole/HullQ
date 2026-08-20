"""Contract tests for SLICE-0012 JSON Schema deliverables.

Verifies:
- CLAIM_SEMANTICS_SCHEMA.v0.1 loads and vocabulary matches runtime
- OBSERVATION_APPLICABILITY_SCHEMA.v0.1 loads and validates correctly
- RESEARCH_OBSERVATION_SCHEMA.v0.1 loads, uses $ref to claim/applicability, accepts fixtures
- FIELD_EVIDENCE_SCHEMA.v0.3 loads, uses $ref to subject/claim/applicability, accepts fixtures
- RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1 loads and accepts valid/invalid bundle fixtures
- v0.2 and earlier schemas remain unmodified (backward compatibility)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from hullq.contracts import ContractRegistry
from hullq.domain.provenance import ClaimSemantics
from hullq.research.observations import ReferenceCheckOutcome

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES = ROOT / "fixtures"

_REGISTRY = ContractRegistry.from_directory(SPECS)


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Shared fixture builders
# ---------------------------------------------------------------------------


def _applicability_json(
    *,
    first_year: int | None = None,
    last_year: int | None = None,
    unknown_or_unbounded: bool = True,
    individual_hull_or_listing_ref: object = None,
    design_option_hints: object = None,
) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "first_year": first_year,
        "last_year": last_year,
        "hull_number_from": None,
        "hull_number_to": None,
        "market_or_region": None,
        "named_variant_hint": None,
        "design_option_hints": design_option_hints,
        "operating_state_hint": None,
        "individual_hull_or_listing_ref": individual_hull_or_listing_ref,
        "unknown_or_unbounded": unknown_or_unbounded,
    }


def _research_observation_json(
    *,
    observation_id: str = "OBS-001",
    model: str = "Test 35",
    claim_semantics: str = "unknown",
    intended_subject_kind_hint: object = None,
    intended_field_pointer: object = None,
    applicability: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "observation_id": observation_id,
        "research_target": {
            "manufacturer": "TestYachts",
            "model": model,
            "first_built": 1980,
        },
        "source_id": "SRC-TEST",
        "source_locator": {
            "page": None,
            "section": None,
            "anchor": None,
            "table": None,
            "figure": None,
            "record_key": None,
        },
        "observation": {
            "raw": {
                "kind": "literal",
                "value": "10.67",
                "unit": "m",
                "excerpt": None,
            },
            "normalized_candidate": None,
        },
        "evidence_type": "manufacturer_specification",
        "claim_semantics": claim_semantics,
        "applicability": applicability or _applicability_json(),
        "producer": {
            "kind": "llm",
            "identifier": "test-agent",
            "version": "0.1",
            "model": "test-model",
            "prompt_or_rule_version": None,
        },
        "research_context": {
            "research_job_id": "JOB-001",
            "activity_id": None,
        },
        "observed_at": "2026-08-20T00:00:00Z",
        "confidence": "high",
        "supersedes_observation_id": None,
        "intended_subject_kind_hint": intended_subject_kind_hint,
        "intended_field_pointer": intended_field_pointer,
        "notes": None,
    }


def _field_evidence_v3_json(
    *,
    evidence_id: str = "EVID-V3-001",
    claim_semantics: str = "nominal_design_value",
    applicability: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "0.3",
        "evidence_id": evidence_id,
        "subject": {"kind": "boat_design", "id": "BD-TEST"},
        "field_pointer": "/loa_m",
        "source_id": "SRC-TEST",
        "source_locator": {
            "page": None,
            "section": None,
            "anchor": None,
            "table": None,
            "figure": None,
            "record_key": None,
        },
        "observation": {
            "raw": {
                "kind": "literal",
                "value": "10.67",
                "unit": "m",
                "excerpt": None,
            },
            "normalized_candidate": {
                "value": 10.67,
                "unit": "m",
                "method_id": "hullq-norm-1.0",
                "method_version": "1.0",
            },
        },
        "evidence_type": "manufacturer_specification",
        "claim_semantics": claim_semantics,
        "applicability": applicability or _applicability_json(unknown_or_unbounded=True),
        "producer": {
            "kind": "llm",
            "identifier": "test-agent",
            "version": "0.1",
            "model": "test-model",
            "prompt_or_rule_version": None,
        },
        "research_context": {
            "research_job_id": "JOB-001",
            "activity_id": None,
        },
        "observed_at": "2026-08-20T00:00:00Z",
        "confidence": "high",
        "supersedes_evidence_id": None,
        "notes": None,
    }


# ---------------------------------------------------------------------------
# Claim semantics schema
# ---------------------------------------------------------------------------


def test_claim_semantics_schema_loads() -> None:
    assert "CLAIM_SEMANTICS_SCHEMA.v0.1.json" in _REGISTRY.schema_names


def test_claim_semantics_runtime_parity() -> None:
    validator = _REGISTRY.validator_by_name("CLAIM_SEMANTICS_SCHEMA.v0.1.json")
    for cs in ClaimSemantics:
        validator.validate(cs.value)


def test_claim_semantics_rejects_evidence_type_value() -> None:
    validator = _REGISTRY.validator_by_name("CLAIM_SEMANTICS_SCHEMA.v0.1.json")
    with pytest.raises(ValidationError):
        validator.validate("manufacturer_specification")


def test_claim_semantics_unknown_is_valid() -> None:
    validator = _REGISTRY.validator_by_name("CLAIM_SEMANTICS_SCHEMA.v0.1.json")
    validator.validate("unknown")


# ---------------------------------------------------------------------------
# Observation applicability schema
# ---------------------------------------------------------------------------


def test_observation_applicability_schema_loads() -> None:
    assert "OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json" in _REGISTRY.schema_names


def test_observation_applicability_accepts_all_null() -> None:
    v = _REGISTRY.validator_by_name("OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json")
    v.validate(_applicability_json())


def test_observation_applicability_accepts_year_bounded() -> None:
    v = _REGISTRY.validator_by_name("OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json")
    v.validate(_applicability_json(first_year=1979, last_year=1979, unknown_or_unbounded=False))


def test_observation_applicability_rejects_missing_schema_version() -> None:
    v = _REGISTRY.validator_by_name("OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json")
    bad = dict(_applicability_json())
    del bad["schema_version"]
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_observation_applicability_accepts_individual_hull_ref() -> None:
    v = _REGISTRY.validator_by_name("OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json")
    v.validate(
        _applicability_json(
            individual_hull_or_listing_ref="LISTING-001",
            unknown_or_unbounded=False,
        )
    )


def test_observation_applicability_accepts_design_option_hints() -> None:
    v = _REGISTRY.validator_by_name("OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json")
    v.validate(
        _applicability_json(
            design_option_hints=["shoal keel", "roller furling"],
            unknown_or_unbounded=False,
        )
    )


def test_observation_applicability_rejects_empty_design_option_hint_string() -> None:
    v = _REGISTRY.validator_by_name("OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json")
    with pytest.raises(ValidationError):
        v.validate(
            _applicability_json(
                design_option_hints=["shoal keel", ""],
                unknown_or_unbounded=False,
            )
        )


# ---------------------------------------------------------------------------
# Research observation schema
# ---------------------------------------------------------------------------


def test_research_observation_schema_loads() -> None:
    assert "RESEARCH_OBSERVATION_SCHEMA.v0.1.json" in _REGISTRY.schema_names


def test_research_observation_accepts_minimal_valid() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    v.validate(_research_observation_json())


def test_research_observation_accepts_with_subject_kind_hint() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    v.validate(
        _research_observation_json(
            intended_subject_kind_hint="boat_design",
            intended_field_pointer="/loa_m",
        )
    )


def test_research_observation_rejects_unknown_claim_semantics() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    bad = dict(_research_observation_json())
    bad["claim_semantics"] = "not_a_real_claim"
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_research_observation_rejects_unknown_intended_subject_kind() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    bad = dict(_research_observation_json())
    bad["intended_subject_kind_hint"] = "not_a_real_kind"
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_research_observation_accepts_null_intended_field_pointer() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    obs = _research_observation_json(intended_field_pointer=None)
    v.validate(obs)


def test_research_observation_rejects_pointer_without_leading_slash() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    bad = dict(_research_observation_json())
    bad["intended_field_pointer"] = "loa_m"
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_research_observation_accepts_all_claim_semantics_values() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json")
    for cs in ClaimSemantics:
        obs = _research_observation_json(claim_semantics=cs.value)
        v.validate(obs)


# ---------------------------------------------------------------------------
# FieldEvidence v0.3 schema
# ---------------------------------------------------------------------------


def test_field_evidence_v03_schema_loads() -> None:
    assert "FIELD_EVIDENCE_SCHEMA.v0.3.json" in _REGISTRY.schema_names


def test_field_evidence_v03_accepts_valid_fixture() -> None:
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.3.json")
    v.validate(_field_evidence_v3_json())


def test_field_evidence_v03_rejects_wrong_schema_version() -> None:
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.3.json")
    bad = dict(_field_evidence_v3_json())
    bad["schema_version"] = "0.2"
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_field_evidence_v03_rejects_missing_claim_semantics() -> None:
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.3.json")
    bad = dict(_field_evidence_v3_json())
    del bad["claim_semantics"]
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_field_evidence_v03_rejects_missing_applicability() -> None:
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.3.json")
    bad = dict(_field_evidence_v3_json())
    del bad["applicability"]
    with pytest.raises(ValidationError):
        v.validate(bad)


def test_field_evidence_v03_accepts_individual_hull_applicability() -> None:
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.3.json")
    app = _applicability_json(
        individual_hull_or_listing_ref="LISTING-2024-001",
        unknown_or_unbounded=False,
    )
    ev = _field_evidence_v3_json(
        claim_semantics="individual_hull_value",
        applicability=app,
    )
    v.validate(ev)


def test_field_evidence_v02_schema_still_valid() -> None:
    # v0.2 must remain unmodified and loadable
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.2.json")
    fixture = _load(FIXTURES / "provenance" / "valid" / "v0.2" / "evidence_v02_brand.json")
    v.validate(fixture)


def test_field_evidence_v02_schema_rejects_v03_schema_version() -> None:
    # v0.2 schema must not accept schema_version "0.3"
    v = _REGISTRY.validator_by_name("FIELD_EVIDENCE_SCHEMA.v0.2.json")
    bad = {**_load(FIXTURES / "provenance" / "valid" / "v0.2" / "evidence_v02_brand.json")}  # type: ignore[arg-type]
    bad["schema_version"] = "0.3"
    with pytest.raises(ValidationError):
        v.validate(bad)


# ---------------------------------------------------------------------------
# ResearchEvidenceBundle schema
# ---------------------------------------------------------------------------


def test_research_evidence_bundle_schema_loads() -> None:
    assert "RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json" in _REGISTRY.schema_names


def _bundle_json(
    *,
    observations: list[object] | None = None,
    promoted_evidence: list[object] | None = None,
    reference_crosschecks: list[object] | None = None,
    unresolved_findings: list[object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "bundle_id": "BUNDLE-001",
        "bundle_version": "1.0",
        "research_target": {
            "manufacturer": "TestYachts",
            "model": "Test 35",
            "first_built": 1980,
        },
        "research_job_id": "JOB-001",
        "activity_id": None,
        "observations": observations
        if observations is not None
        else [_research_observation_json()],
        "unresolved_findings": unresolved_findings or [],
        "promoted_evidence": promoted_evidence or [],
        "reference_crosschecks": reference_crosschecks or [],
    }


def test_bundle_accepts_minimal_valid() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    v.validate(_bundle_json(observations=[]))


def test_bundle_accepts_with_observation() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    v.validate(_bundle_json())


def test_bundle_accepts_with_promoted_evidence() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    v.validate(_bundle_json(promoted_evidence=[_field_evidence_v3_json()]))


def test_bundle_accepts_with_reference_crosscheck() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    cc: dict[str, object] = {
        "crosscheck_id": "CC-001",
        "reference_source_id": "sailboatdata-reference",
        "topic_or_field": "/loa_m",
        "outcome": "conflict",
        "notes": "Reference shows different value",
    }
    v.validate(_bundle_json(reference_crosschecks=[cc]))


def test_bundle_accepts_null_manufacturer_in_target() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    bundle = _bundle_json(observations=[])
    bundle["research_target"] = {  # type: ignore[index]
        "manufacturer": None,
        "model": "Unknown Design",
        "first_built": None,
    }
    v.validate(bundle)


def test_bundle_rejects_invalid_crosscheck_outcome() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    cc: dict[str, object] = {
        "crosscheck_id": "CC-BAD",
        "reference_source_id": "sailboatdata-reference",
        "topic_or_field": None,
        "outcome": "not_a_real_outcome",
        "notes": None,
    }
    with pytest.raises(ValidationError):
        v.validate(_bundle_json(reference_crosschecks=[cc]))


def test_reference_check_outcome_vocabulary_matches_bundle_schema() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    for outcome in ReferenceCheckOutcome:
        cc: dict[str, object] = {
            "crosscheck_id": "CC-VOCAB",
            "reference_source_id": "sailboatdata-reference",
            "topic_or_field": None,
            "outcome": outcome.value,
            "notes": None,
        }
        v.validate(_bundle_json(reference_crosschecks=[cc]))


def test_bundle_unresolved_finding_valid() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    finding: dict[str, object] = {
        "finding_id": "FIND-001",
        "topic": "manufacturer_identity",
        "description": "Manufacturer cannot be resolved to canonical Brand",
        "related_observation_ids": ["OBS-001"],
        "severity": "review",
    }
    v.validate(_bundle_json(unresolved_findings=[finding]))


def test_bundle_rejects_invalid_finding_severity() -> None:
    v = _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json")
    finding: dict[str, object] = {
        "finding_id": "FIND-BAD",
        "topic": "x",
        "description": "y",
        "related_observation_ids": [],
        "severity": "critical",
    }
    with pytest.raises(ValidationError):
        v.validate(_bundle_json(unresolved_findings=[finding]))


# ---------------------------------------------------------------------------
# Backward compatibility — v0.1/v0.2 schemas remain loadable
# ---------------------------------------------------------------------------


def test_existing_v02_field_evidence_schemas_still_loadable() -> None:
    assert "FIELD_EVIDENCE_SCHEMA.v0.1.json" in _REGISTRY.schema_names
    assert "FIELD_EVIDENCE_SCHEMA.v0.2.json" in _REGISTRY.schema_names


def test_existing_v02_field_resolution_schema_still_loadable() -> None:
    assert "FIELD_RESOLUTION_SCHEMA.v0.2.json" in _REGISTRY.schema_names


def test_existing_research_job_schema_still_loadable() -> None:
    assert "RESEARCH_JOB_SCHEMA.v0.1.json" in _REGISTRY.schema_names
