"""Unit tests for hullq.bootstrap.wikidata_tier0 — SLICE-0017.

All tests are offline, deterministic and database-free.

Covers SLICE-0017 required test scenarios 7-19 (persistence-independent subset):
  7.  empty/missing source label cannot auto-admit a BoatModel.
  8.  unique safe candidate produces a schema-valid sparse BoatModel.
  9.  manufacturer P176 does not auto-create Brand/Organization or a Brand relationship.
  10. QID existence alone does not auto-create BoatDesign.
  11. accepted exact source alias remains entity-scoped and does not mutate source spelling.
  12. deterministic same-name/search-projection collision routes candidates to review.
  13. newly minted HullQ ID is opaque and does not encode name/QID.
  14. retained QID mapping is reused exactly on replay.
  15. conflicting retained QID mapping fails closed.
  16. every auto-admitted BoatModel has supporting retained observation/evidence linkage.
  17. ReferenceCrosscheck cannot satisfy admission provenance (structural — no such path exists).
  18. review-required candidate is absent from canonical tables (no admission is built for it).
  19. full retained bootstrap manifest validates against its versioned contract/validator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from hullq.bootstrap.wikidata_tier0 import (
    BootstrapDecision,
    BootstrapReasonCode,
    CrosswalkConflictError,
    build_admission,
    build_bundle,
    build_manifest,
    candidate_from_manifest_dict,
    candidate_to_manifest_dict,
    classify_candidates,
    mint_hullq_id,
    validate_crosswalk_consistency,
)
from hullq.sources.wikidata import WikidataEntityData

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SCHEMA_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "manifest_schema.json"

RETRIEVED_AT = "2026-08-21T00:00:00Z"


def _entity(qid: str, label: str | None, aliases: list[str] | None = None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=aliases or [], raw_claims={})


# ---------------------------------------------------------------------------
# 7. missing label cannot auto-admit
# ---------------------------------------------------------------------------


def test_missing_label_routes_to_not_admitted_with_no_observation() -> None:
    candidates = classify_candidates([_entity("Q1", None)], retrieved_at=RETRIEVED_AT)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.decision == BootstrapDecision.NOT_ADMITTED
    assert BootstrapReasonCode.MISSING_LABEL in c.reason_codes
    assert c.hullq_id is None
    assert c.observation_id is None
    assert build_bundle(c) is None
    assert build_admission(c) is None


def test_empty_string_label_is_treated_as_missing() -> None:
    candidates = classify_candidates([_entity("Q1", "")], retrieved_at=RETRIEVED_AT)
    assert candidates[0].decision == BootstrapDecision.NOT_ADMITTED


# ---------------------------------------------------------------------------
# 8. unique safe candidate produces a schema-valid sparse BoatModel
# ---------------------------------------------------------------------------


def test_unique_candidate_auto_admits_with_sparse_boat_model(registry_validator: Any) -> None:
    candidates = classify_candidates([_entity("Q42", "Example 36")], retrieved_at=RETRIEVED_AT)
    c = candidates[0]
    assert c.decision == BootstrapDecision.AUTO_ADMIT
    admission = build_admission(c)
    assert admission is not None
    assert len(admission.boat_models) == 1
    payload = admission.boat_models[0]
    registry_validator(payload)
    assert payload["canonical_name"] == "Example 36"
    assert payload["first_built"] is None
    assert payload["last_built"] is None


@pytest.fixture
def registry_validator() -> Any:
    from hullq.contracts import ContractRegistry

    specs_dir = ROOT / "specs"
    registry = ContractRegistry.from_directory(specs_dir)
    validator = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")

    def _validate(payload: dict[str, Any]) -> None:
        validator.validate(dict(payload))

    return _validate


# ---------------------------------------------------------------------------
# 9 / 10. no Brand/Organization/BoatDesign auto-creation
# ---------------------------------------------------------------------------


def test_admission_never_populates_brand_relationships_or_boat_designs() -> None:
    candidates = classify_candidates([_entity("Q42", "Example 36")], retrieved_at=RETRIEVED_AT)
    admission = build_admission(candidates[0])
    assert admission is not None
    payload = admission.boat_models[0]
    assert payload["brand_relationships"] == []
    assert payload["boat_design_ids"] == []
    assert admission.boat_designs == ()
    assert admission.brands == ()
    assert admission.organizations == ()


# ---------------------------------------------------------------------------
# 11. accepted exact source alias remains entity-scoped, unmutated
# ---------------------------------------------------------------------------


def test_wikidata_aliases_preserved_unmutated_as_source_spelling() -> None:
    candidates = classify_candidates(
        [_entity("Q42", "Example 36", aliases=["Example XXXVI", "  Example 36  "])],
        retrieved_at=RETRIEVED_AT,
    )
    admission = build_admission(candidates[0])
    assert admission is not None
    payload = admission.boat_models[0]
    names = [a["name"] for a in payload["aliases"]]
    assert names == ["Example XXXVI", "  Example 36  "]  # unmutated, including whitespace
    assert all(a["alias_class"] == "source_spelling" for a in payload["aliases"])
    # Alias IDs are stable/unique within the entity scope.
    ids = [a["id"] for a in payload["aliases"]]
    assert len(ids) == len(set(ids))


def test_alias_identity_does_not_depend_on_array_position() -> None:
    """IDENTITY_MODEL.v0.2 §4: persistent provenance MUST NOT depend on
    fragile array position. Reordering the same alias set MUST NOT change
    the ID assigned to any individual alias.
    """
    forward = classify_candidates(
        [_entity("Q42", "Example 36", aliases=["Alpha Alias", "Beta Alias", "Gamma Alias"])],
        retrieved_at=RETRIEVED_AT,
    )
    reversed_order = classify_candidates(
        [_entity("Q42", "Example 36", aliases=["Gamma Alias", "Beta Alias", "Alpha Alias"])],
        retrieved_at=RETRIEVED_AT,
    )

    forward_by_name = {
        a["name"]: a["id"]
        for a in build_admission(forward[0]).boat_models[0]["aliases"]  # type: ignore[union-attr]
    }
    reversed_by_name = {
        a["name"]: a["id"]
        for a in build_admission(reversed_order[0]).boat_models[0]["aliases"]  # type: ignore[union-attr]
    }
    assert forward_by_name == reversed_by_name
    assert forward_by_name["Alpha Alias"] != forward_by_name["Beta Alias"]


# ---------------------------------------------------------------------------
# 12. deterministic same-name collision routes to review, not forced merge
# ---------------------------------------------------------------------------


def test_same_name_collision_routes_both_candidates_to_review() -> None:
    entities = [
        _entity("Q1", "Example 36"),
        _entity("Q2", "  example   36 "),  # case/whitespace-insensitive collision
        _entity("Q3", "Different 40"),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    by_qid = {c.qid: c for c in candidates}

    assert by_qid["Q1"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert BootstrapReasonCode.NAME_COLLISION in by_qid["Q1"].reason_codes
    assert by_qid["Q2"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q1"].hullq_id is None
    assert by_qid["Q2"].hullq_id is None

    assert by_qid["Q3"].decision == BootstrapDecision.AUTO_ADMIT

    # Neither colliding candidate is admittable.
    assert build_admission(by_qid["Q1"]) is None
    assert build_admission(by_qid["Q2"]) is None

    # But each still retains an auditable observation + review finding.
    bundle_q1 = build_bundle(by_qid["Q1"])
    assert bundle_q1 is not None
    assert len(bundle_q1.observations) == 1
    assert len(bundle_q1.unresolved_findings) == 1


def test_collision_reuses_accepted_generate_search_keys_projection() -> None:
    """Collision detection must use the single accepted HullQ deterministic
    search-key projection (hullq.domain.identity.generate_search_keys), not a
    weaker parallel normalization — proven here via a projection behavior
    (accepted corporate-suffix stripping) that a bare casefold/whitespace
    normalizer would not detect.
    """
    entities = [
        _entity("Q1", "Example Boats Ltd."),
        _entity("Q2", "Example Boats"),  # collides only via suffix-stripped key
        _entity("Q3", "Completely Different"),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    by_qid = {c.qid: c for c in candidates}

    assert by_qid["Q1"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q2"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q3"].decision == BootstrapDecision.AUTO_ADMIT


def test_collision_created_only_through_an_alias() -> None:
    """A collision may arise purely from one candidate's alias matching
    another candidate's canonical label (or another candidate's alias) —
    the full accepted search-key projection covers both label and aliases.
    """
    entities = [
        _entity("Q1", "Voyager 42"),
        _entity("Q2", "Sea Explorer", aliases=["Voyager 42"]),  # alias-only collision
        _entity("Q3", "Unrelated Yacht"),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    by_qid = {c.qid: c for c in candidates}

    assert by_qid["Q1"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q2"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q3"].decision == BootstrapDecision.AUTO_ADMIT


def test_canonical_name_collision_is_reported_as_a_complete_cluster() -> None:
    from hullq.bootstrap.wikidata_tier0 import compute_collision_clusters

    entities = [
        _entity("Q1", "Example 36"),
        _entity("Q2", "Example 36"),
        _entity("Q3", "Different 40"),
    ]
    clusters = compute_collision_clusters(entities)
    assert len(clusters) == 1
    assert clusters[0].qids == ("Q1", "Q2")
    assert len(clusters[0].shared_keys) >= 1


def test_transitive_collision_forms_one_complete_cluster() -> None:
    """A shares a key with B via one path, B shares a different key with C:
    all three must form one complete cluster, not two separate pairs.
    """
    from hullq.bootstrap.wikidata_tier0 import compute_collision_clusters

    entities = [
        _entity("Q1", "Example Boats Ltd."),
        _entity("Q2", "Example Boats", aliases=["Voyager 42"]),
        _entity("Q3", "Something Else", aliases=["Voyager 42"]),
        _entity("Q4", "Fully Independent"),
    ]
    clusters = compute_collision_clusters(entities)
    assert len(clusters) == 1
    assert clusters[0].qids == ("Q1", "Q2", "Q3")

    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    by_qid = {c.qid: c for c in candidates}
    assert by_qid["Q1"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q2"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q3"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q4"].decision == BootstrapDecision.AUTO_ADMIT


def test_distinct_non_colliding_candidates_remain_auto_admit() -> None:
    entities = [
        _entity("Q1", "Alpha 30"),
        _entity("Q2", "Beta 34", aliases=["Beta Thirty-Four"]),
        _entity("Q3", "Gamma 38"),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    assert all(c.decision == BootstrapDecision.AUTO_ADMIT for c in candidates)
    assert len({c.hullq_id for c in candidates}) == 3


def test_collision_preserves_retained_id_as_reserved_not_admitted() -> None:
    """A QID that was previously admitted with a retained ID, but is now
    newly caught by broader collision detection, must keep its historical ID
    visible (never silently reminted) while building no admission for it.
    """
    entities = [_entity("Q1", "Example Boats Ltd."), _entity("Q2", "Example Boats")]
    crosswalk = {"Q1": "BM_WDT0_PRESERVED_HISTORICAL_ID"}
    candidates = classify_candidates(
        entities, retrieved_at=RETRIEVED_AT, existing_crosswalk=crosswalk
    )
    by_qid = {c.qid: c for c in candidates}
    assert by_qid["Q1"].decision == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q1"].hullq_id == "BM_WDT0_PRESERVED_HISTORICAL_ID"
    assert build_admission(by_qid["Q1"]) is None


# ---------------------------------------------------------------------------
# 13. newly minted HullQ ID is opaque
# ---------------------------------------------------------------------------


def test_minted_id_does_not_encode_qid_or_name() -> None:
    entities = [_entity("Q987654", "Very Distinctive Yacht Name")]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    hullq_id = candidates[0].hullq_id
    assert hullq_id is not None
    assert "Q987654" not in hullq_id
    assert "distinctive" not in hullq_id.lower()
    assert "yacht" not in hullq_id.lower()


def test_mint_hullq_id_produces_distinct_opaque_ids() -> None:
    a, b = mint_hullq_id(), mint_hullq_id()
    assert a != b
    assert a.startswith("BM_")


# ---------------------------------------------------------------------------
# 14. retained QID mapping is reused exactly on replay
# ---------------------------------------------------------------------------


def test_existing_crosswalk_id_is_reused_not_reminted() -> None:
    entities = [_entity("Q42", "Example 36")]
    first_pass = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    original_id = first_pass[0].hullq_id
    assert original_id is not None

    crosswalk = {"Q42": original_id}
    second_pass = classify_candidates(
        entities,
        retrieved_at=RETRIEVED_AT,
        existing_crosswalk=crosswalk,
        id_factory=lambda: "SHOULD_NOT_BE_CALLED",
    )
    assert second_pass[0].hullq_id == original_id


def test_manifest_round_trip_preserves_hullq_id_exactly() -> None:
    candidates = classify_candidates([_entity("Q42", "Example 36")], retrieved_at=RETRIEVED_AT)
    row = candidate_to_manifest_dict(candidates[0])
    reconstructed = candidate_from_manifest_dict(row)
    assert reconstructed.hullq_id == candidates[0].hullq_id
    assert reconstructed == candidates[0]


# ---------------------------------------------------------------------------
# 15. conflicting retained QID mapping fails closed
# ---------------------------------------------------------------------------


def test_conflicting_qid_to_id_mapping_fails_closed() -> None:
    entities = [_entity("Q42", "Example 36")]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    good = candidates[0]
    tampered = candidate_from_manifest_dict(
        {**candidate_to_manifest_dict(good), "hullq_id": "BM_WDT0_DIFFERENT_ID"}
    )
    with pytest.raises(CrosswalkConflictError):
        validate_crosswalk_consistency([good, tampered])


def test_two_qids_sharing_one_hullq_id_fails_closed() -> None:
    entities = [_entity("Q1", "Boat One"), _entity("Q2", "Boat Two")]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    a, b = candidates
    collided = candidate_from_manifest_dict(
        {**candidate_to_manifest_dict(b), "hullq_id": a.hullq_id}
    )
    with pytest.raises(CrosswalkConflictError):
        validate_crosswalk_consistency([a, collided])


def test_build_manifest_raises_on_crosswalk_conflict() -> None:
    entities = [_entity("Q42", "Example 36")]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    tampered = candidate_from_manifest_dict(
        {**candidate_to_manifest_dict(candidates[0]), "hullq_id": "BM_WDT0_DIFFERENT_ID"}
    )
    with pytest.raises(CrosswalkConflictError):
        build_manifest(
            [candidates[0], tampered],
            generated_at=RETRIEVED_AT,
            requested_limit=1000,
            unique_qids_returned=1,
            retrieval_count=1,
            extracted_record_count=1,
            target_reached=False,
        )


# ---------------------------------------------------------------------------
# 16. every auto-admitted BoatModel has supporting observation/evidence linkage
# ---------------------------------------------------------------------------


def test_auto_admitted_boat_model_has_evidence_link_to_its_observation() -> None:
    candidates = classify_candidates([_entity("Q42", "Example 36")], retrieved_at=RETRIEVED_AT)
    c = candidates[0]
    bundle = build_bundle(c)
    admission = build_admission(c)
    assert bundle is not None
    assert admission is not None
    assert len(admission.evidence_links) == 1
    link = admission.evidence_links[0]
    assert link.entity_id == c.hullq_id
    assert link.observation_id == bundle.observations[0].observation_id
    assert link.evidence_id is None


# ---------------------------------------------------------------------------
# 18. review-required candidate never becomes an admission
# ---------------------------------------------------------------------------


def test_review_required_and_not_admitted_never_build_admission() -> None:
    entities = [_entity("Q1", "Dup"), _entity("Q2", "Dup"), _entity("Q3", None)]
    for c in classify_candidates(entities, retrieved_at=RETRIEVED_AT):
        assert c.decision != BootstrapDecision.AUTO_ADMIT
        assert build_admission(c) is None


# ---------------------------------------------------------------------------
# 19. full retained bootstrap manifest validates against its schema
# ---------------------------------------------------------------------------


def test_manifest_validates_against_schema() -> None:
    from hullq.bootstrap.wikidata_tier0 import compute_collision_clusters

    entities = [
        _entity("Q1", "Example 36", aliases=["Example XXXVI"]),
        _entity("Q2", None),
        _entity("Q3", "Dup Name"),
        _entity("Q4", "Dup Name"),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    clusters = compute_collision_clusters(entities)
    manifest = build_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        requested_limit=1000,
        unique_qids_returned=4,
        retrieval_count=2,
        extracted_record_count=4,
        target_reached=False,
        collision_clusters=clusters,
    )
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=schema)

    assert manifest["counts"]["auto_admit"] == 1
    assert manifest["counts"]["review_required"] == 2
    assert manifest["counts"]["not_admitted"] == 1
    assert manifest["counts"]["collision_cluster_count"] == 1
    assert manifest["collision_clusters"] == [{"qids": ["Q3", "Q4"], "shared_keys": ["dup name"]}]
