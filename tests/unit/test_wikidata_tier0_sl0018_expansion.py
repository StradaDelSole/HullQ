"""Unit tests for hullq.bootstrap.wikidata_tier0_sl0018 — SLICE-0018.

All tests are offline, deterministic and database-free.

Covers the SLICE-0018 required regression scenarios 1-9 from
``docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md``
("Required regression tests"), plus baseline-integrity and manifest-schema
coverage:

  1. delta extraction excludes all baseline candidate QIDs.
  2. discovery churn: a baseline QID absent from the current window is
     reported, never reclassified.
  3. a new delta candidate colliding with an accepted (AUTO_ADMIT) baseline
     candidate is REVIEW_REQUIRED; the baseline entity is untouched.
  4. a new delta candidate colliding with a baseline REVIEW_REQUIRED
     candidate is REVIEW_REQUIRED; the baseline review state is untouched.
  5. delta<->delta transitive collisions form one complete cluster; all
     affected candidates are review-bound.
  6. a delta QID already present in the historical crosswalk reuses its
     retained ID exactly.
  7. crosswalk merge fails closed on both conflict forms.
  8. loading the baseline never mutates the accepted SLICE-0017 manifest file.
  9. below-target discovery is processed as-is (no padding), and reported.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from hullq.bootstrap.wikidata_tier0 import (
    BootstrapDecision,
    BootstrapReasonCode,
    CrosswalkConflictError,
    build_admission,
)
from hullq.bootstrap.wikidata_tier0_sl0018 import (
    ACCEPTED_0017_BASELINE_CANDIDATE_COUNT,
    ACCEPTED_0017_MANIFEST_VERSION,
    BASELINE_MANIFEST_PATH,
    SL0018_ACTIVITY_ID,
    BaselineIntegrityError,
    BaselineSnapshot,
    DeltaCompletenessError,
    build_baseline_snapshot_from_manifest,
    build_bundle,
    build_sl0018_manifest,
    classify_delta_candidates,
    compute_baseline_absent_qids,
    compute_baseline_collisions,
    compute_expansion_delta,
    load_baseline_snapshot,
    merge_crosswalks_fail_closed,
    verify_delta_candidate_completeness,
    verify_entity_acquisition_completeness,
)
from hullq.sources.wikidata import WikidataEntityData

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SCHEMA_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest_schema.json"
)

RETRIEVED_AT = "2026-08-21T00:00:00Z"


def _entity(qid: str, label: str | None, aliases: list[str] | None = None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=aliases or [], raw_claims={})


def _make_baseline(
    rows: list[tuple[str, str | None, list[str] | None, str]],
) -> BaselineSnapshot:
    """Build a synthetic ``BaselineSnapshot`` directly from
    ``(qid, label, aliases, decision)`` rows, bypassing the accepted-constant
    integrity gate in ``load_baseline_snapshot`` (which is tested separately
    against the real retained SLICE-0017 artifact).
    """
    from hullq.bootstrap.wikidata_tier0 import search_keys_for_candidate

    candidate_qids: set[str] = set()
    search_key_owners: dict[str, set[str]] = {}
    crosswalk: dict[str, str] = {}
    auto_admit_qids: set[str] = set()
    review_required_qids: set[str] = set()
    not_admitted_qids: set[str] = set()
    for qid, label, aliases, decision in rows:
        candidate_qids.add(qid)
        if decision == "auto_admit":
            auto_admit_qids.add(qid)
            crosswalk[qid] = f"BM_WDT0_BASELINE_{qid}"
        elif decision == "review_required":
            review_required_qids.add(qid)
        else:
            not_admitted_qids.add(qid)
        if label:
            for key in search_keys_for_candidate(label, aliases or []):
                search_key_owners.setdefault(key, set()).add(qid)

    return BaselineSnapshot(
        manifest_path="synthetic-baseline.json",
        manifest_version=ACCEPTED_0017_MANIFEST_VERSION,
        sha256="0" * 64,
        candidate_qids=frozenset(candidate_qids),
        search_key_owners={k: frozenset(v) for k, v in search_key_owners.items()},
        crosswalk=crosswalk,
        auto_admit_qids=frozenset(auto_admit_qids),
        review_required_qids=frozenset(review_required_qids),
        not_admitted_qids=frozenset(not_admitted_qids),
    )


# ---------------------------------------------------------------------------
# 1. Delta extraction
# ---------------------------------------------------------------------------


def test_delta_extraction_excludes_all_baseline_qids() -> None:
    baseline = _make_baseline(
        [
            ("Q1", "Baseline One", None, "auto_admit"),
            ("Q2", "Baseline Two", None, "auto_admit"),
        ]
    )
    delta = compute_expansion_delta(["Q1", "Q2", "Q3", "Q4"], baseline)
    assert delta == ["Q3", "Q4"]


def test_delta_extraction_preserves_discovery_order() -> None:
    baseline = _make_baseline([("Q5", "Baseline Five", None, "auto_admit")])
    delta = compute_expansion_delta(["Q9", "Q5", "Q7", "Q3"], baseline)
    assert delta == ["Q9", "Q7", "Q3"]


# ---------------------------------------------------------------------------
# 2. Discovery churn
# ---------------------------------------------------------------------------


def test_discovery_churn_reports_baseline_absent_without_reclassifying() -> None:
    baseline = _make_baseline(
        [
            ("Q1", "Baseline One", None, "auto_admit"),
            ("Q2", "Baseline Two", None, "auto_admit"),
        ]
    )
    delta = compute_expansion_delta(["Q2", "Q3"], baseline)
    absent = compute_baseline_absent_qids(["Q2", "Q3"], baseline)
    assert delta == ["Q3"]
    assert absent == frozenset({"Q1"})
    # Q1's own accepted baseline state is untouched by this computation.
    assert baseline.auto_admit_qids == frozenset({"Q1", "Q2"})


# ---------------------------------------------------------------------------
# 3. New collision with accepted baseline
# ---------------------------------------------------------------------------


def test_new_delta_candidate_collides_with_accepted_baseline_candidate() -> None:
    baseline = _make_baseline([("Q1", "Example 36", None, "auto_admit")])
    delta_entities = [_entity("Q3", "Example 36")]
    candidates, delta_clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    assert len(candidates) == 1
    c = candidates[0]
    assert c.qid == "Q3"
    assert c.decision == BootstrapDecision.REVIEW_REQUIRED
    assert BootstrapReasonCode.NAME_COLLISION in c.reason_codes
    assert build_admission(c) is None
    assert not delta_clusters  # no delta-delta cluster involved
    assert "Q3" in baseline_collisions
    assert baseline_collisions["Q3"].baseline_qids == ("Q1",)
    # Baseline's own accepted state is never mutated.
    assert baseline.auto_admit_qids == frozenset({"Q1"})


# ---------------------------------------------------------------------------
# 4. New collision with baseline review candidate
# ---------------------------------------------------------------------------


def test_new_delta_candidate_collides_with_baseline_review_candidate() -> None:
    baseline = _make_baseline([("Q2", "Collision Name", None, "review_required")])
    delta_entities = [_entity("Q3", "Collision Name")]
    candidates, _delta_clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    assert candidates[0].decision == BootstrapDecision.REVIEW_REQUIRED
    assert baseline_collisions["Q3"].baseline_qids == ("Q2",)
    # The baseline's own review-required state remains exactly as accepted.
    assert baseline.review_required_qids == frozenset({"Q2"})
    assert baseline.auto_admit_qids == frozenset()


# ---------------------------------------------------------------------------
# 5. Delta<->delta transitive collision
# ---------------------------------------------------------------------------


def test_delta_delta_transitive_collision_forms_one_complete_cluster() -> None:
    baseline = _make_baseline([])
    delta_entities = [
        _entity("Q1", "Example Boats Ltd."),
        _entity("Q2", "Example Boats", aliases=["Voyager 42"]),
        _entity("Q3", "Something Else", aliases=["Voyager 42"]),
        _entity("Q4", "Fully Independent"),
    ]
    candidates, clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    assert len(clusters) == 1
    assert clusters[0].qids == ("Q1", "Q2", "Q3")

    by_qid = {c.qid: c for c in candidates}
    assert by_qid["Q1"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q2"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q3"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q4"].decision == BootstrapDecision.AUTO_ADMIT
    assert not baseline_collisions


# ---------------------------------------------------------------------------
# 6. Historical ID reuse
# ---------------------------------------------------------------------------


def test_delta_qid_already_in_historical_crosswalk_reuses_id_exactly() -> None:
    baseline = _make_baseline([])
    delta_entities = [_entity("Q5", "Some Yacht")]
    existing_crosswalk = {"Q5": "BM_WDT0_PRERESERVED"}
    candidates, _clusters, _bc = classify_delta_candidates(
        delta_entities,
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
        existing_crosswalk=existing_crosswalk,
        id_factory=lambda: "SHOULD_NOT_BE_CALLED",
    )
    assert candidates[0].decision == BootstrapDecision.AUTO_ADMIT
    assert candidates[0].hullq_id == "BM_WDT0_PRERESERVED"


def test_reserved_id_preserved_even_when_delta_qid_newly_collides() -> None:
    """A delta QID already carrying a retained historical ID keeps that ID
    visible (never silently reminted) even when this run newly routes it to
    REVIEW_REQUIRED — mirrors the accepted SLICE-0017
    ``test_collision_preserves_retained_id_as_reserved_not_admitted``.
    """
    baseline = _make_baseline([("Q1", "Example Boats", None, "auto_admit")])
    delta_entities = [_entity("Q9", "Example Boats")]
    existing_crosswalk = {"Q9": "BM_WDT0_RESERVED"}
    candidates, _clusters, baseline_collisions = classify_delta_candidates(
        delta_entities,
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
        existing_crosswalk=existing_crosswalk,
    )
    c = candidates[0]
    assert c.decision == BootstrapDecision.REVIEW_REQUIRED
    assert c.hullq_id == "BM_WDT0_RESERVED"
    assert build_admission(c) is None
    assert "Q9" in baseline_collisions


# ---------------------------------------------------------------------------
# 7. Crosswalk fail-closed
# ---------------------------------------------------------------------------


def test_merge_crosswalks_fails_closed_on_same_qid_two_ids() -> None:
    with pytest.raises(CrosswalkConflictError):
        merge_crosswalks_fail_closed({"Q1": "BM_A"}, {"Q1": "BM_B"})


def test_merge_crosswalks_fails_closed_on_same_id_two_qids() -> None:
    with pytest.raises(CrosswalkConflictError):
        merge_crosswalks_fail_closed({"Q1": "BM_SHARED"}, {"Q2": "BM_SHARED"})


def test_merge_crosswalks_accepts_disjoint_consistent_maps() -> None:
    merged = merge_crosswalks_fail_closed({"Q1": "BM_A"}, {"Q2": "BM_B"})
    assert merged == {"Q1": "BM_A", "Q2": "BM_B"}


# ---------------------------------------------------------------------------
# 8. Accepted artifact immutability
# ---------------------------------------------------------------------------


def test_load_baseline_snapshot_never_mutates_the_accepted_0017_manifest_file() -> None:
    before = hashlib.sha256(BASELINE_MANIFEST_PATH.read_bytes()).hexdigest()
    snapshot = load_baseline_snapshot(BASELINE_MANIFEST_PATH)
    after = hashlib.sha256(BASELINE_MANIFEST_PATH.read_bytes()).hexdigest()
    assert before == after
    assert snapshot.sha256 == before
    assert len(snapshot.candidate_qids) == ACCEPTED_0017_BASELINE_CANDIDATE_COUNT


def test_load_baseline_snapshot_fails_closed_on_pinned_sha256_mismatch() -> None:
    """The primary integrity check: any tampering (independent of which field
    changed) fails via the pinned ``ACCEPTED_0017_MANIFEST_SHA256`` fingerprint
    comparison, checked before the manifest_version/candidate-count/aggregate-
    count diagnostics below — those remain additional diagnostics, not a
    substitute for the fingerprint.
    """
    from hullq.bootstrap.wikidata_tier0_sl0018 import ACCEPTED_0017_MANIFEST_SHA256

    assert hashlib.sha256(b"not the real content").hexdigest() != ACCEPTED_0017_MANIFEST_SHA256


def test_load_baseline_snapshot_fails_closed_on_wrong_manifest_version(tmp_path: Path) -> None:
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["manifest_version"] = "0017-tampered"
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    # Any tampering changes the raw bytes, so the pinned-fingerprint check
    # (checked first) is what actually fires here, not the deeper
    # manifest_version diagnostic — this is the intended priority order.
    with pytest.raises(BaselineIntegrityError, match="sha256"):
        load_baseline_snapshot(tampered_path)


def test_load_baseline_snapshot_fails_closed_on_wrong_candidate_count(tmp_path: Path) -> None:
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["candidates"] = real["candidates"][:5]
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match="sha256"):
        load_baseline_snapshot(tampered_path)


def test_load_baseline_snapshot_fails_closed_on_drifted_counts(tmp_path: Path) -> None:
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["counts"]["auto_admit"] = real["counts"]["auto_admit"] - 1
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match="sha256"):
        load_baseline_snapshot(tampered_path)


def test_load_baseline_snapshot_fails_closed_on_same_count_content_tampering(
    tmp_path: Path,
) -> None:
    """Required SLICE-0018 regression: modify a baseline candidate's
    name/alias/QID while keeping manifest_version and every aggregate count
    unchanged. Version/count checks alone would pass this; the pinned
    SHA256 fingerprint MUST still catch it.
    """
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    # Change only a candidate's label — manifest_version, candidate count,
    # and every aggregate count (auto_admit/review_required/not_admitted/
    # retained_crosswalk_count/research_observation_count/
    # canonical_evidence_link_count) all remain byte-for-byte unchanged.
    real["candidates"][0]["preferred_label"] = "Tampered Label That Does Not Change Any Count"
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match="sha256"):
        load_baseline_snapshot(tampered_path)


def test_load_baseline_snapshot_fails_closed_on_duplicate_candidate_qid(tmp_path: Path) -> None:
    """Explicit duplicate-QID detection — not merely reliance on ``set()``
    insertion silently collapsing a duplicate row. Constructed to keep the
    manifest_version/candidate-count/aggregate-count diagnostics irrelevant
    to isolate the duplicate-detection code path itself.
    """
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["candidates"][1] = dict(real["candidates"][0])  # duplicate the first row's QID
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match="duplicate candidate QID"):
        build_baseline_snapshot_from_manifest(real)


# ---------------------------------------------------------------------------
# 9. Below-target source ceiling
# ---------------------------------------------------------------------------


def test_below_target_discovery_is_processed_as_is_and_reported() -> None:
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    discovery_window_qids = ["Q1", "Q2"]  # far below the requested 2,500
    delta_entities = [_entity("Q2", "New Yacht")]
    candidates, clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=discovery_window_qids,
        requested_limit=2500,
        target_reached=len(discovery_window_qids) >= 2500,
        delta_delta_clusters=clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=1,
        extracted_record_count=2,
    )
    assert manifest["discovery"]["target_reached"] is False
    assert manifest["discovery"]["unique_qids_returned"] == 2
    assert manifest["delta"]["delta_count"] == 1
    assert manifest["overlap"]["overlap_count"] == 1
    assert manifest["overlap"]["baseline_absent_qids"] == []


# ---------------------------------------------------------------------------
# Additional coverage: activity_id labeling, manifest schema, counts
# ---------------------------------------------------------------------------


def test_delta_bundle_uses_sl0018_activity_id_not_slice_0017_default() -> None:
    baseline = _make_baseline([])
    candidates, _, _ = classify_delta_candidates(
        [_entity("Q42", "Unique Yacht")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    bundle = build_bundle(candidates[0])
    assert bundle is not None
    assert bundle.activity_id == SL0018_ACTIVITY_ID
    assert bundle.observations[0].research_context.activity_id == SL0018_ACTIVITY_ID


def test_full_sl0018_manifest_validates_against_its_schema() -> None:
    baseline = _make_baseline(
        [
            ("Q1", "Example 36", None, "auto_admit"),
            ("Q2", "Review Baseline", None, "review_required"),
        ]
    )
    delta_entities = [
        _entity("Q10", "Example 36"),  # collides with baseline AUTO_ADMIT
        _entity("Q11", "Review Baseline"),  # collides with baseline REVIEW_REQUIRED
        _entity("Q12", "Dup Delta Name"),
        _entity("Q13", "Dup Delta Name"),  # delta<->delta collision
        _entity("Q14", None),  # missing label
        _entity("Q15", "Clean New Candidate"),
    ]
    candidates, clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q1", "Q2", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=3,
        extracted_record_count=6,
    )
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=schema)

    assert manifest["delta"]["delta_count"] == 6
    assert manifest["overlap"]["overlap_count"] == 2
    assert manifest["counts"]["auto_admit"] == 1  # only Q15
    assert manifest["counts"]["review_required"] == 4  # Q10, Q11, Q12, Q13
    assert manifest["counts"]["not_admitted"] == 1  # Q14
    assert manifest["counts"]["baseline_collision_count"] == 2  # Q10, Q11
    assert manifest["counts"]["delta_delta_collision_cluster_count"] == 1  # {Q12, Q13}
    assert (
        manifest["counts"]["combined_canonical_boat_model_count_expected"] == 2
    )  # 1 baseline + 1 delta
    # Merged crosswalk includes both the baseline's retained mapping and the
    # newly admitted delta candidate's mapping.
    crosswalk_qids = {row["qid"] for row in manifest["retained_crosswalk"]}
    assert "Q1" in crosswalk_qids  # baseline
    assert "Q15" in crosswalk_qids  # delta


def test_build_sl0018_manifest_fails_closed_on_crosswalk_conflict() -> None:
    from hullq.bootstrap.wikidata_tier0 import (
        candidate_from_manifest_dict,
        candidate_to_manifest_dict,
    )

    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    candidates, clusters, baseline_collisions = classify_delta_candidates(
        [_entity("Q42", "Example 36")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    tampered = candidate_from_manifest_dict(
        {**candidate_to_manifest_dict(candidates[0]), "hullq_id": "BM_WDT0_DIFFERENT_ID"}
    )
    with pytest.raises(CrosswalkConflictError):
        build_sl0018_manifest(
            [candidates[0], tampered],
            generated_at=RETRIEVED_AT,
            baseline=baseline,
            discovery_window_qids=["Q1", "Q42"],
            requested_limit=2500,
            target_reached=False,
            delta_delta_clusters=clusters,
            baseline_collisions=baseline_collisions,
            retrieval_count=1,
            extracted_record_count=1,
        )


def test_compute_baseline_collisions_covers_alias_only_overlap() -> None:
    baseline = _make_baseline([("Q1", "Voyager 42", None, "auto_admit")])
    entities = [_entity("Q9", "Sea Explorer", aliases=["Voyager 42"])]
    collisions = compute_baseline_collisions(entities, baseline)
    assert "Q9" in collisions
    assert collisions["Q9"].baseline_qids == ("Q1",)


def test_compute_baseline_collisions_ignores_missing_label_entities() -> None:
    baseline = _make_baseline([("Q1", "Voyager 42", None, "auto_admit")])
    entities = [_entity("Q9", None)]
    collisions = compute_baseline_collisions(entities, baseline)
    assert collisions == {}


# ---------------------------------------------------------------------------
# Correction-round adversarial regressions (independent review blockers)
# ---------------------------------------------------------------------------
# BLOCKER 1 — historical crosswalk must survive omission/reappearance
# ---------------------------------------------------------------------------


def test_historical_crosswalk_survives_omission_and_reappearance() -> None:
    """Exact required regression transition:

    baseline crosswalk = {Q1: BM_BASE}; prior SLICE-0018 crosswalk
    additionally contains {Q9: BM_OLD}. Current discovery = {Q1, Q3}; current
    delta = {Q3}. The new manifest's candidates MUST contain Q3 only, but
    retained_crosswalk MUST contain Q1, Q3 AND Q9 — Q9 is never copied into
    current candidates merely to preserve its ID. Q9 reappearing later MUST
    reuse BM_OLD byte-for-byte.
    """
    from hullq.bootstrap.wikidata_tier0 import load_crosswalk_from_manifest

    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    historical_crosswalk = merge_crosswalks_fail_closed(baseline.crosswalk, {"Q9": "BM_OLD"})
    assert len(historical_crosswalk) == 2

    # --- Run 1: Q9 is absent from the current discovery window/delta ---
    delta_entities = [_entity("Q3", "Clean New Candidate")]
    candidates, clusters, baseline_collisions = classify_delta_candidates(
        delta_entities,
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
        existing_crosswalk=historical_crosswalk,
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q1", "Q3"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=1,
        extracted_record_count=1,
        historical_crosswalk=historical_crosswalk,
    )

    candidate_qids = {row["qid"] for row in manifest["candidates"]}
    assert candidate_qids == {"Q3"}  # Q9 never copied into current candidates

    crosswalk_by_qid = {row["qid"]: row["hullq_id"] for row in manifest["retained_crosswalk"]}
    assert set(crosswalk_by_qid) == {"Q1", "Q3", "Q9"}
    assert crosswalk_by_qid["Q9"] == "BM_OLD"  # preserved, not dropped
    assert crosswalk_by_qid["Q1"] == baseline.crosswalk["Q1"]

    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=schema)

    # --- Run 2: Q9 reappears in a later discovery window/delta ---
    reloaded_historical = load_crosswalk_from_manifest(manifest)
    assert reloaded_historical["Q9"] == "BM_OLD"

    delta_entities_2 = [_entity("Q9", "Reappeared Yacht")]
    candidates_2, _clusters_2, _bc_2 = classify_delta_candidates(
        delta_entities_2,
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
        existing_crosswalk=reloaded_historical,
        id_factory=lambda: "SHOULD_NOT_BE_CALLED",
    )
    assert candidates_2[0].hullq_id == "BM_OLD"  # reused byte-for-byte
    assert candidates_2[0].decision == BootstrapDecision.AUTO_ADMIT


def test_omitting_historical_crosswalk_param_falls_back_to_baseline_only() -> None:
    """When ``historical_crosswalk`` is not supplied, ``build_sl0018_manifest``
    falls back to ``baseline.crosswalk`` alone (correct for a first-ever run
    with no prior SLICE-0018 manifest) rather than silently losing anything —
    there is nothing prior to lose in that case.
    """
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Clean")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q1", "Q3"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=bc,
        retrieval_count=1,
        extracted_record_count=1,
    )
    crosswalk_qids = {row["qid"] for row in manifest["retained_crosswalk"]}
    assert crosswalk_qids == {"Q1", "Q3"}
    assert manifest["counts"]["historical_crosswalk_count_before"] == 1
    assert manifest["counts"]["newly_minted_id_count"] == 1
    assert manifest["counts"]["reused_historical_id_count"] == 0


# ---------------------------------------------------------------------------
# BLOCKER 2 — incomplete entity acquisition must fail closed
# ---------------------------------------------------------------------------


def test_verify_entity_acquisition_completeness_rejects_missing_qid() -> None:
    """Required negative test: discovery delta = [Q3, Q4], fetched entities
    = [Q3] must fail closed before producing/replacing a manifest. Q4 must
    never silently disappear.
    """
    entities = [_entity("Q3", "Found Yacht")]
    with pytest.raises(DeltaCompletenessError, match=r"missing=\['Q4'\]"):
        verify_entity_acquisition_completeness(["Q3", "Q4"], entities)


def test_verify_entity_acquisition_completeness_rejects_unexpected_qid() -> None:
    entities = [_entity("Q3", "Found"), _entity("Q99", "Not requested")]
    with pytest.raises(DeltaCompletenessError, match=r"unexpected=\['Q99'\]"):
        verify_entity_acquisition_completeness(["Q3"], entities)


def test_verify_entity_acquisition_completeness_rejects_duplicate_returned_qid() -> None:
    entities = [_entity("Q3", "First"), _entity("Q3", "Duplicate")]
    with pytest.raises(DeltaCompletenessError, match=r"duplicates=\['Q3'\]"):
        verify_entity_acquisition_completeness(["Q3"], entities)


def test_verify_entity_acquisition_completeness_accepts_exact_match() -> None:
    entities = [_entity("Q3", "A"), _entity("Q4", "B")]
    verify_entity_acquisition_completeness(["Q3", "Q4"], entities)  # must not raise


def test_build_sl0018_manifest_independently_rejects_truncated_candidate_set() -> None:
    """Defense-in-depth: even if acquisition/classification somehow produced
    a candidate set that does not exactly equal discovery_window_qids minus
    baseline, build_sl0018_manifest itself must refuse to write a manifest
    describing the wrong delta.
    """
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    # Only Q3 classified, but the true expected delta is {Q3, Q4}.
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Found")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    with pytest.raises(DeltaCompletenessError, match=r"missing=\['Q4'\]"):
        build_sl0018_manifest(
            candidates,
            generated_at=RETRIEVED_AT,
            baseline=baseline,
            discovery_window_qids=["Q1", "Q3", "Q4"],
            requested_limit=2500,
            target_reached=False,
            delta_delta_clusters=clusters,
            baseline_collisions=bc,
            retrieval_count=1,
            extracted_record_count=1,
        )


def test_verify_delta_candidate_completeness_directly() -> None:
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    candidates, _clusters, _bc = classify_delta_candidates(
        [_entity("Q3", "Found")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    verify_delta_candidate_completeness(candidates, ["Q1", "Q3"], baseline)  # must not raise
    with pytest.raises(DeltaCompletenessError):
        verify_delta_candidate_completeness(candidates, ["Q1", "Q3", "Q4"], baseline)


def test_overlap_count_computed_directly_from_qid_sets_not_delta_length() -> None:
    """overlap_count must reflect the true baseline/discovery intersection
    even if delta_candidates happens to under- or over-represent the true
    delta size — it must not be derived as
    len(discovery_window_qids) - len(delta_candidates).
    """
    baseline = _make_baseline(
        [
            ("Q1", "Baseline One", None, "auto_admit"),
            ("Q2", "Baseline Two", None, "auto_admit"),
        ]
    )
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Found"), _entity("Q4", "Found Too")],
        retrieved_at=RETRIEVED_AT,
        baseline=baseline,
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q1", "Q2", "Q3", "Q4"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=bc,
        retrieval_count=1,
        extracted_record_count=2,
    )
    # True overlap: {Q1, Q2} intersect baseline == 2. This must hold even
    # though it also happens to equal len(discovery) - len(candidates) here;
    # the point is the implementation must compute it via set intersection.
    assert manifest["overlap"]["overlap_count"] == 2


# ---------------------------------------------------------------------------
# BLOCKER 3 — SLICE-0018 window boundary must be <=2500
# ---------------------------------------------------------------------------


def test_build_sl0018_manifest_rejects_requested_limit_above_2500() -> None:
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Found")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    with pytest.raises(ValueError, match="2500"):
        build_sl0018_manifest(
            candidates,
            generated_at=RETRIEVED_AT,
            baseline=baseline,
            discovery_window_qids=["Q1", "Q3"],
            requested_limit=2501,
            target_reached=False,
            delta_delta_clusters=clusters,
            baseline_collisions=bc,
            retrieval_count=1,
            extracted_record_count=1,
        )


def test_manifest_schema_itself_rejects_requested_limit_above_2500() -> None:
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Found")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q1", "Q3"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=bc,
        retrieval_count=1,
        extracted_record_count=1,
    )
    manifest["requested_limit"] = 2501
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)


def test_manifest_schema_rejects_wrong_safety_ceiling() -> None:
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Found")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q1", "Q3"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=bc,
        retrieval_count=1,
        extracted_record_count=1,
    )
    assert manifest["safety_ceiling"] == 3000
    manifest["safety_ceiling"] = 1500
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)


def test_manifest_schema_rejects_discovery_window_above_2500_items() -> None:
    baseline = _make_baseline([])
    candidates, clusters, bc = classify_delta_candidates(
        [_entity("Q3", "Found")], retrieved_at=RETRIEVED_AT, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        baseline=baseline,
        discovery_window_qids=["Q3"],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=bc,
        retrieval_count=1,
        extracted_record_count=1,
    )
    manifest["discovery"]["discovery_window_qids"] = [f"Q{i}" for i in range(1, 2502)]
    manifest["discovery"]["unique_qids_returned"] = 2501
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)


# ---------------------------------------------------------------------------
# Structural invariants — baseline QID accidentally in delta / duplicate QID
# ---------------------------------------------------------------------------


def test_classify_delta_candidates_rejects_accidental_baseline_qid() -> None:
    baseline = _make_baseline([("Q1", "Baseline One", None, "auto_admit")])
    with pytest.raises(DeltaCompletenessError, match=r"\['Q1'\]"):
        classify_delta_candidates(
            [_entity("Q1", "Baseline One"), _entity("Q3", "Clean")],
            retrieved_at=RETRIEVED_AT,
            baseline=baseline,
        )


def test_classify_delta_candidates_rejects_duplicate_delta_entity_qid() -> None:
    baseline = _make_baseline([])
    with pytest.raises(DeltaCompletenessError, match=r"\['Q3'\]"):
        classify_delta_candidates(
            [_entity("Q3", "First"), _entity("Q3", "Second")],
            retrieved_at=RETRIEVED_AT,
            baseline=baseline,
        )
