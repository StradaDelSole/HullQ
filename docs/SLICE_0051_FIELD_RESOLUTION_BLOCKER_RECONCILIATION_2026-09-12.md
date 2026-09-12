# SLICE-0051 — FieldResolution blocker reconciliation

**Date:** 2026-09-12  
**Status:** BLOCKER-RESOLUTION RECONCILIATION  
**Applies to:** active SLICE-0051 only  
**Implementation branch blocked at:** `2f6d7ba4b622a82250fa2c4df62bb43fa41d7814`  
**Canonical main reconciled:** `99025fcb87fdd9f1794f107dec2f024aa0aef3cf`  

## Purpose

SLICE-0051 implementation review exposed a prerequisite that the original readiness reconciliation missed: HullQ has accepted field-level canonical-resolution semantics, but production PostgreSQL does not yet persist current `FieldResolution` state for canonical BoatDesign / NamedVariant technical fields.

This document is a deliberate blocker-resolution artifact under `docs/engineering/AI_SLICE_WORKFLOW.md`. It does **not** create a new product semantic, reopen OQ-004, select another slice, or authorize work outside SLICE-0051.

The implementation agent correctly failed closed instead of treating a value merely present in `canonical_boat_designs` JSONB, or record-level `quality.status` / `quality.confidence`, as a confirmed field value.

## Decision / implementation reconciliation

### Accepted records checked

- `architecture/decisions/ADR-0006-field-provenance-ledger.md`;
- `specs/PROVENANCE_MODEL.v0.1.md`;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`;
- `specs/PROVENANCE_AND_QUALITY.md`;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`;
- `docs/engineering/AI_SLICE_WORKFLOW.md`;
- accepted SLICE-0016 and SLICE-0037 records;
- current SLICE-0051 readiness contract and implementation handoff at `2f6d7ba4b622a82250fa2c4df62bb43fa41d7814`.

### Production implementation checked

- `src/hullq/domain/provenance.py` — accepted `FieldResolution`, resolution-state and invariant domain primitives exist; persistence is explicitly not implemented there;
- `src/hullq/sources/rights.py` — deterministic fail-closed source-use gate including `SourceUse.PRODUCTION_VALUE` exists;
- `src/hullq/persistence/sql/001_initial_schema.sql` — durable `research_evidence` exists and retains `source_id`, subject identity and field pointer;
- `src/hullq/persistence/sql/002_canonical_identity_schema.sql` — durable `canonical_boat_designs` and admission-evidence links exist, but no current/versioned FieldResolution persistence exists;
- current Alembic chain — no FieldResolution migration/table exists;
- `src/hullq/persistence/identity_importer.py` — canonical identity admission is not field resolution;
- accepted SLICE-0037 Oceanis 30.1 retained oracle — a deliberately bounded pilot-specific admission oracle, explicitly not generic production FieldResolution persistence;
- `src/hullq/search/draft_max_design_bridge.py` at blocked SLICE-0051 HEAD — correctly refuses to manufacture `CONFIRMED` from raw persisted design JSON.

### Material classifications

`DECIDED_AND_IMPLEMENTED`

- OQ-004 / ADR-0006 semantic model: immutable `FieldEvidence`, versioned `FieldResolution`, `DerivationRecord`, RFC-6901 field identity, resolution states and canonical-value consistency rules;
- persistence-agnostic FieldResolution domain primitives and validation logic;
- source-rights policy and deterministic `production_value` source-use gate;
- canonical BoatDesign persistence and immutable research evidence persistence;
- SLICE-0051 Search/listing semantics outside this blocker.

`DECIDED_NOT_YET_IMPLEMENTED`

- durable PostgreSQL persistence for versioned FieldResolution records;
- at-most-one current/active resolution per `(subject_kind, subject_id, field_pointer)`;
- durable/current readback suitable for production Search;
- persistence enforcement that a non-null source-backed canonical production value agrees with the active resolution snapshot and is in `resolved` or `resolved_with_conflict` state;
- production-resolution evidence validation including accepted source-rights requirements.

`EXPLICITLY_DEFERRED`

- a generic automatic source winner / source ranking / majority / recency adjudicator;
- global automatic resolution of all canonical fields;
- bulk backfill of every existing BoatDesign field;
- a second search engine or generic all-field native inventory Search;
- broad source-registry redesign beyond what the accepted provenance/source-rights contracts require for this bounded write/read path.

`CONFLICT_OR_REGRESSION`

- the original SLICE-0051 readiness reconciliation stated that the exact remaining gap was only the Search→inventory bridge and omitted the accepted-but-unimplemented FieldResolution persistence prerequisite;
- the original readiness therefore could not support its claim that there was no additional production prerequisite for field-qualified design Search.

There is **no new Project Owner product/domain decision** required merely to choose between FieldResolution and a weaker rule. FieldResolution is already the accepted rule. Per `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`, this is an implementation/traceability gap, not a re-decision.

## Blocker-resolution direction

SLICE-0051 remains the execution owner. Do not create or start SLICE-0052 for this prerequisite.

The accepted 2026-09-11 sequencing decision already requires the minimum backend bridge necessary for the first buyer-facing Requirements → Native Inventory Search vertical to live inside SLICE-0051 rather than inserting a separate foundation-only slice.

The previously stated migration stop condition has now been satisfied: implementation found and reported a schema change genuinely required for correctness. Therefore a **bounded Alembic FieldResolution persistence migration is authorized inside SLICE-0051** as the minimum prerequisite needed to consume qualified canonical design facts. This authorization does not change OQ-004 semantics.

## Bounded implementation contract

### 1. Reuse accepted FieldResolution semantics

Implementation MUST reuse `src/hullq/domain/provenance.py`, `specs/PROVENANCE_MODEL.v0.1.md` and `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json` rather than inventing a new Search-only quality flag or parallel resolution model.

At minimum the durable path must preserve:

- immutable/versioned resolution history;
- explicit `resolution_id`;
- `subject_kind`, `subject_id`, RFC-6901 `field_pointer`;
- `state`;
- lossless `canonical_value_snapshot`;
- supporting / contradicting / considered evidence identities;
- resolution method, policy version, resolver metadata and resolution time;
- supersession identity;
- at most one current/active resolution for one logical subject field.

Exact physical table shape is an engineering detail, provided these accepted invariants are mechanically enforced and tested.

### 2. No automatic adjudication policy is invented

This blocker resolution does not authorize a generic resolver.

A persistence write may store an already-adjudicated FieldResolution only after all accepted invariants pass. If automatic adjudication would be needed to create that resolution, it may occur only under an already accepted deterministic rule. Otherwise the state remains `unknown`, `needs_review` or `conflict` as defined by the accepted provenance model.

No latest-source, source-priority, majority, confidence-score or record-level quality shortcut may be introduced by SLICE-0051.

### 3. Evidence and source-rights enforcement

A resolved production FieldResolution must not become current merely because referenced `research_evidence` rows exist.

For each supporting evidence record used by a non-null production resolution:

- the evidence ID must exist durably;
- its subject identity and field pointer must be compatible with the resolution subject field under the accepted provenance rules;
- its `source_id` must be bound to a schema-valid HullQ Source rights record available to the resolution-admission path;
- `production_value` use must satisfy the accepted `SOURCE_RIGHTS_POLICY.v0.1.md` fail-closed boundary;
- prohibited, unknown, unresolved/legal-review-required use must not support a current production resolution;
- no generic broadening of a pilot-specific conditional clearance is permitted.

The existing `src/hullq/sources/rights.py` gate is the production-rights policy implementation to reuse where applicable. If the implementation cannot mechanically establish the required source-rights state for an attempted resolution, it must fail closed rather than treating provenance existence as permission.

This bounded persistence work does not require a new universal Source-registry architecture. If a genuinely new durable Source-registry semantic becomes necessary rather than a bounded admission/read mechanism over existing accepted Source records, stop and report that distinct prerequisite.

### 4. Canonical-value consistency

For a non-null source-backed production value, the active FieldResolution snapshot must equal the canonical subject value it qualifies, as required by `PROVENANCE_MODEL.v0.1.md`.

SLICE-0051 needs only the exact fields required by its `draft_max` design/configuration vertical:

```text
BoatDesign
/baseline/dimensions/draft_max_m

NamedVariant
/overrides/dimensions/draft_max_m
```

The persistence/read path may remain generic at the FieldResolution layer, but SLICE-0051 Search consumption must stay bounded to those exact field meanings.

A NamedVariant with no draft override inherits the qualified BoatDesign baseline at Search-evaluation time; it must not manufacture a second direct source-backed resolution merely to represent inheritance. A NamedVariant whose own draft override is used must have admissible qualification for that override. Variants requiring unapplied `DesignOption` dependencies remain excluded under the already-reviewed amendment behavior.

### 5. Exact Decimal remains mandatory

PostgreSQL/JSON decoding must not introduce a binary-float intermediary for the `draft_max` qualification path.

The FieldResolution read adapter and Search bridge must surface the qualified draft candidate as `Decimal` (or an exactly equivalent representation) from persistence through criterion evaluation. Existing legacy float Search callers must remain compatible; no unrelated historical numeric-contract rewrite is authorized.

### 6. Search consumption rule

`canonical_boat_designs` storage alone is not confirmation.

For the bounded 0051 design bridge:

```text
raw canonical JSON value
+ no active admissible FieldResolution
→ MISSING / INSUFFICIENT_DATA for hard Search qualification

active resolution state resolved | resolved_with_conflict
+ canonical snapshot/value consistency
+ admissible production evidence
→ qualified numeric candidate

active resolution state unknown | needs_review | conflict
→ non-confirming Search state
```

The existing deterministic configuration-aware Search kernel remains authoritative for requirement evaluation after qualification.

### 7. Migration / transactional requirements

Use the accepted Alembic-only forward migration path.

The migration/persistence implementation must prove at least:

- clean upgrade from the current migration head;
- append/current-head atomicity or an equivalently race-safe one-current-resolution invariant;
- exact retry/idempotency behavior that does not create duplicate current decisions;
- stale/forged supersession cannot replace the current resolution;
- resolution history remains immutable/readable;
- a failed write cannot leave an orphan current head;
- canonical-value mismatch fails closed;
- unresolved states cannot expose a non-null canonical production value;
- supporting evidence/reference failures roll back atomically.

### 8. Retained proof after unblock

The final SLICE-0051 retained proof must revert from the temporary zero-match fail-closed demonstration to the actual readiness objective.

Against real PostgreSQL 18 → FastAPI → built Astro SSR it must demonstrate, at minimum:

- at least one design/configuration whose relevant draft field has a durable admissible active FieldResolution;
- one ACTIVE listing whose publisher concrete draft confirms `draft <= draft_max` and appears as `CONFIRMED_MATCH`;
- insufficient-data behavior;
- conflict behavior;
- non-ACTIVE/no-design/unqualified-design cases do not leak as confirmed results;
- no fixture-only bypass of FieldResolution or source-rights qualification.

## Scope guardrails

This blocker resolution does **not** authorize:

- another public Search criterion;
- generic all-field Search;
- a global canonical-fact resolver;
- an automatic source-ranking/winner policy;
- weakening provenance, rights or verification semantics;
- broad backfill of all BoatDesign fields;
- replacing the accepted OQ-004 ledger with record-level quality metadata;
- a new backend/search service;
- work on the next slice.

## Workflow continuation

Current state after this reconciliation is:

```text
SLICE-0051 implementation
→ BLOCKED at 2f6d7ba4b622a82250fa2c4df62bb43fa41d7814
→ deliberate blocker-resolution reconciliation on main
→ exact-head review / merge of this blocker-resolution artifact
→ same SLICE-0051 branch incorporates the accepted blocker resolution
→ targeted amendment to implement the missing FieldResolution persistence + Search consumption
→ Claude handoff REVIEW
→ independent exact-head implementation review
```

`START_SLICE.bat` MUST NOT be run again. No parallel initial Claude prompt is authorized. After this blocker-resolution artifact is merged to `main`, any instruction to Claude is a targeted amendment inside the already-running SLICE-0051 only.
