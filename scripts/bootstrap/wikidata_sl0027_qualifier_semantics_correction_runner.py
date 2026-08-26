"""SLICE-0027 Wikidata qualifier-semantics correction + offline replay runner.

Three independent modes, all consuming only the already-accepted, unmodified
SLICE-0026 retained package
(``research/stage3/sl0026-wikidata-tier1-enrichment/``) — no live Wikidata
acquisition ever occurs here:

``--build``
    Fully offline (zero network access): offline-verifies the accepted
    SLICE-0026 retained package (failing closed on any digest/schema/self-
    consistency drift), reproduces the exact 100-BoatModel/100-QID input
    boundary, runs the deterministic qualifier-shape analysis, replays the
    retained 100 entities through the SLICE-0027-amended adapter to compute
    "after" coverage, and writes ``qualifier_shape_analysis.json`` +
    ``coverage_before_after.json`` + ``REPORT.md`` +
    ``ARTIFACT-DIGESTS.json`` under
    ``research/stage3/sl0027-wikidata-qualifier-semantics/``.

``--verify``
    Fully offline (zero network access): reloads the retained SLICE-0027
    documents, independently recomputes every derived value purely from the
    (also freshly offline-verified) SLICE-0026 retained package, and compares.
    This is what normal CI runs.

``--persist``
    Offline (no network access) PostgreSQL persistence proof: builds the 100
    pilot ``ResearchEvidenceBundle``s from the amended ("after") evidence
    (rebuilt from the already offline-verified SLICE-0026 raw claims),
    imports them into an isolated schema, reads every persisted evidence item
    back and compares against the in-memory bundle, re-imports the exact same
    bundles to prove idempotency, and confirms zero canonical BoatModel/
    BoatDesign row was created. Writes ``REPLAY-RESULT.json`` +
    ``REPLAY-REPORT.md``.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0027_qualifier_semantics_correction_runner.py --build

    uv run python scripts/bootstrap/wikidata_sl0027_qualifier_semantics_correction_runner.py --verify

    uv run python scripts/bootstrap/wikidata_sl0027_qualifier_semantics_correction_runner.py --persist \\
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

SL0027_DIR = ROOT / "research" / "stage3" / "sl0027-wikidata-qualifier-semantics"
QUALIFIER_SHAPE_PATH = SL0027_DIR / "qualifier_shape_analysis.json"
QUALIFIER_SHAPE_SCHEMA_PATH = SL0027_DIR / "qualifier_shape_analysis_schema.json"
COVERAGE_PATH = SL0027_DIR / "coverage_before_after.json"
COVERAGE_SCHEMA_PATH = SL0027_DIR / "coverage_before_after_schema.json"
REPORT_PATH = SL0027_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0027_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0027_DIR / "artifact_digests_schema.json"
REPLAY_RESULT_PATH = SL0027_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = SL0027_DIR / "REPLAY-REPORT.md"


def _write_text_lf(path: Path, text: str) -> None:
    """Write *text* as UTF-8 bytes with no newline translation, so a
    locally-computed digest matches the digest of the LF-normalized bytes git
    actually stores/checks out (identical rationale to the SLICE-0026/0022
    runners)."""
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
# --build : fully offline derivation + retained-document assembly
# ---------------------------------------------------------------------------


def run_build() -> None:
    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import summarize_field_coverage
    from hullq.bootstrap.wikidata_sl0027_qualifier_semantics_correction import (
        analyze_qualifier_shapes,
        build_artifact_digests,
        build_coverage_before_after_document,
        build_qualifier_shape_analysis_document,
        compute_after_extraction,
        load_and_verify_retained_sl0026_package,
    )

    print(
        "HullQ SLICE-0027 Wikidata Qualifier-Semantics Correction — BUILD "
        "(offline, no network access)",
        flush=True,
    )

    pkg = load_and_verify_retained_sl0026_package()
    print(
        f"  SLICE-0026 retained package offline-verified: {len(pkg.selection)} BoatModels, "
        f"{len(pkg.entities)} entities",
        flush=True,
    )

    shapes = analyze_qualifier_shapes(pkg.entities)
    shape_doc = build_qualifier_shape_analysis_document(
        generated_at=datetime.now(tz=UTC).isoformat(), shapes=shapes
    )
    mismatches = _validate_schema(
        shape_doc, QUALIFIER_SHAPE_SCHEMA_PATH, label="SLICE-0027 qualifier shape analysis"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    QUALIFIER_SHAPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(QUALIFIER_SHAPE_PATH, json.dumps(shape_doc, indent=2))
    print(f"Qualifier shape analysis written to: {QUALIFIER_SHAPE_PATH}", flush=True)
    for s in shapes:
        print(
            f"    {s.statement_property}/{s.qualifier_property}={s.qualifier_value_qid}: "
            f"count={s.count} recognized={s.recognized} mapped_field={s.mapped_field}",
            flush=True,
        )

    acquired_at = pkg.evidence_manifest.get("acquired_at", "")
    after_full_evidence, quality_report = compute_after_extraction(
        pkg.entities, acquired_at=acquired_at
    )
    before_counts = pkg.evidence_manifest["field_coverage"]
    after_counts, _details = summarize_field_coverage(pkg.entities, after_full_evidence)
    coverage_doc = build_coverage_before_after_document(
        generated_at=datetime.now(tz=UTC).isoformat(),
        sample_size=len(pkg.entities),
        before_counts=before_counts,
        after_counts=after_counts,
    )
    mismatches = _validate_schema(
        coverage_doc, COVERAGE_SCHEMA_PATH, label="SLICE-0027 coverage before/after"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(COVERAGE_PATH, json.dumps(coverage_doc, indent=2))
    print(f"Coverage before/after written to: {COVERAGE_PATH}", flush=True)
    for label, buckets in coverage_doc["fields"].items():
        print(f"    {label}: before={buckets['before']} after={buckets['after']}", flush=True)
    print(
        f"  global (all properties) after-extraction quality: "
        f"malformed={quality_report.malformed_statement_count} "
        f"unsupported_qualifier={quality_report.unsupported_qualifier_count}",
        flush=True,
    )

    _write_report(shape_doc, coverage_doc, replay_result=None)

    digests_doc = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0027_DIR
    )
    mismatches = _validate_schema(
        digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0027 artifact digests"
    )
    if mismatches:
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    _write_text_lf(ARTIFACT_DIGESTS_PATH, json.dumps(digests_doc, indent=2))
    print(f"Artifact digests written to: {ARTIFACT_DIGESTS_PATH}", flush=True)


# ---------------------------------------------------------------------------
# --verify : fully offline recompute + compare (what CI runs)
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap.wikidata_sl0027_qualifier_semantics_correction import (
        compute_after_extraction,
        load_and_verify_retained_sl0026_package,
        verify_artifact_digests_self_consistency,
        verify_coverage_before_after_self_consistency,
        verify_qualifier_shape_analysis_self_consistency,
    )

    print(
        "HullQ SLICE-0027 Wikidata Qualifier-Semantics Correction — OFFLINE VERIFY "
        "(no network access)",
        flush=True,
    )

    mismatches: list[str] = []

    pkg = load_and_verify_retained_sl0026_package()
    print(
        f"  SLICE-0026 retained package offline-verified: {len(pkg.selection)} BoatModels, "
        f"{len(pkg.entities)} entities",
        flush=True,
    )

    if not QUALIFIER_SHAPE_PATH.exists() or not COVERAGE_PATH.exists():
        raise SystemExit(
            "SLICE-0027 retained qualifier_shape_analysis.json/coverage_before_after.json not "
            "found; run --build first"
        )

    shape_doc = json.loads(QUALIFIER_SHAPE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            shape_doc, QUALIFIER_SHAPE_SCHEMA_PATH, label="SLICE-0027 qualifier shape analysis"
        )
    )
    mismatches.extend(
        verify_qualifier_shape_analysis_self_consistency(entities=pkg.entities, document=shape_doc)
    )

    coverage_doc = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    mismatches.extend(
        _validate_schema(
            coverage_doc, COVERAGE_SCHEMA_PATH, label="SLICE-0027 coverage before/after"
        )
    )
    after_full_evidence, _report = compute_after_extraction(
        pkg.entities, acquired_at=pkg.evidence_manifest.get("acquired_at", "")
    )
    mismatches.extend(
        verify_coverage_before_after_self_consistency(
            before_counts=pkg.evidence_manifest["field_coverage"],
            entities=pkg.entities,
            after_full_evidence=after_full_evidence,
            document=coverage_doc,
        )
    )
    print(
        f"  recomputed after-coverage from {len(after_full_evidence)} re-extracted raw evidence "
        "item(s)",
        flush=True,
    )

    if ARTIFACT_DIGESTS_PATH.exists():
        digests_doc = json.loads(ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
        mismatches.extend(
            _validate_schema(
                digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0027 artifact digests"
            )
        )
        mismatches.extend(
            verify_artifact_digests_self_consistency(
                artifact_digests=digests_doc, package_dir=SL0027_DIR
            )
        )
    else:
        mismatches.append(f"required ARTIFACT-DIGESTS.json not found at {ARTIFACT_DIGESTS_PATH}")

    if mismatches:
        print("\nOFFLINE VERIFY FAILED:", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)
    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained SLICE-0027 "
        "qualifier-shape analysis, before/after coverage and artifact digests.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(
    shape_doc: dict[str, Any],
    coverage_doc: dict[str, Any],
    *,
    report_path: Path = REPORT_PATH,
    replay_result: dict[str, Any] | None = None,
) -> None:
    lines = [
        "# HullQ SLICE-0027 Wikidata Qualifier-Semantics Correction + Offline Replay Report",
        "",
        f"**Qualifier shape analysis generated_at:** {shape_doc['generated_at']}  ",
        f"**Coverage before/after generated_at:** {coverage_doc['generated_at']}  ",
        f"**Source:** {shape_doc['source_id']}",
        "",
        "## SCOPE",
        "",
        "Bounded qualifier-property compatibility correction and offline replay only. Uses "
        "exclusively the already-retained, unmodified SLICE-0026 100-BoatModel raw-entity claim "
        "payload. No live Wikidata acquisition. Does not expand beyond the five allowed field "
        "pointers, does not mutate the SLICE-0026 retained package, and does not create/mutate "
        "canonical BoatModel/BoatDesign identity.",
        "",
        "## QUALIFIER-SHAPE ANALYSIS",
        "",
        "Every (statement property, qualifier property, qualifier-value QID) combination "
        "observed on the retained SLICE-0026 raw claims for the three shared/qualified "
        "properties (P2043 length, P2048 height, P2067 mass). Beam (P2049) needs no qualifier "
        "disambiguation and is excluded.",
        "",
        "| statement property | qualifier property | qualifier value QID | count | recognized | mapped field |",
        "|---|---|---|---:|---|---|",
    ]
    lines.extend(
        f"| {s['statement_property']} | {s['qualifier_property']} | "
        f"{s['qualifier_value_qid']} | {s['count']} | {s['recognized']} | "
        f"{s['mapped_field'] or '—'} |"
        for s in shape_doc["shapes"]
    )
    lines += [
        "",
        "Evidenced and accepted as alternative carriers of an already-accepted concept QID "
        "(added by this slice): P518 for LOA (Q2358152), P518 for LWL (Q1817392), P518 for "
        "draft (Q244777), P3831 for displacement (Q5636358). The existing accepted P642 path "
        "remains valid unchanged (see hullq.sources.wikidata.QUALIFIER_CARRIERS_BY_VERSION). "
        "P1013 and any unrecognized concept QID under P518 (e.g. Q331744) remain unsupported — "
        "not evidenced/accepted carriers.",
        "",
        f"## PER-FIELD COVERAGE — BEFORE / AFTER (exact retained {coverage_doc['sample_size']}-entity sample)",
        "",
        "Four mutually exclusive, exhaustive states per (BoatModel, field); counts sum to the "
        "sample size for every field, in both before and after.",
        "",
        "| field | state | before | after |",
        "|---|---|---:|---:|",
    ]
    bucket_order = [
        "normalized_candidate_present",
        "source_statement_present",
        "unsupported_or_malformed",
        "no_usable_value",
    ]
    for field, buckets in coverage_doc["fields"].items():
        for bucket in bucket_order:
            lines.append(
                f"| {field} | {bucket} | {buckets['before'][bucket]} | {buckets['after'][bucket]} |"
            )
    lines += [
        "",
    ]
    if replay_result is not None:
        lines += [
            "## POSTGRESQL PERSISTENCE EVIDENCE — LOCAL (this implementation session)",
            "",
            (
                "Evidence below was measured locally by running "
                "`scripts/bootstrap/wikidata_sl0027_qualifier_semantics_correction_runner.py "
                "--persist` against a real PostgreSQL instance during implementation. Remote "
                "GitHub Actions CI independently re-runs the same step at the exact pushed head "
                "and is the authoritative external verification."
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
        "- No live Wikidata acquisition or discovery request was made; only the already-retained "
        "SLICE-0026 raw-entity claim payload was used.",
        "- SLICE-0026 retained package files are unmodified (offline-verified before use).",
        "- No canonical BoatModel/BoatDesign row was created or mutated.",
        "- No FieldResolution was created.",
        "- Existing Wikidata extraction and SLICE-0004 normalization were reused, not "
        "reimplemented; the amendment adds only evidence-backed alternative qualifier-property "
        "carriers for already-accepted concept QIDs.",
        "- SLICE-0028 was not created or started.",
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
    sl0026_package_dir: Path | None = None,
    sl0026_boundary: Any = None,
    sl0026_expected_size: int | None = None,
) -> dict[str, Any]:
    """Offline (no network access) PostgreSQL persistence proof for the
    amended ("after") SLICE-0027 evidence.

    Rebuilds the pilot ``ResearchEvidenceBundle``s from the already offline-
    verified SLICE-0026 retained raw claims re-extracted through the
    SLICE-0027-amended adapter default, imports them into an isolated schema
    via the existing SLICE-0013 importer, reads every persisted evidence item
    back and compares it to the in-memory bundle, re-imports the exact same
    bundles to prove idempotency, and confirms zero canonical BoatModel/
    BoatDesign row exists.

    ``sl0026_package_dir`` defaults to the real retained SLICE-0026 package
    but may be overridden (e.g. by ``tests/persistence/``) to exercise this
    exact mechanism against a small synthetic SLICE-0026-shaped package
    without touching the real retained artifacts.
    """
    import contextlib
    from collections.abc import Iterator

    import psycopg

    from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import filter_to_allowed_evidence
    from hullq.bootstrap.wikidata_sl0027_qualifier_semantics_correction import (
        EXPECTED_PILOT_SIZE,
        SL0026_PACKAGE_DIR,
        build_sl0027_pilot_bundle,
        compute_after_extraction,
        load_and_verify_retained_sl0026_package,
    )
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations
    from hullq.persistence.readback import fetch_bundle_snapshot, fetch_evidence

    pkg = load_and_verify_retained_sl0026_package(
        package_dir=sl0026_package_dir or SL0026_PACKAGE_DIR,
        boundary=sl0026_boundary,
        expected_size=sl0026_expected_size
        if sl0026_expected_size is not None
        else EXPECTED_PILOT_SIZE,
    )

    after_full_evidence, _report = compute_after_extraction(
        pkg.entities, acquired_at=pkg.evidence_manifest.get("acquired_at", "")
    )
    allowed = filter_to_allowed_evidence(list(after_full_evidence))
    by_qid: dict[str, list[Any]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    bundles = [build_sl0027_pilot_bundle(m, by_qid.get(m.qid, [])) for m in pkg.selection]

    schema_name = (
        schema_name or "hullq_sl0027_run_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
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
        "schema_version": "sl0027-replay-v1",
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
        "HullQ SLICE-0027 Wikidata Qualifier-Semantics Correction — PERSIST "
        "(offline, no network access)",
        flush=True,
    )
    result = persist_and_verify(db_url)
    REPLAY_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(REPLAY_RESULT_PATH, json.dumps(result, indent=2))
    print(f"Replay result written to: {REPLAY_RESULT_PATH}", flush=True)

    if not QUALIFIER_SHAPE_PATH.exists() or not COVERAGE_PATH.exists():
        raise SystemExit(
            "--persist requires --build to have already produced the SLICE-0027 package"
        )
    shape_doc = json.loads(QUALIFIER_SHAPE_PATH.read_text(encoding="utf-8"))
    coverage_doc = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    _write_report(shape_doc, coverage_doc, replay_result=result)
    _write_text_lf(
        REPLAY_REPORT_PATH,
        "# HullQ SLICE-0027 PostgreSQL Persistence Replay Report\n\n"
        f"```json\n{json.dumps(result, indent=2)}\n```\n",
    )
    print(f"Replay report written to: {REPLAY_REPORT_PATH}", flush=True)

    from hullq.bootstrap.wikidata_sl0027_qualifier_semantics_correction import (
        build_artifact_digests,
    )

    digests_doc = build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0027_DIR
    )
    mismatches = _validate_schema(
        digests_doc, ARTIFACT_DIGESTS_SCHEMA_PATH, label="SLICE-0027 artifact digests"
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
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--persist", action="store_true")
    parser.add_argument("--db-url", default=None)
    args = parser.parse_args()

    if args.build:
        run_build()
    elif args.verify:
        run_verify()
    elif args.persist:
        if not args.db_url:
            raise SystemExit("--persist requires --db-url")
        run_persist(args.db_url)


if __name__ == "__main__":
    main()
