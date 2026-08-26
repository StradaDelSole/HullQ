"""Unit tests for the SLICE-0026 bounded Wikidata Tier-1 enrichment pilot pure logic."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
    ACCEPTED_SL0018_DELTA_MANIFEST_SHA256,
    ARTIFACT_DIGESTS_FILENAME,
    PILOT_SIZE,
    PTR_BEAM,
    PTR_DISPLACEMENT,
    PTR_DRAFT,
    PTR_LOA,
    PTR_LWL,
    EntityFieldCoverage,
    FieldCoverageBucket,
    IdentityBoundary,
    IdentityBoundaryIntegrityError,
    PilotBoatModel,
    build_artifact_digests,
    build_evidence_manifest_document,
    build_pilot_bundle,
    build_selection_document,
    classify_entity_field_coverage,
    filter_to_allowed_evidence,
    load_reproduced_identity_boundary,
    rebuild_entities_from_manifest,
    retained_package_filenames,
    select_pilot_boatmodels,
    summarize_field_coverage,
    trim_raw_claims_to_allowed_properties,
    verify_artifact_digests_self_consistency,
    verify_evidence_manifest_self_consistency,
    verify_selection_self_consistency,
)
from hullq.bootstrap.wikidata_tier0 import (
    BootstrapCandidate,
    BootstrapDecision,
    BootstrapReasonCode,
    build_manifest,
    candidate_to_manifest_dict,
    mint_hullq_id,
)
from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig, WikidataEntityData

ROOT = Path(__file__).resolve().parents[2]
REAL_BASELINE_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"
REAL_DELTA_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"

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
    amount: str, unit_qid: str | None, qualifier_qid: str | None = None
) -> dict[str, Any]:
    unit = f"http://www.wikidata.org/entity/{unit_qid}" if unit_qid else "1"
    claim: dict[str, Any] = {
        "id": "stmt1",
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"type": "quantity", "value": {"amount": amount, "unit": unit}},
        },
    }
    if qualifier_qid:
        claim["qualifiers"] = {
            "P642": [
                {
                    "snaktype": "value",
                    "datavalue": {"type": "wikibase-entityid", "value": {"id": qualifier_qid}},
                }
            ]
        }
    return claim


# ---------------------------------------------------------------------------
# load_reproduced_identity_boundary — real accepted artifacts
# ---------------------------------------------------------------------------


def test_load_reproduced_identity_boundary_matches_accepted_counts() -> None:
    boundary = load_reproduced_identity_boundary()
    assert boundary.canonical_boat_model_count == 1770
    assert boundary.historical_crosswalk_count == 1772
    assert len(boundary.auto_admit_qid_to_hullq_id) == 1770
    # Each QID and each HullQ ID appears exactly once (bijective by construction).
    qids = [qid for qid, _ in boundary.auto_admit_qid_to_hullq_id]
    ids = [hid for _, hid in boundary.auto_admit_qid_to_hullq_id]
    assert len(set(qids)) == len(qids) == 1770
    assert len(set(ids)) == len(ids) == 1770


def test_load_reproduced_identity_boundary_deterministic_across_calls() -> None:
    b1 = load_reproduced_identity_boundary()
    b2 = load_reproduced_identity_boundary()
    assert b1.auto_admit_qid_to_hullq_id == b2.auto_admit_qid_to_hullq_id
    assert b1.canonical_boat_model_count == b2.canonical_boat_model_count


def test_load_reproduced_identity_boundary_fails_closed_on_delta_drift(tmp_path: Path) -> None:
    tampered = json.loads(REAL_DELTA_PATH.read_bytes().decode("utf-8"))
    tampered["counts"]["combined_canonical_boat_model_count_expected"] = 9999
    tampered_path = tmp_path / "sl0018_tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(IdentityBoundaryIntegrityError, match="sha256"):
        load_reproduced_identity_boundary(delta_manifest_path=tampered_path)


def test_load_reproduced_identity_boundary_fails_closed_on_missing_delta_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(IdentityBoundaryIntegrityError, match="could not be read"):
        load_reproduced_identity_boundary(delta_manifest_path=tmp_path / "does_not_exist.json")


def test_load_reproduced_identity_boundary_fails_closed_on_baseline_drift(tmp_path: Path) -> None:
    tampered_baseline = tmp_path / "manifest.json"
    tampered_baseline.write_text("{}", encoding="utf-8")
    with pytest.raises(IdentityBoundaryIntegrityError):
        load_reproduced_identity_boundary(baseline_manifest_path=tampered_baseline)


def test_load_reproduced_identity_boundary_fails_closed_on_count_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A delta manifest that passes its own sha256 pin but was hand-built to
    have the wrong combined AUTO_ADMIT count must still fail closed.

    Uses a synthetic single-candidate baseline+delta pair with every accepted
    SLICE-0017/SLICE-0026 fixed constant patched to match via
    ``monkeypatch.setattr`` (auto-restored at test teardown even on failure —
    unlike hand-rolled try/finally, a missed attribute can't leak into other
    tests).
    """
    import hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot as sl0026mod
    import hullq.bootstrap.wikidata_tier0_sl0018 as sl0018mod

    small_baseline = _small_manifest_with_one_auto_admit("Q1", "B1")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(small_baseline), encoding="utf-8")
    baseline_sha256 = hashlib.sha256(baseline_path.read_bytes()).hexdigest()

    small_delta = _small_manifest_with_one_auto_admit("Q2", "B2")
    delta_path = tmp_path / "delta.json"
    delta_path.write_text(json.dumps(small_delta), encoding="utf-8")
    delta_sha256 = hashlib.sha256(delta_path.read_bytes()).hexdigest()

    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_MANIFEST_SHA256", baseline_sha256)
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_MANIFEST_VERSION", "0017-v4")
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_BASELINE_CANDIDATE_COUNT", 1)
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_ADMISSIONS", 1)
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_REVIEW_REQUIRED", 0)
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_NOT_ADMITTED", 0)
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_RETAINED_CROSSWALK_COUNT", 1)
    monkeypatch.setattr(sl0018mod, "ACCEPTED_0017_BUNDLES_ON_REPLAY", 1)
    monkeypatch.setattr(sl0026mod, "ACCEPTED_SL0018_DELTA_MANIFEST_SHA256", delta_sha256)

    with pytest.raises(IdentityBoundaryIntegrityError, match="AUTO_ADMIT"):
        load_reproduced_identity_boundary(
            baseline_manifest_path=baseline_path, delta_manifest_path=delta_path
        )


def _small_manifest_with_one_auto_admit(qid: str, hullq_id: str) -> dict[str, Any]:
    candidate = BootstrapCandidate(
        qid=qid,
        retrieved_at="2026-01-01T00:00:00Z",
        preferred_label=f"Label {qid}",
        aliases=(),
        hullq_id=hullq_id,
        decision=BootstrapDecision.AUTO_ADMIT,
        reason_codes=(BootstrapReasonCode.OK,),
        observation_id=f"OBS-{qid}",
        bundle_id=f"BUNDLE-{qid}",
        bundle_version="1",
        evidence_link_id=f"LINK-{qid}",
    )
    return build_manifest(
        [candidate],
        generated_at="2026-01-01T00:00:00Z",
        requested_limit=1,
        unique_qids_returned=1,
        retrieval_count=0,
        extracted_record_count=1,
        target_reached=False,
    )


# ---------------------------------------------------------------------------
# select_pilot_boatmodels
# ---------------------------------------------------------------------------


def test_select_pilot_boatmodels_deterministic_and_ordered() -> None:
    boundary = load_reproduced_identity_boundary()
    s1 = select_pilot_boatmodels(boundary, count=PILOT_SIZE)
    s2 = select_pilot_boatmodels(boundary, count=PILOT_SIZE)
    assert s1 == s2
    assert len(s1) == PILOT_SIZE
    ids = [m.hullq_id for m in s1]
    assert ids == sorted(ids)
    assert len(set(ids)) == PILOT_SIZE
    assert len({m.qid for m in s1}) == PILOT_SIZE


def test_select_pilot_boatmodels_raises_when_count_exceeds_universe() -> None:
    boundary = load_reproduced_identity_boundary()
    with pytest.raises(ValueError, match="exceeds"):
        select_pilot_boatmodels(boundary, count=len(boundary.auto_admit_qid_to_hullq_id) + 1)


def test_select_pilot_boatmodels_rejects_duplicate_hullq_id() -> None:
    boundary = IdentityBoundary(
        baseline_manifest_sha256="0" * 64,
        delta_manifest_sha256="0" * 64,
        canonical_boat_model_count=2,
        historical_crosswalk_count=2,
        auto_admit_qid_to_hullq_id=(("Q1", "BM_SAME"), ("Q2", "BM_SAME")),
        preferred_label_by_qid={"Q1": "A", "Q2": "B"},
    )
    with pytest.raises(ValueError, match="Duplicate BoatModel ID"):
        select_pilot_boatmodels(boundary, count=2)


def test_select_pilot_boatmodels_rejects_duplicate_qid() -> None:
    boundary = IdentityBoundary(
        baseline_manifest_sha256="0" * 64,
        delta_manifest_sha256="0" * 64,
        canonical_boat_model_count=2,
        historical_crosswalk_count=2,
        auto_admit_qid_to_hullq_id=(("Q1", "BM_A"), ("Q1", "BM_B")),
        preferred_label_by_qid={"Q1": "A"},
    )
    with pytest.raises(ValueError, match="Duplicate QID"):
        select_pilot_boatmodels(boundary, count=2)


# ---------------------------------------------------------------------------
# filter_to_allowed_evidence
# ---------------------------------------------------------------------------


def test_filter_to_allowed_evidence_drops_ballast_and_relationship_evidence() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat1",
        aliases=[],
        raw_claims={
            "P2067": [
                _quantity_claim("+4500", "Q11570", "Q5636358"),  # displacement
                _quantity_claim("+900", "Q11570", "Q5461048"),  # ballast — must be dropped
            ],
            "P176": [
                {
                    "id": "stmt2",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"type": "wikibase-entityid", "value": {"id": "Q999"}},
                    },
                }
            ],
        },
    )
    full_evidence, _report = _extract([entity])
    allowed = filter_to_allowed_evidence(full_evidence)
    assert {str(ev.field_pointer) for ev in allowed} == {"/baseline/dimensions/displacement_kg"}


# ---------------------------------------------------------------------------
# classify_entity_field_coverage / summarize_field_coverage
# ---------------------------------------------------------------------------


def test_coverage_normalized_candidate_present() -> None:
    entity = WikidataEntityData(
        qid="Q1", label="B", aliases=[], raw_claims={"P2049": [_quantity_claim("+3.5", "Q11573")]}
    )
    full_evidence, _r = _extract([entity])
    counts, _details = summarize_field_coverage([entity], full_evidence)
    assert counts["beam"]["normalized_candidate_present"] == 1
    assert counts["beam"]["source_statement_present"] == 0
    assert counts["beam"]["unsupported_or_malformed"] == 0
    assert counts["beam"]["no_usable_value"] == 0


def test_coverage_source_statement_present_unrecognized_unit() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="B",
        aliases=[],
        raw_claims={"P2049": [_quantity_claim("+3.5", "Q999999")]},
    )
    full_evidence, _r = _extract([entity])
    counts, _details = summarize_field_coverage([entity], full_evidence)
    assert counts["beam"]["source_statement_present"] == 1
    assert counts["beam"]["normalized_candidate_present"] == 0


def test_coverage_unsupported_wrong_dimension_unit() -> None:
    entity = WikidataEntityData(
        qid="Q1", label="B", aliases=[], raw_claims={"P2049": [_quantity_claim("+100", "Q11570")]}
    )
    full_evidence, _r = _extract([entity])
    counts, _details = summarize_field_coverage([entity], full_evidence)
    assert counts["beam"]["unsupported_or_malformed"] == 1


def test_coverage_no_usable_value_absent_property() -> None:
    entity = WikidataEntityData(qid="Q1", label="B", aliases=[], raw_claims={})
    full_evidence, _r = _extract([entity])
    counts, _details = summarize_field_coverage([entity], full_evidence)
    for field in ("loa", "lwl", "beam", "draft", "displacement"):
        assert counts[field]["no_usable_value"] == 1


def test_coverage_sibling_present_yields_no_usable_value_not_unsupported() -> None:
    """A P2043 statement mapped only to LWL means LOA has genuinely no data
    for this entity — NOT an unsupported/malformed statement."""
    entity = WikidataEntityData(
        qid="Q1",
        label="B",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("+9.0", "Q11573", "Q1817392")]},
    )
    full_evidence, _r = _extract([entity])
    counts, details = summarize_field_coverage([entity], full_evidence)
    assert counts["lwl"]["normalized_candidate_present"] == 1
    assert counts["loa"]["no_usable_value"] == 1
    assert counts["loa"]["unsupported_or_malformed"] == 0
    loa_detail = next(d for d in details if d.qid == "Q1" and d.field_pointer == PTR_LOA)
    assert loa_detail.bucket is FieldCoverageBucket.NO_USABLE_VALUE


def test_coverage_unmatched_qualifier_counts_against_both_siblings() -> None:
    """A P2043 statement with a qualifier that matches neither LOA nor LWL is
    counted as unsupported/malformed against BOTH sibling fields (documented
    conservative upper bound — see classify_entity_field_coverage docstring).
    """
    entity = WikidataEntityData(
        qid="Q1",
        label="B",
        aliases=[],
        raw_claims={"P2043": [_quantity_claim("+9.0", "Q11573", "Q_UNRELATED")]},
    )
    full_evidence, _r = _extract([entity])
    counts, _details = summarize_field_coverage([entity], full_evidence)
    assert counts["loa"]["unsupported_or_malformed"] == 1
    assert counts["lwl"]["unsupported_or_malformed"] == 1


def test_coverage_displacement_ballast_sibling_pair() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="B",
        aliases=[],
        raw_claims={"P2067": [_quantity_claim("+900", "Q11570", "Q5461048")]},  # ballast only
    )
    full_evidence, _r = _extract([entity])
    counts, _details = summarize_field_coverage([entity], full_evidence)
    assert counts["displacement"]["no_usable_value"] == 1
    assert counts["displacement"]["unsupported_or_malformed"] == 0


def test_classify_entity_field_coverage_direct_call_no_evidence_no_siblings() -> None:
    entity = WikidataEntityData(qid="Q1", label="B", aliases=[], raw_claims={})
    bucket = classify_entity_field_coverage(
        entity, field_pointer=PTR_DRAFT, own_field_evidence=(), sibling_field_evidence=()
    )
    assert bucket is FieldCoverageBucket.NO_USABLE_VALUE


def test_summarize_field_coverage_sums_to_pilot_size_per_field() -> None:
    entities = [
        WikidataEntityData(qid=f"Q{i}", label=f"B{i}", aliases=[], raw_claims={}) for i in range(5)
    ]
    full_evidence, _r = _extract(entities)
    counts, details = summarize_field_coverage(entities, full_evidence)
    for field_counts in counts.values():
        assert sum(field_counts.values()) == 5
    assert len(details) == 5 * 5  # 5 entities x 5 allowed fields


# ---------------------------------------------------------------------------
# build_pilot_bundle
# ---------------------------------------------------------------------------


def test_build_pilot_bundle_preserves_subject_and_normalized_candidate() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat1",
        aliases=[],
        raw_claims={"P2049": [_quantity_claim("+3.5", "Q11573")]},
    )
    full_evidence, _r = _extract([entity])
    allowed = filter_to_allowed_evidence(full_evidence)
    model = PilotBoatModel(hullq_id="BM_X", qid="Q1", preferred_label="Boat1")
    bundle = build_pilot_bundle(model, allowed)
    assert bundle.bundle_id == "BUNDLE-SL0026-Q1"
    assert len(bundle.promoted_evidence) == 1
    ev = bundle.promoted_evidence[0]
    assert str(ev.subject.kind) == "boat_design"
    assert ev.subject.id == "Q1"  # never rewritten to the HullQ BoatModel ID
    assert ev.normalized_candidate is not None
    assert bundle.observations == ()
    assert bundle.activity_id == "SLICE-0026-TIER1-ENRICHMENT-PILOT"


def test_build_pilot_bundle_empty_evidence_is_valid() -> None:
    model = PilotBoatModel(hullq_id="BM_X", qid="Q1", preferred_label=None)
    bundle = build_pilot_bundle(model, [])
    assert bundle.promoted_evidence == ()
    assert bundle.research_target.model == "Q1"  # falls back to qid when no label


def test_build_pilot_bundle_rejects_mismatched_subject_qid() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat1",
        aliases=[],
        raw_claims={"P2049": [_quantity_claim("+3.5", "Q11573")]},
    )
    full_evidence, _r = _extract([entity])
    allowed = filter_to_allowed_evidence(full_evidence)
    other_model = PilotBoatModel(hullq_id="BM_X", qid="Q2", preferred_label=None)
    with pytest.raises(ValueError, match="does not match pilot BoatModel QID"):
        build_pilot_bundle(other_model, allowed)


def test_build_pilot_bundle_rejects_disallowed_field_pointer() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat1",
        aliases=[],
        raw_claims={"P2067": [_quantity_claim("+900", "Q11570", "Q5461048")]},  # ballast
    )
    full_evidence, _r = _extract([entity])  # NOT filtered — includes ballast
    model = PilotBoatModel(hullq_id="BM_X", qid="Q1", preferred_label=None)
    with pytest.raises(ValueError, match="not one of the five allowed"):
        build_pilot_bundle(model, full_evidence)


# ---------------------------------------------------------------------------
# trim_raw_claims_to_allowed_properties / rebuild_entities_from_manifest
# ---------------------------------------------------------------------------


def test_trim_raw_claims_keeps_only_relevant_properties() -> None:
    raw = {
        "P2043": [_quantity_claim("+9.0", "Q11573")],
        "P176": [{"id": "x"}],
        "P287": [{"id": "y"}],
    }
    trimmed = trim_raw_claims_to_allowed_properties(raw)
    assert set(trimmed) == {"P2043"}


def test_rebuild_entities_from_manifest_round_trip() -> None:
    entity = WikidataEntityData(
        qid="Q1",
        label="Boat1",
        aliases=["Alt"],
        raw_claims={"P2049": [_quantity_claim("+3.5", "Q11573")]},
    )
    selection = [PilotBoatModel(hullq_id="BM_X", qid="Q1", preferred_label="Boat1")]
    full_evidence, report = _extract([entity])
    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid = {"Q1": allowed}
    counts, _details = summarize_field_coverage([entity], full_evidence)

    doc = build_evidence_manifest_document(
        generated_at="2026-01-01T00:00:00Z",
        acquired_at="2026-01-01T00:00:00Z",
        selection=selection,
        entities=[entity],
        allowed_evidence_by_qid=by_qid,
        coverage_counts=counts,
        quality_report=report,
        requested_qid_count=1,
    )
    rebuilt = rebuild_entities_from_manifest(doc)
    assert len(rebuilt) == 1
    assert rebuilt[0].qid == "Q1"
    assert rebuilt[0].label == "Boat1"
    assert rebuilt[0].aliases == ["Alt"]
    assert rebuilt[0].raw_claims == trim_raw_claims_to_allowed_properties(entity.raw_claims)

    rebuilt_evidence, _r2 = _extract(rebuilt)
    problems = verify_evidence_manifest_self_consistency(
        selection=selection, entities=rebuilt, full_evidence=rebuilt_evidence, evidence_manifest=doc
    )
    assert problems == []


# ---------------------------------------------------------------------------
# build_selection_document / verify_selection_self_consistency
# ---------------------------------------------------------------------------


def test_selection_document_round_trip_self_consistent() -> None:
    boundary = load_reproduced_identity_boundary()
    selection = select_pilot_boatmodels(boundary, count=10)
    doc = build_selection_document(
        generated_at="2026-01-01T00:00:00Z", boundary=boundary, selection=selection
    )
    assert doc["pilot_size"] == 10
    assert len(doc["boat_models"]) == 10
    problems = verify_selection_self_consistency(boundary=boundary, selection_document=doc)
    assert problems == []


def test_selection_document_tamper_detected() -> None:
    boundary = load_reproduced_identity_boundary()
    selection = select_pilot_boatmodels(boundary, count=5)
    doc = build_selection_document(
        generated_at="2026-01-01T00:00:00Z", boundary=boundary, selection=selection
    )
    tampered = copy.deepcopy(doc)
    tampered["boat_models"][0]["hullq_id"] = "TAMPERED"
    problems = verify_selection_self_consistency(boundary=boundary, selection_document=tampered)
    assert problems != []


def test_selection_document_boundary_tamper_detected() -> None:
    boundary = load_reproduced_identity_boundary()
    selection = select_pilot_boatmodels(boundary, count=5)
    doc = build_selection_document(
        generated_at="2026-01-01T00:00:00Z", boundary=boundary, selection=selection
    )
    tampered = copy.deepcopy(doc)
    tampered["identity_boundary"]["canonical_boat_model_count"] = 1
    problems = verify_selection_self_consistency(boundary=boundary, selection_document=tampered)
    assert any("identity_boundary" in p for p in problems)


# ---------------------------------------------------------------------------
# Module constants sanity
# ---------------------------------------------------------------------------


def test_delta_manifest_sha256_pin_matches_real_file() -> None:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import DELTA_MANIFEST_PATH

    actual = hashlib.sha256(DELTA_MANIFEST_PATH.read_bytes()).hexdigest()
    assert actual == ACCEPTED_SL0018_DELTA_MANIFEST_SHA256


def test_allowed_field_pointers_exactly_five_and_distinct() -> None:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import ALLOWED_FIELD_POINTERS

    assert len(ALLOWED_FIELD_POINTERS) == 5
    assert len(set(ALLOWED_FIELD_POINTERS)) == 5
    assert set(ALLOWED_FIELD_POINTERS) == {PTR_LOA, PTR_LWL, PTR_BEAM, PTR_DRAFT, PTR_DISPLACEMENT}


def test_candidate_to_manifest_dict_smoke() -> None:
    """Sanity check the local test helper building a minted candidate is
    itself consistent with the accepted SLICE-0017 manifest-row shape."""
    candidate = BootstrapCandidate(
        qid="Q1",
        retrieved_at="2026-01-01T00:00:00Z",
        preferred_label="X",
        aliases=(),
        hullq_id=mint_hullq_id(),
        decision=BootstrapDecision.AUTO_ADMIT,
        reason_codes=(BootstrapReasonCode.OK,),
        observation_id="OBS-Q1",
        bundle_id="BUNDLE-Q1",
        bundle_version="1",
        evidence_link_id="LINK-Q1",
    )
    row = candidate_to_manifest_dict(candidate)
    assert row["qid"] == "Q1"
    assert row["decision"] == "auto_admit"


def test_entity_field_coverage_dataclass_fields() -> None:
    c = EntityFieldCoverage(
        qid="Q1", field_pointer=PTR_BEAM, bucket=FieldCoverageBucket.NO_USABLE_VALUE
    )
    assert c.qid == "Q1"
    assert c.field_pointer == PTR_BEAM


# ---------------------------------------------------------------------------
# retained_package_filenames / build_artifact_digests /
# verify_artifact_digests_self_consistency — the FINAL retained package must
# have integrity digests covering every file except ARTIFACT-DIGESTS.json
# itself, discovered dynamically (never a hardcoded allowlist), so digest
# coverage automatically tracks both the intermediate --live-only state (6
# files) and the final --persist state (8 files, including the two replay
# artifacts).
# ---------------------------------------------------------------------------


def _write(path: Path, content: str = "x") -> None:
    path.write_text(content, encoding="utf-8")


def test_retained_package_filenames_excludes_only_the_digest_document(tmp_path: Path) -> None:
    _write(tmp_path / "selection.json")
    _write(tmp_path / "evidence_manifest.json")
    _write(tmp_path / ARTIFACT_DIGESTS_FILENAME)
    names = retained_package_filenames(tmp_path)
    assert names == {"selection.json", "evidence_manifest.json"}


def test_retained_package_filenames_ignores_subdirectories(tmp_path: Path) -> None:
    _write(tmp_path / "selection.json")
    (tmp_path / "subdir").mkdir()
    _write(tmp_path / "subdir" / "not_directly_in_package.json")
    assert retained_package_filenames(tmp_path) == {"selection.json"}


def test_build_artifact_digests_covers_exactly_the_six_live_stage_files(tmp_path: Path) -> None:
    """Simulates the intermediate state right after --live (before --persist
    has ever run): only the six selection/evidence-manifest/report/schema
    files exist yet — REPLAY-RESULT.json/REPLAY-REPORT.md are correctly NOT
    expected or required at this stage."""
    live_stage_files = (
        "selection.json",
        "selection_schema.json",
        "evidence_manifest.json",
        "evidence_manifest_schema.json",
        "REPORT.md",
        "artifact_digests_schema.json",
    )
    for name in live_stage_files:
        _write(tmp_path / name, content=name)

    doc = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    assert set(doc["digests"]) == set(live_stage_files)
    problems = verify_artifact_digests_self_consistency(artifact_digests=doc, package_dir=tmp_path)
    assert problems == []


def test_build_artifact_digests_covers_all_eight_files_after_persist(tmp_path: Path) -> None:
    """Simulates the FINAL committed state after --persist has run: the same
    six files plus REPLAY-RESULT.json and REPLAY-REPORT.md must ALL be
    covered — this is the literal contract requirement the reviewer flagged
    as missing."""
    final_stage_files = (
        "selection.json",
        "selection_schema.json",
        "evidence_manifest.json",
        "evidence_manifest_schema.json",
        "REPORT.md",
        "artifact_digests_schema.json",
        "REPLAY-RESULT.json",
        "REPLAY-REPORT.md",
    )
    for name in final_stage_files:
        _write(tmp_path / name, content=name)

    doc = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    assert set(doc["digests"]) == set(final_stage_files)
    assert "REPLAY-RESULT.json" in doc["digests"]
    assert "REPLAY-REPORT.md" in doc["digests"]
    problems = verify_artifact_digests_self_consistency(artifact_digests=doc, package_dir=tmp_path)
    assert problems == []


def test_verify_artifact_digests_detects_undigested_added_file(tmp_path: Path) -> None:
    _write(tmp_path / "selection.json")
    doc = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    # A new retained file (e.g. a freshly-written REPLAY-RESULT.json) appears
    # after the digests were built but before they were rebuilt.
    _write(tmp_path / "REPLAY-RESULT.json")
    problems = verify_artifact_digests_self_consistency(artifact_digests=doc, package_dir=tmp_path)
    assert any("REPLAY-RESULT.json" in p and "missing" in p for p in problems)


def test_verify_artifact_digests_detects_stale_digest_for_removed_file(tmp_path: Path) -> None:
    _write(tmp_path / "selection.json")
    _write(tmp_path / "REPLAY-RESULT.json")
    doc = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    (tmp_path / "REPLAY-RESULT.json").unlink()
    problems = verify_artifact_digests_self_consistency(artifact_digests=doc, package_dir=tmp_path)
    assert any("REPLAY-RESULT.json" in p for p in problems)


def test_verify_artifact_digests_detects_mutated_file_content(tmp_path: Path) -> None:
    _write(tmp_path / "selection.json", content="original")
    doc = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    _write(tmp_path / "selection.json", content="tampered")
    problems = verify_artifact_digests_self_consistency(artifact_digests=doc, package_dir=tmp_path)
    assert any("selection.json" in p and "recomputed" in p for p in problems)


def test_verify_artifact_digests_never_requires_the_digest_document_itself(tmp_path: Path) -> None:
    _write(tmp_path / "selection.json")
    doc = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    assert ARTIFACT_DIGESTS_FILENAME not in doc["digests"]
    _write(tmp_path / ARTIFACT_DIGESTS_FILENAME, content=json.dumps(doc))
    # Writing the digest document itself afterward must not retroactively
    # become a required/undigested entry.
    problems = verify_artifact_digests_self_consistency(artifact_digests=doc, package_dir=tmp_path)
    assert problems == []
