"""PostgreSQL 18 integration tests for the SLICE-0022 retained
alternative-route Tier-0 admission safety pilot.

Exercises the real combined prior-baseline (SLICE-0017 + SLICE-0018)
first / SLICE-0022 delta second offline replay path
(scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py) against
small synthetic manifests built through the same classification/
materialization logic used for the retained production manifests. The full
retained production manifests are replayed separately by the db-integration
CI job invoking the runner script directly against the real committed
``research/bootstrap/wikidata/manifest.json`` /
``research/bootstrap/wikidata/sl0018-2500/manifest.json`` /
``research/bootstrap/wikidata/sl0022-alt-route-admission/manifest.json``.

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).

Covers the SLICE-0022 required PostgreSQL replay scenario:
  baseline (0017+0018) import followed by SLICE-0022 delta import preserves
  the baseline graph and adds only the expected new BoatModels/evidence
  links, with every REVIEW_REQUIRED/NOT_ADMITTED SLICE-0022 candidate
  (including every R3 candidate) absent as a canonical row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (
    classify_sl0022_candidates,
    sl0022_candidate_to_manifest_dict,
)
from hullq.bootstrap.wikidata_tier0 import (
    build_manifest as build_baseline_manifest_0017,
)
from hullq.bootstrap.wikidata_tier0 import (
    classify_candidates,
)
from hullq.bootstrap.wikidata_tier0 import (
    compute_collision_clusters as compute_baseline_collision_clusters,
)
from hullq.bootstrap.wikidata_tier0_sl0018 import (
    build_baseline_snapshot_from_manifest,
    build_sl0018_manifest,
    classify_delta_candidates,
)
from hullq.sources.wikidata import WikidataEntityData

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

RETRIEVED_AT_0017 = "2026-08-20T00:00:00Z"
RETRIEVED_AT_0018 = "2026-08-21T00:00:00Z"
RETRIEVED_AT_0022 = "2026-08-24T00:00:00Z"


def _entity(qid: str, label: str | None, aliases: list[str] | None = None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=aliases or [], raw_claims={})


def _small_sl0017_manifest() -> dict[str, Any]:
    entities = [_entity("Q9001", "SL0017 Auto Admit Yacht")]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT_0017)
    clusters = compute_baseline_collision_clusters(entities)
    return build_baseline_manifest_0017(
        candidates,
        generated_at=RETRIEVED_AT_0017,
        requested_limit=1,
        unique_qids_returned=1,
        retrieval_count=1,
        extracted_record_count=1,
        target_reached=False,
        collision_clusters=clusters,
    )


def _small_sl0018_manifest(sl0017_manifest: dict[str, Any]) -> dict[str, Any]:
    baseline_0017 = build_baseline_snapshot_from_manifest(
        sl0017_manifest, manifest_path="<synthetic-0017>", sha256="0" * 64
    )
    delta_entities = [_entity("Q9101", "SL0018 Auto Admit Yacht")]
    candidates, clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT_0018, baseline=baseline_0017
    )
    return build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT_0018,
        baseline=baseline_0017,
        discovery_window_qids=[*baseline_0017.candidate_qids, *[e.qid for e in delta_entities]],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=1,
        extracted_record_count=1,
    )


def _combined_baseline(sl0017_manifest: dict[str, Any], sl0018_manifest: dict[str, Any]) -> Any:
    combined = {
        "candidates": [*sl0017_manifest["candidates"], *sl0018_manifest["candidates"]],
        "retained_crosswalk": sl0018_manifest["retained_crosswalk"],
    }
    return build_baseline_snapshot_from_manifest(
        combined, manifest_path="<synthetic-combined>", sha256="0" * 64
    )


def _small_sl0022_manifest(
    sl0017_manifest: dict[str, Any], sl0018_manifest: dict[str, Any]
) -> dict[str, Any]:
    """A small synthetic SLICE-0022 delta:

    - D1 (R1) is a clean new candidate -> AUTO_ADMIT.
    - D2 (R1) collides (same search key) with the combined baseline's
      auto-admitted SL0017 Q9001 -> REVIEW_REQUIRED; Q9001 itself untouched.
    - D3/D4 (R1) collide with each other (within-57) -> both REVIEW_REQUIRED.
    - D5 (R1) has no label -> NOT_ADMITTED.
    - D6 (R3) has a usable label and no collision -> REVIEW_REQUIRED
      (r3_repair_signal_requires_review), never AUTO_ADMIT.
    - D7 (R3) has no label -> NOT_ADMITTED.
    """
    baseline = _combined_baseline(sl0017_manifest, sl0018_manifest)
    rows = [
        {
            "qid": "Q9201",
            "route_membership": ["R1"],
            "label": "SL0022 Clean Candidate",
            "aliases": [],
        },
        {
            "qid": "Q9202",
            "route_membership": ["R1"],
            "label": "SL0017 Auto Admit Yacht",
            "aliases": [],
        },
        {
            "qid": "Q9203",
            "route_membership": ["R1"],
            "label": "SL0022 Duplicate Name",
            "aliases": [],
        },
        {
            "qid": "Q9204",
            "route_membership": ["R1"],
            "label": "SL0022 Duplicate Name",
            "aliases": [],
        },
        {"qid": "Q9205", "route_membership": ["R1"], "label": None, "aliases": []},
        {
            "qid": "Q9206",
            "route_membership": ["R3"],
            "label": "SL0022 R3 Repair Signal",
            "aliases": [],
        },
        {"qid": "Q9207", "route_membership": ["R3"], "label": None, "aliases": []},
    ]
    candidates, _within_57_clusters, _baseline_collisions = classify_sl0022_candidates(
        rows, retrieved_at=RETRIEVED_AT_0022, baseline=baseline
    )
    # build_sl0022_manifest requires exactly the accepted 57/53/4 shape; the
    # synthetic 7-candidate fixture here only exercises classification and
    # replay directly (not the production manifest builder's own count
    # guard), so serialize the manifest by hand using the same row shape.
    return {
        "manifest_version": "0022-v1",
        "source_id": "SRC_TEST",
        "generated_at": RETRIEVED_AT_0022,
        "acquired_at": RETRIEVED_AT_0022,
        "classification_recomputed_at": None,
        "candidates": [sl0022_candidate_to_manifest_dict(c) for c in candidates],
    }


@pytest.fixture()
def small_manifests(tmp_path: Path) -> tuple[Path, Path, Path]:
    sl0017_manifest = _small_sl0017_manifest()
    sl0018_manifest = _small_sl0018_manifest(sl0017_manifest)
    sl0022_manifest = _small_sl0022_manifest(sl0017_manifest, sl0018_manifest)

    sl0017_path = tmp_path / "sl0017_manifest.json"
    sl0017_path.write_text(json.dumps(sl0017_manifest), encoding="utf-8")
    sl0018_path = tmp_path / "sl0018_manifest.json"
    sl0018_path.write_text(json.dumps(sl0018_manifest), encoding="utf-8")
    sl0022_path = tmp_path / "sl0022_manifest.json"
    sl0022_path.write_text(json.dumps(sl0022_manifest), encoding="utf-8")
    return sl0017_path, sl0018_path, sl0022_path


def _assert_clean_combined_replay(result: dict[str, Any]) -> None:
    assert result["prior_baseline_candidates"] == 2  # Q9001 (0017) + Q9101 (0018)
    assert result["prior_baseline_auto_admit"] == 2
    assert result["sl0022_candidates"] == 7
    assert result["sl0022_auto_admit"] == 1  # only Q9201

    assert result["expected"] == {
        "combined_bundle_count": 2 + 5,  # 2 prior + 5 labeled sl0022 (Q9201-Q9204, Q9206)
        "combined_admission_count": 2 + 1,
    }

    for pass_result in (result["first_pass"], result["fresh_schema_rerun"]):
        assert pass_result["bundle"]["imported"] == 7
        assert pass_result["bundle"]["already_present"] == 0
        assert pass_result["bundle"]["conflict"] == 0
        assert pass_result["bundle"]["error"] == 0
        assert pass_result["admission"]["imported"] == 3
        assert pass_result["admission"]["already_present"] == 0
        assert pass_result["admission"]["conflict"] == 0
        assert pass_result["admission"]["reference_error"] == 0
        assert pass_result["expected_counts_match"] is True

        pbv = pass_result["prior_baseline_verified_before_sl0022"]
        assert pbv["counts_match"] is True
        assert pbv["id_set_matches"] is True
        assert pbv["readback_mismatches"] == 0

        rb = pass_result["readback"]
        assert rb["mismatches"] == 0
        assert rb["prior_baseline_drift_mismatches"] == 0
        assert rb["unexpected_canonical_rows_for_non_admitted"] == 0
        assert rb["canonical_id_set_matches"] is True
        assert rb["no_stray_brand_organization_boatdesign_rows"] is True

        assert pass_result["reimport"]["conflict"] == 0
        assert pass_result["reimport"]["error"] == 0

    assert result["all_zero_tolerance_conditions_clear"] is True


def test_prior_baseline_then_sl0022_replay_clears_every_zero_tolerance_condition(
    db_url: str, clean_conn: Any, small_manifests: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    from bootstrap.wikidata_sl0022_alt_route_admission_runner import replay_manifest

    clean_conn.close()
    sl0017_path, sl0018_path, sl0022_path = small_manifests

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    result = replay_manifest(
        db_url,
        sl0017_manifest_path=sl0017_path,
        sl0018_manifest_path=sl0018_path,
        manifest_path=sl0022_path,
        result_path=result_path,
        report_path=report_path,
    )
    _assert_clean_combined_replay(result)
    assert result_path.exists()
    assert report_path.exists()


def test_replay_never_persists_review_or_not_admitted_sl0022_candidates(
    db_url: str, clean_conn: Any, small_manifests: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """Q9202 (baseline collision), Q9203/Q9204 (within-57 collision), Q9205
    (missing label), Q9206 (R3 fail-closed review) and Q9207 (R3 missing
    label) must never appear as canonical BoatModel rows — only Q9001
    (0017), Q9101 (0018) and Q9201 (0022) are admitted.
    """
    from bootstrap.wikidata_sl0022_alt_route_admission_runner import replay_manifest

    clean_conn.close()
    sl0017_path, sl0018_path, sl0022_path = small_manifests
    sl0022_manifest = json.loads(sl0022_path.read_text(encoding="utf-8"))
    non_admitted_qids = {
        row["qid"] for row in sl0022_manifest["candidates"] if row["decision"] != "auto_admit"
    }
    assert non_admitted_qids == {"Q9202", "Q9203", "Q9204", "Q9205", "Q9206", "Q9207"}
    r3_qids = {
        row["qid"] for row in sl0022_manifest["candidates"] if row["route_membership"] == ["R3"]
    }
    assert r3_qids <= non_admitted_qids  # every R3 candidate is non-admitted

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    result = replay_manifest(
        db_url,
        sl0017_manifest_path=sl0017_path,
        sl0018_manifest_path=sl0018_path,
        manifest_path=sl0022_path,
        result_path=result_path,
        report_path=report_path,
    )
    assert result["first_pass"]["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
    assert result["all_zero_tolerance_conditions_clear"] is True

    import psycopg

    conn = psycopg.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM canonical_boat_models")
            ids = {row[0] for row in cur.fetchall()}
        assert ids == set()
    finally:
        conn.close()
