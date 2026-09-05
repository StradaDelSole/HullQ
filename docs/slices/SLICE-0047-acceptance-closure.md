# SLICE-0047 — Acceptance closure

**Slice:** SLICE-0047  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #151  
**Accepted implementation HEAD:** `129095f90496f49483fd69d655dc041f4f31914f`  
**Implementation merge commit:** `1e774c788713cbaa9b0f6601557e2e1ce8f89aa3`  
**Independent final ACCEPT review:** `5122907261`  
**Owner acceptance:** explicitly recorded 2026-09-05

## Accepted capability

SLICE-0047 completes the minimum durable marketplace identity/linkage chain needed before the first visible listing vertical slice:

```text
PhysicalBoat
    ↓
MarketEpisode
    ↓
NativeListing creation envelope
```

It adds durable immutable `MarketEpisode` persistence, exact `MarketEpisodeId → PhysicalBoatId` referential integrity, and PostgreSQL-backed validation of the already-existing nullable `NativeListing.market_episode_id` creation-envelope field.

The accepted identity boundary remains:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

No identity collapse, lifecycle model, media flow, public API/UI or post-creation attach/detach mutation was introduced.

## Durable MarketEpisode identity

The accepted migration adds the minimal `market_episodes` authority:

```text
market_episode_id   TEXT PRIMARY KEY
physical_boat_id    TEXT NOT NULL
created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

with database-enforced integrity:

```text
market_episodes.physical_boat_id
    → physical_boats.physical_boat_id
```

Multiple MarketEpisodeIds may reference the same PhysicalBoatId. A later market episode for the same real yacht is therefore not an identity conflict merely because the underlying PhysicalBoat is the same.

No lifecycle/status, first-seen/last-seen, seller ownership, price, source-observation, continuity-confidence, dedup/merge or other episode-business fields were added.

## Deterministic MarketEpisode creation semantics

Accepted runtime outcomes are:

```text
CREATED
ALREADY_EXISTS
CONFLICT
PHYSICAL_BOAT_NOT_FOUND
```

Collision priority is based on the durable existing row:

```text
existing MarketEpisodeId + same stored PhysicalBoatId
→ ALREADY_EXISTS

existing MarketEpisodeId + different requested PhysicalBoatId
→ CONFLICT
```

The second case remains `CONFLICT` even if the different requested PhysicalBoatId itself does not exist.

For a genuinely new MarketEpisodeId:

```text
new id + existing PhysicalBoatId
→ CREATED

new id + unknown PhysicalBoatId
→ PHYSICAL_BOAT_NOT_FOUND
→ zero MarketEpisode rows
```

Creation is race-safe through PostgreSQL conflict handling and exact durable-row classification. Concurrent same-envelope creation yields one `CREATED` and one `ALREADY_EXISTS`; concurrent different-envelope creation for the same MarketEpisodeId yields one `CREATED` and one `CONFLICT`.

## Transaction ownership and durability

SLICE-0047 preserves the accepted marketplace persistence invariant:

```text
CREATED means already durably committed
```

The MarketEpisode write path rejects a caller-supplied psycopg connection that is not `TransactionStatus.IDLE`, owns its top-level transaction and commits before returning `CREATED`.

No caller-owned savepoint may masquerade as a durable successful creation.

## Controlled NativeListing linkage

The canonical NativeListing→MarketEpisode relationship remains the field already accepted in SLICE-0043:

```text
native_listings.market_episode_id
```

SLICE-0047 deliberately did not add a second link table or an attach/detach mutation.

The accepted migration adds database referential integrity:

```text
native_listings.market_episode_id
    → market_episodes.market_episode_id
```

while preserving NULL as a valid unresolved state.

Accepted behavior:

```text
NativeListing(market_episode_id = NONE)
→ valid unresolved listing identity

new NativeListing + existing MarketEpisodeId
→ may be created if publishing eligibility allows it

new NativeListing + unknown non-null MarketEpisodeId
→ MARKET_EPISODE_NOT_FOUND
→ zero listing row
```

There is no post-creation mutation from `NONE` to a MarketEpisode in this slice. A later need for post-creation resolution must be designed as a separate provenance-safe capability rather than silently rewriting the immutable creation envelope.

## NativeListing result priority

SLICE-0047 adds exactly one new NativeListing creation outcome:

```text
MARKET_EPISODE_NOT_FOUND
```

The accepted priority remains authorization-first and collision-safe:

```text
1. evaluate SLICE-0041 publishing eligibility
2. DENIED remains DENIED before linkage classification/write
3. for allowed callers, classify an occupied NativeListingId by the exact existing immutable envelope
4. only a genuinely new NativeListingId with an unknown non-null MarketEpisodeId may return MARKET_EPISODE_NOT_FOUND
```

Therefore an already-occupied NativeListingId with a different supplied MarketEpisodeId remains `CONFLICT`, even if that newly supplied episode ID does not exist.

## Migration governance

The accepted Alembic revision is:

```text
4c9a0dcc98bb
```

and descends from the accepted SLICE-0046 head:

```text
7a3f0e5c1b6d
```

The migration creates `market_episodes` and adds the NativeListing foreign key. Existing NULL NativeListing links remain valid. Existing non-null orphan MarketEpisode references fail migration rather than being silently nulled, backfilled or grandfathered.

Exactly one Alembic head remains after the slice.

## Independent review and remote verification

Independent review ultimately accepted exact implementation HEAD:

```text
129095f90496f49483fd69d655dc041f4f31914f
```

Accepted review:

```text
5122907261
```

The review independently confirmed that the final base-sync delta after the previously reviewed implementation changed only the accepted CI workflow file and did not alter any SLICE-0047 runtime, persistence, migration or test file.

Exact-head remote verification:

```text
CI run 33990690346
→ SUCCESS
→ quality ubuntu: SUCCESS
→ quality windows: SUCCESS
→ dependency audit: SUCCESS
→ PostgreSQL 18 full-suite integration/replay chain: SUCCESS
→ 4408 passed / 2 skipped
→ branch coverage: 93.39%
→ market_episode.py: 100%
→ native_listing.py: 100%
→ physical_boat.py: 100%

Manufacturer artifact reproducibility run 33990690348
→ SUCCESS
→ Ubuntu: SUCCESS
→ Windows: SUCCESS
```

Owner-visible local inspection reported:

```text
MARKET EPISODE LINKAGE RESULT -> PASS
```

## Review-time repository blocker resolutions

Two repository-level CI/governance blockers were exposed during SLICE-0047 review and resolved separately on `main` before final acceptance:

1. Queue-state validation was corrected so canonical readiness must remain startable while a genuine implementation handoff may move the active slice to `REVIEW`/`BLOCKED` only with the required handoff marker.
2. The authoritative global coverage gate was moved to the PostgreSQL-18 job where DB-backed persistence tests actually execute, while retaining the unchanged `fail_under = 90` threshold and preserving Ubuntu/Windows cross-platform quality jobs.

Neither blocker resolution changed SLICE-0047 product/runtime semantics. The final accepted branch incorporated those accepted `main` changes through base-sync merges and was then revalidated on a fresh exact-head PR merge context.

## Scope retained

SLICE-0047 deliberately did not add:

- post-creation NativeListing attach/detach;
- MarketEpisode lifecycle/status/freshness;
- external market-observation linkage behavior;
- PhysicalBoat marketplace facts;
- media upload;
- FastAPI listing surface;
- Astro/React public listing rendering;
- full broker workspace or Auth0 UX;
- search/ranking expansion;
- monitoring/alerts;
- dedup/merge or market-episode continuity heuristics.

These boundaries remain intact after acceptance.

## PROJECT_STATE freshness closure

This acceptance closure advances the highest owner-accepted slice from 0046 to 0047.

In the same closure PR, `docs/PROJECT_STATE.md` is updated to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0047
PROJECT_STATE_QUEUE_SLICE:    0048
```

It moves durable MarketEpisode identity and NativeListing→MarketEpisode referential linkage into the built-capability list, removes the stale statements that those foundations are absent, and records the immediate product horizon:

```text
SLICE-0048
FIRST VISIBLE LISTING VERTICAL SLICE
```

`scripts/validate_repository.py` must fail this closure if the PROJECT_STATE accepted marker and highest acceptance-closure file are not identical.

## Product execution checkpoint

After SLICE-0047, the minimum durable identity/content chain now exists:

```text
PhysicalBoat
→ MarketEpisode
→ NativeListing
→ revisioned LISTING_OFFER facts
```

Estimated remaining distance to first externally visible listing is now:

```text
1 slice — SLICE-0048
```

No additional foundation-only slice should be inserted before SLICE-0048 unless a concrete blocking invariant makes the visible vertical path impossible.

SLICE-0048 should optimize for the narrowest safe end-to-end proof:

```text
minimal/operator-assisted listing intake if necessary
→ FastAPI read boundary
→ simplest public listing rendering
```

Media, complete PhysicalBoat facts, full broker workspace/Auth0 UX, lifecycle polish, search expansion and monitoring may follow after this first visible proof unless required by a concrete blocker.

## Closure decision

```text
SLICE-0047 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
