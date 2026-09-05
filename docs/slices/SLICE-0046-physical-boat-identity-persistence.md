# SLICE-0046 — PhysicalBoat Identity Persistence

**ID:** SLICE-0046  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Native professional supply — physical-yacht identity backbone  
**Depends on:** SLICE-0040, SLICE-0042, SLICE-0043, SLICE-0044, SLICE-0045 owner-accepted / DONE  
**Blocks:** MarketEpisode persistence, NativeListing→MarketEpisode attachment, PhysicalBoat fact persistence

## Objective

Given an explicit caller-supplied `PhysicalBoatId`, durably create and read the smallest accepted PhysicalBoat identity envelope, optionally linked to an already-admitted canonical `BoatDesignRef`, without inferring any physical-yacht facts and without introducing MarketEpisode or listing attachment yet.

This slice turns the accepted SLICE-0040 identity boundary into a real PostgreSQL PhysicalBoat identity. It deliberately stops before episode/listing linkage and before any of the SLICE-0044 `PHYSICAL_BOAT` fact fields are persisted.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: persist one stable real-yacht identity with an optional canonical design reference.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one inspection command against PostgreSQL 18 that creates a PhysicalBoat, reads it back exactly, proves idempotent retry and collision behavior, proves unresolved identity is allowed, proves sister ships may share one BoatDesignRef, and proves no design data or broker/listing identity is silently projected into the PhysicalBoat.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
SLICE-0045 delivered durable offer-state persistence on NativeListing. The next missing product identity primitive is the real yacht itself. Keeping PhysicalBoat creation separate from MarketEpisode and listing attachment avoids combining three new durable identity layers in one change and preserves the accepted sequence `PhysicalBoat → MarketEpisode → NativeListing attachment`.

## Why this slice exists

HullQ can now persist:

```text
professional publishing principal
→ NativeListing identity
→ NativeListing offer revisions
```

but it still cannot persist the real physical yacht that an episode/listing may later refer to.

The accepted identity model requires these to remain different identities:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId
```

and specifically permits:

```text
PhysicalBoat → optional BoatDesignRef
```

The repository already has durable canonical design authority in:

```text
canonical_boat_designs(id)
```

from the accepted legacy identity baseline. Therefore an optional `BoatDesignRef` in this slice must reference that existing authority rather than becoming an unvalidated text label or a second design store.

A PhysicalBoat is global yacht identity. It is not owned by the broker Organization that may later list it. Organization authorization belongs to listing/claim operations, not to the existence of the hull identity itself.

## Controlling artifacts

- Accepted marketplace identity boundary:
  - `docs/slices/SLICE-0040-acceptance-closure.md`
  - `src/hullq/domain/market_identity.py`
- Canonical BoatDesign persistence authority:
  - `src/hullq/persistence/sql/002_canonical_identity_schema.sql`
  - table `canonical_boat_designs`
- Alembic lineage:
  - SLICE-0042 baseline transition
  - current accepted Alembic head after SLICE-0045: `4d8e1a72c9f0`
- Accepted NativeListing identity/persistence:
  - `docs/slices/SLICE-0043-acceptance-closure.md`
- Accepted marketplace fact contract:
  - `docs/slices/SLICE-0044-acceptance-closure.md`
  - `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- Accepted NativeListing offer persistence:
  - `docs/slices/SLICE-0045-acceptance-closure.md`
- Product/architecture precedence:
  - `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
  - `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`

## In scope

- Reuse the accepted runtime-distinct `PhysicalBoatId` and `BoatDesignRef` identity types; do not replace them with interchangeable plain-ID semantics.
- One minimal durable `physical_boats` identity table (name may vary only if repository conventions require it).
- Caller-supplied stable `PhysicalBoatId` as the durable primary identity.
- Optional `BoatDesignRef` persisted as a real foreign key to `canonical_boat_designs(id)`.
- Creation timestamp generated durably by the server/database.
- Internal deterministic semantic fingerprint/hash if useful for exact idempotency/collision proof; it is not a marketplace field and MUST NOT be the sole authority for deciding semantic equality of an already-persisted PhysicalBoat.
- Create/read persistence functions with deterministic `CREATED | ALREADY_EXISTS | CONFLICT | DESIGN_NOT_FOUND` (or equivalently precise typed) outcomes.
- Race-safe concurrent creation semantics.
- Top-level transaction ownership/durability semantics consistent with SLICE-0043/0045.
- One Alembic migration descended from `4d8e1a72c9f0`.
- Real PostgreSQL 18 integration/adversarial tests.
- Owner inspection script ending in one explicit PASS/FAIL result.

## Explicitly out of scope

- `MarketEpisode` persistence;
- NativeListing→MarketEpisode attachment or migration of `native_listings.market_episode_id`;
- ExternalMarketObservation linkage;
- any of the 29 SLICE-0044 `PHYSICAL_BOAT` marketplace fact fields;
- marketed brand/model/builder claims;
- LOA/beam/draft/displacement/configuration/engine/accommodation facts;
- HIN/CIN persistence or using HIN/CIN as identity proof;
- boat name, registration, title, ownership, VAT or legal-status data;
- automatic PhysicalBoat deduplication or merge engine;
- identity matching from broker text, design, HIN, name or external listing data;
- automatic BoatDesign resolution;
- mutation/correction of an existing PhysicalBoat's design association;
- Organization ownership/control of PhysicalBoat identity;
- public listing publication/lifecycle/freshness;
- FastAPI endpoint;
- Astro/React UI or broker workspace;
- Search/ranking integration;
- media/document upload;
- LLM extraction;
- generic EAV/JSON marketplace-fact framework;
- SLICE-0047+ work.

## Required behavior

### 1. Hard identity boundary

The implementation MUST preserve the accepted distinction:

```text
BoatDesignRef != PhysicalBoatId
```

A `PhysicalBoatId` identifies one real yacht/hull identity. A `BoatDesignRef` identifies a canonical design shared by zero, one or many real yachts.

Hard:

```text
same BoatDesignRef
!= same PhysicalBoatId
```

and:

```text
PhysicalBoatId
must never be derived from BoatDesignRef
```

No display name, HIN/CIN, broker listing ID, BoatDesignRef or external-platform ID may be hashed/normalized into a PhysicalBoatId in this slice.

### 2. Minimal immutable creation envelope

The durable business identity envelope is exactly:

```text
PhysicalBoatId
optional BoatDesignRef
created_at
```

An internal content hash/fingerprint may be persisted for collision detection but is not part of marketplace truth.

No other yacht or listing facts belong in the row.

Creation semantics are immutable in this slice. There is no UPDATE operation for `boat_design_ref`.

This is intentional:

```text
PhysicalBoat created with BoatDesignRef = NONE
→ remains unresolved in SLICE-0046
```

A later explicit identity-resolution/correction capability may add a provenance-preserving association workflow. This slice must not silently mutate `NONE → value` or `value A → value B` merely because newer broker/design information appears.

### 3. Canonical BoatDesignRef integrity and result precedence

When a `BoatDesignRef` is supplied for a **new** `PhysicalBoatId`, it MUST already exist in the accepted canonical authority:

```text
canonical_boat_designs(id)
```

The database MUST enforce this with a foreign key (or an equally strong already-existing referential mechanism).

Hard for a not-yet-persisted PhysicalBoatId:

```text
new PhysicalBoatId
+ unknown BoatDesignRef
→ no PhysicalBoat row
→ typed DESIGN_NOT_FOUND / equivalent fail-closed result
```

Do not create a placeholder canonical BoatDesign row merely to satisfy the FK.

`BoatDesignRef = NONE` is valid and means unresolved design identity, not design absence.

For an **already-persisted** `PhysicalBoatId`, existing identity wins result classification before validating a different requested design reference as a new association. The implementation MUST compare the request against the exact durable `boat_design_ref` already stored for that PhysicalBoat:

```text
existing PhysicalBoatId + same stored BoatDesignRef
→ ALREADY_EXISTS

existing PhysicalBoatId + different requested BoatDesignRef
→ CONFLICT
```

This includes an existing PhysicalBoatId where the different requested BoatDesignRef is itself unknown to `canonical_boat_designs`:

```text
existing PhysicalBoatId stores X
+ retry/request supplies unknown Y
→ CONFLICT
→ NOT DESIGN_NOT_FOUND
→ existing row unchanged
```

The purpose is deterministic identity-collision semantics: once a PhysicalBoatId is occupied, the question is whether the immutable creation envelope matches the durable row, not whether a proposed replacement association could be admitted.

### 4. Sister-ship semantics

The relationship is many PhysicalBoats to one BoatDesign.

Hard:

```text
PhysicalBoat A → BoatDesign X
PhysicalBoat B → BoatDesign X
```

is valid when `A != B`.

There MUST be no uniqueness constraint on `boat_design_ref`.

The implementation must not deduplicate or merge PhysicalBoat identities because they share a design.

### 5. Idempotent retry / collision semantics

The caller supplies the `PhysicalBoatId`.

Same `PhysicalBoatId` + same immutable semantic creation envelope:

```text
→ ALREADY_EXISTS
→ no duplicate row
```

Same `PhysicalBoatId` + different immutable semantic creation envelope, including:

```text
NONE vs BoatDesignRef X
BoatDesignRef X vs BoatDesignRef Y
```

must return:

```text
→ CONFLICT
→ existing PhysicalBoat unchanged
```

No last-write-wins behavior and no implicit repair/update.

`created_at` is server-generated and MUST NOT make an otherwise identical retry conflict.

For an existing PhysicalBoatId, semantic equality/collision MUST be decided by exact comparison of the durable business envelope, specifically the stored nullable `boat_design_ref` versus the requested nullable `BoatDesignRef`. An internal fingerprint/hash may be used as an optimization or diagnostic but MUST NOT be the sole authority for returning `ALREADY_EXISTS` or `CONFLICT`.

### 6. Race-safe concurrent creation

Two concurrent calls for the same `PhysicalBoatId` must not leak a database uniqueness exception as the public persistence result.

Required deterministic outcomes:

```text
same ID + same envelope
→ one CREATED
→ one ALREADY_EXISTS
```

```text
same ID + different envelope
→ one CREATED
→ one CONFLICT
```

The database ends with exactly one row for that PhysicalBoatId.

Use `INSERT ... ON CONFLICT ...` or an equivalently race-safe mechanism; do not rely on a check-then-insert window.

After any insert conflict caused by an occupied PhysicalBoatId, fetch/compare the actual durable row and classify the result from its exact stored nullable `boat_design_ref`; do not infer equality only from caller inputs or a hash.

### 7. No broker ownership or claim-authority implication

A PhysicalBoat is global market identity, not an Organization-owned listing resource.

Therefore this slice MUST NOT add:

```text
publishing_organization_id
created_by_account_id
broker_id
seller_id
```

to the PhysicalBoat identity merely because later NativeListings are organization-scoped.

Likewise, linking a PhysicalBoat to a canonical BoatDesign MUST NOT mean that a broker verified the individual yacht's physical specifications.

Hard:

```text
PhysicalBoat → BoatDesignRef
!= BoatDesign baseline facts are PhysicalBoat facts
```

No design baseline/configuration field may be copied into a PhysicalBoat row or marketplace fact table in this slice.

### 8. Transaction ownership / durability

Retain the accepted persistence invariant:

> A returned `CREATED` result means the PhysicalBoat row is already durably committed independent of later caller action.

If the persistence function receives a caller-supplied psycopg connection, it MUST fail closed unless it can safely own a top-level transaction, consistent with the SLICE-0043/0045 IDLE-connection guard.

Do not silently commit or rollback unrelated caller work.

`ALREADY_EXISTS`, `CONFLICT` and `DESIGN_NOT_FOUND` must leave no unintended writes.

### 9. Typed readback

Provide typed readback for one `PhysicalBoatId` sufficient to recover exactly:

```text
PhysicalBoatId
optional BoatDesignRef
created_at
```

A missing PhysicalBoat returns typed `None`/not-found behavior and must not invent a design association.

Readback must not join/project BoatDesign baseline data into PhysicalBoat truth. It may return only the reference itself.

### 10. Migration governance

Add exactly one Alembic revision descended from:

```text
4d8e1a72c9f0
```

Do not modify:

```text
src/hullq/persistence/sql/001_initial_schema.sql
src/hullq/persistence/sql/002_canonical_identity_schema.sql
```

and do not revive the legacy numbered-SQL migration path.

Migration validation MUST prove:

- repository has exactly one Alembic head;
- upgraded PostgreSQL 18 reaches that head;
- `physical_boats.boat_design_ref` (or exact equivalent) references the existing `canonical_boat_designs(id)` authority;
- the design reference is nullable;
- it is not unique.

Tests that previously used the symbolic Alembic `head` merely to inspect an earlier slice's exact schema should be pinned to the historical revision they intend to test rather than weakened or deleted.

### 11. Owner-visible end-to-end proof

Provide one inspection command using real PostgreSQL 18 that demonstrates at minimum:

```text
canonical BoatDesign X exists
+ PhysicalBoat A with BoatDesignRef X
→ CREATED
→ exact typed readback

same A + same X
→ ALREADY_EXISTS
→ exactly one durable row

same A + different BoatDesignRef Y
→ CONFLICT
→ A still references X

same existing A + unknown BoatDesignRef Z
→ CONFLICT
→ not DESIGN_NOT_FOUND
→ A still references X

PhysicalBoat B + BoatDesignRef NONE
→ CREATED
→ exact readback keeps NONE

retry B + BoatDesignRef X
→ CONFLICT
→ no silent unresolved→resolved mutation

PhysicalBoat C + same BoatDesignRef X
→ CREATED
→ A and C coexist as sister ships

new PhysicalBoat D + unknown BoatDesignRef
→ DESIGN_NOT_FOUND / equivalent
→ zero row for D

concurrent same-ID/same-envelope creation
→ CREATED + ALREADY_EXISTS
→ one row

concurrent same-ID/different-envelope creation
→ CREATED + CONFLICT
→ one row
```

The inspection must also explicitly establish that no PhysicalBoat marketplace fact fields, broker Organization ownership, MarketEpisode or NativeListing attachment were introduced by the capability.

End with:

```text
PHYSICAL BOAT IDENTITY RESULT -> PASS
```

## Deliverables

- minimal typed PhysicalBoat persistence representation/readback using the accepted identity types;
- one Alembic migration from `4d8e1a72c9f0`;
- race-safe create/read persistence implementation;
- unit tests;
- real PostgreSQL 18 integration/adversarial tests;
- owner inspection script;
- this slice document updated to `REVIEW` with completion evidence only.

## Acceptance criteria

- [ ] `PhysicalBoatId` is durably persisted as a distinct real-yacht identity and is not interchangeable with BoatDesign/MarketEpisode/NativeListing identities.
- [ ] The durable creation envelope contains only PhysicalBoatId, optional BoatDesignRef, server-side created timestamp and permitted internal collision metadata.
- [ ] A supplied BoatDesignRef for a new PhysicalBoatId is enforced against existing `canonical_boat_designs(id)`; unresolved/NONE remains valid.
- [ ] New PhysicalBoatId + unknown BoatDesignRef fails closed with DESIGN_NOT_FOUND/equivalent and creates no placeholder design or PhysicalBoat row.
- [ ] Existing PhysicalBoatId result classification is based on exact comparison with its durable stored nullable BoatDesignRef: same → ALREADY_EXISTS; different → CONFLICT, even when the newly supplied different ref is unknown.
- [ ] Internal fingerprints/hashes are never the sole authority for semantic retry/collision classification.
- [ ] Multiple PhysicalBoatIds may reference the same BoatDesignRef; sharing a design never deduplicates real yachts.
- [ ] Same ID/same envelope is idempotent; same ID/different immutable envelope returns CONFLICT without mutation.
- [ ] Existing unresolved PhysicalBoat identity is not silently mutated to a resolved design link in this slice.
- [ ] Concurrent same-ID creation is race-safe and returns deterministic typed outcomes rather than leaking uniqueness errors.
- [ ] No Organization/account ownership or broker claim authority is attached to PhysicalBoat identity.
- [ ] BoatDesign linkage does not project design/configuration baseline data into PhysicalBoat truth.
- [ ] Successful creation is durably committed; pre-existing caller transactions cannot produce nested-transaction false success.
- [ ] Typed readback returns exactly PhysicalBoatId, optional BoatDesignRef and created_at, with not-found handled explicitly.
- [ ] Exactly one Alembic migration descends from `4d8e1a72c9f0`; repository/database each retain one Alembic head.
- [ ] Legacy 001/002 SQL schema files remain unchanged.
- [ ] Real PostgreSQL 18 tests cover FK integrity, unresolved design, sister ships, retry/collision, result precedence, concurrency, durability and readback.
- [ ] Owner inspection actually runs against PostgreSQL 18 and ends `PHYSICAL BOAT IDENTITY RESULT -> PASS`.
- [ ] Full repository test/quality/security gates pass.
- [ ] GitHub Actions CI passes on the exact final implementation HEAD.
- [ ] Manufacturer artifact reproducibility passes on the exact final implementation HEAD.
- [ ] Independent exact-head review finds no unresolved material issue.
- [ ] Project Owner explicitly accepts the exact reviewed HEAD before merge.

## Expected touch points

Expected only where needed:

- `src/hullq/domain/...` only if a minimal PhysicalBoat record/result type is not already expressible with accepted identity types;
- `src/hullq/persistence/...` for PhysicalBoat create/read persistence;
- `alembic/versions/...` for one new migration;
- `tests/unit/...`;
- `tests/persistence/...`;
- `scripts/inspect_physical_boat_identity.py` (name may vary minimally);
- this slice document.

Avoid modifying unrelated architecture/specification files merely to restate this slice.

## Required implementation evidence / adversarial cases

At minimum, independently observable tests must cover:

1. create with valid BoatDesignRef;
2. create unresolved with no BoatDesignRef;
3. exact typed readback of both;
4. missing readback;
5. same ID/same envelope idempotent retry;
6. same ID `NONE` vs design collision;
7. same ID design X vs design Y collision;
8. new ID + unknown design FK/reference failure produces typed DESIGN_NOT_FOUND/equivalent and zero row;
9. existing ID + different unknown design produces CONFLICT, not DESIGN_NOT_FOUND, and leaves the row unchanged;
10. direct exact durable-row comparison is authoritative for existing-ID idempotency/collision classification; a stored hash alone cannot authorize ALREADY_EXISTS;
11. two different PhysicalBoatIds sharing one BoatDesignRef both persist;
12. no uniqueness on BoatDesignRef;
13. concurrent same-ID/same-envelope create;
14. concurrent same-ID/different-envelope create;
15. transaction called while connection already has caller-owned transaction fails before write;
16. successful CREATED survives independent subsequent connection/readback without caller commit;
17. rollback/error does not leave partial row;
18. migration has exactly one parent `4d8e1a72c9f0` and leaves one Alembic head;
19. raw PostgreSQL rejects a non-existent non-null BoatDesignRef through FK;
20. persisted schema contains no MarketEpisode/listing attachment/Organization ownership/PhysicalBoat fact columns.

## Handoff rule

Implementation may begin only after this readiness document itself is independently exact-head reviewed, CI/reproducibility gates are green, and the readiness PR is merged to `main`.

After implementation:

```text
implementation report
→ independent exact-head review
→ AMEND until clean
→ ACCEPT
→ explicit Project Owner acceptance
→ guarded merge
→ acceptance closure
→ FINISH_SLICE 0046
```

Do not start SLICE-0047 automatically.
