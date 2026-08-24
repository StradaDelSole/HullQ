"""Unit tests for the SLICE-0022 retained alternative-route Tier-0 admission
safety pilot pure logic (``hullq.bootstrap.wikidata_sl0022_alt_route_admission``).

Covers:
- exact Git blob SHA1 fingerprinting;
- fail-closed immutable-input loading against the real committed retained
  artifacts, and against deliberately tampered copies;
- deterministic classification (R1 admission rules, the R3 fail-closed rule,
  collision detection against the baseline and within the 57-candidate set,
  crosswalk reuse);
- manifest construction guards (exact 57/53/4 split, R3-never-AUTO_ADMIT);
- offline self-consistency verification and its tamper resistance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (
    ACCEPTED_AUTO_ADMIT_COUNT,
    ACCEPTED_DIRECT_DISCOVERY_COUNT,
    ACCEPTED_HISTORICAL_CROSSWALK_COUNT,
    ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1,
    ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1,
    EXPECTED_R1_COUNT,
    EXPECTED_R3_COUNT,
    EXPECTED_TOTAL_CANDIDATES,
    ImmutableInputIntegrityError,
    Sl0022Candidate,
    build_sl0022_manifest,
    classify_sl0022_candidates,
    git_blob_sha1,
    load_and_fingerprint_immutable_inputs,
    sl0022_candidate_from_manifest_dict,
    sl0022_candidate_to_manifest_dict,
    verify_sl0022_manifest_self_consistency,
)
from hullq.bootstrap.wikidata_tier0 import (
    BootstrapCandidate,
    BootstrapDecision,
    BootstrapReasonCode,
    classify_candidates,
)
from hullq.bootstrap.wikidata_tier0 import (
    build_manifest as build_baseline_manifest_0017,
)
from hullq.bootstrap.wikidata_tier0 import (
    compute_collision_clusters as compute_baseline_collision_clusters,
)
from hullq.bootstrap.wikidata_tier0_sl0018 import build_baseline_snapshot_from_manifest
from hullq.sources.wikidata import WikidataEntityData

ROOT = Path(__file__).resolve().parents[2]
RETRIEVED_AT = "2026-08-24T15:29:04.154534+00:00"


# ---------------------------------------------------------------------------
# git_blob_sha1
# ---------------------------------------------------------------------------


def test_git_blob_sha1_matches_known_git_hash_object_value() -> None:
    # Cross-checked against a real `git hash-object` invocation on a file
    # containing the literal 3-byte content "abc" (not the raw SHA1 of "abc"
    # — git's blob object ID hashes the "blob <len>\0" header too).
    assert git_blob_sha1(b"abc") == "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f"


def test_git_blob_sha1_matches_repo_committed_sl0021_artifacts() -> None:
    sampled_bytes = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "sampled_candidates.json"
    ).read_bytes()
    probe_bytes = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "discovery_probe.json"
    ).read_bytes()
    assert git_blob_sha1(sampled_bytes) == ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1
    assert git_blob_sha1(probe_bytes) == ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1


# ---------------------------------------------------------------------------
# load_and_fingerprint_immutable_inputs — real committed artifacts
# ---------------------------------------------------------------------------


def test_load_and_fingerprint_immutable_inputs_against_real_retained_artifacts() -> None:
    inputs = load_and_fingerprint_immutable_inputs()
    assert len(inputs.baseline.candidate_qids) == ACCEPTED_DIRECT_DISCOVERY_COUNT
    assert len(inputs.baseline.auto_admit_qids) == ACCEPTED_AUTO_ADMIT_COUNT
    assert len(inputs.baseline.crosswalk) == ACCEPTED_HISTORICAL_CROSSWALK_COUNT
    assert len(inputs.retained_candidate_rows) == EXPECTED_TOTAL_CANDIDATES
    r1 = [r for r in inputs.retained_candidate_rows if r["route_membership"] == ["R1"]]
    r3 = [r for r in inputs.retained_candidate_rows if r["route_membership"] == ["R3"]]
    assert len(r1) == EXPECTED_R1_COUNT
    assert len(r3) == EXPECTED_R3_COUNT
    # No retained candidate QID may already be part of the accepted baseline.
    for row in inputs.retained_candidate_rows:
        assert row["qid"] not in inputs.baseline.candidate_qids


# ---------------------------------------------------------------------------
# load_and_fingerprint_immutable_inputs — fail-closed on tampered inputs
# ---------------------------------------------------------------------------


@pytest.fixture()
def real_paths() -> dict[str, Path]:
    base = ROOT / "research" / "bootstrap" / "wikidata"
    return {
        "sl0017": base / "manifest.json",
        "sl0018": base / "sl0018-2500" / "manifest.json",
        "sampled": base / "sl0021-alt-discovery" / "sampled_candidates.json",
        "probe": base / "sl0021-alt-discovery" / "discovery_probe.json",
    }


def test_tampered_sl0017_manifest_fails_closed(real_paths: dict[str, Path], tmp_path: Path) -> None:
    tampered = tmp_path / "manifest.json"
    tampered.write_bytes(real_paths["sl0017"].read_bytes() + b" ")
    with pytest.raises(ImmutableInputIntegrityError, match="SLICE-0017"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=tampered,
            sl0018_manifest_path=real_paths["sl0018"],
            sl0021_sampled_candidates_path=real_paths["sampled"],
            sl0021_discovery_probe_path=real_paths["probe"],
        )


def test_tampered_sl0018_manifest_fails_closed(real_paths: dict[str, Path], tmp_path: Path) -> None:
    tampered = tmp_path / "manifest.json"
    tampered.write_bytes(real_paths["sl0018"].read_bytes() + b" ")
    with pytest.raises(ImmutableInputIntegrityError, match="SLICE-0018"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=real_paths["sl0017"],
            sl0018_manifest_path=tampered,
            sl0021_sampled_candidates_path=real_paths["sampled"],
            sl0021_discovery_probe_path=real_paths["probe"],
        )


def test_tampered_sampled_candidates_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path
) -> None:
    tampered = tmp_path / "sampled_candidates.json"
    tampered.write_bytes(real_paths["sampled"].read_bytes() + b" ")
    with pytest.raises(ImmutableInputIntegrityError, match="sampled_candidates"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=real_paths["sl0017"],
            sl0018_manifest_path=real_paths["sl0018"],
            sl0021_sampled_candidates_path=tampered,
            sl0021_discovery_probe_path=real_paths["probe"],
        )


def test_tampered_discovery_probe_fails_closed(real_paths: dict[str, Path], tmp_path: Path) -> None:
    tampered = tmp_path / "discovery_probe.json"
    tampered.write_bytes(real_paths["probe"].read_bytes() + b" ")
    with pytest.raises(ImmutableInputIntegrityError, match="discovery_probe"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=real_paths["sl0017"],
            sl0018_manifest_path=real_paths["sl0018"],
            sl0021_sampled_candidates_path=real_paths["sampled"],
            sl0021_discovery_probe_path=tampered,
        )


def test_tampered_sampled_candidates_is_caught_by_pinned_hash_before_deeper_checks(
    real_paths: dict[str, Path], tmp_path: Path
) -> None:
    """Any content edit to sampled_candidates.json changes its Git blob
    SHA1, so it is rejected by the pinned-hash check before ever reaching the
    deeper cross-document consistency logic below — the primary, first-line
    defense. The deeper checks (duplicate QID, invalid route_membership,
    route split, discovery_probe corroboration, baseline-overlap) are
    defense-in-depth for the otherwise-unreachable case where a corrupted
    file and its pinned hash constant drift together; the tests below reach
    them directly by monkeypatching the pinned hash to the tampered file's
    own (recomputed) value, isolating one specific corruption at a time.
    """
    sampled_doc = json.loads(real_paths["sampled"].read_text(encoding="utf-8"))
    sampled_doc["candidates"][0]["route_membership"] = ["R3"]
    tampered = tmp_path / "sampled_candidates.json"
    tampered.write_text(json.dumps(sampled_doc), encoding="utf-8")
    with pytest.raises(ImmutableInputIntegrityError, match="sampled_candidates"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=real_paths["sl0017"],
            sl0018_manifest_path=real_paths["sl0018"],
            sl0021_sampled_candidates_path=tampered,
            sl0021_discovery_probe_path=real_paths["probe"],
        )


def _load_with_mutated_sampled(
    real_paths: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
) -> None:
    """Mutate a copy of the real retained sampled_candidates.json via
    *mutate*, monkeypatch the pinned Git blob SHA1 to match the mutated
    file's own recomputed hash (so the pinned-hash check does not mask the
    deeper check under test), and run the real loader against it.
    """
    import hullq.bootstrap.wikidata_sl0022_alt_route_admission as sl0022

    sampled_doc = json.loads(real_paths["sampled"].read_text(encoding="utf-8"))
    mutate(sampled_doc)
    tampered = tmp_path / "sampled_candidates.json"
    tampered_bytes = json.dumps(sampled_doc).encode("utf-8")
    tampered.write_bytes(tampered_bytes)
    monkeypatch.setattr(
        sl0022,
        "ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1",
        sl0022.git_blob_sha1(tampered_bytes),
    )
    load_and_fingerprint_immutable_inputs(
        sl0017_manifest_path=real_paths["sl0017"],
        sl0018_manifest_path=real_paths["sl0018"],
        sl0021_sampled_candidates_path=tampered,
        sl0021_discovery_probe_path=real_paths["probe"],
    )


def test_duplicate_candidate_qid_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["candidates"][1]["qid"] = doc["candidates"][0]["qid"]

    with pytest.raises(ImmutableInputIntegrityError, match="duplicate QID"):
        _load_with_mutated_sampled(real_paths, tmp_path, monkeypatch, mutate)


def test_invalid_route_membership_value_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["candidates"][0]["route_membership"] = ["R2"]

    with pytest.raises(ImmutableInputIntegrityError, match="unexpected route_membership"):
        _load_with_mutated_sampled(real_paths, tmp_path, monkeypatch, mutate)


def test_route_split_mismatch_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        # Flip one R1 candidate to R3: still a valid enum value, but breaks
        # the accepted 53/4 split without tripping the enum-value check.
        row = next(r for r in doc["candidates"] if r["route_membership"] == ["R1"])
        row["route_membership"] = ["R3"]

    with pytest.raises(ImmutableInputIntegrityError, match="route split"):
        _load_with_mutated_sampled(real_paths, tmp_path, monkeypatch, mutate)


def test_baseline_overlap_via_sampled_path_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sampled candidate QID that has been swapped to collide with the
    accepted 1,829-candidate baseline (here, an SL0017 QID) must fail closed,
    even when it otherwise still looks like a well-formed single-route row.
    """
    sl0017_manifest = json.loads(real_paths["sl0017"].read_text(encoding="utf-8"))
    a_baseline_qid = sl0017_manifest["candidates"][0]["qid"]

    def mutate(doc: dict[str, Any]) -> None:
        doc["candidates"][0]["qid"] = a_baseline_qid

    with pytest.raises(ImmutableInputIntegrityError, match="already part of the"):
        _load_with_mutated_sampled(real_paths, tmp_path, monkeypatch, mutate)


def _load_with_mutated_probe(
    real_paths: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
) -> None:
    import hullq.bootstrap.wikidata_sl0022_alt_route_admission as sl0022

    probe_doc = json.loads(real_paths["probe"].read_text(encoding="utf-8"))
    mutate(probe_doc)
    tampered = tmp_path / "discovery_probe.json"
    tampered_bytes = json.dumps(probe_doc).encode("utf-8")
    tampered.write_bytes(tampered_bytes)
    monkeypatch.setattr(
        sl0022,
        "ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1",
        sl0022.git_blob_sha1(tampered_bytes),
    )
    load_and_fingerprint_immutable_inputs(
        sl0017_manifest_path=real_paths["sl0017"],
        sl0018_manifest_path=real_paths["sl0018"],
        sl0021_sampled_candidates_path=real_paths["sampled"],
        sl0021_discovery_probe_path=tampered,
    )


def test_probe_incremental_count_mismatch_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["incremental"]["R1"]["count"] = doc["incremental"]["R1"]["count"] + 1

    with pytest.raises(ImmutableInputIntegrityError, match="incremental route counts"):
        _load_with_mutated_probe(real_paths, tmp_path, monkeypatch, mutate)


def test_probe_total_union_count_mismatch_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["cross_route_overlap"]["total_union_count"] = (
            doc["cross_route_overlap"]["total_union_count"] - 1
        )

    with pytest.raises(ImmutableInputIntegrityError, match="total_union_count"):
        _load_with_mutated_probe(real_paths, tmp_path, monkeypatch, mutate)


def test_probe_nonzero_pairwise_overlap_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["cross_route_overlap"]["pairwise"][0]["count"] = 1

    with pytest.raises(ImmutableInputIntegrityError, match="nonzero pairwise"):
        _load_with_mutated_probe(real_paths, tmp_path, monkeypatch, mutate)


# ---------------------------------------------------------------------------
# classify_sl0022_candidates — synthetic small baseline/candidate set
# ---------------------------------------------------------------------------


def _entity(qid: str, label: str | None, aliases: list[str] | None = None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=aliases or [], raw_claims={})


def _small_baseline():
    entities = [
        _entity("Q9001", "Baseline Auto Admit Yacht"),
        _entity("Q9002", "Baseline Collision Target"),
    ]
    candidates = classify_candidates(entities, retrieved_at="2026-08-01T00:00:00Z")
    clusters = compute_baseline_collision_clusters(entities)
    manifest = build_baseline_manifest_0017(
        candidates,
        generated_at="2026-08-01T00:00:00Z",
        requested_limit=2,
        unique_qids_returned=2,
        retrieval_count=1,
        extracted_record_count=2,
        target_reached=False,
        collision_clusters=clusters,
    )
    return build_baseline_snapshot_from_manifest(
        manifest, manifest_path="<synthetic>", sha256="0" * 64
    )


def _rows() -> list[dict[str, Any]]:
    return [
        {"qid": "Q1001", "route_membership": ["R1"], "label": "Clean New Class", "aliases": []},
        {"qid": "Q1002", "route_membership": ["R1"], "label": None, "aliases": []},
        {
            "qid": "Q1003",
            "route_membership": ["R1"],
            "label": "Baseline Collision Target",
            "aliases": [],
        },
        {"qid": "Q1004", "route_membership": ["R1"], "label": "Within Dup", "aliases": []},
        {"qid": "Q1005", "route_membership": ["R1"], "label": "Within Dup", "aliases": []},
        {"qid": "Q1006", "route_membership": ["R3"], "label": "Repair Signal Boat", "aliases": []},
        {"qid": "Q1007", "route_membership": ["R3"], "label": None, "aliases": []},
    ]


def test_classify_r1_clean_candidate_auto_admits() -> None:
    baseline = _small_baseline()
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    assert by_qid["Q1001"].base.decision == BootstrapDecision.AUTO_ADMIT
    assert by_qid["Q1001"].base.reason_codes == (BootstrapReasonCode.OK,)
    assert by_qid["Q1001"].base.hullq_id is not None


def test_classify_missing_label_not_admitted_for_both_r1_and_r3() -> None:
    baseline = _small_baseline()
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    assert by_qid["Q1002"].base.decision == BootstrapDecision.NOT_ADMITTED
    assert by_qid["Q1002"].base.reason_codes == (BootstrapReasonCode.MISSING_LABEL,)
    assert by_qid["Q1007"].base.decision == BootstrapDecision.NOT_ADMITTED
    assert by_qid["Q1007"].base.reason_codes == (BootstrapReasonCode.MISSING_LABEL,)


def test_classify_r1_baseline_collision_routes_review_required() -> None:
    baseline = _small_baseline()
    candidates, _clusters, baseline_collisions = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    assert by_qid["Q1003"].base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q1003"].base.reason_codes == (BootstrapReasonCode.NAME_COLLISION,)
    assert "Q1003" in baseline_collisions
    assert by_qid["Q1003"].base.hullq_id is None


def test_classify_within_57_collision_routes_review_required() -> None:
    baseline = _small_baseline()
    candidates, clusters, _bcol = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    assert by_qid["Q1004"].base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q1005"].base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert {c.qids for c in clusters} == {("Q1004", "Q1005")}


def test_classify_r3_with_label_and_no_collision_is_review_required_not_auto_admit() -> None:
    baseline = _small_baseline()
    candidates, _clusters, baseline_collisions = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    q1006 = by_qid["Q1006"]
    assert q1006.route_membership == ("R3",)
    assert "Q1006" not in baseline_collisions  # no collision — R3 alone forces review
    assert q1006.base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert q1006.base.reason_codes == (BootstrapReasonCode.R3_REPAIR_SIGNAL_REQUIRES_REVIEW,)
    assert q1006.base.hullq_id is None


def test_classify_r3_never_auto_admits_even_with_colliding_label_removed() -> None:
    """An R3 candidate whose label collides with nothing must still never
    reach AUTO_ADMIT — proving R3 short-circuits before the collision check
    (not merely happening to collide in every fixture).
    """
    baseline = _small_baseline()
    rows = [
        {
            "qid": "Q2001",
            "route_membership": ["R3"],
            "label": "Totally Unique R3 Name",
            "aliases": [],
        }
    ]
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        rows, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    assert candidates[0].base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert candidates[0].base.reason_codes == (
        BootstrapReasonCode.R3_REPAIR_SIGNAL_REQUIRES_REVIEW,
    )


def test_classify_reuses_existing_crosswalk_id_exactly() -> None:
    baseline = _small_baseline()
    rows = [{"qid": "Q3001", "route_membership": ["R1"], "label": "Reused Identity", "aliases": []}]
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        rows,
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
        existing_crosswalk={"Q3001": "BM_FIXED_ID"},
    )
    assert candidates[0].base.hullq_id == "BM_FIXED_ID"


def test_classify_rejects_qid_already_in_baseline_universe() -> None:
    baseline = _small_baseline()
    rows = [{"qid": "Q9001", "route_membership": ["R1"], "label": "Anything", "aliases": []}]
    with pytest.raises(ValueError, match="already present in the accepted"):
        classify_sl0022_candidates(rows, retrieved_at=RETRIEVED_AT, baseline=baseline)


def test_sl0022_candidate_rejects_multi_or_wrong_route_membership() -> None:
    base = BootstrapCandidate(
        qid="Q1",
        retrieved_at=RETRIEVED_AT,
        preferred_label=None,
        aliases=(),
        hullq_id=None,
        decision=BootstrapDecision.NOT_ADMITTED,
        reason_codes=(BootstrapReasonCode.MISSING_LABEL,),
        observation_id=None,
        bundle_id=None,
        bundle_version=None,
        evidence_link_id=None,
    )
    with pytest.raises(ValueError):
        Sl0022Candidate(base=base, route_membership=("R2",))
    with pytest.raises(ValueError):
        Sl0022Candidate(base=base, route_membership=("R1", "R3"))


def test_sl0022_candidate_manifest_round_trip() -> None:
    base = BootstrapCandidate(
        qid="Q42",
        retrieved_at=RETRIEVED_AT,
        preferred_label="Roundtrip Boat",
        aliases=("Alt Name",),
        hullq_id="BM_TEST_1",
        decision=BootstrapDecision.AUTO_ADMIT,
        reason_codes=(BootstrapReasonCode.OK,),
        observation_id="OBS-WD-TIER0-Q42",
        bundle_id="BUNDLE-WD-TIER0-Q42",
        bundle_version="1",
        evidence_link_id="LINK-WD-TIER0-Q42",
    )
    candidate = Sl0022Candidate(base=base, route_membership=("R1",))
    row = sl0022_candidate_to_manifest_dict(candidate)
    restored = sl0022_candidate_from_manifest_dict(row)
    assert restored == candidate


# ---------------------------------------------------------------------------
# build_sl0022_manifest — structural guards
# ---------------------------------------------------------------------------


def _full_57_candidates(baseline: Any) -> list[Sl0022Candidate]:
    rows = [
        {
            "qid": f"Q{5000 + i}",
            "route_membership": ["R1"],
            "label": f"R1 Candidate {i}",
            "aliases": [],
        }
        for i in range(53)
    ] + [
        {
            "qid": f"Q{6000 + i}",
            "route_membership": ["R3"],
            "label": f"R3 Candidate {i}",
            "aliases": [],
        }
        for i in range(4)
    ]
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        rows, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    return candidates


def test_build_sl0022_manifest_happy_path_counts() -> None:
    baseline = _small_baseline()
    candidates = _full_57_candidates(baseline)
    manifest = build_sl0022_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        within_57_clusters=[],
        baseline_collisions={},
        inputs=_fake_inputs(baseline),
    )
    assert manifest["counts"]["candidates_processed"] == 57
    assert manifest["counts"]["auto_admit"] == 53
    assert manifest["counts"]["auto_admit_r3"] == 0
    assert manifest["counts"]["review_required"] == 4
    assert manifest["counts"]["not_admitted"] == 0
    assert manifest["counts"]["combined_canonical_boat_model_count_expected"] == (
        len(baseline.auto_admit_qids) + 53
    )


def test_build_sl0022_manifest_rejects_wrong_total_count() -> None:
    baseline = _small_baseline()
    candidates = _full_57_candidates(baseline)[:-1]
    with pytest.raises(ValueError, match="exactly 57"):
        build_sl0022_manifest(
            candidates,
            generated_at=RETRIEVED_AT,
            baseline=baseline,
            within_57_clusters=[],
            baseline_collisions={},
            inputs=_fake_inputs(baseline),
        )


def test_build_sl0022_manifest_rejects_r3_auto_admit() -> None:
    baseline = _small_baseline()
    candidates = _full_57_candidates(baseline)
    tampered_r3 = next(c for c in candidates if c.route_membership == ("R3",))
    tampered_base = BootstrapCandidate(
        qid=tampered_r3.base.qid,
        retrieved_at=tampered_r3.base.retrieved_at,
        preferred_label=tampered_r3.base.preferred_label,
        aliases=tampered_r3.base.aliases,
        hullq_id="BM_TAMPERED",
        decision=BootstrapDecision.AUTO_ADMIT,
        reason_codes=(BootstrapReasonCode.OK,),
        observation_id=tampered_r3.base.observation_id or f"OBS-{tampered_r3.base.qid}",
        bundle_id=tampered_r3.base.bundle_id or f"BUNDLE-{tampered_r3.base.qid}",
        bundle_version="1",
        evidence_link_id=f"LINK-{tampered_r3.base.qid}",
    )
    tampered_candidates = [
        Sl0022Candidate(base=tampered_base, route_membership=("R3",)) if c is tampered_r3 else c
        for c in candidates
    ]
    with pytest.raises(ValueError, match="R3 fail-closed rule violated"):
        build_sl0022_manifest(
            tampered_candidates,
            generated_at=RETRIEVED_AT,
            baseline=baseline,
            within_57_clusters=[],
            baseline_collisions={},
            inputs=_fake_inputs(baseline),
        )


def _fake_inputs(baseline: Any) -> Any:
    from hullq.bootstrap.wikidata_sl0022_alt_route_admission import Sl0022ImmutableInputs

    return Sl0022ImmutableInputs(
        baseline=baseline,
        retained_candidate_rows=(),
        sl0017_manifest_path="<synthetic-0017>",
        sl0017_sha256="0" * 64,
        sl0018_manifest_path="<synthetic-0018>",
        sl0018_sha256="1" * 64,
        sl0021_sampled_candidates_path="<synthetic-sampled>",
        sl0021_sampled_candidates_sha1="2" * 40,
        sl0021_discovery_probe_path="<synthetic-probe>",
        sl0021_discovery_probe_sha1="3" * 40,
    )


# ---------------------------------------------------------------------------
# verify_sl0022_manifest_self_consistency — tamper resistance
# ---------------------------------------------------------------------------


def _valid_manifest_and_inputs() -> tuple[dict[str, Any], Any]:
    baseline = _small_baseline()
    candidates = _full_57_candidates(baseline)
    inputs = _fake_inputs(baseline)
    object.__setattr__(
        inputs,
        "retained_candidate_rows",
        tuple(
            {
                "qid": c.base.qid,
                "route_membership": list(c.route_membership),
                "label": c.base.preferred_label,
                "aliases": list(c.base.aliases),
            }
            for c in candidates
        ),
    )
    manifest = build_sl0022_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        within_57_clusters=[],
        baseline_collisions={},
        inputs=inputs,
    )
    return manifest, inputs


def test_verify_self_consistency_passes_on_untampered_manifest() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    assert verify_sl0022_manifest_self_consistency(manifest, inputs=inputs) == []


def test_verify_detects_tampered_decision() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    row = next(r for r in manifest["candidates"] if r["decision"] == "review_required")
    row["decision"] = "auto_admit"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("decision" in m for m in mismatches)


def test_verify_detects_r3_auto_admit_directly() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    row = next(r for r in manifest["candidates"] if r["route_membership"] == ["R3"])
    row["decision"] = "auto_admit"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("R3 fail-closed rule" in m for m in mismatches)


def test_verify_detects_tampered_route_membership() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    row = manifest["candidates"][0]
    row["route_membership"] = ["R3"] if row["route_membership"] == ["R1"] else ["R1"]
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("route_membership" in m for m in mismatches)


def test_verify_detects_tampered_qid() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["candidates"][0]["qid"] = "Q999999"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("candidate QID set mismatch" in m for m in mismatches)


def test_verify_detects_tampered_crosswalk_mapping() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    entry = next(
        e for e in manifest["retained_crosswalk"] if e["qid"] == manifest["candidates"][0]["qid"]
    )
    original_id = entry["hullq_id"]
    entry["hullq_id"] = original_id + "-TAMPERED"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    # Recomputation reuses the (now tampered) crosswalk id, so the retained
    # candidate row's own hullq_id (untouched) diverges from what the
    # crosswalk claims — surfaced as a hullq_id field mismatch.
    assert any("hullq_id" in m for m in mismatches)


def test_verify_detects_tampered_counts() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["counts"]["auto_admit"] = manifest["counts"]["auto_admit"] + 1
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("counts.auto_admit" in m for m in mismatches)


def test_verify_detects_tampered_expected_total() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["counts"]["combined_canonical_boat_model_count_expected"] += 1
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("combined_canonical_boat_model_count_expected" in m for m in mismatches)


def test_verify_detects_tampered_baseline_reference_counts() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["immutable_inputs"]["retained_direct_discovery_count"] += 1
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("retained_direct_discovery_count" in m for m in mismatches)


def test_verify_detects_tampered_collision_membership() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["collisions"]["baseline"].append(
        {"candidate_qid": "Q999999", "baseline_qids": ["Q1"], "shared_keys": ["fake"]}
    )
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("collisions.baseline" in m for m in mismatches)


def test_verify_detects_tampered_candidate_universe_totals() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["candidate_universe"]["total"] = 58
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("candidate_universe.total" in m for m in mismatches)
