"""Unit tests for hullq.bootstrap.wikidata_sl0031_corrected_tier1_evidence_profile
— SLICE-0031.

All tests are offline, deterministic, and use small synthetic fixtures rather
than the real 1,770-entity retained SLICE-0028/0030 packages. The predecessor
607/1770 recomputation, the corrected/current five-field marginal-total
reproduction, and the full end-to-end offline verifier are independently
exercised against the real committed
research/stage3/sl0031-corrected-tier1-evidence-profile/ package by
``scripts/bootstrap/wikidata_sl0031_corrected_tier1_evidence_profile_runner.py
--verify`` (run directly and in CI) — the same division of labor already used
by the accepted SLICE-0028/0030 test suites.
"""

from __future__ import annotations

from pathlib import Path

from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
    PTR_BEAM,
    PTR_DISPLACEMENT,
    PTR_DRAFT,
    PTR_LOA,
    PTR_LWL,
    FieldCoverageBucket,
)
from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
    BoatModelFieldCoverage,
    BoatModelFieldDisagreement,
    BoatModelLinkage,
)
from hullq.bootstrap.wikidata_sl0031_corrected_tier1_evidence_profile import (
    EXCLUDED_NEGATIVE_CONTROL_QIDS,
    BoatModelEvidenceProfileRow,
    FieldProfile,
    build_aggregate_profile_document,
    build_artifact_digests,
    build_boatmodel_evidence_profile,
    build_boatmodel_evidence_profile_document,
    build_positive_control_candidates_document,
    compute_aggregate_measurements,
    compute_field_count_distribution,
    compute_precursor_overlap_decomposition,
    compute_strong_evidence_subsets,
    eligible_positive_control_rows,
    rank_positive_control_candidates,
    select_positive_control_candidates,
    verify_aggregate_profile_self_consistency,
    verify_artifact_digests_self_consistency,
    verify_boatmodel_evidence_profile_self_consistency,
    verify_positive_control_candidates_self_consistency,
    verify_reproduces_sl0030_after_coverage,
)

NCP = FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
NO_VAL = FieldCoverageBucket.NO_USABLE_VALUE
UNSUPPORTED = FieldCoverageBucket.UNSUPPORTED_OR_MALFORMED

_EMPTY_COVERAGE_COUNTS = {
    "normalized_candidate_present": 0,
    "source_statement_present": 0,
    "unsupported_or_malformed": 0,
    "no_usable_value": 0,
}


def _row(
    hullq_id: str,
    qids: tuple[str, ...] = ("Q1",),
    *,
    loa: bool = False,
    lwl: bool = False,
    beam: bool = False,
    draft: bool = False,
    displacement: bool = False,
    disagreement: bool = False,
) -> BoatModelEvidenceProfileRow:
    """Directly construct a profile row (bypassing coverage/disagreement
    aggregation) for tests that only exercise aggregate/candidate logic."""
    flags = {"loa": loa, "lwl": lwl, "beam": beam, "draft": draft, "displacement": displacement}
    fields = {
        label: FieldProfile(bucket=NCP if present else NO_VAL, normalized_candidate_present=present)
        for label, present in flags.items()
    }
    return BoatModelEvidenceProfileRow(
        hullq_id=hullq_id,
        qids=qids,
        fields=fields,
        normalized_field_count=sum(flags.values()),
        precursor_satisfied=bool(
            flags["loa"] and flags["beam"] and (flags["draft"] or flags["displacement"])
        ),
        draft_and_displacement_present=bool(flags["draft"] and flags["displacement"]),
        has_disagreement_diagnostic=disagreement,
    )


# ---------------------------------------------------------------------------
# verify_reproduces_sl0030_after_coverage
# ---------------------------------------------------------------------------


def test_verify_reproduces_sl0030_after_coverage_accepts_exact_match() -> None:
    counts = {
        "loa": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 888},
        "lwl": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 848},
        "beam": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 891},
        "draft": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 691},
        "displacement": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 858},
    }
    assert verify_reproduces_sl0030_after_coverage(counts) == []


def test_verify_reproduces_sl0030_after_coverage_flags_drift() -> None:
    counts = {
        "loa": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 887},
        "lwl": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 848},
        "beam": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 891},
        "draft": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 691},
        "displacement": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 858},
    }
    problems = verify_reproduces_sl0030_after_coverage(counts)
    assert len(problems) == 1
    assert "loa" in problems[0]


# ---------------------------------------------------------------------------
# build_boatmodel_evidence_profile — joint per-BoatModel aggregation, never
# derived arithmetically from marginal per-field totals
# ---------------------------------------------------------------------------


def _coverage(hullq_id: str, present_pointers: set) -> list[BoatModelFieldCoverage]:
    all_pointers = (PTR_LOA, PTR_LWL, PTR_BEAM, PTR_DRAFT, PTR_DISPLACEMENT)
    return [
        BoatModelFieldCoverage(
            hullq_id=hullq_id,
            field_pointer=ptr,
            bucket=NCP if ptr in present_pointers else NO_VAL,
            contributing_qids=("Q1",) if ptr in present_pointers else (),
        )
        for ptr in all_pointers
    ]


def test_profile_precursor_is_joint_not_arithmetic_from_marginals() -> None:
    """Model X has LOA+beam but no draft/displacement; model Y has draft but
    no LOA/beam. Each individual field's marginal count is >=1, but neither
    model individually satisfies LOA + beam + (draft OR displacement) — the
    joint per-model precursor count must be 0, not "derived" as 1 from the
    nonzero marginal totals."""
    linkage = [
        BoatModelLinkage(hullq_id="BM_X", qids=("QX",), preferred_label_by_qid={"QX": "X"}),
        BoatModelLinkage(hullq_id="BM_Y", qids=("QY",), preferred_label_by_qid={"QY": "Y"}),
    ]
    coverage = [
        *_coverage("BM_X", {PTR_LOA, PTR_BEAM}),
        *_coverage("BM_Y", {PTR_DRAFT}),
    ]
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    assert not rows[0].precursor_satisfied
    assert not rows[1].precursor_satisfied

    measurements = compute_aggregate_measurements(
        rows,
        per_field_corrected_coverage={
            "loa": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 1},
            "lwl": _EMPTY_COVERAGE_COUNTS,
            "beam": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 1},
            "draft": {**_EMPTY_COVERAGE_COUNTS, "normalized_candidate_present": 1},
            "displacement": _EMPTY_COVERAGE_COUNTS,
        },
        predecessor_precursor_count=0,
    )
    assert measurements["corrected_precursor"]["count"] == 0


def test_profile_loa_beam_draft_no_displacement_satisfies_precursor() -> None:
    linkage = [BoatModelLinkage(hullq_id="BM_A", qids=("QA",), preferred_label_by_qid={"QA": "A"})]
    coverage = _coverage("BM_A", {PTR_LOA, PTR_BEAM, PTR_DRAFT})
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    assert rows[0].precursor_satisfied is True


def test_profile_loa_beam_displacement_no_draft_satisfies_precursor() -> None:
    linkage = [BoatModelLinkage(hullq_id="BM_B", qids=("QB",), preferred_label_by_qid={"QB": "B"})]
    coverage = _coverage("BM_B", {PTR_LOA, PTR_BEAM, PTR_DISPLACEMENT})
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    assert rows[0].precursor_satisfied is True


def test_profile_missing_loa_does_not_satisfy_precursor_even_with_draft_and_displacement() -> None:
    linkage = [BoatModelLinkage(hullq_id="BM_C", qids=("QC",), preferred_label_by_qid={"QC": "C"})]
    coverage = _coverage("BM_C", {PTR_BEAM, PTR_DRAFT, PTR_DISPLACEMENT})
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    assert rows[0].precursor_satisfied is False


def test_profile_missing_beam_does_not_satisfy_precursor_even_with_draft_and_displacement() -> None:
    linkage = [BoatModelLinkage(hullq_id="BM_D", qids=("QD",), preferred_label_by_qid={"QD": "D"})]
    coverage = _coverage("BM_D", {PTR_LOA, PTR_DRAFT, PTR_DISPLACEMENT})
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    assert rows[0].precursor_satisfied is False


def test_profile_normalized_field_count_bounded_0_to_5() -> None:
    linkage = [
        BoatModelLinkage(hullq_id="BM_E", qids=("QE",), preferred_label_by_qid={"QE": "E"}),
        BoatModelLinkage(hullq_id="BM_F", qids=("QF",), preferred_label_by_qid={"QF": "F"}),
    ]
    coverage = [
        *_coverage("BM_E", set()),
        *_coverage("BM_F", {PTR_LOA, PTR_LWL, PTR_BEAM, PTR_DRAFT, PTR_DISPLACEMENT}),
    ]
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    by_id = {r.hullq_id: r for r in rows}
    assert by_id["BM_E"].normalized_field_count == 0
    assert by_id["BM_F"].normalized_field_count == 5
    assert all(0 <= r.normalized_field_count <= 5 for r in rows)


def test_profile_flags_disagreement_diagnostic() -> None:
    linkage = [BoatModelLinkage(hullq_id="BM_G", qids=("QG",), preferred_label_by_qid={"QG": "G"})]
    coverage = _coverage("BM_G", {PTR_LOA, PTR_LWL, PTR_BEAM, PTR_DRAFT, PTR_DISPLACEMENT})
    disagreement = (
        BoatModelFieldDisagreement(
            hullq_id="BM_G",
            field_pointer=PTR_LOA,
            normalized_candidate_count=2,
            distinct_normalized_values=("1.0 m", "2.0 m"),
            contributing_qid_count=1,
            unsupported_coexists_with_normalized=False,
        ),
    )
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=disagreement)
    assert rows[0].has_disagreement_diagnostic is True


def test_boatmodel_evidence_profile_document_self_consistency_and_tamper() -> None:
    linkage = [BoatModelLinkage(hullq_id="BM_H", qids=("QH",), preferred_label_by_qid={"QH": "H"})]
    coverage = _coverage("BM_H", {PTR_LOA, PTR_BEAM})
    rows = build_boatmodel_evidence_profile(linkage, coverage, disagreements=())
    doc = build_boatmodel_evidence_profile_document(
        generated_at="2026-01-01T00:00:00+00:00", rows=rows
    )
    assert (
        verify_boatmodel_evidence_profile_self_consistency(
            linkage=linkage, boat_model_coverage=coverage, disagreements=(), document=doc
        )
        == []
    )

    tampered = dict(doc)
    tampered["boat_models"] = []
    problems = verify_boatmodel_evidence_profile_self_consistency(
        linkage=linkage, boat_model_coverage=coverage, disagreements=(), document=tampered
    )
    assert problems


# ---------------------------------------------------------------------------
# Aggregate distribution / overlap / strong-subset helpers
# ---------------------------------------------------------------------------


def test_field_count_distribution_sums_to_total() -> None:
    rows = [
        _row("A", loa=True, beam=True, draft=True, displacement=True, lwl=True),
        _row("B", loa=True, beam=True),
        _row("C"),
    ]
    dist = compute_field_count_distribution(rows)
    assert dist["5"] == 1
    assert dist["2"] == 1
    assert dist["0"] == 1
    assert sum(dist.values()) == len(rows)


def test_precursor_overlap_decomposition() -> None:
    rows = [
        _row("A", loa=True, beam=True, draft=True),  # draft only
        _row("B", loa=True, beam=True, displacement=True),  # displacement only
        _row("C", loa=True, beam=True, draft=True, displacement=True),  # both
        _row("D", draft=True),  # precursor not satisfied -- excluded
    ]
    overlap = compute_precursor_overlap_decomposition(rows)
    assert overlap == {"draft_only": 1, "displacement_only": 1, "both": 1}


def test_strong_evidence_subsets() -> None:
    rows = [
        _row("A", loa=True, beam=True, draft=True, displacement=True),  # 4/5, no lwl
        _row("B", loa=True, lwl=True, beam=True, draft=True),  # loa+lwl+beam+draft
        _row("C", loa=True, lwl=True, beam=True, draft=True, displacement=True),  # all 5
        _row("D", loa=True, lwl=True, beam=True, draft=True, displacement=True, disagreement=True),
    ]
    subsets = compute_strong_evidence_subsets(rows)
    assert (
        subsets["loa_beam_draft_displacement"] == 3
    )  # A, C and D (disagreement is irrelevant here)
    assert subsets["loa_lwl_beam_draft_or_displacement"] == 3  # B, C, D
    assert subsets["all_five_fields"] == 2  # C and D
    assert subsets["gte4_normalized_no_disagreement"] == 3  # A, B, C (D flagged)


def test_aggregate_profile_document_self_consistency_and_tamper() -> None:
    rows = [
        _row("A", loa=True, lwl=True, beam=True, draft=True, displacement=True),
        _row("B", loa=True, beam=True, draft=True),
    ]
    per_field = {
        label: dict(_EMPTY_COVERAGE_COUNTS)
        for label in ("loa", "lwl", "beam", "draft", "displacement")
    }
    doc = build_aggregate_profile_document(
        generated_at="2026-01-01T00:00:00+00:00",
        rows=rows,
        per_field_corrected_coverage=per_field,
        predecessor_precursor_count=1,
    )
    assert doc["corrected_precursor"]["count"] == 2
    assert doc["predecessor_precursor"]["count"] == 1
    assert doc["precursor_delta"]["absolute"] == 1
    assert (
        verify_aggregate_profile_self_consistency(
            rows=rows,
            per_field_corrected_coverage=per_field,
            predecessor_precursor_count=1,
            document=doc,
        )
        == []
    )

    tampered = dict(doc)
    tampered["corrected_precursor"] = dict(doc["corrected_precursor"])
    tampered["corrected_precursor"]["count"] = 999
    problems = verify_aggregate_profile_self_consistency(
        rows=rows,
        per_field_corrected_coverage=per_field,
        predecessor_precursor_count=1,
        document=tampered,
    )
    assert problems


# ---------------------------------------------------------------------------
# Positive-control candidate eligibility / ranking / pool result
# ---------------------------------------------------------------------------


def test_eligibility_requires_precursor_and_at_least_4_fields_and_no_disagreement() -> None:
    rows = [
        _row("A", loa=True, beam=True, draft=True, displacement=True, lwl=True),  # eligible
        _row("B", loa=True, beam=True, draft=True),  # only 3 fields -- not eligible
        _row("C", loa=True, beam=True, draft=True, displacement=True, disagreement=True),  # flagged
        _row(
            "D", draft=True, displacement=True, beam=True, lwl=True
        ),  # missing LOA -- no precursor
    ]
    eligible = eligible_positive_control_rows(rows)
    assert [r.hullq_id for r in eligible] == ["A"]


def test_negative_control_qids_excluded_even_if_otherwise_eligible() -> None:
    for qid in EXCLUDED_NEGATIVE_CONTROL_QIDS:
        row = _row(
            "BM_NC", qids=(qid,), loa=True, beam=True, draft=True, displacement=True, lwl=True
        )
        assert eligible_positive_control_rows([row]) == ()


def test_ranking_order_field_count_then_both_then_lwl_then_hullq_id() -> None:
    rows = [
        _row("Z", loa=True, beam=True, draft=True, displacement=True, lwl=True),  # 5, both, lwl
        _row("A", loa=True, beam=True, draft=True, displacement=True),  # 4, both, no lwl
        _row("B", loa=True, beam=True, draft=True, lwl=True),  # 4, draft only, lwl
        _row("Y", loa=True, beam=True, displacement=True, lwl=True),  # 4, disp only, lwl
    ]
    ranked = rank_positive_control_candidates(rows)
    assert [c.hullq_id for c in ranked] == ["Z", "A", "B", "Y"]


def test_ranking_stable_tie_break_by_hullq_id_ascending() -> None:
    rows = [
        _row("BM_C", loa=True, beam=True, draft=True, displacement=True, lwl=True),
        _row("BM_A", loa=True, beam=True, draft=True, displacement=True, lwl=True),
        _row("BM_B", loa=True, beam=True, draft=True, displacement=True, lwl=True),
    ]
    ranked = rank_positive_control_candidates(rows)
    assert [c.hullq_id for c in ranked] == ["BM_A", "BM_B", "BM_C"]


def test_select_positive_control_candidates_respects_limit() -> None:
    rows = [
        _row(f"BM_{i:02d}", loa=True, beam=True, draft=True, displacement=True, lwl=True)
        for i in range(25)
    ]
    selected = select_positive_control_candidates(rows, limit=20)
    assert len(selected) == 20
    assert [c.rank for c in selected] == list(range(1, 21))


def test_pool_result_available_and_none() -> None:
    eligible_row = _row("A", loa=True, beam=True, draft=True, displacement=True, lwl=True)
    doc_available = build_positive_control_candidates_document(
        generated_at="2026-01-01T00:00:00+00:00", rows=[eligible_row]
    )
    assert doc_available["pool_result"] == "POSITIVE_CONTROL_POOL_AVAILABLE"
    assert doc_available["candidate_pool_size"] == 1

    ineligible_row = _row("B", loa=True, beam=True, draft=True)
    doc_empty = build_positive_control_candidates_document(
        generated_at="2026-01-01T00:00:00+00:00", rows=[ineligible_row]
    )
    assert doc_empty["pool_result"] == "NO_POSITIVE_CONTROL_POOL"
    assert doc_empty["candidate_pool_size"] == 0


def test_positive_control_candidates_document_self_consistency_and_tamper() -> None:
    rows = [
        _row("A", loa=True, beam=True, draft=True, displacement=True, lwl=True),
        _row("B", loa=True, beam=True, draft=True),
    ]
    doc = build_positive_control_candidates_document(
        generated_at="2026-01-01T00:00:00+00:00", rows=rows
    )
    assert verify_positive_control_candidates_self_consistency(rows=rows, document=doc) == []

    tampered = dict(doc)
    tampered["pool_result"] = "NO_POSITIVE_CONTROL_POOL"
    problems = verify_positive_control_candidates_self_consistency(rows=rows, document=tampered)
    assert problems


# ---------------------------------------------------------------------------
# Artifact digests
# ---------------------------------------------------------------------------


def test_artifact_digests_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text('{"x": 1}\n', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"y": 2}\n', encoding="utf-8")

    digests = build_artifact_digests(generated_at="2026-01-01T00:00:00+00:00", package_dir=tmp_path)
    assert (
        verify_artifact_digests_self_consistency(artifact_digests=digests, package_dir=tmp_path)
        == []
    )

    (tmp_path / "a.json").write_text('{"x": 2}\n', encoding="utf-8")
    problems = verify_artifact_digests_self_consistency(
        artifact_digests=digests, package_dir=tmp_path
    )
    assert problems


# ---------------------------------------------------------------------------
# Canonical mutation boundary -- mechanically enforced, not merely claimed
# ---------------------------------------------------------------------------


def test_module_performs_no_persistence_or_network_import() -> None:
    import hullq.bootstrap.wikidata_sl0031_corrected_tier1_evidence_profile as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "hullq.persistence" not in source
    assert "httpx" not in source
