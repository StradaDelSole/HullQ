"""PostgreSQL integration tests for the SLICE-0027 Wikidata qualifier-
semantics correction + offline replay.

Exercises the real persistence mechanism
(scripts/bootstrap/wikidata_sl0027_qualifier_semantics_correction_runner.py::
persist_and_verify) against a small synthetic SLICE-0026-shaped
selection/evidence-manifest pair rather than the real 100-BoatModel retained
artifact, so this test is fast and self-contained. The real retained artifact
is persisted separately by the db-integration CI job invoking the runner
script's ``--persist`` directly against the committed
``research/stage3/sl0026-wikidata-tier1-enrichment/`` package (offline-
verified first) and
``research/stage3/sl0027-wikidata-qualifier-semantics/`` package.

Covers the SLICE-0027 required-behavior 11 regression scenario: first import,
exact re-import/idempotency, offline readback/reproduction, and zero mutation
of canonical BoatModel/BoatDesign state — for the amended ("after") evidence
produced by the SLICE-0027-amended adapter default, which now recognizes the
evidence-backed P518/P3831 alternate qualifier carriers on top of the
existing accepted P642 path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def _quantity_claim(
    amount: str, unit_qid: str, qualifier_qid: str, *, qualifier_property: str = "P642"
) -> dict[str, Any]:
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
            qualifier_property: [
                {
                    "snaktype": "value",
                    "datavalue": {"type": "wikibase-entityid", "value": {"id": qualifier_qid}},
                }
            ]
        },
    }


@pytest.fixture()
def synthetic_sl0026_package(tmp_path: Path) -> Path:
    """Build a tiny (3-BoatModel) SLICE-0026-shaped selection + evidence
    manifest + artifact-digests package on disk, using the real SLICE-0026
    pure-logic builders — not hand-written JSON — so this fixture stays
    byte-compatible with the real schema/shape ``load_and_verify_retained_
    sl0026_package`` expects.

    Q9001 carries its displacement statement via the SLICE-0027-evidenced
    P3831 carrier (not P642) — the exact shape the amendment exists to
    recognize; the P642-only extraction SLICE-0026 originally captured
    therefore has zero usable evidence for Q9001, which is what this
    synthetic package's retained ``evidence_manifest.json`` must reflect.
    """
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        IdentityBoundary,
        build_artifact_digests,
        build_evidence_manifest_document,
        build_selection_document,
        filter_to_allowed_evidence,
        select_pilot_boatmodels,
        summarize_field_coverage,
    )
    from hullq.sources.wikidata import (
        QUALIFIER_CARRIER_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
        WikidataEntityData,
    )

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
        # Q9001: displacement carried only via the SLICE-0027-evidenced P3831
        # carrier — zero usable P642-only ("before") evidence.
        WikidataEntityData(
            qid="Q9001",
            label="Test Yacht 1",
            aliases=[],
            raw_claims={
                "P2067": [
                    _quantity_claim("+4500", "Q11570", "Q5636358", qualifier_property="P3831")
                ]
            },
        ),
        # Q9002: beam present (unaffected by the amendment either way).
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

    # The retained evidence_manifest.json must itself reflect the P642-only
    # ("SLICE-0026 as originally accepted") extraction, exactly like the real
    # retained package, so load_and_verify_retained_sl0026_package's pinned
    # QUALIFIER_CARRIER_VERSION_SLICE0008 re-extraction reproduces it.
    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (test@example.com)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        full_evidence, report = adapter.extract_field_evidence(
            entities,
            "2026-01-01T00:00:00Z",
            requested_qid_count=3,
            qualifier_carrier_version=QUALIFIER_CARRIER_VERSION_SLICE0008,
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

    package_dir = tmp_path / "sl0026-synthetic"
    package_dir.mkdir()
    (package_dir / "selection.json").write_text(json.dumps(selection_doc), encoding="utf-8")
    (package_dir / "evidence_manifest.json").write_text(json.dumps(evidence_doc), encoding="utf-8")
    digests_doc = build_artifact_digests(
        generated_at="2026-01-01T00:00:00Z", package_dir=package_dir
    )
    (package_dir / "ARTIFACT-DIGESTS.json").write_text(json.dumps(digests_doc), encoding="utf-8")

    return package_dir


def _synthetic_boundary() -> Any:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import IdentityBoundary

    return IdentityBoundary(
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


def test_persist_and_verify_first_import_readback_and_idempotent_reimport(
    db_url: str,
    clean_conn: Any,
    synthetic_sl0026_package: Path,
) -> None:
    from bootstrap.wikidata_sl0027_qualifier_semantics_correction_runner import persist_and_verify

    clean_conn.close()

    boundary = _synthetic_boundary()

    from hullq.bootstrap.wikidata_sl0027_qualifier_semantics_correction import (
        load_and_verify_retained_sl0026_package,
    )

    # Sanity: the synthetic package must itself offline-verify (pinned to the
    # SLICE-0026-original P642-only extraction) before persistence is exercised.
    pkg = load_and_verify_retained_sl0026_package(
        package_dir=synthetic_sl0026_package, boundary=boundary, expected_size=3
    )
    assert len(pkg.selection) == 3
    assert len(pkg.entities) == 3
    # Q9001's before-coverage has zero usable P642-only displacement evidence
    # (its statement is P3831-carried, not evidenced under SLICE-0008).
    assert (
        pkg.evidence_manifest["field_coverage"]["displacement"]["normalized_candidate_present"] == 0
    )

    result = persist_and_verify(
        db_url,
        schema_name="hullq_sl0027_test_first",
        sl0026_package_dir=synthetic_sl0026_package,
        sl0026_boundary=boundary,
        sl0026_expected_size=3,
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
    synthetic_sl0026_package: Path,
) -> None:
    """The isolated per-run schema is dropped on exit; the default schema
    used by clean_conn/a fresh connection must remain completely untouched —
    zero canonical rows and zero research-evidence rows leaked outside the
    isolated schema."""
    from bootstrap.wikidata_sl0027_qualifier_semantics_correction_runner import persist_and_verify

    clean_conn.close()

    persist_and_verify(
        db_url,
        schema_name="hullq_sl0027_test_isolation",
        sl0026_package_dir=synthetic_sl0026_package,
        sl0026_boundary=_synthetic_boundary(),
        sl0026_expected_size=3,
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
