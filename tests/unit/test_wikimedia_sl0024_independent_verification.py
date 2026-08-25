"""Unit tests for hullq.bootstrap.wikimedia_sl0024_independent_verification."""

from __future__ import annotations

import pytest

from hullq.bootstrap.wikimedia_sl0024_independent_verification import (
    STRATUM_CAPS,
    STRATUM_ORDER,
    EvidenceStrength,
    ImmutableBoundaryIntegrityError,
    Recommendation,
    ResearchActionCeilingError,
    SourceClass,
    SubjectOutcome,
    build_verification_results_document,
    compute_evidence_strength_from_citations,
    compute_metrics,
    compute_qid_sha256,
    determine_recommendation,
    load_and_verify_immutable_boundaries,
    select_deterministic_sample,
    validate_action_ceilings,
    validate_outcome_evidence_consistency,
)


def _rows(tag_counts: dict[str, int]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    i = 0
    for tag, count in tag_counts.items():
        for _ in range(count):
            rows.append({"qid": f"Q{1000 + i}", "quality_tag": tag, "rationale": "r"})
            i += 1
    return rows


# ---------------------------------------------------------------------------
# Immutable boundaries
# ---------------------------------------------------------------------------


def test_load_and_verify_immutable_boundaries_against_real_repo() -> None:
    boundaries = load_and_verify_immutable_boundaries()
    assert boundaries.incremental_qid_lead_count == 409
    assert boundaries.quality_sample_total == 150
    assert boundaries.quality_tag_counts == {
        "plausible_model_or_class_lead": 102,
        "obvious_out_of_scope": 19,
        "ambiguous": 29,
    }
    assert boundaries.canonical_boat_model_count == 1770
    assert boundaries.historical_crosswalk_count == 1772
    assert len(boundaries.quality_review_rows) == 150


def test_load_and_verify_immutable_boundaries_fails_closed_on_missing_file(tmp_path) -> None:
    with pytest.raises((ImmutableBoundaryIntegrityError, FileNotFoundError, OSError)):
        load_and_verify_immutable_boundaries(quality_sample_path=tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# Deterministic sample selection
# ---------------------------------------------------------------------------


def test_select_deterministic_sample_is_deterministic_and_exact() -> None:
    rows = _rows({"plausible_model_or_class_lead": 20, "ambiguous": 8, "obvious_out_of_scope": 8})
    a = select_deterministic_sample(rows)
    b = select_deterministic_sample(list(reversed(rows)))
    assert a.selected_qids == b.selected_qids
    assert len(a.selected_qids) == 30
    assert len(set(a.selected_qids)) == 30
    for tag in STRATUM_ORDER:
        assert len(a.selected_by_stratum[tag]) == STRATUM_CAPS[tag]


def test_select_deterministic_sample_orders_by_ascending_sha256() -> None:
    rows = _rows({"plausible_model_or_class_lead": 20, "ambiguous": 8, "obvious_out_of_scope": 8})
    sample = select_deterministic_sample(rows)
    chosen = sample.selected_by_stratum["plausible_model_or_class_lead"]
    digests = [compute_qid_sha256(q) for q in chosen]
    assert digests == sorted(digests)


def test_select_deterministic_sample_fails_closed_on_insufficient_stratum_size() -> None:
    rows = _rows({"plausible_model_or_class_lead": 5, "ambiguous": 8, "obvious_out_of_scope": 8})
    with pytest.raises(ValueError):
        select_deterministic_sample(rows)


def test_select_deterministic_sample_fails_closed_on_unknown_tag() -> None:
    rows = [{"qid": "Q1", "quality_tag": "not_a_real_tag", "rationale": "r"}]
    with pytest.raises(ValueError):
        select_deterministic_sample(rows)


def test_select_deterministic_sample_matches_real_repo_committed_selection() -> None:
    boundaries = load_and_verify_immutable_boundaries()
    sample = select_deterministic_sample(list(boundaries.quality_review_rows))
    assert len(sample.selected_qids) == 30
    assert sample.selected_by_stratum["plausible_model_or_class_lead"][0] == "Q110127838"
    assert sample.selected_by_stratum["ambiguous"][0] == "Q119855214"
    assert sample.selected_by_stratum["obvious_out_of_scope"][0] == "Q22570174"


# ---------------------------------------------------------------------------
# Evidence-strength computation
# ---------------------------------------------------------------------------


def _citation(**kwargs) -> dict[str, object]:
    base = {
        "citation_id": "c1",
        "source_class": str(SourceClass.NON_QUALIFYING),
        "accessible": False,
        "supports_identity": False,
        "independent_of": [],
    }
    base.update(kwargs)
    return base


def test_evidence_strength_strong_source_from_single_accessible_supporting_strong_citation() -> (
    None
):
    citations = [
        _citation(
            citation_id="c1",
            source_class=str(SourceClass.MANUFACTURER_SHIPYARD),
            accessible=True,
            supports_identity=True,
        )
    ]
    assert compute_evidence_strength_from_citations(citations) == EvidenceStrength.STRONG_SOURCE


def test_evidence_strength_accessible_but_non_supporting_strong_class_is_insufficient() -> None:
    """Being accessible and in a strong source class is not enough if the
    page's own content does not affirmatively support the determination."""
    citations = [
        _citation(
            citation_id="c1",
            source_class=str(SourceClass.MANUFACTURER_SHIPYARD),
            accessible=True,
            supports_identity=False,
        )
    ]
    assert compute_evidence_strength_from_citations(citations) == EvidenceStrength.INSUFFICIENT


def test_evidence_strength_two_independent_specialists() -> None:
    citations = [
        _citation(
            citation_id="c1",
            source_class=str(SourceClass.HIGH_QUALITY_SPECIALIST_DOCUMENTATION),
            accessible=True,
            supports_identity=True,
            independent_of=["c2"],
        ),
        _citation(
            citation_id="c2",
            source_class=str(SourceClass.HIGH_QUALITY_SPECIALIST_DOCUMENTATION),
            accessible=True,
            supports_identity=True,
            independent_of=["c1"],
        ),
    ]
    assert (
        compute_evidence_strength_from_citations(citations)
        == EvidenceStrength.TWO_INDEPENDENT_SPECIALIST_SOURCES
    )


def test_evidence_strength_two_specialists_without_declared_independence_is_insufficient() -> None:
    citations = [
        _citation(
            citation_id="c1",
            source_class=str(SourceClass.HIGH_QUALITY_SPECIALIST_DOCUMENTATION),
            accessible=True,
            supports_identity=True,
            independent_of=[],
        ),
        _citation(
            citation_id="c2",
            source_class=str(SourceClass.HIGH_QUALITY_SPECIALIST_DOCUMENTATION),
            accessible=True,
            supports_identity=True,
            independent_of=[],
        ),
    ]
    assert compute_evidence_strength_from_citations(citations) == EvidenceStrength.INSUFFICIENT


def test_evidence_strength_single_specialist_is_insufficient() -> None:
    citations = [
        _citation(
            citation_id="c1",
            source_class=str(SourceClass.HIGH_QUALITY_SPECIALIST_DOCUMENTATION),
            accessible=True,
            supports_identity=True,
        )
    ]
    assert compute_evidence_strength_from_citations(citations) == EvidenceStrength.INSUFFICIENT


def test_evidence_strength_inaccessible_strong_citation_is_insufficient() -> None:
    citations = [
        _citation(
            citation_id="c1",
            source_class=str(SourceClass.MANUFACTURER_SHIPYARD),
            accessible=False,
            supports_identity=True,
        )
    ]
    assert compute_evidence_strength_from_citations(citations) == EvidenceStrength.INSUFFICIENT


# ---------------------------------------------------------------------------
# Outcome/evidence-strength consistency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome,strength,expect_ok",
    [
        (str(SubjectOutcome.IN_SCOPE_IDENTITY), str(EvidenceStrength.STRONG_SOURCE), True),
        (
            str(SubjectOutcome.IN_SCOPE_IDENTITY),
            str(EvidenceStrength.TWO_INDEPENDENT_SPECIALIST_SOURCES),
            True,
        ),
        (str(SubjectOutcome.IN_SCOPE_IDENTITY), str(EvidenceStrength.INSUFFICIENT), False),
        (str(SubjectOutcome.UNRESOLVED), str(EvidenceStrength.INSUFFICIENT), True),
        (str(SubjectOutcome.UNRESOLVED), str(EvidenceStrength.STRONG_SOURCE), False),
        (str(SubjectOutcome.CONFLICT), str(EvidenceStrength.INSUFFICIENT), True),
        (str(SubjectOutcome.OUT_OF_SCOPE), str(EvidenceStrength.STRONG_SOURCE), True),
        (str(SubjectOutcome.OUT_OF_SCOPE), str(EvidenceStrength.INSUFFICIENT), True),
    ],
)
def test_validate_outcome_evidence_consistency(outcome, strength, expect_ok) -> None:
    problems = validate_outcome_evidence_consistency(outcome, strength)
    assert (len(problems) == 0) == expect_ok


# ---------------------------------------------------------------------------
# Action ceilings
# ---------------------------------------------------------------------------


def test_validate_action_ceilings_accepts_within_bounds() -> None:
    assert (
        validate_action_ceilings(
            search_query_count=2, source_page_evaluation_count=4, combined_action_count=6
        )
        == []
    )


def test_validate_action_ceilings_rejects_over_search_cap() -> None:
    problems = validate_action_ceilings(
        search_query_count=3, source_page_evaluation_count=1, combined_action_count=4
    )
    assert problems


def test_validate_action_ceilings_rejects_arithmetic_mismatch() -> None:
    problems = validate_action_ceilings(
        search_query_count=1, source_page_evaluation_count=1, combined_action_count=5
    )
    assert problems


# ---------------------------------------------------------------------------
# Metrics + recommendation
# ---------------------------------------------------------------------------


def _result_row(
    qid: str,
    tag: str,
    outcome: str,
    strength: str,
    *,
    search: int = 1,
    evals: int = 1,
) -> dict[str, object]:
    citations = []
    if strength == str(EvidenceStrength.STRONG_SOURCE):
        citations = [
            _citation(
                citation_id=f"{qid}-c1",
                source_class=str(SourceClass.MANUFACTURER_SHIPYARD),
                accessible=True,
                supports_identity=True,
            )
        ]
    combined = search + evals
    return {
        "qid": qid,
        "prior_tag": tag,
        "search_query_count": search,
        "source_page_evaluation_count": evals,
        "combined_action_count": combined,
        "hit_budget_cap": combined >= 6,
        "subject_outcome": outcome,
        "evidence_strength": strength,
        "evidence_citations": citations,
    }


def test_compute_metrics_excludes_out_of_scope_strong_source_from_in_scope_counts() -> None:
    """Regression test for the bug where an out_of_scope row with
    evidence_strength=strong_source was miscounted as independently
    supported in-scope."""
    results = [
        _result_row(
            "Q1", "ambiguous", str(SubjectOutcome.OUT_OF_SCOPE), str(EvidenceStrength.STRONG_SOURCE)
        ),
        _result_row(
            "Q2",
            "ambiguous",
            str(SubjectOutcome.IN_SCOPE_IDENTITY),
            str(EvidenceStrength.STRONG_SOURCE),
        ),
    ]
    metrics = compute_metrics(results)
    assert metrics["independently_supported_in_scope_count"] == 1
    assert metrics["strong_source_in_scope_count"] == 1
    assert metrics["threshold_set_independently_supported_in_scope_count"] == 1
    assert metrics["threshold_set_strong_source_in_scope_count"] == 1


def test_compute_metrics_threshold_set_excludes_obvious_out_of_scope_stratum() -> None:
    results = [
        _result_row(
            "Q1",
            "obvious_out_of_scope",
            str(SubjectOutcome.IN_SCOPE_IDENTITY),
            str(EvidenceStrength.STRONG_SOURCE),
        ),
        _result_row(
            "Q2",
            "plausible_model_or_class_lead",
            str(SubjectOutcome.IN_SCOPE_IDENTITY),
            str(EvidenceStrength.STRONG_SOURCE),
        ),
    ]
    metrics = compute_metrics(results)
    assert metrics["threshold_set_independently_supported_in_scope_count"] == 1
    assert metrics["independently_supported_in_scope_count"] == 2


def test_determine_recommendation_rights_blocked_takes_priority() -> None:
    metrics = {
        "threshold_set_independently_supported_in_scope_count": 20,
        "threshold_set_strong_source_in_scope_count": 20,
        "median_combined_actions_independently_supported_threshold_set": 1,
        "search_query_count_total": 1,
        "source_page_evaluation_count_total": 1,
        "combined_research_action_count_total": 2,
    }
    assert (
        determine_recommendation(rights_access_ok=False, metrics=metrics)
        == Recommendation.RIGHTS_OR_ACCESS_BLOCKED
    )


def test_determine_recommendation_low_yield() -> None:
    metrics = {
        "threshold_set_independently_supported_in_scope_count": 11,
        "threshold_set_strong_source_in_scope_count": 11,
        "median_combined_actions_independently_supported_threshold_set": 1,
        "search_query_count_total": 1,
        "source_page_evaluation_count_total": 1,
        "combined_research_action_count_total": 2,
    }
    assert (
        determine_recommendation(rights_access_ok=True, metrics=metrics)
        == Recommendation.LOW_INDEPENDENT_VERIFICATION_YIELD
    )


def test_determine_recommendation_strong_source_too_weak() -> None:
    metrics = {
        "threshold_set_independently_supported_in_scope_count": 12,
        "threshold_set_strong_source_in_scope_count": 7,
        "median_combined_actions_independently_supported_threshold_set": 1,
        "search_query_count_total": 1,
        "source_page_evaluation_count_total": 1,
        "combined_research_action_count_total": 2,
    }
    assert (
        determine_recommendation(rights_access_ok=True, metrics=metrics)
        == Recommendation.STRONG_SOURCE_COVERAGE_TOO_WEAK
    )


def test_determine_recommendation_too_expensive_on_median() -> None:
    metrics = {
        "threshold_set_independently_supported_in_scope_count": 12,
        "threshold_set_strong_source_in_scope_count": 8,
        "median_combined_actions_independently_supported_threshold_set": 5,
        "search_query_count_total": 1,
        "source_page_evaluation_count_total": 1,
        "combined_research_action_count_total": 2,
    }
    assert (
        determine_recommendation(rights_access_ok=True, metrics=metrics)
        == Recommendation.TOO_EXPENSIVE_FOR_FULL_CAMPAIGN
    )


def test_determine_recommendation_too_expensive_on_global_ceiling() -> None:
    metrics = {
        "threshold_set_independently_supported_in_scope_count": 12,
        "threshold_set_strong_source_in_scope_count": 8,
        "median_combined_actions_independently_supported_threshold_set": 1,
        "search_query_count_total": 61,
        "source_page_evaluation_count_total": 1,
        "combined_research_action_count_total": 62,
    }
    assert (
        determine_recommendation(rights_access_ok=True, metrics=metrics)
        == Recommendation.TOO_EXPENSIVE_FOR_FULL_CAMPAIGN
    )


def test_determine_recommendation_full_campaign_candidate() -> None:
    metrics = {
        "threshold_set_independently_supported_in_scope_count": 13,
        "threshold_set_strong_source_in_scope_count": 12,
        "median_combined_actions_independently_supported_threshold_set": 2.0,
        "search_query_count_total": 48,
        "source_page_evaluation_count_total": 71,
        "combined_research_action_count_total": 119,
    }
    assert (
        determine_recommendation(rights_access_ok=True, metrics=metrics)
        == Recommendation.FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE
    )


# ---------------------------------------------------------------------------
# build_verification_results_document fails closed
# ---------------------------------------------------------------------------


def _sample_stub():
    from hullq.bootstrap.wikimedia_sl0024_independent_verification import SampleSelection

    return SampleSelection(
        selected_by_stratum={
            "plausible_model_or_class_lead": ("Q1",),
            "ambiguous": (),
            "obvious_out_of_scope": (),
        },
        selected_qids=("Q1",),
    )


def test_build_verification_results_document_fails_closed_on_missing_result() -> None:
    with pytest.raises(ValueError):
        build_verification_results_document(
            generated_at="2026-01-01T00:00:00Z",
            sample=_sample_stub(),
            results=[],
            rights_access_ok=True,
            process_deviations=[],
        )


def test_build_verification_results_document_fails_closed_on_ceiling_breach() -> None:
    row = _result_row(
        "Q1",
        "plausible_model_or_class_lead",
        str(SubjectOutcome.UNRESOLVED),
        str(EvidenceStrength.INSUFFICIENT),
        search=3,
        evals=0,
    )
    with pytest.raises(ResearchActionCeilingError):
        build_verification_results_document(
            generated_at="2026-01-01T00:00:00Z",
            sample=_sample_stub(),
            results=[row],
            rights_access_ok=True,
            process_deviations=[],
        )


def test_build_verification_results_document_fails_closed_on_evidence_mismatch() -> None:
    row = _result_row(
        "Q1",
        "plausible_model_or_class_lead",
        str(SubjectOutcome.IN_SCOPE_IDENTITY),
        str(EvidenceStrength.STRONG_SOURCE),
    )
    row["evidence_citations"] = []  # claims strong_source but has no supporting citation
    with pytest.raises(ValueError):
        build_verification_results_document(
            generated_at="2026-01-01T00:00:00Z",
            sample=_sample_stub(),
            results=[row],
            rights_access_ok=True,
            process_deviations=[],
        )
