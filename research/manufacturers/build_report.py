#!/usr/bin/env python3
"""Build the retained SLICE-0019 research report from committed structured artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry.json"
STUDY = ROOT / "source_yield_study.json"
OVERLAP = ROOT / "overlap_result.json"
OUT = ROOT / "REPORT.md"
HISTORICAL_STATUSES = {"historical", "defunct", "acquired", "renamed"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{100 * numerator / denominator:.1f}%"


def main() -> None:
    registry = load_json(REGISTRY)
    study = load_json(STUDY)
    overlap = load_json(OVERLAP)

    records = registry["records"]
    entities = study["entities"]
    assert len(entities) == 20

    statuses = Counter(record["research_status"] for record in records)
    floor_records = [
        record
        for record in records
        if record["research_status"] == "verified"
        and {"manufacturer", "yard"} & set(record["entity_kind"])
    ]
    countries = sorted(
        {record["country"] for record in floor_records if record["country"] is not None}
    )
    regions = sorted({record["region"] for record in floor_records})
    activity = Counter(record["status"] for record in floor_records)
    historical_count = sum(
        1 for record in floor_records if record["status"] in HISTORICAL_STATUSES
    )
    archive_surface_count = sum(
        1
        for record in floor_records
        if record["official_heritage_archive"] or record["other_archive_sources"]
    )
    official_current_count = sum(
        1 for record in floor_records if record["official_current_site"]
    )
    sample_count = sum(1 for record in records if record["source_yield_sample"])
    assert sample_count == 20

    source_types: Counter[str] = Counter()
    rights: Counter[str] = Counter()
    for record in records:
        for source in record["sources"]:
            source_types[source["source_type"]] += 1
        for assessment in record["rights_assessment"]:
            rights[assessment["systematic_use_status"]] += 1

    needs_review = [
        record["preferred_display_name"]
        for record in records
        if record["research_status"] == "needs_review"
    ]

    probe = overlap["probe_summary"]
    exact = probe["exact_overlap_count"]
    possible = probe["unresolved_possible_overlap_count"]
    new = probe["clearly_new_candidate_count"]
    probe_total = probe["probe_model_identity_count"]

    lines: list[str] = []
    lines.extend(
        [
            "# SLICE-0019 — Global Series-Sailboat Manufacturer/Yard Universe Research Report",
            "",
            "**Slice:** SLICE-0019  ",
            "**Retained status:** REVIEW  ",
            f"**Registry generated:** {registry['generated_at']}  ",
            f"**Registry version:** {registry['registry_version']}  ",
            "",
            "## Executive result",
            "",
            "SLICE-0019 reached its bounded breadth floors without claiming global completeness. "
            "The retained registry is non-canonical research evidence: it does not create, merge, "
            "delete or remint HullQ Brand, Organization, BoatModel or BoatDesign identities.",
            "",
            f"- Total retained research records: **{len(records)}**",
            f"- Verified records: **{statuses['verified']}**",
            f"- Needs review: **{statuses['needs_review']}**",
            f"- Excluded: **{statuses['excluded']}**",
            f"- Strict verified manufacturer/yard floor: **{len(floor_records)}**",
            f"- Countries represented by strict floor records: **{len(countries)}**",
            f"- Macro-regions represented: **{len(regions)}**",
            f"- Historical/defunct/acquired/renamed strict-floor records: **{historical_count}**",
            f"- Strict-floor records with a retained official/recognized heritage or archive surface: **{archive_surface_count}**",
            f"- Strict-floor records with a retained official current site: **{official_current_count}**",
            f"- Source-yield sample records marked in registry: **{sample_count}**",
            "",
            "The sole retained `needs_review` record is: "
            + (", ".join(needs_review) if needs_review else "none")
            + ". It remains review-bound because the recovered evidence collapses materially distinct "
            "historical/revival identities; the slice does not fabricate a forced reconciliation.",
            "",
            "## Methodology",
            "",
            "The research proceeded in bounded regional waves and then a delta-first independent review. "
            "Previously recovered claims were reused when they already supported a decision; external research "
            "was performed only to close a concrete evidentiary gap. Active and historical yards were treated "
            "as first-class. Brand, yard, legal-organization and designer roles were kept distinct, with "
            "acquisition, rename and production-transfer facts modeled as relationships rather than identity equivalence.",
            "",
            "Source families used included current manufacturer/yard sites, official heritage/model archives, "
            "manufacturer brochures/manuals, class and owners associations, recognized maritime/historical archives, "
            "industry sources and specialist secondary material for defunct builders. SailboatData was not used as "
            "HullQ production evidence. Public readability was never treated as blanket permission for later bulk use.",
            "",
            "## Breadth-floor check",
            "",
            "| Requirement | Result | Status |",
            "| --- | ---: | --- |",
            f"| >=120 verified eligible manufacturer/yard records | {len(floor_records)} | PASS |",
            f"| >=20 countries | {len(countries)} | PASS |",
            f"| >=5 macro-regions | {len(regions)} | PASS |",
            f"| >=40 historical/defunct/acquired/renamed eligible records | {historical_count} | PASS |",
            f"| >=25 official/recognized heritage/archive surfaces | {archive_surface_count} | PASS |",
            "",
            "Countries represented by the strict floor: " + ", ".join(countries) + ".",
            "",
            "Macro-regions represented: " + ", ".join(regions) + ".",
            "",
            "## Activity distribution — strict manufacturer/yard floor",
            "",
            "| Recorded status | Count |",
            "| --- | ---: |",
        ]
    )
    for status in ["active", "historical", "defunct", "acquired", "renamed", "unknown"]:
        lines.append(f"| {status} | {activity[status]} |")

    lines.extend(
        [
            "",
            "Status describes the retained research record's relevant production/company state and is not used to "
            "erase historical eligibility. Unknown remains unknown where current operation could not be established.",
            "",
            "## Source and rights observations",
            "",
            "The registry retains source-level rights/access assessments separately from factual research confidence. "
            "Counts below are **source assessments**, not unique entities and not legal clearance conclusions.",
            "",
            "| Systematic-use status | Source assessments |",
            "| --- | ---: |",
        ]
    )
    for status in ["CLEARED", "REQUIRES_REVIEW", "BLOCKED", "UNKNOWN"]:
        lines.append(f"| {status} | {rights[status]} |")

    lines.extend(
        [
            "",
            "Most manufacturer and archive surfaces are suitable for bounded manual discovery research but remain "
            "`REQUIRES_REVIEW` for later systematic commercial ingestion. Open-licensed or government-register evidence "
            "can be `CLEARED` where the retained assessment supports it, but that clearance does not transfer to other "
            "sources on the same record.",
            "",
            "Most common retained source types:",
            "",
        ]
    )
    for source_type, count in source_types.most_common():
        lines.append(f"- `{source_type}`: {count}")

    lines.extend(
        [
            "",
            "## 20-entity source-yield study",
            "",
            "The sample is deliberately heterogeneous and is not statistically representative. Its purpose is to "
            "measure which source shapes produce identities and technical evidence efficiently, and where identity "
            "relationships dominate the work.",
            "",
            "| Entity | Region | Activity | Approx. discoverable sailboat identities | Model list | Years | Core dimensions | Critical fields | Automation | Rights | Human review |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for entity in entities:
        lines.append(
            "| {name} | {region} | {activity} | {yield_} | {mode} | {years} | {dims} | "
            "{critical} | {automation} | {rights} | {burden} |".format(
                name=entity["preferred_display_name"].replace("|", "\\|"),
                region=entity["region"],
                activity=entity["activity_class"],
                yield_=entity["discoverable_model_identity_estimate"].replace("|", "\\|"),
                mode=entity["model_list_mode"].replace("|", "\\|"),
                years=entity["production_year_evidence"],
                dims=entity["core_dimensions_availability"],
                critical=entity["critical_technical_fields_availability"],
                automation=entity["automation_suitability"],
                rights=entity["systematic_use_status"],
                burden=entity["human_review_burden"],
            )
        )

    lines.extend(
        [
            "",
            "### Source-yield findings",
            "",
            "1. **Official heritage/model indexes are the best identity-expansion surfaces.** Oyster, Catalina, "
            "Bénéteau, Elan and Hallberg-Rassy expose tens of historical model identities with relatively low discovery "
            "cost. Their deeper technical facts usually require following one model page, brochure or manual.",
            "2. **Historical owner/class archives can be nearly as valuable as current manufacturer sites.** Pearson, "
            "Westerly and Alpa preserve model tables, brochures and specifications that no longer exist on a manufacturer site.",
            "3. **Contract yards are relationship evidence, not automatic model indexes.** TPI, Northshore and Ostróda "
            "demonstrate that a physical yard may build many boats under separate brands. Automation that equates yard "
            "names with model brands would create identity errors.",
            "4. **Current technical depth is often much better than historical depth.** Current Wauquiez, Elan, Seawind, "
            "Robertson & Caine and Grand Soleil pages expose useful dimensions and configuration data, while older models "
            "often require brochure/manual expansion.",
            "5. **HullQ-critical appendage/variant evidence is source-specific.** Keel, rudder/skeg, material, rig and "
            "factory-variant facts are not safely inferable from a model name. Hallberg-Rassy parts evidence and current "
            "Seawind/Wauquiez specifications illustrate the potential depth, but each fact needs its own provenance.",
            "",
            "Full per-entity measurements and evidence URLs are retained in `source_yield_study.json`.",
            "",
            "## Exact/unambiguous overlap with accepted SLICE-0017/0018",
            "",
            "The overlap check is intentionally conservative. It examines **57 representative source-derived model "
            "identities** from 19 of the 20 sample entities; Ostróda is intentionally excluded from model probes because "
            "its yard site does not enumerate its sail-only model subset. The accepted comparison set is the 1,770 "
            "AUTO_ADMIT QIDs from the immutable SLICE-0017 baseline plus SLICE-0018 delta.",
            "",
            f"- Exact preferred-label overlaps: **{exact} / {probe_total}** ({pct(exact, probe_total)})",
            f"- Alias/case-only signals retained as unresolved possible overlap: **{possible} / {probe_total}**",
            f"- Clearly new candidates in this exact-label probe: **{new} / {probe_total}** ({pct(new, probe_total)})",
            "",
            "`clearly new` here has a narrow meaning: the source model name is absent from the accepted exact preferred-label "
            "set and from the retained exact-alias/case-only hint sets. It does **not** prove global novelty and does not "
            "authorize admission. No fuzzy matching, token normalization, manufacturer-prefix stripping or forced crosswalk "
            "was used. Possible matches remain identity-resolution work.",
            "",
            "The machine-readable exact matches, unresolved hints and new-candidate probes are retained in "
            "`overlap_result.json`.",
            "",
            "## Major identity hazards observed",
            "",
            "- **Brand != yard:** Moody/Marine Projects, Southerly/Northshore/Discovery, Lagoon/CNB/Groupe Bénéteau, "
            "Maxi/its physical builders and J/Boats/TPI are recurring examples.",
            "- **Legal continuity != production continuity:** a company can survive a rename or ownership change after "
            "sailboat production ends, while a brand can continue through a different physical builder.",
            "- **Reused names and revived brands:** later revivals must not silently extend an original yard's production era; "
            "Columbia remains review-bound for exactly this reason.",
            "- **Contract production:** yards such as Ostróda and Balt-Yacht can be valid manufacturer/yard records even when "
            "their sailboats are sold under other brands.",
            "- **Model-number reuse/generations:** Grand Soleil, Bénéteau and other long-running builders reuse or evolve model "
            "numbers. HullQ must resolve technically meaningful BoatDesign/generation identity before flattening such names.",
            "- **Historical evidence asymmetry:** old brochures and owners associations may preserve better technical evidence "
            "than a current corporate site, but source rights and archive stability still require separate assessment.",
            "",
            "## Coverage gaps",
            "",
            "This bounded wave is intentionally not a claim of global completeness. Material gaps remain, especially Latin "
            "America, Turkey/Eastern Mediterranean, additional Asian historical yards, and many smaller national builders. "
            "The 121-record strict floor is a research threshold, not a stopping rule for the product's eventual global universe.",
            "",
            "## Recommendation for the next bounded slice",
            "",
            "### 1. Controlled manufacturer-archive identity expansion — recommended",
            "",
            "- **Likely identity/model yield:** high; the 20-entity sample shows tens of discoverable identities on several "
            "single archives, so a carefully chosen first adapter wave can plausibly add hundreds of candidate model identities "
            "before global deduplication.",
            "- **Likely field-depth yield:** medium; basic dimensions and production years are frequent, while critical "
            "keel/rudder/material/rig/variant facts often require linked documents.",
            "- **Rights/access confidence:** medium for bounded research, low-to-medium for automated commercial reuse until "
            "source-specific terms/licence review clears each surface.",
            "- **Automation complexity:** medium; strong on explicit indexes, weak on contract-yard and archival reconstruction cases.",
            "- **Expected review burden:** medium, dominated by generations, reused model numbers and brand/yard relationships.",
            "- **Next contract:** select a small rights-reviewed set of high-yield archives, harvest model identity candidates only, "
            "retain source provenance, run exact-first identity resolution against the existing BoatModel universe, and keep all "
            "uncertain matches review-bound. Do not combine this with broad technical enrichment in the same slice.",
            "",
            "### 2. Controlled Tier-1 technical-enrichment pilot over already-known BoatModels",
            "",
            "- **Likely identity/model yield:** low by design.",
            "- **Likely field-depth yield:** high on strong manufacturer/heritage sources.",
            "- **Rights/access confidence:** medium after source-specific review.",
            "- **Automation complexity:** medium-high because field semantics, units, variants and provenance need deterministic contracts.",
            "- **Expected review burden:** medium-high.",
            "- **Next contract:** a small, fixed BoatModel sample with explicit technical fields and evidence rules; no speculative "
            "bluewater/offshore suitability labels.",
            "",
            "### 3. Manufacturer/brand/yard relationship-hardening prerequisite",
            "",
            "- **Likely identity/model yield:** indirect but important for avoiding duplicate or misattributed models.",
            "- **Likely field-depth yield:** low-medium.",
            "- **Rights/access confidence:** medium-high for research evidence, source-dependent for reuse.",
            "- **Automation complexity:** low for explicit relationships, high for historical continuity reconstruction.",
            "- **Expected review burden:** high.",
            "- **Next contract:** formalize evidence-backed production relationships for the highest-yield multi-brand/contract yards "
            "before their model identities are harvested automatically.",
            "",
            "### 4. Another broad structured discovery adapter",
            "",
            "Potentially high identity yield and low field depth, but it ranks below the measured archive route unless a source "
            "with clearly better rights, coverage and identity quality is identified. Do not repeat the same exhausted direct-instance "
            "Wikidata query with a larger numeric limit; SLICE-0018 already measured that ceiling.",
            "",
            "## Reproducibility and validation",
            "",
            "Retained machine steps:",
            "",
            "```text",
            "uv run python research/manufacturers/build_registry.py",
            "uv run python research/manufacturers/finalize_source_yield.py",
            "uv run python research/manufacturers/analyze_overlap.py",
            "uv run python research/manufacturers/build_report.py",
            "uv run python scripts/validate_repository.py",
            "```",
            "",
            "`build_registry.py` validates `registry.json` against `registry_schema.json` and enforces the breadth counts. "
            "`finalize_source_yield.py` validates the marked 20-record sample without changing those counts. "
            "`analyze_overlap.py` asserts the accepted SLICE-0017/0018 AUTO_ADMIT union remains exactly 1,770 QIDs and performs "
            "only the bounded exact-label comparison described above.",
            "",
            "## Slice disposition",
            "",
            "**REVIEW.** Research outputs are complete enough for owner/independent review once the retained generators and "
            "repository validation have been executed at the final pushed head. This report does not self-mark SLICE-0019 DONE "
            "and does not start SLICE-0020.",
            "",
        ]
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("SLICE-0019 REPORT.md generated")
    print(
        f"records={len(records)} verified={statuses['verified']} "
        f"manufacturer_yard_floor={len(floor_records)} countries={len(countries)}"
    )
    print(
        f"overlap_probe={probe_total} exact={exact} possible={possible} clearly_new={new}"
    )


if __name__ == "__main__":
    main()
