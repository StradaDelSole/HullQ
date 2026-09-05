# SLICE-0046 — Acceptance closure

**Slice:** SLICE-0046  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #147  
**Accepted implementation HEAD:** `69860ae0d891e4e741e155012ab7c4a3ff97a27f`  
**Implementation merge commit:** `39bd5af946649f96133176e4dc865bc53486fe13`  
**Independent final ACCEPT review:** `5121313225`  
**Owner acceptance:** explicitly recorded 2026-09-05

## Accepted capability

SLICE-0046 adds the first durable runtime identity for one real physical yacht while preserving the accepted marketplace identity boundary:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId
```

The accepted durable envelope is exactly:

```text
PhysicalBoatId
optional BoatDesignRef
created_at
```

No MarketEpisode, listing attachment, broker/Organization ownership, PhysicalBoat marketplace facts, API, UI, media, lifecycle or dedup/merge behavior was introduced.

## Durable PhysicalBoat identity

The accepted migration adds one `physical_boats` table with:

```text
physical_boat_id  primary key
boat_design_ref   nullable FK → canonical_boat_designs(id)
created_at        server-generated timestamp
```

`boat_design_ref` is deliberately not unique. Multiple distinct PhysicalBoatIds may reference the same canonical BoatDesign because sister ships are distinct real yachts.

Hard accepted rule:

```text
same BoatDesignRef
!= same PhysicalBoatId
```

A PhysicalBoat may also remain design-unresolved:

```text
BoatDesignRef = NONE
```

This means unresolved design identity, not proof that no design exists.

## Immutable creation semantics

SLICE-0046 exposes no update path for an existing PhysicalBoat's BoatDesign association.

Accepted behavior:

```text
existing PhysicalBoatId + same stored nullable BoatDesignRef
→ ALREADY_EXISTS

existing PhysicalBoatId + different nullable BoatDesignRef
→ CONFLICT
→ existing row unchanged
```

This includes a retry where the newly supplied different BoatDesignRef is itself unknown to the canonical design authority:

```text
existing PhysicalBoatId stores X
+ request supplies unknown Y
→ CONFLICT
→ NOT DESIGN_NOT_FOUND
```

For a genuinely new PhysicalBoatId:

```text
new PhysicalBoatId + unknown non-null BoatDesignRef
→ DESIGN_NOT_FOUND
→ no PhysicalBoat row
→ no placeholder BoatDesign row
```

Classification is based on the exact stored nullable `boat_design_ref`, not a content hash.

## Race-safe creation

Creation uses PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` semantics and reads the durable row after an occupied-ID conflict.

Accepted concurrent outcomes:

```text
same PhysicalBoatId + same envelope
→ one CREATED
→ one ALREADY_EXISTS
→ exactly one durable row
```

```text
same PhysicalBoatId + different envelope
→ one CREATED
→ one CONFLICT
→ exactly one durable row
```

No raw uniqueness exception is exposed as the business result.

## Canonical BoatDesign integrity

A non-null BoatDesignRef for a new PhysicalBoat must already exist in the accepted canonical authority:

```text
canonical_boat_designs(id)
```

The database itself enforces the relationship via foreign key.

The accepted implementation does not copy or project canonical BoatDesign baseline/configuration values into PhysicalBoat truth.

Hard:

```text
PhysicalBoat → BoatDesignRef
!= BoatDesign baseline facts are PhysicalBoat facts
```

## Transaction ownership and durability

The accepted persistence path retains the durability invariant established by earlier marketplace persistence slices:

> A returned `CREATED` result means the row is already durably committed independent of later caller action.

`create_physical_boat()` therefore rejects a caller-supplied psycopg connection that is not `IDLE`, rather than allowing `conn.transaction()` to degrade into a nested savepoint and return a misleading CREATED result.

Real PostgreSQL tests prove that a CREATED row is immediately visible from a separate connection without an additional caller commit.

## Typed readback

Accepted readback recovers exactly:

```text
PhysicalBoatId
optional BoatDesignRef
created_at
```

A missing identity returns not-found/`None` behavior. Readback does not join BoatDesign baseline facts into the PhysicalBoat representation.

## Migration governance

The accepted Alembic revision is:

```text
7a3f0e5c1b6d
```

and descends from:

```text
4d8e1a72c9f0
```

The legacy numbered SQL files were not modified or revived as a migration path.

## Independent review and remote verification

Independent review was performed against exact implementation HEAD:

```text
69860ae0d891e4e741e155012ab7c4a3ff97a27f
```

No material findings remained.

Accepted review:

```text
5121313225
```

Exact-head remote verification:

```text
CI run 33966646013
→ SUCCESS
→ quality ubuntu: SUCCESS
→ quality windows: SUCCESS
→ dependency audit: SUCCESS
→ PostgreSQL 18 integration/replay chain: SUCCESS

Manufacturer artifact reproducibility run 33966646056
→ SUCCESS
```

The implementation handoff also reported local PostgreSQL 18 owner inspection ending:

```text
PHYSICAL BOAT IDENTITY RESULT -> PASS
```

The independent review additionally inspected the implementation, migration and real PostgreSQL adversarial tests corresponding to that owner-visible proof.

## Scope retained

SLICE-0046 deliberately did not add:

- MarketEpisode persistence;
- NativeListing→MarketEpisode attachment;
- ExternalMarketObservation linkage;
- PhysicalBoat marketplace fact fields;
- HIN/CIN identity proof;
- broker/Organization ownership of PhysicalBoat identity;
- automatic identity matching, deduplication or merge;
- BoatDesign resolution/correction workflow;
- FastAPI/Astro/React surface;
- media, lifecycle/freshness or search integration.

These boundaries remain intact after acceptance.

## PROJECT_STATE freshness closure

This acceptance closure advances the highest owner-accepted slice from 0045 to 0046.

In the same closure PR, `docs/PROJECT_STATE.md` is therefore updated to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0046
PROJECT_STATE_QUEUE_SLICE:    0047
```

It also moves durable PhysicalBoat identity into the built-capability list, removes the stale statement that PhysicalBoat persistence is absent, and records the current product horizon:

```text
SLICE-0047
MarketEpisode persistence + controlled NativeListing attachment

SLICE-0048 target
first visible listing vertical slice
```

`scripts/validate_repository.py` must fail this closure if the PROJECT_STATE marker and highest acceptance-closure file are not identical.

## Product execution checkpoint

After SLICE-0046, estimated remaining slice distance to the first externally visible listing is:

```text
2 slices including current queue SLICE-0047
and target vertical SLICE-0048
```

SLICE-0047 is justified before the visible vertical slice because it supplies the minimum missing durable relationship needed to connect a real yacht to a market episode and a HullQ NativeListing without collapsing those identities.

No additional foundation-only slice should be inserted before SLICE-0048 unless a concrete blocking invariant is found during 0047 reassessment.

## Closure decision

```text
SLICE-0046 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
