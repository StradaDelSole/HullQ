"""SLICE-0026 bounded Wikidata Tier-1 enrichment evidence pilot runner.

Four independent modes:

``--select``
    Offline (no network access): reproduces the accepted 1,770/1,772
    identity boundary from the retained SLICE-0017/0018 manifests (failing
    closed on drift), deterministically selects exactly 100 distinct
    canonical BoatModels, and writes
    ``research/stage3/sl0026-wikidata-tier1-enrichment/selection.json``.

``--live``
    Rights-gated live acquisition: fetches exactly the 100 selected QIDs via
    the existing ``WikidataAdapter.fetch_entities`` (no discovery query),
    extracts field evidence via the existing
    ``WikidataAdapter.extract_field_evidence``, classifies per-field
    coverage, and writes ``evidence_manifest.json`` + ``REPORT.md`` +
    ``ARTIFACT-DIGESTS.json``. Requires network access and is NOT part of
    normal CI. Builds ``selection.json`` first if it does not already exist.

``--verify``
    Fully offline (zero network access): reloads the retained
    ``selection.json``/``evidence_manifest.json``, recomputes the identity
    boundary and selection from the retained SLICE-0017/0018 manifests,
    rebuilds every acquired entity from ``evidence_manifest.json``'s own
    retained ``raw_entities`` and reruns the existing adapter's
    ``extract_field_evidence`` on them (no network — the adapter's HTTP
    client is never invoked), and compares every recomputed value against
    the retained documents. This is what normal CI runs.

``--persist``
    Offline (no network access) PostgreSQL persistence proof: imports the
    100 pilot ``ResearchEvidenceBundle``s (rebuilt from the already-retained,
    offline-verified ``evidence_manifest.json``) into an isolated schema,
    reads every persisted evidence item back and compares against the
    in-memory bundle, then re-imports the exact same bundles to prove
    idempotency, and confirms zero canonical BoatModel/BoatDesign row was
    created. Writes ``REPLAY-RESULT.json`` + ``REPLAY-REPORT.md``.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --select

    uv run python scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)"

    uv run python scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --verify

    uv run python scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --persist \\
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

SL0026_DIR = ROOT / "research" / "stage3" / "sl0026-wikidata-tier1-enrichment"
SELECTION_PATH = SL0026_DIR / "selection.json"
SELECTION_SCHEMA_PATH = SL0026_DIR / "selection_schema.json"
EVIDENCE_MANIFEST_PATH = SL0026_DIR / "evidence_manifest.json"
EVIDENCE_MANIFEST_SCHEMA_PATH = SL0026_DIR / "evidence_manifest_schema.json"
REPORT_PATH = SL0026_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0026_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0026_DIR / "artifact_digests_schema.json"
REPLAY_RESULT_PATH = SL0026_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = SL0026_DIR / "REPLAY-REPORT.md"

SOURCE_PATH = ROOT / "fixtures" / "sources" / "wikidata_source.json"

# Digest coverage is NOT a hardcoded filename list here: every retained
# package file except ARTIFACT-DIGESTS.json itself is covered, discovered
# dynamically from the package directory by
# hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.build_artifact_digests
# / verify_artifact_digests_self_consistency — this is what makes the FINAL
# committed package (which includes REPLAY-RESULT.json/REPLAY-REPORT.md once
# --persist has run, in addition to the six files --live already produces)
# fully covered without a second constant to keep in sync.


def _write_text_lf(path: Path, text: str) -> None:
    """Write *text* as UTF-8 bytes with no newline translation (see the
    identical helper/rationale in wikidata_sl0022_alt_route_admission_runner.py:
    Path.write_text applies platform newline translation, which would make a
    locally-computed digest diverge from the digest of the LF-normalized bytes
    git actually stores/checks out."""
    path.write_bytes(text.encode("utf-8"))


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
# --select : offline deterministic selection
# ---------------------------------------------------------------------------


def run_select(*, selection_path: Path = SELECTION_PATH) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        PILOT_SIZE,
        build_selection_document,
        load_reproduced_identity_boundary,
        select_pilot_boatmodels,
    )

    print(
        "HullQ SLICE-0026 Bounded Wikidata Tier-1 Enrichment Evidence Pilot — SELECT "
        "(offline, no network access)",
        flush=True,
    )
    boundary = load_reproduced_identity_boundary()
    print(
        f"  identity boundary reproduced: canonical_boat_models={boundary.canonical_boat_model_count} "
        f"historical_crosswalk={boundary.historical_crosswalk_count}",
        flush=True,
    )
    selection = select_pilot_boatmodels(boundary, count=PILOT_SIZE)
    print(f"  selected {len(selection)} distinct canonical BoatModels", flush=True)

    document = build_selection_document(
        generated_at=datetime.now(tz=UTC).isoformat(), boundary=boundary, selection=selection
    )
    mismatches = _validate_schema(document, SELECTION_SCHEMA_PATH, label="SLICE-0026 selection")
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    selection_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(selection_path, json.dumps(document, indent=2))
    print(f"Selection written to: {selection_path}", flush=True)
    return document


# ---------------------------------------------------------------------------
# --live : rights-gated live acquisition (network access required)
# ---------------------------------------------------------------------------


def run_live(*, user_agent: str, selection_path: Path = SELECTION_PATH) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        ALLOWED_FIELD_POINTERS,
        PilotBoatModel,
        build_evidence_manifest_document,
        filter_to_allowed_evidence,
        summarize_field_coverage,
    )
    from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    print(
        "HullQ SLICE-0026 Bounded Wikidata Tier-1 Enrichment Evidence Pilot — LIVE RUN",
        flush=True,
    )

    # A prior --persist run may have left REPLAY-RESULT.json/REPLAY-REPORT.md
    # on disk. Once evidence_manifest.json below is freshly regenerated,
    # those replay artifacts would describe a bundle set that no longer
    # matches it — remove them now (they are dynamically re-included in
    # digest coverage the moment they exist, per retained_package_filenames,
    # so a stale pair left in place would otherwise be digest-covered as if
    # still valid). --persist regenerates both from the fresh manifest.
    for stale_path in (REPLAY_RESULT_PATH, REPLAY_REPORT_PATH):
        if stale_path.exists():
            stale_path.unlink()
            print(
                f"  removed stale {stale_path.name} (describes a prior evidence_manifest.json; "
                "re-run --persist to regenerate)",
                flush=True,
            )

    if not selection_path.exists():
        print("  selection.json not found; running --select first...", flush=True)
        run_select(selection_path=selection_path)
    selection_doc = json.loads(selection_path.read_text(encoding="utf-8"))
    selection = [
        PilotBoatModel(
            hullq_id=row["hullq_id"], qid=row["qid"], preferred_label=row["preferred_label"]
        )
        for row in selection_doc["boat_models"]
    ]
    qids = [m.qid for m in selection]

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    # Rights/access gate MUST pass before the first network request, or the
    # run performs zero network requests. Only AUTOMATED_INGESTION is checked
    # here: this pilot fetches exactly 100 already-known QIDs (no discovery
    # query), so it is not a BULK_BOOTSTRAP use.
    decision = check_source_use(source, SourceUse.AUTOMATED_INGESTION)
    print(f"  rights_gate.automated_ingestion={decision.outcome!s}", flush=True)
    if decision.outcome != DecisionOutcome.ALLOWED:
        raise SystemExit(
            f"SLICE-0026 refusing before any network request: automated_ingestion gate "
            f"outcome={decision.outcome!s}, reasons={sorted(str(r) for r in decision.reasons)}"
        )

    config = WikidataAdapterConfig(
        user_agent=user_agent, request_timeout_seconds=60.0, item_limit=100
    )

    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        acquired_at = datetime.now(tz=UTC).isoformat()
        entities = adapter.fetch_entities(qids)
        print(f"  fetched {len(entities)} of {len(qids)} requested entities", flush=True)

        fetched_qids = {e.qid for e in entities}
        missing = [q for q in qids if q not in fetched_qids]
        if missing:
            raise SystemExit(
                f"SLICE-0026 live run: {len(missing)} requested QID(s) were not returned by "
                f"wbgetentities (missing/non-item type): {missing}. Refusing to write a "
                "manifest describing a partial pilot."
            )

        full_evidence, quality_report = adapter.extract_field_evidence(
            entities, acquired_at, requested_qid_count=len(qids)
        )
        print(
            f"  extracted {len(full_evidence)} raw evidence item(s) across all properties "
            f"(malformed={quality_report.malformed_statement_count} "
            f"unsupported_qualifier={quality_report.unsupported_qualifier_count})",
            flush=True,
        )

        coverage_counts, _details = summarize_field_coverage(entities, full_evidence)
        for label, buckets in coverage_counts.items():
            print(f"    {label}: {buckets}", flush=True)

        allowed = filter_to_allowed_evidence(full_evidence)
        allowed_by_qid: dict[str, list[Any]] = {}
        for ev in allowed:
            allowed_by_qid.setdefault(ev.subject.id, []).append(ev)
        print(
            f"  retained {len(allowed)} evidence item(s) across the five allowed field pointers "
            f"({sorted(str(p) for p in ALLOWED_FIELD_POINTERS)})",
            flush=True,
        )

        document = build_evidence_manifest_document(
            generated_at=datetime.now(tz=UTC).isoformat(),
            acquired_at=acquired_at,
            selection=selection,
            entities=entities,
            allowed_evidence_by_qid=allowed_by_qid,
            coverage_counts=coverage_counts,
            quality_report=quality_report,
            requested_qid_count=len(qids),
        )

    mismatches = _validate_schema(
        document, EVIDENCE_MANIFEST_SCHEMA_PATH, label="SLICE-0026 evidence manifest"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    EVIDENCE_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(EVIDENCE_MANIFEST_PATH, json.dumps(document, indent=2))
    print(f"Evidence manifest written to: {EVIDENCE_MANIFEST_PATH}", flush=True)

    _write_report(selection_doc, document, replay_result=None)

    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import build_artifact_digests

    # evidence_manifest.json/REPORT.md etc. above are always written to the
    # real SL0026_DIR (only run_select's selection_path is test-overridable),
    # so digest coverage is discovered from that same directory.
    digests_doc = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0026_DIR
    )
    mismatches = _validate_schema(
        digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0026 artifact digests"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(ARTIFACT_DIGESTS_PATH, json.dumps(digests_doc, indent=2))
    print(f"Artifact digests written to: {ARTIFACT_DIGESTS_PATH}", flush=True)

    return document


# ---------------------------------------------------------------------------
# --verify : fully offline recompute + compare (what CI runs)
# ---------------------------------------------------------------------------


def run_verify(
    *,
    selection_path: Path = SELECTION_PATH,
    evidence_manifest_path: Path = EVIDENCE_MANIFEST_PATH,
    artifact_digests_path: Path = ARTIFACT_DIGESTS_PATH,
) -> None:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        PilotBoatModel,
        load_reproduced_identity_boundary,
        rebuild_entities_from_manifest,
        verify_artifact_digests_self_consistency,
        verify_evidence_manifest_self_consistency,
        verify_selection_self_consistency,
    )
    from hullq.sources.wikidata import (
        QUALIFIER_CARRIER_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    print(
        "HullQ SLICE-0026 Bounded Wikidata Tier-1 Enrichment Evidence Pilot — OFFLINE VERIFY "
        "(no network access)",
        flush=True,
    )

    mismatches: list[str] = []

    selection_doc = json.loads(selection_path.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(selection_doc, SELECTION_SCHEMA_PATH, label="SLICE-0026 selection")
    )

    boundary = load_reproduced_identity_boundary()
    print(
        f"  identity boundary reproduced: canonical_boat_models={boundary.canonical_boat_model_count} "
        f"historical_crosswalk={boundary.historical_crosswalk_count}",
        flush=True,
    )
    mismatches.extend(
        verify_selection_self_consistency(boundary=boundary, selection_document=selection_doc)
    )

    selection = [
        PilotBoatModel(
            hullq_id=row["hullq_id"], qid=row["qid"], preferred_label=row["preferred_label"]
        )
        for row in selection_doc["boat_models"]
    ]

    if evidence_manifest_path.exists():
        evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
        mismatches.extend(
            _validate_schema(
                evidence_manifest,
                EVIDENCE_MANIFEST_SCHEMA_PATH,
                label="SLICE-0026 evidence manifest",
            )
        )

        # Zero network access: WikidataAdapter is constructed only to reuse
        # its pure extract_field_evidence — no HTTP method is ever invoked.
        source = {"source_id": "SRC_WIKIDATA_API_2026"}
        config = WikidataAdapterConfig(user_agent="HullQ/0.1 (offline-verify@example.org)")
        import httpx

        with httpx.Client() as client:
            adapter = WikidataAdapter(source=source, config=config, http_client=client)
            rebuilt_entities = rebuild_entities_from_manifest(evidence_manifest)
            # SLICE-0027 pinned note: this reproduction must keep exercising the
            # exact P642-only extraction behavior originally captured in this
            # retained package, independent of the SLICE-0027-evidenced P518/
            # P3831 alternate carriers the shared adapter now also recognizes by
            # default. Pinning QUALIFIER_CARRIER_VERSION_SLICE0008 here is what
            # lets this retained package keep "reproducing deterministically"
            # forever, rather than drifting the moment a later slice legitimately
            # extends the adapter's qualifier-carrier vocabulary. SLICE-0027's own
            # before/after coverage delta is measured separately (see
            # research/stage3/sl0027-wikidata-qualifier-semantics/), against the
            # current (unpinned) adapter default.
            rebuilt_full_evidence, _report = adapter.extract_field_evidence(
                rebuilt_entities,
                evidence_manifest.get("acquired_at", ""),
                requested_qid_count=len(rebuilt_entities),
                qualifier_carrier_version=QUALIFIER_CARRIER_VERSION_SLICE0008,
            )
        print(
            f"  rebuilt {len(rebuilt_entities)} entities and re-extracted "
            f"{len(rebuilt_full_evidence)} raw evidence item(s) offline from retained raw_entities",
            flush=True,
        )
        mismatches.extend(
            verify_evidence_manifest_self_consistency(
                selection=selection,
                entities=rebuilt_entities,
                full_evidence=rebuilt_full_evidence,
                evidence_manifest=evidence_manifest,
            )
        )

        if artifact_digests_path.exists():
            digests_doc = json.loads(artifact_digests_path.read_text(encoding="utf-8"))
            mismatches.extend(
                _validate_schema(
                    digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0026 artifact digests"
                )
            )
            mismatches.extend(
                verify_artifact_digests_self_consistency(
                    artifact_digests=digests_doc, package_dir=artifact_digests_path.parent
                )
            )
        else:
            mismatches.append(
                f"required ARTIFACT-DIGESTS.json not found at {artifact_digests_path}"
            )
    else:
        print(
            "  evidence_manifest.json not found: no --live acquisition retained yet; not treated "
            "as an offline-verify failure",
            flush=True,
        )

    if mismatches:
        print("\nOFFLINE VERIFY FAILED:", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained selection/evidence "
        "manifest and artifact digests.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(
    selection_doc: dict[str, Any],
    evidence_manifest: dict[str, Any],
    *,
    report_path: Path = REPORT_PATH,
    replay_result: dict[str, Any] | None = None,
) -> None:
    boundary = selection_doc["identity_boundary"]
    coverage = evidence_manifest["field_coverage"]
    usage = evidence_manifest["usage_metrics"]
    lines = [
        "# HullQ SLICE-0026 Bounded Wikidata Tier-1 Enrichment Evidence Pilot Report",
        "",
        f"**Selection generated_at:** {selection_doc['generated_at']}  ",
        f"**Evidence manifest generated_at:** {evidence_manifest['generated_at']}  ",
        f"**Acquired at:** {evidence_manifest['acquired_at']}  ",
        f"**Source:** {evidence_manifest['source_id']}",
        "",
        "## SCOPE",
        "",
        "Evidence-path pilot only. Does not create/mutate canonical BoatModel identity, does not "
        "mint or infer a BoatDesign generation, does not create a FieldResolution, and does not "
        "claim these BoatModels are fully Tier-1 searchable.",
        "",
        "## IDENTITY BOUNDARY (reproduced, fail-closed)",
        "",
        f"- canonical BoatModels: **{boundary['canonical_boat_model_count']}** (must equal 1,770)",
        f"- historical QID -> HullQ-ID mappings: **{boundary['historical_crosswalk_count']}** (must equal 1,772)",
        f"- baseline manifest sha256: `{boundary['baseline_manifest_sha256']}`",
        f"- delta manifest sha256: `{boundary['delta_manifest_sha256']}`",
        "",
        f"## PILOT SELECTION ({selection_doc['pilot_size']} BoatModels)",
        "",
        f"- ordering: {selection_doc['selection_ordering']}",
        "- no discovery request was issued; only the selected accepted QIDs were fetched",
        "",
        "## REQUEST / RECORD COUNTS",
        "",
        f"- requested QID count: **{usage['requested_qid_count']}**",
        f"- fetched entity count: **{usage['fetched_entity_count']}**",
        f"- HTTP requests attributed to {evidence_manifest['source_id']}: **{usage['retrieval_count_attributed']}**",
        "",
        "## ALLOWED FIELD POINTERS",
        "",
    ]
    lines.extend(f"- `{p}`" for p in evidence_manifest["allowed_field_pointers"])
    lines += [
        "",
        "## PER-FIELD COVERAGE",
        "",
        "Four mutually exclusive, exhaustive states per (BoatModel, field); counts sum to the "
        "pilot size for every field.",
        "",
        "| field | normalized_candidate_present | source_statement_present | "
        "unsupported_or_malformed | no_usable_value |",
        "|---|---|---|---|---|",
    ]
    for field, buckets in coverage.items():
        lines.append(
            f"| {field} | {buckets['normalized_candidate_present']} | "
            f"{buckets['source_statement_present']} | {buckets['unsupported_or_malformed']} | "
            f"{buckets['no_usable_value']} |"
        )
    lines += [
        "",
        "**Note on `unsupported_or_malformed` for LOA/LWL and displacement:** these two field "
        "pairs share one raw Wikidata property (P2043 for LOA/LWL, P2067 for displacement/"
        "ballast), disambiguated only by a P642 qualifier. A statement whose qualifier value "
        "matches neither sibling field is counted as unsupported/malformed against BOTH sibling "
        "fields (a conservative upper bound), because the adapter's public outputs do not "
        "attribute an unmatched shared-property statement to only one of the two fields without "
        "reimplementing qualifier parsing. See "
        "`hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.classify_entity_field_coverage`.",
        "",
        "## GLOBAL EXTRACTION QUALITY (all properties the adapter extracts, not decomposed per field)",
        "",
        f"- malformed_statement_count: **{evidence_manifest['quality_report_global']['malformed_statement_count']}**",
        f"- unsupported_qualifier_count: **{evidence_manifest['quality_report_global']['unsupported_qualifier_count']}**",
        "",
    ]
    if replay_result is not None:
        lines += [
            "## POSTGRESQL PERSISTENCE EVIDENCE — LOCAL (this implementation session)",
            "",
            (
                "Evidence below was measured locally by running "
                "`scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --persist` "
                "against a real PostgreSQL instance during implementation. Remote GitHub Actions "
                "CI independently re-runs the same step at the exact pushed head and is the "
                "authoritative external verification."
            ),
            "",
            f"- PostgreSQL version: `{replay_result['postgresql_version']}`",
            f"- bundles imported (first pass): {replay_result['first_pass']['imported']}",
            f"- bundles already-present (first pass): {replay_result['first_pass']['already_present']}",
            f"- bundles conflict (first pass): {replay_result['first_pass']['conflict']}",
            f"- readback mismatches: {replay_result['readback_mismatches']}",
            f"- re-import (idempotency) already_imported: {replay_result['reimport']['already_imported']}",
            f"- re-import conflict: {replay_result['reimport']['conflict']}",
            f"- canonical_boat_models row count after both passes: {replay_result['canonical_boat_model_row_count']} (must be 0 — SLICE-0026 never imports a canonical identity admission)",
            f"- canonical_boat_designs row count after both passes: {replay_result['canonical_boat_design_row_count']} (must be 0)",
            "",
            f"### RESULT: zero-mutation and idempotency proof clear (local): **{replay_result['clear']}**",
            "",
        ]
    else:
        lines += [
            "## POSTGRESQL PERSISTENCE EVIDENCE",
            "",
            "PENDING until persisted against real PostgreSQL (db-integration CI or a local "
            "`--persist` run).",
            "",
        ]
    lines += [
        "## SCOPE CONFIRMATION",
        "",
        "- No discovery/SPARQL request was made; only the 100 selected known QIDs were fetched.",
        "- No canonical BoatModel/BoatDesign row was created or mutated.",
        "- No FieldResolution was created.",
        "- Existing Wikidata adapter extraction and SLICE-0004 normalization were reused, not "
        "reimplemented.",
        "- SLICE-0027 was not created or started.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(report_path, "\n".join(lines) + "\n")
    print(f"Report written to: {report_path}", flush=True)


# ---------------------------------------------------------------------------
# --persist : offline PostgreSQL import/readback/idempotency proof
# ---------------------------------------------------------------------------


def persist_and_verify(
    db_url: str,
    *,
    schema_name: str | None = None,
    selection_path: Path = SELECTION_PATH,
    evidence_manifest_path: Path = EVIDENCE_MANIFEST_PATH,
) -> dict[str, Any]:
    """Offline (no network access) PostgreSQL persistence proof.

    Rebuilds the pilot ``ResearchEvidenceBundle``s from the already retained,
    offline-verified ``selection.json``/``evidence_manifest.json`` (no live
    Wikidata request), imports them into an isolated schema via the existing
    SLICE-0013 importer, reads every persisted evidence item back and
    compares it to the in-memory bundle, re-imports the exact same bundles to
    prove idempotency, and confirms zero canonical BoatModel/BoatDesign row
    exists (SLICE-0026 never calls the canonical-identity importer).

    ``selection_path``/``evidence_manifest_path`` default to the real
    retained SLICE-0026 package but may be overridden (e.g. by
    ``tests/persistence/``) to exercise this exact mechanism against a small
    synthetic pair without touching the real retained artifacts.
    """
    import contextlib
    from collections.abc import Iterator

    import psycopg

    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        PilotBoatModel,
        build_pilot_bundle,
        filter_to_allowed_evidence,
    )
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations
    from hullq.persistence.readback import fetch_bundle_snapshot, fetch_evidence

    selection_doc = json.loads(selection_path.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))

    selection = [
        PilotBoatModel(
            hullq_id=row["hullq_id"], qid=row["qid"], preferred_label=row["preferred_label"]
        )
        for row in selection_doc["boat_models"]
    ]

    # Rebuild the exact FieldEvidence used for evidence_manifest.json purely
    # from its own retained raw_entities — no network access.
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        rebuild_entities_from_manifest,
    )
    from hullq.sources.wikidata import (
        QUALIFIER_CARRIER_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (offline-persist@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        entities = rebuild_entities_from_manifest(evidence_manifest)
        # See the identical SLICE-0027 pinning note in run_verify() above: this
        # persistence replay must keep importing exactly the bundles SLICE-0026
        # originally captured and had independently reviewed/accepted.
        full_evidence, _report = adapter.extract_field_evidence(
            entities,
            evidence_manifest.get("acquired_at", ""),
            requested_qid_count=len(entities),
            qualifier_carrier_version=QUALIFIER_CARRIER_VERSION_SLICE0008,
        )

    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    bundles = [build_pilot_bundle(m, by_qid.get(m.qid, [])) for m in selection]

    schema_name = (
        schema_name or "hullq_sl0026_run_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
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
        "schema_version": "sl0026-replay-v1",
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
        "HullQ SLICE-0026 Bounded Wikidata Tier-1 Enrichment Evidence Pilot — PERSIST "
        "(offline, no network access)",
        flush=True,
    )
    result = persist_and_verify(db_url)
    REPLAY_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(REPLAY_RESULT_PATH, json.dumps(result, indent=2))
    print(f"Replay result written to: {REPLAY_RESULT_PATH}", flush=True)

    selection_doc = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    _write_report(selection_doc, evidence_manifest, replay_result=result)
    _write_text_lf(
        REPLAY_REPORT_PATH,
        f"# HullQ SLICE-0026 PostgreSQL Persistence Replay Report\n\n"
        f"```json\n{json.dumps(result, indent=2)}\n```\n",
    )
    print(f"Replay report written to: {REPLAY_REPORT_PATH}", flush=True)

    # REPORT.md changed above (replay evidence appended) and REPLAY-RESULT.json/
    # REPLAY-REPORT.md now exist for the first time; rebuild the retained
    # artifact digests so ARTIFACT-DIGESTS.json covers every retained package
    # file byte-accurately, including the two just-written replay artifacts.
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import build_artifact_digests

    digests_doc = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0026_DIR
    )
    mismatches = _validate_schema(
        digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0026 artifact digests"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(ARTIFACT_DIGESTS_PATH, json.dumps(digests_doc, indent=2))
    print(f"Artifact digests rewritten to: {ARTIFACT_DIGESTS_PATH}", flush=True)

    if not result["clear"]:
        raise SystemExit(1)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--select", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--persist", action="store_true")
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--db-url", default=None)
    args = parser.parse_args()

    if args.select:
        run_select()
    elif args.live:
        if not args.user_agent:
            raise SystemExit("--live requires --user-agent")
        run_live(user_agent=args.user_agent)
    elif args.verify:
        run_verify()
    elif args.persist:
        if not args.db_url:
            raise SystemExit("--persist requires --db-url")
        run_persist(args.db_url)


if __name__ == "__main__":
    main()
