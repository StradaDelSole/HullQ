# SLICE-0002 — Design Data Source Research & Seed Corpus

**Type:** DESIGN_RESEARCH  
**Status:** REVIEW  
**Stage:** 1.6 / pre-domain-implementation evidence gate  
**Depends on:** SLICE-0001  
**Blocks:** first HullQ domain implementation slices  

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

## Source classes to research

### A. Open structured bootstrap candidates

Research sources that may legally and technically seed broad identity/common-field coverage.

Current high-priority candidate:

- **Wikidata structured data (CC0)** — investigate sailboat-class coverage, identifiers, builders/designers, dimensions and reference quality. Treat individual statements as evidence requiring normal HullQ provenance/quality handling; CC0 status does not imply factual correctness.

Any additional open/licensed structured datasets discovered during this slice must be added to the Source Register with explicit rights/access/clearance assessment before use.

### B. Primary factual verification sources

Research manufacturer/builder/designer/official-association sources such as:

- current and heritage model pages;
- archived brochures and specification PDFs;
- owner manuals;
- official class association technical documents;
- designer/builder archives;
- official parts/heritage systems that reveal generation/build-number/configuration changes.

These can be excellent evidence for individual technical facts while still requiring separate bulk-access/redistribution clearance under ADR-0005.

### C. Licensed/open secondary sources

Research secondary datasets/pages only where license and obligations are explicit. Share-alike or mixed-license material must remain quarantined from bulk merge unless the accepted Source Rights Policy permits the specific use.

### D. Reference-only sources

- SailboatData scrape/reference materials may help identify taxonomy, edge cases and candidate models, but MUST NOT become an invisible production-value source.
- Commercial/community databases without sufficient rights clearance may be used as research leads or comparison references only according to their Source clearance.

## Required research work

### 1. Build the source landscape

For every serious candidate record at least:

- source name / operator;
- source type;
- current URL or access method;
- geographic/model coverage;
- approximate breadth where discoverable;
- fields available;
- identity/generation/option usefulness;
- update/archival characteristics;
- rights/license basis;
- access/TOS/automation constraints;
- HullQ clearance category under `SOURCE_RIGHTS_POLICY.v0.1.md`;
- provenance quality;
- expected automation difficulty;
- notes on known ambiguity/conflicts.

### 2. Produce a field-source coverage matrix

Map each HullQ-critical field to realistic source classes and observed availability:

- manufacturer / brand / model;
- BoatDesign generation;
- designer;
- builder;
- first/last built and number built where available;
- LOA / LWL / beam / draft;
- displacement / ballast / sail area with semantic basis where discoverable;
- hull configuration;
- keel type/subtype;
- rudder type;
- skeg type;
- rig;
- construction material/method;
- design options / shallow draft / tall rig / alternate rudder etc.;
- secondary cruising fields where present.

For every field, distinguish `commonly available`, `sometimes available`, `rare`, `requires inference/diagram review`, and `not realistically sourceable at scale` based on evidence rather than assumption.

### 3. Manually research representative real boats

Before writing the automated research pipeline, manually research enough difficult examples to expose real-world source problems.

Initial target: **20–30 representative BoatDesign candidates**, selected across:

- monohull / catamaran / trimaran;
- older / modern;
- large-volume manufacturer / small builder;
- clear identity / reused model name / generation ambiguity;
- fixed keel / centerboard / lifting keel / bilge/twin keel / daggerboard where available;
- spade / skeg / partial-skeg / keel-hung / twin rudder;
- multiple factory draft or rig options;
- strong official documentation / weak documentation;
- conflicting sources.

This is a discovery/evidence sample, not the final 50–100 benchmark and not the product database.

For each sample record capture:

- candidate canonical identity;
- source list;
- observed raw facts;
- conflicts/ambiguities;
- missing fields;
- fields requiring diagram/manual interpretation;
- source-rights classification;
- what an automated system could safely extract vs what likely needs review.

### 4. Test broad-universe bootstrap feasibility

Determine whether one or more cleared sources can provide a sufficiently broad identity queue without copying SailboatData production values.

The research must answer with evidence:

- approximate identity count obtainable from each candidate bootstrap source;
- duplicate/reused-name issues;
- builder/designer coverage;
- basic technical-field completeness;
- whether HullQ likely needs multiple bootstrap sources;
- what enrichment must come from primary-source research.

### 5. Derive pipeline requirements from evidence

Only after the manual source research, document the actual extraction/normalization capabilities the implementation must support, e.g.:

- structured JSON/RDF/API input;
- HTML tables/definition lists;
- PDFs/manuals;
- imperial/metric mixed units;
- ranges and alternate factory options;
- semantic ambiguity in displacement/sail-area basis;
- conflicting authoritative sources;
- diagram/image-assisted classification where unavoidable;
- explicit `unknown` and human-review paths.

Do not implement those capabilities in this slice.

## Deliverables

- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`
- updated `research/evidence/SOURCE_REGISTER.md`
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`
- `research/benchmark/SEED_RESEARCH_NOTES.md` containing the representative 20–30-design core research sample and source leads
- `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md` for the targeted partial-skeg/reused-name edge case
- documented recommendation for broad identity bootstrap + deeper enrichment strategy
- explicit list of pipeline capabilities learned from the real source sample
- updates to subsequent slice boundaries where the evidence requires them

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

## Stop conditions

Stop and surface a decision if:

- a proposed bootstrap source is legally/contractually unclear for the intended use;
- a source appears technically ideal but fails HullQ clearance under ADR-0005;
- a major required field appears infeasible to source reliably at useful scale;
- real source evidence contradicts an accepted domain/schema assumption.

Do not work around those findings silently.

## Status handoff rule

This slice is now handed to independent review. It MUST NOT be moved to `DONE` by the research agent. `DONE` requires the review/acceptance path defined in `CLAUDE.md`.

## Required completion report

### Slice

- Slice ID: `SLICE-0002`
- Recommended slice state: `REVIEW`
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
- Requirements implemented or researched: evidence-first design-data acquisition requirements under accepted data strategy, identity, source-rights and provenance policy; no new production semantics introduced.
- Tests/fixtures added or updated: no executable tests; 20-design core evidence sample plus one targeted partial-skeg supplement added as research evidence.

### Validation

- Local validation: `NOT APPLICABLE`
- Commands run: none required for this documentation/research-only slice.
- Results: research artifacts cross-checked against the controlling source-rights/identity/provenance rules; no domain code changed.

### External verification

- Remote CI: `NOT APPLICABLE` to slice acceptance; repository CI may still run on commits but no CI result is claimed here.
- Other external gates: `NOT APPLICABLE`; source reuse classifications remain governed by ADR-0005 and do not grant new permissions.

### Findings

- Unresolved findings:
  - Exact live Wikidata direct-instance count was not independently executed through WDQS in this research environment. Order-of-magnitude bootstrap feasibility is established by the official data model/query surface, a historical Wikimedia diagnostic count of 1,471 `Q106179098` items, and a current Wikidata-derived catalogue indexing 1,062 production sailboats. The future Wikidata adapter should record an exact reproducible live count and field-completeness snapshot.
  - No single cleared source provides both broad identity coverage and HullQ-level rudder/skeg/configuration depth; multi-layer enrichment is required.
  - ORC is technically attractive but remains blocked for HullQ systematic commercial ingestion without separate permission/licence.
- Spec/ADR ambiguities: no blocking contradiction found. The source evidence reinforces existing identity, provenance and derived-input-basis decisions. Appendage/configuration implementation scope was separated in the backlog because real evidence proved keel/rudder/skeg relationships cannot safely be treated as one flat taxonomy field.
- Scope deviations: one additional Seafarer 26 supplement was added beyond the 20-design core sample to explicitly cover partial-skeg + reused-model-name + defunct-builder behaviour. No implementation work was started.

### Follow-up

- Recommended next action: independent review and user/project-owner acceptance of SLICE-0002. If accepted, detail only `SLICE-0003` (canonical JSON-Schema contract runtime) and make it `READY`; do not begin later slices automatically.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The research agent has NOT marked this slice `DONE`.
