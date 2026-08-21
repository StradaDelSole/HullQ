"""SLICE-0018 controlled Wikidata Tier-0 2,500-window expansion runner.

Three independent modes, mirroring the accepted SLICE-0017 runner contract
(``scripts/bootstrap/wikidata_tier0_runner.py``):

``--live``
    Perform the one controlled live Wikidata acquisition run: rights-gated
    deterministic discovery of up to ``--limit`` (default 2,500) direct
    sailboat-class candidates, compute the expansion delta against the
    accepted SLICE-0017 baseline, bounded entity acquisition for the delta
    only, deterministic delta classification, and a retained versioned
    manifest + human-readable report written under
    ``research/bootstrap/wikidata/sl0018-2500/``. Requires network access and
    is not part of normal CI. If a SLICE-0018 manifest already exists at the
    target path, its retained crosswalk (merged with the baseline's) is
    loaded first and every already-mapped QID reuses its retained ID.

``--recompute``
    Offline reclassification of the already-retained SLICE-0018 manifest
    using the current classification logic, with NO network access:
    reconstructs the original acquired delta label/alias facts from the
    committed manifest, reloads the baseline fresh from disk, and reruns
    delta classification only, reusing every retained HullQ ID exactly.

``--replay``
    Offline replay of the accepted SLICE-0017 baseline artifact FIRST and
    the retained SLICE-0018 delta manifest SECOND against real
    PostgreSQL 18: combined import, deep semantic readback verification
    (including zero baseline drift), exact re-import (idempotency), and a
    fresh-schema isolated rerun (full combined semantic graph equality).
    Performs no network access. This is what the SLICE-0018 db-integration
    CI step runs.

Usage::

    uv run python scripts/bootstrap/wikidata_tier0_sl0018_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)" \\
        --limit 2500

    uv run python scripts/bootstrap/wikidata_tier0_sl0018_runner.py --recompute

    uv run python scripts/bootstrap/wikidata_tier0_sl0018_runner.py --replay \\
        --db-url postgresql://user:pass@host:5432/db
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
import os
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _repo_relative_path(path: Path) -> str:
    """A portable, forward-slash repo-relative path string for retained
    manifest metadata, falling back to the given path's own string form when
    it does not live under the repository root (e.g. a caller-supplied path
    outside the checkout).
    """
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


BASELINE_MANIFEST_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"

SL0018_DIR = ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500"
MANIFEST_PATH = SL0018_DIR / "manifest.json"
REPORT_PATH = SL0018_DIR / "REPORT.md"
MANIFEST_SCHEMA_PATH = SL0018_DIR / "manifest_schema.json"
REPLAY_RESULT_PATH = SL0018_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = SL0018_DIR / "REPLAY-REPORT.md"

DEFAULT_REQUESTED_LIMIT = 2500


def _get_db_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    for var in ("HULLQ_TEST_DATABASE_URL", "HULLQ_DATABASE_URL"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    raise SystemExit("No database URL supplied. Pass --db-url or set HULLQ_TEST_DATABASE_URL.")


@contextlib.contextmanager
def _isolated_schema(conn: Any, schema_name: str) -> Iterator[None]:
    """Create *schema_name* fresh (dropping any same-named leftover first),
    set it as the connection's search_path, and drop it again on exit — full
    isolation from whatever pre-existing rows the default/public schema or
    another CI step's schema may hold.
    """
    with conn.cursor() as cur:
        cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        cur.execute(f'CREATE SCHEMA "{schema_name}"')
        cur.execute(f'SET search_path TO "{schema_name}"')
    conn.commit()
    try:
        yield
    finally:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        conn.commit()


def _pg_version(conn: Any) -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            row = cur.fetchone()
        return str(row[0]) if row else "NOT_MEASURED"
    except Exception:
        return "NOT_MEASURED"


def _validate_manifest_schema(manifest: dict[str, Any]) -> None:
    if not MANIFEST_SCHEMA_PATH.exists():
        return
    import jsonschema

    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=schema)
    print("SLICE-0018 manifest schema validation: PASS", flush=True)


# ---------------------------------------------------------------------------
# Live run
# ---------------------------------------------------------------------------


def run_live_bootstrap(
    *,
    user_agent: str,
    requested_limit: int = DEFAULT_REQUESTED_LIMIT,
    baseline_manifest_path: Path = BASELINE_MANIFEST_PATH,
    manifest_path: Path = MANIFEST_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    """Execute the one controlled SLICE-0018 live Wikidata acquisition run.

    Discovers up to *requested_limit* direct sailboat-class QIDs in
    deterministic order (same accepted query as SLICE-0017, just a larger
    LIMIT), computes the expansion delta against the accepted SLICE-0017
    baseline, fetches entity data for the delta only, classifies every delta
    candidate, and writes the retained SLICE-0018 manifest + report.

    Fails closed (raises ``BaselineIntegrityError``) before any network
    request if the retained baseline artifact does not reproduce its
    accepted SLICE-0017 semantics.
    """
    import httpx

    from hullq.bootstrap.wikidata_tier0 import load_crosswalk_from_manifest
    from hullq.bootstrap.wikidata_tier0_sl0018 import (
        build_sl0018_manifest,
        classify_delta_candidates,
        compute_expansion_delta,
        load_baseline_snapshot,
        merge_crosswalks_fail_closed,
    )
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    print("HullQ SLICE-0018 Wikidata Tier-0 2,500-Window Expansion — LIVE RUN", flush=True)

    # Fails closed before any network request if the baseline has drifted.
    baseline = dataclasses.replace(
        load_baseline_snapshot(baseline_manifest_path),
        manifest_path=_repo_relative_path(baseline_manifest_path),
    )
    print(
        f"  baseline: {len(baseline.candidate_qids)} candidate QIDs, "
        f"{len(baseline.crosswalk)} retained crosswalk entries "
        f"(sha256={baseline.sha256[:12]}...)",
        flush=True,
    )

    historical_crosswalk = dict(baseline.crosswalk)
    if manifest_path.exists():
        prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        prior_crosswalk = load_crosswalk_from_manifest(prior_manifest)
        historical_crosswalk = merge_crosswalks_fail_closed(
            historical_crosswalk,
            prior_crosswalk,
            context="baseline crosswalk merge with prior retained SLICE-0018 manifest",
        )
        print(
            f"  loaded {len(prior_crosswalk)} retained QID->HullQ-ID mapping(s) from existing "
            f"SLICE-0018 manifest at {manifest_path}; merged historical crosswalk has "
            f"{len(historical_crosswalk)} entries",
            flush=True,
        )

    source_path = ROOT / "fixtures" / "sources" / "wikidata_source.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    config = WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=60.0)

    print(f"  requested_limit={requested_limit}", flush=True)

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)

        print("\nDiscovering direct sailboat-class candidates (deterministic order)...", flush=True)
        discovery_window_qids = adapter.discover_bootstrap_qids(requested_limit)
        unique_returned = len(discovery_window_qids)
        target_reached = unique_returned >= requested_limit
        print(
            f"  unique_qids_returned={unique_returned} target_reached={target_reached}", flush=True
        )

        delta_qids = compute_expansion_delta(discovery_window_qids, baseline)
        print(
            f"  overlap_with_baseline={unique_returned - len(delta_qids)} "
            f"expansion_delta={len(delta_qids)}",
            flush=True,
        )

        print("\nFetching entity data for the expansion delta only...", flush=True)
        entities = adapter.fetch_entities_bootstrap(delta_qids) if delta_qids else []
        fetched_entity_count = len(entities)
        print(f"  fetched_entity_count={fetched_entity_count}", flush=True)

        usage = adapter.usage_metrics

    retrieved_at = datetime.now(tz=UTC).isoformat()
    candidates, delta_delta_clusters, baseline_collisions = classify_delta_candidates(
        entities,
        retrieved_at=retrieved_at,
        baseline=baseline,
        existing_crosswalk=historical_crosswalk,
    )

    manifest = build_sl0018_manifest(
        candidates,
        generated_at=retrieved_at,
        baseline=baseline,
        discovery_window_qids=discovery_window_qids,
        requested_limit=requested_limit,
        target_reached=target_reached,
        delta_delta_clusters=delta_delta_clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=usage.retrieval_count,
        extracted_record_count=usage.extracted_record_count,
        acquisition_failure_count=0,
        fetched_entity_count=fetched_entity_count,
        acquired_at=retrieved_at,
        classification_recomputed_at=None,
    )
    _validate_manifest_schema(manifest)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written to: {manifest_path}", flush=True)

    _write_live_report(manifest, report_path)
    return manifest


# ---------------------------------------------------------------------------
# Offline reclassification of an already-retained manifest (no network)
# ---------------------------------------------------------------------------


def recompute_manifest_offline(
    *,
    baseline_manifest_path: Path = BASELINE_MANIFEST_PATH,
    manifest_path: Path = MANIFEST_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    """Reclassify the already-retained SLICE-0018 manifest using current
    classification logic, with zero network access.

    Reconstructs the original acquired delta ``WikidataEntityData`` (qid,
    label, aliases) from the committed manifest rows — never re-fetches from
    Wikidata — reloads the baseline fresh from disk (a local file read, not a
    network request), and reruns ``classify_delta_candidates`` with the
    merged historical crosswalk loaded, so every previously admitted delta
    QID keeps its exact HullQ ID.
    """
    from hullq.bootstrap.wikidata_tier0 import load_crosswalk_from_manifest
    from hullq.bootstrap.wikidata_tier0_sl0018 import (
        build_sl0018_manifest,
        classify_delta_candidates,
        load_baseline_snapshot,
        merge_crosswalks_fail_closed,
    )
    from hullq.sources.wikidata import WikidataEntityData

    baseline = dataclasses.replace(
        load_baseline_snapshot(baseline_manifest_path),
        manifest_path=_repo_relative_path(baseline_manifest_path),
    )

    old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = old_manifest["candidates"]
    if not rows:
        raise SystemExit(f"No candidates found in {manifest_path}; nothing to recompute.")

    retrieved_at_values = {row["retrieved_at"] for row in rows}
    if len(retrieved_at_values) != 1:
        raise SystemExit(
            "Retained SLICE-0018 manifest rows do not share one uniform retrieved_at "
            "timestamp; offline recompute requires a single-acquisition manifest."
        )
    retrieved_at = next(iter(retrieved_at_values))

    entities = [
        WikidataEntityData(
            qid=row["qid"],
            label=row["preferred_label"],
            aliases=list(row.get("aliases") or ()),
            raw_claims={},
        )
        for row in rows
    ]

    prior_crosswalk = load_crosswalk_from_manifest(old_manifest)
    historical_crosswalk = merge_crosswalks_fail_closed(
        dict(baseline.crosswalk),
        prior_crosswalk,
        context="baseline crosswalk merge during SLICE-0018 offline recompute",
    )
    print(
        "HullQ SLICE-0018 Wikidata Tier-0 Expansion — OFFLINE RECOMPUTE (no network access)",
        flush=True,
    )
    print(f"  reclassifying {len(entities)} retained delta candidates", flush=True)
    print(f"  merged historical crosswalk entries: {len(historical_crosswalk)}", flush=True)

    candidates, delta_delta_clusters, baseline_collisions = classify_delta_candidates(
        entities,
        retrieved_at=retrieved_at,
        baseline=baseline,
        existing_crosswalk=historical_crosswalk,
    )

    for candidate in candidates:
        prior = prior_crosswalk.get(candidate.qid)
        if prior is not None and candidate.hullq_id != prior:
            raise SystemExit(
                f"Offline recompute would change the retained HullQ ID for {candidate.qid!r} "
                f"from {prior!r} to {candidate.hullq_id!r}; refusing to overwrite the manifest "
                "with a silently reminted identity."
            )

    discovery = old_manifest["discovery"]
    usage = old_manifest["usage_metrics"]
    now_ts = datetime.now(tz=UTC).isoformat()
    acquired_at = old_manifest.get("acquired_at") or retrieved_at
    manifest = build_sl0018_manifest(
        candidates,
        generated_at=now_ts,
        baseline=baseline,
        discovery_window_qids=discovery["discovery_window_qids"],
        requested_limit=old_manifest["requested_limit"],
        target_reached=discovery["target_reached"],
        delta_delta_clusters=delta_delta_clusters,
        baseline_collisions=baseline_collisions,
        retrieval_count=usage["retrieval_count"],
        extracted_record_count=usage["extracted_record_count"],
        acquisition_failure_count=discovery.get("acquisition_failure_count", 0),
        fetched_entity_count=discovery.get("fetched_entity_count", len(entities)),
        acquired_at=acquired_at,
        classification_recomputed_at=now_ts,
    )
    _validate_manifest_schema(manifest)

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nRecomputed manifest written to: {manifest_path}", flush=True)
    _write_live_report(manifest, report_path)
    return manifest


def _write_live_report(manifest: dict[str, Any], report_path: Path) -> None:
    counts = manifest["counts"]
    discovery = manifest["discovery"]
    usage = manifest["usage_metrics"]
    overlap = manifest["overlap"]
    baseline_ref = manifest["baseline_reference"]
    delta_collisions = manifest.get("delta_collisions", {"baseline": [], "delta_delta": []})
    lines = [
        "# HullQ SLICE-0018 Wikidata Tier-0 2,500-Window Expansion Report",
        "",
        f"**Manifest last written (generated_at):** {manifest['generated_at']}  ",
        f"**Original live acquisition (acquired_at):** {manifest['acquired_at']}  ",
        f"**Last offline reclassification (classification_recomputed_at):** {manifest['classification_recomputed_at']}  ",
        f"**Source:** {manifest['source_id']}  ",
        f"**Requested limit:** {manifest['requested_limit']}  ",
        f"**Safety ceiling:** {manifest['safety_ceiling']}",
        "",
        "## BASELINE REFERENCE (immutable SLICE-0017 input)",
        "",
        f"- Baseline manifest path: `{baseline_ref['manifest_path']}`",
        f"- Baseline manifest version: `{baseline_ref['manifest_version']}`",
        f"- Baseline sha256: `{baseline_ref['sha256']}`",
        f"- Baseline implementation head: `{baseline_ref['implementation_head']}`",
        f"- Baseline candidate count: **{baseline_ref['candidate_count']}**",
        "",
        "## ACQUISITION PATH / VERSION (audit)",
        "",
        f"- SPARQL discovery query version: `{discovery['sparql_query_version']}`",
        f"- SPARQL endpoint: `{discovery['sparql_endpoint']}`",
        f"- Entity API endpoint: `{discovery['entity_api_endpoint']}`",
        f"- Entity API version: `{discovery['entity_api_version']}`",
        "",
        "## MEASURED FACT",
        "",
        f"- Unique QIDs returned by discovery: **{discovery['unique_qids_returned']}**",
        f"- Target ({manifest['requested_limit']}) reached: **{discovery['target_reached']}**",
        f"- Overlap with accepted 1,000-QID baseline: **{overlap['overlap_count']}**",
        f"- Baseline QIDs absent from current discovery window: **{overlap['baseline_absent_count']}**",
        f"- Expansion-delta count: **{manifest['delta']['delta_count']}**",
        f"- Fetched entity count (delta only): **{discovery['fetched_entity_count']}**",
        f"- Delta candidates processed: **{discovery['delta_candidates_processed']}**",
        f"- Acquisition failure/throttle/malformed count: **{discovery['acquisition_failure_count']}**",
        f"- HTTP retrieval count: **{usage['retrieval_count']}**",
        f"- Extracted record count: **{usage['extracted_record_count']}**",
        "",
        "## CLASSIFICATION (delta only)",
        "",
        f"- AUTO_ADMIT: **{counts['auto_admit']}**",
        f"- REVIEW_REQUIRED: **{counts['review_required']}**",
        f"- NOT_ADMITTED: **{counts['not_admitted']}**",
        f"- Retained QID->HullQ-ID crosswalk count (baseline + delta): **{counts['retained_crosswalk_count']}**",
        f"- ResearchObservation count (delta): **{counts['research_observation_count']}**",
        f"- CanonicalEvidenceLink count (expected on replay, delta): **{counts['canonical_evidence_link_count']}**",
        f"- Expected combined canonical BoatModel count after baseline+delta replay: **{counts['combined_canonical_boat_model_count_expected']}**",
        "",
        "### Reason breakdown",
        "",
    ]
    for reason, count in sorted(counts["reason_breakdown"].items()):
        lines.append(f"- `{reason}`: {count}")
    lines += [
        "",
        f"## DELTA <-> BASELINE COLLISIONS ({counts['baseline_collision_count']})",
        "",
    ]
    if delta_collisions["baseline"]:
        for bc in delta_collisions["baseline"]:
            lines.append(
                f"- `{bc['delta_qid']}` collides with baseline `{bc['baseline_qids']}` — "
                f"shared key(s): `{bc['shared_keys']}`"
            )
    else:
        lines.append("- none")
    lines += [
        "",
        f"## DELTA <-> DELTA COLLISION CLUSTERS ({counts['delta_delta_collision_cluster_count']})",
        "",
    ]
    if delta_collisions["delta_delta"]:
        for cluster in delta_collisions["delta_delta"]:
            lines.append(f"- `{cluster['qids']}` — shared key(s): `{cluster['shared_keys']}`")
    else:
        lines.append("- none")
    lines += [
        "",
        "## INTERPRETATION",
        "",
        (
            "This is the SLICE-0018 measured baseline-preserving expansion delta, not a "
            "pre-committed admission-rate target. AUTO_ADMIT delta candidates become sparse "
            "Tier-0 BoatModel identities only after offline PostgreSQL replay (see "
            "REPLAY-RESULT.json / REPLAY-REPORT.md, produced by --replay)."
        ),
        "",
        "PostgreSQL version, combined baseline+delta replay counts and fresh-schema semantic "
        "mismatch count are PENDING until the retained manifest has been replayed against real "
        "PostgreSQL 18 (db-integration CI or a local --replay run).",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}", flush=True)


# ---------------------------------------------------------------------------
# Replay (offline, no network) — baseline first, delta second
# ---------------------------------------------------------------------------


def _actual_boat_model_aliases(fetched: dict[str, Any]) -> set[tuple[str, str, str]]:
    """See the identical helper in ``wikidata_tier0_runner.py`` for why this
    reads the readback dict shape via dict-key access.
    """
    return {(a["id"], a["alias_class"], a["name"]) for a in fetched.get("aliases", [])}


def replay_manifest(
    db_url: str,
    *,
    baseline_manifest_path: Path = BASELINE_MANIFEST_PATH,
    manifest_path: Path = MANIFEST_PATH,
    result_path: Path = REPLAY_RESULT_PATH,
    report_path: Path = REPLAY_REPORT_PATH,
    verify_baseline_integrity: bool = True,
) -> dict[str, Any]:
    """Offline replay: accepted SLICE-0017 baseline FIRST, retained SLICE-0018
    delta SECOND, against real PostgreSQL 18, in two independent isolated
    schemas (first-pass + idempotent-reimport, then an independent
    fresh-schema rerun).

    Fails closed via ``BaselineIntegrityError`` before any PostgreSQL use if
    *verify_baseline_integrity* (the production/CI-safe default) is true and
    the baseline artifact has drifted from its accepted SLICE-0017 semantics.
    A caller MAY pass ``verify_baseline_integrity=False`` to exercise the
    replay mechanism itself (baseline-first import, drift detection,
    idempotency, fresh-schema equality) against a small synthetic baseline
    rather than the full 1,000-candidate accepted artifact — used by the
    ``tests/persistence/`` unit-level integration test; the real accepted
    artifact is always replayed with the check enabled. Performs no network
    access.
    """
    import psycopg

    from hullq.bootstrap.wikidata_tier0 import (
        BootstrapDecision,
        build_admission,
        candidate_from_manifest_dict,
    )
    from hullq.bootstrap.wikidata_tier0 import build_bundle as build_bundle_0017
    from hullq.bootstrap.wikidata_tier0_sl0018 import build_bundle as build_bundle_sl0018
    from hullq.bootstrap.wikidata_tier0_sl0018 import load_baseline_snapshot
    from hullq.contracts import ContractRegistry
    from hullq.domain.provenance import SubjectKind
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.identity_importer import import_canonical_identity_admission
    from hullq.persistence.identity_readback import (
        fetch_boat_model,
        fetch_evidence_links_for_entity,
    )
    from hullq.persistence.identity_types import CanonicalImportStatus, CanonicalReferenceError
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations

    if verify_baseline_integrity:
        # Fails closed before any PostgreSQL use if the baseline has drifted.
        baseline = load_baseline_snapshot(baseline_manifest_path)
        print(
            f"  baseline integrity verified: {len(baseline.candidate_qids)} candidate QIDs, "
            f"sha256={baseline.sha256[:12]}...",
            flush=True,
        )
    else:
        print(
            "  baseline integrity check SKIPPED (verify_baseline_integrity=False; "
            "test-only path against a synthetic baseline)",
            flush=True,
        )
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    baseline_candidates = [
        candidate_from_manifest_dict(row) for row in baseline_manifest["candidates"]
    ]
    baseline_auto_admit = [
        c for c in baseline_candidates if c.decision == BootstrapDecision.AUTO_ADMIT
    ]
    expected_baseline_admitted_ids = {c.hullq_id for c in baseline_auto_admit}
    expected_baseline_bundle_count = sum(1 for c in baseline_candidates if c.preferred_label)
    expected_baseline_admission_count = len(baseline_auto_admit)

    delta_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    delta_candidates = [candidate_from_manifest_dict(row) for row in delta_manifest["candidates"]]
    delta_auto_admit = [c for c in delta_candidates if c.decision == BootstrapDecision.AUTO_ADMIT]
    expected_delta_admitted_ids = {c.hullq_id for c in delta_auto_admit}
    expected_delta_bundle_count = sum(1 for c in delta_candidates if c.preferred_label)
    expected_delta_admission_count = len(delta_auto_admit)

    expected_combined_admitted_ids = expected_baseline_admitted_ids | expected_delta_admitted_ids
    expected_combined_bundle_count = expected_baseline_bundle_count + expected_delta_bundle_count
    expected_combined_admission_count = (
        expected_baseline_admission_count + expected_delta_admission_count
    )

    combined = [(c, build_bundle_0017) for c in baseline_candidates] + [
        (c, build_bundle_sl0018) for c in delta_candidates
    ]

    def _expected_aliases(candidate: Any) -> set[tuple[str, str, str]]:
        admission = build_admission(candidate)
        if admission is None:
            return set()
        return {(a["id"], a["alias_class"], a["name"]) for a in admission.boat_models[0]["aliases"]}

    def _import_bundle_exhaustive(
        conn: Any, candidate: Any, bundle_builder: Any, counters: dict[str, int], *, phase: str
    ) -> None:
        bundle = bundle_builder(candidate)
        if bundle is None:
            return
        try:
            result = import_research_evidence_bundle(conn, bundle)
            if result.status == ImportStatus.IMPORTED:
                counters["imported"] += 1
            elif result.status == ImportStatus.ALREADY_IMPORTED:
                counters["already_present"] += 1
                if phase in ("baseline_first_pass", "delta_first_pass"):
                    print(
                        f"    BUNDLE UNEXPECTED ALREADY_IMPORTED ({phase}): {candidate.qid}",
                        flush=True,
                    )
            elif result.status == ImportStatus.CONFLICT:
                counters["conflict"] += 1
                print(
                    f"    BUNDLE CONFLICT ({phase}): {candidate.qid}: {result.detail}", flush=True
                )
            else:
                counters["unexpected_status"] += 1
                print(
                    f"    BUNDLE UNEXPECTED STATUS {result.status} ({phase}): {candidate.qid}",
                    flush=True,
                )
        except Exception as exc:
            counters["error"] += 1
            print(f"    BUNDLE ERROR ({phase}): {candidate.qid}: {exc}", flush=True)

    def _import_admission_exhaustive(
        conn: Any, candidate: Any, registry: Any, counters: dict[str, int], *, phase: str
    ) -> None:
        admission = build_admission(candidate)
        if admission is None:
            return
        try:
            result = import_canonical_identity_admission(conn, admission, registry)
            if result.status == CanonicalImportStatus.IMPORTED:
                counters["imported"] += 1
            elif result.status == CanonicalImportStatus.ALREADY_IMPORTED:
                counters["already_present"] += 1
                if phase in ("baseline_first_pass", "delta_first_pass"):
                    print(
                        f"    ADMISSION UNEXPECTED ALREADY_IMPORTED ({phase}): {candidate.qid}",
                        flush=True,
                    )
            elif result.status == CanonicalImportStatus.CONFLICT:
                counters["conflict"] += 1
                print(
                    f"    ADMISSION CONFLICT ({phase}): {candidate.qid}: {result.detail}",
                    flush=True,
                )
            else:
                counters["unexpected_status"] += 1
                print(
                    f"    ADMISSION UNEXPECTED STATUS {result.status} ({phase}): {candidate.qid}",
                    flush=True,
                )
        except CanonicalReferenceError as exc:
            counters["reference_error"] += 1
            print(
                f"    ADMISSION REFERENCE ERROR ({phase}): {candidate.qid}: {exc}",
                flush=True,
            )
        except Exception as exc:
            counters["error"] += 1
            print(f"    ADMISSION ERROR ({phase}): {candidate.qid}: {exc}", flush=True)

    def _readback_matches(conn: Any, candidate: Any, mismatch_prefix: str) -> bool:
        fetched = fetch_boat_model(conn, candidate.hullq_id)
        if fetched is None:
            print(f"    {mismatch_prefix} MISSING: {candidate.qid}", flush=True)
            return False
        ok = True
        if fetched.get("canonical_name") != candidate.preferred_label:
            print(f"    {mismatch_prefix} NAME MISMATCH: {candidate.qid}", flush=True)
            ok = False
        if fetched.get("first_built") is not None or fetched.get("last_built") is not None:
            print(
                f"    {mismatch_prefix} UNEXPECTED first_built/last_built: {candidate.qid}",
                flush=True,
            )
            ok = False
        if fetched.get("brand_relationships") != [] or fetched.get("boat_design_ids") != []:
            print(f"    {mismatch_prefix} UNEXPECTED RELATIONSHIP: {candidate.qid}", flush=True)
            ok = False
        if _actual_boat_model_aliases(fetched) != _expected_aliases(candidate):
            print(f"    {mismatch_prefix} ALIAS MISMATCH: {candidate.qid}", flush=True)
            ok = False

        links = fetch_evidence_links_for_entity(conn, SubjectKind.BOAT_MODEL, candidate.hullq_id)
        if (
            len(links) != 1
            or links[0].link_id != candidate.evidence_link_id
            or str(links[0].entity_kind) != str(SubjectKind.BOAT_MODEL)
            or links[0].entity_id != candidate.hullq_id
            or links[0].observation_id != candidate.observation_id
            or links[0].evidence_id is not None
        ):
            print(
                f"    {mismatch_prefix} EVIDENCE LINK MISMATCH: {candidate.qid}: {links}",
                flush=True,
            )
            ok = False
        return ok

    def _run_combined_pass(conn: Any, *, label: str) -> dict[str, Any]:
        """Baseline import -> baseline verification -> delta import -> combined
        verification -> exact reimport, all within one already-isolated schema.
        """
        bundle_counts = {
            "imported": 0,
            "already_present": 0,
            "conflict": 0,
            "error": 0,
            "unexpected_status": 0,
        }
        admission_counts = {
            "imported": 0,
            "already_present": 0,
            "conflict": 0,
            "reference_error": 0,
            "error": 0,
            "unexpected_status": 0,
        }

        t0 = time.perf_counter()
        for candidate in baseline_candidates:
            _import_bundle_exhaustive(
                conn, candidate, build_bundle_0017, bundle_counts, phase="baseline_first_pass"
            )
            _import_admission_exhaustive(
                conn, candidate, registry, admission_counts, phase="baseline_first_pass"
            )
        baseline_elapsed = time.perf_counter() - t0
        print(
            f"  [{label}] baseline import: bundles={bundle_counts} admissions={admission_counts}",
            flush=True,
        )

        # --- Verify baseline exact counts/graph BEFORE delta work applies ---
        baseline_counts_match = (
            bundle_counts["imported"] == expected_baseline_bundle_count
            and admission_counts["imported"] == expected_baseline_admission_count
        )
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM canonical_boat_models")
            baseline_actual_ids = {row[0] for row in cur.fetchall()}
        baseline_id_set_matches = baseline_actual_ids == expected_baseline_admitted_ids
        baseline_readback_mismatches = 0
        for candidate in baseline_auto_admit:
            if not _readback_matches(conn, candidate, f"{label} BASELINE-READBACK"):
                baseline_readback_mismatches += 1
        print(
            f"  [{label}] baseline verified before delta: counts_match={baseline_counts_match} "
            f"id_set_matches={baseline_id_set_matches} readback_mismatches={baseline_readback_mismatches}",
            flush=True,
        )

        t0 = time.perf_counter()
        for candidate in delta_candidates:
            _import_bundle_exhaustive(
                conn, candidate, build_bundle_sl0018, bundle_counts, phase="delta_first_pass"
            )
            _import_admission_exhaustive(
                conn, candidate, registry, admission_counts, phase="delta_first_pass"
            )
        delta_elapsed = time.perf_counter() - t0
        print(
            f"  [{label}] combined import: bundles={bundle_counts} admissions={admission_counts}",
            flush=True,
        )

        expected_counts_match = (
            bundle_counts["imported"] == expected_combined_bundle_count
            and admission_counts["imported"] == expected_combined_admission_count
        )
        if not expected_counts_match:
            print(
                f"    EXPECTED-COUNT MISMATCH [{label}]: bundle_imported={bundle_counts['imported']} "
                f"(expected {expected_combined_bundle_count}), admission_imported="
                f"{admission_counts['imported']} (expected {expected_combined_admission_count})",
                flush=True,
            )

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM canonical_boat_models")
            actual_admitted_ids = {row[0] for row in cur.fetchall()}
        missing_ids = expected_combined_admitted_ids - actual_admitted_ids
        extra_ids = actual_admitted_ids - expected_combined_admitted_ids
        canonical_id_set_matches = not missing_ids and not extra_ids
        if not canonical_id_set_matches:
            print(
                f"    CANONICAL BOAT MODEL ID SET MISMATCH [{label}]: missing="
                f"{sorted(missing_ids)} extra={sorted(extra_ids)}",
                flush=True,
            )

        stray_row_counts: dict[str, int] = {}
        with conn.cursor() as cur:
            for table in ("canonical_brands", "canonical_organizations", "canonical_boat_designs"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stray_row_counts[table] = cur.fetchone()[0]
        no_stray_rows = all(count == 0 for count in stray_row_counts.values())
        if not no_stray_rows:
            print(
                f"    UNEXPECTED BRAND/ORGANIZATION/BOATDESIGN ROWS [{label}]: {stray_row_counts}",
                flush=True,
            )

        # --- Deep readback: baseline (post-delta drift check) + delta ---
        post_delta_baseline_mismatches = 0
        for candidate in baseline_auto_admit:
            if not _readback_matches(conn, candidate, f"{label} BASELINE-DRIFT-CHECK"):
                post_delta_baseline_mismatches += 1

        delta_readback_mismatches = 0
        for candidate in delta_auto_admit:
            if not _readback_matches(conn, candidate, f"{label} DELTA-READBACK"):
                delta_readback_mismatches += 1

        readback_mismatches = post_delta_baseline_mismatches + delta_readback_mismatches
        print(f"  [{label}] readback_mismatches (combined)={readback_mismatches}", flush=True)

        unexpected_canonical = 0
        for candidate in baseline_candidates + delta_candidates:
            if candidate.decision == BootstrapDecision.AUTO_ADMIT:
                continue
            if (
                candidate.hullq_id is not None
                and fetch_boat_model(conn, candidate.hullq_id) is not None
            ):
                unexpected_canonical += 1
                print(
                    f"    UNEXPECTED CANONICAL ROW FOR NON-ADMITTED [{label}]: {candidate.qid}",
                    flush=True,
                )

        # --- Exact re-import idempotency ---
        reimport_already = reimport_conflict = reimport_error = 0
        t0 = time.perf_counter()
        for candidate, bundle_builder in combined:
            bundle = bundle_builder(candidate)
            if bundle is not None:
                try:
                    result = import_research_evidence_bundle(conn, bundle)
                    if result.status != ImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    BUNDLE REIMPORT NOT IDEMPOTENT [{label}]: {candidate.qid}: "
                            f"{result.status}",
                            flush=True,
                        )
                    else:
                        reimport_already += 1
                except Exception as exc:
                    reimport_error += 1
                    print(
                        f"    BUNDLE REIMPORT ERROR [{label}]: {candidate.qid}: {exc}", flush=True
                    )

            admission = build_admission(candidate)
            if admission is not None:
                try:
                    result = import_canonical_identity_admission(conn, admission, registry)
                    if result.status != CanonicalImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    ADMISSION REIMPORT NOT IDEMPOTENT [{label}]: {candidate.qid}: "
                            f"{result.status}",
                            flush=True,
                        )
                    else:
                        reimport_already += 1
                except Exception as exc:
                    reimport_error += 1
                    print(
                        f"    ADMISSION REIMPORT ERROR [{label}]: {candidate.qid}: {exc}",
                        flush=True,
                    )
        reimport_elapsed = time.perf_counter() - t0
        print(
            f"  [{label}] reimport: already_imported={reimport_already} "
            f"conflict={reimport_conflict} error={reimport_error}",
            flush=True,
        )

        return {
            "bundle": bundle_counts,
            "admission": admission_counts,
            "expected_counts_match": expected_counts_match,
            "baseline_verified_before_delta": {
                "counts_match": baseline_counts_match,
                "id_set_matches": baseline_id_set_matches,
                "readback_mismatches": baseline_readback_mismatches,
            },
            "readback": {
                "mismatches": readback_mismatches,
                "post_delta_baseline_drift_mismatches": post_delta_baseline_mismatches,
                "unexpected_canonical_rows_for_non_admitted": unexpected_canonical,
                "canonical_id_set_matches": canonical_id_set_matches,
                "no_stray_brand_organization_boatdesign_rows": no_stray_rows,
                "stray_row_counts": stray_row_counts,
            },
            "reimport": {
                "already_imported": reimport_already,
                "conflict": reimport_conflict,
                "error": reimport_error,
                "wall_clock_seconds": round(reimport_elapsed, 4),
            },
            "wall_clock_seconds": round(baseline_elapsed + delta_elapsed, 4),
        }

    registry = ContractRegistry.from_directory(ROOT / "specs")

    print("HullQ SLICE-0018 Wikidata Tier-0 2,500-Window Expansion — REPLAY", flush=True)
    print(
        f"  baseline_candidates={len(baseline_candidates)} baseline_auto_admit={len(baseline_auto_admit)} "
        f"delta_candidates={len(delta_candidates)} delta_auto_admit={len(delta_auto_admit)}",
        flush=True,
    )
    print(
        f"  expected combined: bundle_imported={expected_combined_bundle_count} "
        f"admission_imported={expected_combined_admission_count}",
        flush=True,
    )

    schema1 = "hullq_wdt0_sl0018_run1_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
    schema2 = "hullq_wdt0_sl0018_run2_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]

    conn1 = psycopg.connect(db_url)
    try:
        with _isolated_schema(conn1, schema1):
            apply_migrations(conn1)
            pg_ver = _pg_version(conn1)
            pass1 = _run_combined_pass(conn1, label="schema1")
    finally:
        conn1.close()

    conn2 = psycopg.connect(db_url)
    try:
        with _isolated_schema(conn2, schema2):
            apply_migrations(conn2)
            pass2 = _run_combined_pass(conn2, label="schema2")
    finally:
        conn2.close()

    result_doc: dict[str, Any] = {
        "schema_version": "0018-replay-v1",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "postgresql_version": pg_ver,
        "baseline_manifest_candidates": len(baseline_candidates),
        "baseline_manifest_auto_admit": len(baseline_auto_admit),
        "delta_manifest_candidates": len(delta_candidates),
        "delta_manifest_auto_admit": len(delta_auto_admit),
        "expected": {
            "combined_bundle_count": expected_combined_bundle_count,
            "combined_admission_count": expected_combined_admission_count,
        },
        "first_pass": pass1,
        "fresh_schema_rerun": pass2,
    }
    result_doc["all_zero_tolerance_conditions_clear"] = (
        pass1["bundle"]["already_present"] == 0
        and pass1["bundle"]["conflict"] == 0
        and pass1["bundle"]["error"] == 0
        and pass1["bundle"]["unexpected_status"] == 0
        and pass1["admission"]["already_present"] == 0
        and pass1["admission"]["conflict"] == 0
        and pass1["admission"]["reference_error"] == 0
        and pass1["admission"]["error"] == 0
        and pass1["admission"]["unexpected_status"] == 0
        and pass1["expected_counts_match"]
        and pass1["baseline_verified_before_delta"]["counts_match"]
        and pass1["baseline_verified_before_delta"]["id_set_matches"]
        and pass1["baseline_verified_before_delta"]["readback_mismatches"] == 0
        and pass1["readback"]["mismatches"] == 0
        and pass1["readback"]["post_delta_baseline_drift_mismatches"] == 0
        and pass1["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
        and pass1["readback"]["canonical_id_set_matches"]
        and pass1["readback"]["no_stray_brand_organization_boatdesign_rows"]
        and pass1["reimport"]["conflict"] == 0
        and pass1["reimport"]["error"] == 0
        and pass2["bundle"]["already_present"] == 0
        and pass2["bundle"]["conflict"] == 0
        and pass2["bundle"]["error"] == 0
        and pass2["bundle"]["unexpected_status"] == 0
        and pass2["admission"]["already_present"] == 0
        and pass2["admission"]["conflict"] == 0
        and pass2["admission"]["reference_error"] == 0
        and pass2["admission"]["error"] == 0
        and pass2["admission"]["unexpected_status"] == 0
        and pass2["expected_counts_match"]
        and pass2["baseline_verified_before_delta"]["counts_match"]
        and pass2["baseline_verified_before_delta"]["id_set_matches"]
        and pass2["baseline_verified_before_delta"]["readback_mismatches"] == 0
        and pass2["readback"]["mismatches"] == 0
        and pass2["readback"]["post_delta_baseline_drift_mismatches"] == 0
        and pass2["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
        and pass2["readback"]["canonical_id_set_matches"]
        and pass2["readback"]["no_stray_brand_organization_boatdesign_rows"]
        and pass2["reimport"]["conflict"] == 0
        and pass2["reimport"]["error"] == 0
    )

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result_doc, indent=2), encoding="utf-8")
    print(f"\nReplay result written to: {result_path}", flush=True)
    print(
        f"All zero-tolerance conditions clear: {result_doc['all_zero_tolerance_conditions_clear']}",
        flush=True,
    )
    _write_replay_report(result_doc, report_path)
    return result_doc


def _write_replay_report(result_doc: dict[str, Any], report_path: Path) -> None:
    exp = result_doc["expected"]
    fp = result_doc["first_pass"]
    fr = result_doc["fresh_schema_rerun"]
    lines = [
        "# HullQ SLICE-0018 Wikidata Tier-0 2,500-Window Expansion Replay Report",
        "",
        f"**Run timestamp:** {result_doc['run_timestamp']}  ",
        f"**PostgreSQL version:** {result_doc['postgresql_version']}  ",
        f"**Baseline manifest candidates/auto_admit:** {result_doc['baseline_manifest_candidates']}/{result_doc['baseline_manifest_auto_admit']}  ",
        f"**Delta manifest candidates/auto_admit:** {result_doc['delta_manifest_candidates']}/{result_doc['delta_manifest_auto_admit']}  ",
        f"**Expected combined bundle/admission imports:** {exp['combined_bundle_count']}/{exp['combined_admission_count']}",
        "",
        "Both passes below run baseline import first, verify the baseline "
        "graph, then import the delta second, in their own newly-created, "
        "migrated-from-zero, isolated PostgreSQL schema.",
        "",
        "## PASS 1 — FIRST-PASS COMBINED IMPORT (isolated schema)",
        "",
        f"- bundle (combined): {fp['bundle']}",
        f"- admission (combined): {fp['admission']}",
        f"- expected combined imported counts match exactly: {fp['expected_counts_match']}",
        f"- baseline verified before delta applied: {fp['baseline_verified_before_delta']}",
        f"- wall clock: {fp['wall_clock_seconds']}s",
        "",
        "## DEEP READBACK VERIFICATION (same isolated schema as pass 1)",
        "",
        f"- semantic mismatches (baseline + delta): {fp['readback']['mismatches']}",
        f"- post-delta baseline drift mismatches: {fp['readback']['post_delta_baseline_drift_mismatches']}",
        f"- unexpected canonical rows for non-admitted candidates: {fp['readback']['unexpected_canonical_rows_for_non_admitted']}",
        f"- combined canonical BoatModel ID set matches exactly: {fp['readback']['canonical_id_set_matches']}",
        f"- zero stray Brand/Organization/BoatDesign rows: {fp['readback']['no_stray_brand_organization_boatdesign_rows']} ({fp['readback']['stray_row_counts']})",
        "",
        "## EXACT RE-REPLAY (IDEMPOTENCY, same isolated schema)",
        "",
        f"- already_imported/conflict/error: {fp['reimport']['already_imported']}/{fp['reimport']['conflict']}/{fp['reimport']['error']}",
        f"- wall clock: {fp['reimport']['wall_clock_seconds']}s",
        "",
        "## PASS 2 — INDEPENDENT FRESH-SCHEMA REPLAY (second isolated schema, full combined semantic graph equality)",
        "",
        f"- bundle (combined): {fr['bundle']}",
        f"- admission (combined): {fr['admission']}",
        f"- baseline verified before delta applied: {fr['baseline_verified_before_delta']}",
        f"- semantic mismatches: {fr['readback']['mismatches']}",
        f"- post-delta baseline drift mismatches: {fr['readback']['post_delta_baseline_drift_mismatches']}",
        f"- combined canonical ID set matches exactly: {fr['readback']['canonical_id_set_matches']}",
        f"- zero stray Brand/Organization/BoatDesign rows: {fr['readback']['no_stray_brand_organization_boatdesign_rows']} ({fr['readback']['stray_row_counts']})",
        f"- expected combined imported counts match exactly: {fr['expected_counts_match']}",
        "",
        f"## RESULT: all zero-tolerance conditions clear: **{result_doc['all_zero_tolerance_conditions_clear']}**",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Replay report written to: {report_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HullQ SLICE-0018 Wikidata Tier-0 2,500-window expansion runner"
    )
    parser.add_argument(
        "--live", action="store_true", help="Run the one live discovery+acquisition run"
    )
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="Offline reclassification of the retained SLICE-0018 manifest (no network access)",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay accepted baseline first, retained SLICE-0018 delta second, against PostgreSQL",
    )
    parser.add_argument(
        "--user-agent", default=None, help="Wikimedia-policy-compliant User-Agent (live mode)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_REQUESTED_LIMIT,
        help="Requested discovery-window candidate limit (live mode)",
    )
    parser.add_argument("--db-url", default=None, help="PostgreSQL connection URL (replay mode)")
    parser.add_argument(
        "--baseline-manifest",
        default=str(BASELINE_MANIFEST_PATH),
        help="Accepted SLICE-0017 baseline manifest path",
    )
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="SLICE-0018 manifest path")
    parser.add_argument(
        "--report",
        default=str(REPORT_PATH),
        help="Human-readable report path (live/recompute mode)",
    )
    parser.add_argument("--result", default=str(REPLAY_RESULT_PATH), help="Replay result JSON path")
    parser.add_argument(
        "--replay-report", default=str(REPLAY_REPORT_PATH), help="Replay report Markdown path"
    )
    args = parser.parse_args()

    modes_selected = sum([args.live, args.recompute, args.replay])
    if modes_selected != 1:
        raise SystemExit("Specify exactly one of --live, --recompute or --replay")

    if args.live:
        if not args.user_agent:
            raise SystemExit("--user-agent is required for --live")
        run_live_bootstrap(
            user_agent=args.user_agent,
            requested_limit=args.limit,
            baseline_manifest_path=Path(args.baseline_manifest),
            manifest_path=Path(args.manifest),
            report_path=Path(args.report),
        )
    elif args.recompute:
        recompute_manifest_offline(
            baseline_manifest_path=Path(args.baseline_manifest),
            manifest_path=Path(args.manifest),
            report_path=Path(args.report),
        )
    else:
        db_url = _get_db_url(args.db_url)
        replay_manifest(
            db_url,
            baseline_manifest_path=Path(args.baseline_manifest),
            manifest_path=Path(args.manifest),
            result_path=Path(args.result),
            report_path=Path(args.replay_report),
        )


if __name__ == "__main__":
    main()
