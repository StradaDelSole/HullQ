# SLICE-0050 — Acceptance closure

**Slice:** SLICE-0050  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #163  
**Initial implementation HEAD:** `5a890cb39e4f194162d2fe48c62fbf8d412e9239`  
**Accepted implementation HEAD:** `d8f41d07e3f84e29ae953b08ac8a5d0459e92c0b`  
**Implementation merge commit:** `7cbd21b9ed002ac0df603dbb15403b1ad706a4a0`  
**Independent AMEND review:** `5170834362`  
**Independent final ACCEPT review:** `5177939569`  
**Owner acceptance:** explicitly recorded 2026-09-11

## Accepted capability

SLICE-0050 adds HullQ's first buyer-critical truth surface for the concrete PhysicalBoat behind a public NativeListing.

Accepted end-to-end capability:

```text
existing NativeListing
→ owning professional principal
→ concrete PhysicalBoat
→ bounded broker-declared PhysicalBoat claim revision
→ explicit current head per (PhysicalBoatId, claiming OrganizationId)
→ existing public FastAPI listing read
→ existing /listings/{NativeListingId}
→ buyer sees what the publishing Organization declares about THIS boat
```

Exactly seven PhysicalBoat fields are in scope:

```text
physical_boat.marketed_brand_claim
physical_boat.model_designation_claim
physical_boat.build_year
physical_boat.loa_length
physical_boat.draft
physical_boat.keel_configuration
physical_boat.rudder_configuration
```

No other PhysicalBoat marketplace-fact field is accepted by this slice.

## Truth semantics retained

The accepted implementation preserves the central HullQ separation:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

BoatDesign values never fill omitted or explicit `UNKNOWN` PhysicalBoat claims.

For the selected optional technical fields:

```text
omitted != UNKNOWN
UNKNOWN carries no invented value
VALUE_ASSERTION carries the broker-declared typed value
```

Numeric canonical values use lossless decimal representation rather than binary floating point.

The public listing selects only the publishing Organization's own current PhysicalBoat claim head for that PhysicalBoat. Different Organizations may hold independent claim histories for the same PhysicalBoat; no cross-Organization winner/resolver is introduced.

`BROKER_CLAIM != VERIFIED_FACT` remains unchanged.

## Authorization boundary

The PhysicalBoat claim write path uses an existing NativeListing as the authorization/context entry point and resolves:

```text
NativeListing
→ MarketEpisode
→ PhysicalBoat
```

The candidate MarketplaceOrganization must equal the NativeListing's immutable `publishing_organization_id`, and the real accepted SLICE-0041 evaluator must allow the supplied Account + Membership + Organization.

Accepted denial coverage includes:

- no membership;
- account mismatch;
- cross-Organization attempt;
- inactive membership;
- missing explicit `PUBLISHER` role;
- `INELIGIBLE` Organization;
- `UNVERIFIED` Organization.

Denied attempts mutate neither claim revisions nor current head.

Claim recording remains separate from listing lifecycle state; an eligible owner can record/correct claims for DRAFT, ACTIVE or later non-public listings.

## Durable revision/current-head semantics

Accepted persistence uses immutable revisions plus one explicit current head per:

```text
(PhysicalBoatId, claiming MarketplaceOrganizationId)
```

Each durable revision records the concrete PhysicalBoat, claiming Organization, recording Account, bounded seven-field snapshot, recorded timestamp and optional explicit predecessor/supersession revision.

Current state is never inferred from timestamp, row order or maximum revision identity.

Correction semantics are compare-and-set style:

```text
expected predecessor == durable current
→ append immutable revision
→ advance current head atomically
```

A stale predecessor conflicts without mutating history/head.

Exact-retry idempotency is defined over the complete immutable revision identity/content, including the recorded predecessor. Reusing a revision identity with a different predecessor or different immutable content conflicts.

The amendment review specifically caught and closed predecessor-blind idempotency.

## PostgreSQL transaction/concurrency guarantees

Revision append and head advance are one PostgreSQL transaction.

Two concurrent corrections from the same predecessor result in exactly one winner/current revision; the losing correction conflicts and no history is lost.

The accepted regression uses a real PostgreSQL trigger to force failure during the head UPSERT after the revision INSERT has executed and proves:

```text
head write failure
→ whole transaction rolls back
→ no orphan revision
→ prior head remains current
→ connection returns usable/IDLE
```

No in-memory lock or production-only test hook is used as the correctness boundary.

## Production public API and Astro surface

SLICE-0050 extends the existing SLICE-0049 exact-listing API/page rather than creating a parallel route.

Public page remains:

```text
/listings/{NativeListingId}
```

When the publishing Organization has current claims, the page visibly separates concrete-yacht truth from the offer narrative:

```text
<brand> <model>
<build year / unknown>
asking price
location

THIS BOAT — broker-declared
LOA
Draft
Keel configuration
Rudder configuration

OFFER
broker narrative...
```

Omitted optional fields render as `not supplied` (or equivalent), explicit `UNKNOWN` renders as `unknown`, and value assertions display the exact typed value.

Broker-controlled strings remain escaped/inert.

An ACTIVE listing with no 0050 claim snapshot remains public under the accepted 0049 completeness predicate; PhysicalBoat claim absence is not a publication failure.

The page remains deliberately `noindex`; SLICE-0050 does not change URL grammar, sitemap state, canonical identity or broader OQ-018 SEO decisions.

## No BoatDesign fallback

This negative contract was explicitly proven end-to-end using a linked BoatDesign whose baseline draft/keel values would expose an accidental projection.

Accepted behavior includes:

```text
BoatDesign draft = 1.80m
PhysicalBoat draft = UNKNOWN
→ public THIS BOAT draft = unknown
→ NOT 1.80m

BoatDesign keel = FIN
PhysicalBoat keel omitted
→ public THIS BOAT keel = not supplied
→ NOT FIN
```

The concrete-yacht claim remains the publishing broker's claim even if it disagrees with BoatDesign reference data. No automatic conflict resolver is introduced.

## Independent review amendment

Initial implementation HEAD:

```text
5a890cb39e4f194162d2fe48c62fbf8d412e9239
```

Independent AMEND review:

```text
5170834362
```

Two material verification/correctness findings were identified:

1. existing-revision idempotency compared the claim fingerprint but not the persisted predecessor, allowing a reused revision ID with a different claimed predecessor to be misclassified as `ALREADY_EXISTS`;
2. the required real PostgreSQL rollback proof for failure after revision insert and during head advance was missing.

The same implementation branch was amended without broadening product scope.

Final accepted implementation HEAD:

```text
d8f41d07e3f84e29ae953b08ac8a5d0459e92c0b
```

The amendment:

- compares stored `previous_claim_revision_id` with the supplied expected predecessor for exact-retry classification;
- proves a forged/different predecessor conflicts while a genuine retry of an older superseded revision remains idempotent;
- injects a real PostgreSQL head-write failure and proves complete transaction rollback/no orphan revision.

Independent final ACCEPT review:

```text
5177939569
```

No material finding remained on the accepted exact HEAD.

## Exact-head verification

Exact accepted implementation HEAD:

```text
d8f41d07e3f84e29ae953b08ac8a5d0459e92c0b
```

Remote verification:

```text
CI run 34531646368
→ SUCCESS
→ quality ubuntu: SUCCESS
→ quality windows: SUCCESS
→ web quality (Astro/Node): SUCCESS
→ dependency audit: SUCCESS
→ PostgreSQL 18 full-suite + branch coverage: SUCCESS
→ repository validation: SUCCESS
→ retained SLICE-0048 preview proof: SUCCESS
→ retained SLICE-0049 production-public proof: SUCCESS

Manufacturer artifact reproducibility run 34531646367
→ SUCCESS
```

Implementation-agent final local validation reported:

```text
focused SLICE-0050 suite: 106 passed
full repository suite: 4653 passed, 2 skipped, 0 failed
ruff: PASS
mypy: PASS
Astro/web validation: PASS
FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH RESULT -> PASS
repository validation: PASS
```

## Scope retained

SLICE-0050 deliberately did not add:

- native inventory search/filter/ranking;
- `CONFIRMED FIT` / `NON-MATCH` evaluation over PhysicalBoat claims;
- global cross-source fact resolution;
- generic all-38-field persistence;
- additional PhysicalBoat fields beyond the accepted seven;
- document verification/upload;
- media/image handling;
- Auth0/session integration;
- browser broker workspace/form;
- persisted generic actor directory;
- freshness/reconfirmation;
- republish/SOLD/ARCHIVED lifecycle;
- save/monitor/alerts;
- contact/leads;
- sitemap/hreflang/indexability expansion;
- pricing/billing.

## PROJECT_STATE freshness closure

This closure advances the highest owner-accepted slice from 0049 to 0050.

In the same closure PR, `docs/PROJECT_STATE.md` must advance atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0050
PROJECT_STATE_QUEUE_SLICE:    0051
```

SLICE-0051 is intentionally not assigned a capability by this closure. Its capability must be selected through the normal post-0050 product/architecture reassessment.

The completed product threshold is now:

```text
PERSISTED REAL LISTING
→ PRODUCTION LIFECYCLE
→ PUBLIC LISTING
→ CONCRETE-YACHT BROKER TRUTH
= BUILT
```

`scripts/validate_repository.py` must fail the closure if the PROJECT_STATE accepted marker and highest acceptance-closure file are not identical.

## Product execution checkpoint

With SLICE-0050 accepted, HullQ now distinguishes a design/configuration reference from claims about the specific offered yacht in the public buyer experience.

The next reassessment should select the smallest highest-leverage continuation of the buyer/broker loop, without pre-selecting SLICE-0051. Candidate families may include native technical search over the now-available concrete-yacht facts, broker operating/auth surfaces, media, or buyer persistence/contact capabilities.

The decision must be made from product leverage after 0050 rather than architecture completeness.

## Closure decision

```text
SLICE-0050 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
