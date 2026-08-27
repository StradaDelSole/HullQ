"""Unit tests for the SLICE-0029 primary-source BoatDesign applicability pilot pure logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0029_boatdesign_applicability_pilot import (
    ALLOWED_FIELD_POINTERS,
    FIXED_QIDS,
    RETRIEVAL_CEILING,
    ApplicabilityOutcome,
    IdentityBoundaryIntegrityError,
    RecommendationCode,
    build_artifact_digests,
    build_pilot_identity_boundary,
    compute_recommendation,
    evaluate_source_use_gate,
    retained_package_filenames,
    source_use_allowed,
    validate_boatdesign_applicability,
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


def test_verify_source_clearance_assessment_self_consistency_matches_retained_package() -> None:
    doc = _load(SL0029_DIR / "source_clearance_assessment.json")
    assert verify_source_clearance_assessment_self_consistency(doc) == []


def test_verify_source_clearance_assessment_self_consistency_detects_drift() -> None:
    doc = json.loads((SL0029_DIR / "source_clearance_assessment.json").read_text(encoding="utf-8"))
    doc["source_use_gate_decisions"]["decisions"]["bulk_bootstrap"]["outcome"] = "allowed"
    assert verify_source_clearance_assessment_self_consistency(doc) != []


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


def _field_applicability(safe_hullq_ids: set[str]) -> dict[str, Any]:
    def _fields(hullq_id: str) -> list[dict[str, Any]]:
        outcome = (
            ApplicabilityOutcome.SAFE_FOR_LATER_DESIGN_PROMOTION.value
            if hullq_id in safe_hullq_ids
            else ApplicabilityOutcome.GENERATION_AMBIGUOUS.value
        )
        return [{"outcome": outcome}]

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


def test_compute_recommendation_matches_retained_package() -> None:
    clearance = _load(SL0029_DIR / "source_clearance_assessment.json")
    boatdesign = _load(SL0029_DIR / "boatdesign_applicability.json")
    field_applicability = _load(SL0029_DIR / "wikidata_candidate_applicability.json")
    result = compute_recommendation(
        source_use_gate_decisions=clearance["source_use_gate_decisions"]["decisions"],
        boatdesign_applicability=boatdesign,
        wikidata_candidate_applicability=field_applicability,
    )
    assert result == RecommendationCode.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT.value
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
