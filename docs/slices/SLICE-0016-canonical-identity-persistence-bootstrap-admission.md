# SLICE-0016 — Canonical Identity Persistence & Bootstrap Admission Boundary

**ID:** SLICE-0016  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 3.0 — canonical identity persistence prerequisite for controlled broad bootstrap  
**Depends on:** SLICE-0015 accepted / DONE / Stage-2 G3 PASS  
**Blocks:** controlled ~1,000-design identity bootstrap

## Objective

Implement the smallest production PostgreSQL boundary that can safely persist **already-admitted canonical HullQ identity records** for the first Stage-3 design-universe bootstrap, without silently turning source candidates into canonical identities.

The accepted runtime currently has:

- pure Brand / Organization identity primitives and search-label generation;
- accepted BoatModel / BoatDesign / generation / variant semantics in versioned schemas/specs;
- rights-gated Wikidata acquisition and pre-canonical research semantics;
- lossless PostgreSQL persistence for ResearchEvidenceBundle / ResearchObservation / FieldEvidence;
- Stage-2 Gate G3 `PASS`.

It does **not** yet have canonical BoatModel / BoatDesign entity persistence. The existing SLICE-0013 schema explicitly stores research/evidence records without requiring canonical entity tables, and the accepted identity runtime explicitly contains no persistence.

SLICE-0016 closes that missing boundary before HullQ attempts the controlled ~1,000-design canonical bootstrap.

This slice is **not** the ~1,000-design bootstrap itself.

## Why this slice exists

Stage 3 requires HullQ to move from a benchmark corpus to thousands of canonical sailboat identities. The next data milestone cannot safely be implemented by inserting Wikidata rows directly into ad-hoc tables or by treating a source QID/model label as a canonical HullQ identity decision.

The accepted identity model requires:

- stable opaque HullQ IDs independent of names;
- separate Brand and Organization identities;
- BoatModel as a continuous commercial lineage;
- BoatDesign as a technically coherent generation belonging to a BoatModel;
- explicit ambiguity instead of forced identity resolution;
- builder/manufacturer relationships separate from Brand/Model relationships;
- no automatic split/merge from one source label;
- provenance for source-backed identity facts.

The accepted Stage-2 PostgreSQL schema intentionally stopped before canonical entity persistence. Therefore the first Stage-3 implementation must establish a deterministic, auditable persistence/admission boundary before any broad canonical bootstrap is authorized.

## Controlling artifacts

Read and obey at minimum:

- `CLAUDE.md`;
- `docs/PROJECT_STATE.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3;
- `docs/ROADMAP.md` — broad design-universe ingestion;
- `docs/DATABASE_COVERAGE_STRATEGY.md`;
- `specs/IDENTITY_MODEL.v0.2.md`;
- `architecture/decisions/ADR-0004-model-generation-variant-identity.md`;
- `architecture/decisions/ADR-0011-brand-builder-identity-separation.md`;
- `specs/BOAT_MODEL_SCHEMA.v0.3.json` or the current accepted BoatModel schema if superseded on `main`;
- `specs/BOAT_DESIGN_SCHEMA.v0.5.json` or the current accepted BoatDesign schema if superseded on `main`;
- accepted Brand / Organization / alias / relationship schemas referenced by IDENTITY_MODEL.v0.2;
- `specs/PROVENANCE_MODEL.v0.1.md` and current accepted FieldEvidence contracts;
- `architecture/decisions/ADR-0006-field-level-provenance.md`;
- `architecture/decisions/ADR-0010-vps-first-application-stack.md`;
- SLICE-0013 PostgreSQL migration/import/readback implementation;
- `docs/slices/SLICE-0015-acceptance-closure.md`.

When filenames/versions differ because a later accepted version exists on `main`, use the current accepted artifact rather than silently reviving an older version.

## Accepted prior evidence

The following facts are already established and must not be re-decided in this slice:

1. PostgreSQL is the accepted production relational store.
2. The existing PostgreSQL schema persists research bundles, observations and FieldEvidence losslessly and deterministically.
3. That schema intentionally does **not** provide canonical BoatModel / BoatDesign tables.
4. `src/hullq/domain/identity.py` is intentionally pure and explicitly has no persistence/network resolution semantics.
5. Wikidata structured data is the strongest current broad CC0 bootstrap candidate and the rights-gated adapter already exists.
6. SLICE-0002 found a plausible four-digit Wikidata candidate universe, but the exact live count must be measured reproducibly later rather than hard-coded.
7. Stage-2 G3 has passed on the fixed benchmark scorecard.
8. G3 passage does not establish a production identity-resolution automation rate.
9. SailboatData remains outcome-only/post-hoc reference QA and must not become HullQ evidence, fallback data or canonical input.

## Core boundary

The desired flow after this slice is:

```text
rights-cleared source candidate / retained ResearchObservation
        ↓
explicit later bootstrap admission / identity decision
        ↓
caller supplies accepted canonical HullQ identity payload + stable HullQ ID
        ↓
SLICE-0016 canonical identity persistence boundary
        ↓
transactional PostgreSQL canonical identity store
        ↓
lossless deterministic readback
```

SLICE-0016 starts at the **already-admitted canonical payload** boundary.

It MUST NOT decide whether an arbitrary Wikidata/source candidate is the same real HullQ BoatModel/BoatDesign as another candidate.

## Binding rules

### 1. No automatic canonical identity resolution

The persistence layer MUST NOT:

- infer a canonical HullQ ID from a display name;
- equate a Wikidata QID or other external ID with a HullQ canonical ID automatically;
- fuzzy-match or typo-match identities;
- merge records because normalized search labels match;
- split BoatModels/BoatDesigns because names/years differ;
- infer Brand from Organization or Organization from Brand;
- infer a BoatDesign generation from one source field;
- create canonical entities from ResearchObservation hints automatically.

Canonical IDs are caller-supplied to this boundary and must already satisfy the accepted identity semantics.

ID minting/resolution for the later broad bootstrap remains a separate explicit concern.

### 2. Stable opaque canonical IDs

Every persisted Brand, Organization, BoatModel and BoatDesign MUST use a non-empty stable opaque HullQ ID independent of canonical display name.

The persistence implementation MUST treat the ID as immutable identity.

Do not derive destructive uniqueness from canonical names or normalized search labels.

Two distinct canonical entity IDs MAY have the same visible name when accepted identity semantics require it.

### 3. Entity types in scope

Persist the minimum Tier-0 identity surface required for the first broad bootstrap:

- Brand;
- Organization;
- BoatModel;
- BoatDesign;
- stable entity-scoped aliases where present;
- Brand ↔ BoatModel relationships where supplied;
- Organization ↔ BoatDesign builder/manufacturer relationships where supplied.

NamedVariant, DesignOption and ResolvedConfiguration persistence are not required in this slice unless the current accepted BoatModel/BoatDesign contract makes a minimal representation structurally unavoidable. Do not broaden the slice to technical configuration persistence merely for completeness.

### 4. Accepted schema validation before persistence

Canonical BoatModel / BoatDesign payloads MUST be validated with the existing repository-local canonical contract runtime against the current accepted schemas before any database mutation.

Where accepted Brand / Organization / alias / relationship schemas exist, use them rather than creating divergent validation semantics.

Validation failure MUST fail closed before committing data.

### 5. Sparse Tier-0 identity records are valid

Stage-3 breadth and verification depth are independent.

A canonical identity record MAY be sparse when accepted schemas permit it. Missing technical fields remain unknown.

Do not require Tier-1/Tier-2 technical enrichment merely to persist a valid Tier-0 identity.

Do not invent years, builders, brands, variants, dimensions or technical configuration to satisfy convenience constraints.

### 6. Canonical research provenance linkage

A canonical identity admission MUST be able to retain explicit links to the persisted HullQ research observations/evidence that supported the admission.

Implement the smallest normalized linkage needed to answer:

> Which retained HullQ observation/evidence supported creation/admission of this canonical identity or relationship?

Requirements:

- links use stable observation/evidence IDs, never array position;
- reference crosschecks remain structurally outside evidence/provenance and MUST NOT satisfy canonical admission provenance;
- no SailboatData field value may become supporting evidence;
- missing/invalid referenced evidence must fail closed;
- the linkage must remain auditable after readback.

Do not implement automatic FieldResolution in this slice.

### 7. Deterministic immutable import semantics

Use the proven SLICE-0013 pattern where appropriate.

For the same canonical entity ID:

- exact same semantic content → deterministic idempotent success / already-present outcome;
- different immutable semantic content → explicit conflict, no silent overwrite;
- partial write on conflict/error → forbidden.

The implementation MAY introduce a small versioned canonical-identity import bundle/manifest if useful, but it must remain narrowly scoped to identity persistence and must not become a generic ingestion framework.

### 8. Transactionality

A multi-entity admission/import unit MUST be atomic where its records depend on one another.

Examples:

- BoatDesign must not commit if its referenced BoatModel fails;
- BrandModelRelationship must not commit with missing Brand/BoatModel references;
- OrganizationDesignRelationship must not commit with missing Organization/BoatDesign references;
- provenance-link failures must not leave a partially admitted canonical entity graph.

### 9. Relationship semantics

Preserve accepted IDENTITY_MODEL.v0.2 rules:

- Brand ↔ BoatModel and Organization ↔ BoatDesign are separate relationship classes;
- a builder change alone MUST NOT create a new BoatDesign;
- same visible name MUST NOT collapse Brand and Organization;
- multiple time-/market-/hull-bounded relationships remain representable when accepted contracts provide those fields.

### 10. Database migration discipline

Extend the existing PostgreSQL migration chain; do not rewrite the accepted SLICE-0013 migration as though it had always contained canonical entities.

Requirements:

- migration from a clean PostgreSQL 18 database succeeds;
- migration from the accepted existing SLICE-0013/0015 schema succeeds;
- existing research tables/data remain intact;
- migration ordering/versioning is deterministic;
- no ORM or new migration framework is introduced without accepted architecture authority.

### 11. Readback

Provide deterministic readback sufficient to reconstruct and compare the persisted canonical identity semantics and provenance links.

Round-trip tests must compare semantic content, not merely row counts.

### 12. Concurrency

Concurrent exact admission/import of the same canonical identity content MUST remain race-safe and idempotent.

Concurrent conflicting content for the same canonical ID MUST produce a deterministic conflict/non-success outcome without corrupting accepted data.

Reuse PostgreSQL-native constraints/transaction behavior rather than process-local locks.

## In scope

### A. PostgreSQL schema extension

Add a new ordered migration after the accepted research-persistence migration for the scoped canonical identity entities, relationships and provenance links.

Keep schema design normalized enough to enforce stable identity/reference integrity. Do not introduce query-engine-specific denormalized projections yet.

### B. Canonical identity persistence API

Add a small Python persistence boundary for validated canonical identity admissions/imports.

It should expose explicit result states comparable in spirit to the accepted research importer, such as inserted/already-present/conflict/error semantics, without copying code blindly or inventing broader workflow orchestration.

### C. Semantic fingerprint/content comparison

Use deterministic semantic hashing/comparison for immutable idempotency/conflict detection.

Ordering of semantically unordered alias/relationship/supporting-evidence collections MUST NOT create false conflicts.

### D. Provenance linkage

Persist stable links from canonical identities/relationships to existing retained HullQ observations/evidence that supported admission.

### E. Readback and tests

Implement readback and PostgreSQL integration tests covering the full scoped identity graph.

## Required tests

At minimum cover:

1. clean PostgreSQL 18 migration creates the canonical identity schema after the existing research schema;
2. upgrade from the accepted existing schema preserves research data;
3. valid Brand admission round-trips exactly;
4. valid Organization admission round-trips exactly;
5. Brand and Organization with the same visible name remain distinct IDs/entities;
6. two distinct BoatModel IDs may retain the same canonical model name without forced merge;
7. BoatDesign requires a valid referenced BoatModel;
8. builder/manufacturer relationship requires valid Organization + BoatDesign references;
9. BrandModelRelationship requires valid Brand + BoatModel references;
10. builder change can be represented through relationships without creating another BoatDesign;
11. stable aliases remain entity-scoped and round-trip losslessly;
12. schema-invalid canonical payload fails before persistence;
13. missing supporting observation/evidence reference fails closed;
14. a reference crosscheck cannot satisfy canonical admission provenance;
15. exact repeated import/admission is idempotent;
16. changed semantic content under the same canonical ID yields explicit conflict and no overwrite;
17. reordering semantically unordered collections does not create a false conflict;
18. transaction failure rolls back the complete dependent identity graph;
19. concurrent exact admission is race-safe;
20. concurrent conflicting admission does not corrupt the accepted row;
21. sparse schema-valid Tier-0 identity payload is accepted without invented technical values;
22. no canonical IDs are minted from names/source IDs inside the persistence layer;
23. no network access occurs in normal persistence/unit/CI tests;
24. existing ResearchEvidenceBundle persistence tests remain green;
25. the full repository quality/coverage gate remains green on Linux and Windows;
26. real PostgreSQL 18 integration is executed in CI.

Add narrower tests where implementation evidence exposes another real failure path inside this scope.

## Required measurements / evidence

The completion report must state at minimum:

- exact migration version/files added;
- entity/relationship types persisted;
- exact idempotency/conflict semantics;
- exact provenance-link semantics;
- PostgreSQL version observed in CI;
- number of new persistence tests;
- full local test/coverage results;
- exact-head remote CI result;
- any unresolved identity/admission questions carried forward to the actual broad bootstrap.

No production-scale identity count is a success criterion for this slice because the ~1,000-design bootstrap is not run here.

## Acceptance criteria

SLICE-0016 is acceptance-ready only when all are true:

- [ ] canonical Brand/Organization/BoatModel/BoatDesign persistence exists on PostgreSQL 18 for the scoped Tier-0 identity surface;
- [ ] aliases and the two accepted relationship classes in scope persist without Brand/Organization collapse;
- [ ] canonical IDs are caller-supplied, stable and immutable; the persistence layer performs no source/name-based identity resolution;
- [ ] schema validation occurs before database mutation;
- [ ] canonical admissions retain auditable links to supporting HullQ observation/evidence IDs;
- [ ] reference crosschecks cannot satisfy that provenance requirement;
- [ ] exact repeat admission/import is idempotent;
- [ ] conflicting immutable content fails closed without overwrite;
- [ ] dependent multi-entity admission is transactional;
- [ ] semantic readback is lossless;
- [ ] concurrent exact/conflicting imports are PostgreSQL-race-safe;
- [ ] existing research persistence remains intact and green;
- [ ] normal tests do not require network access;
- [ ] real PostgreSQL 18 CI passes on the exact reviewed head;
- [ ] repository validator, formatting, lint, type checks, tests and coverage pass;
- [ ] no ~1,000-design bootstrap, fuzzy resolver or broad ingestion was started;
- [ ] independent review finds no remaining blocker;
- [ ] project owner explicitly accepts the slice before `DONE`.

## Explicitly out of scope

Do **not** implement or run:

- the controlled ~1,000-design bootstrap itself;
- live Wikidata candidate census at broad scale;
- fuzzy identity resolution;
- automatic canonical ID minting from names/QIDs/source rows;
- automatic source-candidate → BoatModel/BoatDesign admission;
- duplicate collapse based only on normalized names/search keys;
- automatic generation inference;
- automatic Brand ↔ Organization collapse;
- automatic FieldResolution;
- bulk manufacturer/designer website crawling;
- ORC ingestion;
- SailboatData ingestion/value persistence;
- NamedVariant / DesignOption / ResolvedConfiguration persistence unless strictly required by current accepted schema integrity;
- broad technical enrichment;
- derived-metric recomputation at dataset scale;
- query engine / OQ-009 implementation;
- FastAPI public API;
- Astro frontend;
- authentication/accounts;
- marketplace/listing ingestion;
- monitoring/alerts;
- price-history intelligence;
- SEO/public pages;
- distributed workers/infrastructure;
- 2,500 / 5,000 design expansion;
- Powerboat expansion.

## Expected touch points

Prefer the smallest coherent set, likely including:

- a new ordered SQL migration under `src/hullq/persistence/sql/`;
- one bounded canonical-identity persistence/import module under `src/hullq/persistence/`;
- readback/fingerprint support only where required;
- focused PostgreSQL integration tests under `tests/persistence/`;
- focused unit/contract tests where schema-validation semantics need coverage;
- `.github/workflows/ci.yml` only if the existing PostgreSQL integration job does not already execute the new tests;
- this slice document for completion-report append/handoff.

Do not create a generic repository/service/ORM layer merely because more canonical tables may exist later.

## Completion / handoff

The implementation agent MAY move this slice from `READY` to `IN_PROGRESS`, then to `REVIEW` or `BLOCKED` as evidence requires.

The implementation agent MUST NOT mark SLICE-0016 `DONE`.

The implementation agent MUST NOT begin the controlled ~1,000-design bootstrap or any later slice automatically.

`DONE` requires:

1. all acceptance criteria actually verified;
2. required exact-head PostgreSQL/remote CI observed and passed;
3. independent review complete;
4. explicit project-owner acceptance.

At completion, use the standard HullQ completion-report structure and clearly distinguish local validation from remote/external verification.