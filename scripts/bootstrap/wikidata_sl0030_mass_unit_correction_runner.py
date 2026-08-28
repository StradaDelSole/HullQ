"""SLICE-0030 Wikidata mass-unit QID correction + full-boundary offline replay runner.

Four independent modes:

``--identity-check``
    Rights-gated live acquisition, strictly bounded to the seven fixed unit
    QIDs (``hullq.bootstrap.wikidata_sl0030_mass_unit_correction.FIXED_UNIT_QIDS``):
    fetches each via the existing ``WikidataAdapter.fetch_entities`` (no
    discovery query, no boat data), positively records label/description/P31
    instance-of, and writes ``unit_qid_assessment.json``. Requires network
    access and is NOT part of normal CI. Run once; the retained snapshot
    makes every later mode fully offline.

``--replay``
    Offline (no network access, no re-acquisition): offline-verifies the
    accepted SLICE-0028 retained package first (fails closed on drift),
    rebuilds its exact 1,770 entities from its own retained ``raw_entities``,
    replays extraction twice (once pinned to the legacy
    ``UNIT_QID_MAP_VERSION_SLICE0008`` map, once with the current SLICE-0030
    corrected default), and writes ``coverage_before_after.json`` +
    ``REPORT.md`` + ``ARTIFACT-DIGESTS.json``.

``--verify``
    Fully offline (zero network access): re-verifies the accepted SLICE-0028
    input, re-verifies ``unit_qid_assessment.json`` from its own retained
    raw snapshot, re-verifies ``coverage_before_after.json``, and verifies
    artifact digests. This is what normal CI runs.

``--persist``
    Offline (no network access) PostgreSQL persistence proof: rebuilds the
    corrected full-boundary evidence from the fixed SLICE-0028
    ``evidence_manifest.json`` (current/corrected adapter default), imports
    one ``ResearchEvidenceBundle`` per requested QID into an isolated schema,
    reads every persisted evidence item back and compares against the
    in-memory bundle, re-imports the exact same bundles to prove idempotency,
    and confirms zero canonical BoatModel/BoatDesign row was created. Writes
    ``REPLAY-RESULT.json`` + ``REPLAY-REPORT.md``.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0030_mass_unit_correction_runner.py \\
        --identity-check --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)"

    uv run python scripts/bootstrap/wikidata_sl0030_mass_unit_correction_runner.py --replay

    uv run python scripts/bootstrap/wikidata_sl0030_mass_unit_correction_runner.py --verify

    uv run python scripts/bootstrap/wikidata_sl0030_mass_unit_correction_runner.py --persist \\
        --db-url postgresql://user:pass@host:5432/db
"""

from __future__ import annotations

import argparse
import hashlib
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
UNIT_QID_ASSESSMENT_PATH = SL0030_DIR / "unit_qid_assessment.json"
UNIT_QID_ASSESSMENT_SCHEMA_PATH = SL0030_DIR / "unit_qid_assessment_schema.json"
COVERAGE_BEFORE_AFTER_PATH = SL0030_DIR / "coverage_before_after.json"
COVERAGE_BEFORE_AFTER_SCHEMA_PATH = SL0030_DIR / "coverage_before_after_schema.json"
REPORT_PATH = SL0030_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0030_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0030_DIR / "artifact_digests_schema.json"
REPLAY_RESULT_PATH = SL0030_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = SL0030_DIR / "REPLAY-REPORT.md"

SOURCE_PATH = ROOT / "fixtures" / "sources" / "wikidata_source.json"


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


def _verify_sl0028_input(*, mismatches: list[str]) -> tuple[Any, list[Any]]:
    """Offline-verify the fixed accepted SLICE-0028 retained package before
    it is used as SLICE-0030's replay input, failing closed on drift.

    Returns ``(boundary, entities)`` rebuilt purely from the retained
    SLICE-0028 documents — zero network access.
    """
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        load_reproduced_identity_boundary,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        BoatModelLinkage,
        rebuild_entities_from_manifest,
        verify_artifact_digests_self_consistency,
        verify_evidence_manifest_self_consistency,
        verify_full_boundary_linkage,
        verify_linkage_document_self_consistency,
    )
    from hullq.sources.wikidata import (
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    for path in (
        SL0028_LINKAGE_PATH,
        SL0028_EVIDENCE_MANIFEST_PATH,
        SL0028_ARTIFACT_DIGESTS_PATH,
    ):
        if not path.exists():
            raise SystemExit(f"required fixed SLICE-0028 input not found: {path}")

    boundary = load_reproduced_identity_boundary()
    if boundary.canonical_boat_model_count != 1770 or boundary.historical_crosswalk_count != 1772:
        raise SystemExit(
            "SLICE-0030 refusing: fixed identity boundary drifted from the accepted "
            f"1,770/1,772 (got {boundary.canonical_boat_model_count}/"
            f"{boundary.historical_crosswalk_count})"
        )
    print(
        f"  SLICE-0028 identity boundary reproduced: canonical_boat_models="
        f"{boundary.canonical_boat_model_count} historical_crosswalk={boundary.historical_crosswalk_count}",
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
    mismatches.extend(verify_full_boundary_linkage(boundary=boundary, linkage=linkage))
    if len(linkage) != 1770:
        raise SystemExit(
            f"SLICE-0030 refusing: fixed SLICE-0028 linkage has {len(linkage)} BoatModel "
            "entries, expected exactly 1,770 — full-boundary identity drift"
        )

    evidence_manifest = json.loads(SL0028_EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            evidence_manifest,
            SL0028_EVIDENCE_MANIFEST_SCHEMA_PATH,
            label="fixed SLICE-0028 evidence manifest",
        )
    )

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (sl0030-offline-input-verify@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        entities = rebuild_entities_from_manifest(evidence_manifest)
        if len(entities) != 1770:
            raise SystemExit(
                f"SLICE-0030 refusing: fixed SLICE-0028 raw_entities rebuilt to {len(entities)} "
                "entities, expected exactly 1,770 — full-boundary identity drift"
            )
        rebuilt_full_evidence, rebuilt_report = adapter.extract_field_evidence(
            entities,
            evidence_manifest.get("acquired_at", ""),
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )

    mismatches.extend(
        verify_evidence_manifest_self_consistency(
            linkage=linkage,
            entities=entities,
            full_evidence=rebuilt_full_evidence,
            quality_report=rebuilt_report,
            evidence_manifest=evidence_manifest,
        )
    )

    artifact_digests = json.loads(SL0028_ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0028_DIR
        )
    )

    print(
        f"  fixed SLICE-0028 retained package offline-verified: {len(entities)} entities, "
        f"{len(mismatches)} mismatch(es) so far",
        flush=True,
    )
    return boundary, entities


# ---------------------------------------------------------------------------
# --identity-check : bounded live entity-identity check for the 7 fixed QIDs
# ---------------------------------------------------------------------------


def run_identity_check(*, user_agent: str) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        rebuild_entities_from_manifest,
    )
    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import (
        FIXED_UNIT_QIDS,
        UnitEntitySnapshot,
        UnitIdentityValidationError,
        build_unit_qid_assessment_document,
        count_mass_unit_qid_occurrences,
    )
    from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    print(
        "HullQ SLICE-0030 Wikidata Mass-Unit QID Correction — IDENTITY CHECK "
        f"(rights-gated live acquisition, strictly bounded to {len(FIXED_UNIT_QIDS)} fixed unit QIDs)",
        flush=True,
    )

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    decision = check_source_use(source, SourceUse.AUTOMATED_INGESTION)
    print(f"  rights_gate.automated_ingestion={decision.outcome!s}", flush=True)
    if decision.outcome != DecisionOutcome.ALLOWED:
        raise SystemExit(
            f"SLICE-0030 refusing before any network request: automated_ingestion gate "
            f"outcome={decision.outcome!s}, reasons={sorted(str(r) for r in decision.reasons)}"
        )

    config = WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=30.0)

    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        verified_at = datetime.now(tz=UTC).isoformat()
        entities = adapter.fetch_entities(list(FIXED_UNIT_QIDS))

    fetched_qids = {e.qid for e in entities}
    missing = [q for q in FIXED_UNIT_QIDS if q not in fetched_qids]
    if missing:
        raise SystemExit(
            f"SLICE-0030 identity check: {len(missing)} fixed unit QID(s) were not returned by "
            f"wbgetentities: {missing}. Refusing to write a partial assessment."
        )
    print(f"  fetched {len(entities)} of {len(FIXED_UNIT_QIDS)} fixed unit QIDs", flush=True)

    def _p31_qids(entity: Any) -> tuple[str, ...]:
        result: list[str] = []
        for claim in entity.raw_claims.get("P31", []) or []:
            if not isinstance(claim, dict):
                continue
            mainsnak = claim.get("mainsnak", {})
            if not isinstance(mainsnak, dict) or mainsnak.get("snaktype") != "value":
                continue
            dv = mainsnak.get("datavalue", {})
            if not isinstance(dv, dict) or dv.get("type") != "wikibase-entityid":
                continue
            val = dv.get("value", {})
            if isinstance(val, dict) and isinstance(val.get("id"), str):
                result.append(val["id"])
        return tuple(result)

    snapshots = tuple(
        UnitEntitySnapshot(
            qid=e.qid,
            label=e.label,
            description_en=None,
            p31_qids=_p31_qids(e),
        )
        for e in entities
    )
    for snap in snapshots:
        print(f"    {snap.qid}: label={snap.label!r} P31={list(snap.p31_qids)}", flush=True)

    if not SL0028_EVIDENCE_MANIFEST_PATH.exists():
        raise SystemExit(
            f"required fixed SLICE-0028 input not found: {SL0028_EVIDENCE_MANIFEST_PATH}"
        )
    sl0028_manifest = json.loads(SL0028_EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    sl0028_entities = rebuild_entities_from_manifest(sl0028_manifest)
    occurrence_counts = count_mass_unit_qid_occurrences(sl0028_entities)
    print(f"  occurrence counts in fixed SLICE-0028 raw claims: {occurrence_counts}", flush=True)

    try:
        document = build_unit_qid_assessment_document(
            generated_at=datetime.now(tz=UTC).isoformat(),
            verified_at=verified_at,
            snapshots=snapshots,
            occurrence_counts=occurrence_counts,
        )
    except UnitIdentityValidationError as exc:
        raise SystemExit(
            "SLICE-0030 identity check: fail-closed unit-identity validation failed — "
            f"refusing to write a contradictory unit_qid_assessment.json: {exc}"
        ) from exc
    SL0030_DIR.mkdir(parents=True, exist_ok=True)
    _write_text_lf(UNIT_QID_ASSESSMENT_PATH, json.dumps(document, indent=2, ensure_ascii=False))
    print(f"  wrote {UNIT_QID_ASSESSMENT_PATH}", flush=True)
    return document


# ---------------------------------------------------------------------------
# --replay : offline before/after coverage over the fixed SLICE-0028 entities
# ---------------------------------------------------------------------------


def run_replay() -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import (
        ARTIFACT_DIGESTS_SCHEMA_VERSION,
        build_artifact_digests,
        build_coverage_before_after_document,
        compute_before_after_coverage,
    )
    from hullq.sources.wikidata import (
        DEFAULT_UNIT_QID_MAP_VERSION,
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    print(
        "HullQ SLICE-0030 Wikidata Mass-Unit QID Correction — REPLAY "
        "(offline, no network access, no re-acquisition)",
        flush=True,
    )

    mismatches: list[str] = []
    _boundary, entities = _verify_sl0028_input(mismatches=mismatches)
    if mismatches:
        raise SystemExit(
            "SLICE-0030 refusing to derive after-state: fixed SLICE-0028 input failed offline "
            f"verification: {mismatches}"
        )

    evidence_manifest = json.loads(SL0028_EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    acquired_at = evidence_manifest.get("acquired_at", "")

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (sl0030-replay@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        full_evidence_before, _ = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )
        full_evidence_after, _ = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=DEFAULT_UNIT_QID_MAP_VERSION,
        )

    before_counts, after_counts = compute_before_after_coverage(
        entities, full_evidence_before, full_evidence_after
    )
    document = build_coverage_before_after_document(
        generated_at=datetime.now(tz=UTC).isoformat(),
        qid_count=len(entities),
        before_counts=before_counts,
        after_counts=after_counts,
    )
    print(
        f"  displacement_normalized_candidate_delta={document['displacement_normalized_candidate_delta']} "
        f"non_displacement_fields_unchanged={document['non_displacement_fields_unchanged']}",
        flush=True,
    )

    SL0030_DIR.mkdir(parents=True, exist_ok=True)
    _write_text_lf(COVERAGE_BEFORE_AFTER_PATH, json.dumps(document, indent=2, ensure_ascii=False))
    print(f"  wrote {COVERAGE_BEFORE_AFTER_PATH}", flush=True)

    report_lines = [
        "# HullQ SLICE-0030 Wikidata Mass-Unit QID Correction Report",
        "",
        f"**generated_at:** {document['generated_at']}  ",
        f"**fixed SLICE-0028 input qid_count:** {document['qid_count']}  ",
        "",
        "## SCOPE",
        "",
        "Mass-unit-identity correction + offline full-boundary replay only. Does not "
        "reacquire the 1,770-QID dataset, does not create/mutate canonical BoatModel/"
        "BoatDesign identity, does not create a FieldResolution, and does not reinterpret "
        "the SLICE-0029 applicability result.",
        "",
        "## CORRECTED MASS-UNIT MAP",
        "",
        "| QID | intended unit | before (legacy) | after (default) |",
        "|---|---|---|---|",
        "| Q11570 | kilogram | recognized | recognized (unchanged) |",
        "| Q41803 | gram | not recognized | recognized |",
        "| Q191118 | tonne/metric tonne | not recognized | recognized |",
        "| Q100995 | pound | not recognized | recognized |",
        "| Q12152 | (not a unit — myocardial infarction) | recognized (bug) | not recognized |",
        "| Q11369 | (not a unit — molecule) | recognized (bug) | not recognized |",
        "| Q37795 | (not a unit — Romanian Raven Shepherd Dog) | recognized (bug) | not recognized |",
        "",
        "See `unit_qid_assessment.json` for the positively-verified identity evidence.",
        "",
        "## BEFORE/AFTER COVERAGE (fixed SLICE-0028 full-boundary entities)",
        "",
        "| field | before normalized | after normalized | before source_only | after source_only |",
        "|---|---|---|---|---|",
    ]
    for label in ("loa", "lwl", "beam", "draft", "displacement"):
        b = document["fields"][label]["before"]
        a = document["fields"][label]["after"]
        report_lines.append(
            f"| {label} | {b['normalized_candidate_present']} | {a['normalized_candidate_present']} "
            f"| {b['source_statement_present']} | {a['source_statement_present']} |"
        )
    report_lines += [
        "",
        f"**displacement_normalized_candidate_delta:** "
        f"{document['displacement_normalized_candidate_delta']}  ",
        f"**non_displacement_fields_unchanged:** {document['non_displacement_fields_unchanged']}  ",
        "",
        "## SCOPE CONFIRMATION",
        "",
        "- No discovery/SPARQL request was made; only the fixed accepted SLICE-0028 "
        "retained raw claims were replayed offline.",
        "- No canonical BoatModel/BoatDesign row was created or mutated.",
        "- No FieldResolution was created.",
        "- SLICE-0026/0027/0028/0029 retained artifacts were not modified.",
        "- SLICE-0031 was not created or started.",
        "",
    ]
    _write_text_lf(REPORT_PATH, "\n".join(report_lines))
    print(f"  wrote {REPORT_PATH}", flush=True)

    artifact_digests = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0030_DIR
    )
    _write_text_lf(
        ARTIFACT_DIGESTS_PATH, json.dumps(artifact_digests, indent=2, ensure_ascii=False)
    )
    print(
        f"  wrote {ARTIFACT_DIGESTS_PATH} "
        f"(schema_version={ARTIFACT_DIGESTS_SCHEMA_VERSION}, {len(artifact_digests['digests'])} files)",
        flush=True,
    )
    return document


# ---------------------------------------------------------------------------
# --verify : fully offline verification (what normal CI runs)
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import (
        verify_artifact_digests_self_consistency,
        verify_coverage_before_after_self_consistency,
        verify_unit_qid_assessment_self_consistency,
    )
    from hullq.sources.wikidata import (
        DEFAULT_UNIT_QID_MAP_VERSION,
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    print(
        "HullQ SLICE-0030 Wikidata Mass-Unit QID Correction — OFFLINE VERIFY (no network access)",
        flush=True,
    )

    mismatches: list[str] = []
    _boundary, entities = _verify_sl0028_input(mismatches=mismatches)

    for path in (UNIT_QID_ASSESSMENT_PATH, COVERAGE_BEFORE_AFTER_PATH, ARTIFACT_DIGESTS_PATH):
        if not path.exists():
            raise SystemExit(f"required SLICE-0030 retained artifact not found: {path}")

    assessment_doc = json.loads(UNIT_QID_ASSESSMENT_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            assessment_doc, UNIT_QID_ASSESSMENT_SCHEMA_PATH, label="SLICE-0030 unit QID assessment"
        )
    )
    mismatches.extend(
        verify_unit_qid_assessment_self_consistency(
            sl0028_entities=entities, document=assessment_doc
        )
    )

    evidence_manifest = json.loads(SL0028_EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    acquired_at = evidence_manifest.get("acquired_at", "")
    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (sl0030-offline-verify@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        full_evidence_before, _ = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )
        full_evidence_after, _ = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=DEFAULT_UNIT_QID_MAP_VERSION,
        )
    print(
        f"  rebuilt {len(entities)} entities and re-extracted before/after evidence offline "
        "from the fixed SLICE-0028 retained raw_entities",
        flush=True,
    )

    coverage_doc = json.loads(COVERAGE_BEFORE_AFTER_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            coverage_doc,
            COVERAGE_BEFORE_AFTER_SCHEMA_PATH,
            label="SLICE-0030 coverage before/after",
        )
    )
    mismatches.extend(
        verify_coverage_before_after_self_consistency(
            entities=entities,
            full_evidence_before=full_evidence_before,
            full_evidence_after=full_evidence_after,
            document=coverage_doc,
        )
    )

    artifact_digests = json.loads(ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0030 artifact digests"
        )
    )
    mismatches.extend(
        verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0030_DIR
        )
    )

    if mismatches:
        print("\nOFFLINE VERIFY: FAIL", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained SLICE-0028 input, "
        "unit QID assessment, before/after coverage and artifact digests.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# --persist : offline PostgreSQL persistence proof (corrected map)
# ---------------------------------------------------------------------------


def persist_and_verify(
    db_url: str,
    *,
    schema_name: str | None = None,
    linkage_path: Path = SL0028_LINKAGE_PATH,
    evidence_manifest_path: Path = SL0028_EVIDENCE_MANIFEST_PATH,
) -> dict[str, Any]:
    import contextlib
    from collections.abc import Iterator

    import psycopg

    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        filter_to_allowed_evidence,
        rebuild_entities_from_manifest,
    )
    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import build_sl0030_bundle
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations
    from hullq.persistence.readback import fetch_bundle_snapshot, fetch_evidence
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    linkage_doc = json.loads(linkage_path.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))

    label_by_qid: dict[str, str | None] = {}
    request_qids: list[str] = []
    for row in linkage_doc["boat_models"]:
        for qid, label in row["preferred_label_by_qid"].items():
            label_by_qid[qid] = label
            request_qids.append(qid)
    request_qids = sorted(set(request_qids))

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (sl0030-offline-persist@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        entities = rebuild_entities_from_manifest(evidence_manifest)
        # Uses the current SLICE-0030 corrected/default unit map (no pin):
        # this proof measures persistence of the CORRECTED evidence, distinct
        # from the accepted SLICE-0028 bundles it never overwrites (see
        # build_sl0030_bundle's own BUNDLE-SL0030-* namespace).
        full_evidence, _report = adapter.extract_field_evidence(
            entities, evidence_manifest.get("acquired_at", ""), requested_qid_count=len(entities)
        )

    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    bundles = [
        build_sl0030_bundle(qid, label_by_qid.get(qid), by_qid.get(qid, [])) for qid in request_qids
    ]

    schema_name = (
        schema_name or "hullq_sl0030_run_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
    )

    @contextlib.contextmanager
    def _isolated_schema(conn: Any, name: str) -> Iterator[None]:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{name}"')
            cur.execute(f'SET search_path TO "{name}"')
        conn.commit()
        try:
            yield
        finally:
            with conn.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
            conn.commit()

    conn = psycopg.connect(db_url)
    try:
        with _isolated_schema(conn, schema_name):
            apply_migrations(conn)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    pg_version = str(cur.fetchone()[0])
            except Exception:
                pg_version = "NOT_MEASURED"

            first_pass = {"imported": 0, "already_present": 0, "conflict": 0, "error": 0}
            for bundle in bundles:
                try:
                    result = import_research_evidence_bundle(conn, bundle)
                except Exception as exc:
                    first_pass["error"] += 1
                    print(f"    IMPORT ERROR: {bundle.bundle_id}: {exc}", flush=True)
                    continue
                if result.status == ImportStatus.IMPORTED:
                    first_pass["imported"] += 1
                elif result.status == ImportStatus.ALREADY_IMPORTED:
                    first_pass["already_present"] += 1
                else:
                    first_pass["conflict"] += 1
                    print(f"    IMPORT CONFLICT: {bundle.bundle_id}: {result.detail}", flush=True)
            print(f"  first pass: {first_pass}", flush=True)

            readback_mismatches = 0
            for bundle in bundles:
                snapshot = fetch_bundle_snapshot(conn, bundle.bundle_id, bundle.bundle_version)
                if snapshot is None:
                    readback_mismatches += 1
                    print(f"    READBACK MISSING BUNDLE: {bundle.bundle_id}", flush=True)
                    continue
                expected_evidence_ids = {ev.evidence_id for ev in bundle.promoted_evidence}
                if set(snapshot.evidence_ids) != expected_evidence_ids:
                    readback_mismatches += 1
                    print(f"    READBACK EVIDENCE-ID MISMATCH: {bundle.bundle_id}", flush=True)
                for ev in bundle.promoted_evidence:
                    fetched = fetch_evidence(conn, ev.evidence_id)
                    if fetched is None or fetched != ev:
                        readback_mismatches += 1
                        print(f"    READBACK EVIDENCE MISMATCH: {ev.evidence_id}", flush=True)
            print(f"  readback_mismatches={readback_mismatches}", flush=True)

            reimport = {"already_imported": 0, "conflict": 0, "error": 0}
            for bundle in bundles:
                try:
                    result = import_research_evidence_bundle(conn, bundle)
                except Exception as exc:
                    reimport["error"] += 1
                    print(f"    REIMPORT ERROR: {bundle.bundle_id}: {exc}", flush=True)
                    continue
                if result.status == ImportStatus.ALREADY_IMPORTED:
                    reimport["already_imported"] += 1
                else:
                    reimport["conflict"] += 1
                    print(
                        f"    REIMPORT NOT IDEMPOTENT: {bundle.bundle_id}: {result.status}",
                        flush=True,
                    )
            print(f"  reimport: {reimport}", flush=True)

            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM canonical_boat_models")
                boat_model_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM canonical_boat_designs")
                boat_design_count = cur.fetchone()[0]
    finally:
        conn.close()

    clear = bool(
        first_pass["imported"] == len(bundles)
        and first_pass["conflict"] == 0
        and first_pass["error"] == 0
        and readback_mismatches == 0
        and reimport["already_imported"] == len(bundles)
        and reimport["conflict"] == 0
        and reimport["error"] == 0
        and boat_model_count == 0
        and boat_design_count == 0
    )

    return {
        "schema_version": "sl0030-replay-v1",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "postgresql_version": pg_version,
        "bundle_count": len(bundles),
        "first_pass": first_pass,
        "readback_mismatches": readback_mismatches,
        "reimport": reimport,
        "canonical_boat_model_row_count": boat_model_count,
        "canonical_boat_design_row_count": boat_design_count,
        "clear": clear,
    }


def run_persist(db_url: str) -> dict[str, Any]:
    print(
        "HullQ SLICE-0030 Wikidata Mass-Unit QID Correction — PERSIST "
        "(offline, no network access; PostgreSQL required)",
        flush=True,
    )
    result = persist_and_verify(db_url)
    SL0030_DIR.mkdir(parents=True, exist_ok=True)
    _write_text_lf(REPLAY_RESULT_PATH, json.dumps(result, indent=2, ensure_ascii=False))
    print(f"  wrote {REPLAY_RESULT_PATH}", flush=True)

    report_lines = [
        "# HullQ SLICE-0030 PostgreSQL Persistence Replay Report",
        "",
        f"**run_timestamp:** {result['run_timestamp']}  ",
        f"**postgresql_version:** {result['postgresql_version']}  ",
        f"**bundle_count:** {result['bundle_count']}  ",
        "",
        f"- first_pass: {result['first_pass']}",
        f"- readback_mismatches: {result['readback_mismatches']}",
        f"- reimport: {result['reimport']}",
        f"- canonical_boat_model_row_count: {result['canonical_boat_model_row_count']} (must be 0)",
        f"- canonical_boat_design_row_count: {result['canonical_boat_design_row_count']} (must be 0)",
        "",
        f"### RESULT: zero-mutation and idempotency proof clear: **{result['clear']}**",
        "",
    ]
    _write_text_lf(REPLAY_REPORT_PATH, "\n".join(report_lines))
    print(f"  wrote {REPLAY_REPORT_PATH}", flush=True)

    from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import build_artifact_digests

    artifact_digests = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0030_DIR
    )
    _write_text_lf(
        ARTIFACT_DIGESTS_PATH, json.dumps(artifact_digests, indent=2, ensure_ascii=False)
    )
    print(f"  wrote {ARTIFACT_DIGESTS_PATH} ({len(artifact_digests['digests'])} files)", flush=True)

    if not result["clear"]:
        raise SystemExit(
            "SLICE-0030 persist: zero-mutation/idempotency proof did not come back clear"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity-check", action="store_true")
    mode.add_argument("--replay", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--persist", action="store_true")
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--db-url", default=None)
    args = parser.parse_args()

    if args.identity_check:
        if not args.user_agent:
            raise SystemExit("--identity-check requires --user-agent")
        run_identity_check(user_agent=args.user_agent)
    elif args.replay:
        run_replay()
    elif args.verify:
        run_verify()
    elif args.persist:
        if not args.db_url:
            raise SystemExit("--persist requires --db-url")
        run_persist(args.db_url)


if __name__ == "__main__":
    main()
