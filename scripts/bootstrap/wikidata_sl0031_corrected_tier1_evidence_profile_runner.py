"""SLICE-0031 corrected Tier-1 evidence profile + positive-control candidate
selection runner.

Two independent modes, both fully offline (zero network access, zero
reacquisition of the fixed 1,770-entity boundary):

``--replay``
    Offline-verifies the accepted SLICE-0028 and SLICE-0030 retained
    packages first (fails closed on drift), rebuilds the corrected/current
    five-field evidence and disagreement diagnostics purely from the fixed
    SLICE-0028 retained ``raw_entities``, independently recomputes the
    predecessor (pre-SLICE-0030) precursor from the pre-correction evidence,
    and writes ``boatmodel_evidence_profile.json`` / ``aggregate_profile.json``
    / ``positive_control_candidates.json`` / ``REPORT.md`` /
    ``ARTIFACT-DIGESTS.json``.

``--verify``
    Fully offline (zero network access): re-verifies the accepted SLICE-0028
    and SLICE-0030 inputs, re-derives the corrected/predecessor evidence, and
    re-verifies every retained SLICE-0031 document against that independently
    rebuilt state. This is what normal CI runs.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0031_corrected_tier1_evidence_profile_runner.py --replay
    uv run python scripts/bootstrap/wikidata_sl0031_corrected_tier1_evidence_profile_runner.py --verify
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
PROFILE_PATH = SL0031_DIR / "boatmodel_evidence_profile.json"
PROFILE_SCHEMA_PATH = SL0031_DIR / "boatmodel_evidence_profile_schema.json"
AGGREGATE_PATH = SL0031_DIR / "aggregate_profile.json"
AGGREGATE_SCHEMA_PATH = SL0031_DIR / "aggregate_profile_schema.json"
CANDIDATES_PATH = SL0031_DIR / "positive_control_candidates.json"
CANDIDATES_SCHEMA_PATH = SL0031_DIR / "positive_control_candidates_schema.json"
REPORT_PATH = SL0031_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0031_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0031_DIR / "artifact_digests_schema.json"


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


def _verify_fixed_inputs(*, mismatches: list[str]) -> tuple[Any, Any, Any, Any, Any, str]:
    """Offline-verify the fixed accepted SLICE-0028 and SLICE-0030 retained
    packages, then independently derive the pre-correction (``before``) and
    corrected/current (``after``) five-field evidence over the fixed 1,770
    entities -- zero network access, zero reacquisition.

    Returns ``(boundary, linkage, entities, full_evidence_before,
    full_evidence_after, acquired_at)``.
    """
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
            "SLICE-0031 refusing: fixed identity boundary drifted from the accepted "
            f"1,770/1,772 (got {boundary.canonical_boat_model_count}/"
            f"{boundary.historical_crosswalk_count})"
        )
    print(
        f"  identity boundary reproduced: canonical_boat_models={boundary.canonical_boat_model_count} "
        f"historical_crosswalk={boundary.historical_crosswalk_count}",
        flush=True,
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
            f"SLICE-0031 refusing: fixed SLICE-0028 linkage has {len(linkage)} BoatModel "
            "entries, expected exactly 1,770 -- full-boundary identity drift"
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
            f"SLICE-0031 refusing: fixed SLICE-0028 raw_entities rebuilt to {len(entities)} "
            "entities, expected exactly 1,770 -- full-boundary identity drift"
        )
    acquired_at = evidence_manifest.get("acquired_at", "")

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (sl0031-offline-verify@example.org)")
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
    print(
        f"  fixed SLICE-0028 retained package offline-verified: {len(entities)} entities, "
        f"{len(mismatches)} mismatch(es) so far",
        flush=True,
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
        f"  fixed SLICE-0030 retained package offline-verified: {len(mismatches)} mismatch(es) "
        "so far",
        flush=True,
    )

    return boundary, linkage, entities, full_evidence_before, full_evidence_after, acquired_at


def _derive_profile_state(
    *, linkage: Any, entities: Any, full_evidence_before: Any, full_evidence_after: Any
) -> tuple[Any, int, Any, Any, Any]:
    """Independently derive the corrected evidence profile rows, the
    predecessor precursor count, the corrected BoatModel-level coverage
    counts, the corrected BoatModel-level coverage details and the corrected
    disagreement diagnostics, purely from already-verified fixed inputs.
    Raises ``SystemExit`` if the predecessor precursor or corrected marginal
    totals do not reproduce the accepted SLICE-0028/0030 values.

    Returns ``(rows, predecessor_count, per_field_corrected_coverage,
    boat_model_coverage_after, disagreements_after)``.
    """
    from hullq.bootstrap import wikidata_sl0026_tier1_enrichment_pilot as sl0026
    from hullq.bootstrap import wikidata_sl0028_full_boundary_evidence as sl0028
    from hullq.bootstrap import wikidata_sl0031_corrected_tier1_evidence_profile as sl0031

    _source_counts_before, source_details_before = sl0026.summarize_field_coverage(
        entities, full_evidence_before
    )
    _boat_model_counts_before, boat_model_coverage_before = (
        sl0028.summarize_boat_model_field_coverage(linkage, source_details_before)
    )
    predecessor_count, _predecessor_ids = sl0028.compute_basic_searchable_evidence_precursor(
        boat_model_coverage_before
    )
    if predecessor_count != sl0031.EXPECTED_PREDECESSOR_PRECURSOR_COUNT:
        raise SystemExit(
            "SLICE-0031 refusing: predecessor precursor recomputed to "
            f"{predecessor_count}/1770, expected exactly "
            f"{sl0031.EXPECTED_PREDECESSOR_PRECURSOR_COUNT}/1770 from the accepted "
            "pre-correction evidence"
        )

    _boat_model_counts_after, source_details_after = sl0026.summarize_field_coverage(
        entities, full_evidence_after
    )
    boat_model_field_counts_after, boat_model_coverage_after = (
        sl0028.summarize_boat_model_field_coverage(linkage, source_details_after)
    )
    coverage_problems = sl0031.verify_reproduces_sl0030_after_coverage(
        boat_model_field_counts_after
    )
    if coverage_problems:
        raise SystemExit(
            "SLICE-0031 refusing: corrected/current five-field marginal totals do not reproduce "
            f"the accepted SLICE-0030 result: {coverage_problems}"
        )

    disagreements_after = sl0028.compute_boat_model_field_disagreements(
        linkage, entities, full_evidence_after, source_details_after
    )
    rows = sl0031.build_boatmodel_evidence_profile(
        linkage, boat_model_coverage_after, disagreements_after
    )
    return (
        rows,
        predecessor_count,
        boat_model_field_counts_after,
        boat_model_coverage_after,
        disagreements_after,
    )


# ---------------------------------------------------------------------------
# --replay : build the retained SLICE-0031 package
# ---------------------------------------------------------------------------


def run_replay() -> None:
    from hullq.bootstrap import wikidata_sl0031_corrected_tier1_evidence_profile as sl0031

    print(
        "HullQ SLICE-0031 Corrected Tier-1 Evidence Profile + Positive-Control Selection — "
        "REPLAY (offline, no network access, no re-acquisition)",
        flush=True,
    )

    mismatches: list[str] = []
    _boundary, linkage, entities, full_evidence_before, full_evidence_after, _acquired_at = (
        _verify_fixed_inputs(mismatches=mismatches)
    )
    if mismatches:
        raise SystemExit(
            f"SLICE-0031 refusing to derive a profile: fixed inputs failed offline "
            f"verification: {mismatches}"
        )

    (
        rows,
        predecessor_count,
        per_field_corrected_coverage,
        _boat_model_coverage_after,
        _disagreements_after,
    ) = _derive_profile_state(
        linkage=linkage,
        entities=entities,
        full_evidence_before=full_evidence_before,
        full_evidence_after=full_evidence_after,
    )
    print(f"  built {len(rows)} BoatModel evidence-profile rows", flush=True)

    SL0031_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(tz=UTC).isoformat()

    profile_doc = sl0031.build_boatmodel_evidence_profile_document(
        generated_at=generated_at, rows=rows
    )
    _write_text_lf(PROFILE_PATH, json.dumps(profile_doc, indent=2, ensure_ascii=False))
    print(f"  wrote {PROFILE_PATH}", flush=True)

    aggregate_doc = sl0031.build_aggregate_profile_document(
        generated_at=generated_at,
        rows=rows,
        per_field_corrected_coverage=per_field_corrected_coverage,
        predecessor_precursor_count=predecessor_count,
    )
    _write_text_lf(AGGREGATE_PATH, json.dumps(aggregate_doc, indent=2, ensure_ascii=False))
    print(f"  wrote {AGGREGATE_PATH}", flush=True)
    print(
        f"  predecessor precursor={aggregate_doc['predecessor_precursor']['count']}/1770 "
        f"corrected precursor={aggregate_doc['corrected_precursor']['count']}/1770 "
        f"delta={aggregate_doc['precursor_delta']}",
        flush=True,
    )

    candidates_doc = sl0031.build_positive_control_candidates_document(
        generated_at=generated_at, rows=rows
    )
    _write_text_lf(CANDIDATES_PATH, json.dumps(candidates_doc, indent=2, ensure_ascii=False))
    print(f"  wrote {CANDIDATES_PATH}", flush=True)
    print(
        f"  candidate_pool_size={candidates_doc['candidate_pool_size']} "
        f"pool_result={candidates_doc['pool_result']}",
        flush=True,
    )

    dist = aggregate_doc["normalized_field_count_distribution"]
    report_lines = [
        "# HullQ SLICE-0031 Corrected Tier-1 Evidence Profile Report",
        "",
        f"**generated_at:** {generated_at}  ",
        f"**boat_model_count:** {len(rows)}  ",
        "",
        "## SCOPE",
        "",
        "Validation/selection slice only, over the exact fixed accepted 1,770-canonical-"
        "BoatModel boundary. Creates zero canonical BoatModel/BoatDesign/FieldResolution/"
        "technical-value mutation. Does not reacquire the 1,770-entity dataset, does not "
        "resolve BoatDesign applicability, and does not reinterpret the SLICE-0029 negative-"
        "control result.",
        "",
        "## PER-FIELD CORRECTED COVERAGE (reproduces accepted SLICE-0030 result)",
        "",
        "| field | normalized_candidate_present |",
        "|---|---:|",
    ]
    report_lines.extend(
        f"| {label} | {per_field_corrected_coverage[label]['normalized_candidate_present']} |"
        for label in ("loa", "lwl", "beam", "draft", "displacement")
    )
    report_lines += [
        "",
        "## NORMALIZED-FIELD-COUNT DISTRIBUTION",
        "",
        "| fields | boat_models |",
        "|---:|---:|",
        *[f"| {i} | {dist[str(i)]} |" for i in range(6)],
        "",
        f"cumulative: >=3: {aggregate_doc['cumulative']['gte_3']}, "
        f">=4: {aggregate_doc['cumulative']['gte_4']}, "
        f"all 5: {aggregate_doc['cumulative']['all_5']}",
        "",
        "## PREDECESSOR / CORRECTED PRECURSOR (LOA + beam + (draft OR displacement))",
        "",
        f"- predecessor (pre-SLICE-0030): {aggregate_doc['predecessor_precursor']['count']} / "
        f"{aggregate_doc['predecessor_precursor']['boat_model_count']} = "
        f"{aggregate_doc['predecessor_precursor']['percentage']}%",
        f"- corrected (post-SLICE-0030): {aggregate_doc['corrected_precursor']['count']} / "
        f"{aggregate_doc['corrected_precursor']['boat_model_count']} = "
        f"{aggregate_doc['corrected_precursor']['percentage']}%",
        f"- delta: {aggregate_doc['precursor_delta']['absolute']} BoatModels "
        f"({aggregate_doc['precursor_delta']['percentage_points']} percentage points)",
        f"- overlap decomposition: {aggregate_doc['precursor_overlap_decomposition']}",
        "",
        "## STRONG TECHNICAL-EVIDENCE SUBSETS",
        "",
        f"- LOA+beam+draft+displacement: "
        f"{aggregate_doc['strong_evidence_subsets']['loa_beam_draft_displacement']}",
        f"- LOA+LWL+beam+(draft OR displacement): "
        f"{aggregate_doc['strong_evidence_subsets']['loa_lwl_beam_draft_or_displacement']}",
        f"- all five fixed fields: {aggregate_doc['strong_evidence_subsets']['all_five_fields']}",
        f"- >=4/5 normalized, no disagreement diagnostic: "
        f"{aggregate_doc['strong_evidence_subsets']['gte4_normalized_no_disagreement']}",
        "",
        "## POSITIVE-CONTROL CANDIDATE POOL",
        "",
        f"- eligible candidates: {candidates_doc['eligible_candidate_count']}",
        f"- retained pool size: {candidates_doc['candidate_pool_size']} "
        f"(limit {candidates_doc['candidate_pool_limit']})",
        f"- pool result: **{candidates_doc['pool_result']}**",
        f"- excluded SLICE-0029 negative-control QIDs: "
        f"{candidates_doc['excluded_negative_control_qids']}",
        "",
        "| rank | hullq_id | qids | normalized_field_count | draft+displacement | LWL |",
        "|---:|---|---|---:|:---:|:---:|",
    ]
    for c in candidates_doc["candidates"]:
        report_lines.append(
            f"| {c['rank']} | {c['hullq_id']} | {', '.join(c['qids'])} | "
            f"{c['normalized_field_count']} | {c['draft_and_displacement_present']} | "
            f"{c['lwl_present']} |"
        )
    report_lines += [
        "",
        "A positive pool means only that technically strong BoatModel-scoped source evidence "
        "exists for later applicability research; it is not authorization to research all "
        "listed candidates externally and does not establish a BoatDesign generation boundary, "
        "cleared primary source, or promotable canonical value for any listed BoatModel.",
        "",
        "## CAL-01 / LAUNCH-THRESHOLD BOUNDARY",
        "",
        "This report retains the corrected evidence measurements as a calibration input only. "
        "It does not relabel research evidence as canonical basic-searchable coverage, does not "
        "declare the D2/D2b launch threshold met, and does not declare G4 passed.",
        "",
        "## SCOPE CONFIRMATION",
        "",
        "- No discovery/SPARQL/live acquisition request was made; only the fixed accepted "
        "SLICE-0028/0030 retained raw claims were replayed offline.",
        "- No canonical BoatModel/BoatDesign row was created or mutated.",
        "- No FieldResolution was created.",
        "- SLICE-0026/0027/0028/0029/0030 retained artifacts were not modified.",
        "- SLICE-0032 was not created or started.",
        "",
    ]
    _write_text_lf(REPORT_PATH, "\n".join(report_lines))
    print(f"  wrote {REPORT_PATH}", flush=True)

    for path, schema_path, label in (
        (PROFILE_PATH, PROFILE_SCHEMA_PATH, "boatmodel_evidence_profile.json"),
        (AGGREGATE_PATH, AGGREGATE_SCHEMA_PATH, "aggregate_profile.json"),
        (CANDIDATES_PATH, CANDIDATES_SCHEMA_PATH, "positive_control_candidates.json"),
    ):
        problems = _validate_schema(
            json.loads(path.read_text(encoding="utf-8")), schema_path, label=label
        )
        if problems:
            raise SystemExit(f"SLICE-0031 replay produced a schema-invalid document: {problems}")

    artifact_digests = sl0031.build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0031_DIR
    )
    _write_text_lf(
        ARTIFACT_DIGESTS_PATH, json.dumps(artifact_digests, indent=2, ensure_ascii=False)
    )
    print(
        f"  wrote {ARTIFACT_DIGESTS_PATH} ({len(artifact_digests['digests'])} files)",
        flush=True,
    )


# ---------------------------------------------------------------------------
# --verify : fully offline verification (what normal CI runs)
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap import wikidata_sl0031_corrected_tier1_evidence_profile as sl0031

    print(
        "HullQ SLICE-0031 Corrected Tier-1 Evidence Profile + Positive-Control Selection — "
        "OFFLINE VERIFY (no network access)",
        flush=True,
    )

    mismatches: list[str] = []
    _boundary, linkage, entities, full_evidence_before, full_evidence_after, _acquired_at = (
        _verify_fixed_inputs(mismatches=mismatches)
    )

    for path in (
        PROFILE_PATH,
        AGGREGATE_PATH,
        CANDIDATES_PATH,
        ARTIFACT_DIGESTS_PATH,
    ):
        if not path.exists():
            raise SystemExit(f"required SLICE-0031 retained artifact not found: {path}")

    (
        rows,
        predecessor_count,
        per_field_corrected_coverage,
        boat_model_coverage_after,
        disagreements_after,
    ) = _derive_profile_state(
        linkage=linkage,
        entities=entities,
        full_evidence_before=full_evidence_before,
        full_evidence_after=full_evidence_after,
    )

    profile_doc = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(profile_doc, PROFILE_SCHEMA_PATH, label="SLICE-0031 evidence profile")
    )

    mismatches.extend(
        sl0031.verify_boatmodel_evidence_profile_self_consistency(
            linkage=linkage,
            boat_model_coverage=boat_model_coverage_after,
            disagreements=disagreements_after,
            document=profile_doc,
        )
    )

    aggregate_doc = json.loads(AGGREGATE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(aggregate_doc, AGGREGATE_SCHEMA_PATH, label="SLICE-0031 aggregate profile")
    )
    mismatches.extend(
        sl0031.verify_aggregate_profile_self_consistency(
            rows=rows,
            per_field_corrected_coverage=per_field_corrected_coverage,
            predecessor_precursor_count=predecessor_count,
            document=aggregate_doc,
        )
    )

    candidates_doc = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            candidates_doc, CANDIDATES_SCHEMA_PATH, label="SLICE-0031 positive-control candidates"
        )
    )
    mismatches.extend(
        sl0031.verify_positive_control_candidates_self_consistency(
            rows=rows, document=candidates_doc
        )
    )
    if candidates_doc.get("pool_result") not in (
        "POSITIVE_CONTROL_POOL_AVAILABLE",
        "NO_POSITIVE_CONTROL_POOL",
    ):
        mismatches.append(
            f"retained pool_result {candidates_doc.get('pool_result')!r} is not one of the two "
            "fixed mechanical outcomes"
        )

    artifact_digests = json.loads(ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0031 artifact digests"
        )
    )
    mismatches.extend(
        sl0031.verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0031_DIR
        )
    )

    if mismatches:
        print("\nOFFLINE VERIFY: FAIL", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained SLICE-0028/0030 "
        "inputs and the retained SLICE-0031 evidence profile, aggregate measurements, "
        "positive-control candidate pool and artifact digests.",
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
