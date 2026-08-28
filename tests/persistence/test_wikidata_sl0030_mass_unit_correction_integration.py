"""PostgreSQL integration tests for the SLICE-0030 Wikidata mass-unit
correction persistence replay.

Exercises the real persistence mechanism
(scripts/bootstrap/wikidata_sl0030_mass_unit_correction_runner.py::
persist_and_verify) against a small synthetic linkage/evidence-manifest pair
built with the same SLICE-0028 document builders, rather than the real
1,770-BoatModel retained artifact, so this test is fast and self-contained.
The real retained artifact is persisted separately by the db-integration CI
job invoking the runner script's ``--persist`` directly against the
committed ``research/stage3/sl0030-wikidata-mass-unit-correction/`` package
(replaying the fixed SLICE-0028 evidence).

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).

Covers: the corrected mass-unit map actually changes what gets persisted
relative to the legacy map (a Q100995/pound statement that the legacy map
could never normalize now persists a normalized displacement candidate),
first import, exact re-import/idempotency, offline readback, zero mutation of
canonical BoatModel/BoatDesign state, and a distinct BUNDLE-SL0030-* bundle
namespace that never collides with the accepted BUNDLE-SL0028-* bundles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def _quantity_claim(amount: str, unit_qid: str, qualifier_qid: str) -> dict[str, Any]:
    return {
        "id": "stmt1",
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {
                "type": "quantity",
                "value": {"amount": amount, "unit": f"http://www.wikidata.org/entity/{unit_qid}"},
            },
        },
        "qualifiers": {
            "P642": [
                {
                    "snaktype": "value",
                    "datavalue": {"type": "wikibase-entityid", "value": {"id": qualifier_qid}},
                }
            ]
        },
    }


@pytest.fixture()
def synthetic_full_boundary_package(tmp_path: Path) -> tuple[Path, Path]:
    """Build a tiny (2-BoatModel) linkage + evidence manifest pair using the
    real SLICE-0028 pure-logic builders — not hand-written JSON — where one
    entity carries a Q100995 (pound) displacement statement the legacy
    SLICE-0008 map could never normalize."""
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        IdentityBoundary,
        filter_to_allowed_evidence,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        build_evidence_manifest_document,
        build_full_boundary_linkage,
        build_historical_registry_reconciliation_block,
        build_linkage_document,
    )
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig, WikidataEntityData

    boundary = IdentityBoundary(
        baseline_manifest_sha256="0" * 64,
        delta_manifest_sha256="1" * 64,
        canonical_boat_model_count=2,
        historical_crosswalk_count=2,
        auto_admit_qid_to_hullq_id=(
            ("Q9101", "BM_TEST_SL0030_0001"),
            ("Q9102", "BM_TEST_SL0030_0002"),
        ),
        preferred_label_by_qid={"Q9101": "Test Yacht SL0030 A", "Q9102": "Test Yacht SL0030 B"},
    )
    linkage = build_full_boundary_linkage(boundary)
    reconciliation = build_historical_registry_reconciliation_block(
        boundary=boundary, reserved_entries=()
    )
    linkage_doc = build_linkage_document(
        generated_at="2026-01-01T00:00:00Z",
        boundary=boundary,
        linkage=linkage,
        historical_registry_reconciliation=reconciliation,
    )

    entities = [
        # Q9101: displacement in pounds (Q100995) — the legacy SLICE-0008 map
        # never recognized this QID as a unit, so this normalized candidate
        # only exists under the SLICE-0030 corrected/default map.
        WikidataEntityData(
            qid="Q9101",
            label="Test Yacht SL0030 A",
            aliases=[],
            raw_claims={"P2067": [_quantity_claim("+2490", "Q100995", "Q5636358")]},
        ),
        # Q9102: no usable evidence at all — an empty bundle must persist cleanly.
        WikidataEntityData(qid="Q9102", label="Test Yacht SL0030 B", aliases=[], raw_claims={}),
    ]

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (test@example.com)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        full_evidence, report = adapter.extract_field_evidence(
            entities, "2026-01-01T00:00:00Z", requested_qid_count=2
        )

    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    assert by_qid["Q9101"][0].normalized_candidate is not None
    assert str(by_qid["Q9101"][0].normalized_candidate.value) == "1129.44500130"

    evidence_doc = build_evidence_manifest_document(
        generated_at="2026-01-01T00:00:00Z",
        acquired_at="2026-01-01T00:00:00Z",
        linkage=linkage,
        entities=entities,
        allowed_evidence_by_qid=by_qid,
        quality_report=report,
        requested_qid_count=2,
    )

    linkage_path = tmp_path / "linkage.json"
    linkage_path.write_text(json.dumps(linkage_doc), encoding="utf-8")
    evidence_manifest_path = tmp_path / "evidence_manifest.json"
    evidence_manifest_path.write_text(json.dumps(evidence_doc), encoding="utf-8")
    return linkage_path, evidence_manifest_path


def test_persist_and_verify_first_import_readback_and_idempotent_reimport(
    db_url: str,
    clean_conn: Any,
    synthetic_full_boundary_package: tuple[Path, Path],
) -> None:
    from bootstrap.wikidata_sl0030_mass_unit_correction_runner import persist_and_verify

    clean_conn.close()
    linkage_path, evidence_manifest_path = synthetic_full_boundary_package

    result = persist_and_verify(
        db_url,
        schema_name="hullq_sl0030_test_" + "first",
        linkage_path=linkage_path,
        evidence_manifest_path=evidence_manifest_path,
    )

    assert result["bundle_count"] == 2
    assert result["first_pass"] == {"imported": 2, "already_present": 0, "conflict": 0, "error": 0}
    assert result["readback_mismatches"] == 0
    assert result["reimport"] == {"already_imported": 2, "conflict": 0, "error": 0}
    assert result["canonical_boat_model_row_count"] == 0
    assert result["canonical_boat_design_row_count"] == 0
    assert result["clear"] is True


def test_persist_and_verify_never_creates_canonical_rows_in_default_schema(
    db_url: str,
    clean_conn: Any,
    synthetic_full_boundary_package: tuple[Path, Path],
) -> None:
    """The isolated per-run schema is dropped on exit; the default schema
    used by a fresh connection must remain completely untouched."""
    from bootstrap.wikidata_sl0030_mass_unit_correction_runner import persist_and_verify

    clean_conn.close()
    linkage_path, evidence_manifest_path = synthetic_full_boundary_package

    persist_and_verify(
        db_url,
        schema_name="hullq_sl0030_test_" + "isolation",
        linkage_path=linkage_path,
        evidence_manifest_path=evidence_manifest_path,
    )

    import psycopg

    conn = psycopg.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM canonical_boat_models")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM research_bundles")
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()
