# SLICE-0049 — First production-public NativeListing vertical

**Type:** IMPLEMENTATION  
**Status:** READY  
**Product horizon:** convert the accepted browser-visible preview proof into the first real public NativeListing publication capability without pulling Auth0, broker workspace, search/discovery, freshness, media or full SEO distribution forward.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
**VISIBLE-RESULT CHECK:** PASS  
**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  

## 1. One capability

Given one already-persisted NativeListing chain with an explicit current LISTING_OFFER head and one trusted-operator-supplied professional publishing principal that passes the accepted SLICE-0041 eligibility evaluator for the listing's owning MarketplaceOrganization, allow the listing to move through the minimum production publication lifecycle and expose the ACTIVE listing at one stable public FastAPI + Astro URL without any preview token:

```text
existing durable NativeListing + current LISTING_OFFER
→ explicit authorized publish transition
→ DRAFT → ACTIVE
→ production public FastAPI read model
→ Astro SSR public listing page
→ /listings/{NativeListingId}
→ normal browser visitor can read the listing without a bearer capability
```

The same bounded capability also allows an authorized owning publisher to remove that listing from public visibility:

```text
ACTIVE
→ explicit authorized withdraw transition
→ WITHDRAWN
→ public route no longer reveals listing content
```

This slice does not create a broker workspace, end-user authentication system, marketplace search surface or final SEO-distribution system.

## 2. Lifecycle contract

The only lifecycle states introduced by 0049 are:

```text
DRAFT
ACTIVE
WITHDRAWN
```

The only authorized transitions are:

```text
DRAFT → ACTIVE
ACTIVE → WITHDRAWN
```

Hard rules:

```text
NativeListing durable creation != publication
DRAFT != public
ACTIVE = public
WITHDRAWN != public
WITHDRAWN != SOLD
STALE != WITHDRAWN
STALE != SOLD
freshness != lifecycle
```

`WITHDRAWN → ACTIVE` is NOT authorized in SLICE-0049. Republish is a later capability requiring an explicit future contract.

`SOLD`, `ARCHIVED`, stale/disappeared semantics and any other lifecycle/freshness state are out of scope and MUST NOT be inferred or introduced.

### 2.1 Migration safety

Every NativeListing that exists before the 0049 lifecycle migration MUST enter the new lifecycle as `DRAFT`.

Hard:

```text
pre-existing listing → DRAFT
pre-existing listing → never automatically ACTIVE
```

The migration MUST NOT make any previously durable or previewable listing publicly readable merely because 0049 is deployed.

## 3. Immutable publication-transition history

Every successful lifecycle transition MUST create one append-only immutable publication-transition record.

The retained transition record MUST identify at least:

```text
publication_transition_id
NativeListingId
from_state
to_state
actor AccountId
publishing MarketplaceOrganizationId
occurred_at
```

For `DRAFT → ACTIVE`, the transition may occur only after the real accepted SLICE-0041 eligibility evaluator returns `ALLOWED` for the explicit Account + OrganizationMembership + candidate MarketplaceOrganization supplied to the publication use case.

For `ACTIVE → WITHDRAWN`, the same fail-closed publisher/Organization ownership authorization boundary applies; one Organization cannot withdraw another Organization's listing.

Hard:

```text
publication history is append-only
publication history is not rewritten
publication history is not deleted to clean up state
current lifecycle state != historical truth
```

The implementation MAY retain/project the current lifecycle state directly on NativeListing or in another bounded current-state projection for efficient reads, but the current-state change and corresponding immutable transition record MUST commit atomically. A successful lifecycle transition with no durable audit record, or an audit record with no matching state transition, is forbidden.

Do not serialize or persist arbitrary internal SLICE-0041 runtime object graphs merely for audit. Retain the minimum durable actor/Organization/transition identity required by this contract.

## 4. Authorization boundary

0049 continues to use a trusted operator/CLI-assisted principal input. This is deliberately not an authenticated browser session.

For every lifecycle transition the application layer MUST exercise the accepted SLICE-0041 eligibility evaluator; an `authorized=true` flag, hard-coded bypass, Organization-ID-only bypass or direct SQL state flip is forbidden.

Publish succeeds only when all applicable conditions hold, including:

```text
explicit AccountId
+ explicit OrganizationMembership
+ explicit candidate MarketplaceOrganization
+ candidate Organization matches NativeListing owner
+ SLICE-0041 evaluator returns ALLOWED
+ current lifecycle state is DRAFT
+ public-read completeness predicate is satisfied
```

Withdraw succeeds only when all applicable conditions hold, including:

```text
explicit AccountId
+ explicit OrganizationMembership
+ explicit candidate MarketplaceOrganization
+ candidate Organization matches NativeListing owner
+ SLICE-0041 evaluator returns ALLOWED
+ current lifecycle state is ACTIVE
```

Denied, mismatched, unsupported or stale transition requests MUST leave both current state and immutable transition history unchanged.

0049 does not persist a general Account/Organization/Membership directory, implement Auth0, establish external broker verification/KYB/KYC, or claim that operator input is a future production session mechanism.

## 5. Publication completeness predicate

A listing MUST NOT become ACTIVE unless its existing durable chain is complete enough to support the accepted public read model.

At minimum fail closed unless:

```text
NativeListing exists
AND NativeListing has its accepted owning MarketplaceOrganization identity
AND NativeListing.market_episode_id is non-null
AND referenced MarketEpisode exists
AND referenced PhysicalBoat exists
AND explicit current LISTING_OFFER head exists
AND that head resolves to a typed current LISTING_OFFER revision for this NativeListing
```

Use accepted explicit current-head semantics. Do not infer the current offer by timestamp/history ordering.

No BoatDesign/model/configuration value may be promoted into a PhysicalBoat/listing fact merely to satisfy publication completeness.

## 6. Public FastAPI read boundary

Add one production-public read route for an exact NativeListing identity. The API MAY use the repository's still-bounded non-final versioning shape, but it MUST NOT reuse the preview bearer-token route as the public contract.

The public read predicate is:

```text
complete durable listing chain
+ lifecycle == ACTIVE
→ public read may return listing
```

For DRAFT, WITHDRAWN, missing, incomplete or otherwise non-public listings, return the same ordinary external not-found class so the route does not expose hidden listing existence/state.

The public read model MUST derive from the same accepted truth-bearing current LISTING_OFFER semantics already used by 0048, preserving:

- lossless asking-price representation;
- omission vs explicit UNKNOWN / NOT_APPLICABLE / NO_KNOWN_HISTORY_DECLARED distinctions;
- conservative known-history wording;
- VAT/tax claim qualification and no invented HullQ verification;
- escaped/untrusted broker text boundary;
- no creator/internal hashes/revision-history/transaction metadata exposure;
- no model/design fact promotion into claims about the individual yacht.

Preview-token verification MUST NOT be required for the public ACTIVE route.

## 7. Canonical public web route

The first production-public NativeListing page class is:

```text
/listings/{NativeListingId}
```

For 0049:

```text
NativeListingId = stable page identity
slug = NONE
query-string identity = NONE
```

Do not invent model/name/location slugs before a later accepted public URL taxonomy defines them. A human-readable slug MUST NOT become the sole canonical identity key.

Astro obtains listing data through FastAPI only. No direct browser/web-package PostgreSQL access and no duplicated Python/domain lifecycle rules.

An ACTIVE listing page MUST be viewable in an ordinary browser without preview token/session credentials.

DRAFT and WITHDRAWN identities MUST render the same ordinary not-found result rather than a public status disclosure page.

### 7.1 0049 indexation boundary

0049 establishes a stable public listing URL but intentionally does NOT launch the listing class as an organic-search distribution surface.

Public listing responses/pages MUST therefore be deliberately non-indexable for this slice, using appropriate robots directives such as:

```text
X-Robots-Tag: noindex
<meta name="robots" content="noindex">
```

A self-referential canonical URL for the ACTIVE listing page is acceptable/required where the web response exposes canonical metadata, but 0049 MUST NOT add listing URLs to XML sitemaps, generate hreflang trees, create faceted/listing landing pages, or claim resolution of OQ-018 beyond this single bounded NativeListing page-class decision.

The preview URLs from 0048 remain non-canonical, capability-gated and excluded from public linking/indexation.

## 8. Operator-assisted lifecycle command

Provide one bounded operator/CLI-assisted lifecycle path for `publish` and `withdraw` using explicit stable identifiers and explicit SLICE-0041 principal inputs.

The command/use case MUST report a deterministic result and MUST NOT silently repair unsupported state. Representative result classes should distinguish at least:

- transition applied;
- exact unsupported/current-state conflict;
- listing not found/incomplete;
- authorization denied;
- Organization mismatch;
- persistence conflict/failure.

Exact naming is implementation-specific if semantics remain explicit and typed.

Direct manual database updates are not the acceptance path.

## 9. Concurrency and atomicity

Lifecycle transitions are state changes and MUST be safe under concurrent attempts.

At most one competing request may successfully apply a transition from the same expected current state. The implementation MUST prevent double-transition/double-audit outcomes and stale writers from overwriting a later lifecycle state.

Required examples:

```text
two concurrent DRAFT → ACTIVE attempts
→ exactly one transition applied
→ one matching immutable publication record
→ final state ACTIVE
```

and:

```text
stale DRAFT → ACTIVE attempt after listing is already ACTIVE/WITHDRAWN
→ no mutation
→ no extra history record
```

Use PostgreSQL transactional/locking/compare-and-set semantics appropriate to the existing persistence architecture; do not emulate atomicity in application memory.

## 10. Security / presentation boundary

0049 removes the secret bearer capability from the production ACTIVE URL. It therefore MUST NOT copy preview-token confidentiality behavior into the public route.

However:

- broker/operator-controlled text remains untrusted and must render escaped/inert;
- API errors and browser pages must not expose internal stack traces, database details or actor credentials;
- no external authorization principal data should appear in the public read model unless separately accepted as public attribution;
- public visibility is determined solely by the accepted ACTIVE predicate, never by obscurity of NativeListingId.

Do not weaken the security or noindex/no-store constraints of the existing 0048 preview surface while adding the public surface.

## 11. Owner-visible end-to-end proof

Retain one deterministic local/PostgreSQL 18 + real HTTP proof extending the 0048 vertical.

Minimum proof:

1. migrate database to one current Alembic head;
2. demonstrate a pre-existing/migrated listing is DRAFT and not publicly readable;
3. create/reuse one complete accepted listing chain and current offer;
4. attempt publish with a denied/wrong-Organization principal and prove no state/history/public visibility change;
5. publish with an explicit eligible owning principal;
6. prove exactly one immutable DRAFT → ACTIVE record exists;
7. fetch the production public FastAPI route without preview token and verify accepted persisted content;
8. fetch `/listings/{NativeListingId}` over Astro SSR in a normal browser/HTTP client without preview token and verify visible persisted listing content;
9. verify the page is deliberately `noindex` and uses the intended canonical public identity;
10. withdraw with an authorized owning principal;
11. prove exactly one immutable ACTIVE → WITHDRAWN record was appended;
12. prove the production API and Astro public URL now return ordinary not-found and reveal no hidden listing state;
13. prove `WITHDRAWN → ACTIVE` is unsupported and leaves state/history unchanged;
14. prove the 0048 preview boundary still behaves according to its accepted contract;
15. end with:

```text
FIRST PRODUCTION PUBLIC LISTING RESULT -> PASS
```

Loopback/local HTTP is sufficient for acceptance. Production VPS/Cloudflare deployment is not required by this slice.

## 12. Testing requirements

### Migration / persistence

Cover:

- all pre-existing NativeListings become DRAFT;
- no migration path creates ACTIVE listings;
- lifecycle-state database constraint/typed mapping;
- immutable publication-transition records;
- atomic current-state + audit write;
- rollback on audit/state write failure;
- concurrent same-state transition safety;
- stale expected-state rejection;
- no duplicate audit on denied/failed/unsupported transition.

### Authorization

Cover publish and withdraw with:

- exact eligible owning principal;
- no membership;
- account mismatch;
- Organization mismatch;
- inactive membership;
- missing explicit PUBLISHER role;
- INELIGIBLE Organization;
- UNVERIFIED Organization;
- cross-Organization attempt;
- denied transitions leave state/history unchanged.

### Lifecycle

Cover:

```text
DRAFT → ACTIVE succeeds when all gates pass
ACTIVE → WITHDRAWN succeeds when all gates pass
DRAFT → WITHDRAWN unsupported
ACTIVE → ACTIVE unsupported/idempotency behavior explicit
WITHDRAWN → ACTIVE unsupported
WITHDRAWN → WITHDRAWN unsupported/idempotency behavior explicit
```

Do not add SOLD/ARCHIVED/republish semantics merely to make tests convenient.

### API / public read

Cover:

- ACTIVE complete listing returns accepted public read model;
- DRAFT is externally not-found;
- WITHDRAWN is externally not-found;
- missing/incomplete is externally not-found-equivalent;
- no preview token required for ACTIVE public route;
- accepted price/assertion/history/VAT semantics remain intact;
- no internal actor/audit/revision metadata leaks;
- malicious HTML/script-like broker text remains escaped/inert at web presentation.

### Web

Cover:

- Astro check/build;
- `/listings/{NativeListingId}` SSR for ACTIVE listing;
- DRAFT/WITHDRAWN ordinary not-found behavior;
- no direct DB access;
- no client-side reimplementation of lifecycle authorization;
- deliberate noindex directive;
- stable ID-based canonical identity;
- no sitemap/hreflang/faceted SEO expansion;
- 0048 preview route remains distinct and protected.

## 13. CI / reproducibility

All existing Python quality, PostgreSQL 18, coverage, historical replay/manufacturer reproducibility and web gates remain mandatory and MUST NOT be weakened.

At least one canonical Linux/PostgreSQL job MUST exercise the real lifecycle + HTTP public-listing vertical proof if deterministic.

No quality threshold may be lowered to land 0049.

## 14. Explicit out of scope

Not authorized in SLICE-0049:

- Auth0/session implementation;
- persisted generic Account/Organization/Membership directory;
- broker workspace/browser publication form;
- external professional verification/KYB/KYC;
- republish / `WITHDRAWN → ACTIVE`;
- SOLD, ARCHIVED or other lifecycle states;
- freshness TTL, stale/disappeared logic or automatic lifecycle transitions;
- media upload/gallery;
- PhysicalBoat marketplace-fact expansion;
- public search/list/ranking/discovery;
- saved searches/alerts;
- leads/contact routing;
- price-history product;
- slugs beyond stable NativeListingId identity;
- listing sitemap publication;
- hreflang/multilingual production URL matrix;
- broad OQ-018 resolution for BoatModel/BoatDesign/faceted landing pages;
- external feed/API/CSV ingestion;
- dedup/merge expansion;
- LLM extraction;
- deployment/VPS/Cloudflare/DNS automation;
- mobile app.

## 15. Expected touch points

Likely smallest coherent set includes:

- one Alembic migration for lifecycle + immutable publication-transition persistence;
- bounded lifecycle domain/application types/use case;
- persistence operations/tests for atomic transitions/history;
- operator lifecycle command/inspection fixture;
- FastAPI public listing read route/use case;
- Astro `/listings/{NativeListingId}` SSR route;
- unit/persistence/web tests;
- retained real PostgreSQL/HTTP inspection path;
- CI additions only where required for the new proof.

Do not refactor unrelated marketplace architecture merely because these files are touched.

## 16. Acceptance criteria

SLICE-0049 is acceptable only when all are true:

- [ ] lifecycle vocabulary is exactly DRAFT / ACTIVE / WITHDRAWN for this slice;
- [ ] only DRAFT → ACTIVE and ACTIVE → WITHDRAWN are supported;
- [ ] pre-existing listings migrate to DRAFT and never auto-publish;
- [ ] real SLICE-0041 eligibility is exercised for publish and withdraw;
- [ ] cross-Organization lifecycle mutation fails closed;
- [ ] every successful transition atomically appends one immutable audit record;
- [ ] denied/failed/unsupported transitions append no audit and change no state;
- [ ] concurrent/stale lifecycle writes cannot double-apply or overwrite newer state;
- [ ] only complete ACTIVE listings are publicly readable;
- [ ] DRAFT/WITHDRAWN/missing/incomplete listings are externally not-found-equivalent;
- [ ] ACTIVE listing is readable through FastAPI without preview token;
- [ ] ACTIVE listing is browser-visible through Astro at `/listings/{NativeListingId}` without preview token;
- [ ] public listing page is deliberately noindex in 0049;
- [ ] no sitemap/hreflang/search/faceted SEO expansion is introduced;
- [ ] accepted 0048 preview security and behavior remain intact;
- [ ] owner-visible PostgreSQL + real HTTP proof ends `FIRST PRODUCTION PUBLIC LISTING RESULT -> PASS`;
- [ ] full local/repository/CI gates pass on the exact implementation HEAD;
- [ ] no out-of-scope Auth0/workspace/search/media/freshness/republish work is pulled forward.

## 17. Implementation handoff rule

Implementation MUST begin only from this readiness contract after it is independently reviewed, accepted and merged to `main`, and after `docs/PROJECT_STATE.md` marks SLICE-0049 READY.

Use the normal `START_SLICE.bat` workflow only after that merge. The implementation agent must leave the slice in `REVIEW` or `BLOCKED`, push the exact slice branch, and stop for independent review; it must not owner-accept or merge its own implementation.
