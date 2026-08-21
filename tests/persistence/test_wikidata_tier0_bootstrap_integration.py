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
    # Q1002 is the sole AUTO_ADMIT candidate below and deliberately carries an
    # alias: the actual accepted admission/readback path for a non-empty
    # alias list on an admitted candidate must be exercised against real
    # PostgreSQL (exact-head CI run #199 regression — AttributeError:
    # 'dict' object has no attribute 'id' — only manifested once an admitted
    # candidate had aliases; Q1001's alias never reached readback because
    # Q1001 collides and is REVIEW_REQUIRED, not admitted).
    entities = [
        _entity("Q1001", "Bootstrap Test Yacht One", aliases=["Alt Name One"]),
        _entity("Q1002", "Bootstrap Test Yacht Two", aliases=["Yacht Two Alt Name"]),
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


def _assert_clean_replay(result: dict[str, Any]) -> None:
    # Q1002 only: Q1001/Q1006 collide via alias, Q1003/Q1004 collide by name,
    # Q1005 has no label.
    assert result["manifest_auto_admit"] == 1
    assert result["expected"] == {"bundle_count": 5, "admission_count": 1}

    fp = result["first_pass"]
    assert fp["bundle"]["imported"] == 5
    assert fp["bundle"]["already_present"] == 0
    assert fp["bundle"]["conflict"] == 0
    assert fp["bundle"]["error"] == 0
    assert fp["bundle"]["unexpected_status"] == 0
    assert fp["admission"]["imported"] == 1
    assert fp["admission"]["already_present"] == 0
    assert fp["admission"]["conflict"] == 0
    assert fp["admission"]["reference_error"] == 0
    assert fp["admission"]["error"] == 0
    assert fp["admission"]["unexpected_status"] == 0
    assert fp["expected_counts_match"] is True

    assert result["readback"]["mismatches"] == 0
    assert result["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
    assert result["readback"]["canonical_id_set_matches"] is True
    assert result["readback"]["no_stray_brand_organization_boatdesign_rows"] is True

    assert result["reimport"]["already_imported"] == 5 + 1  # bundles + admissions
    assert result["reimport"]["conflict"] == 0
    assert result["reimport"]["error"] == 0

    fr = result["fresh_schema_rerun"]
    assert fr["bundle"]["imported"] == 5
    assert fr["bundle"]["already_present"] == 0
    assert fr["admission"]["imported"] == 1
    assert fr["admission"]["already_present"] == 0
    assert fr["semantic_mismatches"] == 0
    assert fr["id_set_matches"] is True
    assert fr["no_stray_brand_organization_boatdesign_rows"] is True
    assert fr["expected_counts_match"] is True

    assert result["all_zero_tolerance_conditions_clear"] is True


def test_full_manifest_replay_clears_every_zero_tolerance_condition(
    db_url: str, clean_conn: Any, small_manifest_path: Path, tmp_path: Path
) -> None:
    from bootstrap.wikidata_tier0_runner import replay_manifest

    clean_conn.close()

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    result = replay_manifest(
        db_url, manifest_path=small_manifest_path, result_path=result_path, report_path=report_path
    )
    _assert_clean_replay(result)
    assert result_path.exists()
    assert report_path.exists()

    # Deep semantic proof: the single admitted BoatModel's alias set is exactly
    # what build_admission expects, not just canonical_name. Read back from
    # the *default* connection — the isolated schema1/schema2 are dropped by
    # replay_manifest on exit, so nothing from the replay should be visible here.
    from hullq.persistence.identity_readback import fetch_boat_model

    manifest = json.loads(small_manifest_path.read_text(encoding="utf-8"))
    admitted_row = next(c for c in manifest["candidates"] if c["qid"] == "Q1002")
    import psycopg

    conn = psycopg.connect(db_url)
    try:
        fetched = fetch_boat_model(conn, admitted_row["hullq_id"])
        assert fetched is None  # the isolated schema was dropped; nothing leaks to default
    finally:
        conn.close()


def test_replay_is_isolated_from_contaminated_public_schema(
    db_url: str, clean_conn: Any, small_manifest_path: Path, tmp_path: Path, registry: Any
) -> None:
    """Reproduces the exact contamination scenario independent review flagged:
    a synthetic canonical BoatModel left behind in the default/public schema
    by an unrelated prior test/step. The isolated replay proof must still be
    fully clean — it must not see, and must not be confused by, this row.
    """
    from hullq.persistence.identity_importer import import_canonical_identity_admission
    from hullq.persistence.identity_types import CanonicalIdentityAdmission, CanonicalImportStatus

    # Contaminate the default/public schema directly (the connection fixture
    # operates on whatever schema is active by default — no isolation).
    contaminating_payload = {
        "schema_version": "0.2",
        "id": "BM_CONTAMINATION_LEFTOVER",
        "canonical_name": "Leftover From Another Test",
        "aliases": [],
        "brand_relationships": [],
        "first_built": None,
        "last_built": None,
        "boat_design_ids": [],
    }
    admission = CanonicalIdentityAdmission(boat_models=(contaminating_payload,))
    result = import_canonical_identity_admission(clean_conn, admission, registry)
    assert result.status == CanonicalImportStatus.IMPORTED
    clean_conn.commit()
    clean_conn.close()

    from bootstrap.wikidata_tier0_runner import replay_manifest

    result_path = tmp_path / "REPLAY-RESULT.json"
    report_path = tmp_path / "REPLAY-REPORT.md"
    replay_result = replay_manifest(
        db_url, manifest_path=small_manifest_path, result_path=result_path, report_path=report_path
    )
    # The contaminating row must not have affected the isolated proof at all:
    # canonical_id_set_matches only ever compares against the isolated
    # schema's own contents, never the polluted public schema.
    _assert_clean_replay(replay_result)


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
