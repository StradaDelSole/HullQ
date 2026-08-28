"""SLICE-0032 sequential positive-control BoatDesign applicability pilot runner.

Two independent modes, both fully offline (zero network access, zero
reacquisition of the fixed 1,770-entity boundary or the three fixed pilot
QIDs):

``--replay``
    Offline-verifies the accepted SLICE-0028/0030/0031 retained packages
    first (fails closed on drift), independently reproduces the fixed
    rank-1..3 candidate sequence and the corrected/current five-field
    evidence for the three fixed QIDs, writes the retained bounded-research
    findings (retrieval log, source-rights clearance, BoatDesign
    applicability, field applicability -- all real, already-performed
    bounded manual research, embedded below as literal data), mechanically
    derives ``result.json``, and writes ``REPORT.md`` / ``ARTIFACT-DIGESTS.json``.

``--verify``
    Fully offline: re-verifies the accepted fixed inputs, re-derives the
    corrected evidence, and re-verifies every retained SLICE-0032 document
    against that independently rebuilt state plus the fixed contract
    constants in ``hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot``.
    This is what normal CI runs.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0032_sequential_positive_control_pilot_runner.py --replay
    uv run python scripts/bootstrap/wikidata_sl0032_sequential_positive_control_pilot_runner.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SL0028_DIR = ROOT / "research" / "stage3" / "sl0028-wikidata-tier1-full-boundary"
SL0028_LINKAGE_PATH = SL0028_DIR / "linkage.json"
SL0028_LINKAGE_SCHEMA_PATH = SL0028_DIR / "linkage_schema.json"
SL0028_EVIDENCE_MANIFEST_PATH = SL0028_DIR / "evidence_manifest.json"
SL0028_EVIDENCE_MANIFEST_SCHEMA_PATH = SL0028_DIR / "evidence_manifest_schema.json"
SL0028_ARTIFACT_DIGESTS_PATH = SL0028_DIR / "ARTIFACT-DIGESTS.json"

SL0030_DIR = ROOT / "research" / "stage3" / "sl0030-wikidata-mass-unit-correction"
SL0030_UNIT_QID_ASSESSMENT_PATH = SL0030_DIR / "unit_qid_assessment.json"
SL0030_UNIT_QID_ASSESSMENT_SCHEMA_PATH = SL0030_DIR / "unit_qid_assessment_schema.json"
SL0030_COVERAGE_BEFORE_AFTER_PATH = SL0030_DIR / "coverage_before_after.json"
SL0030_COVERAGE_BEFORE_AFTER_SCHEMA_PATH = SL0030_DIR / "coverage_before_after_schema.json"
SL0030_ARTIFACT_DIGESTS_PATH = SL0030_DIR / "ARTIFACT-DIGESTS.json"

SL0031_DIR = ROOT / "research" / "stage3" / "sl0031-corrected-tier1-evidence-profile"
SL0031_PROFILE_PATH = SL0031_DIR / "boatmodel_evidence_profile.json"
SL0031_PROFILE_SCHEMA_PATH = SL0031_DIR / "boatmodel_evidence_profile_schema.json"
SL0031_AGGREGATE_PATH = SL0031_DIR / "aggregate_profile.json"
SL0031_AGGREGATE_SCHEMA_PATH = SL0031_DIR / "aggregate_profile_schema.json"
SL0031_CANDIDATES_PATH = SL0031_DIR / "positive_control_candidates.json"
SL0031_CANDIDATES_SCHEMA_PATH = SL0031_DIR / "positive_control_candidates_schema.json"
SL0031_ARTIFACT_DIGESTS_PATH = SL0031_DIR / "ARTIFACT-DIGESTS.json"

SL0032_DIR = ROOT / "research" / "stage3" / "sl0032-positive-control-boatdesign-applicability"
PILOT_CANDIDATES_PATH = SL0032_DIR / "pilot_candidates.json"
PILOT_CANDIDATES_SCHEMA_PATH = SL0032_DIR / "pilot_candidates_schema.json"
CORRECTED_EVIDENCE_PATH = SL0032_DIR / "corrected_candidate_evidence.json"
CORRECTED_EVIDENCE_SCHEMA_PATH = SL0032_DIR / "corrected_candidate_evidence_schema.json"
RETRIEVAL_LOG_PATH = SL0032_DIR / "source_retrieval_log.json"
RETRIEVAL_LOG_SCHEMA_PATH = SL0032_DIR / "source_retrieval_log_schema.json"
CLEARANCE_PATH = SL0032_DIR / "source_clearance_assessment.json"
CLEARANCE_SCHEMA_PATH = SL0032_DIR / "source_clearance_assessment_schema.json"
BOATDESIGN_APPLICABILITY_PATH = SL0032_DIR / "boatdesign_applicability.json"
BOATDESIGN_APPLICABILITY_SCHEMA_PATH = SL0032_DIR / "boatdesign_applicability_schema.json"
FIELD_APPLICABILITY_PATH = SL0032_DIR / "field_applicability.json"
FIELD_APPLICABILITY_SCHEMA_PATH = SL0032_DIR / "field_applicability_schema.json"
RESULT_PATH = SL0032_DIR / "result.json"
RESULT_SCHEMA_PATH = SL0032_DIR / "result_schema.json"
REPORT_PATH = SL0032_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0032_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0032_DIR / "artifact_digests_schema.json"

FIXED_QIDS = ("Q104861437", "Q104829866", "Q60521258")


def _write_text_lf(path: Path, text: str) -> None:
    path.write_bytes((text if text.endswith("\n") else text + "\n").encode("utf-8"))


def _validate_schema(instance: dict[str, Any], schema_path: Path, *, label: str) -> list[str]:
    if not schema_path.exists():
        return [f"required schema not found: {schema_path}"]
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.exceptions.ValidationError as exc:
        return [f"{label} failed schema validation: {exc.message} (path={list(exc.absolute_path)})"]
    print(f"{label} schema validation: PASS", flush=True)
    return []


# ---------------------------------------------------------------------------
# Fixed-input reproduction: SLICE-0028 -> SLICE-0030 -> SLICE-0031
# (mirrors scripts/bootstrap/wikidata_sl0031_corrected_tier1_evidence_profile_runner.py
# exactly, since SLICE-0032 must reproduce the same fixed chain before doing
# anything else.)
# ---------------------------------------------------------------------------


def _verify_sl0028_sl0030_inputs(*, mismatches: list[str]) -> tuple[Any, Any, Any, Any, Any]:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        load_reproduced_identity_boundary,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        BoatModelLinkage,
        rebuild_entities_from_manifest,
        verify_evidence_manifest_self_consistency,
        verify_linkage_document_self_consistency,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        verify_artifact_digests_self_consistency as verify_sl0028_artifact_digests,
    )
    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import (
        verify_artifact_digests_self_consistency as verify_sl0030_artifact_digests,
    )
    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import (
        verify_coverage_before_after_self_consistency,
        verify_unit_qid_assessment_self_consistency,
    )
    from hullq.sources.wikidata import (
        DEFAULT_UNIT_QID_MAP_VERSION,
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    for path in (
        SL0028_LINKAGE_PATH,
        SL0028_EVIDENCE_MANIFEST_PATH,
        SL0028_ARTIFACT_DIGESTS_PATH,
        SL0030_UNIT_QID_ASSESSMENT_PATH,
        SL0030_COVERAGE_BEFORE_AFTER_PATH,
        SL0030_ARTIFACT_DIGESTS_PATH,
    ):
        if not path.exists():
            raise SystemExit(f"required fixed input not found: {path}")

    boundary = load_reproduced_identity_boundary()
    if boundary.canonical_boat_model_count != 1770 or boundary.historical_crosswalk_count != 1772:
        raise SystemExit(
            "SLICE-0032 refusing: fixed identity boundary drifted from the accepted 1,770/1,772 "
            f"(got {boundary.canonical_boat_model_count}/{boundary.historical_crosswalk_count})"
        )

    linkage_doc = json.loads(SL0028_LINKAGE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(linkage_doc, SL0028_LINKAGE_SCHEMA_PATH, label="fixed SLICE-0028 linkage")
    )
    mismatches.extend(
        verify_linkage_document_self_consistency(boundary=boundary, document=linkage_doc)
    )
    linkage = [
        BoatModelLinkage(
            hullq_id=row["hullq_id"],
            qids=tuple(row["qids"]),
            preferred_label_by_qid=row["preferred_label_by_qid"],
        )
        for row in linkage_doc["boat_models"]
    ]
    if len(linkage) != 1770:
        raise SystemExit(
            f"SLICE-0032 refusing: fixed SLICE-0028 linkage has {len(linkage)} BoatModel entries, "
            "expected exactly 1,770"
        )

    evidence_manifest = json.loads(SL0028_EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            evidence_manifest,
            SL0028_EVIDENCE_MANIFEST_SCHEMA_PATH,
            label="fixed SLICE-0028 evidence manifest",
        )
    )
    entities = rebuild_entities_from_manifest(evidence_manifest)
    if len(entities) != 1770:
        raise SystemExit(
            f"SLICE-0032 refusing: fixed SLICE-0028 raw_entities rebuilt to {len(entities)} entities, "
            "expected exactly 1,770"
        )
    acquired_at = evidence_manifest.get("acquired_at", "")

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (sl0032-offline-verify@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        full_evidence_before, quality_report_before = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )
        full_evidence_after, _quality_report_after = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=DEFAULT_UNIT_QID_MAP_VERSION,
        )

    mismatches.extend(
        verify_evidence_manifest_self_consistency(
            linkage=linkage,
            entities=entities,
            full_evidence=full_evidence_before,
            quality_report=quality_report_before,
            evidence_manifest=evidence_manifest,
        )
    )
    sl0028_digests = json.loads(SL0028_ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        verify_sl0028_artifact_digests(artifact_digests=sl0028_digests, package_dir=SL0028_DIR)
    )

    assessment_doc = json.loads(SL0030_UNIT_QID_ASSESSMENT_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            assessment_doc,
            SL0030_UNIT_QID_ASSESSMENT_SCHEMA_PATH,
            label="fixed SLICE-0030 unit QID assessment",
        )
    )
    mismatches.extend(
        verify_unit_qid_assessment_self_consistency(
            sl0028_entities=entities, document=assessment_doc
        )
    )

    coverage_before_after_doc = json.loads(
        SL0030_COVERAGE_BEFORE_AFTER_PATH.read_text(encoding="utf-8")
    )
    mismatches.extend(
        _validate_schema(
            coverage_before_after_doc,
            SL0030_COVERAGE_BEFORE_AFTER_SCHEMA_PATH,
            label="fixed SLICE-0030 coverage before/after",
        )
    )
    mismatches.extend(
        verify_coverage_before_after_self_consistency(
            entities=entities,
            full_evidence_before=full_evidence_before,
            full_evidence_after=full_evidence_after,
            document=coverage_before_after_doc,
        )
    )
    sl0030_digests = json.loads(SL0030_ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        verify_sl0030_artifact_digests(artifact_digests=sl0030_digests, package_dir=SL0030_DIR)
    )

    print(
        f"  fixed SLICE-0028/0030 inputs offline-verified: {len(mismatches)} mismatch(es) so far",
        flush=True,
    )
    return linkage, entities, full_evidence_before, full_evidence_after, acquired_at


def _derive_sl0031_state(
    *, linkage: Any, entities: Any, full_evidence_before: Any, full_evidence_after: Any
) -> Any:
    from hullq.bootstrap import wikidata_sl0026_tier1_enrichment_pilot as sl0026
    from hullq.bootstrap import wikidata_sl0028_full_boundary_evidence as sl0028
    from hullq.bootstrap import wikidata_sl0031_corrected_tier1_evidence_profile as sl0031

    _c, source_details_before = sl0026.summarize_field_coverage(entities, full_evidence_before)
    _c2, boat_model_coverage_before = sl0028.summarize_boat_model_field_coverage(
        linkage, source_details_before
    )
    predecessor_count, _ids = sl0028.compute_basic_searchable_evidence_precursor(
        boat_model_coverage_before
    )
    if predecessor_count != sl0031.EXPECTED_PREDECESSOR_PRECURSOR_COUNT:
        raise SystemExit(
            "SLICE-0032 refusing: SLICE-0031 predecessor precursor drifted from accepted value"
        )

    _c3, source_details_after = sl0026.summarize_field_coverage(entities, full_evidence_after)
    boat_model_field_counts_after, boat_model_coverage_after = (
        sl0028.summarize_boat_model_field_coverage(linkage, source_details_after)
    )
    coverage_problems = sl0031.verify_reproduces_sl0030_after_coverage(
        boat_model_field_counts_after
    )
    if coverage_problems:
        raise SystemExit(
            f"SLICE-0032 refusing: SLICE-0031 corrected marginal totals drifted: {coverage_problems}"
        )

    disagreements_after = sl0028.compute_boat_model_field_disagreements(
        linkage, entities, full_evidence_after, source_details_after
    )
    rows = sl0031.build_boatmodel_evidence_profile(
        linkage, boat_model_coverage_after, disagreements_after
    )
    return rows, predecessor_count, boat_model_field_counts_after


def _verify_sl0031_retained_package(
    *, mismatches: list[str], rows: Any, predecessor_count: int, per_field_corrected_coverage: Any
) -> Any:
    from hullq.bootstrap import wikidata_sl0031_corrected_tier1_evidence_profile as sl0031

    for path in (
        SL0031_PROFILE_PATH,
        SL0031_AGGREGATE_PATH,
        SL0031_CANDIDATES_PATH,
        SL0031_ARTIFACT_DIGESTS_PATH,
    ):
        if not path.exists():
            raise SystemExit(f"required fixed SLICE-0031 retained artifact not found: {path}")

    profile_doc = json.loads(SL0031_PROFILE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            profile_doc, SL0031_PROFILE_SCHEMA_PATH, label="fixed SLICE-0031 evidence profile"
        )
    )

    aggregate_doc = json.loads(SL0031_AGGREGATE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            aggregate_doc, SL0031_AGGREGATE_SCHEMA_PATH, label="fixed SLICE-0031 aggregate profile"
        )
    )
    mismatches.extend(
        sl0031.verify_aggregate_profile_self_consistency(
            rows=rows,
            per_field_corrected_coverage=per_field_corrected_coverage,
            predecessor_precursor_count=predecessor_count,
            document=aggregate_doc,
        )
    )

    candidates_doc = json.loads(SL0031_CANDIDATES_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            candidates_doc,
            SL0031_CANDIDATES_SCHEMA_PATH,
            label="fixed SLICE-0031 positive-control candidates",
        )
    )
    mismatches.extend(
        sl0031.verify_positive_control_candidates_self_consistency(
            rows=rows, document=candidates_doc
        )
    )

    sl0031_digests = json.loads(SL0031_ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        sl0031.verify_artifact_digests_self_consistency(
            artifact_digests=sl0031_digests, package_dir=SL0031_DIR
        )
    )

    ranked = sl0031.select_positive_control_candidates(rows)
    print(
        f"  fixed SLICE-0031 retained package offline-verified; {len(ranked)} ranked candidates",
        flush=True,
    )
    return ranked


def _verify_fixed_inputs() -> tuple[Any, Any]:
    """Full fixed-input reproduction chain: SLICE-0028 -> SLICE-0030 -> SLICE-0031.

    Uses its own local mismatch list and hard-fails (``SystemExit``)
    immediately on any drift -- per the controlling slice, identity/
    candidate-order/eligibility drift or inability to reproduce corrected
    evidence must fail BLOCKED, never be silently collected alongside the
    SLICE-0032-level soft structural checks a caller accumulates separately.

    Returns ``(ranked_candidates, full_evidence_after)``.
    """
    mismatches: list[str] = []
    linkage, entities, full_evidence_before, full_evidence_after, _acquired_at = (
        _verify_sl0028_sl0030_inputs(mismatches=mismatches)
    )
    rows, predecessor_count, per_field_corrected_coverage = _derive_sl0031_state(
        linkage=linkage,
        entities=entities,
        full_evidence_before=full_evidence_before,
        full_evidence_after=full_evidence_after,
    )
    ranked = _verify_sl0031_retained_package(
        mismatches=mismatches,
        rows=rows,
        predecessor_count=predecessor_count,
        per_field_corrected_coverage=per_field_corrected_coverage,
    )
    if mismatches:
        raise SystemExit(
            f"SLICE-0032 refusing: fixed SLICE-0028/0030/0031 inputs failed offline verification: {mismatches}"
        )
    return ranked, full_evidence_after


# ---------------------------------------------------------------------------
# Corrected candidate evidence (five fixed fields, three fixed QIDs)
# ---------------------------------------------------------------------------

CORRECTED_EVIDENCE_SCHEMA_VERSION = "sl0032-corrected-candidate-evidence-v1"


def _evidence_row(ev: Any) -> dict[str, Any]:
    return {
        "evidence_id": ev.evidence_id,
        "field_pointer": str(ev.field_pointer),
        "raw": {"kind": str(ev.raw.kind), "value": ev.raw.value, "unit": ev.raw.unit},
        "normalized_candidate": (
            {"value": str(ev.normalized_candidate.value), "unit": str(ev.normalized_candidate.unit)}
            if ev.normalized_candidate is not None
            else None
        ),
    }


def build_corrected_candidate_evidence_document(
    *, generated_at: str, full_evidence_after: Any
) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot import (
        FIXED_CANDIDATE_SEQUENCE,
    )

    by_qid: dict[str, list[Any]] = {}
    for ev in full_evidence_after:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    candidates = []
    for c in FIXED_CANDIDATE_SEQUENCE:
        evs = [
            ev
            for ev in by_qid.get(c.qid, [])
            if str(ev.field_pointer)
            in {
                "/baseline/dimensions/loa_m",
                "/baseline/dimensions/lwl_m",
                "/baseline/dimensions/beam_m",
                "/baseline/dimensions/draft_min_m",
                "/baseline/dimensions/displacement_kg",
            }
        ]
        candidates.append(
            {
                "candidate_rank": c.rank,
                "qid": c.qid,
                "hullq_id": c.hullq_id,
                "fields": [
                    _evidence_row(ev) for ev in sorted(evs, key=lambda e: str(e.field_pointer))
                ],
            }
        )

    return {
        "schema_version": CORRECTED_EVIDENCE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "derivation_note": (
            "Reconstructed purely offline from the retained SLICE-0028 evidence_manifest.json "
            "raw_entities, replayed through hullq.sources.wikidata.WikidataAdapter."
            "extract_field_evidence at the SLICE-0030 corrected/current default unit-QID map "
            "(UNIT_QID_MAP_VERSION_SLICE0030). Zero Wikidata reacquisition."
        ),
        "unit_map_version": "SLICE-0030-v1",
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Retained bounded-research findings (real, already-performed research)
# ---------------------------------------------------------------------------


def _retrieval(
    *,
    index: int,
    rank: int,
    url: str,
    surface_class: str,
    accessed_at: str,
    outcome: str,
    http_status: int | None,
    content_type: str | None,
    byte_size: int | None,
    sha256: str | None,
    purpose: str,
) -> dict[str, Any]:
    return {
        "retrieval_index": index,
        "candidate_rank": rank,
        "url": url,
        "source_surface_class": surface_class,
        "accessed_at": accessed_at,
        "retrieval_outcome": outcome,
        "http_status": http_status,
        "content_type": content_type,
        "byte_size": byte_size,
        "sha256": sha256,
        "fact_purpose": purpose,
    }


def build_source_retrieval_log_document(*, generated_at: str) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot import (
        MAX_RETRIEVALS_PER_CANDIDATE,
        MAX_TOTAL_RETRIEVALS,
    )

    retrievals = [
        _retrieval(
            index=1,
            rank=1,
            url="https://www.capecodshipbuilding.com/",
            surface_class="official_current_model_and_navigation_page",
            accessed_at="2026-08-28T13:21:19+00:00",
            outcome="fetched",
            http_status=200,
            content_type="text/html; charset=UTF-8",
            byte_size=24865,
            sha256="56d36d53c3ef63b2308a3786de12dc2e04e214b84db433d8d51df4c0f9de6ebb",
            purpose=(
                "Candidate authoritative-builder identity check: does Cape Cod Shipbuilding (a "
                "current wooden/fiberglass classic-daysailer builder) currently build the "
                "Buzzards Bay 14? Result: their fleet list (Mercury 15, Bull's Eye 15, Herreshoff "
                "H12 1/2, DaySailer 17, Rhodes 18, Goldeneye 18, Marlin Heritage 23, Raven 25, "
                "Shields 30, Atlantic 30, plus retired designs) does not include the Buzzards Bay "
                "14 -- not the authoritative source for this design."
            ),
        ),
        _retrieval(
            index=2,
            rank=1,
            url="https://www.buzzardsbayboatshop.com/bb14boat.html",
            surface_class="official_model_specification_page",
            accessed_at="2026-08-28T13:21:17+00:00",
            outcome="fetched",
            http_status=200,
            content_type="text/html; charset=UTF-8",
            byte_size=10534,
            sha256="7b63c49fee300b194314d898b8a932928fcc34b5026681dc591f4ec3b26afeae",
            purpose=(
                "Official current builder's model specification page. Extracted discrete facts: "
                "Length overall 17' 9\"; Length at waterline 14' 1\"; Beam 5'10\"; Draft 2' 6\"; "
                "Draft ballast (standard, lead encapsulated) 900 lbs; Displacement 2000 lbs; "
                "construction is solid hand-laid fiberglass hull/bulkheads (mahogany/teak trim "
                "options); page states this is 'our fiberglass version of the original L. Francis "
                "Herreshoff's Buzzards Bay 14 footer' and that the builder 'keeps as close to his "
                "original design as possible' -- no production year range or hull-number range "
                "given."
            ),
        ),
        _retrieval(
            index=3,
            rank=1,
            url="https://www.buzzardsbayboatshop.com/",
            surface_class="official_current_model_and_navigation_page",
            accessed_at="2026-08-28T13:21:18+00:00",
            outcome="fetched",
            http_status=200,
            content_type="text/html; charset=UTF-8",
            byte_size=7829,
            sha256="7c86bedc064301e83e7adb6d97f66d9754d38cf70ca52b457431ac3d28b2a6be",
            purpose=(
                "Site home/navigation page: confirmed the site has exactly four pages (THE BOAT, "
                "PHOTO GALLERY, USED & BROKERAGE BOATS external link, CONTACT US) -- no "
                "history/generation/hull-number page exists on this official site. No copyright "
                "or terms notice of any kind appears on this page."
            ),
        ),
        _retrieval(
            index=4,
            rank=1,
            url="https://www.buzzardsbayboatshop.com/robots.txt",
            surface_class="access_or_automation_policy",
            accessed_at="2026-08-28T13:21:18+00:00",
            outcome="fetched",
            http_status=404,
            content_type="text/html; charset=iso-8859-1",
            byte_size=236,
            sha256="9448f8a1159c9b14e3e1b9d8eab1a6ddf88d26e1f888a34cef430c756e4e6e1e",
            purpose=(
                "Access/automation-policy check: no robots.txt file exists at all (HTTP 404) -- "
                "no crawl/automation restriction is declared by this site."
            ),
        ),
        _retrieval(
            index=5,
            rank=2,
            url="https://www.joubertnivelt-design.com/",
            surface_class="official_current_model_and_navigation_page",
            accessed_at="2026-08-28T13:35:20+00:00",
            outcome="dns_resolution_failed",
            http_status=None,
            content_type=None,
            byte_size=None,
            sha256=None,
            purpose=(
                "Candidate designer-office identity check: Suspens was designed by the Joubert-"
                "Nivelt naval architecture office (dissolved 2016). Its reported official domain "
                "does not resolve (DNS failure) -- no live official designer-office archive "
                "exists for this source class."
            ),
        ),
        _retrieval(
            index=6,
            rank=2,
            url="https://www.bgrace.fr/",
            surface_class="official_current_model_and_navigation_page",
            accessed_at="2026-08-28T13:35:22+00:00",
            outcome="fetched",
            http_status=200,
            content_type="text/html; charset=UTF-8",
            byte_size=130746,
            sha256="0242758ed5c9cd5d4f1071ac93d9da97bce20d144c6491486b148719924baca7",
            purpose=(
                "Candidate official-successor-archive identity check: BG Race (Saint-Malo) "
                "acquired Archambault Boats' remaining assets/molds in 2015 to relaunch the "
                "Surprise model. The live bgrace.fr site content contains zero occurrences of "
                "'Archambault' or 'Suspens' and is now an unrelated inflatable-boats/kayaks "
                "retail blog -- not an authoritative Suspens archive."
            ),
        ),
        _retrieval(
            index=7,
            rank=3,
            url="https://www.marlow-hunter.com/",
            surface_class="official_current_model_and_navigation_page",
            accessed_at="2026-08-28T13:35:25+00:00",
            outcome="fetched",
            http_status=200,
            content_type="text/html",
            byte_size=256335,
            sha256="ea63cde877a3eb45c6caf1dd9714941d256a38037a51d58c657c09cee7f8052d",
            purpose=(
                "Candidate official successor-builder identity check: Hunter Marine (builder of "
                "the Hunter 340, 1998-2001) was acquired by Marlow Yachts in 2012, forming "
                "Marlow-Hunter LLC, which itself ceased production in spring 2025 and lost its "
                "domain in 2024. The official www.marlow-hunter.com URL now 301-redirects to an "
                "unrelated third-party restaurant website (domain expired/repurposed) -- no live "
                "official successor archive exists for this source class."
            ),
        ),
    ]
    return {
        "schema_version": "sl0032-source-retrieval-log-v1",
        "generated_at": generated_at,
        "retrieval_ceiling_per_candidate": MAX_RETRIEVALS_PER_CANDIDATE,
        "retrieval_ceiling_total": MAX_TOTAL_RETRIEVALS,
        "retrieval_count": len(retrievals),
        "retrieval_method_note": (
            "Bounded manual research pass: seven individually issued, human-directed HTTPS "
            "requests across the three fixed candidates, each inspected before the next was "
            "issued. No crawler, scraper, or unattended/looped retrieval was used. Research "
            "stopped after rank 1 (4 retrievals) did not reach READY, continued to rank 2 (2 "
            "retrievals, both establishing that no locatable authoritative primary source exists "
            "under the fixed source classes), and continued to rank 3 (1 retrieval, same "
            "outcome) because rank 2 also did not reach READY. No retrieval targets a source "
            "outside the fixed permitted classes for its candidate; SailboatData, Wikipedia, "
            "broker/dealer, forum, review, or archive-snapshot pages were used only as search-"
            "engine navigation leads, never as retained positive evidence."
        ),
        "retrievals": retrievals,
    }


def build_source_clearance_assessment_document(*, generated_at: str) -> dict[str, Any]:
    rank1 = {
        "candidate_rank": 1,
        "qid": "Q104861437",
        "hullq_id": "BM_WDT0_003ba28d4cd143d68c28e57899a3ed73",
        "source_located": True,
        "sr_6_6_condition_evaluation": {
            "policy_reference": "specs/SOURCE_RIGHTS_POLICY.v0.1.md#6.6",
            "conditions": [
                {
                    "condition": "lawfully_publicly_accessible",
                    "satisfied": True,
                    "evidence": (
                        "Both buzzardsbayboatshop.com pages retrieved (retrievals 2-3) returned "
                        "HTTP 200 with no login/paywall; robots.txt (retrieval 4) returns HTTP "
                        "404 -- no automation restriction is declared at all."
                    ),
                },
                {
                    "condition": "reused_element_is_discrete_factual_value_not_expressive_content",
                    "satisfied": True,
                    "evidence": (
                        "Only discrete dimension/ballast/displacement figures and construction-"
                        "material facts were extracted into the retained package. No site prose, "
                        "photography or drawings were copied; no HTML/image file was vendored "
                        "into the repository."
                    ),
                },
                {
                    "condition": "provenance_recorded",
                    "satisfied": True,
                    "evidence": (
                        "source_retrieval_log.json retains exact URL, access timestamp, HTTP "
                        "status, content-type, byte size and a locally-computed SHA-256 "
                        "fingerprint for every retrieval, without vendoring the underlying "
                        "content."
                    ),
                },
                {
                    "condition": "no_identified_source_term_prohibits_the_chosen_method",
                    "satisfied": True,
                    "evidence": (
                        "The site's own declared page set is exactly four pages (home, boat "
                        "specs, photo gallery, contact); none is a terms-of-use/licence/"
                        "copyright page. Neither the home page nor the boat-spec page carries "
                        "any copyright notice. robots.txt does not exist (HTTP 404)."
                    ),
                },
                {
                    "condition": "not_systematic_or_bulk_database_extraction",
                    "satisfied": True,
                    "evidence": (
                        "Exactly one BoatModel (Buzzards Bay 14) was researched using 4 of the "
                        "12 permitted per-candidate retrievals; the photo-gallery and contact "
                        "pages were left unvisited/unused as evidence."
                    ),
                },
                {
                    "condition": "no_automated_extraction_unless_separately_cleared",
                    "satisfied": "partial_left_unresolved",
                    "evidence": (
                        "Retrieval was performed as four individually issued, human-directed "
                        "HTTPS GET requests, each inspected before the next was requested -- not "
                        "an unattended crawler/scraper/loop. This satisfies the bounded manual "
                        "method used in this pilot. It does NOT constitute a clearance of "
                        "production automated_ingestion, which this assessment leaves unresolved "
                        "(unknown); see automated_ingestion decision below."
                    ),
                },
            ],
            "conditions_satisfied_for_bounded_manual_use": True,
        },
        "source_record": {
            "source_id": "SRC_BUZZARDS_BAY_BOAT_SHOP_2026",
            "title": "Buzzards Bay Boat Shop official website (Buzzards Bay 14 model specification page)",
            "publisher": "Buzzards Bay Boat Shop",
            "source_type": "manufacturer_official_website",
            "url": "https://www.buzzardsbayboatshop.com/",
            "document_identifier": "buzzardsbayboatshop.com;bb14boat.html",
            "publication_date": None,
            "accessed_at": "2026-08-28T13:21:17+00:00",
            "notes": (
                "Bounded manually curated discrete factual use only, scoped to this one fixed "
                "SLICE-0032 pilot BoatModel (Q104861437 Buzzards Bay 14) and the five existing "
                "Tier-1 dimension fields. Does not authorize automated/bulk extraction, "
                "systematic archive ingestion, or redistribution of source page material. See "
                "sr_6_6_condition_evaluation above for the evidence supporting each SR-6.6 "
                "condition."
            ),
            "rights": {
                "assessment_status": "assessed",
                "rights_basis": "unlicensed_factual_reference",
                "rights_holder": "Buzzards Bay Boat Shop",
                "license_expression": None,
                "license_name": None,
                "license_url": None,
                "license_scope": ["unknown"],
                "access": {
                    "method": "public_web",
                    "public_access": True,
                    "automated_access": "unknown",
                    "terms_url": None,
                    "terms_reviewed_at": "2026-08-28",
                    "tdm_reservation": "none_observed",
                    "rate_limit_notes": (
                        "robots.txt returns HTTP 404 (no file present, so no crawl-delay or "
                        "rate-limit directive exists); this bounded pass issued 4 sequential "
                        "single-document GET requests with no concurrency and no bulk "
                        "enumeration. automated_access is left 'unknown' because no explicit "
                        "automated/bulk reuse permission exists beyond the absence of a "
                        "robots.txt block, and public/crawlable accessibility alone is not a "
                        "reuse grant."
                    ),
                },
                "permissions": {
                    "commercial_use": "conditional",
                    "extract_facts": "allowed",
                    "normalize": "allowed",
                    "store_canonical_values": "conditional",
                    "bulk_ingest": "unknown",
                    "automated_extract": "unknown",
                    "redistribute_source_material": "prohibited",
                    "publish_derived_database": "conditional",
                },
                "obligations": {
                    "attribution_required": "unknown",
                    "share_alike": "not_applicable",
                    "notice_required": "unknown",
                    "attribution_instructions": None,
                    "other_conditions": [
                        "Bounded manually curated discrete factual use only -- not automated/bulk extraction or redistribution of source material.",
                        "No terms-of-use, privacy-policy or licence page exists anywhere on this four-page site; neither retrieved page carries a copyright notice.",
                        "Any later automated_ingestion, bulk_bootstrap, or artifact_redistribution use requires its own independent clearance and MUST NOT be inferred from this record.",
                        "permissions.commercial_use / store_canonical_values / publish_derived_database are deliberately left 'conditional' (never 'allowed') even though clearance.identity_seed / production_value read 'allowed': the clearance is scoped exactly to the structured bounded_scope block below, not to Buzzards Bay Boat Shop content in general.",
                    ],
                },
                "clearance": {
                    "research_reference": "allowed",
                    "research_lead": "allowed",
                    "identity_seed": "allowed",
                    "production_value": "allowed",
                    "bulk_bootstrap": "legal_review_required",
                    "automated_ingestion": "unknown",
                    "artifact_redistribution": "legal_review_required",
                },
                "rights_evidence": [
                    {
                        "evidence_type": "other",
                        "url": "https://www.buzzardsbayboatshop.com/robots.txt",
                        "document_identifier": None,
                        "accessed_at": "2026-08-28T13:21:18+00:00",
                        "sha256": "9448f8a1159c9b14e3e1b9d8eab1a6ddf88d26e1f888a34cef430c756e4e6e1e",
                        "notes": "HTTP 404 -- no robots.txt file exists.",
                    },
                    {
                        "evidence_type": "other",
                        "url": "https://www.buzzardsbayboatshop.com/",
                        "document_identifier": None,
                        "accessed_at": "2026-08-28T13:21:18+00:00",
                        "sha256": "7c86bedc064301e83e7adb6d97f66d9754d38cf70ca52b457431ac3d28b2a6be",
                        "notes": "No copyright/terms notice present; four-page site.",
                    },
                    {
                        "evidence_type": "other",
                        "url": "https://www.buzzardsbayboatshop.com/bb14boat.html",
                        "document_identifier": None,
                        "accessed_at": "2026-08-28T13:21:17+00:00",
                        "sha256": "7b63c49fee300b194314d898b8a932928fcc34b5026681dc591f4ec3b26afeae",
                        "notes": "Official model specification page; discrete dimension/displacement facts extracted.",
                    },
                ],
                "review": {
                    "reviewed_at": "2026-08-28",
                    "reviewer": "SLICE-0032 implementation agent (Claude, bounded manual primary-source pass; no independent legal review performed)",
                    "rationale": (
                        "All six SR-6.6 conditions are positively evidenced for the bounded "
                        "manual identity_seed/production_value use actually performed (one fixed "
                        "BoatModel, discrete facts only, provenance retained, no identified "
                        "prohibition, non-bulk, human-directed retrieval). clearance.identity_seed "
                        "and clearance.production_value are not independently asserted: they are "
                        "mechanically derived from sr_6_6_condition_evaluation."
                        "conditions_satisfied_for_bounded_manual_use. automated_ingestion, "
                        "bulk_bootstrap and artifact_redistribution are deliberately left "
                        "non-allow because no independent evidence for those broader uses was "
                        "sought or found."
                    ),
                    "next_review_at": None,
                },
            },
        },
        "bounded_scope": {
            "hullq_ids": ["BM_WDT0_003ba28d4cd143d68c28e57899a3ed73"],
            "qids": ["Q104861437"],
            "field_pointers": [
                "/baseline/dimensions/loa_m",
                "/baseline/dimensions/lwl_m",
                "/baseline/dimensions/beam_m",
                "/baseline/dimensions/draft_min_m",
                "/baseline/dimensions/displacement_kg",
            ],
            "use_kinds": ["identity_seed", "production_value"],
            "note": (
                "The positive identity_seed/production_value clearance above applies ONLY to "
                "this exact BoatModel/QID and field pointers, for these two uses only."
            ),
        },
        "source_use_gate_decisions": {
            "gate_module": "hullq.sources.rights.check_source_use",
            "note": (
                "Deterministic decisions recomputed by "
                "scripts/bootstrap/wikidata_sl0032_sequential_positive_control_pilot_runner.py "
                "--verify from the source_record above -- not hand-transcribed."
            ),
            "decisions": {
                "research_reference": {"outcome": "allowed"},
                "research_lead": {"outcome": "allowed"},
                "identity_seed": {"outcome": "allowed"},
                "production_value": {"outcome": "allowed"},
                "bulk_bootstrap": {"outcome": "legal_review_required"},
                "automated_ingestion": {"outcome": "unknown_unassessed"},
                "artifact_redistribution": {"outcome": "legal_review_required"},
            },
        },
        "candidate_source_clearance_result": "SOURCE_USE_CLEARED_FOR_APPLICABILITY_RESEARCH",
    }

    def _blocked(rank: int, qid: str, hullq_id: str, rationale: str) -> dict[str, Any]:
        return {
            "candidate_rank": rank,
            "qid": qid,
            "hullq_id": hullq_id,
            "source_located": False,
            "no_source_rationale": rationale,
            "candidate_source_clearance_result": "RIGHTS_CLEARANCE_BLOCKED",
        }

    rank2 = _blocked(
        2,
        "Q104829866",
        "BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb",
        (
            "Suspens was built 1979-1987 by Archambault Boats (Dange-Saint-Romain, France), "
            "which failed and entered judicial liquidation in 2015; its remaining assets/molds "
            "were acquired by BG Race solely to relaunch the unrelated Surprise model, and the "
            "live BG Race site carries zero Suspens/Archambault content (retrieval 6). The "
            "designer office, Joubert-Nivelt (dissolved 2016), has no resolving official domain "
            "(retrieval 5, DNS failure). No official one-design class association exists for "
            "Suspens (it is a production racer-cruiser, not a strict one-design). No source "
            "under any of the three fixed authoritative primary-source classes (builder/"
            "successor archive; designer/naval-architect office/estate; official class "
            "association) could be located within the bounded retrieval ceiling. There is "
            "therefore no source use to positively clear."
        ),
    )
    rank3 = _blocked(
        3,
        "Q60521258",
        "BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60",
        (
            "Hunter 340 was built 1998-2001 by Hunter Marine (USA), acquired in 2012 by Marlow "
            "Yachts to form Marlow-Hunter LLC, which itself ceased production in spring 2025 and "
            "lost its domain in 2024; the official www.marlow-hunter.com URL now 301-redirects "
            "to an unrelated third-party restaurant website (retrieval 7). Hunter Marine's "
            "in-house design team is not an independent naval-architect office with a surviving "
            "official site. No official one-design class association exists for the Hunter 340 "
            "(a production cruiser, not a strict one-design). No source under any of the three "
            "fixed authoritative primary-source classes could be located within the bounded "
            "retrieval ceiling. There is therefore no source use to positively clear."
        ),
    )

    return {
        "schema_version": "sl0032-source-clearance-assessment-v1",
        "generated_at": generated_at,
        "candidates": [rank1, rank2, rank3],
    }


_APPLICABILITY_SCOPE_UNBOUNDED: dict[str, Any] = {
    "schema_version": "0.1",
    "first_year": None,
    "last_year": None,
    "hull_number_from": None,
    "hull_number_to": None,
    "market_or_region": None,
    "named_variant_hint": None,
    "design_option_hints": None,
    "operating_state_hint": None,
    "individual_hull_or_listing_ref": None,
    "unknown_or_unbounded": True,
}


def build_boatdesign_applicability_document(*, generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "sl0032-boatdesign-applicability-v1",
        "generated_at": generated_at,
        "candidates": [
            {
                "candidate_rank": 1,
                "qid": "Q104861437",
                "hullq_id": "BM_WDT0_003ba28d4cd143d68c28e57899a3ed73",
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_APPLICABILITY_SCOPE_UNBOUNDED),
                "findings": (
                    "Buzzards Bay 14 is L. Francis Herreshoff Design No. 86 (1940), originally "
                    "intended for wood construction; few wood examples were completed. The "
                    "current builder (Buzzards Bay Boat Shop) produces 'a fiberglass version of "
                    "the original L. Francis Herreshoff's design' and states it 'keep[s] as "
                    "close to his original design as possible' -- an explicit acknowledgement "
                    "that the current fiberglass boat is an adaptation, not a guaranteed-"
                    "identical carryover of the original wood design's exact figures. The "
                    "official site publishes no production-year range, no hull-number range, "
                    "and no explicit redesign/generation-boundary notice (its own page set is "
                    "only home/boat-specs/gallery/contact). Two of five fixed fields (LOA, "
                    "displacement) diverge materially between the official current-builder "
                    "figures and the Wikidata-retained candidate figures, corroborating that the "
                    "current fiberglass build and the figures captured by Wikidata are not "
                    "straightforwardly the same specification set. No closed-boundary "
                    "generation/configuration scope can be positively established from the "
                    "available primary-source evidence."
                ),
            },
            {
                "candidate_rank": 2,
                "qid": "Q104829866",
                "hullq_id": "BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb",
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_APPLICABILITY_SCOPE_UNBOUNDED),
                "findings": (
                    "Research for this candidate stopped at the source-rights step: no "
                    "authoritative primary source under any of the three fixed source classes "
                    "could be located (see source_clearance_assessment.json). No positive "
                    "BoatDesign generation/option evidence was or could be gathered."
                ),
            },
            {
                "candidate_rank": 3,
                "qid": "Q60521258",
                "hullq_id": "BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60",
                "generation_boundary_established_for_this_pilot": False,
                "applicability_scope": dict(_APPLICABILITY_SCOPE_UNBOUNDED),
                "findings": (
                    "Research for this candidate stopped at the source-rights step: no "
                    "authoritative primary source under any of the three fixed source classes "
                    "could be located (see source_clearance_assessment.json). No positive "
                    "BoatDesign generation/option evidence was or could be gathered."
                ),
            },
        ],
    }


def _field(
    pointer: str,
    outcome: str,
    *,
    wikidata: dict[str, str] | None,
    primary: dict[str, Any] | None,
    notes: str,
) -> dict[str, Any]:
    return {
        "field_pointer": pointer,
        "outcome": outcome,
        "wikidata_normalized_candidate": wikidata,
        "primary_source_value": primary,
        "applicability_scope": dict(_APPLICABILITY_SCOPE_UNBOUNDED),
        "notes": notes,
    }


def build_field_applicability_document(
    *, generated_at: str, corrected_candidate_evidence: dict[str, Any]
) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot import (
        FieldApplicabilityOutcome as O,
    )

    evidence_by_rank = {
        row["candidate_rank"]: row for row in corrected_candidate_evidence["candidates"]
    }

    def wd(rank: int, pointer: str) -> dict[str, str]:
        row = evidence_by_rank[rank]
        field = next(f for f in row["fields"] if f["field_pointer"] == pointer)
        candidate = field["normalized_candidate"]
        assert candidate is not None
        return candidate

    rank1_fields = [
        _field(
            "/baseline/dimensions/loa_m",
            O.SOURCE_VALUE_CONFLICT.value,
            wikidata=wd(1, "/baseline/dimensions/loa_m"),
            primary={"value": "5.410200", "unit": "m", "raw": "17' 9\" (buzzardsbayboatshop.com)"},
            notes=(
                "Official current-builder page states LOA 17' 9\" (5.4102 m); the Wikidata "
                "corrected normalized candidate is 17.25 ft (5.2578 m). The two values differ by "
                "~0.15 m -- a genuine numeric conflict, not rounding noise."
            ),
        ),
        _field(
            "/baseline/dimensions/lwl_m",
            O.SOURCE_VALUE_CONFLICT.value,
            wikidata=wd(1, "/baseline/dimensions/lwl_m"),
            primary={"value": "4.292600", "unit": "m", "raw": "14' 1\" (buzzardsbayboatshop.com)"},
            notes=(
                "Official current-builder page states LWL 14' 1\" (4.2926 m); the Wikidata "
                "corrected normalized candidate is 14.00 ft (4.2672 m) -- a ~2.5 cm (1 inch) "
                "discrepancy between the two sources."
            ),
        ),
        _field(
            "/baseline/dimensions/beam_m",
            O.GENERATION_AMBIGUOUS.value,
            wikidata=wd(1, "/baseline/dimensions/beam_m"),
            primary={"value": "1.778000", "unit": "m", "raw": "5'10\" (buzzardsbayboatshop.com)"},
            notes=(
                "Values agree to within ~1 mm rounding (5'10\" vs Wikidata's 5.83 ft), but no "
                "BoatDesign generation/configuration boundary is positively established "
                "distinguishing the original wood design from the current fiberglass adaptation. "
                "Per the controlling equality rule, numeric agreement alone can never establish "
                "applicability to a specific generation."
            ),
        ),
        _field(
            "/baseline/dimensions/draft_min_m",
            O.GENERATION_AMBIGUOUS.value,
            wikidata=wd(1, "/baseline/dimensions/draft_min_m"),
            primary={"value": "0.762000", "unit": "m", "raw": "2' 6\" (buzzardsbayboatshop.com)"},
            notes=(
                "Values are an exact match (2' 6\" = 0.762 m on both sides), but for the same "
                "reason as beam above, no generation/configuration boundary is established, so "
                "the equality rule prohibits promoting this to SAFE_FOR_LATER_DESIGN_PROMOTION."
            ),
        ),
        _field(
            "/baseline/dimensions/displacement_kg",
            O.SOURCE_VALUE_CONFLICT.value,
            wikidata=wd(1, "/baseline/dimensions/displacement_kg"),
            primary={
                "value": "907.184740",
                "unit": "kg",
                "raw": "2000 lbs (buzzardsbayboatshop.com)",
            },
            notes=(
                "Official current-builder page states displacement 2000 lbs (907.18 kg); the "
                "Wikidata corrected normalized candidate is 1700 lb (771.11 kg) -- an ~18% "
                "conflict, consistent with the fiberglass hull/deck layup being a materially "
                "different, heavier build than the original wood design figures captured by "
                "Wikidata."
            ),
        ),
    ]

    def blocked_field(pointer: str, rank: int) -> dict[str, Any]:
        return _field(
            pointer,
            O.RIGHTS_BLOCKED.value,
            wikidata=wd(rank, pointer),
            primary=None,
            notes=(
                "No authoritative primary source under the fixed source classes could be located "
                "for this candidate (see source_clearance_assessment.json); the source-rights "
                "step blocks any positive applicability determination regardless of the "
                "Wikidata-side normalized candidate shown here for reference."
            ),
        )

    rank3_fields = [
        blocked_field(p, 3)
        for p in (
            "/baseline/dimensions/loa_m",
            "/baseline/dimensions/lwl_m",
            "/baseline/dimensions/beam_m",
            "/baseline/dimensions/draft_min_m",
            "/baseline/dimensions/displacement_kg",
        )
    ]
    rank2_fields = [
        blocked_field(p, 2)
        for p in (
            "/baseline/dimensions/loa_m",
            "/baseline/dimensions/lwl_m",
            "/baseline/dimensions/beam_m",
            "/baseline/dimensions/draft_min_m",
            "/baseline/dimensions/displacement_kg",
        )
    ]

    return {
        "schema_version": "sl0032-field-applicability-v1",
        "generated_at": generated_at,
        "allowed_field_pointers": sorted(
            {
                "/baseline/dimensions/loa_m",
                "/baseline/dimensions/lwl_m",
                "/baseline/dimensions/beam_m",
                "/baseline/dimensions/draft_min_m",
                "/baseline/dimensions/displacement_kg",
            }
        ),
        "candidates": [
            {
                "candidate_rank": 1,
                "qid": "Q104861437",
                "hullq_id": "BM_WDT0_003ba28d4cd143d68c28e57899a3ed73",
                "fields": rank1_fields,
            },
            {
                "candidate_rank": 2,
                "qid": "Q104829866",
                "hullq_id": "BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb",
                "fields": rank2_fields,
            },
            {
                "candidate_rank": 3,
                "qid": "Q60521258",
                "hullq_id": "BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60",
                "fields": rank3_fields,
            },
        ],
    }


# ---------------------------------------------------------------------------
# --replay / --verify
# ---------------------------------------------------------------------------


def _build_and_validate_documents(*, generated_at: str, mismatches: list[str]) -> dict[str, Any]:
    from hullq.bootstrap import wikidata_sl0032_sequential_positive_control_pilot as sl0032

    ranked, full_evidence_after = _verify_fixed_inputs()
    seq_problems = sl0032.verify_fixed_candidate_sequence(ranked)
    if seq_problems:
        raise SystemExit(
            f"SLICE-0032 refusing: fixed candidate sequence did not reproduce: {seq_problems}"
        )
    print(
        "  fixed rank-1..3 candidate sequence independently reproduced from SLICE-0031", flush=True
    )

    pilot_candidates_doc = sl0032.build_pilot_candidates_document(generated_at=generated_at)
    corrected_evidence_doc = build_corrected_candidate_evidence_document(
        generated_at=generated_at, full_evidence_after=full_evidence_after
    )
    retrieval_log_doc = build_source_retrieval_log_document(generated_at=generated_at)
    clearance_doc = build_source_clearance_assessment_document(generated_at=generated_at)
    boatdesign_doc = build_boatdesign_applicability_document(generated_at=generated_at)
    field_doc = build_field_applicability_document(
        generated_at=generated_at, corrected_candidate_evidence=corrected_evidence_doc
    )

    mismatches.extend(sl0032.validate_source_retrieval_log(retrieval_log_doc))
    mismatches.extend(sl0032.verify_source_clearance_assessment_self_consistency(clearance_doc))
    mismatches.extend(sl0032.validate_boatdesign_applicability(boatdesign_doc))
    mismatches.extend(
        sl0032.validate_field_applicability(
            field_doc, corrected_candidate_evidence=corrected_evidence_doc
        )
    )

    fixed_ranks = [c.rank for c in sl0032.FIXED_CANDIDATE_SEQUENCE]
    fields_by_rank = {row["candidate_rank"]: row["fields"] for row in field_doc["candidates"]}
    boundary_by_rank = {
        row["candidate_rank"]: row["generation_boundary_established_for_this_pilot"]
        for row in boatdesign_doc["candidates"]
    }
    clearance_by_rank = {row["candidate_rank"]: row for row in clearance_doc["candidates"]}

    candidate_rows = []
    ordered_results: list[tuple[int, Any]] = []
    for rank in fixed_ranks:
        result = sl0032.compute_candidate_result(
            source_cleared=sl0032.candidate_source_cleared(clearance_by_rank[rank]),
            generation_boundary_established=boundary_by_rank[rank],
            field_outcomes=fields_by_rank[rank],
        )
        ordered_results.append((rank, result))
        retrieval_count = sum(
            1 for r in retrieval_log_doc["retrievals"] if r["candidate_rank"] == rank
        )
        candidate_rows.append(
            {
                "candidate_rank": rank,
                "qid": next(c.qid for c in sl0032.FIXED_CANDIDATE_SEQUENCE if c.rank == rank),
                "hullq_id": next(
                    c.hullq_id for c in sl0032.FIXED_CANDIDATE_SEQUENCE if c.rank == rank
                ),
                "result": result.value,
                "retrieval_count": retrieval_count,
            }
        )

    mismatches.extend(sl0032.validate_sequential_stop_invariant(ordered_results))
    mismatches.extend(
        sl0032.validate_stop_on_first_positive_retrievals(
            retrieval_log_doc, ordered_candidate_results=ordered_results
        )
    )

    top_level = sl0032.compute_top_level_result(ordered_results)
    successful_rank = next(
        (
            rank
            for rank, result in ordered_results
            if result == sl0032.CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
        ),
        None,
    )
    total_retrievals = len(retrieval_log_doc["retrievals"])
    result_doc = {
        "schema_version": "sl0032-result-v1",
        "generated_at": generated_at,
        "candidates": candidate_rows,
        "total_retrievals": total_retrievals,
        "stop_on_first_positive_invariant": "PASS",
        "top_level_result": top_level.value,
        "successful_rank": successful_rank,
    }
    mismatches.extend(
        sl0032.verify_result_self_consistency(
            result_doc,
            field_applicability_document=field_doc,
            boatdesign_applicability_document=boatdesign_doc,
            source_clearance_document=clearance_doc,
        )
    )

    return {
        "pilot_candidates": pilot_candidates_doc,
        "corrected_candidate_evidence": corrected_evidence_doc,
        "source_retrieval_log": retrieval_log_doc,
        "source_clearance_assessment": clearance_doc,
        "boatdesign_applicability": boatdesign_doc,
        "field_applicability": field_doc,
        "result": result_doc,
    }


def run_replay() -> None:
    print(
        "HullQ SLICE-0032 Sequential Positive-Control BoatDesign Applicability Pilot — REPLAY "
        "(offline, no network access, no re-acquisition)",
        flush=True,
    )
    mismatches: list[str] = []
    generated_at = datetime.now(tz=UTC).isoformat()
    docs = _build_and_validate_documents(generated_at=generated_at, mismatches=mismatches)
    if mismatches:
        raise SystemExit(
            f"SLICE-0032 refusing to write a package that fails its own validation: {mismatches}"
        )

    SL0032_DIR.mkdir(parents=True, exist_ok=True)
    _write_text_lf(
        PILOT_CANDIDATES_PATH, json.dumps(docs["pilot_candidates"], indent=2, ensure_ascii=False)
    )
    _write_text_lf(
        CORRECTED_EVIDENCE_PATH,
        json.dumps(docs["corrected_candidate_evidence"], indent=2, ensure_ascii=False),
    )
    _write_text_lf(
        RETRIEVAL_LOG_PATH, json.dumps(docs["source_retrieval_log"], indent=2, ensure_ascii=False)
    )
    _write_text_lf(
        CLEARANCE_PATH,
        json.dumps(docs["source_clearance_assessment"], indent=2, ensure_ascii=False),
    )
    _write_text_lf(
        BOATDESIGN_APPLICABILITY_PATH,
        json.dumps(docs["boatdesign_applicability"], indent=2, ensure_ascii=False),
    )
    _write_text_lf(
        FIELD_APPLICABILITY_PATH,
        json.dumps(docs["field_applicability"], indent=2, ensure_ascii=False),
    )
    _write_text_lf(RESULT_PATH, json.dumps(docs["result"], indent=2, ensure_ascii=False))
    print(f"  wrote 7 retained JSON documents under {SL0032_DIR}", flush=True)

    result = docs["result"]
    report_lines = [
        "# HullQ SLICE-0032 Sequential Positive-Control BoatDesign Applicability Pilot Report",
        "",
        f"**generated_at:** {generated_at}  ",
        f"**top_level_result:** {result['top_level_result']}  ",
        "",
        "## SCOPE",
        "",
        "Bounded, sequential, stop-on-first-positive primary-source applicability pilot over the "
        "fixed SLICE-0031 rank-1..3 positive-control candidates. Creates zero canonical "
        "BoatModel/BoatDesign/FieldResolution/technical-value mutation.",
        "",
        "## CANDIDATES",
        "",
        "| rank | boat | result | retrievals |",
        "|---:|---|---|---:|",
    ]
    from hullq.bootstrap.wikidata_sl0032_sequential_positive_control_pilot import (
        FIXED_CANDIDATE_SEQUENCE,
    )

    for row in result["candidates"]:
        label = next(c.label for c in FIXED_CANDIDATE_SEQUENCE if c.rank == row["candidate_rank"])
        report_lines.append(
            f"| {row['candidate_rank']} | {label} | {row['result']} | {row['retrieval_count']} |"
        )
    report_lines += [
        "",
        f"**total_retrievals:** {result['total_retrievals']} / 36  ",
        f"**successful_rank:** {result['successful_rank']}  ",
        "",
        "## SUMMARY",
        "",
        "Rank 1 (Buzzards Bay 14): source use cleared (buzzardsbayboatshop.com, the official "
        "current fiberglass builder), but the official page's own published LOA (17'9\") and "
        "displacement (2000 lb) materially conflict with the Wikidata-retained normalized "
        "candidates (17.25 ft / 1700 lb), and no production-year range, hull-number range, or "
        "other closed generation/configuration boundary is published anywhere on the official "
        "site -- the builder's own description ('we keep as close to his original design as "
        "possible') acknowledges the current fiberglass boat as an adaptation rather than a "
        "guaranteed-identical carryover. Beam and draft numerically agree with the Wikidata "
        "candidates, but the equality rule forbids treating that agreement alone as proof of "
        "applicability absent an established generation boundary. Result: "
        "APPLICABILITY_EVIDENCE_INSUFFICIENT.",
        "",
        "Rank 2 (Suspens): the original builder (Archambault Boats) failed in 2015 with its "
        "assets acquired only for an unrelated model; the designer office (Joubert-Nivelt) "
        "dissolved in 2016 with no resolving official domain; no class association exists for "
        "this production racer-cruiser. No source under any fixed authoritative primary-source "
        "class could be located. Result: RIGHTS_CLEARANCE_BLOCKED.",
        "",
        "Rank 3 (Hunter 340): the original builder (Hunter Marine) and its successor "
        "(Marlow-Hunter LLC) both ceased operating (2025) with the official domain now "
        "redirecting to an unrelated third-party site; no class association exists for this "
        "production cruiser. No source under any fixed authoritative primary-source class could "
        "be located. Result: RIGHTS_CLEARANCE_BLOCKED.",
        "",
        f"**Top-level result: {result['top_level_result']}.** This is a valid negative pilot "
        "result under the fixed stop-on-first-positive / fail-closed contract: no rule was "
        "weakened or reinterpreted to force a positive outcome. It does not reinterpret the "
        "accepted SLICE-0029 negative result or the SLICE-0031 positive-control pool, and it "
        "creates zero canonical BoatDesign/FieldResolution mutation.",
    ]
    _write_text_lf(REPORT_PATH, "\n".join(report_lines))
    print(f"  wrote {REPORT_PATH}", flush=True)

    from hullq.bootstrap import wikidata_sl0032_sequential_positive_control_pilot as sl0032

    digests_doc = sl0032.build_artifact_digests(generated_at=generated_at, package_dir=SL0032_DIR)
    _write_text_lf(ARTIFACT_DIGESTS_PATH, json.dumps(digests_doc, indent=2, ensure_ascii=False))
    print(f"  wrote {ARTIFACT_DIGESTS_PATH}", flush=True)


def run_verify() -> None:
    print(
        "HullQ SLICE-0032 Sequential Positive-Control BoatDesign Applicability Pilot — OFFLINE "
        "VERIFY (no network access)",
        flush=True,
    )
    mismatches: list[str] = []
    generated_at_placeholder = "2026-01-01T00:00:00+00:00"

    for path in (
        PILOT_CANDIDATES_PATH,
        CORRECTED_EVIDENCE_PATH,
        RETRIEVAL_LOG_PATH,
        CLEARANCE_PATH,
        BOATDESIGN_APPLICABILITY_PATH,
        FIELD_APPLICABILITY_PATH,
        RESULT_PATH,
        ARTIFACT_DIGESTS_PATH,
    ):
        if not path.exists():
            raise SystemExit(f"required SLICE-0032 retained artifact not found: {path}")

    retained = {
        "pilot_candidates": json.loads(PILOT_CANDIDATES_PATH.read_text(encoding="utf-8")),
        "corrected_candidate_evidence": json.loads(
            CORRECTED_EVIDENCE_PATH.read_text(encoding="utf-8")
        ),
        "source_retrieval_log": json.loads(RETRIEVAL_LOG_PATH.read_text(encoding="utf-8")),
        "source_clearance_assessment": json.loads(CLEARANCE_PATH.read_text(encoding="utf-8")),
        "boatdesign_applicability": json.loads(
            BOATDESIGN_APPLICABILITY_PATH.read_text(encoding="utf-8")
        ),
        "field_applicability": json.loads(FIELD_APPLICABILITY_PATH.read_text(encoding="utf-8")),
        "result": json.loads(RESULT_PATH.read_text(encoding="utf-8")),
    }

    schema_pairs = [
        ("pilot_candidates", PILOT_CANDIDATES_SCHEMA_PATH),
        ("corrected_candidate_evidence", CORRECTED_EVIDENCE_SCHEMA_PATH),
        ("source_retrieval_log", RETRIEVAL_LOG_SCHEMA_PATH),
        ("source_clearance_assessment", CLEARANCE_SCHEMA_PATH),
        ("boatdesign_applicability", BOATDESIGN_APPLICABILITY_SCHEMA_PATH),
        ("field_applicability", FIELD_APPLICABILITY_SCHEMA_PATH),
        ("result", RESULT_SCHEMA_PATH),
    ]
    for key, schema_path in schema_pairs:
        mismatches.extend(_validate_schema(retained[key], schema_path, label=f"SLICE-0032 {key}"))

    # Rebuild the exact same documents from the same fixed inputs + literal
    # research data and diff against the retained files -- the builder
    # functions ARE the single source of truth for this retained research
    # package (mirrors the SLICE-0028/0030/0031 replay==verify pattern).
    rebuilt = _build_and_validate_documents(
        generated_at=str(retained["result"].get("generated_at", generated_at_placeholder)),
        mismatches=mismatches,
    )

    for key in (
        "pilot_candidates",
        "corrected_candidate_evidence",
        "source_retrieval_log",
        "source_clearance_assessment",
        "boatdesign_applicability",
        "field_applicability",
        "result",
    ):
        expected = dict(rebuilt[key])
        expected["generated_at"] = retained[key].get("generated_at")
        if retained[key] != expected:
            mismatches.append(
                f"retained {key}.json != independently rebuilt document (generated_at excluded)"
            )

    artifact_digests = json.loads(ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0032 artifact digests"
        )
    )
    from hullq.bootstrap import wikidata_sl0032_sequential_positive_control_pilot as sl0032

    mismatches.extend(
        sl0032.verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0032_DIR
        )
    )

    if mismatches:
        print("\nOFFLINE VERIFY: FAIL", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained SLICE-0028/0030/0031 "
        "inputs and the retained SLICE-0032 pilot candidates, corrected evidence, retrieval log, "
        "clearance assessment, applicability findings, result and artifact digests.",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--replay", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.replay:
        run_replay()
    elif args.verify:
        run_verify()


if __name__ == "__main__":
    main()
