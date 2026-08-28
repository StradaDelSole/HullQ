"""Unit tests for the SLICE-0032 sequential positive-control BoatDesign
applicability pilot pure logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot import (
    ALLOWED_FIELD_POINTERS,
    FIXED_CANDIDATE_SEQUENCE,
    MAX_RETRIEVALS_PER_CANDIDATE,
    MAX_TOTAL_RETRIEVALS,
    CandidateOutcome,
    TopLevelResult,
    build_artifact_digests,
    candidate_source_cleared,
    compute_candidate_result,
    compute_top_level_result,
    derive_sr_6_6_use_clearance,
    retained_package_filenames,
    sr_6_6_conditions_satisfied,
    validate_applicability_scope_invariant,
    validate_boatdesign_applicability,
    validate_bounded_scope,
    validate_field_applicability,
    validate_permissions_bounded,
    validate_sequential_stop_invariant,
    validate_source_retrieval_log,
    validate_stop_on_first_positive_retrievals,
    verify_artifact_digests_self_consistency,
    verify_fixed_candidate_sequence,
    verify_result_self_consistency,
    verify_source_clearance_assessment_self_consistency,
)

ROOT = Path(__file__).resolve().parents[2]
SL0032_DIR = ROOT / "research" / "stage3" / "sl0032-positive-control-boatdesign-applicability"


# ---------------------------------------------------------------------------
# Shared fixtures / builders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeRankedCandidate:
    hullq_id: str
    qids: tuple[str, ...]


def _real_ranked_sequence() -> list[_FakeRankedCandidate]:
    return [
        _FakeRankedCandidate(hullq_id=c.hullq_id, qids=(c.qid,)) for c in FIXED_CANDIDATE_SEQUENCE
    ]


_UNBOUNDED_SCOPE: dict[str, Any] = {
    "schema_version": "0.1",
    "first_year": None,
    "last_year": None,
    "hull_number_from": None,
    "hull_number_to": None,
    "market_or_region": None,
    "named_variant_hint": None,
    "design_option_hints": None,
    "operating_state_hint": None,
    "individual_hull_or_listing_ref": None,
    "unknown_or_unbounded": True,
}


def _bounded_year_scope() -> dict[str, Any]:
    scope = dict(_UNBOUNDED_SCOPE)
    scope.update(first_year=1998, last_year=2001, unknown_or_unbounded=False)
    return scope


def _rank1_source_record() -> dict[str, Any]:
    return {
        "source_id": "SRC_TEST_2026",
        "title": "Test official builder page",
        "publisher": "Test Builder",
        "source_type": "manufacturer_official_website",
        "url": "https://www.example-official-builder.com/",
        "document_identifier": "example.com;model.html",
        "publication_date": None,
        "accessed_at": "2026-08-28T00:00:00+00:00",
        "notes": "test",
        "rights": {
            "assessment_status": "assessed",
            "rights_basis": "unlicensed_factual_reference",
            "rights_holder": "Test Builder",
            "license_expression": None,
            "license_name": None,
            "license_url": None,
            "license_scope": ["unknown"],
            "access": {
                "method": "public_web",
                "public_access": True,
                "automated_access": "unknown",
                "terms_url": None,
                "terms_reviewed_at": "2026-08-28",
                "tdm_reservation": "none_observed",
                "rate_limit_notes": "test",
            },
            "permissions": {
                "commercial_use": "conditional",
                "extract_facts": "allowed",
                "normalize": "allowed",
                "store_canonical_values": "conditional",
                "bulk_ingest": "unknown",
                "automated_extract": "unknown",
                "redistribute_source_material": "prohibited",
                "publish_derived_database": "conditional",
            },
            "obligations": {
                "attribution_required": "unknown",
                "share_alike": "not_applicable",
                "notice_required": "unknown",
                "attribution_instructions": None,
                "other_conditions": [],
            },
            "clearance": {
                "research_reference": "allowed",
                "research_lead": "allowed",
                "identity_seed": "allowed",
                "production_value": "allowed",
                "bulk_bootstrap": "legal_review_required",
                "automated_ingestion": "unknown",
                "artifact_redistribution": "legal_review_required",
            },
            "rights_evidence": [],
            "review": {
                "reviewed_at": "2026-08-28",
                "reviewer": "test",
                "rationale": "test",
                "next_review_at": None,
            },
        },
    }


def _satisfied_conditions() -> list[dict[str, Any]]:
    return [
        {"condition": "lawfully_publicly_accessible", "satisfied": True, "evidence": "e"},
        {
            "condition": "reused_element_is_discrete_factual_value_not_expressive_content",
            "satisfied": True,
            "evidence": "e",
        },
        {"condition": "provenance_recorded", "satisfied": True, "evidence": "e"},
        {
            "condition": "no_identified_source_term_prohibits_the_chosen_method",
            "satisfied": True,
            "evidence": "e",
        },
        {
            "condition": "not_systematic_or_bulk_database_extraction",
            "satisfied": True,
            "evidence": "e",
        },
        {
            "condition": "no_automated_extraction_unless_separately_cleared",
            "satisfied": "partial_left_unresolved",
            "evidence": "e",
        },
    ]


def _rank1_clearance_entry() -> dict[str, Any]:
    c = FIXED_CANDIDATE_SEQUENCE[0]
    return {
        "candidate_rank": 1,
        "qid": c.qid,
        "hullq_id": c.hullq_id,
        "source_located": True,
        "sr_6_6_condition_evaluation": {
            "policy_reference": "specs/SOURCE_RIGHTS_POLICY.v0.1.md#6.6",
            "conditions": _satisfied_conditions(),
            "conditions_satisfied_for_bounded_manual_use": True,
        },
        "source_record": _rank1_source_record(),
        "bounded_scope": {
            "hullq_ids": [c.hullq_id],
            "qids": [c.qid],
            "field_pointers": sorted(ALLOWED_FIELD_POINTERS),
            "use_kinds": ["identity_seed", "production_value"],
            "note": "test",
        },
        "source_use_gate_decisions": {
            "gate_module": "hullq.sources.rights.check_source_use",
            "note": "test",
            "decisions": {
                "research_reference": {"outcome": "allowed"},
                "research_lead": {"outcome": "allowed"},
                "identity_seed": {"outcome": "allowed"},
                "production_value": {"outcome": "allowed"},
                "bulk_bootstrap": {"outcome": "legal_review_required"},
                "automated_ingestion": {"outcome": "unknown_unassessed"},
                "artifact_redistribution": {"outcome": "legal_review_required"},
            },
        },
        "candidate_source_clearance_result": "SOURCE_USE_CLEARED_FOR_APPLICABILITY_RESEARCH",
    }


def _blocked_clearance_entry(rank: int) -> dict[str, Any]:
    c = FIXED_CANDIDATE_SEQUENCE[rank - 1]
    return {
        "candidate_rank": rank,
        "qid": c.qid,
        "hullq_id": c.hullq_id,
        "source_located": False,
        "no_source_rationale": "no qualifying source located",
        "candidate_source_clearance_result": "RIGHTS_CLEARANCE_BLOCKED",
    }


def _real_clearance_document() -> dict[str, Any]:
    return {
        "schema_version": "sl0032-source-clearance-assessment-v1",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            _rank1_clearance_entry(),
            _blocked_clearance_entry(2),
            _blocked_clearance_entry(3),
        ],
    }


def _field(pointer: str, outcome: str, *, scope: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "field_pointer": pointer,
        "outcome": outcome,
        "wikidata_normalized_candidate": {"value": "1.0", "unit": "m"},
        "primary_source_value": None,
        "applicability_scope": scope if scope is not None else dict(_UNBOUNDED_SCOPE),
        "notes": "test",
    }


def _all_fields(outcome: str, *, scope: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [_field(p, outcome, scope=scope) for p in sorted(ALLOWED_FIELD_POINTERS)]


def _real_field_applicability_document() -> dict[str, Any]:
    return {
        "schema_version": "sl0032-field-applicability-v1",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "allowed_field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "candidates": [
            {
                "candidate_rank": c.rank,
                "qid": c.qid,
                "hullq_id": c.hullq_id,
                "fields": _all_fields("RIGHTS_BLOCKED" if c.rank != 1 else "SOURCE_VALUE_CONFLICT"),
            }
            for c in FIXED_CANDIDATE_SEQUENCE
        ],
    }


def _real_boatdesign_document() -> dict[str, Any]:
    return {
        "schema_version": "sl0032-boatdesign-applicability-v1",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            {
                "candidate_rank": c.rank,
                "qid": c.qid,
                "hullq_id": c.hullq_id,
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_UNBOUNDED_SCOPE),
                "findings": "test",
            }
            for c in FIXED_CANDIDATE_SEQUENCE
        ],
    }


# ---------------------------------------------------------------------------
# 1. Fixed candidate sequence reproduction
# ---------------------------------------------------------------------------


def test_verify_fixed_candidate_sequence_matches_real_sequence() -> None:
    assert verify_fixed_candidate_sequence(_real_ranked_sequence()) == []


def test_verify_fixed_candidate_sequence_rejects_swapped_order() -> None:
    ranked = _real_ranked_sequence()
    ranked[0], ranked[1] = ranked[1], ranked[0]
    problems = verify_fixed_candidate_sequence(ranked)
    assert problems


def test_verify_fixed_candidate_sequence_rejects_ineligible_replacement() -> None:
    ranked = _real_ranked_sequence()
    ranked[2] = _FakeRankedCandidate(hullq_id="BM_WDT0_NOT_ELIGIBLE", qids=("Q1",))
    problems = verify_fixed_candidate_sequence(ranked)
    assert any("rank 3" in p for p in problems)


def test_verify_fixed_candidate_sequence_rejects_too_few_candidates() -> None:
    problems = verify_fixed_candidate_sequence(_real_ranked_sequence()[:2])
    assert problems


# ---------------------------------------------------------------------------
# 2. Retrieval log
# ---------------------------------------------------------------------------


def _valid_retrieval(index: int, rank: int) -> dict[str, Any]:
    host = sorted(
        {1: {"www.buzzardsbayboatshop.com"}, 2: {"www.bgrace.fr"}, 3: {"www.marlow-hunter.com"}}[
            rank
        ]
    )[0]
    return {
        "retrieval_index": index,
        "candidate_rank": rank,
        "url": f"https://{host}/",
        "source_surface_class": "official_current_model_and_navigation_page",
        "accessed_at": "2026-08-28T00:00:00+00:00",
        "retrieval_outcome": "fetched",
        "http_status": 200,
        "content_type": "text/html",
        "byte_size": 100,
        "sha256": "a" * 64,
        "fact_purpose": "test",
    }


def _valid_retrieval_log(retrievals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "sl0032-source-retrieval-log-v1",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "retrieval_ceiling_per_candidate": MAX_RETRIEVALS_PER_CANDIDATE,
        "retrieval_ceiling_total": MAX_TOTAL_RETRIEVALS,
        "retrieval_count": len(retrievals),
        "retrieval_method_note": "test",
        "retrievals": retrievals,
    }


def test_validate_source_retrieval_log_happy_path() -> None:
    log = _valid_retrieval_log(
        [_valid_retrieval(1, 1), _valid_retrieval(2, 2), _valid_retrieval(3, 3)]
    )
    assert validate_source_retrieval_log(log) == []


def test_validate_source_retrieval_log_rejects_over_per_candidate_ceiling() -> None:
    retrievals = [_valid_retrieval(i, 1) for i in range(1, MAX_RETRIEVALS_PER_CANDIDATE + 2)]
    log = _valid_retrieval_log(retrievals)
    problems = validate_source_retrieval_log(log)
    assert any("exceeds fixed MAX_RETRIEVALS_PER_CANDIDATE" in p for p in problems)


def test_validate_source_retrieval_log_rejects_over_total_ceiling() -> None:
    retrievals = []
    idx = 1
    for rank in (1, 2, 3):
        for _ in range(MAX_RETRIEVALS_PER_CANDIDATE):
            retrievals.append(_valid_retrieval(idx, rank))
            idx += 1
    # 36 exactly is fine; add one more to push rank 1 over its own per-candidate
    # ceiling AND the total ceiling simultaneously is avoided by using a
    # dedicated 4th "rank" bucket check instead: directly assert the total-only
    # ceiling by keeping per-candidate <=12 but total >36 is impossible with
    # only 3 ranks, so we instead assert MAX_TOTAL_RETRIEVALS is enforced by
    # construction: 3 * 12 == 36 == MAX_TOTAL_RETRIEVALS exactly.
    log = _valid_retrieval_log(retrievals)
    assert len(retrievals) == MAX_TOTAL_RETRIEVALS
    assert validate_source_retrieval_log(log) == []
    retrievals.append(_valid_retrieval(37, 1))
    log2 = _valid_retrieval_log(retrievals)
    problems = validate_source_retrieval_log(log2)
    assert any("exceeds fixed MAX_TOTAL_RETRIEVALS" in p for p in problems)


def test_validate_source_retrieval_log_rejects_disallowed_host_for_rank() -> None:
    bad = _valid_retrieval(1, 1)
    bad["url"] = "https://www.sailboatdata.com/"
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("not in the fixed permitted" in p for p in problems)


def test_validate_source_retrieval_log_rejects_search_snippet_surface_class() -> None:
    bad = _valid_retrieval(1, 1)
    bad["source_surface_class"] = "search_result_snippet"
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("source_surface_class" in p for p in problems)


def test_validate_source_retrieval_log_rejects_duplicate_index() -> None:
    log = _valid_retrieval_log([_valid_retrieval(1, 1), _valid_retrieval(1, 2)])
    problems = validate_source_retrieval_log(log)
    assert any("duplicate" in p for p in problems)


def test_validate_source_retrieval_log_rejects_non_contiguous_index_set() -> None:
    log = _valid_retrieval_log([_valid_retrieval(1, 1), _valid_retrieval(3, 2)])
    problems = validate_source_retrieval_log(log)
    assert any("is not exactly 1.." in p for p in problems)


def test_validate_source_retrieval_log_ignores_tampered_document_ceiling_values() -> None:
    """A retained artifact cannot redefine the ceiling by lying about its own
    ceiling fields -- validate_source_retrieval_log never reads them."""
    log = _valid_retrieval_log(
        [_valid_retrieval(i, 1) for i in range(1, MAX_RETRIEVALS_PER_CANDIDATE + 2)]
    )
    log["retrieval_ceiling_per_candidate"] = 999  # tampered, should be ignored
    log["retrieval_count"] = len(log["retrievals"])
    problems = validate_source_retrieval_log(log)
    assert any("exceeds fixed MAX_RETRIEVALS_PER_CANDIDATE" in p for p in problems)


def test_validate_stop_on_first_positive_retrievals_flags_later_rank_retrieval() -> None:
    log = _valid_retrieval_log([_valid_retrieval(1, 1), _valid_retrieval(2, 2)])
    ordered = [
        (1, CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT),
        (2, CandidateOutcome.NOT_ATTEMPTED_AFTER_SUCCESS),
    ]
    problems = validate_stop_on_first_positive_retrievals(log, ordered_candidate_results=ordered)
    assert problems


def test_validate_stop_on_first_positive_retrievals_passes_when_no_ready() -> None:
    log = _valid_retrieval_log(
        [_valid_retrieval(1, 1), _valid_retrieval(2, 2), _valid_retrieval(3, 3)]
    )
    ordered = [
        (1, CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT),
        (2, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
        (3, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
    ]
    assert validate_stop_on_first_positive_retrievals(log, ordered_candidate_results=ordered) == []


# ---------------------------------------------------------------------------
# 3. Source clearance / SR-6.6
# ---------------------------------------------------------------------------


def test_verify_source_clearance_assessment_happy_path() -> None:
    assert verify_source_clearance_assessment_self_consistency(_real_clearance_document()) == []


def test_sr_6_6_missing_condition_blocks_clearance() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["sr_6_6_condition_evaluation"]["conditions"][0]["satisfied"] = False
    # tamper: leave the derived flag/clearance as if still satisfied
    problems = verify_source_clearance_assessment_self_consistency(doc)
    assert problems
    assert not sr_6_6_conditions_satisfied(
        doc["candidates"][0]["sr_6_6_condition_evaluation"]["conditions"]
    )
    assert (
        derive_sr_6_6_use_clearance(
            doc["candidates"][0]["sr_6_6_condition_evaluation"]["conditions"]
        )
        == "conditional"
    )


def test_sr_6_6_condition_unsatisfied_cannot_coexist_with_allowed_clearance() -> None:
    doc = _real_clearance_document()
    entry = doc["candidates"][0]
    entry["sr_6_6_condition_evaluation"]["conditions"][0]["satisfied"] = False
    entry["sr_6_6_condition_evaluation"]["conditions_satisfied_for_bounded_manual_use"] = False
    # clearance.identity_seed/production_value still say 'allowed' -- tampered
    problems = verify_source_clearance_assessment_self_consistency(doc)
    assert any("is not mechanically derived" in p for p in problems)


def test_positive_clearance_cannot_silently_clear_automated_bulk_redistribution() -> None:
    entry = _rank1_clearance_entry()
    clearance = entry["source_record"]["rights"]["clearance"]
    assert clearance["automated_ingestion"] != "allowed"
    assert clearance["bulk_bootstrap"] != "allowed"
    assert clearance["artifact_redistribution"] != "allowed"


def test_validate_permissions_bounded_rejects_unscoped_allowed_permission() -> None:
    source = _rank1_source_record()
    source["rights"]["permissions"]["store_canonical_values"] = "allowed"
    assert validate_permissions_bounded(source) != []


def test_validate_bounded_scope_rejects_wrong_field_pointers() -> None:
    entry = _rank1_clearance_entry()
    entry["bounded_scope"]["field_pointers"] = ["/baseline/dimensions/loa_m"]
    problems = validate_bounded_scope(entry, fixed_candidate=FIXED_CANDIDATE_SEQUENCE[0])
    assert problems


def test_blocked_candidate_requires_rights_clearance_blocked_result() -> None:
    entry = _blocked_clearance_entry(2)
    entry["candidate_source_clearance_result"] = "SOURCE_USE_CLEARED_FOR_APPLICABILITY_RESEARCH"
    doc = _real_clearance_document()
    doc["candidates"][1] = entry
    problems = verify_source_clearance_assessment_self_consistency(doc)
    assert problems


def test_candidate_source_cleared() -> None:
    assert candidate_source_cleared(_rank1_clearance_entry()) is True
    assert candidate_source_cleared(_blocked_clearance_entry(2)) is False


# ---------------------------------------------------------------------------
# 4. Applicability scope invariant (closed-boundary rule)
# ---------------------------------------------------------------------------


def test_scope_half_open_year_range_cannot_be_bounded() -> None:
    scope = dict(_UNBOUNDED_SCOPE)
    scope.update(first_year=1998, last_year=None, unknown_or_unbounded=False)
    assert validate_applicability_scope_invariant(scope) != []

    scope2 = dict(_UNBOUNDED_SCOPE)
    scope2.update(first_year=None, last_year=2001, unknown_or_unbounded=False)
    assert validate_applicability_scope_invariant(scope2) != []


def test_scope_full_year_range_is_bounded() -> None:
    assert validate_applicability_scope_invariant(_bounded_year_scope()) == []


def test_scope_all_null_cannot_be_bounded() -> None:
    scope = dict(_UNBOUNDED_SCOPE)
    scope["unknown_or_unbounded"] = False
    assert validate_applicability_scope_invariant(scope) != []


def test_named_variant_label_alone_without_structured_evidence_cannot_be_bounded() -> None:
    """A 'Mk'/named-variant label mentioned only in prose, never positively
    captured into named_variant_hint (or any other structured dimension),
    leaves the scope all-null and therefore fails the bounded invariant --
    a label alone can never establish a BoatDesign generation boundary."""
    scope = dict(_UNBOUNDED_SCOPE)
    scope["unknown_or_unbounded"] = False  # claiming bounded from "the label" alone
    assert validate_applicability_scope_invariant(scope) != []


def test_named_variant_hint_actually_captured_is_a_valid_non_year_boundary() -> None:
    scope = dict(_UNBOUNDED_SCOPE)
    scope.update(named_variant_hint="Mk II", unknown_or_unbounded=False)
    assert validate_applicability_scope_invariant(scope) == []


# ---------------------------------------------------------------------------
# 5. BoatDesign / field applicability structural validation
# ---------------------------------------------------------------------------


def test_validate_boatdesign_applicability_happy_path() -> None:
    assert validate_boatdesign_applicability(_real_boatdesign_document()) == []


def test_validate_boatdesign_applicability_rejects_established_true_with_unbounded_scope() -> None:
    doc = _real_boatdesign_document()
    doc["candidates"][0]["generation_boundary_established_for_this_pilot"] = True
    # scope left unknown_or_unbounded=True -- inconsistent
    problems = validate_boatdesign_applicability(doc)
    assert problems


def test_validate_field_applicability_happy_path() -> None:
    field_doc = _real_field_applicability_document()
    # cross-reference evidence must match: build a matching corrected_candidate_evidence doc
    evidence_doc = {
        "candidates": [
            {
                "candidate_rank": c.rank,
                "fields": [
                    {"field_pointer": p, "normalized_candidate": {"value": "1.0", "unit": "m"}}
                    for p in sorted(ALLOWED_FIELD_POINTERS)
                ],
            }
            for c in FIXED_CANDIDATE_SEQUENCE
        ]
    }
    assert validate_field_applicability(field_doc, corrected_candidate_evidence=evidence_doc) == []


def test_validate_field_applicability_rejects_candidate_mismatch() -> None:
    field_doc = _real_field_applicability_document()
    evidence_doc = {
        "candidates": [
            {
                "candidate_rank": c.rank,
                "fields": [
                    {"field_pointer": p, "normalized_candidate": {"value": "999.0", "unit": "m"}}
                    for p in sorted(ALLOWED_FIELD_POINTERS)
                ],
            }
            for c in FIXED_CANDIDATE_SEQUENCE
        ]
    }
    problems = validate_field_applicability(field_doc, corrected_candidate_evidence=evidence_doc)
    assert problems


def test_validate_field_applicability_rejects_missing_field_pointer() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"] = field_doc["candidates"][0]["fields"][:-1]
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence={"candidates": []}
    )
    assert any("field pointer coverage" in p for p in problems)


def test_validate_field_applicability_safe_requires_bounded_scope() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"][0]["outcome"] = "SAFE_FOR_LATER_DESIGN_PROMOTION"
    # applicability_scope still unbounded -- must be rejected
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence={"candidates": []}
    )
    assert problems


# ---------------------------------------------------------------------------
# 6. Candidate-level / top-level result derivation
# ---------------------------------------------------------------------------


def test_compute_candidate_result_rights_blocked_wins_regardless_of_evidence() -> None:
    result = compute_candidate_result(
        source_cleared=False,
        generation_boundary_established=True,
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()),
    )
    assert result == CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED


def test_compute_candidate_result_ready_requires_bounded_generation_and_safe_field() -> None:
    result = compute_candidate_result(
        source_cleared=True,
        generation_boundary_established=True,
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()),
    )
    assert result == CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT


def test_compute_candidate_result_equality_alone_cannot_be_ready() -> None:
    """Even if a field is (incorrectly) marked SAFE_FOR_LATER_DESIGN_PROMOTION
    from mere numeric equality, an unbounded scope on that field still blocks
    READY -- the equality rule's guardrail."""
    result = compute_candidate_result(
        source_cleared=True,
        generation_boundary_established=True,
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=dict(_UNBOUNDED_SCOPE)),
    )
    assert result == CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT


def test_compute_candidate_result_option_sensitive_cannot_be_flattened_to_safe() -> None:
    result = compute_candidate_result(
        source_cleared=True,
        generation_boundary_established=True,
        field_outcomes=_all_fields("OPTION_SENSITIVE", scope=_bounded_year_scope()),
    )
    assert result == CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT


def test_compute_candidate_result_requires_generation_boundary_even_with_safe_field() -> None:
    result = compute_candidate_result(
        source_cleared=True,
        generation_boundary_established=False,
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()),
    )
    assert result == CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT


def test_compute_top_level_result_first_ready_rank_wins() -> None:
    ordered = [
        (1, CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT),
        (2, CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT),
    ]
    assert (
        compute_top_level_result(ordered)
        == TopLevelResult.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
    )


def test_compute_top_level_result_insufficient_when_one_cleared_but_none_ready() -> None:
    ordered = [
        (1, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
        (2, CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT),
        (3, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
    ]
    assert compute_top_level_result(ordered) == TopLevelResult.APPLICABILITY_EVIDENCE_INSUFFICIENT


def test_compute_top_level_result_rights_blocked_only_when_all_blocked() -> None:
    ordered = [
        (1, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
        (2, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
        (3, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
    ]
    assert compute_top_level_result(ordered) == TopLevelResult.RIGHTS_CLEARANCE_BLOCKED


# ---------------------------------------------------------------------------
# 7. Sequential stop-on-first-positive invariant
# ---------------------------------------------------------------------------


def test_sequential_invariant_candidate_2_cannot_be_attempted_after_1_ready() -> None:
    ordered = [
        (1, CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT),
        (2, CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT),
    ]
    assert validate_sequential_stop_invariant(ordered) != []


def test_sequential_invariant_candidate_3_cannot_be_attempted_after_1_or_2_ready() -> None:
    ordered = [
        (1, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
        (2, CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT),
        (3, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
    ]
    assert validate_sequential_stop_invariant(ordered) != []


def test_sequential_invariant_candidate_2_permitted_after_1_blocked_or_insufficient() -> None:
    for first in (
        CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED,
        CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT,
    ):
        ordered = [
            (1, first),
            (2, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
            (3, CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED),
        ]
        assert validate_sequential_stop_invariant(ordered) == []


def test_sequential_invariant_not_attempted_marker_requires_earlier_ready() -> None:
    ordered = [
        (1, CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT),
        (2, CandidateOutcome.NOT_ATTEMPTED_AFTER_SUCCESS),
    ]
    problems = validate_sequential_stop_invariant(ordered)
    assert any("no earlier rank reached READY" in p for p in problems)


def test_sequential_invariant_correct_stop_after_ready() -> None:
    ordered = [
        (1, CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT),
        (2, CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT),
        (3, CandidateOutcome.NOT_ATTEMPTED_AFTER_SUCCESS),
    ]
    assert validate_sequential_stop_invariant(ordered) == []


# ---------------------------------------------------------------------------
# 8. result.json cross-document self-consistency
# ---------------------------------------------------------------------------


def test_verify_result_self_consistency_real_negative_result() -> None:
    field_doc = _real_field_applicability_document()
    boundary_doc = _real_boatdesign_document()
    clearance_doc = _real_clearance_document()
    result_doc = {
        "candidates": [
            {"candidate_rank": 1, "result": "APPLICABILITY_EVIDENCE_INSUFFICIENT"},
            {"candidate_rank": 2, "result": "RIGHTS_CLEARANCE_BLOCKED"},
            {"candidate_rank": 3, "result": "RIGHTS_CLEARANCE_BLOCKED"},
        ],
        "top_level_result": "APPLICABILITY_EVIDENCE_INSUFFICIENT",
        "successful_rank": None,
    }
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=field_doc,
        boatdesign_applicability_document=boundary_doc,
        source_clearance_document=clearance_doc,
    )
    assert problems == []


def test_verify_result_self_consistency_rejects_tampered_top_level_result() -> None:
    field_doc = _real_field_applicability_document()
    boundary_doc = _real_boatdesign_document()
    clearance_doc = _real_clearance_document()
    result_doc = {
        "candidates": [
            {"candidate_rank": 1, "result": "APPLICABILITY_EVIDENCE_INSUFFICIENT"},
            {"candidate_rank": 2, "result": "RIGHTS_CLEARANCE_BLOCKED"},
            {"candidate_rank": 3, "result": "RIGHTS_CLEARANCE_BLOCKED"},
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",  # tampered
        "successful_rank": 1,
    }
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=field_doc,
        boatdesign_applicability_document=boundary_doc,
        source_clearance_document=clearance_doc,
    )
    assert problems


def test_verify_result_self_consistency_rejects_successful_rank_without_ready() -> None:
    field_doc = _real_field_applicability_document()
    boundary_doc = _real_boatdesign_document()
    clearance_doc = _real_clearance_document()
    result_doc = {
        "candidates": [
            {"candidate_rank": 1, "result": "APPLICABILITY_EVIDENCE_INSUFFICIENT"},
            {"candidate_rank": 2, "result": "RIGHTS_CLEARANCE_BLOCKED"},
            {"candidate_rank": 3, "result": "RIGHTS_CLEARANCE_BLOCKED"},
        ],
        "top_level_result": "APPLICABILITY_EVIDENCE_INSUFFICIENT",
        "successful_rank": 1,  # tampered -- no rank is READY
    }
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=field_doc,
        boatdesign_applicability_document=boundary_doc,
        source_clearance_document=clearance_doc,
    )
    assert problems


# ---------------------------------------------------------------------------
# 9. Artifact digests
# ---------------------------------------------------------------------------


def test_build_and_verify_artifact_digests_round_trip(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text('{"x": 1}\n', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"y": 2}\n', encoding="utf-8")
    digests = build_artifact_digests(generated_at="2026-08-28T00:00:00+00:00", package_dir=tmp_path)
    assert set(digests["digests"]) == {"a.json", "b.json"}
    assert (
        verify_artifact_digests_self_consistency(artifact_digests=digests, package_dir=tmp_path)
        == []
    )


def test_artifact_digest_tamper_fails_verification(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text('{"x": 1}\n', encoding="utf-8")
    digests = build_artifact_digests(generated_at="2026-08-28T00:00:00+00:00", package_dir=tmp_path)
    (tmp_path / "a.json").write_text('{"x": 2}\n', encoding="utf-8")  # tamper after digesting
    problems = verify_artifact_digests_self_consistency(
        artifact_digests=digests, package_dir=tmp_path
    )
    assert problems


def test_artifact_digest_extra_undeclared_file_fails_verification(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text('{"x": 1}\n', encoding="utf-8")
    digests = build_artifact_digests(generated_at="2026-08-28T00:00:00+00:00", package_dir=tmp_path)
    (tmp_path / "sneaky.json").write_text("{}\n", encoding="utf-8")
    problems = verify_artifact_digests_self_consistency(
        artifact_digests=digests, package_dir=tmp_path
    )
    assert any("sneaky.json" in p for p in problems)


def test_retained_package_filenames_excludes_digest_file(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "ARTIFACT-DIGESTS.json").write_text("{}\n", encoding="utf-8")
    assert retained_package_filenames(tmp_path) == {"a.json"}


# ---------------------------------------------------------------------------
# 9b. Additional retrieval-log adversarial branches
# ---------------------------------------------------------------------------


def test_validate_source_retrieval_log_rejects_count_mismatch() -> None:
    log = _valid_retrieval_log([_valid_retrieval(1, 1)])
    log["retrieval_count"] = 5
    problems = validate_source_retrieval_log(log)
    assert any("retrieval_count" in p for p in problems)


def test_validate_source_retrieval_log_rejects_non_integer_index() -> None:
    bad = _valid_retrieval(1, 1)
    bad["retrieval_index"] = "one"
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("duplicate or non-integer" in p for p in problems)


def test_validate_source_retrieval_log_rejects_malformed_sha256() -> None:
    bad = _valid_retrieval(1, 1)
    bad["sha256"] = "not-a-hex-digest"
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("not a valid lowercase hex digest" in p for p in problems)


def test_validate_source_retrieval_log_rejects_unrecognized_outcome() -> None:
    bad = _valid_retrieval(1, 1)
    bad["retrieval_outcome"] = "cached_forever"
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("unrecognized retrieval_outcome" in p for p in problems)


def test_validate_source_retrieval_log_rejects_dns_failure_carrying_sha256() -> None:
    bad = _valid_retrieval(1, 2)
    bad["retrieval_outcome"] = "dns_resolution_failed"
    # sha256/http_status left populated -- inconsistent with a failed fetch
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("must not carry an sha256/http_status" in p for p in problems)


def test_validate_source_retrieval_log_rejects_missing_http_status_on_fetched() -> None:
    bad = _valid_retrieval(1, 1)
    bad["http_status"] = None
    log = _valid_retrieval_log([bad])
    problems = validate_source_retrieval_log(log)
    assert any("requires an integer http_status" in p for p in problems)


# ---------------------------------------------------------------------------
# 9c. Additional source-clearance adversarial branches
# ---------------------------------------------------------------------------


def test_verify_source_clearance_assessment_rejects_unrecognized_rank() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["candidate_rank"] = 99
    problems = verify_source_clearance_assessment_self_consistency(doc)
    assert any("unrecognized candidate_rank" in p for p in problems)


def test_verify_source_clearance_assessment_rejects_tampered_gate_decisions() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["source_use_gate_decisions"]["decisions"]["bulk_bootstrap"] = {
        "outcome": "allowed"
    }
    problems = verify_source_clearance_assessment_self_consistency(doc)
    assert any("source_use_gate_decisions mismatch" in p for p in problems)


# ---------------------------------------------------------------------------
# 9d. Additional field/boatdesign applicability adversarial branches
# ---------------------------------------------------------------------------


def test_validate_field_applicability_no_normalized_candidate_outcome_allows_null() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"][0]["outcome"] = "NO_NORMALIZED_WIKIDATA_CANDIDATE"
    field_doc["candidates"][0]["fields"][0]["wikidata_normalized_candidate"] = None
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence={"candidates": []}
    )
    assert problems == []


def test_validate_field_applicability_rights_blocked_outcome_allows_null_candidate() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][1]["fields"][0]["wikidata_normalized_candidate"] = None
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence={"candidates": []}
    )
    assert problems == []


def test_validate_field_applicability_rejects_null_candidate_on_other_outcomes() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"][0]["wikidata_normalized_candidate"] = None
    # outcome stays SOURCE_VALUE_CONFLICT, which requires a candidate value
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence={"candidates": []}
    )
    assert problems


def test_validate_boatdesign_applicability_rejects_missing_rank() -> None:
    doc = _real_boatdesign_document()
    doc["candidates"] = doc["candidates"][:-1]
    problems = validate_boatdesign_applicability(doc)
    assert problems


def test_validate_boatdesign_applicability_rejects_non_bool_established() -> None:
    doc = _real_boatdesign_document()
    doc["candidates"][0]["generation_boundary_established_for_this_pilot"] = "yes"
    problems = validate_boatdesign_applicability(doc)
    assert any("is not a bool" in p for p in problems)


# ---------------------------------------------------------------------------
# 10. Real retained package end-to-end sanity (no canonical mutation, no
#     network dependency for the module itself)
# ---------------------------------------------------------------------------


def test_module_has_no_network_or_persistence_imports() -> None:
    import hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("import httpx", "import requests", "sqlalchemy", "psycopg"):
        assert forbidden not in source, f"unexpected network/persistence dependency: {forbidden}"


@pytest.mark.skipif(not SL0032_DIR.exists(), reason="retained SLICE-0032 package not present")
def test_retained_package_digest_matches_current_files() -> None:
    import json

    digests_path = SL0032_DIR / "ARTIFACT-DIGESTS.json"
    if not digests_path.exists():
        pytest.skip("ARTIFACT-DIGESTS.json not yet generated")
    artifact_digests = json.loads(digests_path.read_text(encoding="utf-8"))
    assert (
        verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0032_DIR
        )
        == []
    )


@pytest.mark.skipif(not SL0032_DIR.exists(), reason="retained SLICE-0032 package not present")
def test_retained_result_document_top_level_is_applicability_evidence_insufficient() -> None:
    import json

    result_path = SL0032_DIR / "result.json"
    if not result_path.exists():
        pytest.skip("result.json not yet generated")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["top_level_result"] == "APPLICABILITY_EVIDENCE_INSUFFICIENT"
    assert result["successful_rank"] is None
    for row in result["candidates"]:
        assert row["result"] != "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"


def test_fixed_candidate_sequence_is_exact_three_ranks() -> None:
    assert [c.rank for c in FIXED_CANDIDATE_SEQUENCE] == [1, 2, 3]
    assert [c.qid for c in FIXED_CANDIDATE_SEQUENCE] == ["Q104861437", "Q104829866", "Q60521258"]
    assert [c.hullq_id for c in FIXED_CANDIDATE_SEQUENCE] == [
        "BM_WDT0_003ba28d4cd143d68c28e57899a3ed73",
        "BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb",
        "BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60",
    ]
