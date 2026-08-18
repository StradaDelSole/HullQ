# SLICE-0005 — Identity Contracts and Deterministic Search Labels

**ID:** SLICE-0005  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 2.4 — canonical identity runtime foundation  
**Depends on:** SLICE-0004 accepted / DONE  
**Blocks:** SLICE-0006

## Objective

Implement the accepted HullQ identity boundary that separates Brand/Marque from Organization/Builder/Manufacturer while preserving the existing BoatModel → BoatDesign generation structure.

This slice creates first-class versioned identity contracts and a small pure-Python identity/search-label primitive layer. It MUST migrate the current BoatModel/BoatDesign identity contracts away from authoritative free-text brand/builder fields without changing unrelated technical semantics.

## Why this slice exists

ADR-0011 and `specs/IDENTITY_MODEL.v0.2.md` established that market-facing brands and productive/legal organizations are different identity concepts. Both must be independently searchable, may have different names, may change relationships over time, and must not be collapsed merely for search convenience.

Current accepted schemas predate that decision:

- `BOAT_MODEL_SCHEMA.v0.1.json` stores `manufacturer_name` / `brand_name` as free text;
- `BOAT_DESIGN_SCHEMA.v0.4.json` stores builder identity through free-text names.

The next research/provenance/acquisition slices need stable entity IDs and explicit relationships before real external identity data is ingested.

## Controlling artifacts

- Requirements: `REQ-ID-001` through `REQ-ID-012`; `REQ-SEARCH-007`, `REQ-SEARCH-008`, `REQ-SEARCH-009`.
- Specification: `specs/IDENTITY_MODEL.v0.2.md`.
- Accepted ADRs: ADR-0004 and ADR-0011.
- Existing migration inputs: `specs/BOAT_MODEL_SCHEMA.v0.1.json`, `specs/BOAT_DESIGN_SCHEMA.v0.4.json`.
- Contract runtime: SLICE-0003 / `src/hullq/contracts/`.
- Measurement runtime: SLICE-0004 is already accepted and MUST remain unchanged.
- OQ-009 remains unresolved; therefore this slice MUST NOT implement technical query semantics, fuzzy ranking or result ordering.

## Core semantic rules

1. **Brand is not Builder.** A Brand/Marque and an Organization/Builder/Manufacturer are separate first-class entities even when they share the same visible spelling.
2. **Aliases are entity-scoped.** A Brand alias does not become an Organization alias and vice versa.
3. **Relationships are explicit.** Brand ↔ BoatModel and Organization ↔ BoatDesign relationships must support multiple/historical associations without forcing identity collapse.
4. **Builder transfer is not automatically a new BoatDesign.** Technical generation rules remain governed by ADR-0004 / Identity Model v0.2.
5. **Search convenience is not identity mutation.** Search-label generation may create additional normalized lookup keys but MUST NOT rewrite canonical names, source spellings or canonical IDs.
6. **Raw `manufacturer` input is not role evidence.** This slice MUST NOT infer Brand vs Organization from a source column heading, model prefix or string pattern.

## In scope

### 1. First-class identity contracts

Introduce versioned JSON Schemas for at least:

- `Organization`;
- `Brand`;
- entity-scoped `IdentityAlias`;
- Brand ↔ BoatModel relationship;
- Organization ↔ BoatDesign relationship.

Each canonical identity entity MUST have a stable opaque non-empty ID independent of its display name.

`Organization` and `Brand` MUST each support:

- canonical display name;
- zero or more entity-scoped aliases via stable alias identity/reference;
- no destructive canonical-name normalization.

An alias contract MUST support the accepted alias classes:

```text
common_name
trade_name
abbreviation
historical_name
alternate_spelling
transliteration
source_spelling
other
```

Alias identity/addressing MUST be stable enough for later provenance; do not depend on array position.

### 2. Relationship contracts

Brand ↔ BoatModel and Organization ↔ BoatDesign relationships MUST be independently identifiable and MUST be capable of carrying optional applicability boundaries without inventing precision.

Support optional boundaries where known, at least conceptually for:

- first/last year;
- hull/build number from/to;
- market/region label.

Unknown boundaries MUST be representable by absence/null rather than fabricated dates or hull numbers.

Organization ↔ BoatDesign relationships MUST distinguish builder/manufacturer role semantics without requiring a new BoatDesign when the organization changes.

### 3. BoatModel contract revision

Create a new BoatModel schema version that supersedes v0.1 as the current identity target.

It MUST:

- retain stable opaque BoatModel ID;
- retain canonical model name;
- retain first/last-built and BoatDesign links;
- replace authoritative free-text `manufacturer_name` / `brand_name` identity boundaries with explicit Brand relationship IDs/records;
- replace free-text model aliases with entity-scoped alias IDs/records consistent with the new alias contract;
- allow zero Brand relationships when evidence is insufficient.

Do not delete or silently edit `BOAT_MODEL_SCHEMA.v0.1.json`.

### 4. BoatDesign contract revision

Create a new BoatDesign schema version derived from v0.4.

It MUST preserve v0.4 technical/configuration/ratio semantics unchanged except for the identity migration required here.

It MUST:

- retain stable opaque BoatDesign ID and `boat_model_id`;
- replace canonical free-text builder/manufacturer names with explicit Organization relationship IDs/records;
- support multiple builder/manufacturer relationships;
- keep technical generation, NamedVariant, DesignOption and ResolvedConfiguration semantics unchanged;
- make no appendage/configuration taxonomy changes in this slice.

Do not delete or silently edit `BOAT_DESIGN_SCHEMA.v0.4.json`.

### 5. Pure Python identity primitives

Add a small focused module, preferably `src/hullq/domain/identity.py`, containing only primitives justified by the accepted contracts, such as:

- identity-kind enum(s) where useful;
- alias-type enum matching the schema exactly;
- immutable value objects for Brand, Organization, aliases and the two relationship kinds, if useful;
- deterministic search-label/key generation described below.

Do not add persistence, ORM, repositories, network resolution or generic entity-framework abstractions.

### 6. Deterministic search-label generation

Implement only the minimal identity-name projection needed by `REQ-SEARCH-008/009`.

The projection MAY:

- case-fold;
- normalize punctuation/whitespace;
- produce an additional shortened Organization lookup key by removing accepted non-distinguishing terminal corporate suffixes/source decorations;
- use explicitly supplied aliases/transliterations as additional lookup terms.

At minimum support the accepted suffix/decorations named by ADR-0011 / Identity Model v0.2:

```text
Ltd. / Limited
Inc.
Corp. / Corporation
GmbH
Co. / Company
terminal country annotations such as (USA), (UK), (FRA)
```

Repeated terminal suffixes such as `Co., Ltd.` SHOULD be removable as search-only projection tokens.

The projection MUST:

- leave canonical/source names unchanged;
- return lookup candidates/keys only;
- never merge entities;
- allow two distinct entity IDs to produce the same normalized key;
- perform no fuzzy typo matching/ranking;
- perform no automatic semantic classification from model prefixes.

Curated alternate spellings/transliterations come from explicit alias data; do not invent transliterations from arbitrary names in this slice.

## Explicitly out of scope

Do not implement:

- fuzzy matching, edit-distance ranking or typo correction;
- technical query semantics or OQ-009 three-state matching;
- automatic Brand/Organization resolution from raw source strings;
- manufacturer-prefix heuristics;
- designer person/organization schema redesign;
- appendage/keel/rudder/skeg normalization;
- provenance/FieldEvidence/FieldResolution runtime;
- ResearchJob or source-rights enforcement runtime;
- Wikidata/HTTP/PDF/HTML acquisition;
- PostgreSQL/ORM/migrations;
- FastAPI/frontend/SEO URLs;
- broad data ingestion;
- use or storage of the private reference boat list.

## Required fixtures/tests

Use synthetic fixture names; do not copy the private reference dataset into the repository.

Cover at least:

1. Brand and differently named Organization remain separate but can lead to the same BoatModel/BoatDesign path.
2. Same visible spelling can exist as separate Brand and Organization IDs without collapse.
3. Brand alias remains scoped to Brand and does not mutate Organization.
4. Organization alias remains scoped to Organization and does not mutate Brand.
5. One Brand can relate to multiple Organizations over time through BoatModel/BoatDesign relationships.
6. One Organization can build designs associated with multiple Brands.
7. Builder change can be represented without creating a second BoatDesign solely for that change.
8. Relationship validity can remain unknown/null or use year/hull/market boundaries when explicitly supplied.
9. BoatModel v0.2 has no authoritative free-text manufacturer/brand identity fields.
10. BoatDesign successor has no authoritative free-text builder identity name.
11. Legacy BoatModel v0.1 and BoatDesign v0.4 remain loadable as historical/versioned schemas.
12. Alias-type Python vocabulary exactly matches the normative schema enum if a Python enum is introduced.
13. `Builder Works Ltd. (USA)` or equivalent synthetic canonical Organization name can generate a shortened search key such as `builder works` without changing the canonical string.
14. Repeated suffixes such as `Example Marine Co., Ltd.` can generate a shortened search-only key.
15. Case/punctuation normalization can cause two distinct entity IDs to share a key without merging them.
16. Raw/source manufacturer text alone does not trigger Brand/Organization classification; no such inference path exists in this module.

## Deliverables

Expected deliverables include:

- new versioned identity JSON Schemas under `specs/`;
- successor BoatModel and BoatDesign schema versions;
- focused identity domain module under `src/hullq/domain/`;
- contract/unit tests and synthetic identity fixtures;
- any schema-registry updates required solely because new schemas are added;
- slice/index status updates for handoff.

Schema names/version numbers may follow the repository's existing versioning convention, but MUST NOT mutate existing accepted schema files in place.

## Acceptance criteria

- [ ] Brand and Organization are distinct first-class validated identities with stable opaque IDs.
- [ ] entity-scoped aliases are versioned, typed and provenance-addressable without array-position dependence.
- [ ] Brand ↔ BoatModel and Organization ↔ BoatDesign relationships support multiple/historical associations and optional explicit applicability boundaries.
- [ ] BoatModel successor removes authoritative free-text manufacturer/brand identity boundaries while preserving BoatModel semantics.
- [ ] BoatDesign successor removes authoritative free-text builder identity names while preserving all unrelated v0.4 technical semantics.
- [ ] legacy schema versions remain available and loadable.
- [ ] deterministic search-label generation supports accepted corporate-name shortening without mutating canonical/source strings.
- [ ] normalized-key collisions do not merge distinct canonical entities.
- [ ] no fuzzy matching, raw-string role inference, persistence, provenance runtime, acquisition or appendage redesign is introduced.
- [ ] synthetic tests/fixtures cover the required cases above.
- [ ] repository validator, Ruff, strict mypy, pytest/coverage and dependency audit pass locally.
- [ ] required remote CI is reported truthfully and is not guessed.

## Expected touch points

Likely:

- `specs/*IDENTITY*SCHEMA*.json` and successor BoatModel/BoatDesign schemas;
- `src/hullq/domain/identity.py`;
- `tests/unit/test_identity.py`;
- `tests/contract/` identity contract tests where appropriate;
- `fixtures/identity/` synthetic fixtures;
- `docs/slices/SLICE-0005-identity-contracts-and-search-labels.md`;
- `docs/slices/INDEX.md`.

Avoid unrelated changes.

## Validation

Run at minimum:

```bash
uv lock --check
uv sync --locked --all-groups
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

## Stop conditions

Stop and report instead of inventing a solution when:

- the accepted Identity Model/ADR does not determine whether a field represents Brand, Organization, BoatModel or BoatDesign;
- preserving BoatDesign v0.4 technical semantics would require an unrelated taxonomy redesign;
- a schema choice would require silently resolving raw manufacturer text to an entity kind;
- implementation appears to require OQ-009 query/ranking semantics;
- implementation requires persistence/provenance/acquisition work outside this slice;
- a new third-party dependency appears necessary.

## Status handoff rule

The implementation agent may move this slice to `IN_PROGRESS`, `BLOCKED` or `REVIEW` as justified, but MUST NOT mark it `DONE`.

Successful completion normally hands the slice to `REVIEW`. Do not begin SLICE-0006 automatically.

## Required completion report

Use the exact structure in `docs/slices/SLICE_TEMPLATE.md`.

Also report:

- final schema/version names introduced;
- final public identity Python API;
- how Brand/Organization separation is enforced;
- how relationship history/applicability is represented;
- how corporate-name search keys are generated without canonical mutation;
- any identity ambiguity deliberately deferred to later research/provenance/search slices.
