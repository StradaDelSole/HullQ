"""SLICE-0028 full-boundary Wikidata Tier-1 evidence rollout runner.

Five independent modes:

``--linkage``
    Offline (no network access): reproduces the accepted 1,770/1,772
    identity boundary from the retained SLICE-0017/0018 manifests (failing
    closed on drift), derives the full-boundary QID -> canonical-BoatModel
    linkage from it (structurally multi-QID-safe, though the accepted
    boundary is bijective today), and writes
    ``research/stage3/sl0028-wikidata-tier1-full-boundary/linkage.json``.

``--live``
    Rights-gated live acquisition: fetches every distinct linkage-derived
    request QID (the entire accepted full boundary — 1,770 QIDs today) via
    the existing ``WikidataAdapter.fetch_entities_bootstrap`` (no discovery
    query), fails closed if the response does not exactly cover every
    requested QID (``hullq.bootstrap.wikidata_tier0_sl0018.
    verify_entity_acquisition_completeness`` — a retrieval failure or a
    missing/redirected QID is never silently reclassified as
    ``no_usable_value``), extracts field evidence via the existing
    ``WikidataAdapter.extract_field_evidence``, classifies per-field coverage
    at both source-QID and canonical-BoatModel level, computes disagreement
    diagnostics and the non-canonical ``basic_searchable_evidence_precursor``
    metric, and writes ``evidence_manifest.json`` / ``coverage.json`` /
    ``disagreement_diagnostics.json`` /
    ``basic_searchable_evidence_precursor.json`` / ``REPORT.md`` /
    ``ARTIFACT-DIGESTS.json``. Requires network access and is NOT part of
    normal CI. Builds ``linkage.json`` first if it does not already exist.

``--recompute``
    Offline (no network access, no re-acquisition): rebuilds every derived
    document (``evidence_manifest.json`` / ``coverage.json`` /
    ``disagreement_diagnostics.json`` /
    ``basic_searchable_evidence_precursor.json`` / ``REPORT.md`` /
    ``ARTIFACT-DIGESTS.json``) from the already-retained
    ``evidence_manifest.json``'s own ``raw_entities``, without a new Wikidata
    request. Used after a pure-logic fix to a derived value (e.g. a coverage/
    disagreement classification correction) when the underlying acquired
    evidence has not changed. Preserves the original retained live-
    acquisition telemetry (``retrieval_count_attributed``) rather than
    overwriting it with a fabricated zero from this network-free run.

``--verify``
    Fully offline (zero network access): reloads every retained document,
    recomputes the identity boundary and linkage from the retained
    SLICE-0017/0018 manifests, rebuilds every acquired entity from
    ``evidence_manifest.json``'s own retained ``raw_entities`` and reruns the
    existing adapter's ``extract_field_evidence`` on them (no network — the
    adapter's HTTP client is never invoked), and compares every recomputed
    value against the retained documents. This is what normal CI runs.

``--persist``
    Offline (no network access) PostgreSQL persistence proof: imports one
    ``ResearchEvidenceBundle`` per requested QID (rebuilt from the already-
    retained, offline-verified ``evidence_manifest.json``) into an isolated
    schema, reads every persisted evidence item back and compares against the
    in-memory bundle, then re-imports the exact same bundles to prove
    idempotency, and confirms zero canonical BoatModel/BoatDesign row was
    created. Writes ``REPLAY-RESULT.json`` + ``REPLAY-REPORT.md``.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --linkage

    uv run python scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)"

    uv run python scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --recompute

    uv run python scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --verify

    uv run python scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --persist \\
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
LINKAGE_PATH = SL0028_DIR / "linkage.json"
LINKAGE_SCHEMA_PATH = SL0028_DIR / "linkage_schema.json"
EVIDENCE_MANIFEST_PATH = SL0028_DIR / "evidence_manifest.json"
EVIDENCE_MANIFEST_SCHEMA_PATH = SL0028_DIR / "evidence_manifest_schema.json"
COVERAGE_PATH = SL0028_DIR / "coverage.json"
COVERAGE_SCHEMA_PATH = SL0028_DIR / "coverage_schema.json"
DISAGREEMENT_PATH = SL0028_DIR / "disagreement_diagnostics.json"
DISAGREEMENT_SCHEMA_PATH = SL0028_DIR / "disagreement_schema.json"
PRECURSOR_PATH = SL0028_DIR / "basic_searchable_evidence_precursor.json"
PRECURSOR_SCHEMA_PATH = SL0028_DIR / "basic_searchable_evidence_precursor_schema.json"
REPORT_PATH = SL0028_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0028_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0028_DIR / "artifact_digests_schema.json"
REPLAY_RESULT_PATH = SL0028_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = SL0028_DIR / "REPLAY-REPORT.md"

SOURCE_PATH = ROOT / "fixtures" / "sources" / "wikidata_source.json"


def _write_text_lf(path: Path, text: str) -> None:
    """Write *text* as UTF-8 bytes with no newline translation (identical
    rationale to the SLICE-0026/0027/0022 runners): Path.write_text applies
    platform newline translation, which would make a locally-computed digest
    diverge from the digest of the LF-normalized bytes git actually stores/
    checks out."""
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
# --linkage : offline deterministic full-boundary linkage derivation
# ---------------------------------------------------------------------------


def run_linkage(*, linkage_path: Path = LINKAGE_PATH) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        load_reproduced_identity_boundary,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        build_full_boundary_linkage,
        build_historical_registry_reconciliation_block,
        build_linkage_document,
        distinct_request_qids,
        load_full_historical_registry_reconciliation,
        verify_full_boundary_linkage,
    )

    print(
        "HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout — LINKAGE "
        "(offline, no network access)",
        flush=True,
    )
    boundary = load_reproduced_identity_boundary()
    print(
        f"  identity boundary reproduced: canonical_boat_models={boundary.canonical_boat_model_count} "
        f"historical_crosswalk={boundary.historical_crosswalk_count}",
        flush=True,
    )
    linkage = build_full_boundary_linkage(boundary)
    problems = verify_full_boundary_linkage(boundary=boundary, linkage=linkage)
    if problems:
        for p in problems:
            print(f"  - {p}", flush=True)
        raise SystemExit(1)
    request_qids = distinct_request_qids(linkage)
    print(
        f"  linked {len(linkage)} canonical BoatModels to {len(request_qids)} distinct request "
        "QIDs (no discovery request was issued)",
        flush=True,
    )
    multi_qid_models = [e for e in linkage if len(e.qids) > 1]
    print(f"  BoatModels with more than one accepted QID: {len(multi_qid_models)}", flush=True)

    _full_crosswalk, reserved_entries = load_full_historical_registry_reconciliation(
        boundary=boundary
    )
    reconciliation = build_historical_registry_reconciliation_block(
        boundary=boundary, reserved_entries=reserved_entries
    )
    print(
        f"  historical registry reconciliation: {reconciliation['historical_registry_count']} full "
        f"registry = {reconciliation['canonical_auto_admit_linkage_count']} canonical AUTO_ADMIT "
        f"linkage + {reconciliation['non_canonical_reserved_count']} non-canonical reserved",
        flush=True,
    )
    for e in reserved_entries:
        print(f"    reserved: {e.qid} -> {e.reserved_hullq_id} (decision={e.decision})", flush=True)

    document = build_linkage_document(
        generated_at=datetime.now(tz=UTC).isoformat(),
        boundary=boundary,
        linkage=linkage,
        historical_registry_reconciliation=reconciliation,
    )
    mismatches = _validate_schema(document, LINKAGE_SCHEMA_PATH, label="SLICE-0028 linkage")
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    linkage_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(linkage_path, json.dumps(document, indent=2))
    print(f"Linkage written to: {linkage_path}", flush=True)
    return document


# ---------------------------------------------------------------------------
# Shared: build + write every derived document from already-acquired
# entities/evidence (used by both --live, right after a fresh acquisition,
# and --recompute, which regenerates every derived document offline from an
# already-retained evidence_manifest.json's raw_entities without a new
# acquisition -- e.g. after a pure-logic fix to a derived value).
# ---------------------------------------------------------------------------


def _build_and_write_derived_documents(
    *,
    linkage_doc: dict[str, Any],
    linkage: list[Any],
    entities: list[Any],
    full_evidence: list[Any],
    quality_report: Any,
    requested_qid_count: int,
    acquisition_failure_count: int,
    acquired_at: str,
) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        filter_to_allowed_evidence,
        summarize_field_coverage,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        ALLOWED_FIELD_POINTERS,
        build_artifact_digests,
        build_basic_searchable_precursor_document,
        build_coverage_document,
        build_disagreement_document,
        build_evidence_manifest_document,
        compute_boat_model_field_disagreements,
        summarize_boat_model_field_coverage,
    )

    print(
        f"  extracted {len(full_evidence)} raw evidence item(s) across all properties "
        f"(malformed={quality_report.malformed_statement_count} "
        f"unsupported_qualifier={quality_report.unsupported_qualifier_count})",
        flush=True,
    )

    source_counts, source_details = summarize_field_coverage(entities, full_evidence)
    boat_model_counts, boat_model_details = summarize_boat_model_field_coverage(
        linkage, source_details
    )
    print("  source-QID-level coverage:", flush=True)
    for label, buckets in source_counts.items():
        print(f"    {label}: {buckets}", flush=True)
    print("  BoatModel-level coverage:", flush=True)
    for label, buckets in boat_model_counts.items():
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

    evidence_manifest = build_evidence_manifest_document(
        generated_at=datetime.now(tz=UTC).isoformat(),
        acquired_at=acquired_at,
        linkage=linkage,
        entities=entities,
        allowed_evidence_by_qid=allowed_by_qid,
        quality_report=quality_report,
        requested_qid_count=requested_qid_count,
        acquisition_failure_count=acquisition_failure_count,
    )

    disagreements = compute_boat_model_field_disagreements(
        linkage, entities, full_evidence, source_details
    )
    print(
        f"  candidate-multiplicity/value-disagreement flagged cases: {len(disagreements)}",
        flush=True,
    )

    precursor_doc = build_basic_searchable_precursor_document(
        generated_at=datetime.now(tz=UTC).isoformat(),
        boat_model_count=len(linkage),
        boat_model_coverage=boat_model_details,
    )
    print(
        "  basic_searchable_evidence_precursor (non-canonical): "
        f"{precursor_doc['qualifying_boat_model_count']}/{precursor_doc['boat_model_count']} "
        f"({precursor_doc['qualifying_boat_model_percentage']}%)",
        flush=True,
    )

    mismatches = _validate_schema(
        evidence_manifest, EVIDENCE_MANIFEST_SCHEMA_PATH, label="SLICE-0028 evidence manifest"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    EVIDENCE_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(EVIDENCE_MANIFEST_PATH, json.dumps(evidence_manifest, indent=2))
    print(f"Evidence manifest written to: {EVIDENCE_MANIFEST_PATH}", flush=True)

    coverage_doc = build_coverage_document(
        generated_at=datetime.now(tz=UTC).isoformat(),
        boat_model_count=len(linkage),
        source_qid_count=len(entities),
        source_qid_coverage_counts=source_counts,
        boat_model_coverage_counts=boat_model_counts,
    )
    mismatches = _validate_schema(coverage_doc, COVERAGE_SCHEMA_PATH, label="SLICE-0028 coverage")
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(COVERAGE_PATH, json.dumps(coverage_doc, indent=2))
    print(f"Coverage written to: {COVERAGE_PATH}", flush=True)

    disagreement_doc = build_disagreement_document(
        generated_at=datetime.now(tz=UTC).isoformat(), disagreements=disagreements
    )
    mismatches = _validate_schema(
        disagreement_doc, DISAGREEMENT_SCHEMA_PATH, label="SLICE-0028 disagreement diagnostics"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(DISAGREEMENT_PATH, json.dumps(disagreement_doc, indent=2))
    print(f"Disagreement diagnostics written to: {DISAGREEMENT_PATH}", flush=True)

    mismatches = _validate_schema(
        precursor_doc, PRECURSOR_SCHEMA_PATH, label="SLICE-0028 basic_searchable_evidence_precursor"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(PRECURSOR_PATH, json.dumps(precursor_doc, indent=2))
    print(f"basic_searchable_evidence_precursor written to: {PRECURSOR_PATH}", flush=True)

    _write_report(
        linkage_doc,
        evidence_manifest,
        coverage_doc,
        disagreement_doc,
        precursor_doc,
        replay_result=None,
    )

    digests_doc = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0028_DIR
    )
    mismatches = _validate_schema(
        digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0028 artifact digests"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(ARTIFACT_DIGESTS_PATH, json.dumps(digests_doc, indent=2))
    print(f"Artifact digests written to: {ARTIFACT_DIGESTS_PATH}", flush=True)

    return evidence_manifest


# ---------------------------------------------------------------------------
# --live : rights-gated live acquisition (network access required)
# ---------------------------------------------------------------------------


def run_live(*, user_agent: str, linkage_path: Path = LINKAGE_PATH) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        BoatModelLinkage,
        distinct_request_qids,
    )
    from hullq.bootstrap.wikidata_tier0_sl0018 import (
        DeltaCompletenessError,
        verify_entity_acquisition_completeness,
    )
    from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    print(
        "HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout — LIVE RUN",
        flush=True,
    )

    # A prior --persist run may have left REPLAY-RESULT.json/REPLAY-REPORT.md
    # on disk describing a bundle set that a fresh evidence_manifest.json
    # below would no longer match — remove them now (identical rationale to
    # the SLICE-0026/0027 runners). --persist regenerates both.
    for stale_path in (REPLAY_RESULT_PATH, REPLAY_REPORT_PATH):
        if stale_path.exists():
            stale_path.unlink()
            print(
                f"  removed stale {stale_path.name} (describes a prior evidence_manifest.json; "
                "re-run --persist to regenerate)",
                flush=True,
            )

    if not linkage_path.exists():
        print("  linkage.json not found; running --linkage first...", flush=True)
        run_linkage(linkage_path=linkage_path)
    linkage_doc = json.loads(linkage_path.read_text(encoding="utf-8"))
    linkage = [
        BoatModelLinkage(
            hullq_id=row["hullq_id"],
            qids=tuple(row["qids"]),
            preferred_label_by_qid=row["preferred_label_by_qid"],
        )
        for row in linkage_doc["boat_models"]
    ]
    request_qids = list(distinct_request_qids(linkage))

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    # Rights/access gate MUST pass before the first network request, or the
    # run performs zero network requests. Only AUTOMATED_INGESTION is checked
    # here: this rollout fetches every already-known accepted QID (no
    # discovery query), matching the existing accepted
    # WikidataAdapter.fetch_entities_bootstrap gate contract exactly (never
    # adding or reinterpreting source rights).
    decision = check_source_use(source, SourceUse.AUTOMATED_INGESTION)
    print(f"  rights_gate.automated_ingestion={decision.outcome!s}", flush=True)
    if decision.outcome != DecisionOutcome.ALLOWED:
        raise SystemExit(
            f"SLICE-0028 refusing before any network request: automated_ingestion gate "
            f"outcome={decision.outcome!s}, reasons={sorted(str(r) for r in decision.reasons)}"
        )

    config = WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=60.0)

    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        acquired_at = datetime.now(tz=UTC).isoformat()
        try:
            entities = adapter.fetch_entities_bootstrap(request_qids)
        except Exception as exc:
            raise SystemExit(
                "SLICE-0028 live run: acquisition failed before every requested QID could be "
                f"deterministically classified — refusing to write a manifest describing "
                f"partial/misclassified coverage. Underlying error: {exc!r}"
            ) from exc
        print(f"  fetched {len(entities)} of {len(request_qids)} requested entities", flush=True)

        try:
            verify_entity_acquisition_completeness(request_qids, entities)
        except DeltaCompletenessError as exc:
            raise SystemExit(
                f"SLICE-0028 live run: acquisition did not exactly cover every requested QID; "
                f"refusing to write a manifest describing partial full-boundary coverage: {exc}"
            ) from exc
        print(
            "  acquisition completeness verified: every requested QID has exactly one returned "
            "entity, no unexpected/duplicate QID",
            flush=True,
        )

        full_evidence, quality_report = adapter.extract_field_evidence(
            entities, acquired_at, requested_qid_count=len(request_qids)
        )

        return _build_and_write_derived_documents(
            linkage_doc=linkage_doc,
            linkage=linkage,
            entities=entities,
            full_evidence=full_evidence,
            quality_report=quality_report,
            requested_qid_count=len(request_qids),
            acquisition_failure_count=0,
            acquired_at=acquired_at,
        )


# ---------------------------------------------------------------------------
# --recompute : offline regeneration from an already-retained
# evidence_manifest.json's raw_entities, WITHOUT a new acquisition (used
# after a pure-logic fix to a derived value; preserves the original retained
# live-acquisition telemetry rather than fabricating a fresh, zero,
# recomputed retrieval count).
# ---------------------------------------------------------------------------


def run_recompute(
    *,
    linkage_path: Path = LINKAGE_PATH,
    evidence_manifest_path: Path = EVIDENCE_MANIFEST_PATH,
) -> dict[str, Any]:
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        BoatModelLinkage,
        rebuild_entities_from_manifest,
    )
    from hullq.sources.wikidata import (
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    print(
        "HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout — RECOMPUTE "
        "(offline, no network access, no re-acquisition)",
        flush=True,
    )

    for stale_path in (REPLAY_RESULT_PATH, REPLAY_REPORT_PATH):
        if stale_path.exists():
            stale_path.unlink()
            print(
                f"  removed stale {stale_path.name} (describes a prior evidence_manifest.json; "
                "re-run --persist to regenerate)",
                flush=True,
            )

    linkage_doc = json.loads(linkage_path.read_text(encoding="utf-8"))
    linkage = [
        BoatModelLinkage(
            hullq_id=row["hullq_id"],
            qids=tuple(row["qids"]),
            preferred_label_by_qid=row["preferred_label_by_qid"],
        )
        for row in linkage_doc["boat_models"]
    ]

    existing_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
    existing_usage = existing_manifest["usage_metrics"]
    acquired_at = existing_manifest.get("acquired_at", "")

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (offline-recompute@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        entities = rebuild_entities_from_manifest(existing_manifest)
        # SLICE-0030 pinned note: --recompute regenerates derived documents
        # (coverage.json, disagreement diagnostics, REPORT.md, etc.) from the
        # retained raw_entities without re-acquisition. Pinning
        # UNIT_QID_MAP_VERSION_SLICE0008 keeps that regeneration reproducing
        # exactly the (uncorrected) mass-unit extraction behavior this
        # retained package originally captured, independent of the
        # SLICE-0030 corrected adapter default.
        full_evidence, quality_report = adapter.extract_field_evidence(
            entities,
            acquired_at,
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )

    # This run performs zero network requests, so quality_report's own
    # retrieval_count_attributed is 0 -- NOT a truthful recomputation of the
    # original --live run's HTTP request count. Preserve the original
    # retained live-acquisition telemetry instead of overwriting it with a
    # fabricated zero (WikidataQualityReport is a plain, non-frozen dataclass).
    quality_report.retrieval_count_attributed = existing_usage["retrieval_count_attributed"]

    print(
        f"  rebuilt {len(entities)} entities offline from retained raw_entities "
        f"(preserving original retrieval_count_attributed={quality_report.retrieval_count_attributed})",
        flush=True,
    )

    return _build_and_write_derived_documents(
        linkage_doc=linkage_doc,
        linkage=linkage,
        entities=entities,
        full_evidence=full_evidence,
        quality_report=quality_report,
        requested_qid_count=existing_usage["requested_qid_count"],
        acquisition_failure_count=existing_usage["acquisition_failure_count"],
        acquired_at=acquired_at,
    )


# ---------------------------------------------------------------------------
# --verify : fully offline recompute + compare (what CI runs)
# ---------------------------------------------------------------------------


def run_verify(
    *,
    linkage_path: Path = LINKAGE_PATH,
    evidence_manifest_path: Path = EVIDENCE_MANIFEST_PATH,
    coverage_path: Path = COVERAGE_PATH,
    disagreement_path: Path = DISAGREEMENT_PATH,
    precursor_path: Path = PRECURSOR_PATH,
    artifact_digests_path: Path = ARTIFACT_DIGESTS_PATH,
) -> None:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (
        load_reproduced_identity_boundary,
        summarize_field_coverage,
    )
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        BoatModelLinkage,
        rebuild_entities_from_manifest,
        summarize_boat_model_field_coverage,
        verify_artifact_digests_self_consistency,
        verify_basic_searchable_precursor_self_consistency,
        verify_coverage_self_consistency,
        verify_disagreement_self_consistency,
        verify_evidence_manifest_self_consistency,
        verify_full_boundary_linkage,
        verify_linkage_document_self_consistency,
    )
    from hullq.sources.wikidata import (
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    print(
        "HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout — OFFLINE VERIFY "
        "(no network access)",
        flush=True,
    )

    mismatches: list[str] = []

    boundary = load_reproduced_identity_boundary()
    print(
        f"  identity boundary reproduced: canonical_boat_models={boundary.canonical_boat_model_count} "
        f"historical_crosswalk={boundary.historical_crosswalk_count}",
        flush=True,
    )

    if not linkage_path.exists():
        raise SystemExit(f"required {linkage_path} not found; run --linkage first")
    linkage_doc = json.loads(linkage_path.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(linkage_doc, LINKAGE_SCHEMA_PATH, label="SLICE-0028 linkage")
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

    if evidence_manifest_path.exists():
        evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
        mismatches.extend(
            _validate_schema(
                evidence_manifest,
                EVIDENCE_MANIFEST_SCHEMA_PATH,
                label="SLICE-0028 evidence manifest",
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
            # SLICE-0030 pinned note: this retained package's evidence was
            # originally extracted under the (uncorrected) SLICE-0008
            # mass-unit map — the only map that existed before SLICE-0030.
            # Pinning UNIT_QID_MAP_VERSION_SLICE0008 keeps this offline
            # verifier reproducing exactly that extraction behavior forever,
            # independent of the SLICE-0030 corrected adapter default.
            # SLICE-0030's own before/after coverage delta is measured
            # separately (see research/stage3/sl0030-wikidata-mass-unit-correction/).
            rebuilt_full_evidence, rebuilt_report = adapter.extract_field_evidence(
                rebuilt_entities,
                evidence_manifest.get("acquired_at", ""),
                requested_qid_count=len(rebuilt_entities),
                unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
            )
        print(
            f"  rebuilt {len(rebuilt_entities)} entities and re-extracted "
            f"{len(rebuilt_full_evidence)} raw evidence item(s) offline from retained raw_entities",
            flush=True,
        )
        mismatches.extend(
            verify_evidence_manifest_self_consistency(
                linkage=linkage,
                entities=rebuilt_entities,
                full_evidence=rebuilt_full_evidence,
                quality_report=rebuilt_report,
                evidence_manifest=evidence_manifest,
            )
        )

        _source_counts, source_details = summarize_field_coverage(
            rebuilt_entities, rebuilt_full_evidence
        )
        _boat_model_counts, boat_model_details = summarize_boat_model_field_coverage(
            linkage, source_details
        )

        if coverage_path.exists():
            coverage_doc = json.loads(coverage_path.read_text(encoding="utf-8"))
            mismatches.extend(
                _validate_schema(coverage_doc, COVERAGE_SCHEMA_PATH, label="SLICE-0028 coverage")
            )
            mismatches.extend(
                verify_coverage_self_consistency(
                    linkage=linkage,
                    entities=rebuilt_entities,
                    full_evidence=rebuilt_full_evidence,
                    document=coverage_doc,
                )
            )
        else:
            mismatches.append(f"required {coverage_path} not found")

        if disagreement_path.exists():
            disagreement_doc = json.loads(disagreement_path.read_text(encoding="utf-8"))
            mismatches.extend(
                _validate_schema(
                    disagreement_doc,
                    DISAGREEMENT_SCHEMA_PATH,
                    label="SLICE-0028 disagreement diagnostics",
                )
            )
            mismatches.extend(
                verify_disagreement_self_consistency(
                    linkage=linkage,
                    entities=rebuilt_entities,
                    full_evidence=rebuilt_full_evidence,
                    source_qid_details=source_details,
                    document=disagreement_doc,
                )
            )
        else:
            mismatches.append(f"required {disagreement_path} not found")

        if precursor_path.exists():
            precursor_doc = json.loads(precursor_path.read_text(encoding="utf-8"))
            mismatches.extend(
                _validate_schema(
                    precursor_doc,
                    PRECURSOR_SCHEMA_PATH,
                    label="SLICE-0028 basic_searchable_evidence_precursor",
                )
            )
            mismatches.extend(
                verify_basic_searchable_precursor_self_consistency(
                    boat_model_count=len(linkage),
                    boat_model_coverage=boat_model_details,
                    document=precursor_doc,
                )
            )
        else:
            mismatches.append(f"required {precursor_path} not found")

        if artifact_digests_path.exists():
            digests_doc = json.loads(artifact_digests_path.read_text(encoding="utf-8"))
            mismatches.extend(
                _validate_schema(
                    digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0028 artifact digests"
                )
            )
            mismatches.extend(
                verify_artifact_digests_self_consistency(
                    artifact_digests=digests_doc, package_dir=artifact_digests_path.parent
                )
            )
        else:
            mismatches.append(f"required {artifact_digests_path} not found")
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
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained SLICE-0028 linkage/"
        "evidence manifest/coverage/disagreement/precursor documents and artifact digests.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(
    linkage_doc: dict[str, Any],
    evidence_manifest: dict[str, Any],
    coverage_doc: dict[str, Any],
    disagreement_doc: dict[str, Any],
    precursor_doc: dict[str, Any],
    *,
    report_path: Path = REPORT_PATH,
    replay_result: dict[str, Any] | None = None,
) -> None:
    boundary = linkage_doc["identity_boundary"]
    usage = evidence_manifest["usage_metrics"]
    lines = [
        "# HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout Report",
        "",
        f"**Linkage generated_at:** {linkage_doc['generated_at']}  ",
        f"**Evidence manifest generated_at:** {evidence_manifest['generated_at']}  ",
        f"**Acquired at:** {evidence_manifest['acquired_at']}  ",
        f"**Source:** {evidence_manifest['source_id']}",
        "",
        "## SCOPE",
        "",
        "Full-boundary evidence acquisition, normalization, coverage and persistence rollout "
        "only. Does not create/mutate canonical BoatModel identity, does not mint or infer a "
        "BoatDesign generation, does not create a FieldResolution, and does not claim any "
        "BoatModel is fully Tier-1 searchable merely because source evidence exists.",
        "",
        "## IDENTITY BOUNDARY (reproduced, fail-closed)",
        "",
        f"- canonical BoatModels: **{boundary['canonical_boat_model_count']}** (must equal 1,770)",
        f"- historical QID -> HullQ-ID mappings: **{boundary['historical_crosswalk_count']}** (must equal 1,772)",
        f"- baseline manifest sha256: `{boundary['baseline_manifest_sha256']}`",
        f"- delta manifest sha256: `{boundary['delta_manifest_sha256']}`",
        "",
        "## HISTORICAL REGISTRY RECONCILIATION (1,772 vs 1,770)",
        "",
    ]
    reconciliation = linkage_doc["historical_registry_reconciliation"]
    lines += [
        f"- historical registry count: **{reconciliation['historical_registry_count']}**",
        f"- canonical AUTO_ADMIT QID -> BoatModel linkage count: **{reconciliation['canonical_auto_admit_linkage_count']}**",
        f"- non-canonical historical/reserved mappings excluded from acquisition: **{reconciliation['non_canonical_reserved_count']}**",
    ]
    if reconciliation["reserved_entries"]:
        lines += [
            "",
            "| reserved QID | reserved HullQ ID | decision | reason codes |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {e['qid']} | `{e['reserved_hullq_id']}` | {e['decision']} | {', '.join(e['reason_codes']) or '—'} |"
            for e in reconciliation["reserved_entries"]
        ]
    lines += [
        "",
        reconciliation["note"],
        "",
        "## FULL-BOUNDARY LINKAGE",
        "",
        f"- linked BoatModels: **{linkage_doc['boat_model_count']}**",
        f"- distinct request QIDs: **{linkage_doc['distinct_request_qid_count']}**",
        f"- ordering: {linkage_doc['linkage_ordering']}",
        "- no discovery request was issued; only the accepted linkage-derived QIDs were fetched",
        "",
        "## REQUEST / RECORD COUNTS",
        "",
        f"- requested QID count: **{usage['requested_qid_count']}**",
        f"- fetched entity count: **{usage['fetched_entity_count']}**",
        f"- acquisition failure count: **{usage['acquisition_failure_count']}**",
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
        f"Four mutually exclusive, exhaustive states per field. source_qid_level counts sum to "
        f"{coverage_doc['source_qid_count']} for every field; boat_model_level counts sum to "
        f"{coverage_doc['boat_model_count']} for every field.",
        "",
        "### source-QID level",
        "",
        "| field | normalized_candidate_present | source_statement_present | "
        "unsupported_or_malformed | no_usable_value |",
        "|---|---|---|---|---|",
    ]
    for field, buckets in coverage_doc["source_qid_level"].items():
        lines.append(
            f"| {field} | {buckets['normalized_candidate_present']} | "
            f"{buckets['source_statement_present']} | {buckets['unsupported_or_malformed']} | "
            f"{buckets['no_usable_value']} |"
        )
    lines += [
        "",
        "### canonical-BoatModel level (strongest-available-evidence precedence)",
        "",
        "| field | normalized_candidate_present | source_statement_present | "
        "unsupported_or_malformed | no_usable_value |",
        "|---|---|---|---|---|",
    ]
    for field, buckets in coverage_doc["boat_model_level"].items():
        lines.append(
            f"| {field} | {buckets['normalized_candidate_present']} | "
            f"{buckets['source_statement_present']} | {buckets['unsupported_or_malformed']} | "
            f"{buckets['no_usable_value']} |"
        )
    lines += [
        "",
        "## CANDIDATE-MULTIPLICITY / VALUE-DISAGREEMENT DIAGNOSTICS",
        "",
        f"Flagged (BoatModel, field) cases: **{disagreement_doc['flagged_case_count']}**. Diagnostic "
        "only — no canonical value is chosen and no case is silently resolved.",
        "",
        "## BASIC_SEARCHABLE_EVIDENCE_PRECURSOR (non-canonical diagnostic)",
        "",
        f"- qualifying BoatModels: **{precursor_doc['qualifying_boat_model_count']}** / "
        f"{precursor_doc['boat_model_count']} ({precursor_doc['qualifying_boat_model_percentage']}%)",
        f"- {precursor_doc['non_canonical_disclaimer']}",
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
                "`scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --persist` "
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
            f"- canonical_boat_models row count after both passes: {replay_result['canonical_boat_model_row_count']} (must be 0)",
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
        "- No discovery/SPARQL request was made; only the linkage-derived accepted QIDs were fetched.",
        "- No canonical BoatModel/BoatDesign row was created or mutated.",
        "- No FieldResolution was created.",
        "- Existing Wikidata adapter extraction and SLICE-0004 normalization were reused, not "
        "reimplemented.",
        "- `basic_searchable_evidence_precursor` is explicitly non-canonical and is not CAL-01 D2 "
        "basic-searchable coverage.",
        "- SLICE-0029 was not created or started.",
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
    linkage_path: Path = LINKAGE_PATH,
    evidence_manifest_path: Path = EVIDENCE_MANIFEST_PATH,
) -> dict[str, Any]:
    """Offline (no network access) PostgreSQL persistence proof.

    Rebuilds one ``ResearchEvidenceBundle`` per requested QID from the
    already retained, offline-verified ``evidence_manifest.json`` (no live
    Wikidata request), imports them into an isolated schema via the existing
    SLICE-0013 importer, reads every persisted evidence item back and
    compares it to the in-memory bundle, re-imports the exact same bundles to
    prove idempotency, and confirms zero canonical BoatModel/BoatDesign row
    exists (SLICE-0028 never calls the canonical-identity importer).
    """
    import contextlib
    from collections.abc import Iterator

    import psycopg

    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import filter_to_allowed_evidence
    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import (
        BoatModelLinkage,
        build_sl0028_bundle,
        rebuild_entities_from_manifest,
    )
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations
    from hullq.persistence.readback import fetch_bundle_snapshot, fetch_evidence
    from hullq.sources.wikidata import (
        UNIT_QID_MAP_VERSION_SLICE0008,
        WikidataAdapter,
        WikidataAdapterConfig,
    )

    linkage_doc = json.loads(linkage_path.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))

    linkage = [
        BoatModelLinkage(
            hullq_id=row["hullq_id"],
            qids=tuple(row["qids"]),
            preferred_label_by_qid=row["preferred_label_by_qid"],
        )
        for row in linkage_doc["boat_models"]
    ]

    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (offline-persist@example.org)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        entities = rebuild_entities_from_manifest(evidence_manifest)
        # SLICE-0030 pinned note: this persistence replay must keep importing
        # exactly the evidence SLICE-0028 originally captured and had
        # independently reviewed/accepted, extracted under the (uncorrected)
        # SLICE-0008 mass-unit map.
        full_evidence, _report = adapter.extract_field_evidence(
            entities,
            evidence_manifest.get("acquired_at", ""),
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )

    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    label_by_qid: dict[str, str | None] = {
        qid: label for entry in linkage for qid, label in entry.preferred_label_by_qid.items()
    }

    request_qids = sorted({qid for entry in linkage for qid in entry.qids})
    bundles = [
        build_sl0028_bundle(qid, label_by_qid.get(qid), by_qid.get(qid, [])) for qid in request_qids
    ]

    schema_name = (
        schema_name or "hullq_sl0028_run_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
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
        "schema_version": "sl0028-replay-v1",
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
        "HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout — PERSIST "
        "(offline, no network access)",
        flush=True,
    )
    result = persist_and_verify(db_url)
    REPLAY_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(REPLAY_RESULT_PATH, json.dumps(result, indent=2))
    print(f"Replay result written to: {REPLAY_RESULT_PATH}", flush=True)

    linkage_doc = json.loads(LINKAGE_PATH.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(EVIDENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    coverage_doc = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    disagreement_doc = json.loads(DISAGREEMENT_PATH.read_text(encoding="utf-8"))
    precursor_doc = json.loads(PRECURSOR_PATH.read_text(encoding="utf-8"))
    _write_report(
        linkage_doc,
        evidence_manifest,
        coverage_doc,
        disagreement_doc,
        precursor_doc,
        replay_result=result,
    )
    _write_text_lf(
        REPLAY_REPORT_PATH,
        "# HullQ SLICE-0028 PostgreSQL Persistence Replay Report\n\n"
        f"```json\n{json.dumps(result, indent=2)}\n```\n",
    )
    print(f"Replay report written to: {REPLAY_REPORT_PATH}", flush=True)

    from hullq.bootstrap.wikidata_sl0028_full_boundary_evidence import build_artifact_digests

    digests_doc = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0028_DIR
    )
    mismatches = _validate_schema(
        digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0028 artifact digests"
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
    mode.add_argument("--linkage", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--recompute", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--persist", action="store_true")
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--db-url", default=None)
    args = parser.parse_args()

    if args.linkage:
        run_linkage()
    elif args.live:
        if not args.user_agent:
            raise SystemExit("--live requires --user-agent")
        run_live(user_agent=args.user_agent)
    elif args.recompute:
        run_recompute()
    elif args.verify:
        run_verify()
    elif args.persist:
        if not args.db_url:
            raise SystemExit("--persist requires --db-url")
        run_persist(args.db_url)


if __name__ == "__main__":
    main()
