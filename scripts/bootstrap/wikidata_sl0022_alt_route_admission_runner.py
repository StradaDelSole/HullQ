"""SLICE-0022 retained alternative-route Tier-0 admission safety pilot runner.

Three independent modes. None perform any live network request — SLICE-0022
classifies only already-committed, immutable retained inputs (the accepted
SLICE-0017/0018 baseline manifests and the accepted SLICE-0021 retained
``sampled_candidates.json`` / ``discovery_probe.json``).

``--classify``
    Offline (no network access): loads and fail-closed fingerprints every
    immutable retained input, classifies the exact 57 retained SLICE-0021
    candidates using the accepted Tier-0 machinery plus the SLICE-0022 R3
    fail-closed rule, and writes the retained
    ``research/bootstrap/wikidata/sl0022-alt-route-admission/manifest.json``
    + ``REPORT.md``. If a manifest already exists at the target path, its
    retained crosswalk is loaded first so every already-mapped QID reuses its
    retained HullQ ID exactly (idempotent rerun contract, mirrors SLICE-0017/
    0018/0021).

``--verify``
    Fully offline (zero network access): reloads the already-retained
    manifest and recomputes EVERY structurally-derivable field from the
    manifest's own retained ``retained_crosswalk`` plus freshly (re-)loaded/
    fingerprinted immutable inputs — never from the manifest's own
    already-computed summary fields, so a tampered summary field cannot
    silently validate itself. This is what normal CI runs.

``--replay``
    Offline replay of the accepted SLICE-0017 baseline, the accepted
    SLICE-0018 delta, and the retained SLICE-0022 admission delta — in that
    order — against real PostgreSQL 18: combined import, deep semantic
    readback verification (including zero baseline drift for BOTH prior
    tiers), exact re-import (idempotency), and an independent fresh-schema
    rerun. Performs no network access. This is what the SLICE-0022
    db-integration CI step runs.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py --classify

    uv run python scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py --verify

    uv run python scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py --replay \\
        --db-url postgresql://user:pass@host:5432/db
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SL0022_DIR = ROOT / "research" / "bootstrap" / "wikidata" / "sl0022-alt-route-admission"
MANIFEST_PATH = SL0022_DIR / "manifest.json"
MANIFEST_SCHEMA_PATH = SL0022_DIR / "manifest_schema.json"
REPORT_PATH = SL0022_DIR / "REPORT.md"
REPLAY_RESULT_PATH = SL0022_DIR / "REPLAY-RESULT.json"
REPLAY_REPORT_PATH = SL0022_DIR / "REPLAY-REPORT.md"


def _validate_manifest_schema(manifest: dict[str, Any]) -> None:
    if not MANIFEST_SCHEMA_PATH.exists():
        return
    import jsonschema

    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=schema)
    print("SLICE-0022 manifest schema validation: PASS", flush=True)


# ---------------------------------------------------------------------------
# Offline classification (no network)
# ---------------------------------------------------------------------------


def run_classify(
    *, manifest_path: Path = MANIFEST_PATH, report_path: Path = REPORT_PATH
) -> dict[str, Any]:
    """Offline classification of the 57 retained SLICE-0021 candidates —
    zero network access.

    Fails closed (``ImmutableInputIntegrityError``) before any classification
    if any retained input has drifted from its accepted fingerprint/count.
    """
    from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (
        build_sl0022_manifest,
        classify_sl0022_candidates,
        load_and_fingerprint_immutable_inputs,
    )
    from hullq.bootstrap.wikidata_tier0 import load_crosswalk_from_manifest
    from hullq.bootstrap.wikidata_tier0_sl0018 import merge_crosswalks_fail_closed

    print(
        "HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot — CLASSIFY "
        "(offline, no network access)",
        flush=True,
    )

    inputs = load_and_fingerprint_immutable_inputs()
    print(
        f"  immutable inputs verified: baseline candidates={len(inputs.baseline.candidate_qids)} "
        f"auto_admit={len(inputs.baseline.auto_admit_qids)} "
        f"historical_crosswalk={len(inputs.baseline.crosswalk)} "
        f"retained SLICE-0021 candidates={len(inputs.retained_candidate_rows)}",
        flush=True,
    )

    historical_crosswalk = dict(inputs.baseline.crosswalk)
    acquired_at: str | None = None
    classification_recomputed_at: str | None = None
    now_ts = datetime.now(tz=UTC).isoformat()

    if manifest_path.exists():
        prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        prior_crosswalk = load_crosswalk_from_manifest(prior_manifest)
        historical_crosswalk = merge_crosswalks_fail_closed(
            historical_crosswalk,
            prior_crosswalk,
            context="baseline crosswalk merge with prior retained SLICE-0022 manifest",
        )
        acquired_at = prior_manifest.get("acquired_at")
        classification_recomputed_at = now_ts
        print(
            f"  loaded {len(prior_crosswalk)} retained QID->HullQ-ID mapping(s) from existing "
            f"SLICE-0022 manifest at {manifest_path}; merged historical crosswalk has "
            f"{len(historical_crosswalk)} entries",
            flush=True,
        )
    else:
        acquired_at = now_ts

    candidates, within_57_clusters, baseline_collisions = classify_sl0022_candidates(
        list(inputs.retained_candidate_rows),
        retrieved_at=now_ts,
        baseline=inputs.baseline,
        existing_crosswalk=historical_crosswalk,
    )

    manifest = build_sl0022_manifest(
        candidates,
        generated_at=now_ts,
        baseline=inputs.baseline,
        within_57_clusters=within_57_clusters,
        baseline_collisions=baseline_collisions,
        inputs=inputs,
        retrieval_count=0,
        extracted_record_count=len(candidates),
        acquired_at=acquired_at,
        classification_recomputed_at=classification_recomputed_at,
        historical_crosswalk=historical_crosswalk,
    )
    _validate_manifest_schema(manifest)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written to: {manifest_path}", flush=True)
    print(f"  counts: {manifest['counts']}", flush=True)

    _write_report(manifest, report_path)
    return manifest


# ---------------------------------------------------------------------------
# Offline verification (no network) — what CI runs
# ---------------------------------------------------------------------------


def run_verify(*, manifest_path: Path = MANIFEST_PATH) -> None:
    from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (
        load_and_fingerprint_immutable_inputs,
        verify_sl0022_manifest_self_consistency,
    )

    print(
        "HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot — OFFLINE "
        "VERIFY (no network access)",
        flush=True,
    )

    inputs = load_and_fingerprint_immutable_inputs()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = verify_sl0022_manifest_self_consistency(manifest, inputs=inputs)

    if mismatches:
        print("\nOFFLINE VERIFY FAILED:", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained manifest.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(
    manifest: dict[str, Any],
    report_path: Path,
    *,
    replay_result: dict[str, Any] | None = None,
) -> None:
    counts = manifest["counts"]
    immutable_inputs = manifest["immutable_inputs"]
    universe = manifest["candidate_universe"]
    collisions = manifest.get("collisions", {"baseline": [], "within_57": []})
    lines = [
        "# HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot Report",
        "",
        f"**Manifest last written (generated_at):** {manifest['generated_at']}  ",
        f"**First classification (acquired_at):** {manifest['acquired_at']}  ",
        f"**Last offline reclassification (classification_recomputed_at):** {manifest['classification_recomputed_at']}  ",
        f"**Source:** {manifest['source_id']}",
        "",
        "## ZERO LIVE NETWORK ACQUISITION",
        "",
        "This pilot performs no WDQS/wbgetentities/manufacturer-archive/search-engine request. "
        "Every fact below is classified purely from already-committed, immutable retained inputs.",
        "",
        "## IMMUTABLE RETAINED INPUTS (hard-asserted before classification)",
        "",
        f"- SLICE-0017 manifest: `{immutable_inputs['sl0017_manifest']['path']}` "
        f"sha256=`{immutable_inputs['sl0017_manifest']['sha256']}`",
        f"- SLICE-0018 manifest: `{immutable_inputs['sl0018_manifest']['path']}` "
        f"sha256=`{immutable_inputs['sl0018_manifest']['sha256']}`",
        f"- SLICE-0021 sampled_candidates.json: `{immutable_inputs['sl0021_sampled_candidates']['path']}` "
        f"git_blob_sha1=`{immutable_inputs['sl0021_sampled_candidates']['git_blob_sha1']}`",
        f"- SLICE-0021 discovery_probe.json: `{immutable_inputs['sl0021_discovery_probe']['path']}` "
        f"git_blob_sha1=`{immutable_inputs['sl0021_discovery_probe']['git_blob_sha1']}`",
        f"- SLICE-0021 implementation head (informational): `{immutable_inputs['sl0021_implementation_head']}`",
        f"- Accepted retained direct-discovery universe: **{immutable_inputs['retained_direct_discovery_count']}** (must equal 1,829)",
        f"- Accepted AUTO_ADMIT universe: **{immutable_inputs['accepted_auto_admit_count']}** (must equal 1,770)",
        f"- Accepted historical crosswalk: **{immutable_inputs['accepted_historical_crosswalk_count']}** (must equal 1,772)",
        "",
        "## CANDIDATE UNIVERSE (exactly the 57 retained SLICE-0021 incremental candidates)",
        "",
        f"- total: **{universe['total']}** (must equal 57)",
        f"- R1: **{universe['r1_count']}** (must equal 53)",
        f"- R2: **{universe['r2_count']}** (must equal 0)",
        f"- R3: **{universe['r3_count']}** (must equal 4)",
        "",
        "## DECISION TOTALS",
        "",
        f"- AUTO_ADMIT: **{counts['auto_admit']}** (all R1: **{counts['auto_admit_r1']}**; R3: "
        f"**{counts['auto_admit_r3']}**, must always be 0)",
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
        f"## COLLISIONS AGAINST THE ACCEPTED 1,829-CANDIDATE BASELINE ({counts['baseline_collision_count']})",
        "",
    ]
    if collisions["baseline"]:
        for bc in collisions["baseline"]:
            lines.append(
                f"- `{bc['candidate_qid']}` collides with baseline `{bc['baseline_qids']}` — "
                f"shared key(s): `{bc['shared_keys']}`"
            )
    else:
        lines.append("- none")
    lines += [
        "",
        f"## WITHIN-57 COLLISION CLUSTERS ({counts['within_57_collision_cluster_count']})",
        "",
    ]
    if collisions["within_57"]:
        for cluster in collisions["within_57"]:
            lines.append(f"- `{cluster['qids']}` — shared key(s): `{cluster['shared_keys']}`")
    else:
        lines.append("- none")
    lines += [
        "",
        "## HISTORICAL CROSSWALK",
        "",
        f"- Historical crosswalk entries BEFORE this run: **{counts['historical_crosswalk_count_before']}**",
        f"- Retained crosswalk entries AFTER this run: **{counts['retained_crosswalk_count']}**",
        f"- Newly minted HullQ-ID count (this generation pass): **{counts['newly_minted_id_count']}**",
        f"- Reused historical HullQ-ID count (this generation pass): **{counts['reused_historical_id_count']}**",
        "",
        "## CANONICAL ADMISSION EXPECTATION",
        "",
        f"- Accepted baseline canonical BoatModel count: **{counts['accepted_baseline_canonical_boat_model_count']}**",
        f"- SLICE-0022 AUTO_ADMIT count: **{counts['auto_admit']}**",
        f"- Expected combined canonical BoatModel count after replay: **{counts['combined_canonical_boat_model_count_expected']}**",
        "",
        "## R3 FAIL-CLOSED RULE",
        "",
        "Every structurally usable R3 (misclassified_sailboat_class_description) candidate is "
        "`REVIEW_REQUIRED` with reason `r3_repair_signal_requires_review`, regardless of its own "
        "collision status. No R3 candidate may ever be `AUTO_ADMIT` in SLICE-0022.",
        "",
        "## INTERPRETATION",
        "",
        "This is a bounded admission-safety pilot over retained SLICE-0021 evidence, not "
        "production adoption of R1/R3 Wikidata discovery. The production Wikidata adapter's "
        "default discovery query is unchanged, and no R1/R3 acquisition is scheduled.",
        "",
    ]
    if replay_result is not None:
        fp = replay_result["first_pass"]
        fr = replay_result["fresh_schema_rerun"]
        lines += [
            "## POSTGRESQL REPLAY EVIDENCE — LOCAL (this implementation session)",
            "",
            (
                "Evidence below was measured locally by running "
                "`scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py --replay` "
                "against a real PostgreSQL 18 instance during implementation. Remote GitHub "
                "Actions CI independently re-runs the same `--replay` step at the exact pushed "
                "head and is the authoritative external verification."
            ),
            "",
            f"- PostgreSQL version: `{replay_result['postgresql_version']}`",
            f"- Expected combined bundle / admission imports: "
            f"{replay_result['expected']['combined_bundle_count']} / "
            f"{replay_result['expected']['combined_admission_count']}",
            "",
            "### First-pass combined import (isolated schema)",
            "",
            f"- bundle: {fp['bundle']}",
            f"- admission: {fp['admission']}",
            f"- expected combined imported counts match exactly: {fp['expected_counts_match']}",
            f"- prior-baseline (0017+0018) verified before 0022 applied: {fp['prior_baseline_verified_before_sl0022']}",
            f"- combined readback mismatches: {fp['readback']['mismatches']} "
            f"(prior-baseline drift: {fp['readback']['prior_baseline_drift_mismatches']})",
            f"- unexpected canonical rows for non-admitted candidates: "
            f"{fp['readback']['unexpected_canonical_rows_for_non_admitted']}",
            f"- combined canonical BoatModel ID set matches exactly: "
            f"{fp['readback']['canonical_id_set_matches']}",
            f"- zero stray Brand/Organization/BoatDesign rows: "
            f"{fp['readback']['no_stray_brand_organization_boatdesign_rows']} "
            f"({fp['readback']['stray_row_counts']})",
            f"- exact re-import (idempotency): already_imported={fp['reimport']['already_imported']} "
            f"conflict={fp['reimport']['conflict']} error={fp['reimport']['error']}",
            "",
            "### Independent fresh-schema replay (second isolated schema)",
            "",
            f"- bundle: {fr['bundle']}",
            f"- admission: {fr['admission']}",
            f"- semantic mismatches: {fr['readback']['mismatches']} "
            f"(prior-baseline drift: {fr['readback']['prior_baseline_drift_mismatches']})",
            f"- combined canonical ID set matches exactly: {fr['readback']['canonical_id_set_matches']}",
            f"- zero stray Brand/Organization/BoatDesign rows: "
            f"{fr['readback']['no_stray_brand_organization_boatdesign_rows']} "
            f"({fr['readback']['stray_row_counts']})",
            "",
            f"### RESULT: all zero-tolerance conditions clear (local): "
            f"**{replay_result['all_zero_tolerance_conditions_clear']}**",
            "",
        ]
    else:
        lines += [
            "## POSTGRESQL REPLAY EVIDENCE",
            "",
            "PENDING until replayed against real PostgreSQL 18 (db-integration CI or a local "
            "`--replay` run).",
            "",
        ]
    lines += [
        "## SCOPE CONFIRMATION",
        "",
        "- No live Wikidata (or other) network request was made.",
        "- The accepted SLICE-0017/0018/0021 retained artifacts were read-only inputs and remain byte-unchanged.",
        "- The production Wikidata adapter's default discovery query was not changed.",
        "- No accepted SLICE-0017/0018 review/non-admitted candidate was resolved as a side effect.",
        "- No Brand/Organization/BoatDesign row was created.",
        "- SLICE-0023 was not created or started.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}", flush=True)


# ---------------------------------------------------------------------------
# Replay (offline, no network) — SLICE-0017 baseline, SLICE-0018 delta,
# SLICE-0022 delta, in that order, against real PostgreSQL
# ---------------------------------------------------------------------------


def replay_manifest(
    db_url: str,
    *,
    sl0017_manifest_path: Path | None = None,
    sl0018_manifest_path: Path | None = None,
    manifest_path: Path = MANIFEST_PATH,
    result_path: Path = REPLAY_RESULT_PATH,
    report_path: Path = REPLAY_REPORT_PATH,
) -> dict[str, Any]:
    """Offline replay: accepted SLICE-0017 baseline, accepted SLICE-0018
    delta, retained SLICE-0022 delta — in that order — against real
    PostgreSQL 18, in two independent isolated schemas (first-pass +
    idempotent-reimport, then an independent fresh-schema rerun).

    Performs no network access.
    """
    import psycopg

    from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (
        SL0017_MANIFEST_PATH,
        SL0018_MANIFEST_PATH,
        sl0022_candidate_from_manifest_dict,
    )
    from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (
        build_bundle as build_bundle_sl0022,
    )
    from hullq.bootstrap.wikidata_tier0 import (
        BootstrapDecision,
        build_admission,
        candidate_from_manifest_dict,
    )
    from hullq.bootstrap.wikidata_tier0 import build_bundle as build_bundle_0017
    from hullq.bootstrap.wikidata_tier0_sl0018 import build_bundle as build_bundle_sl0018
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

    sl0017_manifest_path = sl0017_manifest_path or SL0017_MANIFEST_PATH
    sl0018_manifest_path = sl0018_manifest_path or SL0018_MANIFEST_PATH

    sl0017_manifest = json.loads(sl0017_manifest_path.read_text(encoding="utf-8"))
    sl0017_candidates = [candidate_from_manifest_dict(row) for row in sl0017_manifest["candidates"]]
    sl0018_manifest = json.loads(sl0018_manifest_path.read_text(encoding="utf-8"))
    sl0018_candidates = [candidate_from_manifest_dict(row) for row in sl0018_manifest["candidates"]]
    sl0022_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sl0022_candidates = [
        sl0022_candidate_from_manifest_dict(row) for row in sl0022_manifest["candidates"]
    ]

    prior_baseline_candidates = [(c, build_bundle_0017) for c in sl0017_candidates] + [
        (c, build_bundle_sl0018) for c in sl0018_candidates
    ]
    prior_baseline_auto_admit = [
        c for c, _ in prior_baseline_candidates if c.decision == BootstrapDecision.AUTO_ADMIT
    ]
    expected_prior_baseline_admitted_ids = {c.hullq_id for c in prior_baseline_auto_admit}
    expected_prior_baseline_bundle_count = sum(
        1 for c, _ in prior_baseline_candidates if c.preferred_label
    )
    expected_prior_baseline_admission_count = len(prior_baseline_auto_admit)

    sl0022_auto_admit = [
        c for c in sl0022_candidates if c.base.decision == BootstrapDecision.AUTO_ADMIT
    ]
    expected_sl0022_admitted_ids = {c.base.hullq_id for c in sl0022_auto_admit}
    expected_sl0022_bundle_count = sum(1 for c in sl0022_candidates if c.base.preferred_label)
    expected_sl0022_admission_count = len(sl0022_auto_admit)

    expected_combined_admitted_ids = (
        expected_prior_baseline_admitted_ids | expected_sl0022_admitted_ids
    )
    expected_combined_bundle_count = (
        expected_prior_baseline_bundle_count + expected_sl0022_bundle_count
    )
    expected_combined_admission_count = (
        expected_prior_baseline_admission_count + expected_sl0022_admission_count
    )

    def _expected_aliases(candidate: Any) -> set[tuple[str, str, str]]:
        admission = build_admission(candidate)
        if admission is None:
            return set()
        return {(a["id"], a["alias_class"], a["name"]) for a in admission.boat_models[0]["aliases"]}

    def _actual_boat_model_aliases(fetched: dict[str, Any]) -> set[tuple[str, str, str]]:
        return {(a["id"], a["alias_class"], a["name"]) for a in fetched.get("aliases", [])}

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
                print(
                    f"    BUNDLE UNEXPECTED ALREADY_IMPORTED ({phase}): {candidate.qid}", flush=True
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
            print(f"    ADMISSION REFERENCE ERROR ({phase}): {candidate.qid}: {exc}", flush=True)
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
        for candidate, bundle_builder in prior_baseline_candidates:
            _import_bundle_exhaustive(
                conn, candidate, bundle_builder, bundle_counts, phase="prior_baseline_first_pass"
            )
            _import_admission_exhaustive(
                conn, candidate, registry, admission_counts, phase="prior_baseline_first_pass"
            )
        prior_baseline_elapsed = time.perf_counter() - t0
        print(
            f"  [{label}] prior baseline (0017+0018) import: bundles={bundle_counts} "
            f"admissions={admission_counts}",
            flush=True,
        )

        prior_baseline_counts_match = (
            bundle_counts["imported"] == expected_prior_baseline_bundle_count
            and admission_counts["imported"] == expected_prior_baseline_admission_count
        )
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM canonical_boat_models")
            prior_baseline_actual_ids = {row[0] for row in cur.fetchall()}
        prior_baseline_id_set_matches = (
            prior_baseline_actual_ids == expected_prior_baseline_admitted_ids
        )
        prior_baseline_readback_mismatches = 0
        for candidate in prior_baseline_auto_admit:
            if not _readback_matches(conn, candidate, f"{label} PRIOR-BASELINE-READBACK"):
                prior_baseline_readback_mismatches += 1
        print(
            f"  [{label}] prior baseline (0017+0018) verified before 0022: "
            f"counts_match={prior_baseline_counts_match} id_set_matches={prior_baseline_id_set_matches} "
            f"readback_mismatches={prior_baseline_readback_mismatches}",
            flush=True,
        )

        t0 = time.perf_counter()
        for candidate in sl0022_candidates:
            _import_bundle_exhaustive(
                conn, candidate, build_bundle_sl0022, bundle_counts, phase="sl0022_first_pass"
            )
            _import_admission_exhaustive(
                conn, candidate.base, registry, admission_counts, phase="sl0022_first_pass"
            )
        sl0022_elapsed = time.perf_counter() - t0
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
                f"    CANONICAL BOAT MODEL ID SET MISMATCH [{label}]: missing={sorted(missing_ids)} "
                f"extra={sorted(extra_ids)}",
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

        prior_baseline_drift_mismatches = 0
        for candidate in prior_baseline_auto_admit:
            if not _readback_matches(conn, candidate, f"{label} PRIOR-BASELINE-DRIFT-CHECK"):
                prior_baseline_drift_mismatches += 1

        sl0022_readback_mismatches = 0
        for candidate in sl0022_auto_admit:
            if not _readback_matches(conn, candidate.base, f"{label} SL0022-READBACK"):
                sl0022_readback_mismatches += 1

        readback_mismatches = prior_baseline_drift_mismatches + sl0022_readback_mismatches
        print(f"  [{label}] readback_mismatches (combined)={readback_mismatches}", flush=True)

        unexpected_canonical = 0
        for candidate, _ in prior_baseline_candidates:
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
        for candidate in sl0022_candidates:
            if candidate.base.decision == BootstrapDecision.AUTO_ADMIT:
                continue
            if (
                candidate.base.hullq_id is not None
                and fetch_boat_model(conn, candidate.base.hullq_id) is not None
            ):
                unexpected_canonical += 1
                print(
                    f"    UNEXPECTED CANONICAL ROW FOR NON-ADMITTED [{label}]: {candidate.base.qid}",
                    flush=True,
                )

        reimport_already = reimport_conflict = reimport_error = 0
        t0 = time.perf_counter()
        for candidate, bundle_builder in prior_baseline_candidates:
            bundle = bundle_builder(candidate)
            if bundle is not None:
                try:
                    result = import_research_evidence_bundle(conn, bundle)
                    if result.status != ImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    BUNDLE REIMPORT NOT IDEMPOTENT [{label}]: {candidate.qid}: {result.status}",
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
                            f"    ADMISSION REIMPORT NOT IDEMPOTENT [{label}]: {candidate.qid}: {result.status}",
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
        for candidate in sl0022_candidates:
            bundle = build_bundle_sl0022(candidate)
            if bundle is not None:
                try:
                    result = import_research_evidence_bundle(conn, bundle)
                    if result.status != ImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    BUNDLE REIMPORT NOT IDEMPOTENT [{label}]: {candidate.base.qid}: "
                            f"{result.status}",
                            flush=True,
                        )
                    else:
                        reimport_already += 1
                except Exception as exc:
                    reimport_error += 1
                    print(
                        f"    BUNDLE REIMPORT ERROR [{label}]: {candidate.base.qid}: {exc}",
                        flush=True,
                    )
            admission = build_admission(candidate.base)
            if admission is not None:
                try:
                    result = import_canonical_identity_admission(conn, admission, registry)
                    if result.status != CanonicalImportStatus.ALREADY_IMPORTED:
                        reimport_conflict += 1
                        print(
                            f"    ADMISSION REIMPORT NOT IDEMPOTENT [{label}]: {candidate.base.qid}: "
                            f"{result.status}",
                            flush=True,
                        )
                    else:
                        reimport_already += 1
                except Exception as exc:
                    reimport_error += 1
                    print(
                        f"    ADMISSION REIMPORT ERROR [{label}]: {candidate.base.qid}: {exc}",
                        flush=True,
                    )
        reimport_elapsed = time.perf_counter() - t0
        print(
            f"  [{label}] reimport: already_imported={reimport_already} conflict={reimport_conflict} "
            f"error={reimport_error}",
            flush=True,
        )

        return {
            "bundle": bundle_counts,
            "admission": admission_counts,
            "expected_counts_match": expected_counts_match,
            "prior_baseline_verified_before_sl0022": {
                "counts_match": prior_baseline_counts_match,
                "id_set_matches": prior_baseline_id_set_matches,
                "readback_mismatches": prior_baseline_readback_mismatches,
            },
            "readback": {
                "mismatches": readback_mismatches,
                "prior_baseline_drift_mismatches": prior_baseline_drift_mismatches,
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
            "wall_clock_seconds": round(prior_baseline_elapsed + sl0022_elapsed, 4),
        }

    registry = ContractRegistry.from_directory(ROOT / "specs")

    print(
        "HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot — REPLAY",
        flush=True,
    )
    print(
        f"  prior_baseline_candidates={len(prior_baseline_candidates)} "
        f"prior_baseline_auto_admit={len(prior_baseline_auto_admit)} "
        f"sl0022_candidates={len(sl0022_candidates)} sl0022_auto_admit={len(sl0022_auto_admit)}",
        flush=True,
    )
    print(
        f"  expected combined: bundle_imported={expected_combined_bundle_count} "
        f"admission_imported={expected_combined_admission_count}",
        flush=True,
    )

    schema1 = "hullq_wdt0_sl0022_run1_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]
    schema2 = "hullq_wdt0_sl0022_run2_" + hashlib.sha1(db_url.encode()).hexdigest()[:12]

    @contextlib.contextmanager
    def _isolated_schema(conn: Any, schema_name: str) -> Iterator[None]:
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
        "schema_version": "0022-replay-v1",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "postgresql_version": pg_ver,
        "prior_baseline_candidates": len(prior_baseline_candidates),
        "prior_baseline_auto_admit": len(prior_baseline_auto_admit),
        "sl0022_candidates": len(sl0022_candidates),
        "sl0022_auto_admit": len(sl0022_auto_admit),
        "expected": {
            "combined_bundle_count": expected_combined_bundle_count,
            "combined_admission_count": expected_combined_admission_count,
        },
        "first_pass": pass1,
        "fresh_schema_rerun": pass2,
    }

    def _pass_clear(p: dict[str, Any]) -> bool:
        return bool(
            p["bundle"]["already_present"] == 0
            and p["bundle"]["conflict"] == 0
            and p["bundle"]["error"] == 0
            and p["bundle"]["unexpected_status"] == 0
            and p["admission"]["already_present"] == 0
            and p["admission"]["conflict"] == 0
            and p["admission"]["reference_error"] == 0
            and p["admission"]["error"] == 0
            and p["admission"]["unexpected_status"] == 0
            and p["expected_counts_match"]
            and p["prior_baseline_verified_before_sl0022"]["counts_match"]
            and p["prior_baseline_verified_before_sl0022"]["id_set_matches"]
            and p["prior_baseline_verified_before_sl0022"]["readback_mismatches"] == 0
            and p["readback"]["mismatches"] == 0
            and p["readback"]["prior_baseline_drift_mismatches"] == 0
            and p["readback"]["unexpected_canonical_rows_for_non_admitted"] == 0
            and p["readback"]["canonical_id_set_matches"]
            and p["readback"]["no_stray_brand_organization_boatdesign_rows"]
            and p["reimport"]["conflict"] == 0
            and p["reimport"]["error"] == 0
        )

    result_doc["all_zero_tolerance_conditions_clear"] = _pass_clear(pass1) and _pass_clear(pass2)

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
        "# HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot Replay Report",
        "",
        f"**Run timestamp:** {result_doc['run_timestamp']}  ",
        f"**PostgreSQL version:** {result_doc['postgresql_version']}  ",
        f"**Prior baseline (0017+0018) candidates/auto_admit:** {result_doc['prior_baseline_candidates']}/{result_doc['prior_baseline_auto_admit']}  ",
        f"**SLICE-0022 candidates/auto_admit:** {result_doc['sl0022_candidates']}/{result_doc['sl0022_auto_admit']}  ",
        f"**Expected combined bundle/admission imports:** {exp['combined_bundle_count']}/{exp['combined_admission_count']}",
        "",
        "Both passes below import the accepted SLICE-0017 baseline then the accepted SLICE-0018 "
        "delta first, verify that combined prior baseline, then import the retained SLICE-0022 "
        "delta second, in their own newly-created, migrated-from-zero, isolated PostgreSQL schema.",
        "",
        "## PASS 1 — FIRST-PASS COMBINED IMPORT (isolated schema)",
        "",
        f"- bundle (combined): {fp['bundle']}",
        f"- admission (combined): {fp['admission']}",
        f"- expected combined imported counts match exactly: {fp['expected_counts_match']}",
        f"- prior baseline (0017+0018) verified before 0022 applied: {fp['prior_baseline_verified_before_sl0022']}",
        f"- wall clock: {fp['wall_clock_seconds']}s",
        "",
        "## DEEP READBACK VERIFICATION (same isolated schema as pass 1)",
        "",
        f"- semantic mismatches (prior baseline + 0022): {fp['readback']['mismatches']}",
        f"- prior-baseline drift mismatches: {fp['readback']['prior_baseline_drift_mismatches']}",
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
        f"- prior baseline verified before 0022 applied: {fr['prior_baseline_verified_before_sl0022']}",
        f"- semantic mismatches: {fr['readback']['mismatches']}",
        f"- prior-baseline drift mismatches: {fr['readback']['prior_baseline_drift_mismatches']}",
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


def write_report_with_replay_evidence(
    *,
    manifest_path: Path = MANIFEST_PATH,
    replay_result_path: Path = REPLAY_RESULT_PATH,
    report_path: Path = REPORT_PATH,
) -> None:
    """Regenerate the checked-in human-readable REPORT.md from the
    already-retained manifest plus an already-produced offline PostgreSQL
    replay result, with zero network/PostgreSQL access performed by this
    function itself.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    replay_result = json.loads(replay_result_path.read_text(encoding="utf-8"))
    _write_report(manifest, report_path, replay_result=replay_result)


def _get_db_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    import os

    for var in ("HULLQ_TEST_DATABASE_URL", "HULLQ_DATABASE_URL"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    raise SystemExit("No database URL supplied. Pass --db-url or set HULLQ_TEST_DATABASE_URL.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HullQ SLICE-0022 retained alternative-route Tier-0 admission safety pilot runner"
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Offline classification of the 57 retained SLICE-0021 candidates (no network access)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Offline recompute/validation of the retained manifest (no network access)",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay accepted SLICE-0017+0018 baseline then retained SLICE-0022 delta against PostgreSQL",
    )
    parser.add_argument(
        "--regenerate-report",
        action="store_true",
        help="Offline: regenerate REPORT.md from the retained manifest plus an already-produced "
        "--replay result, with no network/PostgreSQL access performed by this step itself",
    )
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="SLICE-0022 manifest path")
    parser.add_argument("--report", default=str(REPORT_PATH), help="Human-readable report path")
    parser.add_argument("--db-url", default=None, help="PostgreSQL connection URL (replay mode)")
    parser.add_argument("--result", default=str(REPLAY_RESULT_PATH), help="Replay result JSON path")
    parser.add_argument(
        "--replay-report", default=str(REPLAY_REPORT_PATH), help="Replay report Markdown path"
    )
    parser.add_argument(
        "--replay-result",
        default=str(REPLAY_RESULT_PATH),
        help="Already-produced replay result JSON path to embed (--regenerate-report mode)",
    )
    args = parser.parse_args()

    modes_selected = sum([args.classify, args.verify, args.replay, args.regenerate_report])
    if modes_selected != 1:
        raise SystemExit(
            "Specify exactly one of --classify, --verify, --replay or --regenerate-report"
        )

    if args.classify:
        run_classify(manifest_path=Path(args.manifest), report_path=Path(args.report))
    elif args.verify:
        run_verify(manifest_path=Path(args.manifest))
    elif args.replay:
        db_url = _get_db_url(args.db_url)
        replay_manifest(
            db_url,
            manifest_path=Path(args.manifest),
            result_path=Path(args.result),
            report_path=Path(args.replay_report),
        )
    else:
        write_report_with_replay_evidence(
            manifest_path=Path(args.manifest),
            replay_result_path=Path(args.replay_result),
            report_path=Path(args.report),
        )


if __name__ == "__main__":
    main()
