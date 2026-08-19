"""Unit tests for hullq.sources.rights — SLICE-0007.

Covers required scenarios 4-26 and 28 from SLICE-0007:
 4. Source-use enum matches the seven Source clearance keys.
 5. production_value=allowed on assessed compatible source can allow.
 6. production_value=unknown fails closed.
 7. production_value=prohibited blocks.
 8. production_value=legal_review_required routes to review.
 9. production_value=conditional does not auto-allow.
10. bulk_bootstrap=allowed and compatible permissions can allow.
11. bulk_bootstrap various non-allow states do not auto-allow.
12. automated ingestion blocked when automated access prohibited.
13. automated ingestion not allowed when access unknown or conditional.
14. explicit permission conflict fails closed.
21. telemetry aggregates by source ID.
22. negative telemetry values are rejected.
23. extraction threshold produces deterministic continue vs block.
24. missing telemetry context fails closed.
25. bulk-cleared source not subjected to invented low-volume cap.
26. routing without falsely completing the job.
28. no API performs network acquisition or grants rights from prestige/name alone.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hullq.sources.rights import (
    DecisionOutcome,
    DecisionReason,
    ExtractionBudget,
    JobRouting,
    SourceUsageMetrics,
    SourceUse,
    SourceUseDecision,
    check_source_use,
    route_research_job,
)

# ---------------------------------------------------------------------------
# Minimal synthetic source builders
# ---------------------------------------------------------------------------


def _make_source(
    *,
    source_id: str = "SRC_SYNTH",
    assessment_status: str = "assessed",
    clearance_overrides: dict[str, str] | None = None,
    permission_overrides: dict[str, str] | None = None,
    automated_access: str = "allowed",
    share_alike: str = "no",
    attribution_required: str = "no",
    notice_required: str = "no",
    bulk_bootstrap_clearance: str = "allowed",
) -> dict[str, Any]:
    """Build a minimal schema-valid Source dict for gate tests."""
    clearance: dict[str, str] = {
        "research_reference": "allowed",
        "research_lead": "allowed",
        "identity_seed": "allowed",
        "production_value": "allowed",
        "bulk_bootstrap": bulk_bootstrap_clearance,
        "automated_ingestion": "allowed",
        "artifact_redistribution": "allowed",
    }
    if clearance_overrides:
        clearance.update(clearance_overrides)

    permissions: dict[str, str] = {
        "commercial_use": "allowed",
        "extract_facts": "allowed",
        "normalize": "allowed",
        "store_canonical_values": "allowed",
        "bulk_ingest": "allowed",
        "automated_extract": "allowed",
        "redistribute_source_material": "allowed",
        "publish_derived_database": "allowed",
    }
    if permission_overrides:
        permissions.update(permission_overrides)

    return {
        "source_id": source_id,
        "title": "Synthetic test source",
        "publisher": "Synthetic Publisher",
        "source_type": "structured_dataset",
        "url": None,
        "document_identifier": None,
        "publication_date": None,
        "accessed_at": "2026-08-19",
        "notes": None,
        "rights": {
            "assessment_status": assessment_status,
            "rights_basis": "standard_license",
            "rights_holder": "Synthetic Publisher",
            "license_expression": "CC0-1.0",
            "license_name": "Creative Commons Zero",
            "license_url": None,
            "license_scope": ["database_contents"],
            "access": {
                "method": "download",
                "public_access": True,
                "automated_access": automated_access,
                "terms_url": None,
                "terms_reviewed_at": "2026-08-19",
                "tdm_reservation": "not_applicable",
                "rate_limit_notes": None,
            },
            "permissions": permissions,
            "obligations": {
                "attribution_required": attribution_required,
                "share_alike": share_alike,
                "notice_required": notice_required,
                "attribution_instructions": None,
                "other_conditions": [],
            },
            "clearance": clearance,
            "rights_evidence": [],
            "review": {
                "reviewed_at": "2026-08-19",
                "reviewer": "fixture",
                "rationale": "Synthetic test.",
                "next_review_at": None,
            },
        },
    }


def _minimal_metrics(source_id: str = "SRC_SYNTH") -> SourceUsageMetrics:
    return SourceUsageMetrics(source_id=source_id, retrieval_count=0, extracted_record_count=0)


def _budget(retrieval_limit: int = 100) -> ExtractionBudget:
    return ExtractionBudget(retrieval_limit=retrieval_limit, extracted_record_limit=None)


# ---------------------------------------------------------------------------
# Scenario 4 — Source-use enum vocabulary
# ---------------------------------------------------------------------------


def test_source_use_enum_has_seven_values() -> None:
    expected = {
        "research_reference",
        "research_lead",
        "identity_seed",
        "production_value",
        "bulk_bootstrap",
        "automated_ingestion",
        "artifact_redistribution",
    }
    actual = {u.value for u in SourceUse}
    assert actual == expected


# ---------------------------------------------------------------------------
# Scenarios 5-9 — production_value clearance gate
# ---------------------------------------------------------------------------


def test_production_value_allowed_on_compatible_assessed_source() -> None:
    src = _make_source()
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.ALLOWED
    assert DecisionReason.CLEARANCE_ALLOWED in dec.reasons


def test_production_value_unknown_fails_closed() -> None:
    src = _make_source(clearance_overrides={"production_value": "unknown"})
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.UNKNOWN_UNASSESSED
    assert DecisionReason.CLEARANCE_UNKNOWN in dec.reasons


def test_production_value_prohibited_blocks() -> None:
    src = _make_source(clearance_overrides={"production_value": "prohibited"})
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.CLEARANCE_PROHIBITED in dec.reasons


def test_production_value_legal_review_required_routes_to_review() -> None:
    src = _make_source(clearance_overrides={"production_value": "legal_review_required"})
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.LEGAL_REVIEW_REQUIRED
    assert DecisionReason.CLEARANCE_LEGAL_REVIEW_REQUIRED in dec.reasons


def test_production_value_conditional_does_not_auto_allow() -> None:
    src = _make_source(clearance_overrides={"production_value": "conditional"})
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert dec.outcome == DecisionOutcome.CONDITIONAL


# ---------------------------------------------------------------------------
# Scenarios 10-11 — bulk_bootstrap clearance gate
# ---------------------------------------------------------------------------


def test_bulk_bootstrap_allowed_with_compatible_permissions_allows() -> None:
    src = _make_source(share_alike="no")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_bulk_bootstrap_unknown_does_not_auto_allow() -> None:
    src = _make_source(clearance_overrides={"bulk_bootstrap": "unknown"})
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.UNKNOWN_UNASSESSED


def test_bulk_bootstrap_prohibited_blocks() -> None:
    src = _make_source(clearance_overrides={"bulk_bootstrap": "prohibited"})
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_bulk_bootstrap_legal_review_required_does_not_auto_allow() -> None:
    src = _make_source(clearance_overrides={"bulk_bootstrap": "legal_review_required"})
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.LEGAL_REVIEW_REQUIRED


def test_bulk_bootstrap_conditional_does_not_auto_allow() -> None:
    src = _make_source(clearance_overrides={"bulk_bootstrap": "conditional"})
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.CONDITIONAL


# ---------------------------------------------------------------------------
# Scenario 12 — automated ingestion blocked when access prohibited
# ---------------------------------------------------------------------------


def test_automated_ingestion_blocked_when_access_prohibited_even_if_clearance_open() -> None:
    src = _make_source(
        clearance_overrides={"automated_ingestion": "allowed"},
        automated_access="prohibited",
    )
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=_minimal_metrics(),
        budget=_budget(),
    )
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.AUTOMATED_ACCESS_PROHIBITED in dec.reasons


# ---------------------------------------------------------------------------
# Scenario 13 — automated ingestion not allowed when access unknown or conditional
# ---------------------------------------------------------------------------


def test_automated_ingestion_not_allowed_when_access_unknown() -> None:
    src = _make_source(automated_access="unknown")
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=_minimal_metrics(),
        budget=_budget(),
    )
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.AUTOMATED_ACCESS_UNKNOWN in dec.reasons


def test_automated_ingestion_not_allowed_when_access_conditional() -> None:
    src = _make_source(automated_access="conditional")
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=_minimal_metrics(),
        budget=_budget(),
    )
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.AUTOMATED_ACCESS_CONDITIONAL in dec.reasons


# ---------------------------------------------------------------------------
# Scenario 14 — explicit permission conflicts fail closed
# ---------------------------------------------------------------------------


def test_production_clearance_allowed_but_store_canonical_prohibited_fails_closed() -> None:
    src = _make_source(
        permission_overrides={"store_canonical_values": "prohibited"},
    )
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.PERMISSION_CONFLICT_STORE_CANONICAL in dec.reasons


def test_bulk_bootstrap_clearance_allowed_but_bulk_ingest_prohibited_fails_closed() -> None:
    src = _make_source(
        permission_overrides={"bulk_ingest": "prohibited"},
    )
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.PERMISSION_CONFLICT_BULK_INGEST in dec.reasons


def test_automated_ingestion_clearance_allowed_but_automated_extract_prohibited_fails_closed() -> (
    None
):
    src = _make_source(
        clearance_overrides={"automated_ingestion": "allowed"},
        permission_overrides={"automated_extract": "prohibited"},
        automated_access="allowed",
    )
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=_minimal_metrics(),
        budget=_budget(),
    )
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.PERMISSION_CONFLICT_AUTOMATED_EXTRACT in dec.reasons


def test_artifact_redistribution_clearance_allowed_but_redistribute_prohibited_fails_closed() -> (
    None
):
    src = _make_source(
        permission_overrides={"redistribute_source_material": "prohibited"},
    )
    dec = check_source_use(src, SourceUse.ARTIFACT_REDISTRIBUTION)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.PERMISSION_CONFLICT_REDISTRIBUTE in dec.reasons


def test_commercial_production_prohibited_fails_closed() -> None:
    src = _make_source(
        permission_overrides={"commercial_use": "prohibited"},
    )
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.PERMISSION_CONFLICT_COMMERCIAL in dec.reasons


# ---------------------------------------------------------------------------
# Scenarios 21-22 — telemetry aggregation and validation
# ---------------------------------------------------------------------------


def test_telemetry_aggregates_by_source_id() -> None:
    m1 = SourceUsageMetrics(source_id="SRC_A", retrieval_count=5, extracted_record_count=10)
    m2 = SourceUsageMetrics(source_id="SRC_B", retrieval_count=3, extracted_record_count=7)
    assert m1.source_id == "SRC_A"
    assert m2.source_id == "SRC_B"
    m1_updated = m1.add(retrieval_delta=2)
    assert m1_updated.retrieval_count == 7
    assert m1_updated.source_id == "SRC_A"


def test_negative_telemetry_retrieval_rejected() -> None:
    with pytest.raises(ValueError, match="retrieval_count must be non-negative"):
        SourceUsageMetrics(source_id="SRC_X", retrieval_count=-1, extracted_record_count=0)


def test_negative_telemetry_extracted_rejected() -> None:
    with pytest.raises(ValueError, match="extracted_record_count must be non-negative"):
        SourceUsageMetrics(source_id="SRC_X", retrieval_count=0, extracted_record_count=-1)


def test_negative_add_delta_rejected() -> None:
    m = SourceUsageMetrics(source_id="SRC_X", retrieval_count=5, extracted_record_count=0)
    with pytest.raises(ValueError, match="deltas must be non-negative"):
        m.add(retrieval_delta=-1)


# ---------------------------------------------------------------------------
# Scenario 23 — extraction threshold produces deterministic continue vs block
# ---------------------------------------------------------------------------


def test_within_extraction_threshold_allows() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=50, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_at_extraction_threshold_blocks() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=100, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.EXTRACTION_THRESHOLD_EXCEEDED in dec.reasons


def test_over_extraction_threshold_blocks() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=150, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_extracted_record_limit_also_enforced() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=0, extracted_record_count=1000
    )
    budget = ExtractionBudget(retrieval_limit=None, extracted_record_limit=500)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=budget)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.EXTRACTION_THRESHOLD_EXCEEDED in dec.reasons


# ---------------------------------------------------------------------------
# Scenario 24 — missing required telemetry context fails closed
# ---------------------------------------------------------------------------


def test_missing_metrics_for_non_bulk_cleared_automated_fails_closed() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=_budget())
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.MISSING_TELEMETRY_CONTEXT in dec.reasons


def test_missing_budget_for_non_bulk_cleared_automated_fails_closed() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    dec = check_source_use(
        src, SourceUse.AUTOMATED_INGESTION, metrics=_minimal_metrics(), budget=None
    )
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.MISSING_TELEMETRY_CONTEXT in dec.reasons


def test_missing_both_for_non_bulk_cleared_automated_fails_closed() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=None)
    assert dec.outcome == DecisionOutcome.BLOCKED


# ---------------------------------------------------------------------------
# Scenario 25 — bulk-cleared source not subjected to invented cap
# ---------------------------------------------------------------------------


def test_bulk_cleared_source_automated_ingestion_no_invented_cap() -> None:
    """A bulk-cleared source must not require telemetry/budget for automated ingestion."""
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="allowed",
    )
    # No metrics or budget provided — must still allow because source is bulk-cleared.
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=None)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_bulk_cleared_source_with_metrics_still_allows_without_budget() -> None:
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="allowed",
    )
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=_minimal_metrics())
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Fix 1 — Effective bulk clearance, not only raw clearance field
# ---------------------------------------------------------------------------


def test_bulk_ingest_prohibited_means_not_effectively_bulk_cleared() -> None:
    """bulk_bootstrap=allowed but bulk_ingest=prohibited: must still require telemetry/budget."""
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="allowed",
        permission_overrides={"bulk_ingest": "prohibited"},
    )
    # No metrics or budget — a truly bulk-cleared source would allow, but this one is not.
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=None)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.MISSING_TELEMETRY_CONTEXT in dec.reasons


def test_share_alike_unresolved_means_not_effectively_bulk_cleared() -> None:
    """bulk_bootstrap=allowed but share_alike=yes: must still require telemetry/budget."""
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="allowed",
        share_alike="yes",
    )
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=None)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.MISSING_TELEMETRY_CONTEXT in dec.reasons


def test_share_alike_unknown_means_not_effectively_bulk_cleared() -> None:
    """bulk_bootstrap=allowed but share_alike=unknown: must still require telemetry/budget."""
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="allowed",
        share_alike="unknown",
    )
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=None)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.MISSING_TELEMETRY_CONTEXT in dec.reasons


def test_compatible_bulk_cleared_source_still_bypasses_telemetry() -> None:
    """Genuinely bulk-cleared (no incompatible constraints) must not receive an invented cap."""
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="allowed",
        share_alike="no",
    )
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=None, budget=None)
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Fix 2 — ExtractionBudget must have at least one configured non-negative limit
# ---------------------------------------------------------------------------


def test_extraction_budget_both_none_is_rejected() -> None:
    """ExtractionBudget(None, None) is not a valid budget — must raise ValueError."""
    with pytest.raises(ValueError, match="at least one configured limit"):
        ExtractionBudget(retrieval_limit=None, extracted_record_limit=None)


def test_extraction_budget_negative_retrieval_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="retrieval_limit must be non-negative"):
        ExtractionBudget(retrieval_limit=-1, extracted_record_limit=None)


def test_extraction_budget_negative_extracted_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="extracted_record_limit must be non-negative"):
        ExtractionBudget(retrieval_limit=None, extracted_record_limit=-1)


def test_extraction_budget_retrieval_only_is_valid() -> None:
    b = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    assert b.retrieval_limit == 100
    assert b.extracted_record_limit is None


def test_extraction_budget_extracted_only_is_valid() -> None:
    b = ExtractionBudget(retrieval_limit=None, extracted_record_limit=500)
    assert b.retrieval_limit is None
    assert b.extracted_record_limit == 500


def test_extraction_budget_both_valid_limits_is_valid() -> None:
    b = ExtractionBudget(retrieval_limit=100, extracted_record_limit=500)
    assert b.retrieval_limit == 100
    assert b.extracted_record_limit == 500


# ---------------------------------------------------------------------------
# Scenario 26 — rights-gate routing does not falsely complete the job
# ---------------------------------------------------------------------------


def _make_decision(outcome: DecisionOutcome) -> SourceUseDecision:
    return SourceUseDecision(
        source_id="SRC_SYNTH",
        use=SourceUse.PRODUCTION_VALUE,
        outcome=outcome,
        reasons=frozenset(),
        obligations=None,
    )


def test_allowed_decision_routes_to_continue() -> None:
    routing = route_research_job(_make_decision(DecisionOutcome.ALLOWED))
    assert routing == JobRouting.CONTINUE


def test_blocked_decision_routes_to_blocked() -> None:
    routing = route_research_job(_make_decision(DecisionOutcome.BLOCKED))
    assert routing == JobRouting.BLOCKED


def test_legal_review_routes_to_needs_review() -> None:
    routing = route_research_job(_make_decision(DecisionOutcome.LEGAL_REVIEW_REQUIRED))
    assert routing == JobRouting.NEEDS_REVIEW


def test_conditional_routes_to_needs_review() -> None:
    routing = route_research_job(_make_decision(DecisionOutcome.CONDITIONAL))
    assert routing == JobRouting.NEEDS_REVIEW


def test_unknown_unassessed_routes_to_needs_review() -> None:
    routing = route_research_job(_make_decision(DecisionOutcome.UNKNOWN_UNASSESSED))
    assert routing == JobRouting.NEEDS_REVIEW


def test_routing_never_produces_complete_status() -> None:
    """No gate outcome routes to a complete ResearchJob status."""
    from hullq.research.jobs import ResearchJobStatus

    complete_equivalent = {ResearchJobStatus.COMPLETE}
    for outcome in DecisionOutcome:
        routing = route_research_job(_make_decision(outcome))
        # JobRouting has no COMPLETE variant — verify by exhaustive check.
        assert routing in {JobRouting.CONTINUE, JobRouting.NEEDS_REVIEW, JobRouting.BLOCKED}
        assert routing.value not in {s.value for s in complete_equivalent}


# ---------------------------------------------------------------------------
# Scenario 20 — allowed permission without use-specific clearance does not allow
# ---------------------------------------------------------------------------


def test_allowed_permission_without_clearance_does_not_allow_production() -> None:
    """permissions.store_canonical_values=allowed is insufficient; clearance must match."""
    src = _make_source(
        clearance_overrides={"production_value": "conditional"},
        permission_overrides={"store_canonical_values": "allowed"},
    )
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED


def test_allowed_permission_without_clearance_does_not_allow_bulk() -> None:
    src = _make_source(
        clearance_overrides={"bulk_bootstrap": "unknown"},
        permission_overrides={"bulk_ingest": "allowed"},
    )
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome != DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Scenario 28 — no network acquisition; no rights from prestige/name alone
# ---------------------------------------------------------------------------


def test_no_network_acquisition_in_check_source_use() -> None:
    """check_source_use must be a pure function with no I/O side effects."""
    import inspect

    source_code = inspect.getsource(check_source_use)
    # The gate must not call any network/IO libraries.
    for forbidden in ("httpx", "urllib", "requests", "socket", "http.client"):
        assert forbidden not in source_code, (
            f"check_source_use references {forbidden!r} — no network acquisition allowed"
        )


def test_prestigious_license_name_alone_does_not_grant_rights() -> None:
    """A source named 'CC0' in license_name but with prohibited clearances must still block."""
    src = _make_source(
        clearance_overrides={"production_value": "prohibited"},
    )
    # Override license_name to something that sounds open.
    src["rights"]["license_name"] = "Creative Commons Zero v1.0 Universal"
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome == DecisionOutcome.BLOCKED


def test_trusted_publisher_name_does_not_grant_rights() -> None:
    """Publisher identity alone must not authorize production use."""
    src = _make_source(
        clearance_overrides={"production_value": "unknown"},
    )
    src["publisher"] = "Trusted Official Publisher"
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Blocker 1 — Telemetry binding: metrics must be attributed to the evaluated source
# ---------------------------------------------------------------------------


def test_metrics_source_id_mismatch_fails_closed() -> None:
    """Blocker 1: metrics from a different source must not satisfy the gate for another source."""
    src = _make_source(
        source_id="SRC_A",
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics_b = SourceUsageMetrics(source_id="SRC_B", retrieval_count=0, extracted_record_count=0)
    dec = check_source_use(
        src, SourceUse.AUTOMATED_INGESTION, metrics=metrics_b, budget=_budget(100)
    )
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.METRICS_SOURCE_ID_MISMATCH in dec.reasons


def test_source_a_cannot_use_source_b_telemetry_regression() -> None:
    """Regression: Source A with a tight budget cannot pass by supplying Source B's counters."""
    src_a = _make_source(
        source_id="SRC_A",
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics_b = SourceUsageMetrics(source_id="SRC_B", retrieval_count=0, extracted_record_count=0)
    budget = ExtractionBudget(retrieval_limit=5, extracted_record_limit=None)
    dec = check_source_use(src_a, SourceUse.AUTOMATED_INGESTION, metrics=metrics_b, budget=budget)
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.METRICS_SOURCE_ID_MISMATCH in dec.reasons


def test_matching_source_id_in_metrics_proceeds_normally() -> None:
    """Matching source_id in metrics does not trigger the mismatch guard."""
    src = _make_source(
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    metrics = SourceUsageMetrics(source_id="SRC_SYNTH", retrieval_count=0, extracted_record_count=0)
    dec = check_source_use(src, SourceUse.AUTOMATED_INGESTION, metrics=metrics, budget=_budget(100))
    assert dec.outcome == DecisionOutcome.ALLOWED
    assert DecisionReason.METRICS_SOURCE_ID_MISMATCH not in dec.reasons


# ---------------------------------------------------------------------------
# Blocker 2 — Projected cumulative extraction usage
# ---------------------------------------------------------------------------


def test_projected_extraction_within_limit_allows() -> None:
    """current=98 + projected=1 with limit=100 → allow."""
    src = _make_source(automated_access="allowed", bulk_bootstrap_clearance="conditional")
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=98, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=metrics,
        budget=budget,
        projected_retrieval_delta=1,
    )
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_projected_extraction_at_limit_blocks() -> None:
    """current=99 + projected=1 with limit=100 → non-allow (at-or-above fails closed)."""
    src = _make_source(automated_access="allowed", bulk_bootstrap_clearance="conditional")
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=99, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=metrics,
        budget=budget,
        projected_retrieval_delta=1,
    )
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.EXTRACTION_THRESHOLD_EXCEEDED in dec.reasons


def test_projected_extraction_crossing_limit_blocks() -> None:
    """Projected increment that would cross the limit → non-allow."""
    src = _make_source(automated_access="allowed", bulk_bootstrap_clearance="conditional")
    metrics = SourceUsageMetrics(
        source_id="SRC_SYNTH", retrieval_count=95, extracted_record_count=0
    )
    budget = ExtractionBudget(retrieval_limit=100, extracted_record_limit=None)
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=metrics,
        budget=budget,
        projected_retrieval_delta=10,
    )
    assert dec.outcome == DecisionOutcome.BLOCKED
    assert DecisionReason.EXTRACTION_THRESHOLD_EXCEEDED in dec.reasons


def test_negative_projected_retrieval_delta_rejected() -> None:
    """Negative projected retrieval increment must be rejected with ValueError."""
    src = _make_source(automated_access="allowed", bulk_bootstrap_clearance="conditional")
    metrics = SourceUsageMetrics(source_id="SRC_SYNTH", retrieval_count=0, extracted_record_count=0)
    with pytest.raises(ValueError, match="non-negative"):
        check_source_use(
            src,
            SourceUse.AUTOMATED_INGESTION,
            metrics=metrics,
            budget=_budget(100),
            projected_retrieval_delta=-1,
        )


def test_negative_projected_extracted_delta_rejected() -> None:
    """Negative projected extracted increment must be rejected with ValueError."""
    src = _make_source(automated_access="allowed", bulk_bootstrap_clearance="conditional")
    metrics = SourceUsageMetrics(source_id="SRC_SYNTH", retrieval_count=0, extracted_record_count=0)
    with pytest.raises(ValueError, match="non-negative"):
        check_source_use(
            src,
            SourceUse.AUTOMATED_INGESTION,
            metrics=metrics,
            budget=_budget(100),
            projected_extracted_delta=-1,
        )


def test_bulk_cleared_source_not_affected_by_projected_deltas() -> None:
    """Bulk-cleared sources skip the telemetry check; projected deltas must not add an invented cap."""
    src = _make_source(automated_access="allowed", bulk_bootstrap_clearance="allowed")
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=None,
        budget=None,
        projected_retrieval_delta=99999,
    )
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Blocker 4 — Fail closed on unresolved overall rights assessment for high-risk uses
# ---------------------------------------------------------------------------


def test_legal_review_required_assessment_blocks_production_value() -> None:
    """assessment_status=legal_review_required + production_value=allowed → non-allow."""
    src = _make_source(assessment_status="legal_review_required")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.ASSESSMENT_UNRESOLVED in dec.reasons


def test_conflict_assessment_blocks_production_value() -> None:
    """assessment_status=conflict + production_value=allowed → non-allow."""
    src = _make_source(assessment_status="conflict")
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.ASSESSMENT_UNRESOLVED in dec.reasons


def test_legal_review_required_assessment_blocks_bulk_bootstrap() -> None:
    """assessment_status=legal_review_required + bulk_bootstrap=allowed → non-allow."""
    src = _make_source(assessment_status="legal_review_required")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.ASSESSMENT_UNRESOLVED in dec.reasons


def test_conflict_assessment_blocks_bulk_bootstrap() -> None:
    """assessment_status=conflict + bulk_bootstrap=allowed → non-allow."""
    src = _make_source(assessment_status="conflict")
    dec = check_source_use(src, SourceUse.BULK_BOOTSTRAP)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.ASSESSMENT_UNRESOLVED in dec.reasons


def test_legal_review_required_assessment_blocks_automated_ingestion() -> None:
    """assessment_status=legal_review_required blocks automated ingestion (high-risk)."""
    src = _make_source(
        assessment_status="legal_review_required",
        automated_access="allowed",
        bulk_bootstrap_clearance="conditional",
    )
    dec = check_source_use(
        src,
        SourceUse.AUTOMATED_INGESTION,
        metrics=_minimal_metrics(),
        budget=_budget(100),
    )
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.ASSESSMENT_UNRESOLVED in dec.reasons


def test_conflict_assessment_blocks_artifact_redistribution() -> None:
    """assessment_status=conflict + artifact_redistribution=allowed → non-allow."""
    src = _make_source(assessment_status="conflict")
    dec = check_source_use(src, SourceUse.ARTIFACT_REDISTRIBUTION)
    assert dec.outcome != DecisionOutcome.ALLOWED
    assert DecisionReason.ASSESSMENT_UNRESOLVED in dec.reasons


def test_unresolved_assessment_does_not_affect_low_risk_uses() -> None:
    """assessment_status=legal_review_required does not block research_reference (low-risk)."""
    src = _make_source(assessment_status="legal_review_required")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.outcome == DecisionOutcome.ALLOWED


def test_unresolved_conflict_does_not_affect_low_risk_uses() -> None:
    """assessment_status=conflict does not block research_reference (low-risk)."""
    src = _make_source(assessment_status="conflict")
    dec = check_source_use(src, SourceUse.RESEARCH_REFERENCE)
    assert dec.outcome == DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


@given(
    retrieval=st.integers(min_value=0, max_value=10_000),
    extracted=st.integers(min_value=0, max_value=10_000),
    r_delta=st.integers(min_value=0, max_value=10_000),
    e_delta=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=200)
def test_usage_metrics_always_non_negative_after_add(
    retrieval: int, extracted: int, r_delta: int, e_delta: int
) -> None:
    m = SourceUsageMetrics(
        source_id="SRC_PROP",
        retrieval_count=retrieval,
        extracted_record_count=extracted,
    )
    m2 = m.add(retrieval_delta=r_delta, extracted_delta=e_delta)
    assert m2.retrieval_count >= 0
    assert m2.extracted_record_count >= 0
    assert m2.retrieval_count == retrieval + r_delta
    assert m2.extracted_record_count == extracted + e_delta


@given(
    clearance_state=st.sampled_from(
        ["prohibited", "legal_review_required", "conditional", "unknown"]
    )
)
@settings(max_examples=100)
def test_non_allow_clearance_never_produces_allowed_outcome(clearance_state: str) -> None:
    src = _make_source(clearance_overrides={"production_value": clearance_state})
    dec = check_source_use(src, SourceUse.PRODUCTION_VALUE)
    assert dec.outcome != DecisionOutcome.ALLOWED
