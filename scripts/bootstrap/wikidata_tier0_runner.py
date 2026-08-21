"""SLICE-0017 controlled Wikidata Tier-0 bootstrap runner.

Three independent modes:

``--live``
    Perform the one controlled live Wikidata bootstrap run: rights-gated
    deterministic discovery of up to ``--limit`` (default 1,000) direct
    sailboat-class candidates, bounded entity acquisition, deterministic
    classification, and a retained versioned manifest + human-readable
    report written under ``research/bootstrap/wikidata/``. Requires network
    access and is not part of normal CI. If a manifest already exists at the
    target path, its retained QID -> HullQ-ID crosswalk is loaded first and
    every already-mapped QID reuses its retained ID — an existing QID is
    never silently reminted.

``--recompute``
    Offline reclassification of the already-retained manifest using the
    current classification logic, with NO network access: reconstructs the
    original acquired label/alias facts from the committed manifest and
    reruns classification only, reusing every retained HullQ ID exactly.
    Used to correct classification-logic defects without a wasteful live
    Wikidata reacquisition.

``--replay``
    Offline replay of the already-retained manifest against real
    PostgreSQL 18: import, deep semantic readback verification, exact
    re-import (idempotency), and a fresh-schema isolated rerun (full
    semantic graph equality). Performs no network access. This is what
    normal ``db-integration`` CI runs.

Usage::

    uv run python scripts/bootstrap/wikidata_tier0_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)" \\
        --limit 1000

    uv run python scripts/bootstrap/wikidata_tier0_runner.py --recompute

    uv run python scripts/bootstrap/wikidata_tier0_runner.py --replay \\
        --db-url postgresql://user:pass@host:5432/db
"""

from __future__ import annotations

import argparse
import contextlib
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

BOOTSTRAP_DIR = ROOT / "research" / "bootstrap" / "wikidata"
MANIFEST_PATH = BOOTSTRAP_DIR / "manifest.json"
REPORT_PATH = BOOTSTRAP_DIR / "REPORT.md"
MANIFEST_SCHEMA_PATH = BOOTSTRAP_DIR / "manifest_schema.json"
REPLAY_RESULT_PATH = BOOTSTRAP_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = BOOTSTRAP_DIR / "REPLAY-REPORT.md"


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
    set it as the connection's search_path, and drop it again on exit.

    This makes every operation performed on *conn* while the context is
    active fully isolated from whatever pre-existing rows the default/public
    schema may hold (e.g. leftover state from an earlier ``tests/persistence/``
    run or the benchmark runner in the same CI job) — the acceptance proof
    must not depend on CI step ordering or on any other job having left a
    clean database behind.
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
    print("Manifest schema validation: PASS", flush=True)


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

    Fail-safe rerun behavior: if *manifest_path* already exists, its full
    historical ``retained_crosswalk`` is loaded and validated for internal
    consistency BEFORE any network request, and reused exactly — an existing
    retained QID is never silently reminted, and a conflicting retained
    mapping fails closed before any new manifest is written. A retained QID
    that is absent from this run's discovery window (e.g. it fell outside
    the current first-N SPARQL result) remains visible in the new manifest's
    ``retained_crosswalk`` — so it is never silently reminted if it
    reappears later — but is NOT carried into ``candidates``: the current
    bounded candidate set (and therefore ``candidates_processed``,
    ``collision_clusters`` and every classification decision) always
    describes exactly this run's discovery window, never a historical QID
    this run never actually saw.
    """
    import httpx

    from hullq.bootstrap.wikidata_tier0 import (
        BOOTSTRAP_SAFETY_CEILING,
        build_manifest,
        classify_candidates,
        compute_collision_clusters,
        load_crosswalk_from_manifest,
        validate_crosswalk_consistency,
    )
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig

    source_path = ROOT / "fixtures" / "sources" / "wikidata_source.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))

    config = WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=60.0)

    print("HullQ SLICE-0017 Wikidata Tier-0 Bootstrap — LIVE RUN", flush=True)
    print(
        f"  requested_limit={requested_limit} safety_ceiling={BOOTSTRAP_SAFETY_CEILING}", flush=True
    )

    historical_crosswalk: dict[str, str] = {}
    if manifest_path.exists():
        # Validated (fails closed on any internal conflict) before any
        # network request below.
        prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        historical_crosswalk = load_crosswalk_from_manifest(prior_manifest)
        print(
            f"  loaded {len(historical_crosswalk)} retained QID->HullQ-ID mapping(s) from "
            f"existing manifest at {manifest_path}; every already-mapped QID will reuse its "
            "retained ID exactly (never reminted)",
            flush=True,
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
        fetched_entity_count = len(entities)
        print(f"  fetched_entity_count={fetched_entity_count}", flush=True)

        usage = adapter.usage_metrics

    retrieved_at = datetime.now(tz=UTC).isoformat()
    # candidates describes ONLY this run's current discovery/entities window
    # — never a QID this run did not actually see.
    candidates = classify_candidates(
        entities, retrieved_at=retrieved_at, existing_crosswalk=historical_crosswalk
    )

    # Fail closed before writing anything if the current window's crosswalk
    # is internally inconsistent.
    validate_crosswalk_consistency(candidates)
    clusters = compute_collision_clusters(entities)

    manifest = build_manifest(
        candidates,
        generated_at=retrieved_at,
        requested_limit=requested_limit,
        unique_qids_returned=unique_returned,
        retrieval_count=usage.retrieval_count,
        extracted_record_count=usage.extracted_record_count,
        target_reached=target_reached,
        collision_clusters=clusters,
        acquisition_failure_count=0,
        fetched_entity_count=fetched_entity_count,
        acquired_at=retrieved_at,
        classification_recomputed_at=None,
        # Merges with the current candidates' own mappings, failing closed on
        # drift; a historical QID absent from `candidates` still appears in
        # the manifest's retained_crosswalk, never in candidates itself.
        historical_crosswalk=historical_crosswalk,
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
    manifest_path: Path = MANIFEST_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    """Reclassify the already-retained manifest using current classification
    logic, with zero network access.

    Reconstructs the original acquired ``WikidataEntityData`` (qid, label,
    aliases) from the committed manifest rows — never re-fetches from
    Wikidata — and reruns ``classify_candidates`` with the retained crosswalk
    loaded, so every previously admitted QID keeps its exact HullQ ID. The
    per-candidate ``retrieved_at``/observation timestamp is preserved from
    the original acquisition, not replaced with the recompute time.
    """
    from hullq.bootstrap.wikidata_tier0 import (
        build_manifest,
        classify_candidates,
        compute_collision_clusters,
        load_crosswalk_from_manifest,
        validate_crosswalk_consistency,
    )
    from hullq.sources.wikidata import WikidataEntityData

    old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = old_manifest["candidates"]
    if not rows:
        raise SystemExit(f"No candidates found in {manifest_path}; nothing to recompute.")

    retrieved_at_values = {row["retrieved_at"] for row in rows}
    if len(retrieved_at_values) != 1:
        raise SystemExit(
            "Retained manifest rows do not share one uniform retrieved_at timestamp; "
            "offline recompute requires a single-acquisition manifest."
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

    existing_crosswalk = load_crosswalk_from_manifest(old_manifest)
    print(
        "HullQ SLICE-0017 Wikidata Tier-0 Bootstrap — OFFLINE RECOMPUTE (no network access)",
        flush=True,
    )
    print(f"  reclassifying {len(entities)} retained candidates", flush=True)
    print(f"  retained crosswalk entries loaded: {len(existing_crosswalk)}", flush=True)

    candidates = classify_candidates(
        entities, retrieved_at=retrieved_at, existing_crosswalk=existing_crosswalk
    )
    validate_crosswalk_consistency(candidates)

    # An already-admitted QID that remains admitted must keep its exact ID.
    for candidate in candidates:
        prior = existing_crosswalk.get(candidate.qid)
        if prior is not None and candidate.hullq_id != prior:
            raise SystemExit(
                f"Offline recompute would change the retained HullQ ID for {candidate.qid!r} "
                f"from {prior!r} to {candidate.hullq_id!r}; refusing to overwrite the manifest "
                "with a silently reminted identity."
            )

    clusters = compute_collision_clusters(entities)
    discovery = old_manifest["discovery"]
    usage = old_manifest["usage_metrics"]
    now_ts = datetime.now(tz=UTC).isoformat()
    # The original live acquisition timestamp is never replaced by the
    # recompute's own timestamp: preserved verbatim from the retained
    # manifest when present, else recovered from the uniform per-candidate
    # retrieved_at (the only source of truth for a pre-acquired_at manifest).
    acquired_at = old_manifest.get("acquired_at") or retrieved_at
    manifest = build_manifest(
        candidates,
        generated_at=now_ts,
        requested_limit=old_manifest["requested_limit"],
        unique_qids_returned=discovery["unique_qids_returned"],
        retrieval_count=usage["retrieval_count"],
        extracted_record_count=usage["extracted_record_count"],
        target_reached=discovery["target_reached"],
        collision_clusters=clusters,
        acquisition_failure_count=discovery.get("acquisition_failure_count", 0),
        fetched_entity_count=discovery.get("fetched_entity_count", len(entities)),
        acquired_at=acquired_at,
        classification_recomputed_at=now_ts,
        historical_crosswalk=existing_crosswalk,
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
    clusters = manifest.get("collision_clusters", [])
    lines = [
        "# HullQ SLICE-0017 Wikidata Tier-0 Bootstrap Report",
        "",
        f"**Manifest last written (generated_at):** {manifest['generated_at']}  ",
        f"**Original live acquisition (acquired_at):** {manifest['acquired_at']}  ",
        f"**Last offline reclassification (classification_recomputed_at):** {manifest['classification_recomputed_at']}  ",
        f"**Source:** {manifest['source_id']}  ",
        f"**Requested limit:** {manifest['requested_limit']}  ",
        f"**Safety ceiling:** {manifest['safety_ceiling']}",
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
        f"- Fetched entity count: **{discovery['fetched_entity_count']}**",
        f"- Candidates processed: **{discovery['candidates_processed']}**",
        f"- Acquisition failure/throttle/malformed count: **{discovery['acquisition_failure_count']}**",
        f"- HTTP retrieval count: **{usage['retrieval_count']}**",
        f"- Extracted record count: **{usage['extracted_record_count']}**",
        "",
        "## CLASSIFICATION",
        "",
        f"- AUTO_ADMIT: **{counts['auto_admit']}**",
        f"- REVIEW_REQUIRED: **{counts['review_required']}**",
        f"- NOT_ADMITTED: **{counts['not_admitted']}**",
        f"- Retained QID->HullQ-ID crosswalk count: **{counts['retained_crosswalk_count']}**",
        f"- ResearchObservation count: **{counts['research_observation_count']}**",
        f"- CanonicalEvidenceLink count (expected on replay): **{counts['canonical_evidence_link_count']}**",
        "",
        "### Reason breakdown",
        "",
    ]
    for reason, count in sorted(counts["reason_breakdown"].items()):
        lines.append(f"- `{reason}`: {count}")
    lines += [
        "",
        f"## COLLISION CLUSTERS ({counts['collision_cluster_count']} complete cluster(s))",
        "",
    ]
    if clusters:
        for cluster in clusters:
            lines.append(f"- `{cluster['qids']}` — shared key(s): `{cluster['shared_keys']}`")
    else:
        lines.append("- none")
    lines += [
        "",
        "## INTERPRETATION",
        "",
        (
            "This is a first controlled broad identity bootstrap measurement, not a "
            "pre-committed admission-rate target. AUTO_ADMIT candidates become sparse "
            "Tier-0 BoatModel identities only after offline PostgreSQL replay "
            "(see REPLAY-RESULT.json / REPLAY-REPORT.md, produced by --replay)."
        ),
        "",
        "PostgreSQL version, first-replay/re-replay counts and fresh-schema semantic "
        "mismatch count are PENDING until the retained manifest has been replayed "
        "against real PostgreSQL 18 (db-integration CI or a local --replay run).",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}", flush=True)


# ---------------------------------------------------------------------------
# Replay (offline, no network) — deep semantic proof
# ---------------------------------------------------------------------------


def _actual_boat_model_aliases(fetched: dict[str, Any]) -> set[tuple[str, str, str]]:
    """Extract the ``(id, alias_class, name)`` tuple set from a
    ``fetch_boat_model()`` readback dict.

    ``hullq.persistence.identity_readback.fetch_boat_model()`` returns a
    ``BOAT_MODEL_SCHEMA.v0.2``-shaped plain dict; each entry in its
    ``"aliases"`` list is itself a plain dict produced by
    ``_alias_to_embedded_dict()`` — ``{"id", "alias_class", "name", "notes"}``
    with ``alias_class`` already stringified — never an ``IdentityAlias``
    object. This must be read via dict-key access (module-level and unit
    tested precisely because a prior attribute-access implementation raised
    ``AttributeError: 'dict' object has no attribute 'id'`` against the real
    readback shape once an admitted candidate actually had aliases).
    """
    return {(a["id"], a["alias_class"], a["name"]) for a in fetched.get("aliases", [])}


def replay_manifest(
    db_url: str,
    manifest_path: Path = MANIFEST_PATH,
    result_path: Path = REPLAY_RESULT_PATH,
    report_path: Path = REPLAY_REPORT_PATH,
) -> dict[str, Any]:
    """Offline replay of the retained manifest against real PostgreSQL 18.

    Both the first-pass replay proof and the independent fresh-schema replay
    proof run in their own newly-created, migrated-from-zero, isolated
    PostgreSQL schema (dropped in a ``finally`` block on exit). Neither proof
    depends on — or is contaminated by — whatever rows a prior CI step
    (``tests/persistence/`` or the benchmark runner) may have left behind in
    the default/public schema.

    Every possible ``ImportStatus``/``CanonicalImportStatus`` outcome is
    explicitly counted, including an unexpected ``ALREADY_IMPORTED`` on a
    genuinely fresh schema. The zero-tolerance boolean requires the exact
    expected imported counts and exact expected canonical BoatModel ID set —
    not merely the absence of explicit conflict/error counters — plus deep
    semantic readback (canonical name, stable aliases, first_built/last_built
    remaining null, and the exact expected CanonicalEvidenceLink including
    link_id/entity_kind/entity_id/observation_id/null-evidence_id) and zero
    stray Brand/Organization/BoatDesign rows. Performs no network access.
    """
    import psycopg

    from hullq.bootstrap.wikidata_tier0 import (
        BootstrapDecision,
        build_admission,
        build_bundle,
        candidate_from_manifest_dict,
    )
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

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = [candidate_from_manifest_dict(row) for row in manifest["candidates"]]
    auto_admit = [c for c in candidates if c.decision == BootstrapDecision.AUTO_ADMIT]
    expected_admitted_ids = {c.hullq_id for c in auto_admit}
    expected_bundle_count = sum(1 for c in candidates if build_bundle(c) is not None)
    expected_admission_count = len(auto_admit)

    def _expected_aliases(candidate: Any) -> set[tuple[str, str, str]]:
        admission = build_admission(candidate)
        if admission is None:
            return set()
        return {(a["id"], a["alias_class"], a["name"]) for a in admission.boat_models[0]["aliases"]}

    def _import_bundle_exhaustive(
        conn: Any, candidate: Any, counters: dict[str, int], *, phase: str
    ) -> None:
        bundle = build_bundle(candidate)
        if bundle is None:
            return
        try:
            result = import_research_evidence_bundle(conn, bundle)
            if result.status == ImportStatus.IMPORTED:
                counters["imported"] += 1
            elif result.status == ImportStatus.ALREADY_IMPORTED:
                counters["already_present"] += 1
                if phase == "first_pass":
                    print(
                        f"    BUNDLE UNEXPECTED ALREADY_IMPORTED on fresh schema: {candidate.qid}",
                        flush=True,
                    )
            elif result.status == ImportStatus.CONFLICT:
                counters["conflict"] += 1
                print(f"    BUNDLE CONFLICT: {candidate.qid}: {result.detail}", flush=True)
            else:
                counters["unexpected_status"] += 1
                print(f"    BUNDLE UNEXPECTED STATUS {result.status}: {candidate.qid}", flush=True)
        except Exception as exc:
            counters["error"] += 1
            print(f"    BUNDLE ERROR: {candidate.qid}: {exc}", flush=True)

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
                if phase == "first_pass":
                    print(
                        f"    ADMISSION UNEXPECTED ALREADY_IMPORTED on fresh schema: {candidate.qid}",
                        flush=True,
                    )
            elif result.status == CanonicalImportStatus.CONFLICT:
                counters["conflict"] += 1
                print(f"    ADMISSION CONFLICT: {candidate.qid}: {result.detail}", flush=True)
            else:
                counters["unexpected_status"] += 1
                print(
                    f"    ADMISSION UNEXPECTED STATUS {result.status}: {candidate.qid}", flush=True
                )
        except CanonicalReferenceError as exc:
            counters["reference_error"] += 1
            print(
                f"    ADMISSION REFERENCE ERROR (wrong-kind/nonexistent target): "
                f"{candidate.qid}: {exc}",
                flush=True,
            )
        except Exception as exc:
            counters["error"] += 1
            print(f"    ADMISSION ERROR: {candidate.qid}: {exc}", flush=True)

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

    registry = ContractRegistry.from_directory(ROOT / "specs")

    print("HullQ SLICE-0017 Wikidata Tier-0 Bootstrap — REPLAY", flush=True)
    print(f"  candidates={len(candidates)} auto_admit={len(auto_admit)}", flush=True)
    print(
        f"  expected: bundle_imported={expected_bundle_count} "
        f"admission_imported={expected_admission_count}",
        flush=True,
    )

    schema1 = "hullq_wdt0_run1_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
    schema2 = "hullq_wdt0_run2_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]

    # --- Pass 1: isolated schema — first-pass import + deep readback + idempotent reimport ---
    conn1 = psycopg.connect(db_url)
    try:
        with _isolated_schema(conn1, schema1):
            apply_migrations(conn1)
            pg_ver = _pg_version(conn1)

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
            for candidate in candidates:
                _import_bundle_exhaustive(conn1, candidate, bundle_counts, phase="first_pass")
                _import_admission_exhaustive(
                    conn1, candidate, registry, admission_counts, phase="first_pass"
                )
            import_elapsed = time.perf_counter() - t0
            print(f"  [schema1] bundles: {bundle_counts}", flush=True)
            print(f"  [schema1] admissions: {admission_counts}", flush=True)

            expected_counts_match = (
                bundle_counts["imported"] == expected_bundle_count
                and admission_counts["imported"] == expected_admission_count
            )
            if not expected_counts_match:
                print(
                    f"    EXPECTED-COUNT MISMATCH: bundle_imported={bundle_counts['imported']} "
                    f"(expected {expected_bundle_count}), admission_imported="
                    f"{admission_counts['imported']} (expected {expected_admission_count})",
                    flush=True,
                )

            # --- Exact canonical BoatModel ID-set equality ---
            with conn1.cursor() as cur:
                cur.execute("SELECT id FROM canonical_boat_models")
                actual_admitted_ids = {row[0] for row in cur.fetchall()}
            missing_ids = expected_admitted_ids - actual_admitted_ids
            extra_ids = actual_admitted_ids - expected_admitted_ids
            canonical_id_set_matches = not missing_ids and not extra_ids
            if not canonical_id_set_matches:
                print(
                    f"    CANONICAL BOAT MODEL ID SET MISMATCH: missing={sorted(missing_ids)} "
                    f"extra={sorted(extra_ids)}",
                    flush=True,
                )

            # --- No stray Brand/Organization/BoatDesign rows ---
            stray_row_counts: dict[str, int] = {}
            with conn1.cursor() as cur:
                for table in (
                    "canonical_brands",
                    "canonical_organizations",
                    "canonical_boat_designs",
                ):
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    stray_row_counts[table] = cur.fetchone()[0]
            no_stray_rows = all(count == 0 for count in stray_row_counts.values())
            if not no_stray_rows:
                print(
                    f"    UNEXPECTED BRAND/ORGANIZATION/BOATDESIGN ROWS: {stray_row_counts}",
                    flush=True,
                )

            # --- Deep readback verification ---
            readback_mismatches = 0
            for candidate in auto_admit:
                if not _readback_matches(conn1, candidate, "READBACK"):
                    readback_mismatches += 1
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
                    print(
                        f"    UNEXPECTED CANONICAL ROW FOR NON-ADMITTED: {candidate.qid}",
                        flush=True,
                    )

            # --- Exact re-import idempotency (same isolated schema) ---
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
                                f"    BUNDLE REIMPORT NOT IDEMPOTENT: {candidate.qid}: "
                                f"{result.status}",
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
                                f"    ADMISSION REIMPORT NOT IDEMPOTENT: {candidate.qid}: "
                                f"{result.status}",
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

    # --- Pass 2: second, independent isolated schema — full semantic graph equality ---
    conn2 = psycopg.connect(db_url)
    try:
        with _isolated_schema(conn2, schema2):
            apply_migrations(conn2)

            fresh_bundle_counts = {
                "imported": 0,
                "already_present": 0,
                "conflict": 0,
                "error": 0,
                "unexpected_status": 0,
            }
            fresh_admission_counts = {
                "imported": 0,
                "already_present": 0,
                "conflict": 0,
                "reference_error": 0,
                "error": 0,
                "unexpected_status": 0,
            }
            for candidate in candidates:
                _import_bundle_exhaustive(conn2, candidate, fresh_bundle_counts, phase="fresh")
                _import_admission_exhaustive(
                    conn2, candidate, registry, fresh_admission_counts, phase="fresh"
                )

            fresh_semantic_mismatches = 0
            for candidate in auto_admit:
                if not _readback_matches(conn2, candidate, "FRESH"):
                    fresh_semantic_mismatches += 1

            with conn2.cursor() as cur:
                cur.execute("SELECT id FROM canonical_boat_models")
                fresh_actual_ids = {row[0] for row in cur.fetchall()}
            fresh_id_set_matches = fresh_actual_ids == expected_admitted_ids
            if not fresh_id_set_matches:
                print(
                    f"    FRESH CANONICAL ID SET MISMATCH: missing="
                    f"{sorted(expected_admitted_ids - fresh_actual_ids)} extra="
                    f"{sorted(fresh_actual_ids - expected_admitted_ids)}",
                    flush=True,
                )

            # --- No stray Brand/Organization/BoatDesign rows (independent proof) ---
            fresh_stray_row_counts: dict[str, int] = {}
            with conn2.cursor() as cur:
                for table in (
                    "canonical_brands",
                    "canonical_organizations",
                    "canonical_boat_designs",
                ):
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    fresh_stray_row_counts[table] = cur.fetchone()[0]
            fresh_no_stray_rows = all(count == 0 for count in fresh_stray_row_counts.values())
            if not fresh_no_stray_rows:
                print(
                    f"    FRESH UNEXPECTED BRAND/ORGANIZATION/BOATDESIGN ROWS: "
                    f"{fresh_stray_row_counts}",
                    flush=True,
                )

            fresh_expected_counts_match = (
                fresh_bundle_counts["imported"] == expected_bundle_count
                and fresh_admission_counts["imported"] == expected_admission_count
            )
            print(f"  [schema2] bundles: {fresh_bundle_counts}", flush=True)
            print(f"  [schema2] admissions: {fresh_admission_counts}", flush=True)
            print(
                f"  fresh: semantic_mismatches={fresh_semantic_mismatches} "
                f"id_set_matches={fresh_id_set_matches} "
                f"no_stray_rows={fresh_no_stray_rows} "
                f"expected_counts_match={fresh_expected_counts_match}",
                flush=True,
            )
    finally:
        conn2.close()

    result_doc: dict[str, Any] = {
        "schema_version": "0017-replay-v3",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "postgresql_version": pg_ver,
        "manifest_candidates": len(candidates),
        "manifest_auto_admit": len(auto_admit),
        "expected": {
            "bundle_count": expected_bundle_count,
            "admission_count": expected_admission_count,
        },
        "first_pass": {
            "bundle": bundle_counts,
            "admission": admission_counts,
            "expected_counts_match": expected_counts_match,
            "wall_clock_seconds": round(import_elapsed, 4),
        },
        "readback": {
            "mismatches": readback_mismatches,
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
        "fresh_schema_rerun": {
            "bundle": fresh_bundle_counts,
            "admission": fresh_admission_counts,
            "semantic_mismatches": fresh_semantic_mismatches,
            "id_set_matches": fresh_id_set_matches,
            "no_stray_brand_organization_boatdesign_rows": fresh_no_stray_rows,
            "stray_row_counts": fresh_stray_row_counts,
            "expected_counts_match": fresh_expected_counts_match,
        },
    }
    result_doc["all_zero_tolerance_conditions_clear"] = (
        bundle_counts["already_present"] == 0
        and bundle_counts["conflict"] == 0
        and bundle_counts["error"] == 0
        and bundle_counts["unexpected_status"] == 0
        and admission_counts["already_present"] == 0
        and admission_counts["conflict"] == 0
        and admission_counts["reference_error"] == 0
        and admission_counts["error"] == 0
        and admission_counts["unexpected_status"] == 0
        and expected_counts_match
        and readback_mismatches == 0
        and unexpected_canonical == 0
        and canonical_id_set_matches
        and no_stray_rows
        and reimport_conflict == 0
        and reimport_error == 0
        and fresh_bundle_counts["already_present"] == 0
        and fresh_bundle_counts["conflict"] == 0
        and fresh_bundle_counts["error"] == 0
        and fresh_bundle_counts["unexpected_status"] == 0
        and fresh_admission_counts["already_present"] == 0
        and fresh_admission_counts["conflict"] == 0
        and fresh_admission_counts["reference_error"] == 0
        and fresh_admission_counts["error"] == 0
        and fresh_admission_counts["unexpected_status"] == 0
        and fresh_semantic_mismatches == 0
        and fresh_id_set_matches
        and fresh_no_stray_rows
        and fresh_expected_counts_match
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
    rb = result_doc["readback"]
    ri = result_doc["reimport"]
    fr = result_doc["fresh_schema_rerun"]
    lines = [
        "# HullQ SLICE-0017 Wikidata Tier-0 Bootstrap Replay Report",
        "",
        f"**Run timestamp:** {result_doc['run_timestamp']}  ",
        f"**PostgreSQL version:** {result_doc['postgresql_version']}  ",
        f"**Manifest candidates:** {result_doc['manifest_candidates']}  ",
        f"**Manifest auto_admit:** {result_doc['manifest_auto_admit']}  ",
        f"**Expected bundle/admission imports:** {exp['bundle_count']}/{exp['admission_count']}",
        "",
        "Both passes below run in their own newly-created, migrated-from-zero, "
        "isolated PostgreSQL schema, independent of any pre-existing rows a "
        "prior CI step may have left in the default/public schema.",
        "",
        "## PASS 1 — FIRST-PASS IMPORT (isolated schema)",
        "",
        f"- bundle: {fp['bundle']}",
        f"- admission: {fp['admission']}",
        f"- expected imported counts match exactly: {fp['expected_counts_match']}",
        f"- wall clock: {fp['wall_clock_seconds']}s",
        "",
        "## DEEP READBACK VERIFICATION (same isolated schema as pass 1)",
        "",
        f"- semantic mismatches (name/first_built/last_built/relationships/aliases/evidence-link): {rb['mismatches']}",
        f"- unexpected canonical rows for non-admitted candidates: {rb['unexpected_canonical_rows_for_non_admitted']}",
        f"- canonical BoatModel ID set matches exactly: {rb['canonical_id_set_matches']}",
        f"- zero stray Brand/Organization/BoatDesign rows: {rb['no_stray_brand_organization_boatdesign_rows']} ({rb['stray_row_counts']})",
        "",
        "## EXACT RE-REPLAY (IDEMPOTENCY, same isolated schema)",
        "",
        f"- already_imported/conflict/error: {ri['already_imported']}/{ri['conflict']}/{ri['error']}",
        f"- wall clock: {ri['wall_clock_seconds']}s",
        "",
        "## PASS 2 — INDEPENDENT FRESH-SCHEMA REPLAY (second isolated schema, full semantic graph equality)",
        "",
        f"- bundle: {fr['bundle']}",
        f"- admission: {fr['admission']}",
        f"- semantic mismatches: {fr['semantic_mismatches']}",
        f"- canonical ID set matches exactly: {fr['id_set_matches']}",
        f"- zero stray Brand/Organization/BoatDesign rows: {fr['no_stray_brand_organization_boatdesign_rows']} ({fr['stray_row_counts']})",
        f"- expected imported counts match exactly: {fr['expected_counts_match']}",
        "",
        f"## RESULT: all zero-tolerance conditions clear: **{result_doc['all_zero_tolerance_conditions_clear']}**",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Replay report written to: {report_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HullQ SLICE-0017 Wikidata Tier-0 bootstrap runner"
    )
    parser.add_argument(
        "--live", action="store_true", help="Run the one live discovery+acquisition run"
    )
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="Offline reclassification of the retained manifest (no network access)",
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
            manifest_path=Path(args.manifest),
            report_path=Path(args.report),
        )
    elif args.recompute:
        recompute_manifest_offline(manifest_path=Path(args.manifest), report_path=Path(args.report))
    else:
        db_url = _get_db_url(args.db_url)
        replay_manifest(
            db_url,
            manifest_path=Path(args.manifest),
            result_path=Path(args.result),
            report_path=Path(args.replay_report),
        )


if __name__ == "__main__":
    main()
