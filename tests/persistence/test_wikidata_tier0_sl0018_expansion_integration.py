"""PostgreSQL 18 integration tests for the SLICE-0018 Wikidata Tier-0
2,500-window expansion.

Exercises the real combined baseline-first/delta-second offline replay path
(scripts/bootstrap/wikidata_tier0_sl0018_runner.py) against small synthetic
baseline + delta manifests built through the same classification/
materialization logic used for the retained production manifests
(``verify_baseline_integrity=False`` — the accepted-constant integrity gate
is exercised separately in tests/unit against the real retained artifact).
The full retained production manifests themselves are replayed separately by
the db-integration CI job invoking the runner script directly against
``research/bootstrap/wikidata/manifest.json`` (baseline) and
``research/bootstrap/wikidata/sl0018-2500/manifest.json`` (delta).

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).

Covers SLICE-0018 required regression scenario 10:
  10. baseline import followed by delta import preserves the baseline graph
      and adds only the expected new BoatModels/evidence links.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

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

RETRIEVED_AT_BASELINE = "2026-08-21T00:00:00Z"
RETRIEVED_AT_DELTA = "2026-08-22T00:00:00Z"


def _entity(qid: str, label: str | None, aliases: list[str] | None = None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=aliases or [], raw_claims={})


def _small_baseline_manifest() -> dict[str, Any]:
    """A small synthetic baseline (mirrors SLICE-0017's own small test
    manifest shape): B1 auto-admits, B2/B3 collide with each other and are
    REVIEW_REQUIRED, B4 has no label and is NOT_ADMITTED.
    """
    entities = [
        _entity("Q9001", "Baseline Auto Admit Yacht", aliases=["Baseline Alt Name"]),
        _entity("Q9002", "Baseline Collision Name"),
        _entity("Q9003", "Baseline Collision Name"),
        _entity("Q9004", None),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT_BASELINE)
    clusters = compute_baseline_collision_clusters(entities)
    return build_baseline_manifest_0017(
        candidates,
        generated_at=RETRIEVED_AT_BASELINE,
        requested_limit=4,
        unique_qids_returned=4,
        retrieval_count=1,
        extracted_record_count=4,
        target_reached=False,
        collision_clusters=clusters,
    )


def _small_delta_manifest(baseline_manifest: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    """A small synthetic SLICE-0018 delta against *baseline_manifest*:

    - D1 is a clean new candidate -> AUTO_ADMIT.
    - D2 collides (same search key) with the baseline's AUTO_ADMIT B1 ->
      REVIEW_REQUIRED; B1 itself is untouched.
    - D3/D4 collide with each other (delta<->delta) -> both REVIEW_REQUIRED.
    - D5 has no label -> NOT_ADMITTED.
    """
    baseline = build_baseline_snapshot_from_manifest(
        baseline_manifest, manifest_path="<synthetic-baseline>", sha256="0" * 64
    )
    delta_entities = [
        _entity("Q9101", "Delta Clean Candidate"),
        _entity("Q9102", "Baseline Auto Admit Yacht"),  # collides with baseline B1 (Q9001)
        _entity("Q9103", "Delta Duplicate Name"),
        _entity("Q9104", "Delta Duplicate Name"),
        _entity("Q9105", None),
    ]
    candidates, delta_clusters, baseline_collisions = classify_delta_candidates(
        delta_entities, retrieved_at=RETRIEVED_AT_DELTA, baseline=baseline
    )
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=RETRIEVED_AT_DELTA,
        baseline=baseline,
        discovery_window_qids=[*baseline.candidate_qids, *[e.qid for e in delta_entities]],
        requested_limit=2500,
        target_reached=False,
        delta_delta_clusters=delta_clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=1,
        extracted_record_count=5,
    )
    return manifest, baseline


@pytest.fixture()
def small_manifests(tmp_path: Path) -> tuple[Path, Path]:
    baseline_manifest = _small_baseline_manifest()
    delta_manifest, _baseline = _small_delta_manifest(baseline_manifest)

    baseline_path = tmp_path / "baseline_manifest.json"
    baseline_path.write_text(json.dumps(baseline_manifest), encoding="utf-8")
    delta_path = tmp_path / "sl0018_manifest.json"
    delta_path.write_text(json.dumps(delta_manifest), encoding="utf-8")
    return baseline_path, delta_path


def _assert_clean_combined_replay(result: dict[str, Any]) -> None:
    # Baseline: only Q9001 auto-admits (985-style: bundle for every labeled
    # candidate = 3 of 4; admission only for Q9001).
    assert result["baseline_manifest_candidates"] == 4
    assert result["baseline_manifest_auto_admit"] == 1
    # Delta: only Q9101 auto-admits; bundle built for every labeled delta
    # candidate (Q9101, Q9102, Q9103, Q9104 = 4 of 5).
    assert result["delta_manifest_candidates"] == 5
    assert result["delta_manifest_auto_admit"] == 1

    assert result["expected"] == {
        "combined_bundle_count": 3 + 4,
        "combined_admission_count": 1 + 1,
    }

    for pass_result in (result["first_pass"], result["fresh_schema_rerun"]):
        assert pass_result["bundle"]["imported"] == 7
        assert pass_result["bundle"]["already_present"] == 0
        assert pass_result["bundle"]["conflict"] == 0
        assert pass_result["bundle"]["error"] == 0
        assert pass_result["bundle"]["unexpected_status"] == 0
        assert pass_result["admission"]["imported"] == 2
        assert pass_result["admission"]["already_present"] == 0
        assert pass_result["admission"]["conflict"] == 0
        assert pass_result["admission"]["reference_error"] == 0
        assert pass_result["admission"]["error"] == 0
        assert pass_result["admission"]["unexpected_status"] == 0
        assert pass_result["expected_counts_match"] is True

        bvbd = pass_result["baseline_verified_before_delta"]
        assert bvbd["counts_match"] is True
        assert bvbd["id_set_matches"] is True
        assert bvbd["readback_mismatches"] == 0

        rb = pass_result["readback"]
        assert rb["mismatches"] == 0
        assert rb["post_delta_baseline_drift_mismatches"] == 0
        assert rb["unexpected_canonical_rows_for_non_admitted"] == 0
        assert rb["canonical_id_set_matches"] is True
        assert rb["no_stray_brand_organization_boatdesign_rows"] is True

        assert pass_result["reimport"]["conflict"] == 0
        assert pass_result["reimport"]["error"] == 0
        assert pass_result["reimport"]["already_imported"] == 7 + 2  # bundles + admissions

    assert result["all_zero_tolerance_conditions_clear"] is True


def test_combined_baseline_then_delta_replay_clears_every_zero_tolerance_condition(
    db_url: str, clean_conn: Any, small_manifests: tuple[Path, Path], tmp_path: Path
) -> None:
    from bootstrap.wikidata_tier0_sl0018_runner import replay_manifest

    clean_conn.close()
    baseline_path, delta_path = small_manifests

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    result = replay_manifest(
        db_url,
        baseline_manifest_path=baseline_path,
        manifest_path=delta_path,
        result_path=result_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    _assert_clean_combined_replay(result)
    assert result_path.exists()
    assert report_path.exists()


def test_combined_replay_never_persists_review_or_not_admitted_delta_candidates(
    db_url: str, clean_conn: Any, small_manifests: tuple[Path, Path], tmp_path: Path
) -> None:
    """Q9102 (baseline collision), Q9103/Q9104 (delta<->delta collision) and
    Q9105 (missing label) must never appear as canonical BoatModel rows —
    only Q9001 (baseline) and Q9101 (delta) are admitted.
    """
    from bootstrap.wikidata_tier0_sl0018_runner import replay_manifest

    clean_conn.close()
    baseline_path, delta_path = small_manifests
    delta_manifest = json.loads(delta_path.read_text(encoding="utf-8"))
    non_admitted_qids = {
        row["qid"] for row in delta_manifest["candidates"] if row["decision"] != "auto_admit"
    }
    assert non_admitted_qids == {"Q9102", "Q9103", "Q9104", "Q9105"}

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    result = replay_manifest(
        db_url,
        baseline_manifest_path=baseline_path,
        manifest_path=delta_path,
        result_path=result_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    assert result["first_pass"]["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
    assert result["all_zero_tolerance_conditions_clear"] is True

    import psycopg

    conn = psycopg.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM canonical_boat_models")
            ids = {row[0] for row in cur.fetchall()}
        # Isolated replay schemas are dropped on exit; the default schema
        # used by clean_conn/this fresh connection must remain untouched.
        assert ids == set()
    finally:
        conn.close()
