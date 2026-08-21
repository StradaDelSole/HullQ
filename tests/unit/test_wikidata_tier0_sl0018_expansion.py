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
    build_bundle,
    build_sl0018_manifest,
    classify_delta_candidates,
    compute_baseline_absent_qids,
    compute_baseline_collisions,
    compute_expansion_delta,
    load_baseline_snapshot,
    merge_crosswalks_fail_closed,
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


def test_load_baseline_snapshot_fails_closed_on_wrong_manifest_version(tmp_path: Path) -> None:
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["manifest_version"] = "0017-tampered"
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match="manifest_version"):
        load_baseline_snapshot(tampered_path)


def test_load_baseline_snapshot_fails_closed_on_wrong_candidate_count(tmp_path: Path) -> None:
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["candidates"] = real["candidates"][:5]
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match="candidate count"):
        load_baseline_snapshot(tampered_path)


def test_load_baseline_snapshot_fails_closed_on_drifted_counts(tmp_path: Path) -> None:
    real = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    real["counts"]["auto_admit"] = real["counts"]["auto_admit"] - 1
    tampered_path = tmp_path / "manifest.json"
    tampered_path.write_text(json.dumps(real), encoding="utf-8")
    with pytest.raises(BaselineIntegrityError, match=r"counts\.auto_admit"):
        load_baseline_snapshot(tampered_path)


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
