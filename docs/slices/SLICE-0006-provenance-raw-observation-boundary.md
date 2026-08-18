# SLICE-0006 — Provenance and Raw Observation Boundary

**ID:** SLICE-0006  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 2.5 — provenance/runtime foundation before external acquisition  
**Depends on:** SLICE-0005 accepted / DONE  
**Blocks:** SLICE-0007

## Objective

Implement the accepted persistence-agnostic provenance boundary that keeps immutable source observations separate from canonical values and from versioned resolution decisions.

The slice must make the existing `FieldEvidence` / `FieldResolution` contracts usable from Python before any real external acquisition is introduced. It must also reconcile provenance subject identity with the first-class Brand/Organization/alias/relationship identities introduced by SLICE-0005.

The central flow is:

```text
Source
  ↓ source_id
immutable raw observation
  ↓
FieldEvidence
  ↓ considered/supporting/contradicting evidence
FieldResolution
  ↓ exact current canonical-value snapshot
plain canonical subject value
```

Derived/calculated values remain a separate `DerivationRecord` concern and MUST NOT be represented as fabricated source evidence.

## Why this slice exists

ADR-0006 already accepted a separate provenance ledger:

1. immutable `FieldEvidence` source observations;
2. versioned `FieldResolution` canonical decisions;
3. separate `DerivationRecord` lineage for calculated/inherited values.

The accepted v0.1 provenance schemas predate SLICE-0005. Their subject-kind vocabulary currently covers BoatModel, BoatDesign, NamedVariant and DesignOption but not the newly first-class Brand, Organization, IdentityAlias, Brand↔BoatModel relationship and Organization↔BoatDesign relationship identities.

Real acquisition in SLICE-0008 must not begin until an observed external fact can be represented without:

- overwriting raw source information;
- silently converting unknown/conflicting evidence into accepted truth;
- embedding provenance into canonical BoatDesign/BoatModel records;
- losing the relationship between a canonical value and the evidence that justified it.

## Controlling artifacts

- ADR: `architecture/decisions/ADR-0006-field-provenance-ledger.md`.
- Requirements: `REQ-DATA-001` through `REQ-DATA-004`; `REQ-PROV-001` through `REQ-PROV-008`; `REQ-RESEARCH-003`.
- Existing migration inputs:
  - `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json`;
  - `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`;
  - `specs/DERIVATION_RECORD_SCHEMA.v0.1.json` (boundary reference only; do not redesign it here).
- Source identity/rights contract: `specs/SOURCE_SCHEMA.v0.2.json`.
- Identity contracts from SLICE-0005, including stable IDs for Brand, Organization, IdentityAlias and both relationship types.
- Measurement normalization runtime from SLICE-0004.
- Contract registry/runtime from SLICE-0003.

## Core semantic rules

1. **Observation is not canonical truth.** A `FieldEvidence` record says what one source was observed to say; it does not by itself make the candidate canonical.
2. **Raw is preserved.** Normalization MUST NOT overwrite the raw observation. Raw representation and normalized candidate remain separate.
3. **Evidence is append/supersede oriented.** Correcting an observation creates a new evidence record. Existing evidence records are not destructively rewritten.
4. **Resolution is a separate versioned decision.** Canonical acceptance/rejection/conflict state belongs to `FieldResolution`, not to `FieldEvidence`.
5. **Conflict remains visible.** Unresolved conflict cannot emit a non-null canonical value. `resolved_with_conflict` must retain contradicting evidence.
6. **Field addressing uses RFC 6901 JSON Pointer** relative to a stable subject identity.
7. **Stable identity, not array position, addresses provenance.** NamedVariant, DesignOption, IdentityAlias and relationship records use their own stable IDs as provenance subjects rather than fragile parent-array positions.
8. **Source evidence is not derived lineage.** Configuration inheritance, formulas and HullQ-generated calculations remain `DerivationRecord` work; this slice must not manufacture `FieldEvidence` for them.
9. **Confidence is observation/extraction confidence, not hidden source prestige.** This slice must not introduce an opaque source-authority score.
10. **Rights enforcement is not this slice.** `FieldEvidence.source_id` links to Source identity, but production-value / automated-ingestion / bulk-bootstrap clearance enforcement belongs to SLICE-0007.

## In scope

### 1. Versioned provenance subject contract

Introduce one shared versioned provenance-subject contract, preferably `PROVENANCE_SUBJECT_SCHEMA.v0.1.json`, so `FieldEvidence` and `FieldResolution` do not maintain independent subject-kind enums.

It must contain a stable non-empty subject ID and a typed subject kind.

The subject-kind vocabulary for this slice must support:

```text
boat_model
boat_design
named_variant
design_option
brand
organization
identity_alias
brand_model_relationship
organization_design_relationship
```

Do not add `resolved_configuration` as a direct external-evidence subject in this slice; ResolvedConfiguration is derived from canonical design/options and belongs to derivation lineage.

### 2. Successor FieldEvidence and FieldResolution schemas

Create successor schema versions derived from the accepted v0.1 contracts, expected as:

- `FIELD_EVIDENCE_SCHEMA.v0.2.json`;
- `FIELD_RESOLUTION_SCHEMA.v0.2.json`.

They must use the shared provenance-subject contract and preserve the accepted v0.1 semantics unless this slice explicitly requires a compatibility refinement.

Do not delete or silently edit `FIELD_EVIDENCE_SCHEMA.v0.1.json` or `FIELD_RESOLUTION_SCHEMA.v0.1.json`.

The successor FieldEvidence contract must retain at least:

- stable `evidence_id`;
- provenance subject;
- RFC 6901 field pointer;
- `source_id`;
- source locator;
- raw observation;
- optional/nullable normalized candidate metadata/value;
- evidence type;
- producer identity/version metadata;
- optional research context IDs;
- observed timestamp;
- observation confidence;
- optional superseded evidence ID;
- notes.

The successor FieldResolution contract must retain at least:

- stable `resolution_id`;
- provenance subject;
- field pointer;
- resolution state;
- canonical value snapshot;
- supporting / contradicting / considered evidence IDs;
- resolution method;
- policy version;
- resolver metadata;
- timestamp;
- optional superseded resolution ID;
- notes.

### 3. Focused Python provenance primitives

Add a focused module, preferably `src/hullq/domain/provenance.py`, with only the value objects/enums/helpers required to execute the accepted contracts.

Likely primitives include:

- subject kind / `ProvenanceSubject`;
- source locator;
- raw observation and normalized candidate;
- producer metadata;
- immutable/snapshot-safe `FieldEvidence`;
- resolution state/method/resolver metadata;
- immutable/snapshot-safe `FieldResolution`.

Implementation shape may differ if simpler, but it must not introduce persistence, ORM, generic event sourcing or a broad domain framework.

Caller-owned mutable JSON-like input used as a raw/canonical snapshot MUST NOT remain aliased such that later caller mutation changes an already-created evidence/resolution record.

### 4. RFC 6901 pointer primitives

Implement small deterministic pointer utilities sufficient for provenance validation:

- syntactic validation/parsing of RFC 6901 JSON Pointer;
- correct `~0` and `~1` decoding;
- deterministic lookup of a pointer in a JSON-like canonical subject snapshot where needed for consistency tests.

Do not invent dot-path aliases.

Do not use a parent collection array index as the persistent identity of NamedVariant, DesignOption, IdentityAlias or relationship records; those entities already have stable IDs and should be addressed as subjects themselves.

### 5. FieldEvidence invariant validation

Provide pure validation/helper behavior that can prove at least:

- evidence IDs are non-empty and independently addressable;
- source observation raw value survives normalization unchanged;
- a normalized candidate does not erase raw unit/text/excerpt information;
- supersession appends a new record and preserves the old snapshot;
- if an evidence record claims to supersede another evidence record available to the validator, the superseded record refers to the same provenance subject and field pointer;
- evidence from different sources may coexist for the same subject/field without auto-resolution.

Do not automatically infer a source's authority from evidence type, publisher or source name.

### 6. FieldResolution invariant validation

Provide pure validation/helper behavior for the accepted resolution semantics.

At minimum enforce when the relevant evidence records are supplied:

- every referenced evidence ID exists;
- referenced evidence belongs to the same subject and field pointer as the resolution;
- supporting and contradicting evidence IDs are included in considered evidence;
- one evidence ID cannot simultaneously be supporting and contradicting in the same resolution;
- `resolved` / `resolved_with_conflict` require a non-null canonical snapshot and supporting evidence;
- `resolved_with_conflict` retains at least one contradicting evidence record;
- `unknown` / `needs_review` / unresolved `conflict` do not emit a non-null canonical snapshot;
- unresolved `conflict` retains contradicting evidence;
- superseding a resolution creates a new record; the old resolution remains auditable.

Do not invent a global source-priority policy. `source_priority_rule` remains a valid explicit resolution-method label, but policy content/ranking is not implemented here.

### 7. Resolution-history/current-state validation

Implement a persistence-agnostic collection-level validator/helper that can establish the accepted history rule without choosing a database.

For a supplied resolution collection it must be possible to detect/reject:

- two unsuperseded/current resolutions for the same `(subject_kind, subject_id, field_pointer)`;
- a supersession link crossing to a different subject/field;
- missing superseded resolution IDs where a complete history collection is being validated;
- cycles/forks that make current resolution ambiguous.

A simple deterministic in-memory validation/query helper is sufficient. Do not build a repository/storage abstraction.

### 8. Canonical-value consistency check

Provide a pure helper that can validate REQ-PROV-005 against a supplied canonical JSON-like subject snapshot and its current resolution.

For a source-backed non-null canonical field:

```text
canonical value at field_pointer
==
current resolved/resolved_with_conflict canonical_value_snapshot
```

A mismatch must be detectable as a validation failure.

Unknown/conflict states with null canonical snapshot must not be turned into a canonical value by this helper.

This is a validation boundary only; it must not write/mutate canonical domain records.

### 9. Source-impact/reverse lookup primitive

Implement a small persistence-agnostic query/helper satisfying the logical requirement behind REQ-PROV-007:

```text
source_id
  ↓
FieldEvidence records
  ↓
current/past FieldResolution records that reference those evidence IDs
```

Given an in-memory collection of evidence/resolutions, the caller must be able to enumerate affected evidence and field resolutions for one Source ID.

Do not implement rights-change workflows or database indexes here; SLICE-0007 will use this boundary when enforcing source clearance.

### 10. Raw → normalized integration test

Add at least one test integrating the existing SLICE-0004 measurement normalization with provenance:

- preserve a synthetic raw source representation and source unit;
- calculate a deterministic normalized SI candidate using the accepted measurement runtime;
- store both in separate observation fields;
- prove normalization did not mutate or replace the raw source representation.

No source-specific parsing heuristics are authorized.

## Explicitly out of scope

Do not implement:

- ResearchJob state machine;
- source clearance/rights gate enforcement;
- `production_value`, `bulk_bootstrap` or `automated_ingestion` authorization logic;
- HTTP/API/Wikidata/PDF/HTML acquisition;
- source crawling, request counting or extraction telemetry;
- PostgreSQL, SQLite provenance persistence, ORM or migrations;
- repository/storage interfaces beyond pure collection helpers required for tests;
- DerivationRecord calculation/inheritance engine;
- derived metrics;
- query/search semantics or OQ-009;
- fuzzy identity matching;
- appendage taxonomy redesign;
- source-authority scoring/ranking heuristics;
- full W3C PROV implementation;
- FastAPI/frontend;
- use, copying or storage of the private reference boat list.

## Required synthetic fixtures/tests

Use synthetic data only. Do not use the private reference dataset.

Cover at least the following:

1. BoatDesign field evidence can address `/baseline/dimensions/loa_m` by BoatDesign ID.
2. Brand canonical-name evidence can use Brand as a provenance subject.
3. Organization evidence can use Organization as a provenance subject.
4. IdentityAlias evidence can address an alias record by its stable alias ID rather than a parent-array index.
5. BrandModelRelationship and OrganizationDesignRelationship can each be provenance subjects by stable relationship ID.
6. FieldEvidence v0.1 remains loadable as a historical schema while v0.2 supports the expanded subject kinds.
7. FieldResolution v0.1 remains loadable as a historical schema while v0.2 supports the expanded subject kinds.
8. FieldEvidence and FieldResolution use the same shared subject-kind definition rather than copied enums.
9. RFC 6901 escaping works for keys containing `~` and `/`.
10. malformed pointer escape syntax is rejected by the Python pointer validator.
11. raw value/unit/excerpt remain unchanged after a normalized candidate is created.
12. mutation of caller-owned mutable input after record construction does not alter the captured evidence/resolution snapshot.
13. two contradictory source observations can coexist without either becoming canonical automatically.
14. an evidence supersession retains the earlier evidence record and links the replacement.
15. a resolution cannot cite evidence belonging to another subject or field.
16. supporting/contradicting evidence are subsets of considered evidence and cannot overlap.
17. `resolved` requires support and a non-null canonical snapshot.
18. `resolved_with_conflict` retains both support and contradiction.
19. unresolved `conflict` has null canonical snapshot and contradiction evidence.
20. two current resolutions for one subject/field are rejected by history validation.
21. a valid supersession chain yields exactly one current resolution.
22. cross-field/cyclic/forked resolution supersession is rejected.
23. canonical value/resolution snapshot equality passes; mismatch fails.
24. reverse lookup by `source_id` returns affected evidence and current/past resolutions.
25. a SLICE-0004 synthetic measurement normalization can become a normalized evidence candidate while raw source representation remains intact.
26. no API in the module grants source rights, fetches network data or auto-ranks source authority.

Property-based tests SHOULD be used for JSON Pointer escaping/round-trip or history invariants where they add useful coverage without obscuring semantics.

## Deliverables

Expected deliverables:

- `specs/PROVENANCE_SUBJECT_SCHEMA.v0.1.json`;
- successor `specs/FIELD_EVIDENCE_SCHEMA.v0.2.json`;
- successor `specs/FIELD_RESOLUTION_SCHEMA.v0.2.json`;
- focused `src/hullq/domain/provenance.py`;
- unit/contract tests and small synthetic fixtures as needed;
- registry changes required only because successor schemas are introduced;
- slice/index status updates for handoff.

Do not modify the accepted v0.1 evidence/resolution schemas in place.

## Acceptance criteria

- [ ] provenance subject identity is single-source-of-truth across successor FieldEvidence and FieldResolution contracts.
- [ ] Brand, Organization, IdentityAlias and both SLICE-0005 relationship identities are first-class provenance subjects alongside the existing design/model subjects.
- [ ] legacy FieldEvidence v0.1 and FieldResolution v0.1 remain unchanged/loadable.
- [ ] Python evidence records preserve immutable/snapshot-safe raw observations separately from normalized candidates.
- [ ] RFC 6901 pointer parsing/lookup is deterministic and supports required escaping.
- [ ] evidence supersession is append-oriented and does not rewrite historical observations.
- [ ] resolution validation preserves unknown/conflict semantics and rejects mismatched evidence references.
- [ ] resolution-history validation can detect multiple-current, cross-field, missing-link, cycle and fork errors without selecting a persistence technology.
- [ ] a supplied canonical value can be checked against the current resolution snapshot without mutating canonical data.
- [ ] reverse Source → FieldEvidence → FieldResolution impact lookup works over supplied collections.
- [ ] measurement normalization can feed a normalized candidate while preserving the source's raw representation.
- [ ] no source-rights gate, ResearchJob, acquisition, persistence, derived-value engine, source-authority score or search/query behavior is introduced.
- [ ] repository validator, Ruff, strict mypy, pytest/branch coverage and dependency audit pass locally.
- [ ] required remote CI is observed independently and reported truthfully before project-owner acceptance.

## Expected touch points

Likely:

- `specs/PROVENANCE_SUBJECT_SCHEMA.v0.1.json`;
- `specs/FIELD_EVIDENCE_SCHEMA.v0.2.json`;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.2.json`;
- `src/hullq/domain/provenance.py`;
- `tests/unit/test_provenance.py`;
- `tests/contract/test_provenance_contracts.py`;
- optional small synthetic fixture under `fixtures/provenance/`;
- `docs/slices/SLICE-0006-provenance-raw-observation-boundary.md`;
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

Stop and report rather than inventing semantics when:

- a provenance subject cannot be mapped to an accepted stable identity;
- a requested behavior would require source-rights/clearance decisions from SLICE-0007;
- canonical acceptance would require an unspecified source-priority or adjudication policy;
- a derived/calculated value would need fabricated external evidence;
- implementing current-resolution uniqueness appears to require choosing a persistence/database technology;
- implementation would require network acquisition;
- a new third-party dependency appears necessary.

## Status handoff rule

The implementation agent may move this slice to `IN_PROGRESS`, `BLOCKED` or `REVIEW` as justified, but MUST NOT mark it `DONE`.

Successful completion hands SLICE-0006 to independent review. Do not begin SLICE-0007 automatically.

## Required completion report

Use the exact structure in `docs/slices/SLICE_TEMPLATE.md`.

Also report:

- final successor schema/version names;
- final provenance subject-kind vocabulary;
- final public Python provenance API;
- how raw observation snapshot safety is enforced;
- how RFC 6901 pointers are parsed/resolved;
- how evidence and resolution supersession/current-state invariants are validated;
- how canonical consistency and reverse source-impact lookup work;
- any provenance semantics deliberately deferred to SLICE-0007 or later.
