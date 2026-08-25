"""Unit tests for the SLICE-0022 retained alternative-route Tier-0 admission
safety pilot pure logic (``hullq.bootstrap.wikidata_sl0022_alt_route_admission``),
under the R1 admission governance amendment
(``docs/slices/SLICE-0022-r1-admission-governance-amendment.md``).

Covers:
- exact Git blob SHA1 fingerprinting;
- fail-closed immutable-input loading against the real committed retained
  artifacts, and against deliberately tampered copies;
- deterministic classification: R1 route membership alone never produces
  AUTO_ADMIT (reason ``r1_alternative_route_requires_review``), R3 remains
  fail-closed review-bound, missing-label candidates are NOT_ADMITTED
  regardless of route, and no SLICE-0022 candidate can ever reach
  AUTO_ADMIT — including the retained real-data regression case Q232393;
- retained source-fact timestamp provenance (never a SLICE-0022 computation
  time);
- manifest construction guards (exact 57/53/4 split, never-AUTO_ADMIT,
  crosswalk bijection against the accepted baseline);
- offline self-consistency verification and its tamper resistance across
  every hardened category (ordering, timestamps, collision records, full
  counts, crosswalk bijection, static/usage semantics, immutable references);
- retained non-self-referential artifact digests;
- offline self-consistency verification of checked-in PostgreSQL replay
  evidence (REPLAY-RESULT.json) against the already-verified manifest and
  accepted baseline, and tamper resistance across its zero-tolerance
  invariants.
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
    Sl0022ImmutableInputs,
    build_artifact_digests,
    build_sl0022_manifest,
    classify_sl0022_candidates,
    git_blob_sha1,
    load_and_fingerprint_immutable_inputs,
    sl0022_candidate_from_manifest_dict,
    sl0022_candidate_to_manifest_dict,
    verify_artifact_digests,
    verify_replay_result_self_consistency,
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
    for row in inputs.retained_candidate_rows:
        assert row["qid"] not in inputs.baseline.candidate_qids
    # Retained source-fact acquisition timestamp: the accepted
    # sampled_candidates.json document's own top-level generated_at.
    assert inputs.sl0021_generated_at == RETRIEVED_AT


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
    route split, discovery_probe corroboration, baseline-overlap, missing
    generated_at) are defense-in-depth for the otherwise-unreachable case
    where a corrupted file and its pinned hash constant drift together; the
    tests below reach them directly by monkeypatching the pinned hash to the
    tampered file's own (recomputed) value, isolating one corruption at a
    time.
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
        row = next(r for r in doc["candidates"] if r["route_membership"] == ["R1"])
        row["route_membership"] = ["R3"]

    with pytest.raises(ImmutableInputIntegrityError, match="route split"):
        _load_with_mutated_sampled(real_paths, tmp_path, monkeypatch, mutate)


def test_baseline_overlap_via_sampled_path_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sl0017_manifest = json.loads(real_paths["sl0017"].read_text(encoding="utf-8"))
    a_baseline_qid = sl0017_manifest["candidates"][0]["qid"]

    def mutate(doc: dict[str, Any]) -> None:
        doc["candidates"][0]["qid"] = a_baseline_qid

    with pytest.raises(ImmutableInputIntegrityError, match="already part of the"):
        _load_with_mutated_sampled(real_paths, tmp_path, monkeypatch, mutate)


def test_missing_generated_at_fails_closed(
    real_paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hullq.bootstrap.wikidata_sl0022_alt_route_admission as sl0022

    sampled_doc = json.loads(real_paths["sampled"].read_text(encoding="utf-8"))
    del sampled_doc["generated_at"]
    tampered = tmp_path / "sampled_candidates.json"
    tampered_bytes = json.dumps(sampled_doc).encode("utf-8")
    tampered.write_bytes(tampered_bytes)
    monkeypatch.setattr(
        sl0022,
        "ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1",
        sl0022.git_blob_sha1(tampered_bytes),
    )
    with pytest.raises(ImmutableInputIntegrityError, match="generated_at"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=real_paths["sl0017"],
            sl0018_manifest_path=real_paths["sl0018"],
            sl0021_sampled_candidates_path=tampered,
            sl0021_discovery_probe_path=real_paths["probe"],
        )


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


def test_classify_r1_clean_candidate_is_review_required_never_auto_admit() -> None:
    """R1 route membership alone can never produce AUTO_ADMIT, even with a
    usable label and zero collisions (the R1 admission governance amendment)."""
    baseline = _small_baseline()
    candidates, _clusters, baseline_collisions = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    q1001 = by_qid["Q1001"]
    assert "Q1001" not in baseline_collisions
    assert q1001.base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert q1001.base.reason_codes == (BootstrapReasonCode.R1_ALTERNATIVE_ROUTE_REQUIRES_REVIEW,)
    assert q1001.base.hullq_id is None


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


def test_classify_r1_baseline_collision_still_review_required_same_reason() -> None:
    """Collision evidence is still computed/retained for audit, but no
    longer changes the R1 decision or reason — it was already
    REVIEW_REQUIRED / r1_alternative_route_requires_review regardless."""
    baseline = _small_baseline()
    candidates, _clusters, baseline_collisions = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    q1003 = by_qid["Q1003"]
    assert "Q1003" in baseline_collisions  # collision evidence still computed
    assert q1003.base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert q1003.base.reason_codes == (BootstrapReasonCode.R1_ALTERNATIVE_ROUTE_REQUIRES_REVIEW,)
    assert q1003.base.hullq_id is None


def test_classify_within_57_collision_still_review_required_same_reason() -> None:
    baseline = _small_baseline()
    candidates, clusters, _bcol = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    assert {c.qids for c in clusters} == {("Q1004", "Q1005")}  # collision evidence still computed
    for qid in ("Q1004", "Q1005"):
        assert by_qid[qid].base.decision == BootstrapDecision.REVIEW_REQUIRED
        assert by_qid[qid].base.reason_codes == (
            BootstrapReasonCode.R1_ALTERNATIVE_ROUTE_REQUIRES_REVIEW,
        )


def test_classify_r3_with_label_and_no_collision_is_review_required() -> None:
    baseline = _small_baseline()
    candidates, _clusters, baseline_collisions = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    by_qid = {c.base.qid: c for c in candidates}
    q1006 = by_qid["Q1006"]
    assert q1006.route_membership == ("R3",)
    assert "Q1006" not in baseline_collisions
    assert q1006.base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert q1006.base.reason_codes == (BootstrapReasonCode.R3_REPAIR_SIGNAL_REQUIRES_REVIEW,)
    assert q1006.base.hullq_id is None


def test_classify_never_produces_auto_admit_regardless_of_route() -> None:
    baseline = _small_baseline()
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        _rows(), retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    assert all(c.base.decision != BootstrapDecision.AUTO_ADMIT for c in candidates)


def test_classify_reuses_existing_crosswalk_id_exactly_for_review_bound_candidate() -> None:
    """Defense-in-depth: if an already-existing historical mapping exists for
    a QID, it is reused exactly even though the candidate is REVIEW_REQUIRED
    (never AUTO_ADMIT) — no candidate mints a NEW mapping, but an existing
    one is never silently dropped either."""
    baseline = _small_baseline()
    rows = [{"qid": "Q3001", "route_membership": ["R1"], "label": "Reused Identity", "aliases": []}]
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        rows,
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
        existing_crosswalk={"Q3001": "BM_FIXED_ID"},
    )
    assert candidates[0].base.hullq_id == "BM_FIXED_ID"
    assert candidates[0].base.decision == BootstrapDecision.REVIEW_REQUIRED


def test_classify_rejects_qid_already_in_baseline_universe() -> None:
    baseline = _small_baseline()
    rows = [{"qid": "Q9001", "route_membership": ["R1"], "label": "Anything", "aliases": []}]
    with pytest.raises(ValueError, match="already present in the accepted"):
        classify_sl0022_candidates(rows, retrieved_at=RETRIEVED_AT, baseline=baseline)


def test_classify_q232393_real_retained_regression_case_is_review_required() -> None:
    """Q232393 ("Zweier-Canadier", a German canoe-class term retained via the
    R1 sailboat-class-closure route) triggered the R1 admission governance
    amendment: it satisfied every pre-amendment Tier-0 admission condition
    (usable label, no baseline collision, no within-57 collision) yet is not
    a sailboat. It MUST NOT be AUTO_ADMIT under the amended rule — it is
    REVIEW_REQUIRED with r1_alternative_route_requires_review purely because
    of its R1 route membership, with no description/P31/P279 inference
    involved.
    """
    inputs = load_and_fingerprint_immutable_inputs()
    candidates, _clusters, _bcol = classify_sl0022_candidates(
        list(inputs.retained_candidate_rows),
        retrieved_at=inputs.sl0021_generated_at,
        baseline=inputs.baseline,
    )
    q232393 = next(c for c in candidates if c.base.qid == "Q232393")
    assert q232393.route_membership == ("R1",)
    assert q232393.base.preferred_label == "Zweier-Canadier"
    assert q232393.base.decision == BootstrapDecision.REVIEW_REQUIRED
    assert q232393.base.reason_codes == (BootstrapReasonCode.R1_ALTERNATIVE_ROUTE_REQUIRES_REVIEW,)
    assert q232393.base.hullq_id is None


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
        hullq_id=None,
        decision=BootstrapDecision.REVIEW_REQUIRED,
        reason_codes=(BootstrapReasonCode.R1_ALTERNATIVE_ROUTE_REQUIRES_REVIEW,),
        observation_id="OBS-WD-TIER0-Q42",
        bundle_id="BUNDLE-WD-TIER0-Q42",
        bundle_version="1",
        evidence_link_id=None,
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


def _fake_inputs(baseline: Any) -> Sl0022ImmutableInputs:
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
        sl0021_generated_at=RETRIEVED_AT,
    )


def test_build_sl0022_manifest_happy_path_counts() -> None:
    baseline = _small_baseline()
    candidates = _full_57_candidates(baseline)
    manifest = build_sl0022_manifest(
        candidates,
        generated_at="2026-08-25T00:00:00+00:00",
        baseline=baseline,
        within_57_clusters=[],
        baseline_collisions={},
        inputs=_fake_inputs(baseline),
    )
    assert manifest["counts"]["candidates_processed"] == 57
    assert manifest["counts"]["auto_admit"] == 0
    assert manifest["counts"]["auto_admit_r1"] == 0
    assert manifest["counts"]["auto_admit_r3"] == 0
    assert manifest["counts"]["review_required"] == 57
    assert manifest["counts"]["not_admitted"] == 0
    assert manifest["counts"]["combined_canonical_boat_model_count_expected"] == len(
        baseline.auto_admit_qids
    )
    # No new mapping is ever minted: the retained crosswalk stays exactly the
    # accepted baseline crosswalk.
    assert manifest["counts"]["newly_minted_id_count"] == 0
    assert manifest["counts"]["retained_crosswalk_count"] == len(baseline.crosswalk)
    assert manifest["acquired_at"] == RETRIEVED_AT
    assert manifest["generated_at"] == "2026-08-25T00:00:00+00:00"


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


def test_build_sl0022_manifest_rejects_any_auto_admit_from_either_route() -> None:
    baseline = _small_baseline()
    candidates = _full_57_candidates(baseline)
    tampered_target = next(c for c in candidates if c.route_membership == ("R1",))
    tampered_base = BootstrapCandidate(
        qid=tampered_target.base.qid,
        retrieved_at=tampered_target.base.retrieved_at,
        preferred_label=tampered_target.base.preferred_label,
        aliases=tampered_target.base.aliases,
        hullq_id="BM_TAMPERED",
        decision=BootstrapDecision.AUTO_ADMIT,
        reason_codes=(BootstrapReasonCode.OK,),
        observation_id=tampered_target.base.observation_id or f"OBS-{tampered_target.base.qid}",
        bundle_id=tampered_target.base.bundle_id or f"BUNDLE-{tampered_target.base.qid}",
        bundle_version="1",
        evidence_link_id=f"LINK-{tampered_target.base.qid}",
    )
    tampered_candidates = [
        Sl0022Candidate(base=tampered_base, route_membership=("R1",)) if c is tampered_target else c
        for c in candidates
    ]
    with pytest.raises(ValueError, match="R1 admission governance amendment violated"):
        build_sl0022_manifest(
            tampered_candidates,
            generated_at=RETRIEVED_AT,
            baseline=baseline,
            within_57_clusters=[],
            baseline_collisions={},
            inputs=_fake_inputs(baseline),
        )


# ---------------------------------------------------------------------------
# verify_sl0022_manifest_self_consistency — tamper resistance
# ---------------------------------------------------------------------------


def _valid_manifest_and_inputs() -> tuple[dict[str, Any], Sl0022ImmutableInputs]:
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
        extracted_record_count=len(candidates),
    )
    return manifest, inputs


def test_verify_self_consistency_passes_on_untampered_manifest() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    assert verify_sl0022_manifest_self_consistency(manifest, inputs=inputs) == []


def test_verify_detects_tampered_decision() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    row = manifest["candidates"][0]
    row["decision"] = "not_admitted"
    row["reason_codes"] = ["missing_label"]
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("decision" in m for m in mismatches)


def test_verify_detects_auto_admit_directly() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    row = manifest["candidates"][0]
    row["decision"] = "auto_admit"
    row["reason_codes"] = ["ok"]
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("R1 admission governance" in m for m in mismatches)


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


def test_verify_detects_duplicate_candidate_row() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    duplicate = dict(manifest["candidates"][0])
    duplicate["qid"] = manifest["candidates"][1]["qid"]
    manifest["candidates"][0] = duplicate
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("duplicate QID row" in m for m in mismatches)


def test_verify_detects_reordered_candidates() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["candidates"][0], manifest["candidates"][1] = (
        manifest["candidates"][1],
        manifest["candidates"][0],
    )
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("order does not match" in m for m in mismatches)


def test_verify_detects_tampered_retrieved_at() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["candidates"][0]["retrieved_at"] = "2099-01-01T00:00:00+00:00"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("retrieved_at" in m for m in mismatches)


def test_verify_detects_tampered_acquired_at() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["acquired_at"] = "2099-01-01T00:00:00+00:00"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any(m.startswith("acquired_at=") for m in mismatches)


def test_verify_detects_tampered_manifest_version() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["manifest_version"] = "0022-v1"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("manifest_version" in m for m in mismatches)


def test_verify_detects_tampered_source_id() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["source_id"] = "SRC_WRONG"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any(m.startswith("source_id=") for m in mismatches)


def test_verify_detects_nonzero_retrieval_count() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["usage_metrics"]["retrieval_count"] = 1
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("retrieval_count" in m for m in mismatches)


def test_verify_detects_tampered_extracted_record_count() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["usage_metrics"]["extracted_record_count"] = 999
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("extracted_record_count" in m for m in mismatches)


def test_verify_detects_tampered_crosswalk_dropped_baseline_entry() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["retained_crosswalk"].pop()
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("not byte-identical" in m for m in mismatches)


def test_verify_detects_tampered_crosswalk_unjustified_extra_entry() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["retained_crosswalk"].append({"qid": "Q9999999", "hullq_id": "BM_UNJUSTIFIED"})
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("not byte-identical" in m for m in mismatches)


def test_verify_detects_duplicate_qid_in_retained_crosswalk_with_conflicting_id() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    existing = manifest["retained_crosswalk"][0]
    manifest["retained_crosswalk"].append({"qid": existing["qid"], "hullq_id": "BM_CONFLICTING"})
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("fail-closed parsing" in m for m in mismatches)


def test_verify_detects_same_hullq_id_assigned_to_two_qids() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    first, second = manifest["retained_crosswalk"][0], manifest["retained_crosswalk"][1]
    second["hullq_id"] = first["hullq_id"]
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("fail-closed parsing" in m for m in mismatches)


def test_verify_detects_tampered_counts() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["counts"]["review_required"] = manifest["counts"]["review_required"] + 1
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("counts.review_required" in m for m in mismatches)


def test_verify_detects_tampered_reason_breakdown() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["counts"]["reason_breakdown"]["missing_label"] = 999
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("counts.reason_breakdown" in m for m in mismatches)


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


def test_verify_detects_tampered_immutable_reference_path() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["immutable_inputs"]["sl0017_manifest"]["path"] = "some/other/path.json"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("sl0017_manifest.path" in m for m in mismatches)


def test_verify_detects_tampered_implementation_head() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["immutable_inputs"]["sl0021_implementation_head"] = "deadbeef"
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("sl0021_implementation_head" in m for m in mismatches)


def test_verify_detects_tampered_collision_membership() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["collisions"]["baseline"].append(
        {"candidate_qid": "Q999999", "baseline_qids": ["Q1"], "shared_keys": ["fake"]}
    )
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("collisions.baseline" in m for m in mismatches)


def test_verify_detects_tampered_within_57_shared_keys() -> None:
    """Full-record collision comparison, not merely cluster membership: a
    cluster whose QIDs are unchanged but whose shared_keys were tampered must
    still be flagged."""
    baseline = _small_baseline()
    rows = [
        {"qid": "Q7001", "route_membership": ["R1"], "label": "Collide Twins", "aliases": []},
        {"qid": "Q7002", "route_membership": ["R1"], "label": "Collide Twins", "aliases": []},
        *[
            {
                "qid": f"Q{7100 + i}",
                "route_membership": ["R1"],
                "label": f"Filler {i}",
                "aliases": [],
            }
            for i in range(51)
        ],
        *[
            {
                "qid": f"Q{7200 + i}",
                "route_membership": ["R3"],
                "label": f"R3 Filler {i}",
                "aliases": [],
            }
            for i in range(4)
        ],
    ]
    candidates, clusters, baseline_collisions = classify_sl0022_candidates(
        rows, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
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
        within_57_clusters=clusters,
        baseline_collisions=baseline_collisions,
        inputs=inputs,
    )
    assert manifest["collisions"]["within_57"], (
        "fixture must contain at least one collision cluster"
    )
    manifest["collisions"]["within_57"][0]["shared_keys"] = ["tampered key"]
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("collisions.within_57" in m for m in mismatches)


def test_verify_detects_tampered_candidate_universe_totals() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    manifest["candidate_universe"]["total"] = 58
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)
    assert any("candidate_universe.total" in m for m in mismatches)


# ---------------------------------------------------------------------------
# retained artifact digests — non-self-referential
# ---------------------------------------------------------------------------


def _write_covered_files(tmp_path: Path) -> dict[str, Path]:
    manifest_path = tmp_path / "manifest.json"
    schema_path = tmp_path / "manifest_schema.json"
    report_path = tmp_path / "REPORT.md"
    manifest_path.write_text('{"a": 1}', encoding="utf-8")
    schema_path.write_text('{"b": 2}', encoding="utf-8")
    report_path.write_text("# report", encoding="utf-8")
    return {
        "manifest.json": manifest_path,
        "manifest_schema.json": schema_path,
        "REPORT.md": report_path,
    }


def test_build_and_verify_artifact_digests_round_trip(tmp_path: Path) -> None:
    paths = _write_covered_files(tmp_path)
    doc = build_artifact_digests(generated_at=RETRIEVED_AT, paths=paths)
    assert doc["excludes_self"] == "ARTIFACT-DIGESTS.json"
    assert set(doc["digests"]) == {"manifest.json", "manifest_schema.json", "REPORT.md"}
    assert verify_artifact_digests(doc, paths=paths) == []


def test_build_artifact_digests_rejects_wrong_paths_keys(tmp_path: Path) -> None:
    paths = _write_covered_files(tmp_path)
    del paths["REPORT.md"]
    with pytest.raises(ValueError, match="paths keys must be exactly"):
        build_artifact_digests(generated_at=RETRIEVED_AT, paths=paths)


def test_verify_artifact_digests_detects_tampered_file_content(tmp_path: Path) -> None:
    paths = _write_covered_files(tmp_path)
    doc = build_artifact_digests(generated_at=RETRIEVED_AT, paths=paths)
    paths["manifest.json"].write_text('{"a": 2}', encoding="utf-8")
    mismatches = verify_artifact_digests(doc, paths=paths)
    assert any("manifest.json" in m for m in mismatches)


def test_verify_artifact_digests_detects_missing_target_file(tmp_path: Path) -> None:
    paths = _write_covered_files(tmp_path)
    doc = build_artifact_digests(generated_at=RETRIEVED_AT, paths=paths)
    paths["REPORT.md"].unlink()
    mismatches = verify_artifact_digests(doc, paths=paths)
    assert any("missing on disk" in m for m in mismatches)


def test_verify_artifact_digests_detects_unexpected_extra_entry(tmp_path: Path) -> None:
    paths = _write_covered_files(tmp_path)
    doc = build_artifact_digests(generated_at=RETRIEVED_AT, paths=paths)
    doc["digests"]["EXTRA.json"] = "sha256:" + "0" * 64
    mismatches = verify_artifact_digests(doc, paths=paths)
    assert any("unexpected digest entries" in m for m in mismatches)


# ---------------------------------------------------------------------------
# verify_replay_result_self_consistency — checked-in PostgreSQL replay
# evidence, tamper resistance
# ---------------------------------------------------------------------------


def _valid_replay_pass(expected_bundle_count: int, expected_admission_count: int) -> dict[str, Any]:
    return {
        "bundle": {
            "imported": expected_bundle_count,
            "already_present": 0,
            "conflict": 0,
            "error": 0,
            "unexpected_status": 0,
        },
        "admission": {
            "imported": expected_admission_count,
            "already_present": 0,
            "conflict": 0,
            "reference_error": 0,
            "error": 0,
            "unexpected_status": 0,
        },
        "expected_counts_match": True,
        "prior_baseline_verified_before_sl0022": {
            "counts_match": True,
            "id_set_matches": True,
            "readback_mismatches": 0,
        },
        "readback": {
            "mismatches": 0,
            "prior_baseline_drift_mismatches": 0,
            "unexpected_canonical_rows_for_non_admitted": 0,
            "canonical_id_set_matches": True,
            "no_stray_brand_organization_boatdesign_rows": True,
            "stray_row_counts": {
                "canonical_brands": 0,
                "canonical_organizations": 0,
                "canonical_boat_designs": 0,
            },
        },
        "reimport": {
            "already_imported": expected_bundle_count + expected_admission_count,
            "conflict": 0,
            "error": 0,
            "wall_clock_seconds": 0.01,
        },
        "wall_clock_seconds": 0.01,
    }


def _valid_replay_result(manifest: dict[str, Any], baseline: Any) -> dict[str, Any]:
    baseline_labeled = len(baseline.auto_admit_qids) + len(baseline.review_required_qids)
    sl0022_labeled = sum(
        1 for row in manifest["candidates"] if row.get("preferred_label") is not None
    )
    expected_bundle_count = baseline_labeled + sl0022_labeled
    expected_admission_count = len(baseline.auto_admit_qids) + manifest["counts"]["auto_admit"]
    return {
        "schema_version": "0022-replay-v1",
        "run_timestamp": "2026-08-25T00:00:00+00:00",
        "postgresql_version": "PostgreSQL 18.6 test",
        "prior_baseline_candidates": len(baseline.candidate_qids),
        "prior_baseline_auto_admit": len(baseline.auto_admit_qids),
        "sl0022_candidates": manifest["candidate_universe"]["total"],
        "sl0022_auto_admit": manifest["counts"]["auto_admit"],
        "expected": {
            "combined_bundle_count": expected_bundle_count,
            "combined_admission_count": expected_admission_count,
        },
        "first_pass": _valid_replay_pass(expected_bundle_count, expected_admission_count),
        "fresh_schema_rerun": _valid_replay_pass(expected_bundle_count, expected_admission_count),
        "all_zero_tolerance_conditions_clear": True,
    }


def test_verify_replay_result_passes_on_untampered_result() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    assert (
        verify_replay_result_self_consistency(
            replay_result, manifest=manifest, baseline=inputs.baseline
        )
        == []
    )


def test_verify_replay_result_passes_against_real_committed_artifacts() -> None:
    """The actual checked-in SLICE-0022 manifest.json + REPLAY-RESULT.json
    must themselves be self-consistent — the same check normal CI runs."""
    inputs = load_and_fingerprint_immutable_inputs()
    base = ROOT / "research" / "bootstrap" / "wikidata" / "sl0022-alt-route-admission"
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    replay_result = json.loads((base / "REPLAY-RESULT.json").read_text(encoding="utf-8"))
    assert (
        verify_replay_result_self_consistency(
            replay_result, manifest=manifest, baseline=inputs.baseline
        )
        == []
    )


def test_verify_replay_result_detects_sl0022_auto_admit_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["sl0022_auto_admit"] = 1
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("sl0022_auto_admit" in m for m in mismatches)


def test_verify_replay_result_detects_expected_combined_admission_count_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["expected"]["combined_admission_count"] += 1
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("expected.combined_admission_count" in m for m in mismatches)


def test_verify_replay_result_detects_expected_combined_bundle_count_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["expected"]["combined_bundle_count"] += 1
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("expected.combined_bundle_count" in m for m in mismatches)


def test_verify_replay_result_detects_all_zero_tolerance_flag_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["all_zero_tolerance_conditions_clear"] = False
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("all_zero_tolerance_conditions_clear" in m for m in mismatches)


def test_verify_replay_result_detects_first_pass_counter_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["first_pass"]["bundle"]["conflict"] = 1
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("first_pass.bundle.conflict" in m for m in mismatches)


def test_verify_replay_result_detects_fresh_schema_counter_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["fresh_schema_rerun"]["readback"]["mismatches"] = 1
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("fresh_schema_rerun.readback.mismatches" in m for m in mismatches)


def test_verify_replay_result_detects_stray_row_count_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["first_pass"]["readback"]["stray_row_counts"]["canonical_brands"] = 1
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("stray_row_counts[canonical_brands]" in m for m in mismatches)


def test_verify_replay_result_detects_schema_version_changed() -> None:
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["schema_version"] = "0022-replay-v0"
    mismatches = verify_replay_result_self_consistency(
        replay_result, manifest=manifest, baseline=inputs.baseline
    )
    assert any("schema_version" in m for m in mismatches)


def test_verify_replay_result_ignores_runtime_variable_fields() -> None:
    """run_timestamp/postgresql_version/wall_clock_seconds are accepted as
    non-deterministic metadata and must never be compared to a fixed value."""
    manifest, inputs = _valid_manifest_and_inputs()
    replay_result = _valid_replay_result(manifest, inputs.baseline)
    replay_result["run_timestamp"] = "1999-01-01T00:00:00+00:00"
    replay_result["postgresql_version"] = "some other string entirely"
    replay_result["first_pass"]["wall_clock_seconds"] = 999.0
    replay_result["first_pass"]["reimport"]["wall_clock_seconds"] = 999.0
    assert (
        verify_replay_result_self_consistency(
            replay_result, manifest=manifest, baseline=inputs.baseline
        )
        == []
    )
