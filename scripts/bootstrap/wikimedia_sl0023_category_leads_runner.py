"""SLICE-0023 Wikimedia category identity-lead discovery pilot runner.

Three independent modes:

``--live``
    Perform the one bounded live acquisition run: rights-gated
    ``list=categorymembers`` acquisition (``cmnamespace=0``) over exactly the
    three fixed category roots, page-properties QID mapping, overlap
    categorization against the accepted 1,829/57 retained boundaries, the
    SLICE-0021 exact title-signal probe, deterministic SHA256 quality-sample
    selection, and the bounded Wikidata CC0 quality-sample context fetch
    (reusing the already-accepted ``WikidataAdapter``). Fails closed before
    any network use if an immutable boundary has drifted, and fails closed
    mid-run on a category-cap or request-ceiling breach. Writes
    ``discovery_manifest.json`` under
    ``research/bootstrap/wikimedia/sl0023-category-leads/`` and a scratch
    Wikidata-context file (NOT part of the retained package) for the
    separate manual quality-tag review step. Requires network access and is
    NOT part of normal CI.

``--assemble``
    Fully offline: combine the scratch Wikidata-context file with a
    manually-authored quality-tags JSON file (one ``{qid, quality_tag,
    rationale}`` row per selected sample QID — deliberately not computed by
    this script, per the controlling slice's "do not create an automated
    semantic classifier" rule) and the already-written
    ``discovery_manifest.json`` to produce ``quality_sample.json``,
    ``source_assessment.json``, ``REPORT.md`` and ``ARTIFACT-DIGESTS.json``.

``--verify``
    Fully offline (zero network access): reloads every already-retained
    document and recomputes EVERY structurally-derivable field purely from
    each document's own retained raw facts. This is what normal CI runs.

Usage::

    uv run python scripts/bootstrap/wikimedia_sl0023_category_leads_runner.py --live \\
        --user-agent "HullQ/0.1 (research@example.org; https://github.com/example/hullq)" \\
        --scratch-context PATH

    uv run python scripts/bootstrap/wikimedia_sl0023_category_leads_runner.py --assemble \\
        --scratch-context PATH --quality-tags PATH

    uv run python scripts/bootstrap/wikimedia_sl0023_category_leads_runner.py --verify
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

SL0023_DIR = ROOT / "research" / "bootstrap" / "wikimedia" / "sl0023-category-leads"
SOURCE_ASSESSMENT_PATH = SL0023_DIR / "source_assessment.json"
SOURCE_ASSESSMENT_SCHEMA_PATH = SL0023_DIR / "source_assessment_schema.json"
DISCOVERY_MANIFEST_PATH = SL0023_DIR / "discovery_manifest.json"
DISCOVERY_MANIFEST_SCHEMA_PATH = SL0023_DIR / "discovery_manifest_schema.json"
QUALITY_SAMPLE_PATH = SL0023_DIR / "quality_sample.json"
QUALITY_SAMPLE_SCHEMA_PATH = SL0023_DIR / "quality_sample_schema.json"
REPORT_PATH = SL0023_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0023_DIR / "ARTIFACT-DIGESTS.json"

WIKIPEDIA_SOURCE_PATH = ROOT / "fixtures" / "sources" / "wikipedia_source.json"
WIKIDATA_SOURCE_PATH = ROOT / "fixtures" / "sources" / "wikidata_source.json"

RIGHTS_EVIDENCE_URLS = (
    "https://foundation.wikimedia.org/wiki/Terms_of_Use",
    "https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy",
    "https://www.mediawiki.org/wiki/API:Categorymembers",
    "https://www.mediawiki.org/wiki/API:Licensing",
)


def _write_json_lf(path: Path, data: Any) -> None:
    """Write JSON with a guaranteed LF-only trailing-newline byte layout,
    independent of platform newline translation, so retained artifacts are
    byte-stable across Windows/Linux CI (see the SLICE-0019 manufacturer
    artifact byte-stability fix for the established repository pattern).
    """
    path.write_bytes((json.dumps(data, indent=2) + "\n").encode("utf-8"))


def _write_text_lf(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


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


def run_live(*, user_agent: str, scratch_context_path: Path) -> None:
    from hullq.bootstrap.wikimedia_sl0023_category_leads import (
        CATEGORY_ROUTES,
        COMBINED_MEMBERSHIP_CAP,
        CategoryPage,
        apply_qid_mapping,
        build_accepted_label_index,
        build_category_membership_record,
        build_discovery_manifest_document,
        build_incremental_by_stratum,
        build_request_ceiling_summary,
        build_unique_pages,
        classify_title_signal,
        compute_overlap_sets,
        compute_qid_multiplicity,
        load_and_verify_immutable_boundaries,
        select_deterministic_sample,
    )
    from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use
    from hullq.sources.wikidata import WikidataAdapter, WikidataAdapterConfig
    from hullq.sources.wikimedia import WikimediaAdapter, WikimediaAdapterConfig

    print(
        "HullQ SLICE-0023 Wikimedia Category Identity-Lead Discovery Pilot — LIVE RUN", flush=True
    )

    boundaries = load_and_verify_immutable_boundaries()
    print(
        "  immutable boundaries verified: "
        f"accepted_direct={len(boundaries.accepted_direct_qids)} "
        f"accepted_auto_admit={len(boundaries.accepted_universe.accepted_auto_admit_identities)} "
        f"retained_crosswalk={boundaries.retained_historical_crosswalk_count} "
        f"alternative_union={len(boundaries.alternative_union_qids)}",
        flush=True,
    )

    wikipedia_source = json.loads(WIKIPEDIA_SOURCE_PATH.read_text(encoding="utf-8"))
    wikidata_source = json.loads(WIKIDATA_SOURCE_PATH.read_text(encoding="utf-8"))

    rl_decision = check_source_use(wikipedia_source, SourceUse.RESEARCH_LEAD)
    rights_gate = {
        "wikipedia_research_lead": str(rl_decision.outcome),
        "wikipedia_automated_ingestion_clearance": wikipedia_source["rights"]["clearance"][
            "automated_ingestion"
        ],
    }
    print(f"  rights_gate={rights_gate}", flush=True)
    if rl_decision.outcome != DecisionOutcome.ALLOWED:
        raise SystemExit(
            f"SLICE-0023 refusing before any network request: research_lead gate "
            f"outcome={rl_decision.outcome!s}"
        )
    if wikipedia_source["rights"]["clearance"]["automated_ingestion"] != "allowed":
        raise SystemExit(
            "SLICE-0023 refusing before any network request: automated_ingestion clearance is "
            f"not 'allowed': {wikipedia_source['rights']['clearance']['automated_ingestion']!r}"
        )

    wikipedia_config = WikimediaAdapterConfig(user_agent=user_agent, wikipedia_request_ceiling=75)

    import httpx

    category_records: dict[str, dict[str, Any]] = {}
    total_wikipedia_requests = 0
    combined_raw_member_count = 0

    with httpx.Client() as client:
        wikipedia_adapter = WikimediaAdapter(
            source=wikipedia_source, config=wikipedia_config, http_client=client
        )
        for route in CATEGORY_ROUTES:
            acquired_at = datetime.now(tz=UTC).isoformat()
            print(f"\nAcquiring Category:{route.name} (hard_cap={route.hard_cap})...", flush=True)
            members, request_count, continuation_count = wikipedia_adapter.fetch_category_members(
                route.name, hard_cap=route.hard_cap
            )
            print(
                f"  member_count={len(members)} request_count={request_count} "
                f"continuation_count={continuation_count}",
                flush=True,
            )
            combined_raw_member_count += len(members)
            if combined_raw_member_count > COMBINED_MEMBERSHIP_CAP:
                raise SystemExit(
                    f"SLICE-0023 BLOCKED: combined pre-dedup membership count "
                    f"{combined_raw_member_count} exceeds the fixed cap of "
                    f"{COMBINED_MEMBERSHIP_CAP}"
                )
            category_records[route.name] = build_category_membership_record(
                route,
                [CategoryPage(pageid=m.pageid, title=m.title, ns=m.ns) for m in members],
                acquired_at=acquired_at,
                request_count=request_count,
                continuation_count=continuation_count,
            )
            total_wikipedia_requests += request_count

        unique_pages = build_unique_pages(category_records)
        all_pageids = sorted(unique_pages)
        print(f"\nUnique pages across all categories: {len(all_pageids)}", flush=True)

        category_request_total = total_wikipedia_requests
        pageid_to_qid = wikipedia_adapter.fetch_pageprops_wikibase_items(all_pageids)
        total_wikipedia_requests = wikipedia_adapter.usage_metrics.retrieval_count
        pageprops_request_count = total_wikipedia_requests - category_request_total
        print(
            f"  pages with linked QID: {len(pageid_to_qid)} "
            f"(total wikipedia_request_count={total_wikipedia_requests})",
            flush=True,
        )

        unique_pages = apply_qid_mapping(unique_pages, pageid_to_qid)
        qid_multiplicity = compute_qid_multiplicity(unique_pages)
        no_qid_pageids = frozenset(
            pid for pid, info in unique_pages.items() if info.get("qid") is None
        )
        overlap_sets = compute_overlap_sets(
            qid_multiplicity,
            no_qid_pageids,
            accepted_direct_qids=boundaries.accepted_direct_qids,
            alternative_union_qids=boundaries.alternative_union_qids,
        )
        print(
            "  overlap: accepted_direct="
            f"{len(overlap_sets.accepted_direct_qid_overlap)} "
            f"retained_alternative={len(overlap_sets.retained_alternative_qid_overlap)} "
            f"incremental={len(overlap_sets.incremental_qid_lead)} "
            f"no_qid={len(overlap_sets.no_wikidata_qid_pageids)}",
            flush=True,
        )

        accepted_label_index = build_accepted_label_index(
            boundaries.accepted_universe.accepted_auto_admit_identities
        )
        title_signal_rows: list[dict[str, Any]] = []
        for pid, info in sorted(unique_pages.items()):
            qid = info.get("qid")
            if qid in overlap_sets.accepted_direct_qid_overlap:
                continue
            category, owners = classify_title_signal(
                info["title"], accepted_label_index=accepted_label_index
            )
            title_signal_rows.append(
                {
                    "pageid": pid,
                    "qid": qid,
                    "title": info["title"],
                    "title_signal_category": str(category),
                    "owner_qids": list(owners),
                }
            )

        incremental_by_stratum = build_incremental_by_stratum(
            overlap_sets.incremental_qid_lead, qid_multiplicity, unique_pages
        )
        sample = select_deterministic_sample(incremental_by_stratum)
        print(
            f"\nDeterministic quality sample: selected_count={len(sample.selected_qids)} "
            f"(per-stratum: { {s: len(qs) for s, qs in sample.selected_by_stratum.items()} })",
            flush=True,
        )

        wikidata_adapter = WikidataAdapter(
            source=wikidata_source,
            config=WikidataAdapterConfig(user_agent=user_agent, request_timeout_seconds=120.0),
            http_client=client,
        )
        details = (
            wikidata_adapter.fetch_sampled_entity_details(list(sample.selected_qids))
            if sample.selected_qids
            else []
        )
        print(f"  fetched wikidata_context_count={len(details)}", flush=True)
        if {d.qid for d in details} != set(sample.selected_qids):
            raise SystemExit(
                "SLICE-0023 BLOCKED: Wikidata quality-sample fetch did not exactly cover the "
                "selected sample"
            )

    request_ceiling_summary = build_request_ceiling_summary(
        wikipedia_request_count=total_wikipedia_requests,
        wikidata_request_count=wikidata_adapter.usage_metrics.retrieval_count,
    )
    print(f"\nRequest ceilings: {request_ceiling_summary}", flush=True)

    rights_gate_full = {
        **rights_gate,
        "wikidata_bulk_bootstrap": wikidata_source["rights"]["clearance"]["bulk_bootstrap"],
        "wikidata_automated_ingestion": wikidata_source["rights"]["clearance"][
            "automated_ingestion"
        ],
    }

    generated_at = datetime.now(tz=UTC).isoformat()
    discovery_manifest = build_discovery_manifest_document(
        generated_at=generated_at,
        source_id="SRC_WIKIPEDIA_API_2026",
        rights_gate=rights_gate_full,
        boundaries=boundaries,
        category_records=category_records,
        unique_pages=unique_pages,
        qid_multiplicity=qid_multiplicity,
        no_qid_pageids=no_qid_pageids,
        overlap_sets=overlap_sets,
        title_signal_rows=title_signal_rows,
        incremental_by_stratum=incremental_by_stratum,
        sample=sample,
        request_ceiling_summary=request_ceiling_summary,
        pageprops_request_count=pageprops_request_count,
    )
    _validate_schema(
        discovery_manifest, DISCOVERY_MANIFEST_SCHEMA_PATH, label="discovery_manifest.json"
    )

    SL0023_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_lf(DISCOVERY_MANIFEST_PATH, discovery_manifest)
    print(f"\nWritten: {DISCOVERY_MANIFEST_PATH}", flush=True)

    wikidata_context_rows = [
        {
            "qid": d.qid,
            "label": d.label,
            "description_en": d.description_en,
            "p31_qids": list(d.p31_qids),
            "p176_qids": list(d.p176_qids),
            "p287_qids": list(d.p287_qids),
        }
        for d in sorted(details, key=lambda d: d.qid)
    ]
    scratch = {
        "generated_at": generated_at,
        "selected_qids": list(sample.selected_qids),
        "unique_incremental_qid_lead_count": len(overlap_sets.incremental_qid_lead),
        "wikidata_context_rows": wikidata_context_rows,
    }
    scratch_context_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_lf(scratch_context_path, scratch)
    print(
        f"Written (scratch, NOT part of the retained package): {scratch_context_path}", flush=True
    )
    print(
        "\nNext step: manually review each sampled QID's retained Wikidata CC0 context and "
        "write a quality-tags JSON file (list of {qid, quality_tag, rationale}), then run "
        "--assemble.",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Offline assembly of quality_sample.json / source_assessment.json / REPORT.md
# ---------------------------------------------------------------------------


def run_assemble(*, scratch_context_path: Path, quality_tags_path: Path) -> None:
    from hullq.bootstrap.wikimedia_sl0023_category_leads import (
        SampleSelection,
        build_quality_sample_document,
        load_and_verify_immutable_boundaries,
        recompute_rights_access_ok,
    )

    print(
        "HullQ SLICE-0023 Wikimedia Category Identity-Lead Discovery Pilot — ASSEMBLE", flush=True
    )

    discovery_manifest = json.loads(DISCOVERY_MANIFEST_PATH.read_text(encoding="utf-8"))
    scratch = json.loads(scratch_context_path.read_text(encoding="utf-8"))
    quality_rows = json.loads(quality_tags_path.read_text(encoding="utf-8"))

    boundaries = load_and_verify_immutable_boundaries()

    selection = discovery_manifest["sample_selection"]
    sample = SampleSelection(
        selected_by_stratum={
            stratum: tuple(qids)
            for stratum, qids in selection["selected_by_stratum_sha256_order"].items()
        },
        selected_qids=tuple(selection["selected_qids"]),
    )

    wikipedia_source = json.loads(WIKIPEDIA_SOURCE_PATH.read_text(encoding="utf-8"))
    wikidata_source = json.loads(WIKIDATA_SOURCE_PATH.read_text(encoding="utf-8"))
    rights_access_ok = recompute_rights_access_ok(
        rights_gate=discovery_manifest["rights_gate"],
        wikipedia_source=wikipedia_source,
        wikidata_source=wikidata_source,
    )
    unique_incremental_count = discovery_manifest["overlap_sets"]["incremental_qid_lead"]["count"]

    generated_at = datetime.now(tz=UTC).isoformat()
    quality_sample = build_quality_sample_document(
        generated_at=generated_at,
        boundaries=boundaries,
        sample=sample,
        wikidata_context_rows=scratch["wikidata_context_rows"],
        quality_rows=quality_rows,
        rights_access_ok=rights_access_ok,
        unique_incremental_count=unique_incremental_count,
    )
    _validate_schema(quality_sample, QUALITY_SAMPLE_SCHEMA_PATH, label="quality_sample.json")

    SL0023_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_lf(QUALITY_SAMPLE_PATH, quality_sample)
    print(f"Written: {QUALITY_SAMPLE_PATH}", flush=True)

    source_assessment = _build_source_assessment_document(generated_at, discovery_manifest)
    _validate_schema(
        source_assessment, SOURCE_ASSESSMENT_SCHEMA_PATH, label="source_assessment.json"
    )
    _write_json_lf(SOURCE_ASSESSMENT_PATH, source_assessment)
    print(f"Written: {SOURCE_ASSESSMENT_PATH}", flush=True)

    _write_report(discovery_manifest, quality_sample, source_assessment, REPORT_PATH)
    _write_artifact_digests(ARTIFACT_DIGESTS_PATH)
    print(f"Written: {REPORT_PATH}", flush=True)
    print(f"Written: {ARTIFACT_DIGESTS_PATH}", flush=True)


def _build_source_assessment_document(
    generated_at: str, discovery_manifest: dict[str, Any]
) -> dict[str, Any]:
    wikipedia_source = json.loads(WIKIPEDIA_SOURCE_PATH.read_text(encoding="utf-8"))
    wikidata_source = json.loads(WIKIDATA_SOURCE_PATH.read_text(encoding="utf-8"))
    return {
        "schema_version": "sl0023-source-assessment-v1",
        "generated_at": generated_at,
        "sources": {
            "wikipedia": {
                "source_id": wikipedia_source["source_id"],
                "rights_basis": wikipedia_source["rights"]["rights_basis"],
                "license_expression": wikipedia_source["rights"]["license_expression"],
                "clearance": wikipedia_source["rights"]["clearance"],
                "review_date": wikipedia_source["rights"]["review"]["reviewed_at"],
            },
            "wikidata": {
                "source_id": wikidata_source["source_id"],
                "rights_basis": wikidata_source["rights"]["rights_basis"],
                "license_expression": wikidata_source["rights"]["license_expression"],
                "clearance": wikidata_source["rights"]["clearance"],
                "review_date": wikidata_source["rights"]["review"]["reviewed_at"],
            },
        },
        "rights_evidence_urls": list(RIGHTS_EVIDENCE_URLS),
        "user_agent_used": True,
        "rights_gate_result": discovery_manifest["rights_gate"],
        "request_ceilings": discovery_manifest["request_ceilings"],
        "no_wikipedia_prose_infobox_content_retained": True,
        "no_canonical_mutation": True,
    }


# ---------------------------------------------------------------------------
# Offline verification (zero network access)
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap.wikimedia_sl0023_category_leads import (
        SampleSelection,
        build_accepted_label_index,
        build_incremental_by_stratum,
        compute_overlap_sets,
        compute_qid_multiplicity,
        load_and_verify_immutable_boundaries,
        recompute_rights_access_ok,
        reconstruct_unique_pages_from_manifest,
        select_deterministic_sample,
        verify_category_record_self_consistency,
        verify_discovery_manifest_derived_sets_self_consistency,
        verify_immutable_boundaries_reference_self_consistency,
        verify_quality_sample_self_consistency,
        verify_request_breakdown_self_consistency,
        verify_sample_selection_self_consistency,
        verify_title_signal_rows_self_consistency,
        verify_unique_pages_reconstruction_self_consistency,
        verify_wikidata_context_coverage_self_consistency,
    )

    print(
        "HullQ SLICE-0023 Wikimedia Category Identity-Lead Discovery Pilot — OFFLINE VERIFY "
        "(no network access)",
        flush=True,
    )

    discovery_manifest = json.loads(DISCOVERY_MANIFEST_PATH.read_text(encoding="utf-8"))
    quality_sample = json.loads(QUALITY_SAMPLE_PATH.read_text(encoding="utf-8"))
    source_assessment = json.loads(SOURCE_ASSESSMENT_PATH.read_text(encoding="utf-8"))

    _validate_schema(
        discovery_manifest, DISCOVERY_MANIFEST_SCHEMA_PATH, label="discovery_manifest.json"
    )
    _validate_schema(quality_sample, QUALITY_SAMPLE_SCHEMA_PATH, label="quality_sample.json")
    _validate_schema(
        source_assessment, SOURCE_ASSESSMENT_SCHEMA_PATH, label="source_assessment.json"
    )
    if ARTIFACT_DIGESTS_PATH.exists():
        _validate_schema(
            json.loads(ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8")),
            SL0023_DIR / "artifact_digests_schema.json",
            label="ARTIFACT-DIGESTS.json",
        )

    mismatches: list[str] = []

    boundaries = load_and_verify_immutable_boundaries()
    mismatches.extend(
        verify_immutable_boundaries_reference_self_consistency(discovery_manifest, boundaries)
    )

    for name, record in discovery_manifest["categories"].items():
        mismatches.extend(verify_category_record_self_consistency(name, record))

    mismatches.extend(verify_unique_pages_reconstruction_self_consistency(discovery_manifest))

    unique_pages = reconstruct_unique_pages_from_manifest(discovery_manifest)
    qid_multiplicity = compute_qid_multiplicity(unique_pages)
    no_qid_pageids = frozenset(pid for pid, info in unique_pages.items() if info.get("qid") is None)
    overlap_sets = compute_overlap_sets(
        qid_multiplicity,
        no_qid_pageids,
        accepted_direct_qids=boundaries.accepted_direct_qids,
        alternative_union_qids=boundaries.alternative_union_qids,
    )
    incremental_by_stratum = build_incremental_by_stratum(
        overlap_sets.incremental_qid_lead, qid_multiplicity, unique_pages
    )
    sample = select_deterministic_sample(incremental_by_stratum)

    mismatches.extend(
        verify_discovery_manifest_derived_sets_self_consistency(
            discovery_manifest,
            overlap_sets=overlap_sets,
            incremental_by_stratum=incremental_by_stratum,
            sample=sample,
        )
    )
    mismatches.extend(verify_sample_selection_self_consistency(incremental_by_stratum, sample))

    accepted_label_index = build_accepted_label_index(
        boundaries.accepted_universe.accepted_auto_admit_identities
    )
    mismatches.extend(
        verify_title_signal_rows_self_consistency(
            discovery_manifest, unique_pages, overlap_sets, accepted_label_index
        )
    )

    unique_incremental_count = discovery_manifest["overlap_sets"]["incremental_qid_lead"]["count"]

    # Rights-access truth is re-derived independently from the live reviewed
    # Source records + the retained discovery_manifest.rights_gate — NEVER
    # trusted from the retained quality_sample.rights_access_ok flag itself,
    # so a coherent tamper of rights_access_ok + recommendation (even one
    # that also regenerates ARTIFACT-DIGESTS.json to match) cannot pass.
    wikipedia_source = json.loads(WIKIPEDIA_SOURCE_PATH.read_text(encoding="utf-8"))
    wikidata_source = json.loads(WIKIDATA_SOURCE_PATH.read_text(encoding="utf-8"))
    recomputed_rights_access_ok = recompute_rights_access_ok(
        rights_gate=discovery_manifest["rights_gate"],
        wikipedia_source=wikipedia_source,
        wikidata_source=wikidata_source,
    )
    mismatches.extend(
        verify_quality_sample_self_consistency(
            quality_sample,
            unique_incremental_count=unique_incremental_count,
            recomputed_rights_access_ok=recomputed_rights_access_ok,
        )
    )
    mismatches.extend(verify_wikidata_context_coverage_self_consistency(quality_sample))

    stored_selection = discovery_manifest["sample_selection"]
    reconstructed_sample = SampleSelection(
        selected_by_stratum={
            stratum: tuple(qids)
            for stratum, qids in stored_selection["selected_by_stratum_sha256_order"].items()
        },
        selected_qids=tuple(stored_selection["selected_qids"]),
    )
    if reconstructed_sample.selected_qids != sample.selected_qids:
        mismatches.append(
            "discovery_manifest.sample_selection.selected_qids does not match the recomputed "
            "sample selection"
        )
    if quality_sample["selection_reference"]["selected_qids"] != list(sample.selected_qids):
        mismatches.append(
            "quality_sample.selection_reference.selected_qids does not match the recomputed "
            "sample selection"
        )

    # Structural request-count reconciliation: not merely "count <= ceiling",
    # but that the retained aggregate wikipedia_request_count is exactly tied
    # back to each fixed category's own retained request_count plus a
    # pageprops-phase batch count independently derivable from
    # unique_page_count, and that total == wikipedia + wikidata.
    mismatches.extend(verify_request_breakdown_self_consistency(discovery_manifest))

    for name, route_cap in (("Keelboats", 2000), ("Catamarans", 250), ("Trimarans", 200)):
        record = discovery_manifest["categories"][name]
        if record["member_count"] > route_cap:
            mismatches.append(f"category {name} member_count exceeds its accepted hard cap")

    if _artifact_digests_match():
        print("ARTIFACT-DIGESTS.json: PASS", flush=True)
    else:
        mismatches.append("ARTIFACT-DIGESTS.json does not match recomputed retained-file digests")

    if mismatches:
        print("\nOFFLINE VERIFY FAILED:", flush=True)
        for m in mismatches:
            print(f"  - {m}", flush=True)
        raise SystemExit(1)

    print(
        "\nOFFLINE VERIFY: PASS — every recomputed value matches the retained documents.",
        flush=True,
    )


def _artifact_digests_match() -> bool:
    if not ARTIFACT_DIGESTS_PATH.exists():
        return False
    stored = json.loads(ARTIFACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    recomputed = _compute_artifact_digests()
    return stored.get("digests") == recomputed


def _compute_artifact_digests() -> dict[str, str]:
    files = [
        SOURCE_ASSESSMENT_PATH,
        SOURCE_ASSESSMENT_SCHEMA_PATH,
        DISCOVERY_MANIFEST_PATH,
        DISCOVERY_MANIFEST_SCHEMA_PATH,
        QUALITY_SAMPLE_PATH,
        QUALITY_SAMPLE_SCHEMA_PATH,
        REPORT_PATH,
    ]
    digests: dict[str, str] = {}
    for path in files:
        if path.exists():
            digests[path.name] = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    return digests


def _write_artifact_digests(path: Path) -> None:
    document = {
        "schema_version": "sl0023-artifact-digests-v1",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "excludes_self": "ARTIFACT-DIGESTS.json",
        "digests": _compute_artifact_digests(),
    }
    _write_json_lf(path, document)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _write_report(
    discovery_manifest: dict[str, Any],
    quality_sample: dict[str, Any],
    source_assessment: dict[str, Any],
    report_path: Path,
) -> None:
    boundaries = discovery_manifest["immutable_boundaries"]
    categories = discovery_manifest["categories"]
    overlap = discovery_manifest["overlap_sets"]
    title_signal = discovery_manifest["title_signal"]
    request_ceilings = discovery_manifest["request_ceilings"]
    selection = discovery_manifest["sample_selection"]
    totals = quality_sample["quality_tag_counts"]
    pct = quality_sample["quality_tag_percentages"]

    lines = [
        "# HullQ SLICE-0023 Wikimedia Category Identity-Lead Discovery Pilot Report",
        "",
        f"**Generated at:** {discovery_manifest['generated_at']}  ",
        f"**Source:** {discovery_manifest['source_id']}  ",
        f"**Rights gate:** {discovery_manifest['rights_gate']}",
        "",
        "## IMMUTABLE COMPARISON BOUNDARIES (hard-asserted before live acquisition)",
        "",
        f"- accepted direct-discovery candidate universe: **{boundaries['accepted_direct_discovery_count']}** (must equal 1,829)",
        f"- accepted canonical BoatModel universe: **{boundaries['accepted_auto_admit_count']}** (must equal 1,770)",
        f"- accepted historical QID -> HullQ-ID mappings: **{boundaries['retained_historical_crosswalk_count']}** (must equal 1,772)",
        f"- accepted SLICE-0021 alternative-route union: **{boundaries['accepted_alternative_union_count']}** (must equal 57)",
        f"- SLICE-0017 manifest sha256: `{boundaries['sl0017_manifest_sha256']}`",
        f"- SLICE-0018 manifest sha256: `{boundaries['sl0018_manifest_sha256']}`",
        f"- SLICE-0021 discovery_probe.json Git blob sha1: `{boundaries['sl0021_discovery_probe_git_blob_sha1']}`",
        f"- SLICE-0021 sampled_candidates.json Git blob sha1: `{boundaries['sl0021_sampled_candidates_git_blob_sha1']}`",
        "",
        "## FIXED CATEGORY ROUTES (exactly three, no recursion/expansion)",
        "",
    ]
    for name in ("Keelboats", "Catamarans", "Trimarans"):
        rec = categories[name]
        lines.append(
            f"- **{name}**: member_count={rec['member_count']} hard_cap={rec['hard_cap']} "
            f"complete={rec['complete']} request_count={rec['request_count']} "
            f"continuation_count={rec['continuation_count']}"
        )
    lines += [
        "",
        f"- combined pre-dedup membership: **{sum(categories[n]['member_count'] for n in categories)}** (cap 2,450)",
        f"- unique page count: **{discovery_manifest['unique_page_count']}**",
        f"- cross-category duplicate page IDs: **{len(discovery_manifest['cross_category_duplicate_pageids'])}**",
        f"- duplicate QIDs (same QID via >1 page): **{len(discovery_manifest['page_qid_mapping']['duplicate_qids'])}**",
        "",
        "## OVERLAP CATEGORIES",
        "",
        f"- accepted_direct_qid_overlap: **{overlap['accepted_direct_qid_overlap']['count']}**",
        f"- retained_alternative_qid_overlap: **{overlap['retained_alternative_qid_overlap']['count']}**",
        f"- incremental_qid_lead: **{overlap['incremental_qid_lead']['count']}**",
        f"- no_wikidata_qid: **{overlap['no_wikidata_qid']['count']}**",
        "",
        "## EXACT IDENTITY-SIGNAL TOTALS (trim+casefold-only probe)",
        "",
    ]
    for cat, count in sorted(title_signal["totals"].items()):
        lines.append(f"- `{cat}`: {count}")
    lines += [
        "",
        "## DETERMINISTIC QUALITY SAMPLE (SHA256-ordered, no cross-stratum backfill)",
        "",
        f"- cap_by_stratum: {selection['cap_by_stratum']}, total_cap: {selection['total_cap']}",
        f"- selected_count: **{selection['selected_count']}**",
        "",
        "## QUALITY REVIEW TOTALS",
        "",
    ]
    for tag in sorted(totals):
        lines.append(f"- `{tag}`: {totals[tag]} ({pct[tag]}%)")
    lines += [
        "",
        f"- total_sampled: **{quality_sample['total_sampled']}**",
        "",
        "## REQUEST CEILINGS",
        "",
        f"- wikipedia_request_count: **{request_ceilings['wikipedia_request_count']}** (ceiling {request_ceilings['wikipedia_request_ceiling']})",
        f"- wikidata_request_count: **{request_ceilings['wikidata_request_count']}** (ceiling {request_ceilings['wikidata_request_ceiling']})",
        f"- total_request_count: **{request_ceilings['total_request_count']}** (ceiling {request_ceilings['total_request_ceiling']})",
        "",
        "## RECOMMENDATION (precommitted, mechanical rule)",
        "",
        f"- **{quality_sample['recommendation']}**",
        "",
        "## SOURCE-RIGHTS / ACCESS CONFIRMATION",
        "",
        "- Wikipedia is used strictly as a research-lead surface: category name, page ID, "
        "namespace, page title, canonical URL and linked Wikidata QID only.",
        "- No Wikipedia article prose, infobox value, table, image or reference content became "
        "HullQ evidence.",
        "- Wikidata CC0 quality-sample context is bounded to the deterministic <=150-QID sample; "
        "no broad WDQS/SPARQL discovery was run.",
        f"- Rights evidence URLs reviewed: {source_assessment['rights_evidence_urls']}",
        "",
        "## SCOPE CONFIRMATION",
        "",
        "- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified "
        "or deleted.",
        "- No HullQ ID was minted for any lead.",
        "- The accepted SLICE-0017/0018/0021 retained manifests were read-only inputs and remain "
        "byte-unchanged.",
        "- The production Wikidata adapter's default discovery query was not changed and "
        "Wikipedia/Wikimedia was not added to production discovery.",
        "- No prior SLICE-0017/0018/0021/0022 review queue was resolved as a side effect.",
        "- Stage-3.3 was not started and SLICE-0024 was not created/started.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_lf(report_path, "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HullQ SLICE-0023 Wikimedia category identity-lead discovery pilot runner"
    )
    parser.add_argument("--live", action="store_true", help="Run the one live acquisition run")
    parser.add_argument(
        "--assemble",
        action="store_true",
        help="Offline: assemble quality_sample.json/source_assessment.json/REPORT.md",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Offline recompute/validation of the retained documents (no network access)",
    )
    parser.add_argument(
        "--user-agent", default=None, help="Wikimedia-policy-compliant User-Agent (live mode)"
    )
    parser.add_argument(
        "--scratch-context",
        type=Path,
        default=None,
        help="Path to the scratch Wikidata-context JSON file (live/assemble modes)",
    )
    parser.add_argument(
        "--quality-tags",
        type=Path,
        default=None,
        help="Path to a manually-authored quality-tags JSON file (assemble mode)",
    )
    args = parser.parse_args()

    if sum([args.live, args.assemble, args.verify]) != 1:
        raise SystemExit("Specify exactly one of --live, --assemble or --verify")

    if args.live:
        if not args.user_agent:
            raise SystemExit("--user-agent is required for --live")
        if not args.scratch_context:
            raise SystemExit("--scratch-context is required for --live")
        run_live(user_agent=args.user_agent, scratch_context_path=args.scratch_context)
    elif args.assemble:
        if not args.scratch_context or not args.quality_tags:
            raise SystemExit("--scratch-context and --quality-tags are required for --assemble")
        run_assemble(scratch_context_path=args.scratch_context, quality_tags_path=args.quality_tags)
    else:
        run_verify()


if __name__ == "__main__":
    main()
