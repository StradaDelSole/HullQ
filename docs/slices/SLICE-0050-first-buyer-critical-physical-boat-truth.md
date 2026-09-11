# SLICE-0050 — First buyer-critical PhysicalBoat truth vertical

**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Status set by this handoff:** `REVIEW`  
**Base main:** `42ec5597af5b2570b462019680b2ff220440def1`  
**Product horizon:** make the first production-public NativeListing materially useful for technical buyer decisions by showing what the publishing broker actually declares about the concrete PhysicalBoat, without yet building native-inventory search, Auth0/broker UI, media or broad fact coverage.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
**VISIBLE-RESULT CHECK:** PASS  
**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  

## 1. One capability

Given an existing NativeListing → MarketEpisode → PhysicalBoat chain and an explicit eligible principal for that NativeListing's owning professional Organization, persist one bounded revisioned set of buyer-critical broker claims about the **concrete PhysicalBoat** and expose the publishing Organization's current claims on the existing production-public NativeListing API/page as a clearly separate `THIS BOAT` truth surface.

```text
existing NativeListing
→ owning professional principal
→ concrete PhysicalBoat
→ bounded broker-declared PhysicalBoat claims
→ immutable revision + explicit per-Organization current head
→ existing public FastAPI listing read
→ existing /listings/{NativeListingId}
→ buyer can see what is actually declared about THIS boat
```

The capability deliberately stops before structured native-inventory search. It creates the first durable/useful PhysicalBoat truth needed for that later search.

## 2. Why this slice exists

SLICE-0049 completed:

```text
persisted real listing
→ explicit publication lifecycle
→ ACTIVE
→ production public API
→ stable public Astro page
```

But the accepted page still primarily contains `LISTING_OFFER` data — asking price, location and broker narrative. It does not yet carry durable marketplace facts about the individual yacht beyond PhysicalBoat identity.

The post-0049 reassessment compared:

1. authenticated broker operating surface;
2. richer PhysicalBoat/listing truth;
3. minimal native-inventory search/discovery;
4. media;
5. buyer save/monitor/contact.

The selected next capability is PhysicalBoat truth because:

- operator-assisted intake already exists, so browser broker UX is not yet the blocking path;
- media improves presentation but does not prove HullQ's technical differentiation and immediately adds rights/storage/quarantine scope;
- save/monitor/contact is premature while native inventory cannot yet express the concrete technical facts that make HullQ different;
- public native search over only current offer fields would mostly reproduce ordinary price/location/identity filtering;
- the strongest HullQ-specific value hypothesis is the distinction between `this design can fit` and `this offered boat is actually declared/known to have these characteristics`.

SLICE-0050 therefore makes that distinction browser-visible on real public inventory before search is layered on top.

## 3. Controlling artifacts

Implementation MUST preserve the accepted boundaries in:

- `docs/MARKET_AND_BUSINESS_MODEL_VALIDATION_RECLASSIFICATION_2026-09-06.md`;
- `docs/PRODUCT_EXECUTION_PLAN.md` where not superseded by later owner direction;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/PRODUCT_UX_PRINCIPLES.md` because this slice materially changes a public market/listing UI;
- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`;
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`;
- `specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md` and accepted SLICE-0041 implementation;
- accepted SLICE-0043 NativeListing immutable creation semantics;
- accepted SLICE-0045 LISTING_OFFER revision/current-head semantics;
- accepted SLICE-0046 PhysicalBoat identity and BoatDesignRef separation;
- accepted SLICE-0047 NativeListing → MarketEpisode → PhysicalBoat linkage;
- accepted SLICE-0048 preview security/read-model boundaries;
- accepted SLICE-0049 publication/public-read/SEO boundaries.

Hard truth remains:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
BROKER_CLAIM != VERIFIED_FACT
UNKNOWN != omitted
```

## 4. Exact bounded field set

SLICE-0050 implements **exactly seven** already-accepted `PHYSICAL_BOAT` registry fields.

### Identity/basic claims

```text
physical_boat.marketed_brand_claim
physical_boat.model_designation_claim
physical_boat.build_year
```

### Buyer-critical technical claims

```text
physical_boat.loa_length
physical_boat.draft
physical_boat.keel_configuration
physical_boat.rudder_configuration
```

No other PhysicalBoat registry field is implemented in 0050.

The selection is intentional:

- brand/model/year makes a public listing recognizable as a yacht rather than a price-first generic object;
- actual LOA supports exact dimensional constraints relevant to berth/marina/tax/use cases;
- actual draft is a major hard operating constraint;
- keel and rudder configuration are high-value sailboat-specific configuration constraints and directly express HullQ's Design-vs-concrete-boat distinction.

The existing registry remains authoritative for assertion kinds, value types, units, categorical vocabularies, presentation, search-use classification, requiredness and risk class.

## 5. Bounded runtime value model

Implement a small typed runtime representation for exactly the seven fields. Do NOT build a generic 38-field marketplace-fact framework in this slice.

Required response semantics:

```text
marketed_brand_claim      = VALUE_ASSERTION(non-blank string)
model_designation_claim   = VALUE_ASSERTION(non-blank string)
build_year                = VALUE_ASSERTION(integer) | UNKNOWN
```

Optional selected technical fields:

```text
loa_length                = omitted | VALUE_ASSERTION(decimal SI meters) | UNKNOWN
draft                     = omitted | VALUE_ASSERTION(decimal SI meters) | UNKNOWN
keel_configuration        = omitted | VALUE_ASSERTION(accepted registry enum) | UNKNOWN
rudder_configuration      = omitted | VALUE_ASSERTION(accepted registry enum) | UNKNOWN
```

Hard:

```text
omitted != UNKNOWN
UNKNOWN carries no invented value
numeric canonical values are not binary floating point
unit-bearing free-text strings are not canonical searchable values
```

Use `Decimal`/lossless equivalent for numeric runtime/public transport. Do not invent an unaccepted measurement range merely for convenience; structural/domain validation must follow existing accepted measurement/registry semantics.

## 6. Claim authority and authorization boundary

The claims are about `PhysicalBoat`, but 0050 uses an existing NativeListing as the authorization/context entry point.

The write use case receives at least:

```text
NativeListingId
explicit AccountId
explicit OrganizationMembership
explicit candidate MarketplaceOrganization
PhysicalBoat-claim revision identity/input
bounded seven-field claim snapshot
```

It MUST resolve:

```text
NativeListing
→ MarketEpisode
→ PhysicalBoat
```

and fail closed if that durable chain is missing/incomplete.

The candidate MarketplaceOrganization MUST equal the NativeListing's immutable `publishing_organization_id`, and the real accepted SLICE-0041 evaluator MUST return `ALLOWED` for the supplied Account + Membership + Organization.

Forbidden:

- `authorized=true` bypass;
- Organization-ID-only bypass;
- direct SQL claim insertion bypassing the application authorization boundary;
- one Organization writing or superseding another Organization's PhysicalBoat claims merely because both listings reference the same PhysicalBoat.

The claim authority recorded durably is the publishing professional Organization that made the statement. The recording Account is retained for audit but is not promoted into public yacht truth.

Claim recording is not conditioned on the NativeListing being `ACTIVE`; an authorized owning publisher may supply/correct claims while its listing is DRAFT, ACTIVE or later non-public. Listing lifecycle and PhysicalBoat claim history remain separate truths.

## 7. Durable non-destructive revision semantics

Persist immutable claim revisions and an explicit current head **per `(PhysicalBoatId, claiming MarketplaceOrganizationId)`**.

Minimum durable revision identity/envelope:

```text
PhysicalBoatClaimRevisionId
PhysicalBoatId
claiming MarketplaceOrganizationId
recorded_by AccountId
recorded_at
optional supersedes PhysicalBoatClaimRevisionId
bounded seven-field typed snapshot
```

The current head MUST NOT be inferred by timestamp, insertion order or maximum revision identity.

Hard:

```text
old revision retained
current head explicit
same-authority correction explicit
no silent latest-wins
cross-Organization supersession forbidden
```

### 7.1 First revision

For a `(PhysicalBoatId, OrganizationId)` with no current head:

```text
new valid revision
→ durable immutable revision
→ explicit current head = new revision
```

### 7.2 Correction

A correction MUST explicitly name/expect the current revision it supersedes (or an accepted equivalent compare-and-set predecessor token).

```text
expected current == durable current
+ same PhysicalBoat
+ same claiming Organization
→ append new immutable revision
→ advance head atomically
```

A stale predecessor MUST fail closed and change neither history nor head.

### 7.3 Idempotency / collision

For an exact retry of one already-durable revision identity and identical immutable revision content:

```text
same revision id + same immutable content
→ idempotent already-exists equivalent
→ no duplicate revision
→ no duplicate head movement
```

The same revision identity with materially different immutable content MUST be a conflict.

## 8. Transaction and concurrency semantics

Persistence uses PostgreSQL 18 and MUST preserve the repository's accepted transaction ownership discipline.

Appending a revision and advancing its current head are one atomic transaction.

For two concurrent valid corrections that both name the same current predecessor:

```text
exactly one advances the head
exactly one becomes current
losing stale correction fails/returns conflict
no duplicate current heads
no lost history
```

Do not use in-memory locks as the correctness boundary.

A failure after inserting the immutable revision but before/while advancing the head MUST roll the transaction back so no orphan revision appears as a successful correction.

## 9. Cross-source resolution is deliberately NOT implemented

`specs/MARKETPLACE_FACT_CONTRACT.v0.1.md` preserves future multi-source disagreement/resolution semantics.

SLICE-0050 does not implement a global resolver across different Organizations/sources and does not manufacture `VERIFIED_FACT` or a universal PhysicalBoat canonical value.

Instead the public NativeListing displays the **current claims from that listing's own publishing Organization**:

```text
ACTIVE NativeListing
→ PhysicalBoat
→ publishing_organization_id
→ current PhysicalBoat claim head for (PhysicalBoat, that Organization)
```

If another Organization later has its own listing for the same PhysicalBoat, its own current claim head remains independent.

No rule equivalent to:

```text
newer Organization wins
majority wins
BoatDesign baseline wins
```

is permitted.

A future slice may add cross-source resolution when there is a real consumer for it.

## 10. Production public read model extension

Extend the accepted SLICE-0049 public exact-listing read model; do not create a parallel listing API.

For an ordinary complete `ACTIVE` listing, resolve the publishing Organization's current bounded PhysicalBoat claim snapshot if one exists.

The public projection may expose a nested bounded structure such as `physical_boat_claims`, but MUST preserve:

- exact seven-field scope;
- broker-claim attribution;
- lossless numeric representation;
- explicit `UNKNOWN`;
- optional omission distinct from explicit `UNKNOWN`;
- no internal Account ID, content hash, transaction metadata or revision-history leakage;
- no BoatDesign fallback.

An ACTIVE listing with **no** 0050 claim snapshot remains publicly readable under the accepted 0049 completeness predicate. SLICE-0050 MUST NOT retroactively make existing 0049 listings unpublished merely because new optional buyer-detail data is absent.

Hard:

```text
0049 publication completeness remains unchanged
PhysicalBoat claims enrich public content
PhysicalBoat claim absence != listing lifecycle failure
```

## 11. Public Astro presentation

Update the existing production page:

```text
/listings/{NativeListingId}
```

No new public listing route is introduced.

When the owning publisher's current claim snapshot exists, the page MUST visibly separate the concrete-yacht information from offer narrative.

A suitable semantic structure is:

```text
<broker-declared brand> <broker-declared model>
<build year or explicit unknown>
asking price
location

THIS BOAT — broker-declared
LOA
Draft
Keel configuration
Rudder configuration

OFFER
broker summary/description/etc.
```

Exact visual styling is implementation-level, but the user must be able to understand without training that the technical values are claims about **this physical boat**, not generic BoatDesign reference specs.

For the selected optional technical fields:

```text
omitted        -> visibly "not supplied" / accepted equivalent
UNKNOWN        -> visibly "unknown" / accepted equivalent
VALUE_ASSERTION -> display exact typed value
```

Do not collapse omission and UNKNOWN into the same transport value if doing so loses the accepted distinction.

All broker-controlled strings remain escaped/inert.

The public page remains `noindex` under the accepted SLICE-0049 SEO contract. This slice does not change canonical URL grammar, sitemap state or indexability.

## 12. No BoatDesign-to-PhysicalBoat projection

This is the most important negative contract in 0050.

If the linked PhysicalBoat has a `BoatDesignRef`, values from that BoatDesign/configuration MUST NOT fill missing/UNKNOWN selected PhysicalBoat claims.

Examples:

```text
BoatDesign draft = 1.80 m
PhysicalBoat draft omitted
→ public THIS BOAT draft = not supplied
→ NOT 1.80 m

BoatDesign keel = FIN
PhysicalBoat keel = UNKNOWN
→ public THIS BOAT keel = UNKNOWN
→ NOT FIN
```

If a broker-declared PhysicalBoat value differs from the BoatDesign baseline, the public PhysicalBoat claim remains the broker's concrete-yacht claim. This slice does not automatically declare the design or broker wrong and does not implement cross-evidence conflict resolution.

## 13. Operator-assisted write surface

Provide the smallest operator-assisted command/fixture needed to exercise the capability on real PostgreSQL.

A CLI/script may accept a validated JSON fixture containing:

- NativeListingId;
- explicit runtime principal inputs required by SLICE-0041;
- new revision identity;
- expected current/superseded revision identity where correcting;
- exact bounded seven-field snapshot.

No Auth0 session, browser broker form or generic admin console is required.

Fixture examples MUST contain no real personal secrets/credentials.

## 14. Database migration

Use Alembic as the sole forward migration path.

Migration MUST create the minimum durable structures/constraints needed for:

- immutable claim revision identity;
- PhysicalBoat FK;
- claiming Organization identity value;
- recording Account identity value;
- optional explicit predecessor/supersession relationship;
- exactly one current head per `(PhysicalBoatId, OrganizationId)`;
- accepted categorical/assertion-kind constraints where stored relationally;
- safe numeric representation;
- atomic correction semantics.

Do not add a persisted generic Account/Organization directory merely to satisfy these audit identities; accepted SLICE-0041 runtime identity types remain the authorization boundary until a later actor-directory/auth slice.

## 15. Owner-visible implementation proof

Add one retained executable proof against real PostgreSQL 18 and real FastAPI/Astro HTTP boundaries.

The proof MUST demonstrate at least:

1. migrate from the accepted pre-0050 head through the new Alembic revision;
2. create a real PhysicalBoat → MarketEpisode → NativeListing → current LISTING_OFFER chain using accepted persistence paths;
3. where practical, link the PhysicalBoat to a BoatDesign/reference whose baseline values make projection bugs observable;
4. publish the listing through the accepted 0049 authorized lifecycle path;
5. before any 0050 PhysicalBoat claim revision exists, prove the ACTIVE listing remains public and no BoatDesign value is invented into the `THIS BOAT` projection;
6. record the first seven-field snapshot through the real SLICE-0041 authorization gate;
7. public FastAPI read returns the broker-declared brand/model/build-year semantics and the selected technical facts;
8. public Astro page visibly shows the `THIS BOAT` section without preview token/login;
9. prove one optional field omitted and another explicitly `UNKNOWN` remain distinguishable through persistence → API → browser;
10. prove a BoatDesign/reference value does not fill either omitted or UNKNOWN PhysicalBoat data;
11. wrong/cross-Organization write attempt is denied and leaves revision history/head unchanged;
12. append one same-authority correction with explicit predecessor, retain the old revision and show the new current value publicly;
13. stale correction attempt is rejected with head/history unchanged;
14. exact retry of an already-durable identical revision is idempotent/no duplicate;
15. concurrency test/proof for two corrections from the same predecessor results in exactly one head advance;
16. withdraw the NativeListing and prove the accepted 0049 ordinary public 404 behavior remains intact;
17. rerun the accepted SLICE-0048 preview regression and SLICE-0049 production-public regression sufficiently to prove no security/lifecycle boundary weakened.

The proof MUST end exactly:

```text
FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH RESULT -> PASS
```

## 16. Required tests

At minimum add/retain automated coverage for:

### Domain/value semantics

- exactly seven fields represented;
- brand/model required and non-blank;
- build year required response with `VALUE_ASSERTION | UNKNOWN`;
- selected technical fields preserve `omitted | VALUE_ASSERTION | UNKNOWN`;
- categorical vocabularies reject unsupported values;
- numeric values are lossless/non-float at the domain/public boundary.

### Persistence

- first revision/current head;
- exact retry idempotency;
- same revision identity with different content conflict;
- explicit correction retains old revision;
- stale predecessor rejection;
- cross-Organization supersession impossible;
- transaction rollback on revision/head failure;
- concurrent same-predecessor correction exactly-one-winner behavior;
- FK/constraint negative paths;
- typed readback.

### Authorization

Exercise the real SLICE-0041 evaluator, including at least:

- eligible owning principal succeeds;
- no membership denied;
- account mismatch denied;
- Organization mismatch/cross-Organization denied;
- inactive membership denied;
- missing explicit `PUBLISHER` denied;
- INELIGIBLE Organization denied;
- UNVERIFIED Organization denied;
- denied attempts mutate neither revisions nor current head.

### Public read / web

- ACTIVE listing with claims returns only owning publisher's current snapshot;
- ACTIVE listing without claims remains public;
- omission != explicit UNKNOWN through transport/rendering;
- no BoatDesign fallback;
- current correction visible, old correction not selected as current;
- DRAFT/WITHDRAWN/missing/incomplete listing behavior remains accepted 0049 ordinary not-found;
- broker strings escaped/inert;
- `noindex` + self-canonical 0049 behavior retained;
- preview capability remains separate and secure.

## 17. Explicitly out of scope

SLICE-0050 MUST NOT implement:

- public native-inventory search/filter/ranking;
- `CONFIRMED FIT` / `NON-MATCH` evaluation over the new PhysicalBoat claims;
- generic cross-source resolution/conflict engine;
- generic all-38-field marketplace-fact persistence framework;
- builder, boat name, HIN/CIN;
- beam, displacement, hull material, rig configuration;
- engine/fuel fields;
- cabins/berths/heads;
- refit/history/survey/damage/osmosis fields;
- verification/document upload;
- media/image upload/storage;
- Auth0/session integration;
- browser broker workspace/form;
- persisted generic actor directory;
- freshness/reconfirmation;
- republish/SOLD/ARCHIVED lifecycle;
- save/monitor/alerts;
- contact/lead workflow;
- listing sitemap/hreflang/indexability expansion;
- pricing/billing.

Future slices may add these only when selected through the normal product-priority process.

## 18. Product execution alignment

### ONE-CAPABILITY CHECK

PASS.

The single visible capability is:

> a buyer can inspect one public HullQ listing and see a bounded set of durable broker claims about the concrete PhysicalBoat, separately from design truth and offer narrative.

### VISIBLE-RESULT CHECK

PASS.

The Project Owner can run the retained proof and open the resulting real public listing page to inspect the concrete-yacht truth surface.

### PRODUCT EXECUTION PLAN ALIGNMENT

PASS.

This slice directly strengthens the HullQ-specific product advantage that remains to be validated: strict technical truth about an individual offered yacht. It does not spend a slice reproving category demand and does not pull broker infrastructure/media/search forward before the facts those capabilities need exist.

## 19. Handoff / completion state

Implementation agent requirements:

- work only in the SLICE-0050 worktree/branch created by `START_SLICE.bat`;
- do not change this readiness contract merely to fit implementation convenience;
- material ambiguity/blocker must be reported rather than silently reinterpreted;
- run all required repository, PostgreSQL, API/HTTP and web validation;
- update this slice document to `REVIEW` only when implementation and proof are complete;
- include an implementation handoff marker required by repository validation;
- push the implementation branch and stop;
- do not merge;
- do not mark DONE;
- do not start SLICE-0051.

A successful implementation handoff remains `REVIEW` until independent exact-head review and explicit Project Owner acceptance.
