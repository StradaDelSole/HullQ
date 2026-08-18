# SLICE-0002 — Canonical Logical Data Model Research

**Type:** DESIGN_RESEARCH  
**Status:** BACKLOG  
**Stage:** 1.6 / pre-Stage-2 implementation gate  
**Depends on:** SLICE-0001  
**Blocks:** SLICE-0003 and all HullQ domain implementation  
**Primary decision:** OQ-019

## Objective

Produce and accept one persistence-neutral canonical logical data model for HullQ before domain code is written.

The model must consolidate the currently distributed identity, design/configuration, provenance, research, derived-metric and dataset concepts into one coherent relationship/lifecycle model while recording the access patterns and invariants that a later physical database/search-technology decision must support.

## Why this slice exists

HullQ already has strong individual contracts, but they are distributed across multiple specs. Implementing Python classes or persistence adapters before consolidating entity boundaries, relationships, ownership, versioning and temporal semantics would risk encoding accidental database assumptions into code.

This slice answers **what the data means and how it relates**. It deliberately does **not** answer which database product stores it in production.

## Controlling artifacts

At minimum:

- `specs/IDENTITY_MODEL.v0.1.md`
- `specs/BOAT_MODEL_SCHEMA.v0.1.json`
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json`
- `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json`
- `specs/SOURCE_SCHEMA.v0.2.json`
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- `specs/PROVENANCE_MODEL.v0.1.md`
- `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json`
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json`
- `specs/DERIVED_METRICS_SPEC.v1.0.md`
- `specs/DERIVED_METRICS_SCHEMA.v1.0.json`
- `research/RESEARCH_WORKFLOW.md`
- `docs/DATABASE_COVERAGE_STRATEGY.md`
- `docs/DATA_STRATEGY.md`
- ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0008
- `docs/PRODUCT_RETENTION_AND_MONETIZATION.md` for future query/monitor boundaries only
- `docs/governance/OPEN_QUESTIONS.md`

## Research questions

### Canonical entity inventory

Identify and define the role of every first-class entity required by accepted contracts, including at least:

- BoatModel;
- BoatDesign;
- NamedVariant where applicable;
- DesignOption;
- ResolvedConfiguration;
- Source;
- FieldEvidence;
- FieldResolution;
- DerivationRecord;
- ResearchJob;
- raw research artifact/reference;
- dataset/release/version metadata;
- derived-metric result;
- any required manufacturer/builder/designer identity concept if current contracts cannot represent it cleanly.

Future product concepts such as SavedQuery, Monitor, Alert, market listing/observation and SubscriptionEntitlement SHOULD be represented only far enough to ensure domain separation and future compatibility; their unresolved semantics remain governed by later OQs.

### Relationships and cardinality

Define explicit cardinalities and ownership/reference direction, e.g. model → designs, design → options, configuration → selected options, evidence → source/subject/field, resolution → evidence, derivation → inputs/method/output.

Avoid array-position identity. Stable identifiers must identify entities independently of serialization order.

### Lifecycle and mutability

For each entity classify:

- mutable canonical state;
- immutable evidence/artifact;
- versioned decision/history;
- derived/recomputable output;
- temporal observation;
- soft-delete/archive expectations where necessary.

Do not collapse immutable evidence into mutable canonical values.

### Domain boundaries

At minimum assess separation between:

1. canonical design universe;
2. research/evidence/provenance;
3. derived calculations;
4. dataset/version/release metadata;
5. market observation/listing layer;
6. user query/monitor/alert layer.

The model must preserve the existing rule that marketplace/property/user-preference data cannot silently mutate canonical technical design truth.

### Access patterns

Record the data-access patterns that the later OQ-012 technology decision must support, including:

- broad technical filtering across thousands of designs;
- resolving model → generation → configuration/options;
- design detail retrieval;
- provenance/source audit for one field;
- "which canonical values depend on source X?" impact analysis;
- research reprocessing/re-resolution;
- derived-metric recomputation by method version;
- dataset snapshot/reproducibility;
- later listing-to-design identity resolution;
- later saved-query/monitor evaluation.

### Scale assumptions

Document order-of-magnitude design goals rather than fake precision:

- 5,000–10,000+ BoatDesign identities as a realistic broad-universe direction;
- potentially many evidence records per design/field over time;
- many resolved configurations without forcing Cartesian materialization of every theoretical option combination;
- future market observations potentially much higher-volume and more temporal than canonical design records.

These assumptions inform OQ-012 but do not choose technology here.

## Deliverables

- `docs/research/OQ-019_CANONICAL_DATA_MODEL_RESEARCH.md`
- `architecture/CANONICAL_DATA_MODEL.v0.1-DRAFT.md`
- a Mermaid or equivalent textual entity/relationship diagram inside the architecture document;
- explicit mapping from logical entities to current schemas/specs;
- identified gaps/conflicts, with new OQ/ADR proposals only where a real unresolved decision exists;
- update OQ-019 to `READY_FOR_DECISION` after research, then `DECIDED` only after explicit user acceptance;
- update `docs/slices/INDEX.md` and `docs/PROJECT_STATE.md` after acceptance.

## Explicitly out of scope

Do not select or implement:

- PostgreSQL;
- SQLite as production persistence;
- Elasticsearch/OpenSearch;
- a document database;
- vector database;
- ORM/query builder;
- migration framework;
- production indexes;
- caching architecture;
- backend framework;
- API format;
- market price-history retention semantics.

Those belong to OQ-012, OQ-011, OQ-015, OQ-017 or later implementation gates.

## Acceptance criteria

- [ ] every accepted Stage-1 canonical/provenance/derived entity is represented or explicitly mapped as an embedded value object;
- [ ] relationships/cardinalities are explicit;
- [ ] stable identity does not depend on array position or display slug;
- [ ] immutable evidence, mutable canonical state and recomputable derived state remain distinct;
- [ ] BoatDesign baseline, NamedVariant/DesignOption and ResolvedConfiguration semantics remain consistent with ADR-0004;
- [ ] field-level provenance remains compatible with ADR-0006 and RFC-6901 field addressing;
- [ ] source-rights restrictions can be traced to affected evidence/values;
- [ ] derived results retain method/input lineage;
- [ ] unknown/missing data remains representable without becoming false;
- [ ] access patterns needed for later technical search are documented;
- [ ] scale assumptions are documented as ranges/orders of magnitude;
- [ ] no production database technology is selected by accident;
- [ ] unresolved contradictions become explicit decision items rather than implementation guesses.

## Stop conditions

Stop and surface the issue if current accepted contracts imply contradictory entity ownership, identity, lifecycle or provenance semantics.

Do not resolve a conflict merely by choosing whichever shape is easiest to code or easiest for a particular database.

## Required completion report

Report:

- entity inventory;
- relationship model;
- lifecycle/mutability classifications;
- access patterns;
- contract gaps or contradictions;
- whether a new ADR/OQ is required;
- explicit confirmation that physical DB technology remains undecided under OQ-012.

Do not automatically begin SLICE-0003.
