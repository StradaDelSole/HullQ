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
    FIXED_SR_6_6_CONDITION_IDENTIFIERS,
    MAX_RETRIEVALS_PER_CANDIDATE,
    MAX_TOTAL_RETRIEVALS,
    SOURCE_CLEARANCE_RIGHTS_BLOCKED,
    SOURCE_CLEARANCE_USE_CLEARED,
    SR_6_6_POLICY_REFERENCE,
    AttemptStatus,
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
    validate_attempted_row_identity,
    validate_boatdesign_applicability,
    validate_bounded_scope,
    validate_field_applicability,
    validate_permissions_bounded,
    validate_sequential_stop_invariant,
    validate_source_retrieval_log,
    validate_sr_6_6_condition_set,
    validate_stop_on_first_positive_retrievals,
    verify_artifact_digests_self_consistency,
    verify_fixed_candidate_sequence,
    verify_result_self_consistency,
    verify_source_clearance_assessment_self_consistency,
)

ROOT = Path(__file__).resolve().parents[2]
SL0032_DIR = ROOT / "research" / "stage3" / "sl0032-positive-control-boatdesign-applicability"

A = AttemptStatus.ATTEMPTED
NA = AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS
READY = CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
BLOCKED = CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED
INSUFFICIENT = CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT


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
        "candidate_source_clearance_result": SOURCE_CLEARANCE_USE_CLEARED,
    }


def _blocked_clearance_entry(rank: int) -> dict[str, Any]:
    c = FIXED_CANDIDATE_SEQUENCE[rank - 1]
    return {
        "candidate_rank": rank,
        "qid": c.qid,
        "hullq_id": c.hullq_id,
        "source_located": False,
        "no_source_rationale": "no qualifying source located",
        "candidate_source_clearance_result": SOURCE_CLEARANCE_RIGHTS_BLOCKED,
    }


def _real_clearance_document() -> dict[str, Any]:
    """All three fixed ranks genuinely ATTEMPTED (the real SLICE-0032 result)."""
    return {
        "schema_version": "sl0032-source-clearance-assessment-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            _rank1_clearance_entry(),
            _blocked_clearance_entry(2),
            _blocked_clearance_entry(3),
        ],
    }


ALL_ATTEMPTED_RANKS = frozenset({1, 2, 3})


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


def _real_field_applicability_document(ranks: tuple[int, ...] = (1, 2, 3)) -> dict[str, Any]:
    by_rank = {c.rank: c for c in FIXED_CANDIDATE_SEQUENCE}
    return {
        "schema_version": "sl0032-field-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "allowed_field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "candidates": [
            {
                "candidate_rank": by_rank[r].rank,
                "qid": by_rank[r].qid,
                "hullq_id": by_rank[r].hullq_id,
                "fields": _all_fields("RIGHTS_BLOCKED" if r != 1 else "SOURCE_VALUE_CONFLICT"),
            }
            for r in ranks
        ],
    }


def _real_boatdesign_document(ranks: tuple[int, ...] = (1, 2, 3)) -> dict[str, Any]:
    by_rank = {c.rank: c for c in FIXED_CANDIDATE_SEQUENCE}
    return {
        "schema_version": "sl0032-boatdesign-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            {
                "candidate_rank": by_rank[r].rank,
                "qid": by_rank[r].qid,
                "hullq_id": by_rank[r].hullq_id,
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_UNBOUNDED_SCOPE),
                "findings": "test",
            }
            for r in ranks
        ],
    }


def _retrieval_log_document(retrievals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "sl0032-source-retrieval-log-v1",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "retrieval_ceiling_per_candidate": MAX_RETRIEVALS_PER_CANDIDATE,
        "retrieval_ceiling_total": MAX_TOTAL_RETRIEVALS,
        "retrieval_count": len(retrievals),
        "retrieval_method_note": "test",
        "retrievals": retrievals,
    }


def _real_retrieval_log_document() -> dict[str, Any]:
    return _retrieval_log_document(
        [_valid_retrieval(1, 1), _valid_retrieval(2, 2), _valid_retrieval(3, 3)]
    )


def _real_result_document() -> dict[str, Any]:
    """Mirrors the real retained result.json: all three ranks ATTEMPTED, none READY."""
    by_rank = {c.rank: c for c in FIXED_CANDIDATE_SEQUENCE}
    return {
        "candidates": [
            {
                "candidate_rank": 1,
                "qid": by_rank[1].qid,
                "hullq_id": by_rank[1].hullq_id,
                "attempt_status": "ATTEMPTED",
                "result": "APPLICABILITY_EVIDENCE_INSUFFICIENT",
                "retrieval_count": 1,
            },
            {
                "candidate_rank": 2,
                "qid": by_rank[2].qid,
                "hullq_id": by_rank[2].hullq_id,
                "attempt_status": "ATTEMPTED",
                "result": "RIGHTS_CLEARANCE_BLOCKED",
                "retrieval_count": 1,
            },
            {
                "candidate_rank": 3,
                "qid": by_rank[3].qid,
                "hullq_id": by_rank[3].hullq_id,
                "attempt_status": "ATTEMPTED",
                "result": "RIGHTS_CLEARANCE_BLOCKED",
                "retrieval_count": 1,
            },
        ],
        "top_level_result": "APPLICABILITY_EVIDENCE_INSUFFICIENT",
        "successful_rank": None,
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
    return _retrieval_log_document(retrievals)


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


def test_validate_stop_on_first_positive_retrievals_flags_not_attempted_rank_retrieval() -> None:
    log = _valid_retrieval_log([_valid_retrieval(1, 1), _valid_retrieval(2, 2)])
    problems = validate_stop_on_first_positive_retrievals(log, not_attempted_ranks=frozenset({2}))
    assert problems


def test_validate_stop_on_first_positive_retrievals_passes_when_nothing_not_attempted() -> None:
    log = _valid_retrieval_log(
        [_valid_retrieval(1, 1), _valid_retrieval(2, 2), _valid_retrieval(3, 3)]
    )
    assert validate_stop_on_first_positive_retrievals(log, not_attempted_ranks=frozenset()) == []


# ---------------------------------------------------------------------------
# 3. Source clearance / SR-6.6
# ---------------------------------------------------------------------------


def test_verify_source_clearance_assessment_happy_path() -> None:
    problems = verify_source_clearance_assessment_self_consistency(
        _real_clearance_document(), attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert problems == []


def test_verify_source_clearance_assessment_rejects_wrong_attempted_rank_set() -> None:
    """A clearance document must cover exactly the independently-derived
    attempted-rank set -- neither more nor fewer rows."""
    problems = verify_source_clearance_assessment_self_consistency(
        _real_clearance_document(), attempted_ranks=frozenset({1, 2})
    )
    assert any("rank set" in p for p in problems)


def test_sr_6_6_missing_condition_blocks_clearance() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["sr_6_6_condition_evaluation"]["conditions"][0]["satisfied"] = False
    # tamper: leave the derived flag/clearance as if still satisfied
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
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
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
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
    entry["candidate_source_clearance_result"] = SOURCE_CLEARANCE_USE_CLEARED
    doc = _real_clearance_document()
    doc["candidates"][1] = entry
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert problems


def test_candidate_source_cleared() -> None:
    assert candidate_source_cleared(_rank1_clearance_entry()) is True
    assert candidate_source_cleared(_blocked_clearance_entry(2)) is False


# ---------------------------------------------------------------------------
# 3b. Pinned exact SR-6.6 condition set (Finding 1, review 5058020519)
# ---------------------------------------------------------------------------


def test_validate_sr_6_6_condition_set_all_six_present_passes() -> None:
    assert validate_sr_6_6_condition_set(_satisfied_conditions()) == []
    assert len(FIXED_SR_6_6_CONDITION_IDENTIFIERS) == 6


def test_validate_sr_6_6_condition_set_rejects_missing_condition() -> None:
    conditions = _satisfied_conditions()[:-1]  # remove one of the six
    problems = validate_sr_6_6_condition_set(conditions)
    assert any("missing required identifiers" in p for p in problems)
    assert sr_6_6_conditions_satisfied(conditions) is False


def test_validate_sr_6_6_condition_set_rejects_renamed_condition() -> None:
    conditions = _satisfied_conditions()
    conditions[0]["condition"] = "lawfully_publicly_accessible_renamed"
    problems = validate_sr_6_6_condition_set(conditions)
    assert any("missing required identifiers" in p for p in problems)
    assert any("non-normative identifiers" in p for p in problems)
    assert sr_6_6_conditions_satisfied(conditions) is False


def test_validate_sr_6_6_condition_set_rejects_duplicate_condition() -> None:
    conditions = _satisfied_conditions()
    conditions.append(dict(conditions[0]))  # duplicate one of the six -> 7 rows
    problems = validate_sr_6_6_condition_set(conditions)
    assert any("duplicated normative identifiers" in p for p in problems)
    assert sr_6_6_conditions_satisfied(conditions) is False


def test_validate_sr_6_6_condition_set_rejects_seventh_arbitrary_condition() -> None:
    conditions = _satisfied_conditions()
    conditions.append({"condition": "invented_condition", "satisfied": True, "evidence": "e"})
    problems = validate_sr_6_6_condition_set(conditions)
    assert any("non-normative identifiers" in p for p in problems)
    assert sr_6_6_conditions_satisfied(conditions) is False


def test_validate_sr_6_6_condition_set_rejects_all_six_replaced_by_one_invented() -> None:
    conditions = [{"condition": "invented_condition", "satisfied": True, "evidence": "e"}]
    problems = validate_sr_6_6_condition_set(conditions)
    assert any("missing required identifiers" in p for p in problems)
    assert any("non-normative identifiers" in p for p in problems)
    assert sr_6_6_conditions_satisfied(conditions) is False


def test_sr_6_6_policy_reference_tamper_fails_verification() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["sr_6_6_condition_evaluation"]["policy_reference"] = (
        "specs/SOME_OTHER_POLICY.md#1.1"
    )
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("policy_reference" in p for p in problems)
    assert SR_6_6_POLICY_REFERENCE == "specs/SOURCE_RIGHTS_POLICY.v0.1.md#6.6"


def test_invented_condition_set_cannot_mechanically_derive_positive_clearance() -> None:
    """The exact defect described by the independent review: an artifact
    substituting an invented single condition for the fixed six must never
    mechanically derive an 'allowed' identity_seed/production_value
    clearance."""
    invented_conditions = [{"condition": "invented_condition", "satisfied": True, "evidence": "e"}]
    assert derive_sr_6_6_use_clearance(invented_conditions) == "conditional"

    doc = _real_clearance_document()
    doc["candidates"][0]["sr_6_6_condition_evaluation"]["conditions"] = invented_conditions
    doc["candidates"][0]["sr_6_6_condition_evaluation"][
        "conditions_satisfied_for_bounded_manual_use"
    ] = True
    # clearance still says 'allowed' -- tampered, must be caught
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert problems


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
    problems = validate_boatdesign_applicability(
        _real_boatdesign_document(), attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert problems == []


def test_validate_boatdesign_applicability_rejects_established_true_with_unbounded_scope() -> None:
    doc = _real_boatdesign_document()
    doc["candidates"][0]["generation_boundary_established_for_this_pilot"] = True
    # scope left unknown_or_unbounded=True -- inconsistent
    problems = validate_boatdesign_applicability(doc, attempted_ranks=ALL_ATTEMPTED_RANKS)
    assert problems


def test_validate_boatdesign_applicability_rejects_wrong_attempted_rank_set() -> None:
    doc = _real_boatdesign_document()
    problems = validate_boatdesign_applicability(doc, attempted_ranks=frozenset({1, 2}))
    assert problems


def test_validate_field_applicability_happy_path() -> None:
    field_doc = _real_field_applicability_document()
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
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence=evidence_doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert problems == []


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
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence=evidence_doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert problems


def test_validate_field_applicability_rejects_missing_field_pointer() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"] = field_doc["candidates"][0]["fields"][:-1]
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert any("field pointer coverage" in p for p in problems)


def test_validate_field_applicability_safe_requires_bounded_scope() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"][0]["outcome"] = "SAFE_FOR_LATER_DESIGN_PROMOTION"
    # applicability_scope still unbounded -- must be rejected
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert problems


def test_validate_field_applicability_rejects_wrong_attempted_rank_set() -> None:
    field_doc = _real_field_applicability_document()
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=frozenset({1, 2}),
    )
    assert any("rank set" in p for p in problems)


# ---------------------------------------------------------------------------
# 5b. Duplicate-row / fixed-identity pinning (Finding 3, review 5058020519)
# ---------------------------------------------------------------------------


def test_validate_attempted_row_identity_happy_path() -> None:
    problems, rows_by_rank = validate_attempted_row_identity(
        _real_clearance_document()["candidates"]
    )
    assert problems == []
    assert set(rows_by_rank) == {1, 2, 3}


def test_validate_attempted_row_identity_rejects_duplicate_rank() -> None:
    rows = [_rank1_clearance_entry(), dict(_rank1_clearance_entry())]
    problems, rows_by_rank = validate_attempted_row_identity(rows)
    assert any("duplicate row for candidate_rank 1" in p for p in problems)
    assert set(rows_by_rank) == {1}


def test_validate_attempted_row_identity_rejects_wrong_qid() -> None:
    row = dict(_rank1_clearance_entry())
    row["qid"] = "Q999999"
    problems, rows_by_rank = validate_attempted_row_identity([row])
    assert any("qid" in p and "!= fixed" in p for p in problems)
    assert (
        1 not in rows_by_rank or rows_by_rank[1]["qid"] == "Q999999"
    )  # row still returned, flagged


def test_validate_attempted_row_identity_rejects_wrong_hullq_id() -> None:
    row = dict(_rank1_clearance_entry())
    row["hullq_id"] = "BM_WDT0_WRONG"
    problems, _rows_by_rank = validate_attempted_row_identity([row])
    assert any("hullq_id" in p and "!= fixed" in p for p in problems)


def test_duplicate_rank1_source_clearance_rows_fail() -> None:
    doc = _real_clearance_document()
    doc["candidates"].append(dict(_rank1_clearance_entry()))  # duplicate rank 1
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("duplicate row for candidate_rank 1" in p for p in problems)


def test_duplicate_rank1_field_applicability_rows_fail() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"].append(dict(field_doc["candidates"][0]))  # duplicate rank 1
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert any("duplicate row for candidate_rank 1" in p for p in problems)


def test_duplicate_rank1_boatdesign_applicability_rows_fail() -> None:
    boatdesign_doc = _real_boatdesign_document()
    boatdesign_doc["candidates"].append(dict(boatdesign_doc["candidates"][0]))  # duplicate rank 1
    problems = validate_boatdesign_applicability(
        boatdesign_doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("duplicate row for candidate_rank 1" in p for p in problems)


def test_correct_rank_wrong_qid_fails_source_clearance() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["qid"] = "Q1"  # wrong QID, rank still 1
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("qid" in p and "!= fixed" in p for p in problems)


def test_correct_rank_qid_wrong_hullq_id_fails_source_clearance() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["hullq_id"] = "BM_WDT0_WRONG"
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("hullq_id" in p and "!= fixed" in p for p in problems)


def test_correct_rank_wrong_qid_fails_field_applicability() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["qid"] = "Q1"
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert any("qid" in p and "!= fixed" in p for p in problems)


def test_correct_rank_wrong_hullq_id_fails_boatdesign_applicability() -> None:
    boatdesign_doc = _real_boatdesign_document()
    boatdesign_doc["candidates"][0]["hullq_id"] = "BM_WDT0_WRONG"
    problems = validate_boatdesign_applicability(
        boatdesign_doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("hullq_id" in p and "!= fixed" in p for p in problems)


def test_positive_stop_path_duplicate_row_within_single_attempted_rank_fails() -> None:
    """Positive-stop path (only rank 1 attempted, READY): a duplicate rank-1
    row in field_applicability.json must still fail even though there is
    only one attempted rank total."""
    field_doc = _ready_field_doc_for_rank(1)
    field_doc["candidates"].append(dict(field_doc["candidates"][0]))
    problems = validate_field_applicability(
        field_doc, corrected_candidate_evidence={"candidates": []}, attempted_ranks=frozenset({1})
    )
    assert any("duplicate row for candidate_rank 1" in p for p in problems)


def test_positive_stop_path_wrong_identity_on_two_attempted_ranks_fails() -> None:
    """Positive-stop path (ranks 1 and 2 attempted, rank 2 READY): a wrong
    QID on the rank-1 boatdesign-applicability row must still be caught."""
    boatdesign_doc = {
        "schema_version": "sl0032-boatdesign-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            {
                "candidate_rank": 1,
                "qid": "Q1",  # wrong -- should be FIXED_CANDIDATE_SEQUENCE[0].qid
                "hullq_id": FIXED_CANDIDATE_SEQUENCE[0].hullq_id,
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_UNBOUNDED_SCOPE),
                "findings": "test",
            },
            _ready_boatdesign_doc_for_rank(2)["candidates"][0],
        ],
    }
    problems = validate_boatdesign_applicability(boatdesign_doc, attempted_ranks=frozenset({1, 2}))
    assert any("qid" in p and "!= fixed" in p for p in problems)


def test_real_all_three_attempted_package_remains_valid_under_identity_pinning() -> None:
    """The existing real all-three-attempted retained-package fixtures must
    remain valid under the strengthened duplicate/identity checks."""
    assert (
        validate_field_applicability(
            _real_field_applicability_document(),
            corrected_candidate_evidence={
                "candidates": [
                    {
                        "candidate_rank": c.rank,
                        "fields": [
                            {
                                "field_pointer": p,
                                "normalized_candidate": {"value": "1.0", "unit": "m"},
                            }
                            for p in sorted(ALLOWED_FIELD_POINTERS)
                        ],
                    }
                    for c in FIXED_CANDIDATE_SEQUENCE
                ]
            },
            attempted_ranks=ALL_ATTEMPTED_RANKS,
        )
        == []
    )
    assert (
        validate_boatdesign_applicability(
            _real_boatdesign_document(), attempted_ranks=ALL_ATTEMPTED_RANKS
        )
        == []
    )
    assert (
        verify_source_clearance_assessment_self_consistency(
            _real_clearance_document(), attempted_ranks=ALL_ATTEMPTED_RANKS
        )
        == []
    )


# ---------------------------------------------------------------------------
# 6. Candidate-level / top-level result derivation
# ---------------------------------------------------------------------------


def _mismatched_bounded_year_scope() -> dict[str, Any]:
    """A second, independently-bounded year scope that does NOT equal
    ``_bounded_year_scope()`` -- used to prove two independently-bounded
    scopes are never treated as "the same scope" merely because both are
    bounded."""
    scope = dict(_UNBOUNDED_SCOPE)
    scope.update(first_year=2002, last_year=2005, unknown_or_unbounded=False)
    return scope


def _bounded_named_variant_scope(hint: str) -> dict[str, Any]:
    scope = dict(_UNBOUNDED_SCOPE)
    scope.update(named_variant_hint=hint, unknown_or_unbounded=False)
    return scope


def test_compute_candidate_result_rights_blocked_wins_regardless_of_evidence() -> None:
    result = compute_candidate_result(
        source_cleared=False,
        boatdesign_applicability_scope=_bounded_year_scope(),
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()),
    )
    assert result == BLOCKED


def test_compute_candidate_result_ready_requires_bounded_generation_and_safe_field() -> None:
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=_bounded_year_scope(),
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()),
    )
    assert result == READY


def test_compute_candidate_result_same_scope_contributes_to_ready() -> None:
    """CASE SAME-SCOPE (required by independent review): a bounded BoatDesign
    scope plus a SAFE field with an IDENTICAL bounded scope may contribute to
    READY."""
    scope = _bounded_year_scope()
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=scope,
        field_outcomes=[
            _field(
                "/baseline/dimensions/loa_m", "SAFE_FOR_LATER_DESIGN_PROMOTION", scope=dict(scope)
            )
        ],
    )
    assert result == READY


def test_compute_candidate_result_mismatched_year_scope_cannot_be_ready() -> None:
    """CASE MISMATCH (required by independent review): a bounded BoatDesign
    scope (1998-2001) and a SAFE field with a DIFFERENT bounded scope
    (2002-2005) must NOT produce READY -- both are independently bounded,
    but they are not the same scope."""
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=_bounded_year_scope(),
        field_outcomes=_all_fields(
            "SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_mismatched_bounded_year_scope()
        ),
    )
    assert result == INSUFFICIENT


def test_compute_candidate_result_mismatched_named_variant_scope_cannot_be_ready() -> None:
    """Mismatch on a non-year applicability dimension (named variant/design
    option) must also block READY, not only a year-range mismatch."""
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=_bounded_named_variant_scope("Mk I"),
        field_outcomes=_all_fields(
            "SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_named_variant_scope("Mk II")
        ),
    )
    assert result == INSUFFICIENT


def test_compute_candidate_result_equality_alone_cannot_be_ready() -> None:
    """Even if a field is (incorrectly) marked SAFE_FOR_LATER_DESIGN_PROMOTION
    from mere numeric equality, an unbounded scope on that field still blocks
    READY -- the equality rule's guardrail."""
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=_bounded_year_scope(),
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=dict(_UNBOUNDED_SCOPE)),
    )
    assert result == INSUFFICIENT


def test_compute_candidate_result_option_sensitive_cannot_be_flattened_to_safe() -> None:
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=_bounded_year_scope(),
        field_outcomes=_all_fields("OPTION_SENSITIVE", scope=_bounded_year_scope()),
    )
    assert result == INSUFFICIENT


def test_compute_candidate_result_requires_generation_boundary_even_with_safe_field() -> None:
    result = compute_candidate_result(
        source_cleared=True,
        boatdesign_applicability_scope=dict(_UNBOUNDED_SCOPE),
        field_outcomes=_all_fields("SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()),
    )
    assert result == INSUFFICIENT


def test_candidate_outcome_has_exactly_three_members() -> None:
    """CandidateOutcome must never grow a fourth 'not attempted' member --
    attempt status is a wholly separate concept (AttemptStatus)."""
    assert {member.value for member in CandidateOutcome} == {
        "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "RIGHTS_CLEARANCE_BLOCKED",
        "APPLICABILITY_EVIDENCE_INSUFFICIENT",
    }
    assert {member.value for member in AttemptStatus} == {
        "ATTEMPTED",
        "NOT_ATTEMPTED_AFTER_SUCCESS",
    }


def test_compute_top_level_result_first_ready_rank_wins() -> None:
    attempted = [(1, INSUFFICIENT), (2, READY)]
    assert (
        compute_top_level_result(attempted)
        == TopLevelResult.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
    )


def test_compute_top_level_result_insufficient_when_one_cleared_but_none_ready() -> None:
    attempted = [(1, BLOCKED), (2, INSUFFICIENT), (3, BLOCKED)]
    assert compute_top_level_result(attempted) == TopLevelResult.APPLICABILITY_EVIDENCE_INSUFFICIENT


def test_compute_top_level_result_rights_blocked_only_when_all_blocked() -> None:
    attempted = [(1, BLOCKED), (2, BLOCKED), (3, BLOCKED)]
    assert compute_top_level_result(attempted) == TopLevelResult.RIGHTS_CLEARANCE_BLOCKED


# ---------------------------------------------------------------------------
# 7. Sequential stop-on-first-positive invariant (attempt_status + result)
# ---------------------------------------------------------------------------


def test_sequential_invariant_candidate_2_cannot_be_attempted_after_1_ready() -> None:
    entries = [(1, A, READY), (2, A, INSUFFICIENT)]
    problems = validate_sequential_stop_invariant(entries)
    assert any("must have attempt_status=NOT_ATTEMPTED_AFTER_SUCCESS" in p for p in problems)


def test_sequential_invariant_candidate_3_cannot_be_attempted_after_1_or_2_ready() -> None:
    entries = [(1, A, BLOCKED), (2, A, READY), (3, A, BLOCKED)]
    problems = validate_sequential_stop_invariant(entries)
    assert any("must have attempt_status=NOT_ATTEMPTED_AFTER_SUCCESS" in p for p in problems)


def test_sequential_invariant_candidate_2_permitted_after_1_blocked_or_insufficient() -> None:
    for first_result in (BLOCKED, INSUFFICIENT):
        entries = [(1, A, first_result), (2, A, BLOCKED), (3, A, BLOCKED)]
        assert validate_sequential_stop_invariant(entries) == []


def test_sequential_invariant_not_attempted_marker_requires_earlier_ready() -> None:
    entries = [(1, A, INSUFFICIENT), (2, NA, None)]
    problems = validate_sequential_stop_invariant(entries)
    assert any("no earlier rank reached READY" in p for p in problems)


def test_sequential_invariant_correct_stop_after_ready() -> None:
    entries = [(1, A, INSUFFICIENT), (2, A, READY), (3, NA, None)]
    assert validate_sequential_stop_invariant(entries) == []


def test_sequential_invariant_attempted_row_requires_non_null_result() -> None:
    entries = [(1, A, None)]
    problems = validate_sequential_stop_invariant(entries)
    assert any("attempt_status=ATTEMPTED requires a non-null result" in p for p in problems)


def test_sequential_invariant_not_attempted_row_requires_null_result() -> None:
    """NOT_ATTEMPTED_AFTER_SUCCESS is never a fourth candidate result -- a row
    claiming it while also carrying a real CandidateOutcome is a tamper."""
    entries = [(1, A, READY), (2, NA, BLOCKED)]
    problems = validate_sequential_stop_invariant(entries)
    assert any(
        "NOT_ATTEMPTED_AFTER_SUCCESS is not a fourth candidate result" in p for p in problems
    )


# ---------------------------------------------------------------------------
# 8. result.json cross-document self-consistency (real negative result +
#    Case A / Case B positive-path scenarios required by independent review)
# ---------------------------------------------------------------------------


def test_verify_result_self_consistency_real_negative_result() -> None:
    problems = verify_result_self_consistency(
        _real_result_document(),
        field_applicability_document=_real_field_applicability_document(),
        boatdesign_applicability_document=_real_boatdesign_document(),
        source_clearance_document=_real_clearance_document(),
        source_retrieval_log_document=_real_retrieval_log_document(),
    )
    assert problems == []


def test_verify_result_self_consistency_rejects_tampered_top_level_result() -> None:
    result_doc = _real_result_document()
    result_doc["top_level_result"] = "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"  # tampered
    result_doc["successful_rank"] = 1
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=_real_field_applicability_document(),
        boatdesign_applicability_document=_real_boatdesign_document(),
        source_clearance_document=_real_clearance_document(),
        source_retrieval_log_document=_real_retrieval_log_document(),
    )
    assert problems


def test_verify_result_self_consistency_rejects_successful_rank_without_ready() -> None:
    result_doc = _real_result_document()
    result_doc["successful_rank"] = 1  # tampered -- no rank is READY
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=_real_field_applicability_document(),
        boatdesign_applicability_document=_real_boatdesign_document(),
        source_clearance_document=_real_clearance_document(),
        source_retrieval_log_document=_real_retrieval_log_document(),
    )
    assert problems


def _ready_field_doc_for_rank(rank: int) -> dict[str, Any]:
    c = next(c for c in FIXED_CANDIDATE_SEQUENCE if c.rank == rank)
    return {
        "schema_version": "sl0032-field-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "allowed_field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "candidates": [
            {
                "candidate_rank": c.rank,
                "qid": c.qid,
                "hullq_id": c.hullq_id,
                "fields": _all_fields(
                    "SAFE_FOR_LATER_DESIGN_PROMOTION", scope=_bounded_year_scope()
                ),
            }
        ],
    }


def _ready_boatdesign_doc_for_rank(rank: int) -> dict[str, Any]:
    c = next(c for c in FIXED_CANDIDATE_SEQUENCE if c.rank == rank)
    return {
        "schema_version": "sl0032-boatdesign-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            {
                "candidate_rank": c.rank,
                "qid": c.qid,
                "hullq_id": c.hullq_id,
                "generation_boundary_established_for_this_pilot": True,
                "applicability_scope": _bounded_year_scope(),
                "findings": "test",
            }
        ],
    }


def _ready_clearance_doc_for_rank(rank: int) -> dict[str, Any]:
    entry = dict(_rank1_clearance_entry())
    c = next(c for c in FIXED_CANDIDATE_SEQUENCE if c.rank == rank)
    entry["candidate_rank"] = rank
    entry["qid"] = c.qid
    entry["hullq_id"] = c.hullq_id
    entry["bounded_scope"] = {
        "hullq_ids": [c.hullq_id],
        "qids": [c.qid],
        "field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "use_kinds": ["identity_seed", "production_value"],
        "note": "test",
    }
    return {
        "schema_version": "sl0032-source-clearance-assessment-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [entry],
    }


def _not_attempted_row(rank: int) -> dict[str, Any]:
    c = next(c for c in FIXED_CANDIDATE_SEQUENCE if c.rank == rank)
    return {
        "candidate_rank": rank,
        "qid": c.qid,
        "hullq_id": c.hullq_id,
        "attempt_status": "NOT_ATTEMPTED_AFTER_SUCCESS",
        "result": None,
        "retrieval_count": 0,
    }


def _attempted_row(rank: int, result: str, retrieval_count: int) -> dict[str, Any]:
    c = next(c for c in FIXED_CANDIDATE_SEQUENCE if c.rank == rank)
    return {
        "candidate_rank": rank,
        "qid": c.qid,
        "hullq_id": c.hullq_id,
        "attempt_status": "ATTEMPTED",
        "result": result,
        "retrieval_count": retrieval_count,
    }


def test_case_a_rank1_ready_ranks_2_and_3_not_attempted() -> None:
    """CASE A (required by independent review): rank 1 = READY, ranks 2/3 =
    NOT_ATTEMPTED_AFTER_SUCCESS. Zero retrievals for ranks 2/3, no
    attempted-only evidence for ranks 2/3, top-level READY rank 1."""
    result_doc = {
        "candidates": [
            _attempted_row(1, "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT", 4),
            _not_attempted_row(2),
            _not_attempted_row(3),
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "successful_rank": 1,
    }
    retrieval_log = _retrieval_log_document([_valid_retrieval(i, 1) for i in range(1, 5)])
    field_doc = _ready_field_doc_for_rank(1)
    boatdesign_doc = _ready_boatdesign_doc_for_rank(1)
    clearance_doc = _ready_clearance_doc_for_rank(1)

    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=field_doc,
        boatdesign_applicability_document=boatdesign_doc,
        source_clearance_document=clearance_doc,
        source_retrieval_log_document=retrieval_log,
    )
    assert problems == []

    # zero retrievals for ranks 2/3
    assert all(r["candidate_rank"] == 1 for r in retrieval_log["retrievals"])
    # no attempted-only evidence for ranks 2/3
    assert {row["candidate_rank"] for row in field_doc["candidates"]} == {1}
    assert {row["candidate_rank"] for row in boatdesign_doc["candidates"]} == {1}
    assert {row["candidate_rank"] for row in clearance_doc["candidates"]} == {1}
    # top-level READY rank 1
    assert result_doc["top_level_result"] == "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
    assert result_doc["successful_rank"] == 1


def test_case_a_later_result_cannot_be_injected_into_not_attempted_rank() -> None:
    result_doc = {
        "candidates": [
            _attempted_row(1, "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT", 4),
            _not_attempted_row(2),
            _not_attempted_row(3),
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "successful_rank": 1,
    }
    # tamper: inject a result value into a NOT_ATTEMPTED_AFTER_SUCCESS row
    result_doc["candidates"][1]["result"] = "RIGHTS_CLEARANCE_BLOCKED"
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=_ready_field_doc_for_rank(1),
        boatdesign_applicability_document=_ready_boatdesign_doc_for_rank(1),
        source_clearance_document=_ready_clearance_doc_for_rank(1),
        source_retrieval_log_document=_retrieval_log_document(
            [_valid_retrieval(i, 1) for i in range(1, 5)]
        ),
    )
    assert problems


def test_case_b_rank1_blocked_rank2_ready_rank3_not_attempted() -> None:
    """CASE B (required by independent review): rank 1 = RIGHTS_CLEARANCE_BLOCKED
    or APPLICABILITY_EVIDENCE_INSUFFICIENT, rank 2 = READY, rank 3 =
    NOT_ATTEMPTED_AFTER_SUCCESS. Rank 3 has zero retrievals, carries no
    attempted-only evidence/result, top-level READY rank 2."""
    result_doc = {
        "candidates": [
            _attempted_row(1, "RIGHTS_CLEARANCE_BLOCKED", 2),
            _attempted_row(2, "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT", 3),
            _not_attempted_row(3),
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "successful_rank": 2,
    }
    retrieval_log = _retrieval_log_document(
        [
            _valid_retrieval(1, 1),
            _valid_retrieval(2, 1),
            _valid_retrieval(3, 2),
            _valid_retrieval(4, 2),
            _valid_retrieval(5, 2),
        ]
    )
    field_doc = {
        "schema_version": "sl0032-field-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "allowed_field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "candidates": [
            _ready_field_doc_for_rank(2)["candidates"][0],
        ],
    }
    field_doc["candidates"].insert(
        0,
        {
            "candidate_rank": 1,
            "qid": FIXED_CANDIDATE_SEQUENCE[0].qid,
            "hullq_id": FIXED_CANDIDATE_SEQUENCE[0].hullq_id,
            "fields": _all_fields("RIGHTS_BLOCKED"),
        },
    )
    boatdesign_doc = {
        "schema_version": "sl0032-boatdesign-applicability-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            {
                "candidate_rank": 1,
                "qid": FIXED_CANDIDATE_SEQUENCE[0].qid,
                "hullq_id": FIXED_CANDIDATE_SEQUENCE[0].hullq_id,
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_UNBOUNDED_SCOPE),
                "findings": "test",
            },
            _ready_boatdesign_doc_for_rank(2)["candidates"][0],
        ],
    }
    clearance_doc = {
        "schema_version": "sl0032-source-clearance-assessment-v2",
        "generated_at": "2026-08-28T00:00:00+00:00",
        "candidates": [
            _blocked_clearance_entry(1),
            _ready_clearance_doc_for_rank(2)["candidates"][0],
        ],
    }

    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=field_doc,
        boatdesign_applicability_document=boatdesign_doc,
        source_clearance_document=clearance_doc,
        source_retrieval_log_document=retrieval_log,
    )
    assert problems == []

    # rank 3 has zero retrievals
    assert all(r["candidate_rank"] != 3 for r in retrieval_log["retrievals"])
    # rank 3 cannot carry attempted-only evidence/result
    assert 3 not in {row["candidate_rank"] for row in field_doc["candidates"]}
    assert 3 not in {row["candidate_rank"] for row in boatdesign_doc["candidates"]}
    assert 3 not in {row["candidate_rank"] for row in clearance_doc["candidates"]}
    # top-level READY rank 2
    assert result_doc["top_level_result"] == "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
    assert result_doc["successful_rank"] == 2


# ---------------------------------------------------------------------------
# 8b. Tamper tests required by independent review
# ---------------------------------------------------------------------------


def test_tamper_artifact_cannot_mark_later_rank_attempted_after_earlier_ready() -> None:
    result_doc = {
        "candidates": [
            _attempted_row(1, "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT", 4),
            _attempted_row(2, "RIGHTS_CLEARANCE_BLOCKED", 1),  # tampered: should be NOT_ATTEMPTED
            _not_attempted_row(3),
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "successful_rank": 1,
    }
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=_ready_field_doc_for_rank(1),
        boatdesign_applicability_document=_ready_boatdesign_doc_for_rank(1),
        source_clearance_document=_ready_clearance_doc_for_rank(1),
        source_retrieval_log_document=_retrieval_log_document(
            [_valid_retrieval(i, 1) for i in range(1, 5)]
        ),
    )
    assert problems


def test_tamper_artifact_cannot_add_later_retrieval_after_ready() -> None:
    result_doc = {
        "candidates": [
            _attempted_row(1, "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT", 4),
            _not_attempted_row(2),
            _not_attempted_row(3),
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "successful_rank": 1,
    }
    # tamper: a retrieval targets rank 2, which is NOT_ATTEMPTED_AFTER_SUCCESS
    retrieval_log = _retrieval_log_document(
        [_valid_retrieval(i, 1) for i in range(1, 5)] + [_valid_retrieval(5, 2)]
    )
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=_ready_field_doc_for_rank(1),
        boatdesign_applicability_document=_ready_boatdesign_doc_for_rank(1),
        source_clearance_document=_ready_clearance_doc_for_rank(1),
        source_retrieval_log_document=retrieval_log,
    )
    assert problems


def test_tamper_artifact_cannot_attach_evidence_to_not_attempted_rank() -> None:
    result_doc = {
        "candidates": [
            _attempted_row(1, "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT", 4),
            _not_attempted_row(2),
            _not_attempted_row(3),
        ],
        "top_level_result": "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT",
        "successful_rank": 1,
    }
    # tamper: field_applicability.json carries a row for the NOT_ATTEMPTED rank 2
    field_doc = _ready_field_doc_for_rank(1)
    field_doc["candidates"].append(
        {
            "candidate_rank": 2,
            "qid": FIXED_CANDIDATE_SEQUENCE[1].qid,
            "hullq_id": FIXED_CANDIDATE_SEQUENCE[1].hullq_id,
            "fields": _all_fields("RIGHTS_BLOCKED"),
        }
    )
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=field_doc,
        boatdesign_applicability_document=_ready_boatdesign_doc_for_rank(1),
        source_clearance_document=_ready_clearance_doc_for_rank(1),
        source_retrieval_log_document=_retrieval_log_document(
            [_valid_retrieval(i, 1) for i in range(1, 5)]
        ),
    )
    assert problems


def test_tamper_not_attempted_cannot_be_used_as_fourth_candidate_result() -> None:
    """result.json's own per-row 'result' field must never literally be the
    string 'NOT_ATTEMPTED_AFTER_SUCCESS' -- that is an attempt_status value,
    never a CandidateOutcome. An ATTEMPTED row asserting it fails the
    sequential-invariant recomputation (invalid CandidateOutcome)."""
    result_doc = _real_result_document()
    result_doc["candidates"][1]["result"] = "NOT_ATTEMPTED_AFTER_SUCCESS"
    problems = verify_result_self_consistency(
        result_doc,
        field_applicability_document=_real_field_applicability_document(),
        boatdesign_applicability_document=_real_boatdesign_document(),
        source_clearance_document=_real_clearance_document(),
        source_retrieval_log_document=_real_retrieval_log_document(),
    )
    assert problems
    assert "NOT_ATTEMPTED_AFTER_SUCCESS" not in {member.value for member in CandidateOutcome}


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
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("unrecognized candidate_rank" in p for p in problems)


def test_verify_source_clearance_assessment_rejects_tampered_gate_decisions() -> None:
    doc = _real_clearance_document()
    doc["candidates"][0]["source_use_gate_decisions"]["decisions"]["bulk_bootstrap"] = {
        "outcome": "allowed"
    }
    problems = verify_source_clearance_assessment_self_consistency(
        doc, attempted_ranks=ALL_ATTEMPTED_RANKS
    )
    assert any("source_use_gate_decisions mismatch" in p for p in problems)


# ---------------------------------------------------------------------------
# 9d. Additional field/boatdesign applicability adversarial branches
# ---------------------------------------------------------------------------


def test_validate_field_applicability_no_normalized_candidate_outcome_allows_null() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"][0]["outcome"] = "NO_NORMALIZED_WIKIDATA_CANDIDATE"
    field_doc["candidates"][0]["fields"][0]["wikidata_normalized_candidate"] = None
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert problems == []


def test_validate_field_applicability_rights_blocked_outcome_allows_null_candidate() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][1]["fields"][0]["wikidata_normalized_candidate"] = None
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert problems == []


def test_validate_field_applicability_rejects_null_candidate_on_other_outcomes() -> None:
    field_doc = _real_field_applicability_document()
    field_doc["candidates"][0]["fields"][0]["wikidata_normalized_candidate"] = None
    # outcome stays SOURCE_VALUE_CONFLICT, which requires a candidate value
    problems = validate_field_applicability(
        field_doc,
        corrected_candidate_evidence={"candidates": []},
        attempted_ranks=ALL_ATTEMPTED_RANKS,
    )
    assert problems


def test_validate_boatdesign_applicability_rejects_missing_rank() -> None:
    doc = _real_boatdesign_document()
    doc["candidates"] = doc["candidates"][:-1]
    problems = validate_boatdesign_applicability(doc, attempted_ranks=ALL_ATTEMPTED_RANKS)
    assert problems


def test_validate_boatdesign_applicability_rejects_non_bool_established() -> None:
    doc = _real_boatdesign_document()
    doc["candidates"][0]["generation_boundary_established_for_this_pilot"] = "yes"
    problems = validate_boatdesign_applicability(doc, attempted_ranks=ALL_ATTEMPTED_RANKS)
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
        assert row["attempt_status"] == "ATTEMPTED"
        assert row["result"] != "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
        assert row["retrieval_count"] >= 1


@pytest.mark.skipif(not SL0032_DIR.exists(), reason="retained SLICE-0032 package not present")
def test_retained_source_clearance_evidence_contains_no_false_page_count_or_copyright_claim() -> (
    None
):
    """Regression guard for the independent-review Finding 1 correction:
    the retained rank-1 SR-6.6 evidence must never again claim the site is
    'exactly four pages' or that the pages carry no copyright notice --
    both were observed to be false."""
    clearance_path = SL0032_DIR / "source_clearance_assessment.json"
    if not clearance_path.exists():
        pytest.skip("source_clearance_assessment.json not yet generated")
    text = clearance_path.read_text(encoding="utf-8")
    assert "exactly four pages" not in text
    assert "no copyright" not in text.lower()
    assert "&copy; Buzzards Bay Boat Shop" in text


def test_fixed_candidate_sequence_is_exact_three_ranks() -> None:
    assert [c.rank for c in FIXED_CANDIDATE_SEQUENCE] == [1, 2, 3]
    assert [c.qid for c in FIXED_CANDIDATE_SEQUENCE] == ["Q104861437", "Q104829866", "Q60521258"]
    assert [c.hullq_id for c in FIXED_CANDIDATE_SEQUENCE] == [
        "BM_WDT0_003ba28d4cd143d68c28e57899a3ed73",
        "BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb",
        "BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60",
    ]
