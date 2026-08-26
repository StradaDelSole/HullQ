"""PostgreSQL integration tests for the SLICE-0028 full-boundary Wikidata
Tier-1 evidence rollout.

Exercises the real persistence mechanism
(scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py::
persist_and_verify) against a small synthetic linkage/evidence-manifest pair
rather than the real 1,770-BoatModel retained artifact, so this test is fast
and self-contained. The real retained artifact is persisted separately by the
db-integration CI job invoking the runner script's ``--persist`` directly
against the committed
``research/stage3/sl0028-wikidata-tier1-full-boundary/`` package.

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).

Covers: first import, exact re-import/idempotency, offline readback, zero
mutation of canonical BoatModel/BoatDesign state, and one BoatModel with more
than one accepted QID persisting as two independent QID-keyed bundles.
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
    """Build a tiny (3-BoatModel, one with two accepted QIDs) linkage +
    evidence manifest pair using the real SLICE-0028 pure-logic builders —
    not hand-written JSON — so this fixture stays byte-compatible with the
    real schema/shape."""
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        IdentityBoundary,
        filter_to_allowed_evidence,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        build_evidence_manifest_document,
        build_full_boundary_linkage,
        build_linkage_document,
    )
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig, WikidataEntityData

    boundary = IdentityBoundary(
        baseline_manifest_sha256="0" * 64,
        delta_manifest_sha256="1" * 64,
        canonical_boat_model_count=2,
        historical_crosswalk_count=3,
        auto_admit_qid_to_hullq_id=(
            ("Q9001", "BM_TEST_0001"),
            ("Q9002", "BM_TEST_0001"),  # BM_TEST_0001 has two accepted QIDs.
            ("Q9003", "BM_TEST_0002"),
        ),
        preferred_label_by_qid={
            "Q9001": "Test Yacht 1",
            "Q9002": "Test Yacht 1 (alt)",
            "Q9003": None,
        },
    )
    linkage = build_full_boundary_linkage(boundary)
    linkage_doc = build_linkage_document(
        generated_at="2026-01-01T00:00:00Z", boundary=boundary, linkage=linkage
    )

    entities = [
        # Q9001: displacement present with a Decimal-valued normalized candidate.
        WikidataEntityData(
            qid="Q9001",
            label="Test Yacht 1",
            aliases=[],
            raw_claims={"P2067": [_quantity_claim("+4500", "Q11570", "Q5636358")]},
        ),
        # Q9002: same BoatModel, a different accepted QID with beam present.
        WikidataEntityData(
            qid="Q9002",
            label="Test Yacht 1 (alt)",
            aliases=[],
            raw_claims={
                "P2049": [
                    {
                        "id": "stmt2",
                        "mainsnak": {
                            "snaktype": "value",
                            "datavalue": {
                                "type": "quantity",
                                "value": {
                                    "amount": "+3.5",
                                    "unit": "http://www.wikidata.org/entity/Q11573",
                                },
                            },
                        },
                    }
                ]
            },
        ),
        # Q9003: no usable evidence at all — an empty bundle must persist cleanly.
        WikidataEntityData(qid="Q9003", label=None, aliases=[], raw_claims={}),
    ]

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (test@example.com)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        full_evidence, report = adapter.extract_field_evidence(
            entities, "2026-01-01T00:00:00Z", requested_qid_count=3
        )

    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    evidence_doc = build_evidence_manifest_document(
        generated_at="2026-01-01T00:00:00Z",
        acquired_at="2026-01-01T00:00:00Z",
        linkage=linkage,
        entities=entities,
        allowed_evidence_by_qid=by_qid,
        quality_report=report,
        requested_qid_count=3,
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
    from bootstrap.wikidata_sl0028_full_boundary_evidence_runner import persist_and_verify

    clean_conn.close()
    linkage_path, evidence_manifest_path = synthetic_full_boundary_package

    result = persist_and_verify(
        db_url,
        schema_name="hullq_sl0028_test_" + "first",
        linkage_path=linkage_path,
        evidence_manifest_path=evidence_manifest_path,
    )

    # Three distinct requested QIDs -> three independent QID-keyed bundles,
    # even though two of them (Q9001, Q9002) belong to the same BoatModel.
    assert result["bundle_count"] == 3
    assert result["first_pass"] == {"imported": 3, "already_present": 0, "conflict": 0, "error": 0}
    assert result["readback_mismatches"] == 0
    assert result["reimport"] == {"already_imported": 3, "conflict": 0, "error": 0}
    assert result["canonical_boat_model_row_count"] == 0
    assert result["canonical_boat_design_row_count"] == 0
    assert result["clear"] is True


def test_persist_and_verify_never_creates_canonical_rows_in_default_schema(
    db_url: str,
    clean_conn: Any,
    synthetic_full_boundary_package: tuple[Path, Path],
) -> None:
    """The isolated per-run schema is dropped on exit; the default schema
    used by clean_conn/a fresh connection must remain completely untouched —
    zero canonical rows and zero research-evidence rows leaked outside the
    isolated schema."""
    from bootstrap.wikidata_sl0028_full_boundary_evidence_runner import persist_and_verify

    clean_conn.close()
    linkage_path, evidence_manifest_path = synthetic_full_boundary_package

    persist_and_verify(
        db_url,
        schema_name="hullq_sl0028_test_" + "isolation",
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
