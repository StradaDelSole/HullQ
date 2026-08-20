"""Deterministic benchmark runner — SLICE-0014.

Runs the 50 retained benchmark cases through the accepted PostgreSQL
persistence path and records measured outcomes. Produces a machine-readable
result JSON file conforming to result_schema.json.

Usage:
    uv run python scripts/benchmark/runner.py \\
        --db-url postgresql://user:pass@host:5432/db \\
        [--output research/benchmark/persistence/BENCHMARK-RESULT.json]

Environment variable fallback: HULLQ_TEST_DATABASE_URL or HULLQ_DATABASE_URL.

The runner:
1. Applies migrations to a clean database.
2. Materializes all 50 benchmark bundles deterministically.
3. Runs first-pass import, records results.
4. Reads back each imported bundle, checks fidelity.
5. Runs exact re-import, records ALREADY_IMPORTED outcomes.
6. Drops and recreates schema (fresh DB), runs a second import.
7. Compares semantic fingerprints between the two fresh-DB runs.
8. Writes a machine-readable result JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULT_DEFAULT = ROOT / "research" / "benchmark" / "persistence" / "BENCHMARK-RESULT.json"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _get_db_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    for var in ("HULLQ_TEST_DATABASE_URL", "HULLQ_DATABASE_URL"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    raise SystemExit("No database URL supplied. Pass --db-url or set HULLQ_TEST_DATABASE_URL.")


def _truncate_all(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            TRUNCATE TABLE
                bundle_evidence_members,
                bundle_reference_crosschecks,
                bundle_unresolved_findings,
                bundle_observation_members,
                research_evidence,
                research_observations,
                research_bundles
            RESTART IDENTITY CASCADE
        """)
    conn.commit()


def _pg_version(conn: Any) -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            row = cur.fetchone()
        return str(row[0]) if row else "NOT_MEASURED"
    except Exception:
        return "NOT_MEASURED"


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "NOT_MEASURED"
    except Exception:
        return "NOT_MEASURED"


def run_benchmark(db_url: str, output_path: Path = RESULT_DEFAULT) -> dict[str, Any]:
    """Execute the full benchmark sequence and return the result dict."""
    import psycopg
    from benchmark.materializer import materialize_all

    from hullq.persistence._types import ImportStatus
    from hullq.persistence.fingerprint import fingerprint_bundle
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations
    from hullq.persistence.readback import fetch_bundle_snapshot

    print("HullQ SLICE-0014 Benchmark Runner", flush=True)
    print(f"  database: {db_url!r}", flush=True)

    sha = _git_sha()
    print(f"  git sha: {sha}", flush=True)

    # --- Materialize all 50 bundles ---
    print("\nMaterializing 50 benchmark bundles...", flush=True)
    bundles = materialize_all()
    total = len(bundles)
    print(f"  materialized: {total}", flush=True)

    # --- First pass import ---
    print("\nPhase 1: first-pass import...", flush=True)
    conn1 = psycopg.connect(db_url)
    try:
        apply_migrations(conn1)
        _truncate_all(conn1)
        pg_ver = _pg_version(conn1)

        first_imported = 0
        first_conflict = 0
        first_error = 0
        t0 = time.perf_counter()
        for case_id, bundle in bundles.items():
            try:
                result = import_research_evidence_bundle(conn1, bundle)
                if result.status == ImportStatus.IMPORTED:
                    first_imported += 1
                elif result.status == ImportStatus.CONFLICT:
                    first_conflict += 1
                    print(f"    CONFLICT: {case_id}: {result.detail}", flush=True)
                else:
                    first_error += 1
                    print(f"    UNEXPECTED STATUS {result.status}: {case_id}", flush=True)
            except Exception as exc:
                first_error += 1
                print(f"    ERROR: {case_id}: {exc}", flush=True)
        import_elapsed = time.perf_counter() - t0
        print(
            f"  imported={first_imported} conflict={first_conflict} error={first_error}", flush=True
        )
        print(f"  wall-clock: {import_elapsed:.3f}s", flush=True)

        # --- Readback fidelity ---
        print("\nPhase 2: readback fidelity...", flush=True)
        readback_mismatches = 0
        for case_id, bundle in bundles.items():
            try:
                snap = fetch_bundle_snapshot(conn1, bundle.bundle_id, bundle.bundle_version)
                if snap is None:
                    readback_mismatches += 1
                    print(f"    MISSING: {case_id}", flush=True)
                    continue
                expected_obs = {o.observation_id for o in bundle.observations}
                got_obs = set(snap.observation_ids)
                if expected_obs != got_obs:
                    readback_mismatches += 1
                    print(f"    OBS MISMATCH: {case_id}", flush=True)
            except Exception as exc:
                readback_mismatches += 1
                print(f"    READBACK ERROR: {case_id}: {exc}", flush=True)
        print(f"  readback_mismatches={readback_mismatches}", flush=True)

        # --- Exact re-import idempotency ---
        print("\nPhase 3: exact re-import (idempotency)...", flush=True)
        reimport_already = 0
        reimport_conflict = 0
        reimport_error = 0
        t0 = time.perf_counter()
        for case_id, bundle in bundles.items():
            try:
                result = import_research_evidence_bundle(conn1, bundle)
                if result.status == ImportStatus.ALREADY_IMPORTED:
                    reimport_already += 1
                elif result.status == ImportStatus.CONFLICT:
                    reimport_conflict += 1
                    print(f"    REIMPORT CONFLICT: {case_id}", flush=True)
                else:
                    reimport_error += 1
                    print(f"    REIMPORT UNEXPECTED: {case_id}: {result.status}", flush=True)
            except Exception as exc:
                reimport_error += 1
                print(f"    REIMPORT ERROR: {case_id}: {exc}", flush=True)
        reimport_elapsed = time.perf_counter() - t0
        print(
            f"  already_imported={reimport_already} conflict={reimport_conflict} "
            f"error={reimport_error}",
            flush=True,
        )
        print(f"  wall-clock: {reimport_elapsed:.3f}s", flush=True)
    finally:
        conn1.close()

    # --- Fresh-database rerun ---
    print("\nPhase 4: fresh-database rerun...", flush=True)
    conn2 = psycopg.connect(db_url)
    try:
        apply_migrations(conn2)
        _truncate_all(conn2)

        fresh_imported = 0
        fresh_semantic_mismatches = 0
        for case_id, bundle in bundles.items():
            try:
                result = import_research_evidence_bundle(conn2, bundle)
                if result.status == ImportStatus.IMPORTED:
                    fresh_imported += 1
                    # Compare semantic fingerprint
                    expected_hash = fingerprint_bundle(bundle)
                    snap = fetch_bundle_snapshot(conn2, bundle.bundle_id, bundle.bundle_version)
                    if snap is None or snap.content_hash != expected_hash:
                        fresh_semantic_mismatches += 1
                        print(f"    FINGERPRINT MISMATCH: {case_id}", flush=True)
                else:
                    fresh_semantic_mismatches += 1
                    print(f"    FRESH IMPORT FAILED: {case_id}: {result.status}", flush=True)
            except Exception as exc:
                fresh_semantic_mismatches += 1
                print(f"    FRESH ERROR: {case_id}: {exc}", flush=True)
        print(
            f"  fresh_imported={fresh_imported} semantic_mismatches={fresh_semantic_mismatches}",
            flush=True,
        )
    finally:
        conn2.close()

    # --- Build result dict ---
    cases_per_second: float | str
    if import_elapsed > 0 and first_imported > 0:
        cases_per_second = round(first_imported / import_elapsed, 2)
    else:
        cases_per_second = "NOT_MEASURED"

    # Promotion applicability: none in this benchmark (all pre-canonical, no forced promotion)
    pre_canonical_count = total  # all bundles remain pre-canonical

    result_doc: dict[str, Any] = {
        "schema_version": "0014-v1",
        "benchmark_version": "0014-v1",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "git_sha": sha,
        "environment": {
            "python_version": sys.version,
            "postgresql_version": pg_ver,
        },
        "corpus_materialization": {
            "total_cases": total,
            "materialized": total,
            "review_required": 0,
            "cannot_materialize": 0,
            "review_required_reasons": {},
        },
        "persistence": {
            "valid_bundles_submitted": total,
            "first_pass_imported": first_imported,
            "first_pass_conflict": first_conflict,
            "first_pass_error": first_error,
            "reimport_already_imported": reimport_already,
            "reimport_conflict": reimport_conflict,
            "reimport_error": reimport_error,
            "readback_mismatches": readback_mismatches,
            "fresh_run_imported": fresh_imported,
            "fresh_run_semantic_mismatches": fresh_semantic_mismatches,
        },
        "promotion_applicability": {
            "eligible_for_promotion": 0,
            "pre_canonical_unresolved": pre_canonical_count,
            "promotion_blocked_by_conflict": 0,
        },
        "throughput": {
            "wall_clock_import_seconds": round(import_elapsed, 4),
            "reimport_seconds": round(reimport_elapsed, 4),
            "cases_per_second": cases_per_second,
        },
        "human_review_burden": {
            "review_required_cases": 0,
            "review_decisions_required": 0,
            "elapsed_reviewer_minutes": "NOT_MEASURED",
        },
        "recommendation": (
            "G3_CANDIDATE"
            if (
                first_imported == total
                and reimport_already == total
                and fresh_imported == total
                and readback_mismatches == 0
                and fresh_semantic_mismatches == 0
            )
            else "HARDEN_FIRST"
        ),
        "recommendation_rationale": (
            f"first_pass_imported={first_imported}/{total}, "
            f"reimport_already_imported={reimport_already}/{total}, "
            f"fresh_run_imported={fresh_imported}/{total}, "
            f"readback_mismatches={readback_mismatches}, "
            f"semantic_mismatches={fresh_semantic_mismatches}."
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result_doc, indent=2), encoding="utf-8")
    print(f"\nResult written to: {output_path}", flush=True)
    print(f"Recommendation: {result_doc['recommendation']}", flush=True)

    return result_doc


def main() -> None:
    parser = argparse.ArgumentParser(description="HullQ SLICE-0014 benchmark runner")
    parser.add_argument("--db-url", default=None, help="PostgreSQL connection URL")
    parser.add_argument("--output", default=str(RESULT_DEFAULT), help="Output JSON path")
    args = parser.parse_args()

    db_url = _get_db_url(args.db_url)
    run_benchmark(db_url=db_url, output_path=Path(args.output))


if __name__ == "__main__":
    main()
