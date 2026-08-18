# SLICE-0002 — Design Data Source Research & Seed Corpus

**Type:** DESIGN_RESEARCH  
**Status:** DONE  
**Stage:** 1.6 / pre-domain-implementation evidence gate  
**Depends on:** SLICE-0001  
**Blocks:** none after acceptance; SLICE-0003 is now READY  

## Objective

Research the **actual independent sailboat-design data sources** HullQ can use instead of treating SailboatData as a production database, and build a small manually verified evidence corpus that exposes the real source shapes, gaps, conflicts, rights constraints and normalization problems before pipeline code is written.

This slice is about the **boat data itself** and where it comes from. It is not a database-technology or ORM-design exercise.

## Why this slice exists

HullQ cannot safely design a research pipeline around hypothetical inputs. Before writing extraction/normalization code, the project needs evidence for questions such as:

- Which independent sources can provide broad model/design identity coverage?
- Which sources contain LOA/LWL/beam/draft/displacement/ballast/sail area?
- Where can HullQ obtain keel, rudder, skeg, rig and construction details?
- How often do official sources distinguish generations and factory options?
- Which fields are commonly missing or semantically ambiguous?
- Which sources are suitable for bulk/bootstrap use and which are only suitable for individual factual verification?
- What source conflicts and unit/definition differences actually occur in real boats?

The goal is to let real evidence shape the pipeline rather than building the pipeline first and forcing sources into it later.

## Controlling artifacts

- `docs/DATA_STRATEGY.md`
- `docs/DATABASE_COVERAGE_STRATEGY.md`
- `research/RESEARCH_WORKFLOW.md`
- `research/RESEARCH_PILOT.md`
- `research/evidence/SOURCE_REGISTER.md`
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- `specs/SOURCE_SCHEMA.v0.2.json`
- `specs/IDENTITY_MODEL.v0.1.md`
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json`
- `specs/PROVENANCE_MODEL.v0.1.md`
- ADR-0003, ADR-0004, ADR-0005, ADR-0006

## Source classes researched

### A. Open structured bootstrap candidates

The research evaluated sources that may legally and technically seed broad identity/common-field coverage.

The strongest current candidate is:

- **Wikidata structured data (CC0)** — suitable as a broad identity/common-field bootstrap candidate, subject to normal HullQ provenance, quality and access controls. CC0 status does not imply factual correctness.

### B. Primary factual verification sources

Manufacturer/builder/designer/official-association sources were researched, including:

- current and heritage model pages;
- archived brochures and specification PDFs;
- owner manuals;
- official class association technical documents;
- designer/builder archives;
- official heritage systems that reveal generation/build-number/configuration changes.

These can be excellent evidence for individual technical facts while still requiring separate bulk-access/redistribution clearance under ADR-0005.

### C. Licensed/open secondary sources

Secondary datasets/pages were considered only where license and obligations were explicit. Share-alike or mixed-license material remains quarantined from bulk merge unless the accepted Source Rights Policy permits the specific use.

### D. Reference-only / blocked sources

- SailboatData scrape/reference materials remain useful for taxonomy, edge cases and candidate leads, but are not an invisible production-value source.
- ORC was found technically valuable but blocked for systematic HullQ commercial ingestion under current published terms absent separate permission/licence.
- Commercial/community databases without sufficient rights clearance remain research leads/comparison references only according to their Source clearance.

## Research completed

### 1. Source landscape

Serious candidates were recorded with source/operator, source class, access method, coverage/breadth, fields, identity/configuration usefulness, rights/access constraints, HullQ clearance, provenance quality and automation/review notes.

See `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md` and `research/evidence/SOURCE_REGISTER.md`.

### 2. Field-source coverage matrix

HullQ-critical fields were mapped against observed source availability, including identity, dimensions, displacement/ballast/sail-area bases, hull/keel/rudder/skeg/rig, construction and option-sensitive values.

See `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`.

### 3. Representative real-boat seed research

A 20-design core sample plus one targeted partial-skeg/reused-name supplement was researched across monohull/catamaran/trimaran, older/modern, large/small/defunct builders, generation ambiguity, multiple appendage forms, option-sensitive configurations, strong/weak documentation and conflicting source evidence.

See:

- `research/benchmark/SEED_RESEARCH_NOTES.md`;
- `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md`.

### 4. Broad-universe bootstrap feasibility

The research established a plausible four-digit open seed path through Wikidata. Historical/current comparison evidence supports planning around roughly 1,000–1,500 sailboat-class/production-sailboat candidates as an order-of-magnitude bootstrap range, not as a frozen live count.

The exact live direct-instance count and field-completeness snapshot should be measured reproducibly by the later Wikidata adapter rather than hard-coded into a specification.

### 5. Pipeline requirements derived from real evidence

The sample proved the later implementation must support at least:

- structured Wikidata/RDF/API-style statements and qualifiers;
- manufacturer HTML specification tables;
- linked brochure/manual/PDF evidence;
- mixed metric/imperial units;
- source-semantic mass and sail-area bases;
- multiple concurrent factory configurations/options;
- generation boundaries expressed by year/hull number/prose;
- source conflicts and explicit unknowns;
- appendage relationships beyond one flat taxonomy field;
- manual/diagram review for some rudder/skeg/construction cases;
- provenance from accepted canonical values to exact source observations.

No implementation of these capabilities was performed in this slice.

## Deliverables

- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`
- updated `research/evidence/SOURCE_REGISTER.md`
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`
- `research/benchmark/SEED_RESEARCH_NOTES.md`
- `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md`
- documented recommendation for broad identity bootstrap + deeper enrichment strategy
- evidence-derived implementation backlog in `docs/slices/INDEX.md`

## Acceptance criteria

- [x] at least one plausible broad identity-bootstrap path has been researched under the accepted source-rights model;
- [x] source candidates are classified by rights/access/clearance, not merely technical accessibility;
- [x] all HullQ-critical technical field groups are covered by the field-source matrix;
- [x] 20–30 representative real designs have been manually source-researched deeply enough to expose missing/conflicting/option-sensitive data behavior;
- [x] SailboatData is not used as an invisible production-value source;
- [x] actual observed source shapes and ambiguities are documented;
- [x] likely automated vs human-review work is estimated from evidence;
- [x] pipeline requirements are derived from the researched sample rather than invented in advance;
- [x] no domain implementation is introduced in this slice.

## Quantitative checkpoint from the researched sample

Across the 20-design core plus one targeted supplement:

- 18/21 exposed usable common specifications directly;
- 17/21 exposed usable keel/board architecture explicitly;
- 13/21 exposed rudder/support architecture explicitly enough to classify;
- 7/21 exposed skeg/skegless state explicitly;
- 8/21 had option-sensitive technical core values;
- 7/21 required multiple source surfaces;
- 2/21 already showed real source conflicts;
- 11/21 exposed materially different displacement/mass-basis semantics.

These numbers are seed evidence, not final production-quality estimates. The later 50–100-design benchmark must measure the actual automated-acceptance/review/cost distribution.

## Major findings

1. No single cleared source replaces SailboatData across breadth + HullQ-critical depth.
2. Wikidata is the strongest current broad CC0 bootstrap candidate, but deeper primary-source enrichment is required.
3. Manufacturer/official sources are high-value evidence but are not automatically bulk-reuse sources and are not automatically conflict-free.
4. Rudder/skeg/support relationships are significantly less available than common dimensions and will drive disproportionate review effort.
5. Option-sensitive values are common enough that one scalar technical record per commercial model would be incorrect.
6. Measurement labels such as lightship, half-load, measurement trim and other source-specific mass bases must survive normalization.
7. Real appendage combinations justify a dedicated implementation slice rather than one generic taxonomy mapper.
8. Source authority must remain evidence-based; even primary manufacturer material can contain internal contradictions.

## Acceptance evidence

- Independent review: **PASS** — repository research artifacts and the SLICE-0002 diff were independently reviewed on 2026-08-18; recommendation was `ACCEPT`.
- Required remote/external checks: **NOT APPLICABLE** to this research-only slice; no CI status is claimed as acceptance evidence.
- Project-owner acceptance: **ACCEPTED** explicitly by the user/project owner on 2026-08-18.
- Final state transition: `REVIEW → DONE` performed only after independent review and project-owner acceptance, consistent with `CLAUDE.md`.

## Completion report

### Slice

- Slice ID: `SLICE-0002`
- Final slice state: `DONE`
- Scope completed: `YES`

### Changes

- Changed files:
  - `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`
  - `research/evidence/SOURCE_REGISTER.md`
  - `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`
  - `research/benchmark/SEED_RESEARCH_NOTES.md`
  - `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md`
  - `docs/slices/INDEX.md`
  - this slice document
  - `docs/PROJECT_STATE.md`
- Requirements implemented or researched: evidence-first design-data acquisition requirements under accepted data strategy, identity, source-rights and provenance policy; no new production semantics introduced.
- Tests/fixtures added or updated: no executable tests; 20-design core evidence sample plus one targeted partial-skeg supplement added as research evidence.

### Validation

- Local validation: `NOT APPLICABLE`
- Commands run: none required for the documentation/research-only scope.
- Results: research artifacts were cross-checked against controlling source-rights/identity/provenance rules; no domain code changed.

### External verification

- Remote CI: `NOT APPLICABLE`
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings:
  - exact live Wikidata direct-instance count remains for the later rights-gated Wikidata adapter to measure reproducibly;
  - no single cleared source supplies broad identity plus HullQ-level rudder/skeg/configuration depth;
  - ORC remains blocked without separate permission/licence.
- Spec/ADR ambiguities: no blocking contradiction found. Existing identity, provenance and derived-input-basis decisions were reinforced by the source evidence.
- Scope deviations: one additional Seafarer 26 supplement was added beyond the 20-design core to explicitly cover partial-skeg + reused-model-name + defunct-builder behavior. No implementation work was started.

### Follow-up

- Accepted next action: `SLICE-0003 — Canonical JSON-Schema Contract Runtime` is now the only `READY` implementation slice.

### Agent declaration

The research agent handed this slice off at `REVIEW` and did not self-mark it `DONE`. Final acceptance was applied only after independent review and project-owner acceptance.
