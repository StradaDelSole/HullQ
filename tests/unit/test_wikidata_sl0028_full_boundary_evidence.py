"""Unit tests for the SLICE-0028 full-boundary Wikidata Tier-1 evidence rollout pure logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
    ALLOWED_FIELD_POINTERS,
    PTR_BEAM,
    PTR_DISPLACEMENT,
    PTR_DRAFT,
    PTR_LOA,
    EntityFieldCoverage,
    FieldCoverageBucket,
    IdentityBoundary,
    filter_to_allowed_evidence,
    load_reproduced_identity_boundary,
    summarize_field_coverage,
)
from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
    ARTIFACT_DIGESTS_FILENAME,
    BoatModelLinkage,
    build_artifact_digests,
    build_basic_searchable_precursor_document,
    build_coverage_document,
    build_disagreement_document,
    build_evidence_manifest_document,
    build_full_boundary_linkage,
    build_historical_registry_reconciliation_block,
    build_linkage_document,
    build_sl0028_bundle,
    classify_boat_model_field_coverage,
    compute_basic_searchable_evidence_precursor,
    compute_boat_model_field_disagreements,
    distinct_request_qids,
    load_full_historical_registry_reconciliation,
    rebuild_entities_from_manifest,
    retained_package_filenames,
    summarize_boat_model_field_coverage,
    verify_artifact_digests_self_consistency,
    verify_basic_searchable_precursor_self_consistency,
    verify_coverage_self_consistency,
    verify_disagreement_self_consistency,
    verify_evidence_manifest_self_consistency,
    verify_full_boundary_linkage,
    verify_linkage_document_self_consistency,
)
from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig, WikidataEntityData

_SOURCE = {"source_id": "SRC_WIKIDATA_API_2026"}
_CONFIG = WikidataAdapterConfig(user_agent="HullQ/0.1 (test@example.com)")


def _extract(entities: list[WikidataEntityData]) -> tuple[list[Any], Any]:
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=_SOURCE, config=_CONFIG, http_client=client)
        return adapter.extract_field_evidence(
            entities, retrieved_at="2026-01-01T00:00:00Z", requested_qid_count=len(entities)
        )


def _quantity_claim(
    amount: str,
    unit_qid: str | None,
    qualifier_qid: str | None = None,
    qualifier_prop: str = "P642",
) -> dict[str, Any]:
    unit = f"http://www.wikidata.org/entity/{unit_qid}" if unit_qid else "1"
    claim: dict[str, Any] = {
        "id": f"stmt-{amount}-{qualifier_qid}",
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"type": "quantity", "value": {"amount": amount, "unit": unit}},
        },
    }
    if qualifier_qid:
        claim["qualifiers"] = {
            qualifier_prop: [
                {
                    "snaktype": "value",
                    "datavalue": {"type": "wikibase-entityid", "value": {"id": qualifier_qid}},
                }
            ]
        }
    return claim


def json_copy_with(doc: dict[str, Any], path: tuple[str, ...], value: Any) -> dict[str, Any]:
    """Deep-copy *doc* and override the nested key at *path* with *value* —
    a small test-only helper for building a single-field-tampered document
    without hand-writing a full nested dict literal per test."""
    import copy

    copied = copy.deepcopy(doc)
    node = copied
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return copied


def _boundary(
    pairs: tuple[tuple[str, str], ...], *, canonical_count: int | None = None
) -> IdentityBoundary:
    """A synthetic IdentityBoundary for pure-logic tests. IdentityBoundary
    itself enforces no bijection (that is the loader's job) so a test may
    freely construct one with multiplicity."""
    hullq_ids = {hid for _qid, hid in pairs}
    return IdentityBoundary(
        baseline_manifest_sha256="a" * 64,
        delta_manifest_sha256="b" * 64,
        canonical_boat_model_count=canonical_count
        if canonical_count is not None
        else len(hullq_ids),
        historical_crosswalk_count=len(pairs),
        auto_admit_qid_to_hullq_id=pairs,
        preferred_label_by_qid={qid: f"label-{qid}" for qid, _hid in pairs},
    )


# ---------------------------------------------------------------------------
# build_full_boundary_linkage / distinct_request_qids / verify_full_boundary_linkage
# ---------------------------------------------------------------------------


def test_build_full_boundary_linkage_bijective_case() -> None:
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_B")))
    linkage = build_full_boundary_linkage(boundary)
    assert len(linkage) == 2
    assert linkage[0].hullq_id == "BM_A"
    assert linkage[0].qids == ("Q1",)
    assert linkage[1].hullq_id == "BM_B"
    assert linkage[1].qids == ("Q2",)


def test_build_full_boundary_linkage_preserves_multiplicity() -> None:
    """A BoatModel with more than one accepted QID must retain every one of
    them -- never silently collapsed to a single QID."""
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_A"), ("Q3", "BM_B")), canonical_count=2)
    linkage = build_full_boundary_linkage(boundary)
    assert len(linkage) == 2
    by_id = {e.hullq_id: e for e in linkage}
    assert by_id["BM_A"].qids == ("Q1", "Q2")
    assert by_id["BM_B"].qids == ("Q3",)


def test_distinct_request_qids_sorted_deduplicated() -> None:
    boundary = _boundary((("Q10", "BM_A"), ("Q2", "BM_A"), ("Q3", "BM_B")), canonical_count=2)
    linkage = build_full_boundary_linkage(boundary)
    assert distinct_request_qids(linkage) == ("Q10", "Q2", "Q3")


def test_boat_model_linkage_rejects_empty_qids() -> None:
    with pytest.raises(ValueError, match="at least one QID"):
        BoatModelLinkage(hullq_id="BM_A", qids=(), preferred_label_by_qid={})


def test_boat_model_linkage_dedupes_and_sorts_qids() -> None:
    entry = BoatModelLinkage(hullq_id="BM_A", qids=("Q2", "Q1", "Q2"), preferred_label_by_qid={})
    assert entry.qids == ("Q1", "Q2")


def test_verify_full_boundary_linkage_detects_missing_boat_model() -> None:
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_B")))
    linkage = build_full_boundary_linkage(boundary)[:1]  # drop BM_B
    problems = verify_full_boundary_linkage(boundary=boundary, linkage=linkage)
    assert any("BoatModel entries" in p for p in problems)
    assert any("value set" in p for p in problems)
    assert any("QID set" in p for p in problems)


def test_verify_full_boundary_linkage_passes_for_correct_linkage() -> None:
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_A"), ("Q3", "BM_B")), canonical_count=2)
    linkage = build_full_boundary_linkage(boundary)
    assert verify_full_boundary_linkage(boundary=boundary, linkage=linkage) == []


def test_verify_full_boundary_linkage_detects_duplicate_hullq_id() -> None:
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_B")))
    linkage = (
        BoatModelLinkage(hullq_id="BM_A", qids=("Q1",), preferred_label_by_qid={}),
        BoatModelLinkage(hullq_id="BM_A", qids=("Q2",), preferred_label_by_qid={}),
    )
    problems = verify_full_boundary_linkage(boundary=boundary, linkage=linkage)
    assert any("duplicate BoatModel hullq_id" in p for p in problems)


# ---------------------------------------------------------------------------
# real accepted boundary reproduces / linkage matches it
# ---------------------------------------------------------------------------


def test_real_boundary_linkage_reproduces_1770_and_matches() -> None:
    boundary = load_reproduced_identity_boundary()
    linkage = build_full_boundary_linkage(boundary)
    assert len(linkage) == 1770
    assert len(distinct_request_qids(linkage)) == 1770
    assert verify_full_boundary_linkage(boundary=boundary, linkage=linkage) == []
    # Real accepted boundary is bijective today: every BoatModel has exactly
    # one accepted QID (the linkage code itself never assumes this).
    assert all(len(e.qids) == 1 for e in linkage)


# ---------------------------------------------------------------------------
# linkage document build/verify round trip
# ---------------------------------------------------------------------------


def test_linkage_document_round_trip() -> None:
    """Pure composition test with a synthetic boundary (not tied to real
    manifest files on disk) -- the historical-registry reconciliation block
    is built directly (``build_historical_registry_reconciliation_block``,
    no file I/O), not via ``load_full_historical_registry_reconciliation``
    (which requires a boundary whose historical_crosswalk_count matches the
    real retained SLICE-0017/0018 manifests; exercised separately below
    against the real boundary)."""
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_A"), ("Q3", "BM_B")), canonical_count=2)
    linkage = build_full_boundary_linkage(boundary)
    reconciliation = build_historical_registry_reconciliation_block(
        boundary=boundary, reserved_entries=()
    )
    doc = build_linkage_document(
        generated_at="2026-01-01T00:00:00Z",
        boundary=boundary,
        linkage=linkage,
        historical_registry_reconciliation=reconciliation,
    )
    assert doc["boat_model_count"] == 2
    assert doc["distinct_request_qid_count"] == 3
    assert doc["historical_registry_reconciliation"]["historical_registry_count"] == 3
    assert doc["historical_registry_reconciliation"]["canonical_auto_admit_linkage_count"] == 2


def test_linkage_document_self_consistency_detects_tamper() -> None:
    boundary = load_reproduced_identity_boundary()
    linkage = build_full_boundary_linkage(boundary)
    _full_crosswalk, reserved_entries = load_full_historical_registry_reconciliation(
        boundary=boundary
    )
    reconciliation = build_historical_registry_reconciliation_block(
        boundary=boundary, reserved_entries=reserved_entries
    )
    doc = build_linkage_document(
        generated_at="t",
        boundary=boundary,
        linkage=linkage,
        historical_registry_reconciliation=reconciliation,
    )
    tampered = dict(doc)
    tampered["boat_model_count"] = 999
    problems = verify_linkage_document_self_consistency(boundary=boundary, document=tampered)
    assert problems


# ---------------------------------------------------------------------------
# 1,772 historical registry vs 1,770 canonical AUTO_ADMIT linkage reconciliation
# ---------------------------------------------------------------------------


def test_real_historical_registry_reconciliation_has_exactly_two_reserved_entries() -> None:
    """SLICE-0028 review clarification: the accepted 1,772-entry historical
    registry minus the 1,770-entry canonical AUTO_ADMIT linkage is exactly 2
    non-canonical REVIEW_REQUIRED reserved-ID crosswalk entries -- never
    silently equated with the acquisition request set."""
    boundary = load_reproduced_identity_boundary()
    full_crosswalk, reserved_entries = load_full_historical_registry_reconciliation(
        boundary=boundary
    )
    assert len(full_crosswalk) == 1772
    assert len(reserved_entries) == 2
    assert {e.qid for e in reserved_entries} == {"Q109650429", "Q2461915"}
    for e in reserved_entries:
        assert e.decision == "review_required"
        assert "name_collision" in e.reason_codes
        assert e.reserved_hullq_id == full_crosswalk[e.qid]
        # A reserved QID must never appear in the canonical AUTO_ADMIT linkage.
        assert e.qid not in {qid for qid, _hid in boundary.auto_admit_qid_to_hullq_id}


def test_historical_registry_reconciliation_block_composition() -> None:
    boundary = load_reproduced_identity_boundary()
    _full_crosswalk, reserved_entries = load_full_historical_registry_reconciliation(
        boundary=boundary
    )
    block = build_historical_registry_reconciliation_block(
        boundary=boundary, reserved_entries=reserved_entries
    )
    assert block["historical_registry_count"] == 1772
    assert block["canonical_auto_admit_linkage_count"] == 1770
    assert block["non_canonical_reserved_count"] == 2
    assert (
        block["historical_registry_count"]
        == block["canonical_auto_admit_linkage_count"] + block["non_canonical_reserved_count"]
    )
    assert len(block["reserved_entries"]) == 2


def test_real_linkage_document_round_trip_with_reconciliation() -> None:
    boundary = load_reproduced_identity_boundary()
    linkage = build_full_boundary_linkage(boundary)
    _full_crosswalk, reserved_entries = load_full_historical_registry_reconciliation(
        boundary=boundary
    )
    reconciliation = build_historical_registry_reconciliation_block(
        boundary=boundary, reserved_entries=reserved_entries
    )
    doc = build_linkage_document(
        generated_at="t",
        boundary=boundary,
        linkage=linkage,
        historical_registry_reconciliation=reconciliation,
    )
    assert verify_linkage_document_self_consistency(boundary=boundary, document=doc) == []


def test_load_full_historical_registry_reconciliation_fails_closed_on_count_mismatch() -> None:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        IdentityBoundaryIntegrityError,
    )

    boundary = load_reproduced_identity_boundary()
    tampered_boundary = IdentityBoundary(
        baseline_manifest_sha256=boundary.baseline_manifest_sha256,
        delta_manifest_sha256=boundary.delta_manifest_sha256,
        canonical_boat_model_count=boundary.canonical_boat_model_count,
        historical_crosswalk_count=9999,
        auto_admit_qid_to_hullq_id=boundary.auto_admit_qid_to_hullq_id,
        preferred_label_by_qid=boundary.preferred_label_by_qid,
    )
    with pytest.raises(IdentityBoundaryIntegrityError, match="Reconciled full historical registry"):
        load_full_historical_registry_reconciliation(boundary=tampered_boundary)


# ---------------------------------------------------------------------------
# classify_boat_model_field_coverage / summarize_boat_model_field_coverage
# ---------------------------------------------------------------------------


def test_classify_boat_model_field_coverage_precedence() -> None:
    NCP = FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    SSP = FieldCoverageBucket.SOURCE_STATEMENT_PRESENT
    UOM = FieldCoverageBucket.UNSUPPORTED_OR_MALFORMED
    NUV = FieldCoverageBucket.NO_USABLE_VALUE

    assert classify_boat_model_field_coverage({"Q1": NUV, "Q2": UOM}) == UOM
    assert classify_boat_model_field_coverage({"Q1": UOM, "Q2": SSP}) == SSP
    assert classify_boat_model_field_coverage({"Q1": SSP, "Q2": NCP}) == NCP
    assert classify_boat_model_field_coverage({"Q1": NUV}) == NUV
    assert classify_boat_model_field_coverage({}) == NUV


def test_summarize_boat_model_field_coverage_aggregates_across_multiple_qids() -> None:
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_A")), canonical_count=1)
    linkage = build_full_boundary_linkage(boundary)
    details = (
        EntityFieldCoverage(
            qid="Q1", field_pointer=PTR_LOA, bucket=FieldCoverageBucket.NO_USABLE_VALUE
        ),
        EntityFieldCoverage(
            qid="Q2", field_pointer=PTR_LOA, bucket=FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
        ),
    )
    counts, results = summarize_boat_model_field_coverage(linkage, details)
    loa_result = next(r for r in results if r.field_pointer == PTR_LOA)
    assert loa_result.bucket == FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    assert loa_result.contributing_qids == ("Q2",)
    assert counts["loa"]["normalized_candidate_present"] == 1
    assert counts["loa"]["no_usable_value"] == 0


def test_summarize_boat_model_field_coverage_missing_detail_defaults_no_usable() -> None:
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    counts, results = summarize_boat_model_field_coverage(linkage, ())
    assert all(r.bucket == FieldCoverageBucket.NO_USABLE_VALUE for r in results)
    for label in ("loa", "lwl", "beam", "draft", "displacement"):
        assert counts[label]["no_usable_value"] == 1


def test_coverage_document_round_trip_against_real_entities() -> None:
    entity_a = WikidataEntityData(
        qid="Q1",
        label="Boat A",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("12.5", "Q11573", "Q2358152")]},
    )
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity_a])
    source_counts, source_details = summarize_field_coverage([entity_a], full_evidence)
    boat_model_counts, _details = summarize_boat_model_field_coverage(linkage, source_details)
    doc = build_coverage_document(
        generated_at="t",
        boat_model_count=len(linkage),
        source_qid_count=1,
        source_qid_coverage_counts=source_counts,
        boat_model_coverage_counts=boat_model_counts,
    )
    assert doc["boat_model_level"]["loa"]["normalized_candidate_present"] == 1
    assert (
        verify_coverage_self_consistency(
            linkage=linkage, entities=[entity_a], full_evidence=full_evidence, document=doc
        )
        == []
    )


def test_coverage_document_self_consistency_detects_tamper() -> None:
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    entity_a = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    full_evidence, _report = _extract([entity_a])
    source_counts, source_details = summarize_field_coverage([entity_a], full_evidence)
    boat_model_counts, _details = summarize_boat_model_field_coverage(linkage, source_details)
    doc = build_coverage_document(
        generated_at="t",
        boat_model_count=1,
        source_qid_count=1,
        source_qid_coverage_counts=source_counts,
        boat_model_coverage_counts=boat_model_counts,
    )
    tampered = dict(doc)
    tampered["boat_model_count"] = 42
    assert verify_coverage_self_consistency(
        linkage=linkage, entities=[entity_a], full_evidence=full_evidence, document=tampered
    )


# ---------------------------------------------------------------------------
# compute_boat_model_field_disagreements
# ---------------------------------------------------------------------------


def test_disagreement_flags_multi_candidate_and_multi_value_within_one_qid() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat A",
        aliases=[],
        raw_claims={
            "P2043": [
                _quantity_claim("12.5", "Q11573", "Q2358152"),
                _quantity_claim("13.0", "Q11573", "Q2358152"),
            ]
        },
    )
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity])
    _counts, details = summarize_field_coverage([entity], full_evidence)
    disagreements = compute_boat_model_field_disagreements(
        linkage, [entity], full_evidence, details
    )
    loa_case = next(d for d in disagreements if d.field_pointer == PTR_LOA)
    assert loa_case.normalized_candidate_count == 2
    assert len(loa_case.distinct_normalized_values) == 2
    assert loa_case.contributing_qid_count == 1
    assert loa_case.unsupported_coexists_with_normalized is False


def test_disagreement_flags_unsupported_coexisting_with_normalized_across_qids() -> None:
    entity_normal = WikidataEntityData(
        qid="Q3",
        label="Boat C",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("10.0", "Q11573", "Q2358152")]},
    )
    entity_unsupported = WikidataEntityData(
        qid="Q4",
        label="Boat D",
        aliases=[],
        # P642 qualifier value Q999999 is not a recognized concept QID -> unsupported.
        raw_claims={"P2043": [_quantity_claim("10.0", "Q11573", "Q999999")]},
    )
    boundary = _boundary((("Q3", "BM_C"), ("Q4", "BM_C")), canonical_count=1)
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity_normal, entity_unsupported])
    entities = [entity_normal, entity_unsupported]
    _counts, details = summarize_field_coverage(entities, full_evidence)
    disagreements = compute_boat_model_field_disagreements(
        linkage, entities, full_evidence, details
    )
    loa_case = next(d for d in disagreements if d.field_pointer == PTR_LOA)
    assert loa_case.unsupported_coexists_with_normalized is True


def test_disagreement_flags_unsupported_coexisting_with_normalized_within_same_qid() -> None:
    """SLICE-0028 review finding: a single QID with BOTH a correctly-qualified
    statement (normalized) AND another unsupported/malformed statement on the
    SAME shared property must still be flagged -- the per-QID coverage bucket
    alone (NORMALIZED_CANDIDATE_PRESENT takes precedence over
    UNSUPPORTED_OR_MALFORMED) cannot reveal this by itself."""
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat Mixed",
        aliases=[],
        raw_claims={
            "P2043": [
                _quantity_claim("12.5", "Q11573", "Q2358152"),  # recognized LOA -> normalized
                _quantity_claim(
                    "9.9", "Q11573", "Q999999"
                ),  # unrecognized qualifier -> unsupported
            ]
        },
    )
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity])
    _counts, details = summarize_field_coverage([entity], full_evidence)
    disagreements = compute_boat_model_field_disagreements(
        linkage, [entity], full_evidence, details
    )
    loa_case = next(d for d in disagreements if d.field_pointer == PTR_LOA)
    assert loa_case.normalized_candidate_count == 1
    assert loa_case.contributing_qid_count == 1
    assert loa_case.unsupported_coexists_with_normalized is True


def test_disagreement_flags_multi_qid_contribution() -> None:
    entity_5 = WikidataEntityData(
        qid="Q5",
        label="Boat E",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("9.0", "Q11573", "Q2358152")]},
    )
    entity_6 = WikidataEntityData(
        qid="Q6",
        label="Boat F",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("9.0", "Q11573", "Q2358152")]},
    )
    boundary = _boundary((("Q5", "BM_E"), ("Q6", "BM_E")), canonical_count=1)
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity_5, entity_6])
    entities = [entity_5, entity_6]
    _counts, details = summarize_field_coverage(entities, full_evidence)
    disagreements = compute_boat_model_field_disagreements(
        linkage, entities, full_evidence, details
    )
    loa_case = next(d for d in disagreements if d.field_pointer == PTR_LOA)
    assert loa_case.contributing_qid_count == 2


def test_disagreement_empty_for_clean_single_candidate() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat A",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("12.5", "Q11573", "Q2358152")]},
    )
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity])
    _counts, details = summarize_field_coverage([entity], full_evidence)
    disagreements = compute_boat_model_field_disagreements(
        linkage, [entity], full_evidence, details
    )
    assert not any(d.field_pointer == PTR_LOA for d in disagreements)


def test_disagreement_document_round_trip() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat A",
        aliases=[],
        raw_claims={
            "P2043": [
                _quantity_claim("12.5", "Q11573", "Q2358152"),
                _quantity_claim("13.0", "Q11573", "Q2358152"),
            ]
        },
    )
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, _report = _extract([entity])
    _counts, details = summarize_field_coverage([entity], full_evidence)
    disagreements = compute_boat_model_field_disagreements(
        linkage, [entity], full_evidence, details
    )
    doc = build_disagreement_document(generated_at="t", disagreements=disagreements)
    assert doc["flagged_case_count"] == len(disagreements)
    assert (
        verify_disagreement_self_consistency(
            linkage=linkage,
            entities=[entity],
            full_evidence=full_evidence,
            source_qid_details=details,
            document=doc,
        )
        == []
    )


# ---------------------------------------------------------------------------
# basic_searchable_evidence_precursor
# ---------------------------------------------------------------------------


def _cov(hullq_id: str, ptr: Any, bucket: FieldCoverageBucket) -> Any:
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import BoatModelFieldCoverage

    return BoatModelFieldCoverage(
        hullq_id=hullq_id, field_pointer=ptr, bucket=bucket, contributing_qids=()
    )


def test_basic_searchable_evidence_precursor_requires_loa_beam_and_draft_or_displacement() -> None:
    NCP = FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    NUV = FieldCoverageBucket.NO_USABLE_VALUE
    coverage = [
        _cov("BM_A", PTR_LOA, NCP),
        _cov("BM_A", PTR_BEAM, NCP),
        _cov("BM_A", PTR_DRAFT, NCP),
        _cov("BM_A", PTR_DISPLACEMENT, NUV),
        # BM_B has LOA + beam but neither draft nor displacement.
        _cov("BM_B", PTR_LOA, NCP),
        _cov("BM_B", PTR_BEAM, NCP),
        _cov("BM_B", PTR_DRAFT, NUV),
        _cov("BM_B", PTR_DISPLACEMENT, NUV),
        # BM_C qualifies via displacement instead of draft.
        _cov("BM_C", PTR_LOA, NCP),
        _cov("BM_C", PTR_BEAM, NCP),
        _cov("BM_C", PTR_DRAFT, NUV),
        _cov("BM_C", PTR_DISPLACEMENT, NCP),
    ]
    count, qualifying = compute_basic_searchable_evidence_precursor(coverage)
    assert count == 2
    assert qualifying == ("BM_A", "BM_C")


def test_basic_searchable_precursor_document_round_trip() -> None:
    NCP = FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    coverage = [
        _cov("BM_A", PTR_LOA, NCP),
        _cov("BM_A", PTR_BEAM, NCP),
        _cov("BM_A", PTR_DRAFT, NCP),
    ]
    doc = build_basic_searchable_precursor_document(
        generated_at="t", boat_model_count=1, boat_model_coverage=coverage
    )
    assert doc["qualifying_boat_model_count"] == 1
    assert doc["metric_name"] == "basic_searchable_evidence_precursor"
    assert (
        verify_basic_searchable_precursor_self_consistency(
            boat_model_count=1, boat_model_coverage=coverage, document=doc
        )
        == []
    )


def test_basic_searchable_precursor_document_zero_boat_models_no_division_error() -> None:
    doc = build_basic_searchable_precursor_document(
        generated_at="t", boat_model_count=0, boat_model_coverage=[]
    )
    assert doc["qualifying_boat_model_percentage"] == 0.0


# ---------------------------------------------------------------------------
# build_sl0028_bundle
# ---------------------------------------------------------------------------


def test_build_sl0028_bundle_empty_valid() -> None:
    bundle = build_sl0028_bundle("Q1", "Boat A", [])
    assert bundle.bundle_id == "BUNDLE-SL0028-Q1"
    assert bundle.promoted_evidence == ()


def test_build_sl0028_bundle_rejects_subject_mismatch() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat A",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("12.5", "Q11573", "Q2358152")]},
    )
    full_evidence, _report = _extract([entity])
    allowed = filter_to_allowed_evidence(full_evidence)
    with pytest.raises(ValueError, match="does not match requested QID"):
        build_sl0028_bundle("Q999", "Boat A", allowed)


def test_build_sl0028_bundle_rejects_disallowed_field_pointer() -> None:
    from hullq.domain.provenance import (
        ConfidenceLevel,
        EvidenceType,
        JsonPointer,
        ProducerKind,
        ProducerMetadata,
        ProvenanceSubject,
        RawObservation,
        RawObservationKind,
        ResearchContext,
        SourceLocator,
        SubjectKind,
    )
    from hullq.domain.provenance import FieldEvidence as _FE

    bad_evidence = _FE(
        evidence_id="X",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="Q1"),
        field_pointer=JsonPointer("/relationships/builders"),
        source_id="SRC_WIKIDATA_API_2026",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD, value={}, unit=None, excerpt=None
        ),
        normalized_candidate=None,
        evidence_type=EvidenceType.API_RECORD,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="x",
            version=None,
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-01-01T00:00:00Z",
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_evidence_id=None,
        notes=None,
    )
    with pytest.raises(ValueError, match="not one of the five allowed"):
        build_sl0028_bundle("Q1", "Boat A", [bad_evidence])


# ---------------------------------------------------------------------------
# evidence manifest document build/verify + rebuild
# ---------------------------------------------------------------------------


def test_evidence_manifest_round_trip() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat A",
        aliases=["Alt"],
        raw_claims={"P2043": [_quantity_claim("12.5", "Q11573", "Q2358152")]},
    )
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid=by_qid,
        quality_report=quality_report,
        requested_qid_count=1,
        acquisition_failure_count=0,
    )
    assert doc["usage_metrics"]["requested_qid_count"] == 1
    assert doc["usage_metrics"]["acquisition_failure_count"] == 0
    assert "retrieval_count_attributed_note" in doc["usage_metrics"]
    assert len(doc["requested_qid_evidence"]) == 1
    assert (
        verify_evidence_manifest_self_consistency(
            linkage=linkage,
            entities=[entity],
            full_evidence=full_evidence,
            quality_report=quality_report,
            evidence_manifest=doc,
        )
        == []
    )

    rebuilt = rebuild_entities_from_manifest(doc)
    assert len(rebuilt) == 1
    assert rebuilt[0].qid == "Q1"


def test_evidence_manifest_self_consistency_detects_tamper() -> None:
    entity = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid={},
        quality_report=quality_report,
        requested_qid_count=1,
    )
    tampered = dict(doc)
    tampered["raw_entities"] = []
    problems = verify_evidence_manifest_self_consistency(
        linkage=linkage,
        entities=[entity],
        full_evidence=full_evidence,
        quality_report=quality_report,
        evidence_manifest=tampered,
    )
    assert problems


def test_evidence_manifest_self_consistency_detects_requested_qid_count_tamper() -> None:
    entity = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid={},
        quality_report=quality_report,
        requested_qid_count=1,
    )
    tampered = json_copy_with(doc, ("usage_metrics", "requested_qid_count"), 999)
    problems = verify_evidence_manifest_self_consistency(
        linkage=linkage,
        entities=[entity],
        full_evidence=full_evidence,
        quality_report=quality_report,
        evidence_manifest=tampered,
    )
    assert any("requested_qid_count" in p for p in problems)


def test_evidence_manifest_self_consistency_detects_fetched_entity_count_tamper() -> None:
    entity = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid={},
        quality_report=quality_report,
        requested_qid_count=1,
    )
    tampered = json_copy_with(doc, ("usage_metrics", "fetched_entity_count"), 0)
    problems = verify_evidence_manifest_self_consistency(
        linkage=linkage,
        entities=[entity],
        full_evidence=full_evidence,
        quality_report=quality_report,
        evidence_manifest=tampered,
    )
    assert any("fetched_entity_count" in p for p in problems)


def test_evidence_manifest_self_consistency_detects_zero_failure_count_mismatch() -> None:
    """acquisition_failure_count == 0 but fetched_entity_count !=
    requested_qid_count is internally inconsistent and must be caught even
    though both individual values might otherwise look independently
    plausible."""
    entity = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    boundary = _boundary((("Q1", "BM_A"), ("Q2", "BM_A")), canonical_count=1)
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid={},
        quality_report=quality_report,
        requested_qid_count=2,
        acquisition_failure_count=0,
    )
    # requested_qid_count(2) != fetched_entity_count(1) with acquisition_failure_count == 0.
    problems = verify_evidence_manifest_self_consistency(
        linkage=linkage,
        entities=[entity],
        full_evidence=full_evidence,
        quality_report=quality_report,
        evidence_manifest=doc,
    )
    assert any("internally inconsistent" in p for p in problems)


def test_evidence_manifest_self_consistency_detects_malformed_count_tamper() -> None:
    entity = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid={},
        quality_report=quality_report,
        requested_qid_count=1,
    )
    tampered = json_copy_with(doc, ("quality_report_global", "malformed_statement_count"), 999)
    problems = verify_evidence_manifest_self_consistency(
        linkage=linkage,
        entities=[entity],
        full_evidence=full_evidence,
        quality_report=quality_report,
        evidence_manifest=tampered,
    )
    assert any("malformed_statement_count" in p for p in problems)


def test_evidence_manifest_self_consistency_detects_unsupported_qualifier_count_tamper() -> None:
    entity = WikidataEntityData(qid="Q1", label="Boat A", aliases=[], raw_claims={})
    boundary = _boundary((("Q1", "BM_A"),))
    linkage = build_full_boundary_linkage(boundary)
    full_evidence, quality_report = _extract([entity])
    doc = build_evidence_manifest_document(
        generated_at="t",
        acquired_at="t2",
        linkage=linkage,
        entities=[entity],
        allowed_evidence_by_qid={},
        quality_report=quality_report,
        requested_qid_count=1,
    )
    tampered = json_copy_with(doc, ("quality_report_global", "unsupported_qualifier_count"), 999)
    problems = verify_evidence_manifest_self_consistency(
        linkage=linkage,
        entities=[entity],
        full_evidence=full_evidence,
        quality_report=quality_report,
        evidence_manifest=tampered,
    )
    assert any("unsupported_qualifier_count" in p for p in problems)


# ---------------------------------------------------------------------------
# artifact digests
# ---------------------------------------------------------------------------


def test_artifact_digests_round_trip(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    digests = build_artifact_digests(generated_at="t", package_dir=tmp_path)
    assert set(digests["digests"]) == {"a.json", "b.json"}
    assert (
        verify_artifact_digests_self_consistency(artifact_digests=digests, package_dir=tmp_path)
        == []
    )


def test_artifact_digests_detect_mutation(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    digests = build_artifact_digests(generated_at="t", package_dir=tmp_path)
    (tmp_path / "a.json").write_text('{"changed": true}', encoding="utf-8")
    problems = verify_artifact_digests_self_consistency(
        artifact_digests=digests, package_dir=tmp_path
    )
    assert problems


def test_retained_package_filenames_excludes_digest_file(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / ARTIFACT_DIGESTS_FILENAME).write_text("{}", encoding="utf-8")
    assert retained_package_filenames(tmp_path) == {"a.json"}


# ---------------------------------------------------------------------------
# Reused-constant sanity (never redefined/duplicated)
# ---------------------------------------------------------------------------


def test_allowed_field_pointers_reused_from_sl0026() -> None:
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        ALLOWED_FIELD_POINTERS as SL0028_PTRS,
    )

    assert SL0028_PTRS is ALLOWED_FIELD_POINTERS
