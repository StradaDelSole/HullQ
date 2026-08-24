"""SLICE-0021 alternative Wikidata sailboat-class discovery-semantics pilot runner.

Two independent modes:

``--live``
    Perform the one bounded live Wikidata acquisition run: rights-gated
    dispatch of the four fixed R0-R3 routes (docs/slices/SLICE-0021-*.md),
    current-R0 drift measurement against the retained 1,829-QID universe,
    alternative-route incremental yield against CURRENT R0, cross-route
    overlap, a deterministic hard-capped entity-detail sample, exact-only
    identity-signal classification against the accepted 1,770 AUTO_ADMIT
    universe, and evidence-derived route dispositions. Writes
    ``discovery_probe.json`` + ``sampled_candidates.json`` + ``REPORT.md``
    under ``research/bootstrap/wikidata/sl0021-alt-discovery/``. Requires
    network access and is NOT part of normal CI.

``--verify``
    Fully offline (zero network access): reloads the already-retained
    ``discovery_probe.json`` + ``sampled_candidates.json``, recomputes every
    derived measurement (drift, incremental yield, cross-route overlap,
    sample selection, identity-signal classification, route dispositions)
    purely from the retained raw QID/entity-detail facts, and fails loudly on
    any mismatch against the committed documents. This is what normal CI runs
    to prove the retained result is offline-reproducible.

Usage::

    uv run python scripts/bootstrap/wikidata_sl0021_alt_discovery_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)"

    uv run python scripts/bootstrap/wikidata_sl0021_alt_discovery_runner.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SL0021_DIR = ROOT / "research" / "bootstrap" / "wikidata" / "sl0021-alt-discovery"
DISCOVERY_PROBE_PATH = SL0021_DIR / "discovery_probe.json"
SAMPLED_CANDIDATES_PATH = SL0021_DIR / "sampled_candidates.json"
DISCOVERY_PROBE_SCHEMA_PATH = SL0021_DIR / "discovery_probe_schema.json"
SAMPLED_CANDIDATES_SCHEMA_PATH = SL0021_DIR / "sampled_candidates_schema.json"
REPORT_PATH = SL0021_DIR / "REPORT.md"

SOURCE_PATH = ROOT / "fixtures" / "sources" / "wikidata_source.json"

_ROUTE_KEY_BY_ID = {
    "current_direct_control": "R0",
    "sailboat_class_closure": "R1",
    "legacy_sailboat_class_closure": "R2",
    "misclassified_sailboat_class_description": "R3",
}


def _validate_schema(instance: dict[str, Any], schema_path: Path, *, label: str) -> None:
    if not schema_path.exists():
        return
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)
    print(f"{label} schema validation: PASS", flush=True)


# ---------------------------------------------------------------------------
# Live acquisition
# ---------------------------------------------------------------------------


def run_live(*, user_agent: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from hullq.bootstrap.wikidata_sl0021_alt_discovery import (
        R3,
        ROUTE_ALT_IDS,
        ROUTES,
        build_accepted_label_index,
        build_discovery_probe_document,
        build_route_record,
        build_sampled_candidates_document,
        classify_identity_signal,
        compute_cross_route_overlap,
        compute_incremental_yield,
        compute_r0_drift,
        determine_route_disposition,
        load_and_fingerprint_immutable_inputs,
        select_entity_detail_sample,
    )
    from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use
    from hullq.sources.wikidata import WIKIDATA_SOURCE_ID, WikidataAdapter, WikidataAdapterConfig

    print("HullQ SLICE-0021 Wikidata Alternative Discovery-Semantics Pilot — LIVE RUN", flush=True)

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    # Rights/access gate MUST pass before the first network request, or the
    # run performs zero network requests (controlling slice "Rights/access
    # gate").
    automated_decision = check_source_use(source, SourceUse.AUTOMATED_INGESTION)
    bulk_decision = check_source_use(source, SourceUse.BULK_BOOTSTRAP)
    rights_gate = {
        "automated_ingestion": str(automated_decision.outcome),
        "bulk_bootstrap": str(bulk_decision.outcome),
    }
    print(f"  rights_gate={rights_gate}", flush=True)
    if automated_decision.outcome != DecisionOutcome.ALLOWED:
        raise SystemExit(
            f"SLICE-0021 refusing before any network request: automated_ingestion gate "
            f"outcome={automated_decision.outcome!s}, reasons={sorted(str(r) for r in automated_decision.reasons)}"
        )
    if bulk_decision.outcome != DecisionOutcome.ALLOWED:
        raise SystemExit(
            f"SLICE-0021 refusing before any network request: bulk_bootstrap gate "
            f"outcome={bulk_decision.outcome!s}, reasons={sorted(str(r) for r in bulk_decision.reasons)}"
        )

    # Fails closed (ImmutableInputIntegrityError) before any network request
    # if either retained SLICE-0017/0018 input has drifted from its accepted
    # fingerprint/counts.
    accepted_universe = load_and_fingerprint_immutable_inputs()
    print(
        f"  immutable inputs verified: retained_direct_discovery_count="
        f"{len(accepted_universe.retained_direct_discovery_qids)} "
        f"accepted_auto_admit_count={len(accepted_universe.accepted_auto_admit_identities)}",
        flush=True,
    )

    config = WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=120.0)

    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)

        route_records: dict[str, dict[str, Any]] = {}
        route_qids: dict[str, list[str]] = {}
        for route in ROUTES:
            key = _ROUTE_KEY_BY_ID[route.route_id]
            requests_before = adapter.usage_metrics.retrieval_count
            acquired_at = datetime.now(tz=UTC).isoformat()
            print(f"\nDispatching route {key} ({route.route_id})...", flush=True)
            if route is R3:
                pairs = adapter.run_alt_discovery_item_desc_query(route.query_text)
                qids = [qid for qid, _desc in pairs]
                item_descriptions = dict(pairs)
            else:
                qids = adapter.run_alt_discovery_item_query(route.query_text)
                item_descriptions = None
            requests_after = adapter.usage_metrics.retrieval_count
            print(f"  result_count={len(qids)}", flush=True)
            route_records[key] = build_route_record(
                route,
                qids,
                acquired_at=acquired_at,
                http_request_count=requests_after - requests_before,
                item_descriptions=item_descriptions,
            )
            route_qids[key] = qids

        r0_qids = route_qids["R0"]
        drift = compute_r0_drift(accepted_universe.retained_direct_discovery_qids, r0_qids)
        print(
            f"\nR0 drift: current={drift.current_direct_count} "
            f"still_present={drift.retained_direct_still_present_count} "
            f"absent_now={drift.retained_direct_absent_now_count} "
            f"new_since={drift.new_current_direct_since_sl0018_count}",
            flush=True,
        )

        incremental_by_route = {
            rid: compute_incremental_yield(route_qids[rid], r0_qids) for rid in ROUTE_ALT_IDS
        }
        for rid in ROUTE_ALT_IDS:
            print(f"  {rid} incremental_count={len(incremental_by_route[rid])}", flush=True)

        cross_route_overlap = compute_cross_route_overlap(incremental_by_route)

        generated_at = datetime.now(tz=UTC).isoformat()
        discovery_probe = build_discovery_probe_document(
            generated_at=generated_at,
            source_id=WIKIDATA_SOURCE_ID,
            rights_gate=rights_gate,
            accepted_universe=accepted_universe,
            route_records=route_records,
            drift=drift,
            incremental_by_route=incremental_by_route,
            cross_route_overlap=cross_route_overlap,
        )

        sample = select_entity_detail_sample(incremental_by_route)
        print(
            f"\nEntity-detail sample: selected_count={len(sample.selected_qids)} "
            f"(per-route pre-global-cap sizes: "
            f"{ {rid: len(qs) for rid, qs in sample.per_route_pre_global_cap.items()} })",
            flush=True,
        )

        details = (
            adapter.fetch_sampled_entity_details(list(sample.selected_qids))
            if sample.selected_qids
            else []
        )
        print(f"  fetched_entity_detail_count={len(details)}", flush=True)

    accepted_label_index = build_accepted_label_index(
        accepted_universe.accepted_auto_admit_identities
    )

    candidate_rows: list[dict[str, Any]] = []
    categories_by_route: dict[str, list[str]] = {rid: [] for rid in ROUTE_ALT_IDS}
    for detail in details:
        category, owner_qids = classify_identity_signal(
            detail.qid,
            detail.label,
            detail.aliases,
            accepted_qids=accepted_universe.accepted_auto_admit_qids,
            accepted_label_index=accepted_label_index,
        )
        membership = sorted(
            rid for rid in ROUTE_ALT_IDS if detail.qid in sample.route_membership.get(rid, ())
        )
        for rid in membership:
            categories_by_route[rid].append(str(category))
        candidate_rows.append(
            {
                "qid": detail.qid,
                "route_membership": membership,
                "label": detail.label,
                "aliases": list(detail.aliases),
                "description_en": detail.description_en,
                "p31_qids": list(detail.p31_qids),
                "p279_qids": list(detail.p279_qids),
                "p176_qids": list(detail.p176_qids),
                "p287_qids": list(detail.p287_qids),
                "identity_signal_category": str(category),
                "identity_signal_owner_qids": list(owner_qids),
            }
        )

    route_dispositions = {
        rid: str(
            determine_route_disposition(len(incremental_by_route[rid]), categories_by_route[rid])
        )
        for rid in ROUTE_ALT_IDS
    }
    print(f"\nRoute dispositions: {route_dispositions}", flush=True)

    sampled_candidates = build_sampled_candidates_document(
        generated_at=generated_at,
        accepted_universe=accepted_universe,
        sample=sample,
        candidate_rows=candidate_rows,
        route_dispositions=route_dispositions,
    )

    _validate_schema(discovery_probe, DISCOVERY_PROBE_SCHEMA_PATH, label="discovery_probe.json")
    _validate_schema(
        sampled_candidates, SAMPLED_CANDIDATES_SCHEMA_PATH, label="sampled_candidates.json"
    )

    SL0021_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERY_PROBE_PATH.write_text(json.dumps(discovery_probe, indent=2), encoding="utf-8")
    SAMPLED_CANDIDATES_PATH.write_text(json.dumps(sampled_candidates, indent=2), encoding="utf-8")
    print(f"\nWritten: {DISCOVERY_PROBE_PATH}", flush=True)
    print(f"Written: {SAMPLED_CANDIDATES_PATH}", flush=True)

    _write_report(discovery_probe, sampled_candidates, REPORT_PATH)
    return discovery_probe, sampled_candidates


# ---------------------------------------------------------------------------
# Offline verification (zero network access)
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap.wikidata_sl0021_alt_discovery import (
        ROUTE_ALT_IDS,
        IdentitySignalCategory,
        build_accepted_label_index,
        classify_identity_signal,
        compute_cross_route_overlap,
        compute_incremental_yield,
        compute_r0_drift,
        determine_route_disposition,
        load_and_fingerprint_immutable_inputs,
        select_entity_detail_sample,
    )

    print(
        "HullQ SLICE-0021 Wikidata Alternative Discovery-Semantics Pilot — OFFLINE VERIFY "
        "(no network access)",
        flush=True,
    )

    discovery_probe = json.loads(DISCOVERY_PROBE_PATH.read_text(encoding="utf-8"))
    sampled_candidates = json.loads(SAMPLED_CANDIDATES_PATH.read_text(encoding="utf-8"))

    mismatches: list[str] = []

    def _check(label: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            mismatches.append(f"{label}: recomputed={actual!r} != retained={expected!r}")

    accepted_universe = load_and_fingerprint_immutable_inputs()
    _check(
        "retained_direct_discovery_count",
        len(accepted_universe.retained_direct_discovery_qids),
        discovery_probe["immutable_inputs"]["retained_direct_discovery_count"],
    )
    _check(
        "accepted_auto_admit_count",
        len(accepted_universe.accepted_auto_admit_identities),
        discovery_probe["immutable_inputs"]["accepted_auto_admit_count"],
    )

    route_qids = {rid: rec["qids"] for rid, rec in discovery_probe["routes"].items()}
    r0_qids = route_qids["R0"]

    drift = compute_r0_drift(accepted_universe.retained_direct_discovery_qids, r0_qids)
    stored_drift = discovery_probe["drift"]
    _check(
        "drift.current_direct_count",
        drift.current_direct_count,
        stored_drift["current_direct_count"],
    )
    _check(
        "drift.retained_direct_still_present_count",
        drift.retained_direct_still_present_count,
        stored_drift["retained_direct_still_present_count"],
    )
    _check(
        "drift.retained_direct_absent_now_count",
        drift.retained_direct_absent_now_count,
        stored_drift["retained_direct_absent_now_count"],
    )
    _check(
        "drift.new_current_direct_since_sl0018_count",
        drift.new_current_direct_since_sl0018_count,
        stored_drift["new_current_direct_since_sl0018_count"],
    )

    incremental_by_route = {
        rid: compute_incremental_yield(route_qids[rid], r0_qids) for rid in ROUTE_ALT_IDS
    }
    for rid in ROUTE_ALT_IDS:
        _check(
            f"incremental.{rid}.count",
            len(incremental_by_route[rid]),
            discovery_probe["incremental"][rid]["count"],
        )

    cross_route_overlap = compute_cross_route_overlap(incremental_by_route)
    _check(
        "cross_route_overlap.total_union_count",
        len(cross_route_overlap.total_union),
        discovery_probe["cross_route_overlap"]["total_union_count"],
    )
    for rid, qids in cross_route_overlap.unique_contribution.items():
        _check(
            f"cross_route_overlap.unique_contribution.{rid}.count",
            len(qids),
            discovery_probe["cross_route_overlap"]["unique_contribution"][rid]["count"],
        )

    sample = select_entity_detail_sample(incremental_by_route)
    stored_selection = sampled_candidates["selection"]
    _check(
        "selection.selected_qids",
        list(sample.selected_qids),
        stored_selection["selected_qids"],
    )
    for rid, qids in sample.per_route_pre_global_cap.items():
        _check(
            f"selection.per_route_pre_global_cap.{rid}",
            list(qids),
            stored_selection["per_route_pre_global_cap"][rid],
        )

    accepted_label_index = build_accepted_label_index(
        accepted_universe.accepted_auto_admit_identities
    )
    categories_by_route: dict[str, list[str]] = {rid: [] for rid in ROUTE_ALT_IDS}
    for row in sampled_candidates["candidates"]:
        category, owner_qids = classify_identity_signal(
            row["qid"],
            row["label"],
            row["aliases"],
            accepted_qids=accepted_universe.accepted_auto_admit_qids,
            accepted_label_index=accepted_label_index,
        )
        _check(
            f"candidate[{row['qid']}].identity_signal_category",
            str(category),
            row["identity_signal_category"],
        )
        _check(
            f"candidate[{row['qid']}].identity_signal_owner_qids",
            list(owner_qids),
            row["identity_signal_owner_qids"],
        )
        for rid in row["route_membership"]:
            categories_by_route[rid].append(str(category))

    for rid in ROUTE_ALT_IDS:
        disposition = determine_route_disposition(
            len(incremental_by_route[rid]), categories_by_route[rid]
        )
        _check(
            f"route_dispositions.{rid}",
            str(disposition),
            sampled_candidates["route_dispositions"][rid],
        )

    # No fuzzy/whitespace-collapse/prefix transformation may ever manufacture
    # a match: prove that IdentitySignalCategory covers exactly the retained
    # candidate categories (defense-in-depth against a typo'd category string
    # silently passing the equality checks above via string coincidence).
    valid_categories = {str(c) for c in IdentitySignalCategory}
    mismatches.extend(
        f"candidate[{row['qid']}].identity_signal_category="
        f"{row['identity_signal_category']!r} is not a recognized category"
        for row in sampled_candidates["candidates"]
        if row["identity_signal_category"] not in valid_categories
    )

    if mismatches:
        print("\nOFFLINE VERIFY FAILED:", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained documents.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(
    discovery_probe: dict[str, Any], sampled_candidates: dict[str, Any], report_path: Path
) -> None:
    drift = discovery_probe["drift"]
    routes = discovery_probe["routes"]
    incremental = discovery_probe["incremental"]
    cross = discovery_probe["cross_route_overlap"]
    selection = sampled_candidates["selection"]
    totals = sampled_candidates["category_totals"]
    dispositions = sampled_candidates["route_dispositions"]

    lines = [
        "# HullQ SLICE-0021 Alternative Wikidata Discovery-Semantics Pilot Report",
        "",
        f"**Generated at:** {discovery_probe['generated_at']}  ",
        f"**Source:** {discovery_probe['source_id']}  ",
        f"**Rights gate:** {discovery_probe['rights_gate']}",
        "",
        "## IMMUTABLE HISTORICAL INPUTS (hard-asserted before live acquisition)",
        "",
        f"- Retained direct-discovery universe (SLICE-0017+0018): "
        f"**{discovery_probe['immutable_inputs']['retained_direct_discovery_count']}** "
        "(must equal 1,829)",
        f"- Accepted AUTO_ADMIT universe (SLICE-0017+0018): "
        f"**{discovery_probe['immutable_inputs']['accepted_auto_admit_count']}** (must equal 1,770)",
        f"- SLICE-0017 manifest: `{discovery_probe['immutable_inputs']['sl0017_manifest']['path']}` "
        f"sha256=`{discovery_probe['immutable_inputs']['sl0017_manifest']['sha256']}`",
        f"- SLICE-0018 manifest: `{discovery_probe['immutable_inputs']['sl0018_manifest']['path']}` "
        f"sha256=`{discovery_probe['immutable_inputs']['sl0018_manifest']['sha256']}`",
        "",
        "## ROUTES (R0-R3, exactly four, hard-capped at 3,000 each)",
        "",
    ]
    for key in ("R0", "R1", "R2", "R3"):
        rec = routes[key]
        lines.append(
            f"- **{key}** (`{rec['route_id']}`, version `{rec['version']}`): "
            f"result_count={rec['result_count']} possibly_truncated={rec['possibly_truncated']} "
            f"query_sha256=`{rec['query_sha256'][:16]}...` qid_list_digest=`{rec['qid_list_digest'][:16]}...` "
            f"http_request_count={rec['http_request_count']}"
        )
    lines += [
        "",
        "## CURRENT-R0 DRIFT (separate from alternative-route incremental yield)",
        "",
        f"- retained_direct_count: **{drift['retained_direct_count']}**",
        f"- current_direct_count: **{drift['current_direct_count']}**",
        f"- retained_direct_still_present_count: **{drift['retained_direct_still_present_count']}**",
        f"- retained_direct_absent_now_count: **{drift['retained_direct_absent_now_count']}**",
        f"- new_current_direct_since_sl0018_count: **{drift['new_current_direct_since_sl0018_count']}**",
        "",
        "## ALTERNATIVE-ROUTE INCREMENTAL YIELD (vs CURRENT R0, not merely the historical 1,829)",
        "",
    ]
    for rid in ("R1", "R2", "R3"):
        lines.append(f"- {rid} incremental_count: **{incremental[rid]['count']}**")
    lines += [
        "",
        "## CROSS-ROUTE OVERLAP",
        "",
        f"- total_union_count: **{cross['total_union_count']}**",
    ]
    for rid, uc in cross["unique_contribution"].items():
        lines.append(f"- {rid} unique_contribution_count: **{uc['count']}**")
    for pw in cross["pairwise"]:
        lines.append(f"- {pw['routes'][0]} ∩ {pw['routes'][1]}: {pw['count']}")
    lines += [
        "",
        "## ENTITY-DETAIL SAMPLE (hard-capped, deterministic)",
        "",
        f"- cap_per_route: {selection['cap_per_route']}, cap_global: {selection['cap_global']}",
        f"- selected_count: **{selection['selected_count']}**",
        "",
        "## IDENTITY-SIGNAL CATEGORY TOTALS (exact QID/label/alias probe only)",
        "",
    ]
    for cat, count in sorted(totals.items()):
        lines.append(f"- `{cat}`: {count}")
    lines += [
        "",
        f"- {sampled_candidates['no_exact_signal_notice']}",
        "",
        "## ROUTE DISPOSITIONS (evidence-derived recommendation only, not production authorization)",
        "",
    ]
    for rid in ("R1", "R2", "R3"):
        lines.append(f"- {rid}: **{dispositions[rid]}**")
    lines += [
        "",
        f"- {sampled_candidates['r3_fail_closed_notice']}",
        "",
        "## SCOPE CONFIRMATION",
        "",
        "- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified or deleted.",
        "- No HullQ ID was minted for any incremental candidate.",
        "- The accepted SLICE-0017/0018 retained manifests were read-only inputs and remain byte-unchanged.",
        "- The production Wikidata adapter's default discovery query was not changed.",
        "- SLICE-0022 was not created or started.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to: {report_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HullQ SLICE-0021 alternative Wikidata discovery-semantics pilot runner"
    )
    parser.add_argument("--live", action="store_true", help="Run the one live acquisition run")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Offline recompute/validation of the retained documents (no network access)",
    )
    parser.add_argument(
        "--user-agent", default=None, help="Wikimedia-policy-compliant User-Agent (live mode)"
    )
    args = parser.parse_args()

    if sum([args.live, args.verify]) != 1:
        raise SystemExit("Specify exactly one of --live or --verify")

    if args.live:
        if not args.user_agent:
            raise SystemExit("--user-agent is required for --live")
        run_live(user_agent=args.user_agent)
    else:
        run_verify()


if __name__ == "__main__":
    main()
