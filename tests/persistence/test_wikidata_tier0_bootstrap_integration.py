"""PostgreSQL 18 integration tests for the SLICE-0017 Wikidata Tier-0 bootstrap.

Exercises the real offline replay path (scripts/bootstrap/wikidata_tier0_runner.py)
against a small synthetic manifest built through the same
hullq.bootstrap.wikidata_tier0 classification/materialization logic used for
the retained production manifest. The full retained manifest itself is
replayed separately by the db-integration CI job invoking the runner script
directly against research/bootstrap/wikidata/manifest.json.

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).

Covers SLICE-0017 required test scenarios 20-23:
  20. full retained manifest replays against real PostgreSQL 18.
  21. exact second replay is idempotent with zero conflicts/errors.
  22. fresh-schema replay is semantically equal.
  23. no unexpected Brand/Organization/BoatDesign rows are created during
      Tier-0 model bootstrap.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from hullq.bootstrap.wikidata_tier0 import (
    BootstrapDecision,
    build_manifest,
    classify_candidates,
    compute_collision_clusters,
)
from hullq.sources.wikidata import WikidataEntityData

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

RETRIEVED_AT = "2026-08-21T00:00:00Z"


def _entity(qid: str, label: str | None, aliases: list[str] | None = None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=aliases or [], raw_claims={})


def _small_manifest() -> dict[str, Any]:
    entities = [
        _entity("Q1001", "Bootstrap Test Yacht One", aliases=["Alt Name One"]),
        _entity("Q1002", "Bootstrap Test Yacht Two"),
        _entity("Q1003", "Bootstrap Duplicate Name"),
        _entity("Q1004", "Bootstrap Duplicate Name"),
        _entity("Q1005", None),
        _entity("Q1006", "Alias Collider", aliases=["Bootstrap Test Yacht One"]),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)
    clusters = compute_collision_clusters(entities)
    return build_manifest(
        candidates,
        generated_at=RETRIEVED_AT,
        requested_limit=6,
        unique_qids_returned=6,
        retrieval_count=1,
        extracted_record_count=6,
        target_reached=False,
        collision_clusters=clusters,
    )


@pytest.fixture()
def small_manifest_path(tmp_path: Path) -> Path:
    manifest = _small_manifest()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_full_manifest_replay_clears_every_zero_tolerance_condition(
    db_url: str, clean_conn: Any, small_manifest_path: Path, tmp_path: Path
) -> None:
    from bootstrap.wikidata_tier0_runner import replay_manifest

    clean_conn.close()  # ensures a clean, truncated schema; replay_manifest opens its own connections

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    result = replay_manifest(
        db_url, manifest_path=small_manifest_path, result_path=result_path, report_path=report_path
    )

    # Q1002 only: Q1001/Q1006 collide via alias, Q1003/Q1004 collide by name,
    # Q1005 has no label.
    assert result["manifest_auto_admit"] == 1
    assert result["first_pass"]["bundle_imported"] == 5  # every candidate with a label
    assert result["first_pass"]["admission_imported"] == 1
    assert result["first_pass"]["admission_reference_error"] == 0
    assert result["readback"]["mismatches"] == 0
    assert result["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
    assert result["readback"]["canonical_id_set_matches"] is True
    assert result["readback"]["no_stray_brand_organization_boatdesign_rows"] is True
    assert result["reimport"]["already_imported"] == 5 + 1  # bundles + admissions
    assert result["reimport"]["conflict"] == 0
    assert result["reimport"]["error"] == 0
    assert result["fresh_schema_rerun"]["imported"] == 1
    assert result["fresh_schema_rerun"]["semantic_mismatches"] == 0
    assert result["fresh_schema_rerun"]["error"] == 0
    assert result["fresh_schema_rerun"]["id_set_matches"] is True
    assert result["all_zero_tolerance_conditions_clear"] is True
    assert result_path.exists()
    assert report_path.exists()

    # Deep semantic proof: the single admitted BoatModel's alias set is exactly
    # what build_admission expects, not just canonical_name.
    from hullq.persistence.identity_readback import fetch_boat_model

    manifest = json.loads(small_manifest_path.read_text(encoding="utf-8"))
    admitted_row = next(c for c in manifest["candidates"] if c["qid"] == "Q1002")
    import psycopg

    conn = psycopg.connect(db_url)
    try:
        fetched = fetch_boat_model(conn, admitted_row["hullq_id"])
        assert fetched is not None
        assert fetched["canonical_name"] == "Bootstrap Test Yacht Two"
        assert fetched["aliases"] == []
    finally:
        conn.close()


def test_review_required_and_not_admitted_never_persist_as_canonical(
    clean_conn: Any, registry: Any
) -> None:
    from hullq.bootstrap.wikidata_tier0 import build_admission, build_bundle
    from hullq.persistence.importer import import_research_evidence_bundle

    entities = [
        _entity("Q2001", "Collision Name"),
        _entity("Q2002", "Collision Name"),
        _entity("Q2003", None),
    ]
    candidates = classify_candidates(entities, retrieved_at=RETRIEVED_AT)

    for candidate in candidates:
        assert candidate.decision != BootstrapDecision.AUTO_ADMIT
        bundle = build_bundle(candidate)
        if bundle is not None:
            import_research_evidence_bundle(clean_conn, bundle)
        assert build_admission(candidate) is None

    with clean_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM canonical_boat_models")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM canonical_brands")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM canonical_organizations")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT COUNT(*) FROM canonical_boat_designs")
        assert cur.fetchone()[0] == 0


def test_auto_admitted_candidate_persists_sparse_boat_model_with_evidence_link(
    clean_conn: Any, registry: Any
) -> None:
    from hullq.bootstrap.wikidata_tier0 import build_admission, build_bundle
    from hullq.domain.provenance import SubjectKind
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.identity_importer import import_canonical_identity_admission
    from hullq.persistence.identity_readback import (
        fetch_boat_model,
        fetch_evidence_links_for_entity,
    )
    from hullq.persistence.identity_types import CanonicalImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle

    candidates = classify_candidates(
        [_entity("Q3001", "Unique Bootstrap Yacht")], retrieved_at=RETRIEVED_AT
    )
    candidate = candidates[0]
    assert candidate.decision == BootstrapDecision.AUTO_ADMIT

    bundle = build_bundle(candidate)
    admission = build_admission(candidate)
    assert bundle is not None and admission is not None

    bundle_result = import_research_evidence_bundle(clean_conn, bundle)
    assert bundle_result.status == ImportStatus.IMPORTED
    admission_result = import_canonical_identity_admission(clean_conn, admission, registry)
    assert admission_result.status == CanonicalImportStatus.IMPORTED

    fetched = fetch_boat_model(clean_conn, candidate.hullq_id)
    assert fetched is not None
    assert fetched["canonical_name"] == "Unique Bootstrap Yacht"
    assert fetched["brand_relationships"] == []
    assert fetched["boat_design_ids"] == []

    links = fetch_evidence_links_for_entity(clean_conn, SubjectKind.BOAT_MODEL, candidate.hullq_id)
    assert len(links) == 1
    assert links[0].observation_id == candidate.observation_id


@pytest.fixture()
def registry() -> Any:
    from hullq.contracts import ContractRegistry

    return ContractRegistry.from_directory(ROOT / "specs")
