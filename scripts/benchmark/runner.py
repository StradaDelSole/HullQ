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

from benchmark.semantics_compare import (  # noqa: E402
    compare_crosscheck_semantics,
    compare_finding_semantics,
    compare_observation_semantics,
)


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


def _git_sha(explicit_sha: str | None = None) -> str:
    """Return the implementation SHA. Prefers HULLQ_IMPL_SHA env var, then explicit arg, then git."""
    env_sha = os.environ.get("HULLQ_IMPL_SHA", "").strip()
    if env_sha:
        return env_sha
    if explicit_sha:
        return explicit_sha
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


# compare_observation_semantics, compare_finding_semantics, compare_crosscheck_semantics
# are imported from benchmark.semantics_compare (the single canonical implementation).


def _write_report(result_doc: dict[str, Any], report_path: Path) -> None:
    """Write a human-readable BENCHMARK-REPORT.md with clearly separated sections."""
    rec = result_doc.get("recommendation", "UNKNOWN")
    corpus = result_doc.get("corpus_materialization", {})
    pers = result_doc.get("persistence", {})
    hrb = result_doc.get("human_review_burden", {})
    throughput = result_doc.get("throughput", {})

    lines: list[str] = [
        "# HullQ SLICE-0014 Benchmark Report",
        "",
        f"**Run timestamp:** {result_doc.get('run_timestamp', 'NOT_MEASURED')}  ",
        f"**Implementation SHA:** {result_doc.get('git_sha', 'NOT_MEASURED')}  ",
        f"**PostgreSQL version:** {result_doc.get('environment', {}).get('postgresql_version', 'NOT_MEASURED')}",
        "",
        "---",
        "",
        "## MEASURED FACT",
        "",
        "These values were directly observed during the benchmark run.",
        "",
        f"- Corpus total cases: **{corpus.get('total_cases', '?')}**",
        f"- Materialized: **{corpus.get('materialized', '?')}**",
        f"- Review required: **{corpus.get('review_required', '?')}**",
        f"- Cannot materialize: **{corpus.get('cannot_materialize', '?')}**",
        f"- First-pass imported: **{pers.get('first_pass_imported', '?')}**",
        f"- First-pass conflict: **{pers.get('first_pass_conflict', '?')}**",
        f"- First-pass error: **{pers.get('first_pass_error', '?')}**",
        f"- Reimport ALREADY_IMPORTED: **{pers.get('reimport_already_imported', '?')}**",
        f"- Readback semantic mismatches: **{pers.get('readback_mismatches', '?')}**",
        f"- Fresh-schema imported: **{pers.get('fresh_run_imported', '?')}**",
        f"- Fresh-schema semantic mismatches: **{pers.get('fresh_run_semantic_mismatches', '?')}**",
        f"- Wall-clock import: **{throughput.get('wall_clock_import_seconds', 'NOT_MEASURED')}s**",
        f"- Review-required cases: **{hrb.get('review_required_cases', '?')}**",
        f"- Review decisions required: **{hrb.get('review_decisions_required', '?')}**",
        "",
        "---",
        "",
        "## INTERPRETATION",
        "",
        f"Recommendation: **{rec}**",
        "",
        result_doc.get("recommendation_rationale", ""),
        "",
        result_doc.get("automation_rate_disclaimer", ""),
        "",
        "---",
        "",
        "## RECOMMENDED NEXT ACTION",
        "",
    ]
    if rec == "G3_CANDIDATE":
        lines += [
            "All 50 benchmark cases materialized, imported, and round-tripped with zero",
            "semantic mismatches. The persistence path is ready for G3 gate review.",
            "",
            "Next: proceed to independent SLICE-0014 acceptance review.",
        ]
    else:
        lines += [
            "One or more acceptance criteria were not met. Review the MEASURED FACT section",
            "above to identify failing areas before proceeding to SLICE-0015.",
            "",
            f"Recommendation: **{rec}** — resolve blockers before advancing the slice.",
        ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}", flush=True)


def _validate_result_json(result_doc: dict[str, Any], schema_path: Path) -> None:
    """Validate result_doc against result_schema.json using jsonschema. Raises on failure."""
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=result_doc, schema=schema)
    print("  schema validation: PASS", flush=True)


def run_benchmark(
    db_url: str,
    output_path: Path = RESULT_DEFAULT,
    report_path: Path | None = None,
    explicit_sha: str | None = None,
) -> dict[str, Any]:
    """Execute the full benchmark sequence and return the result dict."""
    import hashlib

    import psycopg
    from benchmark.materializer import materialize_all

    from hullq.persistence._types import ImportStatus
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations
    from hullq.persistence.readback import fetch_bundle_snapshot

    print("HullQ SLICE-0014 Benchmark Runner", flush=True)
    print(f"  database: {db_url!r}", flush=True)

    sha = _git_sha(explicit_sha)
    print(f"  git sha: {sha}", flush=True)

    # --- Materialize all 50 bundles ---
    print("\nMaterializing 50 benchmark bundles...", flush=True)
    mat_results = materialize_all()
    total = len(mat_results)
    mat_count = sum(1 for r in mat_results.values() if r.status == "MATERIALIZED")
    review_count = sum(1 for r in mat_results.values() if r.status == "REVIEW_REQUIRED")
    cannot_count = sum(1 for r in mat_results.values() if r.status == "CANNOT_MATERIALIZE")
    # review_required_reasons must be {failure_class: count} per result_schema.json
    _REASON_TO_CLASS: dict[str, str] = {
        "no_observations_extracted": "INSUFFICIENT_RETAINED_FACT",
    }
    review_reason_counts: dict[str, int] = {}
    for r in mat_results.values():
        if r.status != "MATERIALIZED":
            for raw_reason in r.review_reasons:
                cls = _REASON_TO_CLASS.get(raw_reason)
                if cls is None:
                    # Classify exception-derived reasons as VALIDATION_FAILURE
                    cls = "VALIDATION_FAILURE"
                review_reason_counts[cls] = review_reason_counts.get(cls, 0) + 1
    print(
        f"  total={total} materialized={mat_count} review_required={review_count} "
        f"cannot_materialize={cannot_count}",
        flush=True,
    )
    # Extract only successfully materialized bundles for persistence phases
    bundles = {cid: r.bundle for cid, r in mat_results.items() if r.bundle is not None}

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

        # --- Readback fidelity (full semantic comparison for all bundle children) ---
        print("\nPhase 2: readback fidelity (semantic)...", flush=True)
        from hullq.persistence.readback import fetch_crosscheck as _fetch_cc
        from hullq.persistence.readback import fetch_finding as _fetch_finding
        from hullq.persistence.readback import fetch_observation as _fetch_obs

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
                    print(f"    OBS ID MISMATCH: {case_id}", flush=True)
                    continue
                # Observations: full semantic comparison (all fields)
                for original in bundle.observations:
                    fetched = _fetch_obs(conn1, original.observation_id)
                    if fetched is None:
                        readback_mismatches += 1
                        print(f"    OBS NOT FOUND: {case_id}/{original.observation_id}", flush=True)
                        continue
                    diffs = compare_observation_semantics(case_id, original, fetched)
                    if diffs:
                        readback_mismatches += len(diffs)
                        for d in diffs[:3]:
                            print(f"    SEMANTIC DIFF: {d}", flush=True)
                # Findings: full semantic comparison
                for original_f in bundle.unresolved_findings:
                    fetched_f = _fetch_finding(
                        conn1, original_f.finding_id, bundle.bundle_id, bundle.bundle_version
                    )
                    if fetched_f is None:
                        readback_mismatches += 1
                        print(
                            f"    FINDING NOT FOUND: {case_id}/{original_f.finding_id}", flush=True
                        )
                        continue
                    diffs = compare_finding_semantics(case_id, original_f, fetched_f)
                    if diffs:
                        readback_mismatches += len(diffs)
                        for d in diffs[:3]:
                            print(f"    FINDING DIFF: {d}", flush=True)
                # Crosschecks: full semantic comparison
                for original_cc in bundle.reference_crosschecks:
                    fetched_cc = _fetch_cc(
                        conn1, original_cc.crosscheck_id, bundle.bundle_id, bundle.bundle_version
                    )
                    if fetched_cc is None:
                        readback_mismatches += 1
                        print(
                            f"    CC NOT FOUND: {case_id}/{original_cc.crosscheck_id}", flush=True
                        )
                        continue
                    diffs = compare_crosscheck_semantics(case_id, original_cc, fetched_cc)
                    if diffs:
                        readback_mismatches += len(diffs)
                        for d in diffs[:3]:
                            print(f"    CC DIFF: {d}", flush=True)
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

    # --- Fresh-database rerun (schema-isolated: apply migrations from zero) ---
    print("\nPhase 4: fresh-database rerun (schema-isolated)...", flush=True)
    schema = "hullq_bm_run2_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
    conn2 = psycopg.connect(db_url)
    try:
        with conn2.cursor() as cur:
            # DROP first — IF NOT EXISTS is insufficient when a prior interrupted run left state
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema}"')
            cur.execute(f'SET search_path TO "{schema}"')
        conn2.commit()
        apply_migrations(conn2)

        from hullq.persistence.readback import fetch_crosscheck as _fetch_cc4
        from hullq.persistence.readback import fetch_finding as _fetch_finding4
        from hullq.persistence.readback import fetch_observation as _fetch_obs4

        fresh_imported = 0
        fresh_semantic_mismatches = 0
        for case_id, bundle in bundles.items():
            try:
                result = import_research_evidence_bundle(conn2, bundle)
                if result.status == ImportStatus.IMPORTED:
                    fresh_imported += 1
                    # Observations: full semantic comparison
                    for original in bundle.observations:
                        fetched = _fetch_obs4(conn2, original.observation_id)
                        if fetched is None:
                            fresh_semantic_mismatches += 1
                            print(
                                f"    FRESH OBS MISSING: {case_id}/{original.observation_id}",
                                flush=True,
                            )
                            continue
                        diffs = compare_observation_semantics(case_id, original, fetched)
                        if diffs:
                            fresh_semantic_mismatches += len(diffs)
                            for d in diffs[:3]:
                                print(f"    FRESH SEMANTIC DIFF: {d}", flush=True)
                    # Findings: full semantic comparison
                    for original_f in bundle.unresolved_findings:
                        fetched_f = _fetch_finding4(
                            conn2, original_f.finding_id, bundle.bundle_id, bundle.bundle_version
                        )
                        if fetched_f is None:
                            fresh_semantic_mismatches += 1
                            print(
                                f"    FRESH FINDING MISSING: {case_id}/{original_f.finding_id}",
                                flush=True,
                            )
                            continue
                        diffs = compare_finding_semantics(case_id, original_f, fetched_f)
                        if diffs:
                            fresh_semantic_mismatches += len(diffs)
                            for d in diffs[:3]:
                                print(f"    FRESH FINDING DIFF: {d}", flush=True)
                    # Crosschecks: full semantic comparison
                    for original_cc in bundle.reference_crosschecks:
                        fetched_cc = _fetch_cc4(
                            conn2,
                            original_cc.crosscheck_id,
                            bundle.bundle_id,
                            bundle.bundle_version,
                        )
                        if fetched_cc is None:
                            fresh_semantic_mismatches += 1
                            print(
                                f"    FRESH CC MISSING: {case_id}/{original_cc.crosscheck_id}",
                                flush=True,
                            )
                            continue
                        diffs = compare_crosscheck_semantics(case_id, original_cc, fetched_cc)
                        if diffs:
                            fresh_semantic_mismatches += len(diffs)
                            for d in diffs[:3]:
                                print(f"    FRESH CC DIFF: {d}", flush=True)
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
        with conn2.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn2.commit()
        conn2.close()

    # --- Build result dict ---
    cases_per_second: float | str
    if import_elapsed > 0 and first_imported > 0:
        cases_per_second = round(first_imported / import_elapsed, 2)
    else:
        cases_per_second = "NOT_MEASURED"

    # Promotion applicability: none in this benchmark (all pre-canonical, no forced promotion)
    pre_canonical_count = mat_count  # all successfully materialized bundles remain pre-canonical

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
            "materialized": mat_count,
            "review_required": review_count,
            "cannot_materialize": cannot_count,
            # review_required_reasons: {failure_class: count} per result_schema.json contract
            "review_required_reasons": review_reason_counts,
        },
        "persistence": {
            "valid_bundles_submitted": mat_count,
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
            "review_required_cases": review_count,
            "review_decisions_required": review_count + cannot_count,
            "elapsed_reviewer_minutes": "NOT_MEASURED",
        },
        "automation_rate_disclaimer": (
            "Fixture materialization counts do NOT establish a production automation rate. "
            "These bundles are pre-curated benchmark cases, not a random sample of the broader "
            "design universe. A production automation rate study requires a separate evaluation."
        ),
        "benchmark_cost": {
            "researcher_hours": "NOT_MEASURED",
            "researcher_hours_reason": (
                "Benchmark uses pre-curated retained evidence; no live research sessions "
                "are conducted during this runner execution."
            ),
            "compute_cost_usd": "NOT_MEASURED",
            "compute_cost_reason": (
                "Runner executes on CI infrastructure; per-run cost is not directly "
                "measurable from within the runner process."
            ),
        },
    }

    # Derive recommendation: BLOCKED when contracts cannot represent retained reality
    # (CANNOT_MATERIALIZE means bundle building threw an exception — the domain contracts
    # are insufficient for those cases, not just that the evidence is ambiguous).
    # HARDEN_FIRST for cases where persistence/readback criteria were not met.
    # G3_CANDIDATE only when all acceptance criteria pass.
    if cannot_count > 0:
        recommendation = "BLOCKED"
        rationale = (
            f"BLOCKED: {cannot_count} case(s) cannot_materialize — accepted domain contracts "
            f"cannot represent retained benchmark reality for those cases. "
            f"materialized={mat_count}/{total}, "
            f"first_pass_imported={first_imported}/{mat_count}, "
            f"reimport_already_imported={reimport_already}/{mat_count}, "
            f"fresh_run_imported={fresh_imported}/{mat_count}, "
            f"readback_mismatches={readback_mismatches}, "
            f"semantic_mismatches={fresh_semantic_mismatches}."
        )
    elif (
        mat_count == total
        and first_imported == mat_count
        and reimport_already == mat_count
        and fresh_imported == mat_count
        and readback_mismatches == 0
        and fresh_semantic_mismatches == 0
    ):
        recommendation = "G3_CANDIDATE"
        rationale = (
            f"All acceptance criteria met: materialized={mat_count}/{total}, "
            f"first_pass_imported={first_imported}/{mat_count}, "
            f"reimport_already_imported={reimport_already}/{mat_count}, "
            f"fresh_run_imported={fresh_imported}/{mat_count}, "
            f"readback_mismatches={readback_mismatches}, "
            f"semantic_mismatches={fresh_semantic_mismatches}."
        )
    else:
        recommendation = "HARDEN_FIRST"
        rationale = (
            f"One or more acceptance criteria not met: materialized={mat_count}/{total}, "
            f"first_pass_imported={first_imported}/{mat_count}, "
            f"reimport_already_imported={reimport_already}/{mat_count}, "
            f"fresh_run_imported={fresh_imported}/{mat_count}, "
            f"readback_mismatches={readback_mismatches}, "
            f"semantic_mismatches={fresh_semantic_mismatches}."
        )

    result_doc["recommendation"] = recommendation
    result_doc["recommendation_rationale"] = rationale

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result_doc, indent=2), encoding="utf-8")
    print(f"\nResult written to: {output_path}", flush=True)
    print(f"Recommendation: {result_doc['recommendation']}", flush=True)

    # Validate output against result_schema.json (raises on failure)
    schema_path = ROOT / "research" / "benchmark" / "persistence" / "result_schema.json"
    if schema_path.exists():
        print("\nValidating result against result_schema.json...", flush=True)
        _validate_result_json(result_doc, schema_path)

    # Write human-readable report if requested
    if report_path is not None:
        _write_report(result_doc, report_path)

    return result_doc


def main() -> None:
    parser = argparse.ArgumentParser(description="HullQ SLICE-0014 benchmark runner")
    parser.add_argument("--db-url", default=None, help="PostgreSQL connection URL")
    parser.add_argument("--output", default=str(RESULT_DEFAULT), help="Output JSON path")
    parser.add_argument(
        "--report",
        default=None,
        help="Path for human-readable BENCHMARK-REPORT.md output",
    )
    parser.add_argument(
        "--sha",
        default=None,
        help="Explicit implementation SHA (overridden by HULLQ_IMPL_SHA env var)",
    )
    args = parser.parse_args()

    db_url = _get_db_url(args.db_url)
    run_benchmark(
        db_url=db_url,
        output_path=Path(args.output),
        report_path=Path(args.report) if args.report else None,
        explicit_sha=args.sha,
    )


if __name__ == "__main__":
    main()
