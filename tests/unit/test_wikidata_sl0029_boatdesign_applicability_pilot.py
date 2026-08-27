"""Unit tests for the SLICE-0029 primary-source BoatDesign applicability pilot pure logic."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0029_boatdesign_applicability_pilot import (
    ALLOWED_FIELD_POINTERS,
    BOUNDED_ONLY_PERMISSION_KEYS,
    FIXED_QIDS,
    RETRIEVAL_CEILING,
    SR_6_6_DEFAULT_CLEARANCE,
    SR_6_6_GATED_USES,
    SR_6_6_SATISFIED_CLEARANCE,
    ApplicabilityOutcome,
    IdentityBoundaryIntegrityError,
    RecommendationCode,
    build_artifact_digests,
    build_pilot_identity_boundary,
    compute_recommendation,
    derive_sr_6_6_use_clearance,
    evaluate_source_use_gate,
    retained_package_filenames,
    source_use_allowed,
    validate_applicability_scope_invariant,
    validate_boatdesign_applicability,
    validate_bounded_scope,
    validate_permissions_bounded,
    validate_source_retrieval_log,
    validate_wikidata_candidate_applicability,
    verify_artifact_digests_self_consistency,
    verify_pilot_identity_boundary_self_consistency,
    verify_source_clearance_assessment_self_consistency,
)

ROOT = Path(__file__).resolve().parents[2]
SL0029_DIR = ROOT / "research" / "stage3" / "sl0029-primary-source-boatdesign-applicability"
SL0028_DIR = ROOT / "research" / "stage3" / "sl0028-wikidata-tier1-full-boundary"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _minimal_linkage_document() -> dict[str, Any]:
    return {
        "identity_boundary": {
            "canonical_boat_model_count": 1770,
            "historical_crosswalk_count": 1772,
        },
        "boat_models": [
            {
                "hullq_id": "BM_TEST_22",
                "qids": ["Q5051252"],
                "preferred_label_by_qid": {"Q5051252": "Catalina 22"},
            },
            {
                "hullq_id": "BM_TEST_30",
                "qids": ["Q5051253"],
                "preferred_label_by_qid": {"Q5051253": "Catalina 30"},
            },
            {
                "hullq_id": "BM_TEST_OTHER",
                "qids": ["Q999999"],
                "preferred_label_by_qid": {"Q999999": "Some Other Boat"},
            },
        ],
    }


def _minimal_overlap_result() -> dict[str, Any]:
    return {
        "exact_overlap": [
            {
                "manufacturer_sample": "Catalina Yachts",
                "probe_model_name": "Catalina 22",
                "accepted_matches": [{"qid": "Q5051252"}],
            },
            {
                "manufacturer_sample": "Catalina Yachts",
                "probe_model_name": "Catalina 30",
                "accepted_matches": [{"qid": "Q5051253"}],
            },
            {
                "manufacturer_sample": "Other Yachts",
                "probe_model_name": "Some Other Boat",
                "accepted_matches": [{"qid": "Q999999"}],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Pilot identity boundary
# ---------------------------------------------------------------------------


def test_build_pilot_identity_boundary_happy_path() -> None:
    doc = build_pilot_identity_boundary(
        linkage_document=_minimal_linkage_document(),
        overlap_result=_minimal_overlap_result(),
        generated_at="2026-08-27T00:00:00+00:00",
    )
    assert [m["qid"] for m in doc["pilot_boat_models"]] == list(FIXED_QIDS)
    assert doc["pilot_boat_models"][0]["hullq_id"] == "BM_TEST_22"
    assert doc["pilot_boat_models"][1]["hullq_id"] == "BM_TEST_30"
    assert doc["boundary_invariants"]["fixed_qid_count"] == 2
    assert doc["source_identity_boundary"]["canonical_boat_model_count"] == 1770


def test_build_pilot_identity_boundary_rejects_wrong_canonical_count() -> None:
    linkage = _minimal_linkage_document()
    linkage["identity_boundary"]["canonical_boat_model_count"] = 1771
    with pytest.raises(IdentityBoundaryIntegrityError):
        build_pilot_identity_boundary(
            linkage_document=linkage,
            overlap_result=_minimal_overlap_result(),
            generated_at="2026-08-27T00:00:00+00:00",
        )


def test_build_pilot_identity_boundary_rejects_missing_fixed_qid() -> None:
    linkage = _minimal_linkage_document()
    linkage["boat_models"] = [m for m in linkage["boat_models"] if "Q5051253" not in m["qids"]]
    with pytest.raises(IdentityBoundaryIntegrityError):
        build_pilot_identity_boundary(
            linkage_document=linkage,
            overlap_result=_minimal_overlap_result(),
            generated_at="2026-08-27T00:00:00+00:00",
        )


def test_build_pilot_identity_boundary_rejects_missing_overlap_entry() -> None:
    overlap = _minimal_overlap_result()
    overlap["exact_overlap"] = [
        e for e in overlap["exact_overlap"] if e["probe_model_name"] != "Catalina 30"
    ]
    with pytest.raises(IdentityBoundaryIntegrityError):
        build_pilot_identity_boundary(
            linkage_document=_minimal_linkage_document(),
            overlap_result=overlap,
            generated_at="2026-08-27T00:00:00+00:00",
        )


def test_verify_pilot_identity_boundary_self_consistency_detects_drift() -> None:
    doc = build_pilot_identity_boundary(
        linkage_document=_minimal_linkage_document(),
        overlap_result=_minimal_overlap_result(),
        generated_at="2026-08-27T00:00:00+00:00",
    )
    tampered = json.loads(json.dumps(doc))
    tampered["pilot_boat_models"][0]["hullq_id"] = "BM_TAMPERED"
    mismatches = verify_pilot_identity_boundary_self_consistency(
        tampered,
        linkage_document=_minimal_linkage_document(),
        overlap_result=_minimal_overlap_result(),
    )
    assert mismatches


def test_verify_pilot_identity_boundary_self_consistency_matches_retained_package() -> None:
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    linkage_document = _load(SL0028_DIR / "linkage.json")
    overlap_result = _load(ROOT / "research" / "manufacturers" / "overlap_result.json")
    assert (
        verify_pilot_identity_boundary_self_consistency(
            identity_boundary, linkage_document=linkage_document, overlap_result=overlap_result
        )
        == []
    )


# ---------------------------------------------------------------------------
# Retrieval log
# ---------------------------------------------------------------------------


def _valid_retrieval_entry(index: int) -> dict[str, Any]:
    return {
        "retrieval_index": index,
        "url": f"https://www.catalinayachts.com/page-{index}/",
        "sha256": "a" * 64,
    }


def test_validate_source_retrieval_log_happy_path() -> None:
    entries = [_valid_retrieval_entry(i) for i in range(1, 4)]
    doc = {"retrieval_ceiling": RETRIEVAL_CEILING, "retrieval_count": 3, "retrievals": entries}
    assert validate_source_retrieval_log(doc) == []


def test_validate_source_retrieval_log_rejects_ceiling_mismatch() -> None:
    doc = {"retrieval_ceiling": 30, "retrieval_count": 0, "retrievals": []}
    problems = validate_source_retrieval_log(doc)
    assert any("retrieval_ceiling" in p for p in problems)


def test_validate_source_retrieval_log_rejects_count_mismatch() -> None:
    entries = [_valid_retrieval_entry(1)]
    doc = {"retrieval_ceiling": RETRIEVAL_CEILING, "retrieval_count": 2, "retrievals": entries}
    problems = validate_source_retrieval_log(doc)
    assert any("retrieval_count" in p for p in problems)


def test_validate_source_retrieval_log_rejects_bad_host() -> None:
    entry = _valid_retrieval_entry(1)
    entry["url"] = "https://www.sailboatdata.com/page-1/"
    doc = {"retrieval_ceiling": RETRIEVAL_CEILING, "retrieval_count": 1, "retrievals": [entry]}
    problems = validate_source_retrieval_log(doc)
    assert any("permitted host set" in p for p in problems)


def test_validate_source_retrieval_log_rejects_duplicate_index() -> None:
    entries = [_valid_retrieval_entry(1), _valid_retrieval_entry(1)]
    doc = {"retrieval_ceiling": RETRIEVAL_CEILING, "retrieval_count": 2, "retrievals": entries}
    problems = validate_source_retrieval_log(doc)
    assert any("duplicate" in p for p in problems)


def test_validate_source_retrieval_log_matches_retained_package() -> None:
    doc = _load(SL0029_DIR / "source_retrieval_log.json")
    assert validate_source_retrieval_log(doc) == []
    assert doc["retrieval_count"] <= RETRIEVAL_CEILING


# ---------------------------------------------------------------------------
# Source-rights gate
# ---------------------------------------------------------------------------


def _minimal_source_record(*, identity_seed: str, production_value: str) -> dict[str, Any]:
    return {
        "source_id": "SRC_TEST",
        "rights": {
            "assessment_status": "assessed",
            "access": {
                "automated_access": "unknown",
            },
            "permissions": {
                "store_canonical_values": "conditional",
                "commercial_use": "conditional",
                "publish_derived_database": "conditional",
                "bulk_ingest": "unknown",
                "redistribute_source_material": "prohibited",
                "automated_extract": "unknown",
            },
            "obligations": {
                "attribution_required": "unknown",
                "share_alike": "not_applicable",
                "notice_required": "unknown",
            },
            "clearance": {
                "research_reference": "allowed",
                "research_lead": "allowed",
                "identity_seed": identity_seed,
                "production_value": production_value,
                "bulk_bootstrap": "legal_review_required",
                "automated_ingestion": "unknown",
                "artifact_redistribution": "legal_review_required",
            },
        },
    }


def test_evaluate_source_use_gate_allowed_when_cleared() -> None:
    record = _minimal_source_record(identity_seed="allowed", production_value="allowed")
    decisions = evaluate_source_use_gate(record)
    assert decisions["identity_seed"]["outcome"] == "allowed"
    assert decisions["production_value"]["outcome"] == "allowed"
    assert decisions["bulk_bootstrap"]["outcome"] == "legal_review_required"
    assert decisions["automated_ingestion"]["outcome"] == "unknown_unassessed"
    assert source_use_allowed(decisions, "identity_seed") is True


def test_evaluate_source_use_gate_conditional_never_auto_allowed() -> None:
    record = _minimal_source_record(identity_seed="conditional", production_value="conditional")
    decisions = evaluate_source_use_gate(record)
    assert decisions["identity_seed"]["outcome"] == "conditional"
    assert decisions["production_value"]["outcome"] == "conditional"
    assert source_use_allowed(decisions, "identity_seed") is False


# ---------------------------------------------------------------------------
# SR-6.6 <-> clearance fail-closed coupling (the review's blocking finding #1)
# ---------------------------------------------------------------------------

_SATISFIED_CONDITIONS = [
    {"condition": "c1", "satisfied": True, "evidence": "e1"},
    {"condition": "c2", "satisfied": "partial_left_unresolved", "evidence": "e2"},
]
_UNSATISFIED_CONDITIONS = [
    {"condition": "c1", "satisfied": True, "evidence": "e1"},
    {"condition": "c2", "satisfied": False, "evidence": "e2"},
]


def test_derive_sr_6_6_use_clearance_satisfied() -> None:
    assert derive_sr_6_6_use_clearance(_SATISFIED_CONDITIONS) == SR_6_6_SATISFIED_CLEARANCE
    assert SR_6_6_SATISFIED_CLEARANCE == "allowed"


def test_derive_sr_6_6_use_clearance_unsatisfied() -> None:
    assert derive_sr_6_6_use_clearance(_UNSATISFIED_CONDITIONS) == SR_6_6_DEFAULT_CLEARANCE
    assert SR_6_6_DEFAULT_CLEARANCE == "conditional"


def _pilot_identity_boundary_for_gated_tests() -> dict[str, Any]:
    return _load(SL0029_DIR / "pilot_identity_boundary.json")


def _valid_bounded_scope(pilot_identity_boundary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "hullq_ids": [m["hullq_id"] for m in pilot_identity_boundary["pilot_boat_models"]],
        "qids": [m["qid"] for m in pilot_identity_boundary["pilot_boat_models"]],
        "field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "use_kinds": list(SR_6_6_GATED_USES),
        "note": "test scope",
    }


def _assessment_document(
    *, conditions: list[dict[str, Any]], use_clearance: str, gate_outcome: str
) -> dict[str, Any]:
    identity_boundary = _pilot_identity_boundary_for_gated_tests()
    source_record = _minimal_source_record(
        identity_seed=use_clearance, production_value=use_clearance
    )
    return {
        "sr_6_6_condition_evaluation": {
            "conditions": conditions,
            "conditions_satisfied_for_bounded_manual_use": all(
                c["satisfied"] in (True, "partial_left_unresolved") for c in conditions
            ),
        },
        "source_record": source_record,
        "bounded_scope": _valid_bounded_scope(identity_boundary),
        "source_use_gate_decisions": {
            "decisions": {
                "research_reference": {"outcome": "allowed"},
                "research_lead": {"outcome": "allowed"},
                "identity_seed": {"outcome": gate_outcome},
                "production_value": {"outcome": gate_outcome},
                "bulk_bootstrap": {"outcome": "legal_review_required"},
                "automated_ingestion": {"outcome": "unknown_unassessed"},
                "artifact_redistribution": {"outcome": "legal_review_required"},
            }
        },
    }, identity_boundary


def test_verify_source_clearance_assessment_self_consistency_matches_retained_package() -> None:
    doc = _load(SL0029_DIR / "source_clearance_assessment.json")
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    assert (
        verify_source_clearance_assessment_self_consistency(
            doc, pilot_identity_boundary=identity_boundary
        )
        == []
    )


def test_verify_source_clearance_assessment_self_consistency_detects_drift() -> None:
    doc = json.loads((SL0029_DIR / "source_clearance_assessment.json").read_text(encoding="utf-8"))
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    doc["source_use_gate_decisions"]["decisions"]["bulk_bootstrap"]["outcome"] = "allowed"
    assert (
        verify_source_clearance_assessment_self_consistency(
            doc, pilot_identity_boundary=identity_boundary
        )
        != []
    )


def test_tampered_conditions_with_unchanged_allowed_clearance_fails_verification() -> None:
    """The review's exact attack: SR-6.6 conditions fail but clearance/gate still say
    'allowed'. This MUST be caught -- clearance can never be independently asserted."""
    doc, identity_boundary = _assessment_document(
        conditions=_UNSATISFIED_CONDITIONS, use_clearance="allowed", gate_outcome="allowed"
    )
    mismatches = verify_source_clearance_assessment_self_consistency(
        doc, pilot_identity_boundary=identity_boundary
    )
    assert mismatches
    assert any("not mechanically derived" in m for m in mismatches)


def test_unsatisfied_conditions_correctly_downgraded_passes_verification_but_blocks_recommendation() -> (
    None
):
    """When conditions genuinely fail, the ONLY self-consistent state is clearance
    downgraded to 'conditional', which the unmodified gate maps to non-allow, which
    compute_recommendation must then report as RIGHTS_CLEARANCE_BLOCKED -- never READY."""
    doc, identity_boundary = _assessment_document(
        conditions=_UNSATISFIED_CONDITIONS,
        use_clearance=SR_6_6_DEFAULT_CLEARANCE,
        gate_outcome="conditional",
    )
    assert (
        verify_source_clearance_assessment_self_consistency(
            doc, pilot_identity_boundary=identity_boundary
        )
        == []
    )
    boatdesign = _load(SL0029_DIR / "boatdesign_applicability.json")
    field_applicability = _load(SL0029_DIR / "wikidata_candidate_applicability.json")
    result = compute_recommendation(
        source_use_gate_decisions=doc["source_use_gate_decisions"]["decisions"],
        boatdesign_applicability=boatdesign,
        wikidata_candidate_applicability=field_applicability,
    )
    assert result == RecommendationCode.RIGHTS_CLEARANCE_BLOCKED.value


def test_satisfied_conditions_require_allowed_clearance_not_conditional() -> None:
    """The inverse tamper: conditions are satisfied but clearance was left at the
    policy default 'conditional' -- also a mismatch, since satisfaction and clearance
    are the same computation."""
    doc, identity_boundary = _assessment_document(
        conditions=_SATISFIED_CONDITIONS,
        use_clearance=SR_6_6_DEFAULT_CLEARANCE,
        gate_outcome="conditional",
    )
    mismatches = verify_source_clearance_assessment_self_consistency(
        doc, pilot_identity_boundary=identity_boundary
    )
    assert any("not mechanically derived" in m for m in mismatches)


def test_broader_uses_stay_non_allow_regardless_of_sr_6_6_satisfaction() -> None:
    """bulk_bootstrap / automated_ingestion / artifact_redistribution are never
    derived from SR-6.6 conditions and must stay non-allow either way."""
    for conditions in (_SATISFIED_CONDITIONS, _UNSATISFIED_CONDITIONS):
        clearance = derive_sr_6_6_use_clearance(conditions)
        record = _minimal_source_record(identity_seed=clearance, production_value=clearance)
        decisions = evaluate_source_use_gate(record)
        assert decisions["bulk_bootstrap"]["outcome"] == "legal_review_required"
        assert decisions["automated_ingestion"]["outcome"] == "unknown_unassessed"
        assert decisions["artifact_redistribution"]["outcome"] == "legal_review_required"


def test_validate_permissions_bounded_rejects_unscoped_allowed_permission() -> None:
    for key in BOUNDED_ONLY_PERMISSION_KEYS:
        record = _minimal_source_record(identity_seed="allowed", production_value="allowed")
        record["rights"]["permissions"][key] = "allowed"
        problems = validate_permissions_bounded(record)
        assert any(key in p for p in problems)


def test_validate_permissions_bounded_accepts_conditional_permissions() -> None:
    record = _minimal_source_record(identity_seed="allowed", production_value="allowed")
    assert validate_permissions_bounded(record) == []


def test_validate_bounded_scope_matches_retained_package() -> None:
    doc = _load(SL0029_DIR / "source_clearance_assessment.json")
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    assert validate_bounded_scope(doc, pilot_identity_boundary=identity_boundary) == []


def test_validate_bounded_scope_rejects_extra_qid() -> None:
    doc = json.loads((SL0029_DIR / "source_clearance_assessment.json").read_text(encoding="utf-8"))
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    doc["bounded_scope"]["qids"] = ["Q5051252", "Q999999"]
    problems = validate_bounded_scope(doc, pilot_identity_boundary=identity_boundary)
    assert any("qids" in p for p in problems)


# ---------------------------------------------------------------------------
# OBSERVATION_APPLICABILITY_SCHEMA.v0.1 no-absence-as-proof invariant
# (the review's blocking finding #2)
# ---------------------------------------------------------------------------


def _unbounded_scope() -> dict[str, Any]:
    return {
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


def _bounded_scope(**overrides: Any) -> dict[str, Any]:
    """A genuinely closed production-year range: BOTH first_year and last_year known."""
    scope = _unbounded_scope()
    scope["unknown_or_unbounded"] = False
    scope["first_year"] = 1974
    scope["last_year"] = 1995
    scope.update(overrides)
    return scope


def test_validate_applicability_scope_invariant_accepts_unknown_unbounded() -> None:
    assert validate_applicability_scope_invariant(_unbounded_scope()) == []


def test_validate_applicability_scope_invariant_accepts_genuinely_bounded() -> None:
    assert validate_applicability_scope_invariant(_bounded_scope()) == []


def test_validate_applicability_scope_invariant_accepts_bounded_by_hull_number() -> None:
    """A non-year dimension (e.g. a hull-number range) can independently justify a
    genuinely bounded scope without needing a production-year range at all."""
    scope = _unbounded_scope()
    scope["unknown_or_unbounded"] = False
    scope["hull_number_from"] = "1"
    scope["hull_number_to"] = "500"
    assert validate_applicability_scope_invariant(scope) == []


def test_validate_applicability_scope_invariant_rejects_empty_bounded_claim() -> None:
    """unknown_or_unbounded=false with every dimension null is an empty scope
    masquerading as bounded -- exactly the forbidden absence-as-proof pattern."""
    empty_but_claimed_bounded = _unbounded_scope()
    empty_but_claimed_bounded["unknown_or_unbounded"] = False
    problems = validate_applicability_scope_invariant(empty_but_claimed_bounded)
    assert problems
    assert any("empty scope" in p for p in problems)


def test_validate_applicability_scope_invariant_rejects_half_open_year_range() -> None:
    """The review's exact second-round finding: a genuinely unknown production-year
    upper (or lower) bound must not be treated as bounded merely because the OTHER
    bound is known. Neither a known first_year alone nor a known last_year alone is
    sufficient."""
    known_start_only = _bounded_scope(last_year=None)
    problems = validate_applicability_scope_invariant(known_start_only)
    assert problems
    assert any("only one of first_year/last_year is known" in p for p in problems)

    known_end_only = _bounded_scope(first_year=None, last_year=1995)
    problems = validate_applicability_scope_invariant(known_end_only)
    assert problems
    assert any("only one of first_year/last_year is known" in p for p in problems)


# ---------------------------------------------------------------------------
# BoatDesign / field applicability structural validation
# ---------------------------------------------------------------------------


def test_validate_boatdesign_applicability_matches_retained_package() -> None:
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    boatdesign = _load(SL0029_DIR / "boatdesign_applicability.json")
    assert (
        validate_boatdesign_applicability(boatdesign, pilot_identity_boundary=identity_boundary)
        == []
    )


def test_validate_boatdesign_applicability_rejects_hullq_id_mismatch() -> None:
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    boatdesign = json.loads(
        (SL0029_DIR / "boatdesign_applicability.json").read_text(encoding="utf-8")
    )
    boatdesign["boat_models"][0]["hullq_id"] = "BM_WRONG"
    problems = validate_boatdesign_applicability(
        boatdesign, pilot_identity_boundary=identity_boundary
    )
    assert problems


def test_validate_boatdesign_applicability_rejects_established_true_with_unbounded_scope() -> None:
    """The review's exact original defect: generation_boundary_established_for_this_pilot
    = true while applicability_scope claims unknown_or_unbounded -- the two facts
    must agree. Both BoatModels are currently established=false in the retained
    package (amended per review), so this test forces established=true onto a
    synthetic copy to exercise the invariant directly."""
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    boatdesign = json.loads(
        (SL0029_DIR / "boatdesign_applicability.json").read_text(encoding="utf-8")
    )
    catalina_30 = next(m for m in boatdesign["boat_models"] if m["qid"] == "Q5051253")
    assert catalina_30["generation_boundary_established_for_this_pilot"] is False
    assert catalina_30["applicability_scope"]["unknown_or_unbounded"] is True
    catalina_30["generation_boundary_established_for_this_pilot"] = True
    problems = validate_boatdesign_applicability(
        boatdesign, pilot_identity_boundary=identity_boundary
    )
    assert any("unknown_or_unbounded" in p for p in problems)


def test_validate_wikidata_candidate_applicability_matches_retained_package() -> None:
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    field_applicability = _load(SL0029_DIR / "wikidata_candidate_applicability.json")
    evidence_manifest = _load(SL0028_DIR / "evidence_manifest.json")
    assert (
        validate_wikidata_candidate_applicability(
            field_applicability,
            pilot_identity_boundary=identity_boundary,
            evidence_manifest=evidence_manifest,
        )
        == []
    )
    for model in field_applicability["boat_models"]:
        pointers = {f["field_pointer"] for f in model["fields"]}
        assert pointers == ALLOWED_FIELD_POINTERS


def test_validate_wikidata_candidate_applicability_rejects_tampered_candidate() -> None:
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    evidence_manifest = _load(SL0028_DIR / "evidence_manifest.json")
    field_applicability = json.loads(
        (SL0029_DIR / "wikidata_candidate_applicability.json").read_text(encoding="utf-8")
    )
    field = field_applicability["boat_models"][1]["fields"][0]
    assert field["field_pointer"] == "/baseline/dimensions/loa_m"
    field["sl0028_normalized_candidate"] = {"value": "999.0", "unit": "m"}
    problems = validate_wikidata_candidate_applicability(
        field_applicability,
        pilot_identity_boundary=identity_boundary,
        evidence_manifest=evidence_manifest,
    )
    assert any("!= reused SLICE-0028 evidence" in p for p in problems)


def test_validate_wikidata_candidate_applicability_rejects_safe_with_unbounded_scope() -> None:
    """The core anti-overclaim rule: SAFE_FOR_LATER_DESIGN_PROMOTION requires a
    genuinely bounded applicability_scope -- absence of evidence must never become
    evidence of all-production applicability. No field in the retained package is
    currently SAFE (amended per review), so this test forces the outcome onto a
    synthetic copy of an already-unbounded retained field to exercise the check."""
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    evidence_manifest = _load(SL0028_DIR / "evidence_manifest.json")
    field_applicability = json.loads(
        (SL0029_DIR / "wikidata_candidate_applicability.json").read_text(encoding="utf-8")
    )
    catalina_30 = next(m for m in field_applicability["boat_models"] if m["qid"] == "Q5051253")
    loa_field = next(
        f for f in catalina_30["fields"] if f["field_pointer"] == "/baseline/dimensions/loa_m"
    )
    assert loa_field["outcome"] == ApplicabilityOutcome.INSUFFICIENT_EVIDENCE.value
    assert loa_field["applicability_scope"]["unknown_or_unbounded"] is True
    loa_field["outcome"] = ApplicabilityOutcome.SAFE_FOR_LATER_DESIGN_PROMOTION.value
    problems = validate_wikidata_candidate_applicability(
        field_applicability,
        pilot_identity_boundary=identity_boundary,
        evidence_manifest=evidence_manifest,
    )
    assert any("requires applicability_scope.unknown_or_unbounded == false" in p for p in problems)


def test_validate_wikidata_candidate_applicability_rejects_bad_outcome() -> None:
    identity_boundary = _load(SL0029_DIR / "pilot_identity_boundary.json")
    evidence_manifest = _load(SL0028_DIR / "evidence_manifest.json")
    field_applicability = json.loads(
        (SL0029_DIR / "wikidata_candidate_applicability.json").read_text(encoding="utf-8")
    )
    field_applicability["boat_models"][0]["fields"][0]["outcome"] = "NOT_A_REAL_OUTCOME"
    problems = validate_wikidata_candidate_applicability(
        field_applicability,
        pilot_identity_boundary=identity_boundary,
        evidence_manifest=evidence_manifest,
    )
    assert any("invalid outcome" in p for p in problems)


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def _gate(identity_seed: str, production_value: str) -> dict[str, Any]:
    return {
        "identity_seed": {"outcome": identity_seed},
        "production_value": {"outcome": production_value},
    }


def _boatdesign(established_hullq_ids: set[str]) -> dict[str, Any]:
    return {
        "boat_models": [
            {
                "hullq_id": "BM_A",
                "generation_boundary_established_for_this_pilot": "BM_A" in established_hullq_ids,
            },
            {
                "hullq_id": "BM_B",
                "generation_boundary_established_for_this_pilot": "BM_B" in established_hullq_ids,
            },
        ]
    }


def _field_applicability(
    safe_hullq_ids: set[str], *, safe_scope_bounded: bool = True
) -> dict[str, Any]:
    def _fields(hullq_id: str) -> list[dict[str, Any]]:
        is_safe = hullq_id in safe_hullq_ids
        outcome = (
            ApplicabilityOutcome.SAFE_FOR_LATER_DESIGN_PROMOTION.value
            if is_safe
            else ApplicabilityOutcome.GENERATION_AMBIGUOUS.value
        )
        scope = _bounded_scope() if (is_safe and safe_scope_bounded) else _unbounded_scope()
        return [{"outcome": outcome, "applicability_scope": scope}]

    return {
        "boat_models": [
            {"hullq_id": "BM_A", "fields": _fields("BM_A")},
            {"hullq_id": "BM_B", "fields": _fields("BM_B")},
        ]
    }


def test_compute_recommendation_rights_blocked() -> None:
    result = compute_recommendation(
        source_use_gate_decisions=_gate("conditional", "allowed"),
        boatdesign_applicability=_boatdesign({"BM_A"}),
        wikidata_candidate_applicability=_field_applicability({"BM_A"}),
    )
    assert result == RecommendationCode.RIGHTS_CLEARANCE_BLOCKED.value


def test_compute_recommendation_applicability_insufficient() -> None:
    result = compute_recommendation(
        source_use_gate_decisions=_gate("allowed", "allowed"),
        boatdesign_applicability=_boatdesign(set()),
        wikidata_candidate_applicability=_field_applicability({"BM_A"}),
    )
    assert result == RecommendationCode.APPLICABILITY_EVIDENCE_INSUFFICIENT.value


def test_compute_recommendation_ready() -> None:
    result = compute_recommendation(
        source_use_gate_decisions=_gate("allowed", "allowed"),
        boatdesign_applicability=_boatdesign({"BM_B"}),
        wikidata_candidate_applicability=_field_applicability({"BM_B"}),
    )
    assert result == RecommendationCode.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT.value


def test_compute_recommendation_requires_boundary_and_safe_field_on_same_model() -> None:
    """A safe field on a model without an established boundary must not count."""
    result = compute_recommendation(
        source_use_gate_decisions=_gate("allowed", "allowed"),
        boatdesign_applicability=_boatdesign({"BM_A"}),
        wikidata_candidate_applicability=_field_applicability({"BM_B"}),
    )
    assert result == RecommendationCode.APPLICABILITY_EVIDENCE_INSUFFICIENT.value


def test_compute_recommendation_rejects_safe_field_with_unbounded_scope() -> None:
    """Defense in depth: even if validate_wikidata_candidate_applicability was
    skipped, compute_recommendation itself must not treat a SAFE_FOR_LATER_DESIGN_PROMOTION
    field as usable when its applicability_scope is unknown/unbounded."""
    result = compute_recommendation(
        source_use_gate_decisions=_gate("allowed", "allowed"),
        boatdesign_applicability=_boatdesign({"BM_B"}),
        wikidata_candidate_applicability=_field_applicability({"BM_B"}, safe_scope_bounded=False),
    )
    assert result == RecommendationCode.APPLICABILITY_EVIDENCE_INSUFFICIENT.value


def test_compute_recommendation_matches_retained_package() -> None:
    clearance = _load(SL0029_DIR / "source_clearance_assessment.json")
    boatdesign = _load(SL0029_DIR / "boatdesign_applicability.json")
    field_applicability = _load(SL0029_DIR / "wikidata_candidate_applicability.json")
    result = compute_recommendation(
        source_use_gate_decisions=clearance["source_use_gate_decisions"]["decisions"],
        boatdesign_applicability=boatdesign,
        wikidata_candidate_applicability=field_applicability,
    )
    assert result == RecommendationCode.APPLICABILITY_EVIDENCE_INSUFFICIENT.value
    report_text = (SL0029_DIR / "REPORT.md").read_text(encoding="utf-8")
    assert result in report_text


# ---------------------------------------------------------------------------
# Artifact digests
# ---------------------------------------------------------------------------


def test_build_and_verify_artifact_digests_round_trip(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_bytes(b'{"x": 1}')
    (tmp_path / "b.json").write_bytes(b'{"y": 2}')
    document = build_artifact_digests(
        generated_at="2026-08-27T00:00:00+00:00", package_dir=tmp_path
    )
    assert set(document["digests"]) == {"a.json", "b.json"}
    assert (
        verify_artifact_digests_self_consistency(artifact_digests=document, package_dir=tmp_path)
        == []
    )


def test_verify_artifact_digests_self_consistency_detects_tamper(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_bytes(b'{"x": 1}')
    document = build_artifact_digests(
        generated_at="2026-08-27T00:00:00+00:00", package_dir=tmp_path
    )
    (tmp_path / "a.json").write_bytes(b'{"x": 2}')
    mismatches = verify_artifact_digests_self_consistency(
        artifact_digests=document, package_dir=tmp_path
    )
    assert mismatches


def test_artifact_digests_match_retained_package() -> None:
    artifact_digests = _load(SL0029_DIR / "ARTIFACT-DIGESTS.json")
    assert (
        verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0029_DIR
        )
        == []
    )
    assert retained_package_filenames(SL0029_DIR) == set(artifact_digests["digests"])
