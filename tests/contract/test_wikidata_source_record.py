"""Contract test for the reviewed Wikidata Source record — SLICE-0008.

Covers required test scenario 1:
  1. reviewed Wikidata Source record validates against SOURCE_SCHEMA.v0.2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from hullq.contracts.registry import ContractRegistry
from hullq.sources.rights import (
    DecisionOutcome,
    SourceUse,
    check_source_use,
)
from hullq.sources.wikidata import WIKIDATA_SOURCE_ID

ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "specs"
WIKIDATA_FIXTURE = ROOT / "fixtures" / "sources" / "wikidata_source.json"


def _load_wikidata_source() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(WIKIDATA_FIXTURE.read_text(encoding="utf-8")))


def _make_registry() -> ContractRegistry:
    return ContractRegistry.from_directory(SPECS_DIR)


# ---------------------------------------------------------------------------
# Scenario 1 — source record validates against SOURCE_SCHEMA.v0.2
# ---------------------------------------------------------------------------


def test_wikidata_source_record_exists() -> None:
    assert WIKIDATA_FIXTURE.exists(), f"Missing fixture: {WIKIDATA_FIXTURE}"


def test_wikidata_source_record_is_valid_json() -> None:
    source = _load_wikidata_source()
    assert isinstance(source, dict)


def test_wikidata_source_record_validates_against_schema() -> None:
    registry = _make_registry()
    source = _load_wikidata_source()
    validator = registry.validator_by_name("SOURCE_SCHEMA.v0.2.json")
    errors = list(validator.iter_errors(source))
    assert errors == [], f"Schema validation errors: {[str(e) for e in errors]}"


def test_wikidata_source_record_has_correct_source_id() -> None:
    source = _load_wikidata_source()
    assert source["source_id"] == WIKIDATA_SOURCE_ID


def test_wikidata_source_record_is_assessed() -> None:
    source = _load_wikidata_source()
    assert source["rights"]["assessment_status"] == "assessed"


def test_wikidata_source_record_automated_access_is_allowed() -> None:
    source = _load_wikidata_source()
    assert source["rights"]["access"]["automated_access"] == "allowed"


def test_wikidata_source_record_automated_ingestion_clearance_is_allowed() -> None:
    source = _load_wikidata_source()
    assert source["rights"]["clearance"]["automated_ingestion"] == "allowed"


def test_wikidata_source_record_is_cc0() -> None:
    source = _load_wikidata_source()
    assert source["rights"]["license_expression"] == "CC0-1.0"


def test_wikidata_source_record_no_share_alike() -> None:
    source = _load_wikidata_source()
    assert source["rights"]["obligations"]["share_alike"] == "no"


def test_wikidata_source_record_has_rights_evidence() -> None:
    source = _load_wikidata_source()
    evidence = source["rights"]["rights_evidence"]
    assert isinstance(evidence, list)
    assert len(evidence) >= 1


def test_wikidata_source_record_has_review_date() -> None:
    source = _load_wikidata_source()
    review = source["rights"]["review"]
    assert isinstance(review["reviewed_at"], str)
    assert len(review["reviewed_at"]) > 0


# ---------------------------------------------------------------------------
# Rights-gate behaviour on the reviewed source record
# ---------------------------------------------------------------------------


def test_wikidata_rights_gate_automated_ingestion_allows() -> None:
    """The reviewed source record must pass the SLICE-0007 gate for automated ingestion."""
    source = _load_wikidata_source()
    decision = check_source_use(source, SourceUse.AUTOMATED_INGESTION)
    assert decision.outcome == DecisionOutcome.ALLOWED, (
        f"Expected ALLOWED; got {decision.outcome} with reasons {decision.reasons}"
    )


def test_wikidata_rights_gate_bulk_bootstrap_allows() -> None:
    source = _load_wikidata_source()
    decision = check_source_use(source, SourceUse.BULK_BOOTSTRAP)
    assert decision.outcome == DecisionOutcome.ALLOWED


def test_wikidata_rights_gate_production_value_allows() -> None:
    source = _load_wikidata_source()
    decision = check_source_use(source, SourceUse.PRODUCTION_VALUE)
    assert decision.outcome == DecisionOutcome.ALLOWED


def test_wikidata_rights_gate_research_reference_allows() -> None:
    source = _load_wikidata_source()
    decision = check_source_use(source, SourceUse.RESEARCH_REFERENCE)
    assert decision.outcome == DecisionOutcome.ALLOWED


def test_wikidata_source_record_does_not_weaken_existing_cc0_fixture() -> None:
    """The Wikidata record is a separate file; it must not modify source_rights_cases.v0.1.json."""
    existing_fixture = ROOT / "fixtures" / "sources" / "source_rights_cases.v0.1.json"
    existing_data = json.loads(existing_fixture.read_text(encoding="utf-8"))
    case_ids = [c["case_id"] for c in existing_data.get("cases", [])]
    assert "SRC-RIGHTS-CC0" in case_ids
    # Source IDs in the existing fixture must not include the Wikidata source ID
    source_ids = [c["source"]["source_id"] for c in existing_data.get("cases", [])]
    assert WIKIDATA_SOURCE_ID not in source_ids
