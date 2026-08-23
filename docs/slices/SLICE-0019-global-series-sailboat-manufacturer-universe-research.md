# SLICE-0019 — Global Series-Sailboat Manufacturer/Yard Universe Research

**ID:** SLICE-0019  
**Type:** DESIGN_RESEARCH  
**Status:** REVIEW — research execution complete and merged to `main`; not yet owner-accepted. An independent-review amendment may exist on its own branch to correct findings without broadening scope. Not `DONE`; does not authorize SLICE-0020.
**Stage:** 3.2–3.3 — post-Wikidata breadth strategy / source-yield research  
**Depends on:** SLICE-0018 accepted / DONE  
**Blocks:** the next bounded identity-expansion and/or technical-enrichment slice

## Why this slice exists

SLICE-0018 established a measured fact: the accepted direct-instance Wikidata sailboat-class discovery path returned **1,829** unique QIDs under a requested limit of 2,500. The accepted combined Tier-0 graph contains **1,770** sparse canonical BoatModels. Simply raising the same query limit is therefore not an evidence-based route toward HullQ's intended 5,000–10,000+ design universe.

The existing data strategy already expects multiple identity sources plus progressive primary-source enrichment. Manufacturer/yard model indexes, heritage archives, brochures, manuals, designer archives and recognized historical sources are the strongest observed next source family.

Before another ingestion implementation is authorized, HullQ needs a structured global map of the **series-sailboat manufacturers/yards themselves**, including historical/defunct entities, and measured evidence about which source surfaces can safely and efficiently yield additional model identities and technical facts.

## Objective

Build the **first bounded global research wave** of a series-sailboat manufacturer/yard universe — active and historical — and measure the next viable source paths for HullQ identity expansion and technical enrichment.

This is a research/source-mapping slice. It does **not** create canonical Brand, Organization, BoatModel or BoatDesign rows and does not ingest a new production dataset.

The long-term coverage direction is global. This slice is deliberately not an attempt to finish the complete global manufacturer universe in one Claude session.

## Core semantic rule

The research must preserve the distinction:

```text
manufacturer / yard
        !=
brand
        !=
legal organization
        !=
designer / naval architect
        !=
model / BoatModel
        !=
BoatDesign
```

A yard may build boats sold under another brand. A brand may have multiple builders over time. A legal organization may own a brand without building boats itself. Acquisition, renaming, brand transfer and production transfer are relationships, not automatic identity equivalence.

No record may collapse those concepts merely because a website or secondary source uses the words loosely.

## Scope

### Included

Research entities that have evidence of producing or marketing **series / production sailing boats** relevant to HullQ, including:

- active manufacturers and yards;
- historical / defunct manufacturers and yards;
- acquired or renamed manufacturers;
- brands whose production relationship to one or more yards is materially relevant;
- monohull and multihull production builders;
- large-volume and small specialist production builders;
- manufacturers whose useful evidence survives mainly in archives, owner/class associations, museums, designer archives or historic brochures.

Historical entities are first-class. HullQ's useful market/design universe is not limited to companies that still exist.

### Excluded unless needed as relationship context

- pure brokers/dealers;
- charter operators;
- marinas;
- designers/naval architects that never manufactured/marketed a series boat;
- one-off custom builders with no demonstrated series/production model line;
- powerboat-only manufacturers;
- generic component suppliers;
- marketplace/listing sites as production-value sources;
- subjective categories such as `bluewater builder`, `offshore builder`, `luxury builder` or similar suitability/marketing classifications.

## Coverage target vs completeness claim

The long-term product target is global coverage. **SLICE-0019 must not claim that this bounded research wave has found every manufacturer.**

The retained outputs must explicitly distinguish:

- `discovered`;
- `eligible`;
- `verified`;
- `needs_review`;
- `excluded`;
- `coverage_gap`.

The phrase `global manufacturer universe` describes the coverage direction, not a completeness guarantee.

## Research approach

Use independent, broad web research with source-specific provenance. Prefer direct/authoritative evidence but use reputable archival/secondary sources when historical companies no longer maintain official material.

Useful source families include:

1. current manufacturer/yard websites and model indexes;
2. official heritage / previous-model archives;
3. original brochures, manuals and catalogues;
4. designer/naval-architect archives where they document builder/model relationships;
5. class/owner associations preserving original documents;
6. museums, recognized maritime archives and historical company sources;
7. national/international industry associations or directories for discovery leads;
8. Wikidata/open structured data as discovery/cross-check input;
9. web archives where source provenance and capture date are retained;
10. reputable specialist sources for historical gaps, clearly marked secondary.

Commercial/community boat databases, marketplaces and mixed-rights datasets may be used only as **discovery leads or post-hoc cross-checks** unless their use is separately cleared under HullQ's source-rights policy. SailboatData remains reference-only under the existing project rule.

Public readability does not imply bulk-production clearance.

## Rights and access discipline

For every source surface that may be recommended for later automated use, record separately:

- operator / source identity;
- URL / access path;
- source type;
- public/manual access status;
- robots/API/download situation where material;
- licence / terms evidence where identifiable;
- whether discovery use is acceptable for this research slice;
- whether later systematic/bulk commercial ingestion appears `CLEARED`, `REQUIRES_REVIEW`, `BLOCKED` or `UNKNOWN` under the accepted HullQ rights model;
- review date.

This slice may research publicly accessible material, but it **must not convert research access into blanket authorization for future bulk ingestion**.

## Required retained outputs

Create a dedicated retained package:

```text
research/manufacturers/
    registry_schema.json
    registry.json
    REPORT.md
```

Additional small supporting files are allowed only if they make provenance/reproducibility materially clearer.

### `registry_schema.json`

A strict schema for the research registry. The schema must make non-canonical research status explicit and must not reuse canonical HullQ entity IDs as if this research had already resolved identity.

### `registry.json`

Each verified/review candidate should retain enough structure to support later source/identity work, including where evidence exists:

- stable research-record identifier;
- preferred research display name;
- aliases / former names;
- entity kind or role evidence (`manufacturer`, `yard`, `brand` relationship context, etc.);
- country / region evidence;
- active / historical / defunct / acquired / renamed / unknown status;
- approximate or evidenced production era;
- related-name relationships such as `predecessor`, `successor`, `acquired_by`, `formerly_known_as`, `brand_owned_by`, `production_transferred_to` or equivalent explicit relation vocabulary;
- evidence that the entity actually produced/marketed series sailing boats;
- official current site if one exists;
- official heritage/archive/model-index surface if one exists;
- other authoritative/recognized archive surfaces;
- source references and retrieval dates;
- rights/access assessment for later systematic use;
- exact or explicitly estimated model-yield information where supportable;
- review status / ambiguity notes.

Do not invent dates, ownership chains, model counts or relationships. Unknown remains unknown.

### `REPORT.md`

The report must summarize at least:

- discovery methodology and source families used;
- total records discovered / eligible / verified / review-bound / excluded;
- active vs historical/defunct/acquired distribution;
- country and geographic coverage;
- sources with official current model indexes;
- sources with official heritage/previous-model archives;
- sources where only recognized secondary/archival evidence survives;
- rights/access distribution for possible later automation;
- estimated/exact model-yield evidence by source family;
- major identity hazards observed (brand vs yard, acquisitions, transferred production, reused names, etc.);
- notable geographic/historical coverage gaps;
- a measured recommendation for the **next bounded slice**, without starting it.

## Bounded breadth target

This is a **first global research wave**, not an unbounded collection exercise.

Target a retained registry of approximately **120–160 verified eligible manufacturer/yard research records**. The slice should stop expanding the count once the minimum evidence/coverage floors and source-yield study below are satisfied; it must not continue toward 250, 500 or “all manufacturers” merely to maximize the number.

Minimum floors:

- **>=120 verified eligible manufacturer/yard research records**;
- **>=20 countries** represented;
- coverage across at least **5 geographic macro-regions**;
- **>=40 historical/defunct/acquired/renamed** eligible records;
- **>=25** entities with a verified official or recognized model/heritage archive surface.

These are breadth floors, not permission to lower evidence quality. If a floor cannot be reached with defensible evidence during the bounded slice, retain the actual result and return `BLOCKED` or `REVIEW` with the precise gap rather than fabricating or padding entries.

If a high-quality discovery source yields more than 160 eligible names cheaply, additional candidates may be retained as `discovered` leads, but deep verification beyond the bounded verified wave is not required by this slice.

## Source-yield study

From the verified registry, select a deliberately varied **20-entity source-yield sample** covering:

- active and historical manufacturers;
- high-volume and specialist builders;
- multiple regions;
- monohull and multihull production;
- strong official archives and difficult archival-only cases.

For each sampled entity measure, where supportable:

- approximate number of discoverable production sailboat model identities;
- whether the model list is explicit or reconstructed;
- availability of first-built / production-year evidence;
- availability of LOA/LWL/beam/draft/displacement;
- availability of HullQ-critical keel/rudder/skeg/material/rig/variant evidence;
- whether useful evidence lives on one page or requires linked brochure/manual/archive expansion;
- source volatility;
- automation suitability;
- rights/access status for later systematic use;
- expected human-review burden.

The sample is for source-strategy measurement, not population-statistical inference.

## Cross-check against accepted HullQ state

Where exact source identifiers or unambiguous exact identities make comparison safe, measure overlap with the accepted SLICE-0017/0018 universe.

Do **not** force fuzzy mappings merely to produce an overlap percentage. Report:

- exact/unambiguous overlap found;
- clearly new candidate-model yield;
- unresolved possible overlap;
- cases requiring later identity resolution.

No accepted HullQ ID may be changed, reminted, merged or deleted in this slice.

## Required decision output

The report must end with a ranked evidence-based recommendation among concrete next-step patterns such as:

- another rights-cleared structured identity source / discovery adapter;
- controlled manufacturer-archive identity expansion;
- controlled Tier-1 technical enrichment pilot over existing BoatModels;
- a prerequisite identity/relationship hardening slice;
- no-go / further rights research where the attractive source path is not reusable.

For each recommended path state:

- likely identity/model yield;
- likely field-depth yield;
- rights/access confidence;
- automation complexity;
- expected review burden;
- what exact contract should be bounded next.

Do not start that next slice automatically.

## Acceptance criteria

SLICE-0019 is acceptance-ready only when all of the following are true:

1. the retained package validates against its own committed schema;
2. manufacturer/yard/brand/organization/designer semantics are not silently collapsed;
3. active and historical manufacturers are both materially represented;
4. every verified registry record has at least one source supporting series-sailboat eligibility;
5. relationships such as acquisition/renaming/production transfer are evidence-backed or explicitly unknown;
6. source references and retrieval dates are retained;
7. later systematic-use rights/access are assessed separately from mere public readability;
8. the bounded minimum breadth floors are met, or the slice explicitly reports the unmet floor without padding;
9. the 20-entity source-yield study is complete and reproducible from cited evidence;
10. overlap with existing HullQ identities is exact/unambiguous only — no forced fuzzy crosswalk;
11. no production canonical entity rows or IDs are created/modified;
12. no SailboatData value is used as HullQ production evidence;
13. no subjective `bluewater`/offshore/luxury suitability classification is introduced;
14. the report gives a bounded, evidence-based next-slice recommendation;
15. repository validation / formatting / tests applicable to retained structured artifacts pass;
16. the agent returns SLICE-0019 in `REVIEW`, `BLOCKED` or `IN_PROGRESS`, never self-marks it `DONE` and never starts SLICE-0020.

## Explicit non-goals

SLICE-0019 does **not** authorize:

- completing the entire global manufacturer universe in one slice;
- canonical Brand/Organization creation;
- canonical BoatModel/BoatDesign admission;
- remapping or resolving the accepted SLICE-0017/0018 review queues;
- a 5,000 Wikidata rerun;
- recursive Wikidata subclass expansion unless needed only as research evidence and clearly separated from production authorization;
- bulk ingestion from manufacturer sites;
- broad Tier-1/Tier-2 field enrichment;
- query-engine implementation;
- API/frontend work;
- marketplace/dealer integration;
- accounts, alerts, monitoring or price-history work;
- a powerboat manufacturer universe;
- automatic transition to the next slice.

## Agent execution note

Run this slice through the normal isolated worktree workflow. The research agent may use web research necessary to complete the evidence package, subject to the rights/access rules above. Preserve exact source URLs and retrieval dates. Prefer quality and traceability over superficially maximizing record count.

The completion report must state the exact pushed HEAD SHA, changed files, validation/tests, registry counts, breadth-floor results, 20-entity yield-study summary, rights/access findings, unresolved gaps and the recommended next bounded slice.