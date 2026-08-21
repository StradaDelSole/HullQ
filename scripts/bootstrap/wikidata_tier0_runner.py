"""SLICE-0017 controlled Wikidata Tier-0 bootstrap runner.

Two independent modes:

``--live``
    Perform the one controlled live Wikidata bootstrap run: rights-gated
    deterministic discovery of up to ``--limit`` (default 1,000) direct
    sailboat-class candidates, bounded entity acquisition, deterministic
    classification, and a retained versioned manifest + human-readable
    report written under ``research/bootstrap/wikidata/``. Requires network
    access and is not part of normal CI.

``--replay``
    Offline replay of the already-retained manifest against real
    PostgreSQL 18: import, readback verification, exact re-import
    (idempotency), and a fresh-schema isolated rerun (semantic equality).
    Performs no network access. This is what normal ``db-integration`` CI
    runs.

Usage::

    uv run python scripts/bootstrap/wikidata_tier0_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)" \\
        --limit 1000

    uv run python scripts/bootstrap/wikidata_tier0_runner.py --replay \\
        --db-url postgresql://user:pass@host:5432/db
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

BOOTSTRAP_DIR = ROOT / "research" / "bootstrap" / "wikidata"
MANIFEST_PATH = BOOTSTRAP_DIR / "manifest.json"
REPORT_PATH = BOOTSTRAP_DIR / "REPORT.md"
MANIFEST_SCHEMA_PATH = BOOTSTRAP_DIR / "manifest_schema.json"
REPLAY_RESULT_PATH = BOOTSTRAP_DIR / "REPLAY-RESULT.json"


def _get_db_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    for var in ("HULLQ_TEST_DATABASE_URL", "HULLQ_DATABASE_URL"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    raise SystemExit("No database URL supplied. Pass --db-url or set HULLQ_TEST_DATABASE_URL.")


def _pg_version(conn: Any) -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            row = cur.fetchone()
        return str(row[0]) if row else "NOT_MEASURED"
    except Exception:
        return "NOT_MEASURED"


# ---------------------------------------------------------------------------
# Live run
# ---------------------------------------------------------------------------


def run_live_bootstrap(
    *,
    user_agent: str,
    requested_limit: int,
    manifest_path: Path = MANIFEST_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    """Execute the one controlled live Wikidata bootstrap run.

    Discovers up to *requested_limit* direct sailboat-class QIDs in
    deterministic order, fetches their entity data, classifies every
    candidate, and writes the retained manifest + human-readable report.
    """
    import json as _json

    import httpx

    from hullq.bootstrap.wikidata_tier0 import (
        BOOTSTRAP_SAFETY_CEILING,
        build_manifest,
        classify_candidates,
    )
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    source_path = ROOT / "fixtures" / "sources" / "wikidata_source.json"
    source = _json.loads(source_path.read_text(encoding="utf-8"))

    config = WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=60.0)

    print("HullQ SLICE-0017 Wikidata Tier-0 Bootstrap — LIVE RUN", flush=True)
    print(
        f"  requested_limit={requested_limit} safety_ceiling={BOOTSTRAP_SAFETY_CEILING}", flush=True
    )

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)

        print("\nDiscovering direct sailboat-class candidates (deterministic order)...", flush=True)
        qids = adapter.discover_bootstrap_qids(requested_limit)
        unique_returned = len(qids)
        target_reached = unique_returned >= requested_limit
        print(
            f"  unique_qids_returned={unique_returned} target_reached={target_reached}", flush=True
        )

        print("\nFetching entity data...", flush=True)
        entities = adapter.fetch_entities_bootstrap(qids) if qids else []
        print(f"  fetched_entity_count={len(entities)}", flush=True)

        usage = adapter.usage_metrics

    retrieved_at = datetime.now(tz=UTC).isoformat()
    candidates = classify_candidates(entities, retrieved_at=retrieved_at)

    manifest = build_manifest(
        candidates,
        generated_at=retrieved_at,
        requested_limit=requested_limit,
        unique_qids_returned=unique_returned,
        retrieval_count=usage.retrieval_count,
        extracted_record_count=usage.extracted_record_count,
        target_reached=target_reached,
    )

    if MANIFEST_SCHEMA_PATH.exists():
        import jsonschema

        schema = _json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=manifest, schema=schema)
        print("\nManifest schema validation: PASS", flush=True)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written to: {manifest_path}", flush=True)

    _write_live_report(manifest, report_path)
    return manifest


def _write_live_report(manifest: dict[str, Any], report_path: Path) -> None:
    counts = manifest["counts"]
    discovery = manifest["discovery"]
    usage = manifest["usage_metrics"]
    lines = [
        "# HullQ SLICE-0017 Wikidata Tier-0 Bootstrap Report",
        "",
        f"**Generated:** {manifest['generated_at']}  ",
        f"**Source:** {manifest['source_id']}  ",
        f"**Requested limit:** {manifest['requested_limit']}  ",
        f"**Safety ceiling:** {manifest['safety_ceiling']}",
        "",
        "## MEASURED FACT",
        "",
        f"- Unique QIDs returned by discovery: **{discovery['unique_qids_returned']}**",
        f"- Target ({manifest['requested_limit']}) reached: **{discovery['target_reached']}**",
        f"- Candidates processed: **{discovery['candidates_processed']}**",
        f"- HTTP retrieval count: **{usage['retrieval_count']}**",
        f"- Extracted record count: **{usage['extracted_record_count']}**",
        "",
        "## CLASSIFICATION",
        "",
        f"- AUTO_ADMIT: **{counts['auto_admit']}**",
        f"- REVIEW_REQUIRED: **{counts['review_required']}**",
        f"- NOT_ADMITTED: **{counts['not_admitted']}**",
        "",
        "### Reason breakdown",
        "",
    ]
    for reason, count in sorted(counts["reason_breakdown"].items()):
        lines.append(f"- `{reason}`: {count}")
    lines += [
        "",
        "## INTERPRETATION",
        "",
        (
            "This is a first controlled broad identity bootstrap measurement, not a "
            "pre-committed admission-rate target. AUTO_ADMIT candidates become sparse "
            "Tier-0 BoatModel identities only after offline PostgreSQL replay "
            "(see REPLAY-RESULT.json / REPLAY-REPORT.md)."
        ),
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}", flush=True)


# ---------------------------------------------------------------------------
# Replay (offline, no network)
# ---------------------------------------------------------------------------


def replay_manifest(
    db_url: str,
    manifest_path: Path = MANIFEST_PATH,
    result_path: Path = REPLAY_RESULT_PATH,
) -> dict[str, Any]:
    """Offline replay of the retained manifest against real PostgreSQL 18.

    Performs, in order: first-pass import, readback verification, exact
    re-import (idempotency), and a fresh-schema isolated rerun (semantic
    equality). Performs no network access.
    """
    import psycopg

    from hullq.bootstrap.wikidata_tier0 import (
        BootstrapDecision,
        build_admission,
        build_bundle,
        candidate_from_manifest_dict,
    )
    from hullq.contracts import ContractRegistry
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.identity_importer import import_canonical_identity_admission
    from hullq.persistence.identity_readback import fetch_boat_model
    from hullq.persistence.identity_types import CanonicalImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = [candidate_from_manifest_dict(row) for row in manifest["candidates"]]
    auto_admit = [c for c in candidates if c.decision == BootstrapDecision.AUTO_ADMIT]

    registry = ContractRegistry.from_directory(ROOT / "specs")

    print("HullQ SLICE-0017 Wikidata Tier-0 Bootstrap — REPLAY", flush=True)
    print(f"  candidates={len(candidates)} auto_admit={len(auto_admit)}", flush=True)

    conn1 = psycopg.connect(db_url)
    try:
        apply_migrations(conn1)
        pg_ver = _pg_version(conn1)

        bundle_imported = bundle_conflict = bundle_error = 0
        admission_imported = admission_conflict = admission_error = 0
        t0 = time.perf_counter()
        for candidate in candidates:
            bundle = build_bundle(candidate)
            if bundle is not None:
                try:
                    result = import_research_evidence_bundle(conn1, bundle)
                    if result.status == ImportStatus.IMPORTED:
                        bundle_imported += 1
                    elif result.status == ImportStatus.CONFLICT:
                        bundle_conflict += 1
                        print(f"    BUNDLE CONFLICT: {candidate.qid}: {result.detail}", flush=True)
                except Exception as exc:
                    bundle_error += 1
                    print(f"    BUNDLE ERROR: {candidate.qid}: {exc}", flush=True)

            admission = build_admission(candidate)
            if admission is not None:
                try:
                    result = import_canonical_identity_admission(conn1, admission, registry)
                    if result.status == CanonicalImportStatus.IMPORTED:
                        admission_imported += 1
                    elif result.status == CanonicalImportStatus.CONFLICT:
                        admission_conflict += 1
                        print(
                            f"    ADMISSION CONFLICT: {candidate.qid}: {result.detail}", flush=True
                        )
                except Exception as exc:
                    admission_error += 1
                    print(f"    ADMISSION ERROR: {candidate.qid}: {exc}", flush=True)
        import_elapsed = time.perf_counter() - t0
        print(
            f"  bundles: imported={bundle_imported} conflict={bundle_conflict} error={bundle_error}",
            flush=True,
        )
        print(
            f"  admissions: imported={admission_imported} conflict={admission_conflict} "
            f"error={admission_error}",
            flush=True,
        )

        # --- Readback verification ---
        readback_mismatches = 0
        for candidate in auto_admit:
            fetched = fetch_boat_model(conn1, candidate.hullq_id)
            if fetched is None:
                readback_mismatches += 1
                print(f"    READBACK MISSING: {candidate.qid}", flush=True)
                continue
            if fetched.get("canonical_name") != candidate.preferred_label:
                readback_mismatches += 1
                print(f"    READBACK NAME MISMATCH: {candidate.qid}", flush=True)
            if fetched.get("brand_relationships") != [] or fetched.get("boat_design_ids") != []:
                readback_mismatches += 1
                print(f"    READBACK UNEXPECTED RELATIONSHIP: {candidate.qid}", flush=True)
        print(f"  readback_mismatches={readback_mismatches}", flush=True)

        # --- Non-admitted candidates must never appear as canonical rows ---
        unexpected_canonical = 0
        for candidate in candidates:
            if candidate.decision == BootstrapDecision.AUTO_ADMIT:
                continue
            if (
                candidate.hullq_id is not None
                and fetch_boat_model(conn1, candidate.hullq_id) is not None
            ):
                unexpected_canonical += 1
                print(f"    UNEXPECTED CANONICAL ROW FOR NON-ADMITTED: {candidate.qid}", flush=True)

        # --- Exact re-import idempotency ---
        reimport_already = reimport_conflict = reimport_error = 0
        t0 = time.perf_counter()
        for candidate in candidates:
            bundle = build_bundle(candidate)
            if bundle is not None:
                try:
                    result = import_research_evidence_bundle(conn1, bundle)
                    if result.status != ImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    BUNDLE REIMPORT NOT IDEMPOTENT: {candidate.qid}: {result.status}",
                            flush=True,
                        )
                    else:
                        reimport_already += 1
                except Exception as exc:
                    reimport_error += 1
                    print(f"    BUNDLE REIMPORT ERROR: {candidate.qid}: {exc}", flush=True)

            admission = build_admission(candidate)
            if admission is not None:
                try:
                    result = import_canonical_identity_admission(conn1, admission, registry)
                    if result.status != CanonicalImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    ADMISSION REIMPORT NOT IDEMPOTENT: {candidate.qid}: {result.status}",
                            flush=True,
                        )
                    else:
                        reimport_already += 1
                except Exception as exc:
                    reimport_error += 1
                    print(f"    ADMISSION REIMPORT ERROR: {candidate.qid}: {exc}", flush=True)
        reimport_elapsed = time.perf_counter() - t0
        print(
            f"  reimport: already_imported={reimport_already} conflict={reimport_conflict} "
            f"error={reimport_error}",
            flush=True,
        )
    finally:
        conn1.close()

    # --- Fresh-schema isolated rerun ---
    schema = "hullq_wdt0_run2_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
    conn2 = psycopg.connect(db_url)
    fresh_imported = 0
    fresh_semantic_mismatches = 0
    fresh_error = 0
    try:
        with conn2.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema}"')
            cur.execute(f'SET search_path TO "{schema}"')
        conn2.commit()
        apply_migrations(conn2)

        for candidate in candidates:
            bundle = build_bundle(candidate)
            if bundle is not None:
                try:
                    import_research_evidence_bundle(conn2, bundle)
                except Exception as exc:
                    fresh_error += 1
                    print(f"    FRESH BUNDLE ERROR: {candidate.qid}: {exc}", flush=True)

            admission = build_admission(candidate)
            if admission is not None:
                try:
                    result = import_canonical_identity_admission(conn2, admission, registry)
                    if result.status == CanonicalImportStatus.IMPORTED:
                        fresh_imported += 1
                        fetched = fetch_boat_model(conn2, candidate.hullq_id)
                        if (
                            fetched is None
                            or fetched.get("canonical_name") != candidate.preferred_label
                        ):
                            fresh_semantic_mismatches += 1
                            print(f"    FRESH SEMANTIC MISMATCH: {candidate.qid}", flush=True)
                    else:
                        fresh_error += 1
                        print(
                            f"    FRESH ADMISSION FAILED: {candidate.qid}: {result.status}",
                            flush=True,
                        )
                except Exception as exc:
                    fresh_error += 1
                    print(f"    FRESH ADMISSION ERROR: {candidate.qid}: {exc}", flush=True)
        print(
            f"  fresh: imported={fresh_imported} semantic_mismatches={fresh_semantic_mismatches} "
            f"error={fresh_error}",
            flush=True,
        )
    finally:
        with conn2.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn2.commit()
        conn2.close()

    result_doc: dict[str, Any] = {
        "schema_version": "0017-replay-v1",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "postgresql_version": pg_ver,
        "manifest_candidates": len(candidates),
        "manifest_auto_admit": len(auto_admit),
        "first_pass": {
            "bundle_imported": bundle_imported,
            "bundle_conflict": bundle_conflict,
            "bundle_error": bundle_error,
            "admission_imported": admission_imported,
            "admission_conflict": admission_conflict,
            "admission_error": admission_error,
            "wall_clock_seconds": round(import_elapsed, 4),
        },
        "readback": {
            "mismatches": readback_mismatches,
            "unexpected_canonical_rows_for_non_admitted": unexpected_canonical,
        },
        "reimport": {
            "already_imported": reimport_already,
            "conflict": reimport_conflict,
            "error": reimport_error,
            "wall_clock_seconds": round(reimport_elapsed, 4),
        },
        "fresh_schema_rerun": {
            "imported": fresh_imported,
            "semantic_mismatches": fresh_semantic_mismatches,
            "error": fresh_error,
        },
    }
    result_doc["all_zero_tolerance_conditions_clear"] = (
        bundle_conflict == 0
        and bundle_error == 0
        and admission_conflict == 0
        and admission_error == 0
        and readback_mismatches == 0
        and unexpected_canonical == 0
        and reimport_conflict == 0
        and reimport_error == 0
        and fresh_semantic_mismatches == 0
        and fresh_error == 0
    )

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result_doc, indent=2), encoding="utf-8")
    print(f"\nReplay result written to: {result_path}", flush=True)
    print(
        f"All zero-tolerance conditions clear: {result_doc['all_zero_tolerance_conditions_clear']}",
        flush=True,
    )
    return result_doc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HullQ SLICE-0017 Wikidata Tier-0 bootstrap runner"
    )
    parser.add_argument(
        "--live", action="store_true", help="Run the one live discovery+acquisition run"
    )
    parser.add_argument(
        "--replay", action="store_true", help="Replay the retained manifest against PostgreSQL"
    )
    parser.add_argument(
        "--user-agent", default=None, help="Wikimedia-policy-compliant User-Agent (live mode)"
    )
    parser.add_argument(
        "--limit", type=int, default=1000, help="Requested candidate limit (live mode)"
    )
    parser.add_argument("--db-url", default=None, help="PostgreSQL connection URL (replay mode)")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Manifest path")
    parser.add_argument(
        "--report", default=str(REPORT_PATH), help="Human-readable report path (live mode)"
    )
    parser.add_argument("--result", default=str(REPLAY_RESULT_PATH), help="Replay result JSON path")
    args = parser.parse_args()

    if args.live == args.replay:
        raise SystemExit("Specify exactly one of --live or --replay")

    if args.live:
        if not args.user_agent:
            raise SystemExit("--user-agent is required for --live")
        run_live_bootstrap(
            user_agent=args.user_agent,
            requested_limit=args.limit,
            manifest_path=Path(args.manifest),
            report_path=Path(args.report),
        )
    else:
        db_url = _get_db_url(args.db_url)
        replay_manifest(db_url, manifest_path=Path(args.manifest), result_path=Path(args.result))


if __name__ == "__main__":
    main()
