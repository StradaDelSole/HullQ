"""PostgreSQL integration tests for the SLICE-0026 bounded Wikidata Tier-1
enrichment evidence pilot.

Exercises the real persistence mechanism
(scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py::
persist_and_verify) against a small synthetic selection/evidence-manifest
pair rather than the real 100-BoatModel retained artifact, so this test is
fast and self-contained. The real retained artifact is persisted separately
by the db-integration CI job invoking the runner script's ``--persist``
directly against the committed
``research/stage3/sl0026-wikidata-tier1-enrichment/`` package.

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).

Covers the SLICE-0026 required-behavior 9 regression scenario: first import,
exact re-import/idempotency, offline readback/reproduction, and zero mutation
of canonical BoatModel/BoatDesign state. Also regression-covers the Decimal
JSONB round-trip fix in hullq.persistence.schema/fingerprint/readback (a
Decimal-valued NormalizedCandidate, produced by every real Wikidata quantity
measurement, previously raised ``TypeError: Object of type Decimal is not
JSON serializable`` on the very first import through this exact path).
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
def synthetic_pilot_package(tmp_path: Path) -> tuple[Path, Path]:
    """Build a tiny (3-BoatModel) selection + evidence manifest pair using
    the real SLICE-0026 pure-logic builders — not hand-written JSON — so this
    fixture stays byte-compatible with the real schema/shape.
    """
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        IdentityBoundary,
        build_evidence_manifest_document,
        build_selection_document,
        filter_to_allowed_evidence,
        select_pilot_boatmodels,
        summarize_field_coverage,
    )
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig, WikidataEntityData

    boundary = IdentityBoundary(
        baseline_manifest_sha256="0" * 64,
        delta_manifest_sha256="1" * 64,
        canonical_boat_model_count=3,
        historical_crosswalk_count=3,
        auto_admit_qid_to_hullq_id=(
            ("Q9001", "BM_TEST_0001"),
            ("Q9002", "BM_TEST_0002"),
            ("Q9003", "BM_TEST_0003"),
        ),
        preferred_label_by_qid={"Q9001": "Test Yacht 1", "Q9002": "Test Yacht 2", "Q9003": None},
    )
    selection = select_pilot_boatmodels(boundary, count=3)
    selection_doc = build_selection_document(
        generated_at="2026-01-01T00:00:00Z", boundary=boundary, selection=selection
    )

    entities = [
        # Q9001: displacement present with a Decimal-valued normalized candidate
        # — the exact shape that previously broke the JSONB persistence path.
        WikidataEntityData(
            qid="Q9001",
            label="Test Yacht 1",
            aliases=[],
            raw_claims={"P2067": [_quantity_claim("+4500", "Q11570", "Q5636358")]},
        ),
        # Q9002: beam present.
        WikidataEntityData(
            qid="Q9002",
            label="Test Yacht 2",
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

    coverage_counts, _details = summarize_field_coverage(entities, full_evidence)

    evidence_doc = build_evidence_manifest_document(
        generated_at="2026-01-01T00:00:00Z",
        acquired_at="2026-01-01T00:00:00Z",
        selection=selection,
        entities=entities,
        allowed_evidence_by_qid=by_qid,
        coverage_counts=coverage_counts,
        quality_report=report,
        requested_qid_count=3,
    )

    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection_doc), encoding="utf-8")
    evidence_manifest_path = tmp_path / "evidence_manifest.json"
    evidence_manifest_path.write_text(json.dumps(evidence_doc), encoding="utf-8")
    return selection_path, evidence_manifest_path


def test_persist_and_verify_first_import_readback_and_idempotent_reimport(
    db_url: str,
    clean_conn: Any,
    synthetic_pilot_package: tuple[Path, Path],
) -> None:
    from bootstrap.wikidata_sl0026_tier1_enrichment_pilot_runner import persist_and_verify

    clean_conn.close()
    selection_path, evidence_manifest_path = synthetic_pilot_package

    result = persist_and_verify(
        db_url,
        schema_name="hullq_sl0026_test_" + "first",
        selection_path=selection_path,
        evidence_manifest_path=evidence_manifest_path,
    )

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
    synthetic_pilot_package: tuple[Path, Path],
) -> None:
    """The isolated per-run schema is dropped on exit; the default schema
    used by clean_conn/a fresh connection must remain completely untouched —
    zero canonical rows and zero research-evidence rows leaked outside the
    isolated schema."""
    from bootstrap.wikidata_sl0026_tier1_enrichment_pilot_runner import persist_and_verify

    clean_conn.close()
    selection_path, evidence_manifest_path = synthetic_pilot_package

    persist_and_verify(
        db_url,
        schema_name="hullq_sl0026_test_" + "isolation",
        selection_path=selection_path,
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
