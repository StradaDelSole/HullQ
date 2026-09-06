# SLICE-0049 — Acceptance closure

**Slice:** SLICE-0049  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #159  
**Initial implementation HEAD:** `b48969528b60abcb29ce583b70eb31f49a071568`  
**Accepted implementation HEAD:** `c7a2f1731c90e4eac915c5497236bafc3b0bde48`  
**Implementation merge commit:** `86465399bd59639b38290745fbc5978de42ac41a`  
**Independent AMEND review:** `5125967563`  
**Independent final ACCEPT review:** `5126057991`  
**Owner acceptance:** explicitly recorded 2026-09-06

## Accepted capability

SLICE-0049 completes HullQ's first production-public NativeListing vertical.

Accepted end-to-end capability:

```text
existing complete durable NativeListing
→ explicit SLICE-0041-authorized owning publisher/operator
→ DRAFT → ACTIVE
→ public FastAPI exact-listing read
→ Astro SSR
→ /listings/{NativeListingId}
→ normal visitor can read without preview token or login
```

Controlled removal is also accepted:

```text
ACTIVE
→ explicit SLICE-0041-authorized owning publisher/operator
→ WITHDRAWN
→ public API and web route become ordinary not-found
```

The accepted lifecycle is intentionally only:

```text
DRAFT → ACTIVE → WITHDRAWN
```

`WITHDRAWN → ACTIVE` is not authorized in SLICE-0049. `SOLD`, `ARCHIVED`, freshness and stale-state semantics remain out of scope.

Hard boundaries retained:

```text
DURABLE CREATION != PUBLICATION
PREVIEWABLE != PUBLISHED
PUBLIC != INDEXABLE
FRESHNESS != LIFECYCLE
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

## Durable lifecycle and migration

SLICE-0049 adds lifecycle state outside the accepted SLICE-0043 immutable NativeListing creation envelope.

The original creation envelope and collision/idempotency semantics remain unchanged:

```text
NativeListingId
publishing_organization_id
created_by_account_id
optional MarketEpisodeId
optional broker_listing_reference
content_hash
created_at
```

Lifecycle changes do not alter those immutable fields or `content_hash`.

All pre-existing NativeListings migrate to `DRAFT`; no migration or creation path auto-publishes a listing. Newly created NativeListings also begin `DRAFT`.

Exact retries of the original immutable creation request remain accepted/idempotent after the listing becomes `ACTIVE` and after it becomes `WITHDRAWN`.

The PostgreSQL lifecycle constraint permits only:

```text
DRAFT
ACTIVE
WITHDRAWN
```

and rejects invalid values at the database boundary.

## Publication authorization

Every publish and withdraw transition reuses the real accepted SLICE-0041 evaluator.

A transition requires an explicit runtime principal composed from:

```text
AccountId
+ OrganizationMembership
+ candidate MarketplaceOrganization
```

and additionally requires the candidate Organization to match the NativeListing's durable `publishing_organization_id`.

Accepted denial coverage includes:

- no membership;
- account mismatch;
- Organization mismatch / cross-Organization attempt;
- inactive membership;
- missing explicit `PUBLISHER` role;
- `INELIGIBLE` Organization;
- `UNVERIFIED` Organization.

Denied transitions leave lifecycle state and publication history unchanged.

SLICE-0049 does not add Auth0, sessions, a persisted generic actor directory or broker workspace. The trusted operator supplies the explicit runtime principal.

## Publication completeness predicate

A listing can become public only when the durable chain is complete:

```text
NativeListing exists
AND durable publishing Organization identity exists on the listing
AND NativeListing.market_episode_id is non-null
AND referenced MarketEpisode exists
AND referenced PhysicalBoat exists
AND explicit current LISTING_OFFER head exists
AND that head resolves to the typed current LISTING_OFFER revision for the listing
```

The current offer is resolved through the accepted explicit current-head relationship; timestamp or row-order inference is forbidden.

No BoatDesign/model facts are promoted into PhysicalBoat or listing truth to satisfy completeness.

An `ACTIVE` listing still fails closed on public read if the required durable chain cannot be resolved.

## Atomic immutable publication history

Every successful lifecycle transition atomically appends one immutable publication-transition record containing at least:

```text
publication_transition_id
NativeListingId
from_state
to_state
actor AccountId
publishing MarketplaceOrganizationId
occurred_at
```

State change and audit append occur in the same PostgreSQL transaction.

The accepted failure-injection regression proves that a real PostgreSQL failure during the audit insert rolls back the preceding lifecycle update as well:

```text
failed audit insert
→ lifecycle remains prior state
→ no unmatched audit row
```

Concurrency is serialized at the database boundary. Two competing `DRAFT → ACTIVE` attempts produce exactly one successful transition, one immutable audit record and final `ACTIVE`; the stale competing attempt changes nothing.

Publication history is append-only and is distinct from both current lifecycle state and SLICE-0043 creation truth.

## Production public API and web surface

SLICE-0049 adds the first production-public NativeListing read path:

```text
GET /api/listings/{NativeListingId}
GET /listings/{NativeListingId}
```

The API route is separate from the accepted SLICE-0048 preview-token route.

Only complete `ACTIVE` listings resolve publicly.

These cases intentionally collapse to the same ordinary external not-found behavior:

```text
DRAFT
WITHDRAWN
missing
incomplete
```

This prevents the public surface from becoming a NativeListingId existence/status oracle.

Astro obtains listing data only through FastAPI and does not connect directly to PostgreSQL or reimplement Python domain rules.

The public projection preserves the accepted SLICE-0048 truth semantics, including lossless money representation, conservative known-history wording, broker attribution for VAT/tax claims and no model-to-physical truth promotion.

Untrusted broker-controlled text renders escaped/inert.

## Canonical public URL / bounded SEO contract

The first production-public NativeListing page identity is:

```text
/listings/{NativeListingId}
```

Accepted rules:

- `NativeListingId` is the stable page identity;
- no slug is introduced;
- query parameters do not select another listing or change lifecycle/content identity;
- the clean ID path remains canonical when query parameters are present;
- no alternate/legacy NativeListing route grammar is invented;
- the `ACTIVE` page is publicly retrievable but deliberately `noindex`;
- no NativeListing XML sitemap, hreflang tree, faceted listing URLs, broad structured-data expansion or technical landing-page system is introduced.

This is the bounded implementation of `specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`. Broader OQ-018 resolution remains required before wider organic public routing/indexation work.

## SLICE-0048 preview boundary retained

Production publication does not weaken the existing preview capability.

Preview URLs remain:

```text
capability-gated
finite
non-canonical
non-indexed
private/no-store
no-referrer
```

The public route does not copy preview confidentiality headers because an `ACTIVE` listing is ordinary public content.

The accepted SLICE-0049 real-HTTP proof reruns the SLICE-0048 preview regression and verifies tampered preview tokens remain rejected and token/secret values do not leak into ordinary captured logs.

## Independent review amendment

Initial implementation HEAD:

```text
b48969528b60abcb29ce583b70eb31f49a071568
```

Independent AMEND review:

```text
5125967563
```

The review identified three verification gaps against the already accepted readiness contract, not an architecture/product redesign:

1. the owner-visible proof called a listing "pre-existing/migrated" even though it had been created after upgrading to the SLICE-0049 head;
2. the explicit authorization denial matrix was broad for publish but incomplete for withdraw;
3. no deterministic failure-injection regression directly proved rollback when the audit write fails after lifecycle update, and the database lifecycle CHECK lacked a direct invalid-value regression.

The same implementation branch was amended without changing production behavior merely to satisfy tests.

Final accepted implementation HEAD:

```text
c7a2f1731c90e4eac915c5497236bafc3b0bde48
```

The amendment:

- seeds a genuine NativeListing while schema is pinned to pre-0049 Alembic revision `4c9a0dcc98bb`, upgrades to head and proves `DRAFT` backfill plus public not-found equivalence;
- completes publish/withdraw authorization denial coverage;
- injects a real PostgreSQL audit-table CHECK failure and proves transaction rollback;
- directly proves the lifecycle-state CHECK rejects an invalid database value.

Independent final ACCEPT review:

```text
5126057991
```

No blocker/high/medium finding remained on the accepted exact HEAD.

## Exact-head remote verification

Exact accepted HEAD:

```text
c7a2f1731c90e4eac915c5497236bafc3b0bde48
```

Remote verification:

```text
CI run 34048203748
→ SUCCESS
→ quality ubuntu: SUCCESS
→ quality windows: SUCCESS
→ web quality (Astro/Node): SUCCESS
→ dependency audit: SUCCESS
→ PostgreSQL 18 full-suite + branch coverage: SUCCESS
→ repository validation: SUCCESS
→ SLICE-0048 real HTTP preview regression: SUCCESS
→ SLICE-0049 first-production-public-listing real HTTP proof: SUCCESS
→ complete retained PostgreSQL/reproducibility replay chain: SUCCESS

Manufacturer artifact reproducibility run 34048203749
→ SUCCESS
```

Claude's final local validation reported:

```text
4560 passed
2 skipped (pre-existing live-network tests)
coverage 93.46%
31 focused lifecycle-persistence tests PASS
Astro check/build PASS
8/8 web tests PASS
FIRST PRODUCTION PUBLIC LISTING RESULT -> PASS
FIRST VISIBLE LISTING PREVIEW RESULT -> PASS
```

## Scope retained

SLICE-0049 deliberately did not add:

- Auth0/session implementation;
- broker dashboard/workspace;
- persisted generic actor directory;
- republish;
- `SOLD` or `ARCHIVED` lifecycle states;
- freshness/staleness automation;
- PhysicalBoat marketplace facts beyond identity;
- media upload/storage/presentation;
- public inventory search/ranking;
- saved search / monitoring / alerts;
- lead/contact workflow;
- price-history intelligence;
- sitemap/hreflang/faceted SEO expansion;
- external feeds or dedup expansion.

These remain post-0049 product-prioritization decisions.

## PROJECT_STATE freshness closure

This acceptance closure advances the highest owner-accepted slice from 0048 to 0049.

In the same closure PR, `docs/PROJECT_STATE.md` is updated to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0049
PROJECT_STATE_QUEUE_SLICE:    0050
```

SLICE-0050 is intentionally not assigned a capability in this closure. Its content must be selected by the required post-0049 architecture/product reassessment.

The completed product threshold is now:

```text
PERSISTED REAL LISTING
→ PRODUCTION LIFECYCLE
→ PUBLIC FASTAPI READ
→ STABLE PUBLIC ASTRO URL
= BUILT
```

`scripts/validate_repository.py` must fail this closure if the PROJECT_STATE accepted marker and highest acceptance-closure file are not identical.

## Product execution checkpoint

With SLICE-0049 accepted, HullQ now has the minimum technical spine of a native production-public marketplace object rather than only a preview surface.

The next reassessment should select the smallest highest-leverage continuation of the buyer/broker loop. Candidate families include, without pre-selecting SLICE-0050:

```text
broker operating surface / authenticated intake
vs
richer PhysicalBoat/listing facts and presentation
vs
minimal native-inventory search/discovery
vs
media where it is materially blocking
vs
buyer save/monitor/contact capability
```

The decision must be made from product leverage after 0049, not from architecture completeness.

## Closure decision

```text
SLICE-0049 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
