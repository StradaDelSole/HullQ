"""Contract test for the reviewed Wikipedia Source record — SLICE-0023.

Covers:
  1. reviewed Wikipedia Source record validates against SOURCE_SCHEMA.v0.2;
  2. research_lead and (budget-gated) automated_ingestion clearances allow;
  3. bulk_bootstrap/production_value/identity_seed/artifact_redistribution
     remain legal_review_required (never silently allowed);
  4. Wikipedia text share-alike/attribution obligations are recorded truthfully
     and are distinct from the Wikidata CC0 baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from hullq.contracts.registry import ContractRegistry
from hullq.sources.rights import (
    DecisionOutcome,
    ExtractionBudget,
    SourceUsageMetrics,
    SourceUse,
    check_source_use,
)
from hullq.sources.wikimedia import WIKIPEDIA_SOURCE_ID

ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "specs"
WIKIPEDIA_FIXTURE = ROOT / "fixtures" / "sources" / "wikipedia_source.json"


def _load_wikipedia_source() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(WIKIPEDIA_FIXTURE.read_text(encoding="utf-8")))


def _make_registry() -> ContractRegistry:
    return ContractRegistry.from_directory(SPECS_DIR)


# ---------------------------------------------------------------------------
# Schema validity
# ---------------------------------------------------------------------------


def test_wikipedia_source_record_exists() -> None:
    assert WIKIPEDIA_FIXTURE.exists(), f"Missing fixture: {WIKIPEDIA_FIXTURE}"


def test_wikipedia_source_record_is_valid_json() -> None:
    source = _load_wikipedia_source()
    assert isinstance(source, dict)


def test_wikipedia_source_record_validates_against_schema() -> None:
    registry = _make_registry()
    source = _load_wikipedia_source()
    validator = registry.validator_by_name("SOURCE_SCHEMA.v0.2.json")
    errors = list(validator.iter_errors(source))
    assert errors == [], f"Schema validation errors: {[str(e) for e in errors]}"


def test_wikipedia_source_record_has_correct_source_id() -> None:
    source = _load_wikipedia_source()
    assert source["source_id"] == WIKIPEDIA_SOURCE_ID


def test_wikipedia_source_record_is_assessed() -> None:
    source = _load_wikipedia_source()
    assert source["rights"]["assessment_status"] == "assessed"


def test_wikipedia_source_record_has_rights_evidence() -> None:
    source = _load_wikipedia_source()
    evidence = source["rights"]["rights_evidence"]
    assert isinstance(evidence, list)
    assert len(evidence) >= 4


def test_wikipedia_source_record_evidence_covers_required_urls() -> None:
    source = _load_wikipedia_source()
    urls = {e["url"] for e in source["rights"]["rights_evidence"]}
    required = {
        "https://foundation.wikimedia.org/wiki/Terms_of_Use",
        "https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy",
        "https://www.mediawiki.org/wiki/API:Categorymembers",
        "https://www.mediawiki.org/wiki/API:Licensing",
    }
    assert required <= urls


def test_wikipedia_source_record_has_review_date() -> None:
    source = _load_wikipedia_source()
    review = source["rights"]["review"]
    assert isinstance(review["reviewed_at"], str)
    assert len(review["reviewed_at"]) > 0


# ---------------------------------------------------------------------------
# Wikipedia is not equivalent to Wikidata CC0 (SOURCE_RIGHTS_POLICY section 8)
# ---------------------------------------------------------------------------


def test_wikipedia_source_record_is_not_cc0() -> None:
    source = _load_wikipedia_source()
    assert source["rights"]["license_expression"] != "CC0-1.0"
    assert source["rights"]["license_expression"] == "CC-BY-SA-4.0"


def test_wikipedia_source_record_records_share_alike_and_attribution() -> None:
    source = _load_wikipedia_source()
    obligations = source["rights"]["obligations"]
    assert obligations["share_alike"] == "yes"
    assert obligations["attribution_required"] == "yes"


def test_wikipedia_source_record_redistribution_is_not_allowed() -> None:
    source = _load_wikipedia_source()
    assert source["rights"]["permissions"]["redistribute_source_material"] == "prohibited"


# ---------------------------------------------------------------------------
# Use-specific clearance: research_lead + automated_ingestion allow; bulk/
# production/identity/redistribution remain legal-review-required
# ---------------------------------------------------------------------------


def test_wikipedia_rights_gate_research_lead_allows() -> None:
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.RESEARCH_LEAD)
    assert decision.outcome == DecisionOutcome.ALLOWED, (
        f"Expected ALLOWED; got {decision.outcome} with reasons {decision.reasons}"
    )


def test_wikipedia_rights_gate_research_reference_allows() -> None:
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.RESEARCH_REFERENCE)
    assert decision.outcome == DecisionOutcome.ALLOWED


def test_wikipedia_rights_gate_automated_ingestion_allows_within_budget() -> None:
    """Not bulk-cleared, so AUTOMATED_INGESTION requires metrics+budget
    (REQ-RESEARCH-008) even though it is allowed within the configured ceiling.
    """
    source = _load_wikipedia_source()
    metrics = SourceUsageMetrics(
        source_id=WIKIPEDIA_SOURCE_ID, retrieval_count=0, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=75, extracted_record_limit=None)
    decision = check_source_use(
        source, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget
    )
    assert decision.outcome == DecisionOutcome.ALLOWED, (
        f"Expected ALLOWED; got {decision.outcome} with reasons {decision.reasons}"
    )


def test_wikipedia_rights_gate_automated_ingestion_blocks_without_telemetry() -> None:
    """REQ-RESEARCH-008: since bulk_bootstrap is not cleared, AUTOMATED_INGESTION
    without metrics/budget must fail closed rather than default-allow.
    """
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.AUTOMATED_INGESTION)
    assert decision.outcome != DecisionOutcome.ALLOWED


def test_wikipedia_rights_gate_automated_ingestion_blocks_over_budget() -> None:
    source = _load_wikipedia_source()
    metrics = SourceUsageMetrics(
        source_id=WIKIPEDIA_SOURCE_ID, retrieval_count=75, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=75, extracted_record_limit=None)
    decision = check_source_use(
        source, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget
    )
    assert decision.outcome != DecisionOutcome.ALLOWED


def test_wikipedia_rights_gate_bulk_bootstrap_requires_review() -> None:
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.BULK_BOOTSTRAP)
    assert decision.outcome != DecisionOutcome.ALLOWED


def test_wikipedia_rights_gate_production_value_requires_review() -> None:
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.PRODUCTION_VALUE)
    assert decision.outcome != DecisionOutcome.ALLOWED


def test_wikipedia_rights_gate_identity_seed_requires_review() -> None:
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.IDENTITY_SEED)
    assert decision.outcome != DecisionOutcome.ALLOWED


def test_wikipedia_rights_gate_artifact_redistribution_requires_review() -> None:
    source = _load_wikipedia_source()
    decision = check_source_use(source, SourceUse.ARTIFACT_REDISTRIBUTION)
    assert decision.outcome != DecisionOutcome.ALLOWED


def test_wikipedia_source_record_does_not_weaken_existing_cc0_fixture() -> None:
    """The Wikipedia record is a separate file; it must not modify the existing
    Wikidata source-rights fixtures.
    """
    existing_fixture = ROOT / "fixtures" / "sources" / "source_rights_cases.v0.1.json"
    existing_data = json.loads(existing_fixture.read_text(encoding="utf-8"))
    source_ids = [c["source"]["source_id"] for c in existing_data.get("cases", [])]
    assert WIKIPEDIA_SOURCE_ID not in source_ids
