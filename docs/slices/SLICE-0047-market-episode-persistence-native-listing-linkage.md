# SLICE-0047 — MarketEpisode persistence + controlled NativeListing linkage

**Type:** IMPLEMENTATION READINESS  
**Status:** READY_FOR_REVIEW  
**Base main:** `3c3599c9131c7226fb73042bf4ea4f537179f635`  
**Product horizon:** this slice must unblock SLICE-0048, the first visible listing vertical slice.

## 1. One capability

Persist the missing identity/linkage segment between an accepted durable `PhysicalBoat` and an accepted durable `NativeListing`:

```text
PhysicalBoat
    ↓
MarketEpisode
    ↓
NativeListing creation envelope
```

The capability is deliberately bounded to:

1. durable immutable `MarketEpisode` identity persistence;
2. exact `MarketEpisodeId -> PhysicalBoatId` referential integrity;
3. controlled use of the already-existing nullable `NativeListing.market_episode_id` creation-envelope field;
4. typed exact readback and owner-visible PostgreSQL proof.

This slice does **not** add a post-creation mutable attach/detach workflow. `market_episode_id` was accepted in SLICE-0043 as part of the immutable NativeListing creation envelope and remains so.

## 2. Product-execution justification

Current estimated distance to the first externally visible listing is two slices including SLICE-0047 and the SLICE-0048 vertical slice.

SLICE-0047 is justified before the visible vertical because it supplies the smallest durable identity chain that 0048 can read without collapsing identities:

```text
PhysicalBoatId != MarketEpisodeId != NativeListingId
```

SLICE-0048 must then be able to use the concrete sequence:

```text
create PhysicalBoat
→ create MarketEpisode for that PhysicalBoat
→ create authorized NativeListing already linked to that MarketEpisode
→ write accepted LISTING_OFFER revision
→ expose minimal FastAPI read model
→ render simplest public listing page
```

No additional marketplace foundation slice should be inserted between accepted SLICE-0047 and the first-visible SLICE-0048 unless a material blocker is discovered.

## 3. Existing accepted boundaries that control this slice

The accepted SLICE-0040 identity relation is:

```text
MarketEpisode(id=MarketEpisodeId, physical_boat_id=PhysicalBoatId)
NativeListing(id=NativeListingId, market_episode_id=MarketEpisodeId | NONE)
```

Hard identity rule:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId
```

SLICE-0046 already provides durable `physical_boats` authority.

SLICE-0043 already persists a nullable `native_listings.market_episode_id` inside the immutable NativeListing creation envelope. It intentionally had no FK because a durable MarketEpisode authority did not yet exist.

0047 must complete that missing reference boundary without inventing a second linkage source of truth.

## 4. Durable MarketEpisode schema

Add exactly one minimal `market_episodes` table with:

```text
market_episode_id   TEXT PRIMARY KEY
physical_boat_id    TEXT NOT NULL
created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Required PostgreSQL integrity:

```text
market_episodes.physical_boat_id
    → physical_boats.physical_boat_id
```

No additional episode business fields are authorized in this slice.

Specifically absent:

- lifecycle/status;
- first-seen / last-seen / freshness;
- sold/withdrawn/disappeared semantics;
- seller/broker ownership;
- price;
- source observations;
- continuity confidence;
- dedup/merge metadata.

Multiple distinct `MarketEpisodeId` values may reference the same `PhysicalBoatId`. A later sale episode for the same yacht is not an identity conflict merely because the physical boat is the same.

## 5. MarketEpisode creation semantics

Provide a typed runtime operation equivalent to:

```text
create_market_episode(conn, market_episode)
```

and typed readback equivalent to:

```text
fetch_market_episode(conn, market_episode_id)
```

Use the accepted SLICE-0040 `MarketEpisode`, `MarketEpisodeId`, and `PhysicalBoatId` runtime types. Do not create parallel identity classes.

Creation outcomes must be mechanically distinct:

```text
CREATED
ALREADY_EXISTS
CONFLICT
PHYSICAL_BOAT_NOT_FOUND
```

### 5.1 Deterministic collision priority

For an already-occupied `MarketEpisodeId`, classify from the exact durable row before treating the requested `PhysicalBoatId` as a new-reference lookup problem:

```text
existing MarketEpisodeId
+ same stored PhysicalBoatId
→ ALREADY_EXISTS

existing MarketEpisodeId
+ different requested PhysicalBoatId
→ CONFLICT
```

This remains `CONFLICT` even when the different requested `PhysicalBoatId` does not exist.

For a genuinely new MarketEpisode identity:

```text
new MarketEpisodeId
+ existing PhysicalBoatId
→ CREATED

new MarketEpisodeId
+ unknown PhysicalBoatId
→ PHYSICAL_BOAT_NOT_FOUND
→ zero durable MarketEpisode rows
```

No raw PostgreSQL FK exception may escape as ordinary business behavior.

### 5.2 Race safety

The implementation must be race-safe for at least:

```text
same MarketEpisodeId + same PhysicalBoatId
→ exactly one CREATED, one ALREADY_EXISTS

same MarketEpisodeId + different existing PhysicalBoatIds
→ exactly one CREATED, one CONFLICT
```

No duplicate row, unhandled uniqueness exception, or silent overwrite.

### 5.3 Transaction ownership

Mirror the accepted SLICE-0043/0045/0046 transaction-ownership rule:

```text
CREATED means already durably committed
```

The write operation must fail closed before writing if the supplied psycopg connection is not `TransactionStatus.IDLE`; it must own and commit its own top-level transaction rather than degrade to a caller-owned savepoint.

## 6. Controlled NativeListing linkage

Do **not** add a new mutable linkage table and do **not** add an `attach_native_listing_to_market_episode()` mutation in this slice.

The canonical NativeListing→MarketEpisode relationship remains the already-persisted nullable column:

```text
native_listings.market_episode_id
```

0047 must add PostgreSQL referential integrity:

```text
native_listings.market_episode_id
    → market_episodes.market_episode_id
```

with NULL remaining valid.

Therefore:

```text
NativeListing(market_episode_id = NONE)
→ remains valid/unresolved

NativeListing(market_episode_id = existing MarketEpisodeId)
→ may be created

NativeListing(market_episode_id = unknown MarketEpisodeId)
→ fail closed
→ zero listing row
```

No later mutation from `NONE` to a MarketEpisode is introduced here. If the product later requires post-creation resolution, it must be designed as a separate provenance-safe capability rather than silently rewriting the accepted immutable creation envelope.

## 7. NativeListing runtime outcome for missing MarketEpisode

The existing SLICE-0043 creation result vocabulary is currently:

```text
CREATED | ALREADY_EXISTS | DENIED | CONFLICT
```

Because an explicitly supplied but nonexistent `MarketEpisodeId` is neither authorization denial nor immutable-envelope collision, 0047 may extend the typed result vocabulary with exactly one additional outcome:

```text
MARKET_EPISODE_NOT_FOUND
```

Required behavior:

```text
eligible publisher
+ new NativeListingId
+ unknown non-null MarketEpisodeId
→ MARKET_EPISODE_NOT_FOUND
→ zero NativeListing row
```

### 7.1 NativeListing outcome priority

Preserve SLICE-0043's authorization-first boundary. Result priority must be deterministic:

```text
1. evaluate accepted SLICE-0041 publishing eligibility
2. if DENIED → DENIED, before any database write or linkage classification
3. only for ALLOWED callers, preserve existing NativeListingId collision semantics
4. only for a genuinely new NativeListingId may an unknown non-null MarketEpisodeId become MARKET_EPISODE_NOT_FOUND
```

For an ALLOWED caller and an already-existing `NativeListingId`, existing-envelope comparison is authoritative:

```text
existing NativeListingId + exact original immutable envelope
→ ALREADY_EXISTS

existing NativeListingId + different immutable envelope
→ CONFLICT
```

An unknown different MarketEpisodeId supplied against an already-occupied NativeListingId by an ALLOWED caller must not relabel that existing-envelope conflict as `MARKET_EPISODE_NOT_FOUND`.

Authorization remains independently enforced by the accepted SLICE-0041 evaluator. An ineligible caller remains `DENIED` regardless of whether the requested episode exists; `MARKET_EPISODE_NOT_FOUND` must never leak or substitute for the authorization decision.

## 8. Migration governance and existing data

The new Alembic revision must descend from the current single repository head:

```text
7a3f0e5c1b6d
```

After 0047 there must still be exactly one Alembic head.

Do not synthesize placeholder `MarketEpisode` or `PhysicalBoat` identities to make old data fit.

A pre-0047 database may contain non-null `native_listings.market_episode_id` text because SLICE-0043 intentionally stored the creation-envelope field before a durable MarketEpisode authority existed. 0047 has no truthful PhysicalBoat mapping from which it could reconstruct such an episode.

Therefore if any such pre-existing non-null value would be orphaned by the new FK, upgrade must fail closed rather than fabricate a MarketEpisode, silently null the value, or rewrite the NativeListing envelope. A clear migration failure is preferable to invented identity truth.

Existing `NULL` NativeListing episode links remain valid through upgrade.

Do not introduce cascade-delete behavior across either identity FK in this slice.

## 9. Typed readback

`fetch_market_episode()` must return the exact accepted runtime identity relationship:

```text
MarketEpisode(
    id=MarketEpisodeId(...),
    physical_boat_id=PhysicalBoatId(...),
)
```

plus persisted `created_at` in a dedicated persistence record if needed.

Existing `fetch_native_listing()` must continue to reconstruct:

```text
NativeListing.market_episode_id = MarketEpisodeId | NONE
```

No join may project BoatDesign facts, PhysicalBoat facts, listing offer facts, or lifecycle state into either identity object.

## 10. Required PostgreSQL adversarial coverage

Real PostgreSQL 18 tests must cover at minimum:

1. create MarketEpisode for existing PhysicalBoat → CREATED;
2. exact typed MarketEpisode readback;
3. identical retry → ALREADY_EXISTS;
4. same episode ID + different existing PhysicalBoat → CONFLICT;
5. same episode ID + different unknown PhysicalBoat → CONFLICT;
6. new episode ID + unknown PhysicalBoat → PHYSICAL_BOAT_NOT_FOUND and zero row;
7. two episodes for same PhysicalBoat are both valid;
8. concurrent same/same episode creation → one CREATED + one ALREADY_EXISTS;
9. concurrent same/different episode creation → one CREATED + one CONFLICT;
10. non-IDLE connection rejects MarketEpisode write before mutation;
11. CREATED survives writer connection close without caller commit;
12. NativeListing with NULL episode remains creatable;
13. authorized NativeListing with existing episode link → CREATED;
14. typed NativeListing readback preserves exact MarketEpisodeId;
15. new NativeListing with unknown episode → MARKET_EPISODE_NOT_FOUND and zero row;
16. existing NativeListing + exact original envelope → ALREADY_EXISTS;
17. existing NativeListing + different episode envelope → CONFLICT;
18. existing NativeListing + different unknown episode → CONFLICT, not MARKET_EPISODE_NOT_FOUND;
19. authorization DENIED remains DENIED and writes zero rows regardless of episode input;
20. raw SQL cannot persist a non-null NativeListing episode reference that violates the FK;
21. migration from the prior accepted head preserves existing NULL NativeListing episode links;
22. migration from the prior accepted head with a pre-existing orphan non-null NativeListing episode reference fails closed and does not fabricate/null/rewrite identity state;
23. Alembic reports exactly one head after upgrade.

Tests should prefer semantic assertions over implementation-specific SQL shape.

## 11. Owner-visible proof

Add an owner inspection script, expected name:

```text
scripts/inspect_market_episode_linkage.py
```

It must run against disposable PostgreSQL 18 state and visibly prove at least:

```text
PhysicalBoat create/read
MarketEpisode create/read
MarketEpisode identical retry
MarketEpisode collision
unknown PhysicalBoat fail-closed
NativeListing unresolved creation
NativeListing creation linked to real MarketEpisode
NativeListing typed linked readback
unknown MarketEpisode fail-closed
no post-creation mutable attach API/table introduced
```

Final success marker:

```text
MARKET EPISODE LINKAGE RESULT -> PASS
```

Do not mark this proof verified unless the script actually executes successfully against PostgreSQL 18.

## 12. Expected implementation touch points

Expected bounded changes include:

```text
src/hullq/persistence/market_episode.py                    # new
src/hullq/persistence/native_listing.py                    # bounded FK-aware creation behavior
alembic/versions/<revision>_market_episode_linkage.py      # new
scripts/inspect_market_episode_linkage.py                  # new
tests/unit/test_market_episode_persistence_unit.py         # new / equivalent
tests/persistence/test_market_episode_persistence.py       # new / equivalent
tests/... native-listing tests                             # bounded additions
docs/slices/SLICE-0047-...md                               # implementation evidence/status
```

Do not modify `docs/PROJECT_STATE.md` during readiness or implementation. The accepted-slice marker advances only in the acceptance-closure PR after explicit owner acceptance.

## 13. Explicitly out of scope

Do not add in SLICE-0047:

- FastAPI endpoint;
- Astro/React page;
- broker workspace or Auth0 UI wiring;
- media/document upload;
- lifecycle/freshness/status;
- SOLD/ACTIVE/STALE semantics;
- public publication policy;
- PhysicalBoat marketplace fact persistence;
- dedup/merge or HIN/CIN resolution;
- SAME/NEW/UNRESOLVED episode-continuity inference;
- external marketplace observations;
- search indexing/projection;
- Saved Search/monitoring/alerts;
- generic EAV/event-sourcing framework;
- post-creation NativeListing attach/detach mutation.

These exclusions are deliberate so SLICE-0048 remains the immediate next product target.

## 14. Acceptance boundary

SLICE-0047 may be recommended `REVIEW` only when:

- the capability remains one bounded identity/linkage slice;
- all required runtime outcomes are typed and fail closed;
- PostgreSQL enforces both `MarketEpisode→PhysicalBoat` and nullable `NativeListing→MarketEpisode` references;
- immutable NativeListing creation semantics remain intact;
- concurrency and top-level transaction ownership are proven;
- real PostgreSQL 18 tests are green;
- the owner inspection script has actually passed or is explicitly reported NOT VERIFIED;
- remote exact-head CI and Manufacturer reproducibility are observed before independent ACCEPT;
- no 0048/API/UI or unrelated marketplace scope has started.

After owner acceptance and closure, `docs/PROJECT_STATE.md` must advance in the same closure PR to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0047
PROJECT_STATE_QUEUE_SLICE: 0048
```

and the current product horizon should state that the next slice is the first visible listing vertical slice.
