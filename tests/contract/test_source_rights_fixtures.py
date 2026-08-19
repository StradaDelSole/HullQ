"""Contract tests for SLICE-0007 source-rights gate using accepted fixtures.

Covers required scenarios 15-19 and 27 using the canonical fixtures in
fixtures/sources/source_rights_cases.v0.1.json without weakening their
semantic outcomes.

Fixture semantics preserved:
- CC0: production/bulk allowed; automation independently conditional.
- CC BY: attribution/notice obligations visible; production/bulk conditional.
- Share-alike (ODbL): bulk/publication remains legal-review-required.
- Unlicensed primary factual: discrete reference only; bulk prohibited.
- NonCommercial: not acceptable for HullQ commercial production reliance.
- Unknown rights: fails closed for production/bulk.
- Historical reference scrape: barred from production/bulk/automation.

Scenario 27 — provenance impact integration test:
  Source → FieldEvidence → FieldResolution impact lookup still enumerates
  historical impact after a source is newly blocked, without deleting or
  mutating historical records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hullq.domain.provenance import (
    ConfidenceLevel,
    EvidenceType,
    FieldEvidence,
    FieldResolution,
    JsonPointer,
    NormalizedCandidate,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    ResolutionMethod,
    ResolutionState,
    ResolverKind,
    ResolverMetadata,
    SourceLocator,
    SubjectKind,
    source_impact_lookup,
)
from hullq.sources.rights import (
    DecisionOutcome,
    DecisionReason,
    ExtractionBudget,
    SourceUsageMetrics,
    SourceUse,
    check_source_use,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES_FILE = ROOT / "fixtures" / "sources" / "source_rights_cases.v0.1.json"


def _load_fixtures() -> dict[str, Any]:
    return json.loads(FIXTURES_FILE.read_text(encoding="utf-8"))


def _case_by_id(case_id: str) -> dict[str, Any]:
    data = _load_fixtures()
    for case in data["cases"]:
        if case["case_id"] == case_id:
            return case["source"]
    raise KeyError(f"Fixture case {case_id!r} not found")


# ---------------------------------------------------------------------------
# Scenario 15 — CC BY attribution/notice obligations are machine-visible
# ---------------------------------------------------------------------------


def test_ccby_exposes_attribution_obligation() -> None:
    src = _case_by_id("SRC-RIGHTS-CCBY")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.obligations is not None
    assert dec.obligations.attribution_required == "yes"


def test_ccby_exposes_notice_obligation() -> None:
    src = _case_by_id("SRC-RIGHTS-CCBY")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.obligations is not None
    assert dec.obligations.notice_required == "yes"


def test_ccby_attribution_instructions_present() -> None:
    src = _case_by_id("SRC-RIGHTS-CCBY")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.obligations is not None
    assert dec.obligations.attribution_instructions is not None


def test_ccby_automated_ingestion_allows_when_access_allowed_and_within_budget() -> None:
    """CC BY has automated_access=allowed and clearance=allowed; within budget → ALLOWED."""
    src = _case_by_id("SRC-RIGHTS-CCBY")
    # CC BY: clearance.automated_ingestion = "allowed", access.automated_access = "allowed"
    # clearance.bulk_bootstrap = "conditional" (not bulk-cleared) → requires telemetry.
    metrics = SourceUsageMetrics(source_id="SRC_TEST_CCBY", retrieval_count=0, extracted_record_count=0)
    budget = ExtractionBudget(retrieval_limit=1000, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_ccby_production_is_conditional_not_auto_allowed() -> None:
    """CC BY production clearance is 'conditional' — gate must not auto-allow."""
    src = _case_by_id("SRC-RIGHTS-CCBY")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert dec.outcome == DecisionOutcome.CONDITIONAL


# ---------------------------------------------------------------------------
# Scenario 16 — share-alike fixture does not silently pass bulk/publication use
# ---------------------------------------------------------------------------


def test_sharealike_bulk_bootstrap_does_not_allow() -> None:
    src = _case_by_id("SRC-RIGHTS-SHAREALIKE")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome != DecisionOutcome.ALLOWED


def test_sharealike_bulk_bootstrap_routes_to_legal_review() -> None:
    src = _case_by_id("SRC-RIGHTS-SHAREALIKE")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.LEGAL_REVIEW_REQUIRED


def test_sharealike_artifact_redistribution_does_not_allow() -> None:
    src = _case_by_id("SRC-RIGHTS-SHAREALIKE")
    dec = check_source_use(src, SourceUse.ARTIFACT_REDISTRIBUTION)
    assert dec.outcome != DecisionOutcome.ALLOWED


def test_sharealike_research_reference_is_allowed() -> None:
    """Research reference is explicitly allowed for the share-alike fixture."""
    src = _case_by_id("SRC-RIGHTS-SHAREALIKE")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Scenario 17 — NonCommercial fixture does not pass commercial production use
# ---------------------------------------------------------------------------


def test_nc_production_value_is_prohibited() -> None:
    src = _case_by_id("SRC-RIGHTS-NC")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_nc_bulk_bootstrap_is_prohibited() -> None:
    src = _case_by_id("SRC-RIGHTS-NC")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_nc_automated_ingestion_is_blocked() -> None:
    src = _case_by_id("SRC-RIGHTS-NC")
    metrics = SourceUsageMetrics(source_id="SRC_TEST_NC", retrieval_count=0, extracted_record_count=0)
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_nc_research_reference_is_allowed() -> None:
    src = _case_by_id("SRC-RIGHTS-NC")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Scenario 18 — unknown-rights fixture fails closed for production/bulk
# ---------------------------------------------------------------------------


def test_unknown_rights_production_does_not_allow() -> None:
    src = _case_by_id("SRC-RIGHTS-UNKNOWN")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED


def test_unknown_rights_bulk_does_not_allow() -> None:
    src = _case_by_id("SRC-RIGHTS-UNKNOWN")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome != DecisionOutcome.ALLOWED


def test_unknown_rights_unassessed_source_blocks_high_risk_uses() -> None:
    """assessment_status=unassessed on UNKNOWN fixture must block high-risk uses."""
    src = _case_by_id("SRC-RIGHTS-UNKNOWN")
    assert src["rights"]["assessment_status"] == "unassessed"
    for use in (
        SourceUse.PRODUCTION_VALUE,
        SourceUse.BULK_BOOTSTRAP,
        SourceUse.ARTIFACT_REDISTRIBUTION,
    ):
        dec = check_source_use(src, use)
        assert dec.outcome == DecisionOutcome.UNKNOWN_UNASSESSED
        assert DecisionReason.SOURCE_UNASSESSED in dec.reasons


def test_unknown_rights_automated_ingestion_fails_closed() -> None:
    src = _case_by_id("SRC-RIGHTS-UNKNOWN")
    metrics = SourceUsageMetrics(
        source_id="SRC_TEST_UNKNOWN", retrieval_count=0, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome != DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Scenario 19 — historical reference scrape cannot authorize production/bulk/automation
# ---------------------------------------------------------------------------


def test_reference_scrape_production_is_prohibited() -> None:
    src = _case_by_id("SRC-RIGHTS-REFERENCE-SCRAPE")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_reference_scrape_bulk_is_prohibited() -> None:
    src = _case_by_id("SRC-RIGHTS-REFERENCE-SCRAPE")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_reference_scrape_automated_ingestion_blocked_by_access_prohibition() -> None:
    src = _case_by_id("SRC-RIGHTS-REFERENCE-SCRAPE")
    metrics = SourceUsageMetrics(
        source_id="SRC_TEST_REFERENCE_SCRAPE", retrieval_count=0, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.AUTOMATED_ACCESS_PROHIBITED in dec.reasons


def test_reference_scrape_research_reference_is_allowed() -> None:
    src = _case_by_id("SRC-RIGHTS-REFERENCE-SCRAPE")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# CC0 fixture — production/bulk allowed; automation conditional
# ---------------------------------------------------------------------------


def test_cc0_production_value_is_allowed() -> None:
    src = _case_by_id("SRC-RIGHTS-CC0")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_cc0_bulk_bootstrap_is_allowed() -> None:
    src = _case_by_id("SRC-RIGHTS-CC0")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_cc0_automated_ingestion_is_conditional_not_allowed() -> None:
    """CC0 has automated_access=conditional — automation is independently non-allow."""
    src = _case_by_id("SRC-RIGHTS-CC0")
    metrics = SourceUsageMetrics(
        source_id="SRC_TEST_CC0", retrieval_count=0, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome != DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Primary factual reference fixture
# ---------------------------------------------------------------------------


def test_primary_fact_research_reference_is_allowed() -> None:
    src = _case_by_id("SRC-RIGHTS-PRIMARY-FACT")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_primary_fact_bulk_is_prohibited() -> None:
    src = _case_by_id("SRC-RIGHTS-PRIMARY-FACT")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_primary_fact_production_is_conditional() -> None:
    src = _case_by_id("SRC-RIGHTS-PRIMARY-FACT")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.CONDITIONAL


# ---------------------------------------------------------------------------
# Scenario 27 — provenance impact integration (SLICE-0006 reverse lookup)
# ---------------------------------------------------------------------------


def _make_evidence(
    evidence_id: str,
    source_id: str,
    subject: ProvenanceSubject,
    fp: JsonPointer,
) -> FieldEvidence:
    return FieldEvidence(
        evidence_id=evidence_id,
        subject=subject,
        field_pointer=fp,
        source_id=source_id,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.LITERAL,
            value=10.5,
            unit="m",
            excerpt=None,
        ),
        normalized_candidate=NormalizedCandidate(
            value=10.5, unit="m", method_id="length_v1", method_version="1.0"
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="test-tool",
            version="1.0",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-19",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
    )


def _make_resolution(
    resolution_id: str,
    subject: ProvenanceSubject,
    fp: JsonPointer,
    evidence_id: str,
) -> FieldResolution:
    return FieldResolution(
        resolution_id=resolution_id,
        subject=subject,
        field_pointer=fp,
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot=10.5,
        supporting_evidence_ids=frozenset({evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="0.1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="test-resolver",
            version="1.0",
        ),
        resolved_at="2026-08-19",
        supersedes_resolution_id=None,
        notes=None,
    )


def test_source_rights_block_enumerates_affected_evidence_and_resolutions_without_mutation() -> None:
    """Scenario 27: blocking a source enumerates affected provenance without deleting records."""
    blocked_source_id = "SRC_TEST_REFERENCE_SCRAPE"
    unrelated_source_id = "SRC_OTHER"

    subject = ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="BD_TEST_IMPACT")
    fp = JsonPointer("/baseline/dimensions/loa_m")

    # Evidence from the blocked source and an unrelated source.
    ev_blocked = _make_evidence("EV_001", blocked_source_id, subject, fp)
    ev_other = _make_evidence("EV_002", unrelated_source_id, subject, fp)

    # Resolution referencing the blocked evidence.
    res_blocked = _make_resolution("RES_001", subject, fp, "EV_001")

    evidence_collection = [ev_blocked, ev_other]
    resolution_collection = [res_blocked]

    # Gate decision: reference scrape → blocked.
    src = _case_by_id("SRC-RIGHTS-REFERENCE-SCRAPE")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED

    # Reverse impact lookup using SLICE-0006 boundary.
    affected_ev, affected_res = source_impact_lookup(
        blocked_source_id, evidence_collection, resolution_collection
    )

    # Historical evidence is enumerated but not deleted or mutated.
    assert len(affected_ev) == 1
    assert affected_ev[0].evidence_id == "EV_001"
    assert len(affected_res) == 1
    assert affected_res[0].resolution_id == "RES_001"

    # Evidence records remain intact (immutable — read-only verification).
    assert evidence_collection[0].evidence_id == "EV_001"
    assert evidence_collection[1].evidence_id == "EV_002"
    assert len(evidence_collection) == 2

    # Unrelated evidence is not affected.
    unrelated_ev, unrelated_res = source_impact_lookup(
        unrelated_source_id, evidence_collection, resolution_collection
    )
    assert len(unrelated_ev) == 1
    assert unrelated_ev[0].evidence_id == "EV_002"
    assert len(unrelated_res) == 0
