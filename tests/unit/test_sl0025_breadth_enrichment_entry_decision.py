"""Unit tests for
src/hullq/bootstrap/sl0025_breadth_enrichment_entry_decision.py.

Covers the three precommitted-decision-rule branches
(``BLOCKED_ON_ACCEPTED_STATE``, ``CONTINUE_STAGE_3_2_ONLY`` via a qualifying
breadth path, ``CONTINUE_STAGE_3_2_ONLY`` via insufficient readiness, and
``BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL``), the real accepted-boundary
reproduction from the committed SLICE-0018/0020/0021/0022/0023/0024
artifacts, and digest/self-consistency tamper detection.

Synthetic candidates/mappings used to exercise individual branches are
logic tests only and are never presented as real project evidence -- the
real accepted evidence is exercised separately via ``load_reproduced_boundary``
and ``KNOWN_BREADTH_PATH_CANDIDATES``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import hullq.bootstrap.sl0025_breadth_enrichment_entry_decision as sl0025
from hullq.bootstrap.sl0025_breadth_enrichment_entry_decision import (
    ARTIFACT_DIGEST_COVERED_FILENAMES,
    FIXED_ACCEPTED_BOUNDARY,
    KNOWN_BREADTH_PATH_CANDIDATES,
    AcceptedBoundaryIntegrityError,
    BreadthPathCandidate,
    Decision,
    ParallelReadinessConditions,
    build_decision_input_document,
    build_decision_result_document,
    build_known_breadth_path_candidates,
    candidate_to_dict,
    determine_decision,
    evaluate_boundary_consistency,
    evaluate_parallel_readiness,
    find_qualifying_breadth_path,
    load_reproduced_boundary,
    verify_artifact_digests_self_consistency,
    verify_decision_input_self_consistency,
    verify_decision_result_self_consistency,
)

SL0025_DIR = (
    Path(__file__).resolve().parents[2] / "research" / "stage3" / "sl0025-breadth-enrichment-entry"
)


# ---------------------------------------------------------------------------
# Real accepted-boundary reproduction (regression against committed artifacts)
# ---------------------------------------------------------------------------


def test_load_reproduced_boundary_matches_fixed_accepted_boundary() -> None:
    reproduced = load_reproduced_boundary()
    mismatches = evaluate_boundary_consistency(reproduced)
    assert mismatches == []
    for key, expected in FIXED_ACCEPTED_BOUNDARY.items():
        assert reproduced[key] == expected


def test_load_reproduced_boundary_includes_zero_tolerance_flags() -> None:
    reproduced = load_reproduced_boundary()
    assert reproduced["zero_tolerance_conditions_clear"] is True
    assert reproduced["prior_baseline_verified_before_sl0022"] is True


def test_load_reproduced_boundary_fails_closed_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AcceptedBoundaryIntegrityError):
        load_reproduced_boundary(sl0018_manifest_path=tmp_path / "does-not-exist.json")


def test_load_reproduced_boundary_fails_closed_on_missing_field(tmp_path: Path) -> None:
    sl0018_path = tmp_path / "manifest.json"
    sl0018_path.write_text(json.dumps({"counts": {}}), encoding="utf-8")
    with pytest.raises(AcceptedBoundaryIntegrityError):
        load_reproduced_boundary(sl0018_manifest_path=sl0018_path)


# ---------------------------------------------------------------------------
# evaluate_boundary_consistency (pure, synthetic-testable rule-1 input)
# ---------------------------------------------------------------------------


def test_evaluate_boundary_consistency_detects_drift() -> None:
    drifted = dict(FIXED_ACCEPTED_BOUNDARY)
    drifted["accepted_canonical_boat_models"] = 1771
    drifted["sl0022_auto_admit_from_57"] = 3
    mismatches = evaluate_boundary_consistency(drifted)
    assert len(mismatches) == 2
    assert any("accepted_canonical_boat_models" in m for m in mismatches)
    assert any("sl0022_auto_admit_from_57" in m for m in mismatches)


def test_evaluate_boundary_consistency_detects_missing_key() -> None:
    incomplete = {
        k: v for k, v in FIXED_ACCEPTED_BOUNDARY.items() if k != "sl0024_final_recommendation"
    }
    mismatches = evaluate_boundary_consistency(incomplete)
    assert any("sl0024_final_recommendation" in m for m in mismatches)


def test_evaluate_boundary_consistency_clean_on_exact_match() -> None:
    assert evaluate_boundary_consistency(dict(FIXED_ACCEPTED_BOUNDARY)) == []


def test_evaluate_boundary_consistency_accepts_explicit_fixed_mapping() -> None:
    custom_fixed = {"accepted_canonical_boat_models": 42}
    assert evaluate_boundary_consistency({"accepted_canonical_boat_models": 42}, custom_fixed) == []
    assert evaluate_boundary_consistency({"accepted_canonical_boat_models": 43}, custom_fixed) != []


# ---------------------------------------------------------------------------
# sl0024_threshold_required: the fixed side must be a self-contained literal,
# not the same mutable constant reproduced on the other side, so a drift in
# the shared upstream SLICE-0024 constant is actually detectable.
# ---------------------------------------------------------------------------


def test_fixed_accepted_boundary_threshold_required_is_the_accepted_literal_12() -> None:
    assert FIXED_ACCEPTED_BOUNDARY["sl0024_threshold_required"] == 12


def test_load_reproduced_boundary_threshold_required_tracks_sl0024_module_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulate drift/tamper in the upstream accepted SLICE-0024 module
    # constant that the reproduced side (deliberately) still reads. The fixed
    # side must NOT move in lockstep -- it is a self-contained literal.
    monkeypatch.setattr(sl0025, "IN_SCOPE_MIN_INDEPENDENT_SUPPORTED", 5)
    reproduced = load_reproduced_boundary()
    assert reproduced["sl0024_threshold_required"] == 5

    mismatches = evaluate_boundary_consistency(reproduced)
    assert any(
        "sl0024_threshold_required" in m and "expected 12" in m and "reproduced 5" in m
        for m in mismatches
    )


# ---------------------------------------------------------------------------
# Real known breadth-path candidates (regression: none qualify today)
# ---------------------------------------------------------------------------


def test_known_breadth_path_candidates_count() -> None:
    assert len(KNOWN_BREADTH_PATH_CANDIDATES) == 4


def test_no_real_known_breadth_path_candidate_qualifies() -> None:
    assert find_qualifying_breadth_path(KNOWN_BREADTH_PATH_CANDIDATES) is None
    for candidate in KNOWN_BREADTH_PATH_CANDIDATES:
        assert candidate.qualifies() is False


def test_build_known_breadth_path_candidates_matches_module_constant() -> None:
    reproduced = load_reproduced_boundary()
    rebuilt = build_known_breadth_path_candidates(reproduced)
    assert [c.name for c in rebuilt] == [c.name for c in KNOWN_BREADTH_PATH_CANDIDATES]


@pytest.mark.parametrize(
    ("name", "expected_reason"),
    [
        ("sl0018_larger_direct_discovery_limit", "materially_different_from_sl0018"),
        ("sl0020_manufacturer_archive_bulk_bootstrap", "production_bulk_cleared"),
        ("sl0021_sl0022_alternative_wikidata_route", "already_executed"),
        ("sl0023_sl0024_full_wikimedia_verification_campaign", "requires_full_wikimedia_campaign"),
    ],
)
def test_each_known_candidate_fails_for_its_documented_reason(
    name: str, expected_reason: str
) -> None:
    candidate = next(c for c in KNOWN_BREADTH_PATH_CANDIDATES if c.name == name)
    field_value = getattr(candidate, expected_reason)
    # The disqualifying field is either False when a True is required, or
    # True when a False is required -- assert it is on the disqualifying side.
    if expected_reason in {"production_bulk_cleared", "materially_different_from_sl0018"}:
        assert field_value is False
    else:
        assert field_value is True


# ---------------------------------------------------------------------------
# BreadthPathCandidate.qualifies() / find_qualifying_breadth_path (synthetic)
# ---------------------------------------------------------------------------


def _synthetic_qualifying_candidate() -> BreadthPathCandidate:
    return BreadthPathCandidate(
        name="synthetic_qualifying_route",
        source_slices="TEST-ONLY",
        already_executed=False,
        production_bulk_cleared=True,
        materially_different_from_sl0018=True,
        likely_incremental_yield=150,
        requires_full_wikimedia_campaign=False,
        requires_upstream_governance_decision=False,
        rationale="synthetic logic-test fixture, not real project evidence",
    )


def test_synthetic_qualifying_candidate_qualifies() -> None:
    candidate = _synthetic_qualifying_candidate()
    assert candidate.qualifies() is True
    assert find_qualifying_breadth_path([*KNOWN_BREADTH_PATH_CANDIDATES, candidate]) is candidate


@pytest.mark.parametrize(
    "overrides",
    [
        {"already_executed": True},
        {"production_bulk_cleared": False},
        {"materially_different_from_sl0018": False},
        {"likely_incremental_yield": 99},
        {"requires_full_wikimedia_campaign": True},
        {"requires_upstream_governance_decision": True},
    ],
)
def test_synthetic_candidate_fails_when_one_condition_violated(overrides: dict[str, Any]) -> None:
    base = _synthetic_qualifying_candidate()
    candidate = BreadthPathCandidate(
        **{**base.__dict__, **overrides},
    )
    assert candidate.qualifies() is False
    assert find_qualifying_breadth_path([candidate]) is None


# ---------------------------------------------------------------------------
# evaluate_parallel_readiness / ParallelReadinessConditions.all_met
# ---------------------------------------------------------------------------


def test_evaluate_parallel_readiness_all_met_on_real_accepted_evidence() -> None:
    reproduced = load_reproduced_boundary()
    readiness = evaluate_parallel_readiness(reproduced, qualifying_breadth_path=None)
    assert readiness.all_met() is True


def test_evaluate_parallel_readiness_fails_on_insufficient_corpus() -> None:
    reproduced = dict(load_reproduced_boundary())
    reproduced["accepted_canonical_boat_models"] = 500
    readiness = evaluate_parallel_readiness(reproduced, qualifying_breadth_path=None)
    assert readiness.canonical_count_at_least_1000 is False
    assert readiness.all_met() is False


def test_evaluate_parallel_readiness_fails_when_qualifying_path_present() -> None:
    reproduced = load_reproduced_boundary()
    candidate = _synthetic_qualifying_candidate()
    readiness = evaluate_parallel_readiness(reproduced, qualifying_breadth_path=candidate)
    assert readiness.no_qualifying_breadth_path_pending is False
    assert readiness.all_met() is False


def test_evaluate_parallel_readiness_fails_when_zero_tolerance_not_clear() -> None:
    reproduced = dict(load_reproduced_boundary())
    reproduced["zero_tolerance_conditions_clear"] = False
    readiness = evaluate_parallel_readiness(reproduced, qualifying_breadth_path=None)
    assert readiness.zero_tolerance_identity_foundation_accepted is False
    assert readiness.all_met() is False


# ---------------------------------------------------------------------------
# determine_decision -- all three decision-vocabulary branches
# ---------------------------------------------------------------------------


def _readiness_all_true() -> ParallelReadinessConditions:
    return ParallelReadinessConditions(True, True, True, True, True, True, True)


def _readiness_all_false() -> ParallelReadinessConditions:
    return ParallelReadinessConditions(False, False, False, False, False, False, False)


def test_determine_decision_blocked_on_accepted_state_boundary_inconsistency() -> None:
    decision = determine_decision(
        boundary_mismatches=["accepted_canonical_boat_models: expected 1770, reproduced 1771"],
        qualifying_breadth_path=None,
        readiness=_readiness_all_true(),
    )
    assert decision is Decision.BLOCKED_ON_ACCEPTED_STATE


def test_determine_decision_continue_stage_3_2_only_when_qualifying_path_found() -> None:
    decision = determine_decision(
        boundary_mismatches=[],
        qualifying_breadth_path=_synthetic_qualifying_candidate(),
        readiness=_readiness_all_true(),
    )
    assert decision is Decision.CONTINUE_STAGE_3_2_ONLY


def test_determine_decision_continue_stage_3_2_only_when_readiness_not_met() -> None:
    decision = determine_decision(
        boundary_mismatches=[],
        qualifying_breadth_path=None,
        readiness=_readiness_all_false(),
    )
    assert decision is Decision.CONTINUE_STAGE_3_2_ONLY


def test_determine_decision_begin_bounded_stage_3_3_in_parallel_on_real_accepted_evidence() -> None:
    reproduced = load_reproduced_boundary()
    mismatches = evaluate_boundary_consistency(reproduced)
    candidates = build_known_breadth_path_candidates(reproduced)
    qualifying = find_qualifying_breadth_path(candidates)
    readiness = evaluate_parallel_readiness(reproduced, qualifying_breadth_path=qualifying)
    decision = determine_decision(
        boundary_mismatches=mismatches, qualifying_breadth_path=qualifying, readiness=readiness
    )
    assert decision is Decision.BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL


def test_boundary_mismatches_take_priority_over_qualifying_path() -> None:
    # Rule 1 (integrity) is applied before rule 2 (breadth path) -- even a
    # synthetic qualifying path must not override a boundary inconsistency.
    decision = determine_decision(
        boundary_mismatches=["some drift"],
        qualifying_breadth_path=_synthetic_qualifying_candidate(),
        readiness=_readiness_all_true(),
    )
    assert decision is Decision.BLOCKED_ON_ACCEPTED_STATE


# ---------------------------------------------------------------------------
# Document assembly + self-consistency verification
# ---------------------------------------------------------------------------


def _build_real_documents() -> tuple[dict[str, Any], dict[str, Any]]:
    reproduced = load_reproduced_boundary()
    candidates = build_known_breadth_path_candidates(reproduced)
    decision_input = build_decision_input_document(
        generated_at="2026-08-25T00:00:00+00:00", reproduced=reproduced, candidates=candidates
    )
    decision_result = build_decision_result_document(
        generated_at="2026-08-25T00:00:00+00:00", decision_input=decision_input
    )
    return decision_input, decision_result


def test_build_decision_result_document_matches_real_committed_decision() -> None:
    _decision_input, decision_result = _build_real_documents()
    assert decision_result["decision"] == "BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL"
    assert decision_result["interpretation"]["declares_stage_3_2_complete"] is False
    assert decision_result["interpretation"]["stage_3_2_remains_open"] is True


def test_verify_decision_result_self_consistency_clean_on_fresh_build() -> None:
    decision_input, decision_result = _build_real_documents()
    assert (
        verify_decision_result_self_consistency(
            decision_input=decision_input, decision_result=decision_result
        )
        == []
    )


def test_verify_decision_result_self_consistency_detects_tampered_decision() -> None:
    decision_input, decision_result = _build_real_documents()
    tampered = copy.deepcopy(decision_result)
    tampered["decision"] = "CONTINUE_STAGE_3_2_ONLY"
    mismatches = verify_decision_result_self_consistency(
        decision_input=decision_input, decision_result=tampered
    )
    assert any("decision" in m for m in mismatches)


def test_verify_decision_result_self_consistency_detects_tampered_readiness() -> None:
    decision_input, decision_result = _build_real_documents()
    tampered = copy.deepcopy(decision_result)
    tampered["parallel_readiness_conditions"]["canonical_count_at_least_1770"] = False
    mismatches = verify_decision_result_self_consistency(
        decision_input=decision_input, decision_result=tampered
    )
    assert any("parallel_readiness_conditions" in m for m in mismatches)


# ---------------------------------------------------------------------------
# verify_artifact_digests_self_consistency (tamper resistance)
# ---------------------------------------------------------------------------


def test_verify_artifact_digests_self_consistency_clean_on_real_committed_package() -> None:
    artifact_digests = json.loads((SL0025_DIR / "ARTIFACT-DIGESTS.json").read_bytes())
    mismatches = verify_artifact_digests_self_consistency(
        artifact_digests=artifact_digests, package_dir=SL0025_DIR
    )
    assert mismatches == []


def _real_digests_with(package_dir: Path, **overrides: str) -> dict[str, Any]:
    """The real committed digest set for every ``ARTIFACT_DIGEST_COVERED_FILENAMES``
    entry, with selected entries overridden -- used so filename-set-drift
    tests exercise only the intended tamper, not an incidental hash
    mismatch."""
    artifact_digests = json.loads((package_dir / "ARTIFACT-DIGESTS.json").read_bytes())
    digests = dict(artifact_digests["digests"])
    digests.update(overrides)
    return digests


def test_verify_artifact_digests_self_consistency_detects_tamper(tmp_path: Path) -> None:
    for name in ARTIFACT_DIGEST_COVERED_FILENAMES:
        (tmp_path / name).write_bytes((SL0025_DIR / name).read_bytes())
    (tmp_path / "decision_result.json").write_text('{"tampered": true}', encoding="utf-8")
    artifact_digests = {"digests": _real_digests_with(SL0025_DIR)}
    mismatches = verify_artifact_digests_self_consistency(
        artifact_digests=artifact_digests, package_dir=tmp_path
    )
    assert len(mismatches) == 1
    assert "decision_result.json" in mismatches[0]


def test_verify_artifact_digests_self_consistency_detects_missing_file(tmp_path: Path) -> None:
    for name in ARTIFACT_DIGEST_COVERED_FILENAMES:
        if name == "decision_result.json":
            continue
        (tmp_path / name).write_bytes((SL0025_DIR / name).read_bytes())
    artifact_digests = {"digests": _real_digests_with(SL0025_DIR)}
    mismatches = verify_artifact_digests_self_consistency(
        artifact_digests=artifact_digests, package_dir=tmp_path
    )
    assert any("decision_result.json" in m and "does not exist" in m for m in mismatches)


# ---------------------------------------------------------------------------
# verify_artifact_digests_self_consistency: exact covered-filename-set
# enforcement (independent of JSON Schema)
# ---------------------------------------------------------------------------


def test_artifact_digest_covered_filenames_matches_real_committed_package() -> None:
    on_disk = {
        p.name for p in SL0025_DIR.iterdir() if p.is_file() and p.name != "ARTIFACT-DIGESTS.json"
    }
    assert set(ARTIFACT_DIGEST_COVERED_FILENAMES) == on_disk


def test_verify_artifact_digests_self_consistency_detects_missing_digest_entry(
    tmp_path: Path,
) -> None:
    for name in ARTIFACT_DIGEST_COVERED_FILENAMES:
        (tmp_path / name).write_bytes((SL0025_DIR / name).read_bytes())
    digests = _real_digests_with(SL0025_DIR)
    del digests["REPORT.md"]
    mismatches = verify_artifact_digests_self_consistency(
        artifact_digests={"digests": digests}, package_dir=tmp_path
    )
    assert any("file-name set" in m and "REPORT.md" in m for m in mismatches)


def test_verify_artifact_digests_self_consistency_detects_unexpected_digest_entry(
    tmp_path: Path,
) -> None:
    for name in ARTIFACT_DIGEST_COVERED_FILENAMES:
        (tmp_path / name).write_bytes((SL0025_DIR / name).read_bytes())
    digests = _real_digests_with(SL0025_DIR, **{"unexpected-file.json": "sha256:" + "0" * 64})
    mismatches = verify_artifact_digests_self_consistency(
        artifact_digests={"digests": digests}, package_dir=tmp_path
    )
    assert any("file-name set" in m and "unexpected-file.json" in m for m in mismatches)


# ---------------------------------------------------------------------------
# verify_decision_input_self_consistency (independent candidate/boundary
# rebuild -- never trusts retained candidate fields as verification inputs)
# ---------------------------------------------------------------------------


def test_candidate_to_dict_matches_real_committed_decision_input_candidates() -> None:
    reproduced = load_reproduced_boundary()
    rebuilt = [candidate_to_dict(c) for c in build_known_breadth_path_candidates(reproduced)]
    decision_input = json.loads((SL0025_DIR / "decision_input.json").read_bytes())
    assert rebuilt == decision_input["known_breadth_path_candidates"]


def test_verify_decision_input_self_consistency_clean_on_real_committed_package() -> None:
    reproduced = load_reproduced_boundary()
    decision_input = json.loads((SL0025_DIR / "decision_input.json").read_bytes())
    assert (
        verify_decision_input_self_consistency(reproduced=reproduced, decision_input=decision_input)
        == []
    )


def test_verify_decision_input_self_consistency_detects_tampered_fixed_boundary() -> None:
    reproduced = load_reproduced_boundary()
    decision_input = json.loads((SL0025_DIR / "decision_input.json").read_bytes())
    tampered = copy.deepcopy(decision_input)
    tampered["fixed_accepted_boundary"]["accepted_canonical_boat_models"] = 1771
    mismatches = verify_decision_input_self_consistency(
        reproduced=reproduced, decision_input=tampered
    )
    assert any("fixed_accepted_boundary" in m for m in mismatches)


def test_verify_decision_input_self_consistency_detects_tampered_boundary_mismatches() -> None:
    reproduced = load_reproduced_boundary()
    decision_input = json.loads((SL0025_DIR / "decision_input.json").read_bytes())
    tampered = copy.deepcopy(decision_input)
    tampered["boundary_mismatches"] = ["fabricated: this drift was never actually detected"]
    mismatches = verify_decision_input_self_consistency(
        reproduced=reproduced, decision_input=tampered
    )
    assert any("boundary_mismatches" in m for m in mismatches)


def test_verify_decision_input_self_consistency_detects_single_field_candidate_tamper() -> None:
    # A tamper that alters only one candidate field (here, a yield bump that
    # does not by itself flip the candidate's ``qualifies()`` result) must
    # still be caught, because the whole candidate is independently rebuilt
    # and compared -- not just re-derived fields that happen to change the
    # decision.
    reproduced = load_reproduced_boundary()
    decision_input = json.loads((SL0025_DIR / "decision_input.json").read_bytes())
    tampered = copy.deepcopy(decision_input)
    tampered["known_breadth_path_candidates"][0]["likely_incremental_yield"] += 1
    mismatches = verify_decision_input_self_consistency(
        reproduced=reproduced, decision_input=tampered
    )
    assert any("known_breadth_path_candidates" in m for m in mismatches)


def test_verify_decision_input_self_consistency_detects_coherent_tamper() -> None:
    # The core coherence attack: alter a candidate's raw fields so it now
    # *qualifies* (flipping what rule 2 would decide), while every other
    # part of decision_input stays byte-identical to the real accepted
    # package. verify_decision_result_self_consistency alone cannot catch
    # this -- it only checks that decision_result agrees with whatever
    # decision_input already says. This function must catch it because it
    # independently rebuilds the candidate from the live reproduced boundary.
    reproduced = load_reproduced_boundary()
    decision_input = json.loads((SL0025_DIR / "decision_input.json").read_bytes())
    tampered = copy.deepcopy(decision_input)
    alt_route = next(
        c
        for c in tampered["known_breadth_path_candidates"]
        if c["name"] == "sl0021_sl0022_alternative_wikidata_route"
    )
    alt_route["already_executed"] = False
    alt_route["likely_incremental_yield"] = 150
    alt_route["qualifies"] = True

    mismatches = verify_decision_input_self_consistency(
        reproduced=reproduced, decision_input=tampered
    )
    assert any("known_breadth_path_candidates" in m for m in mismatches)

    # And the tampered candidate really would flip the mechanical decision,
    # confirming this is exactly the coherent-tamper scenario, not a no-op.
    real_candidate = next(
        c
        for c in KNOWN_BREADTH_PATH_CANDIDATES
        if c.name == "sl0021_sl0022_alternative_wikidata_route"
    )
    assert real_candidate.qualifies() is False
    tampered_candidate = BreadthPathCandidate(
        **{**real_candidate.__dict__, "already_executed": False, "likely_incremental_yield": 150}
    )
    assert tampered_candidate.qualifies() is True
