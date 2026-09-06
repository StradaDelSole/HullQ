# SLICE-0049 — First production-public NativeListing vertical

**Type:** IMPLEMENTATION  
**Status:** READY  
**Base main:** `967967d078862e527c53a22346ba2ed2e7f95338`  
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

## 2. Why this slice exists

SLICE-0048 proved the full real-data application path through persistence, FastAPI, Astro and a browser while deliberately preserving:

```text
PREVIEWABLE != PUBLISHED
DURABLE CREATION != PUBLICATION
```

The post-0048 reassessment compared publication/lifecycle, broker workspace/authentication, native-inventory discovery, PhysicalBoat marketplace facts and media. Publication is the narrowest missing product bridge: broker workflow and buyer discovery should operate on genuine public inventory rather than on preview capabilities.

0049 therefore closes exactly that bridge and no more.

## 3. Controlling artifacts

Implementation must preserve the accepted boundaries in:

- `docs/PRODUCT_EXECUTION_PLAN.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`;
- `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, specifically the requirement that public URL/indexation semantics are intentional and that stable domain IDs remain the identity anchor;
- `specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md` and accepted SLICE-0041 implementation/closure for professional publisher eligibility;
- accepted SLICE-0043 immutable NativeListing creation-envelope/idempotency/transaction semantics;
- accepted SLICE-0047 MarketEpisode linkage semantics;
- accepted SLICE-0045 current `LISTING_OFFER` revision/head semantics;
- accepted SLICE-0046 PhysicalBoat identity/truth separation;
- accepted SLICE-0048 preview/read-model/security semantics where reused by the public read model.

Where this slice makes a deliberately narrower production-public page-class decision, it does not authorize reinterpretation of unrelated OQ-018/search/SEO questions.

## 4. Lifecycle contract

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

### 4.1 Creation-envelope and migration safety

SLICE-0043's accepted immutable NativeListing creation envelope remains exactly:

```text
NativeListingId
publishing_organization_id
created_by_account_id
optional MarketEpisodeId
optional broker_listing_reference
internal deterministic content_hash
created_at
```

0049 MUST NOT reinterpret lifecycle state as part of that immutable semantic envelope. In particular lifecycle changes MUST NOT alter the accepted creation `content_hash`, creation idempotency/collision comparison, `created_at`, publishing Organization, creator Account, MarketEpisode link or broker listing reference.

Every NativeListing that exists before the 0049 lifecycle migration MUST enter the new lifecycle as `DRAFT`. Every NativeListing created after the migration MUST also begin as `DRAFT`.

Hard:

```text
pre-existing listing → DRAFT
new listing → DRAFT
pre-existing listing → never automatically ACTIVE
new listing → never automatically ACTIVE
```

A lifecycle implementation may use an added current-state column or a separate one-to-one current-state projection/table, but either way lifecycle state is semantically outside the accepted 0043 immutable creation envelope and outside its deterministic content hash/collision semantics.

If the existing create path must be extended so a newly created NativeListing receives explicit DRAFT lifecycle state, that extension MUST preserve all accepted 0043 transaction-ownership, durable-commit, idempotency and conflict guarantees. An exact retry of the same immutable NativeListing creation request MUST NOT conflict merely because lifecycle state later changed.

The migration MUST NOT make any previously durable or previewable listing publicly readable merely because 0049 is deployed.

## 5. Immutable publication-transition history

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
current lifecycle state != 0043 immutable creation-envelope truth
```

The current lifecycle-state change and corresponding immutable transition record MUST commit atomically. A successful lifecycle transition with no durable audit record, or an audit record with no matching state transition, is forbidden.

Do not serialize or persist arbitrary internal SLICE-0041 runtime object graphs merely for audit. Retain the minimum durable actor/Organization/transition identity required by this contract.

## 6. Authorization boundary

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

## 7. Publication completeness predicate

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

## 8. Public FastAPI read boundary

Add one production-public read route for an exact NativeListing identity. The API route naming/versioning may remain explicitly bounded/non-final if the repository has not yet accepted a stable global API version contract, but it MUST NOT reuse the preview bearer-token route as the public contract and MUST NOT silently freeze an unrelated API-version policy.

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

## 9. Canonical public web route

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

### 9.1 0049 indexation boundary

0049 establishes a stable public listing URL but intentionally does NOT launch the listing class as an organic-search distribution surface.

Public listing responses/pages MUST therefore be deliberately non-indexable for this slice, using appropriate robots directives such as:

```text
X-Robots-Tag: noindex
<meta name="robots" content="noindex">
```

The ACTIVE page MUST identify `/listings/{NativeListingId}` as its own canonical URL. 0049 MUST NOT add listing URLs to XML sitemaps, generate hreflang trees, create faceted/listing landing pages, or claim resolution of OQ-018 beyond this single bounded NativeListing page-class decision.

The preview URLs from 0048 remain non-canonical, capability-gated and excluded from public linking/indexation.

## 10. Operator-assisted lifecycle command

Provide one bounded operator/CLI-assisted lifecycle path for `publish` and `withdraw` using explicit stable identifiers and explicit SLICE-0041 principal inputs.

The command/use case MUST report a deterministic result and MUST NOT silently repair unsupported state. Representative result classes should distinguish at least:

- transition applied;
- unsupported/current-state conflict;
- listing not found/incomplete;
- authorization denied;
- Organization mismatch;
- persistence conflict/failure.

Exact naming is implementation-specific if semantics remain explicit and typed.

Direct manual database updates are not the acceptance path.

## 11. Concurrency and atomicity

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

## 12. Security / presentation boundary

0049 removes the secret bearer capability from the production ACTIVE URL. It therefore MUST NOT copy preview-token confidentiality behavior into the public route.

However:

- broker/operator-controlled text remains untrusted and must render escaped/inert;
- API errors and browser pages must not expose internal stack traces, database details or actor credentials;
- no external authorization principal data should appear in the public read model unless separately accepted as public attribution;
- public visibility is determined solely by the accepted ACTIVE predicate, never by obscurity of NativeListingId.

Do not weaken the security or noindex/no-store constraints of the existing 0048 preview surface while adding the public surface.

## 13. Owner-visible end-to-end proof

Retain one deterministic local/PostgreSQL 18 + real HTTP proof extending the 0048 vertical.

Minimum proof:

1. migrate database to one current Alembic head;
2. demonstrate a pre-existing/migrated listing is DRAFT and not publicly readable;
3. demonstrate a newly created listing also begins DRAFT without changing 0043 immutable create idempotency/collision semantics;
4. create/reuse one complete accepted listing chain and current offer;
5. attempt publish with a denied/wrong-Organization principal and prove no state/history/public visibility change;
6. publish with an explicit eligible owning principal;
7. prove exactly one immutable DRAFT → ACTIVE record exists;
8. fetch the production public FastAPI route without preview token and verify accepted persisted content;
9. fetch `/listings/{NativeListingId}` over Astro SSR in a normal browser/HTTP client without preview token and verify visible persisted listing content;
10. verify the page is deliberately noindex and has the intended self-canonical public identity;
11. prove an exact retry of the original immutable NativeListing creation envelope does not conflict merely because lifecycle is ACTIVE;
12. withdraw with an authorized owning principal;
13. prove exactly one immutable ACTIVE → WITHDRAWN record was appended;
14. prove the production API and Astro public URL now return ordinary not-found and reveal no hidden listing state;
15. prove `WITHDRAWN → ACTIVE` is unsupported and leaves state/history unchanged;
16. prove another exact retry of the original immutable NativeListing creation envelope still preserves accepted 0043 idempotency after withdrawal;
17. prove the 0048 preview boundary still behaves according to its accepted contract;
18. end with:

```text
FIRST PRODUCTION PUBLIC LISTING RESULT -> PASS
```

Loopback/local HTTP is sufficient for acceptance. Production VPS/Cloudflare deployment is not required by this slice.

## 14. Testing requirements

### Migration / persistence

Cover:

- all pre-existing NativeListings begin DRAFT;
- all newly created NativeListings begin DRAFT;
- no migration/create path automatically creates ACTIVE listings;
- lifecycle-state database constraint/typed mapping;
- lifecycle state is excluded from 0043 immutable content hash and creation collision semantics;
- exact immutable creation retry remains `ALREADY_EXISTS`/accepted equivalent after ACTIVE and WITHDRAWN lifecycle changes;
- immutable publication-transition records;
- atomic current-state + audit write;
- rollback on audit/state write failure;
- concurrent same-state transition safety;
- stale expected-state rejection;
- no duplicate audit on denied/failed/unsupported transition;
- accepted 0043 top-level transaction ownership and durability guarantees remain intact if create persistence is touched.

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
- self-canonical stable ID-based public identity;
- no sitemap/hreflang/faceted SEO expansion;
- 0048 preview route remains distinct and protected.

## 15. CI / reproducibility

All existing Python quality, PostgreSQL 18, coverage, historical replay/manufacturer reproducibility and web gates remain mandatory and MUST NOT be weakened.

At least one canonical Linux/PostgreSQL job MUST exercise the real lifecycle + HTTP public-listing vertical proof if deterministic.

Do not reduce the existing Python coverage threshold or weaken current repository-validation gates to land 0049.

## 16. Explicit out of scope

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

## 17. Expected touch points

Likely smallest coherent set includes:

- one Alembic migration for lifecycle + immutable publication-transition persistence;
- bounded lifecycle domain/application types/use case;
- persistence operations/tests for current lifecycle and atomic transition history while preserving the 0043 immutable creation envelope;
- operator lifecycle command/inspection fixture;
- FastAPI public listing read route/use case;
- Astro `/listings/{NativeListingId}` SSR route;
- unit/persistence/web tests;
- retained real PostgreSQL/HTTP inspection path;
- CI additions only where required for the new proof;
- this slice document for implementation handoff status/evidence.

Do not refactor unrelated marketplace architecture merely because these files are touched.

## 18. Acceptance criteria

Accept only if all are true on exact final implementation PR HEAD:

1. lifecycle vocabulary is exactly DRAFT / ACTIVE / WITHDRAWN for this slice;
2. only DRAFT → ACTIVE and ACTIVE → WITHDRAWN are supported;
3. pre-existing and newly created listings begin DRAFT and never auto-publish;
4. 0043 immutable creation-envelope fields, content hash, idempotency/collision and created-at semantics remain unchanged by lifecycle transitions;
5. exact immutable create retries remain accepted/idempotent after lifecycle changes;
6. real SLICE-0041 eligibility is exercised for publish and withdraw;
7. cross-Organization lifecycle mutation fails closed;
8. every successful transition atomically appends one immutable audit record;
9. denied/failed/unsupported transitions append no audit and change no state;
10. concurrent/stale lifecycle writes cannot double-apply or overwrite newer state;
11. only complete ACTIVE listings are publicly readable;
12. DRAFT/WITHDRAWN/missing/incomplete listings are externally not-found-equivalent;
13. ACTIVE listing is readable through FastAPI without preview token;
14. ACTIVE listing is browser-visible through Astro at `/listings/{NativeListingId}` without preview token;
15. ACTIVE public page is self-canonical and deliberately noindex in 0049;
16. no sitemap/hreflang/search/faceted SEO expansion is introduced;
17. accepted 0048 preview security and behavior remain intact;
18. owner-visible PostgreSQL + real HTTP proof ends `FIRST PRODUCTION PUBLIC LISTING RESULT -> PASS`;
19. full local/repository/CI gates pass on the exact implementation HEAD;
20. no out-of-scope Auth0/workspace/search/media/freshness/republish work is pulled forward;
21. exact-head independent implementation review has no material finding;
22. explicit Project Owner acceptance occurs before implementation merge.

## 19. Stop conditions

Stop and return `BLOCKED` rather than inventing policy if implementation reveals that any of the following cannot be satisfied within this contract:

- lifecycle implementation would require mutating or rehashing any accepted 0043 immutable NativeListing creation-envelope field;
- lifecycle state cannot remain outside 0043 creation idempotency/collision semantics;
- a safe DRAFT backfill/new-listing DRAFT default cannot be implemented without making listings public or weakening accepted create durability;
- atomic lifecycle-state + immutable-history persistence cannot be achieved within the existing PostgreSQL persistence boundary;
- production public read requires a new truth claim or PhysicalBoat/model projection not already accepted;
- the chosen public route would require resolving broader OQ-018/i18n/search policy rather than remaining the bounded ID-based noindex page class defined here;
- implementation would require Auth0, a persisted actor directory, broker workspace, freshness, media or public search to make the capability work.

A blocker must be reported with the smallest concrete architectural amendment needed; do not broaden the slice silently.

## 20. Implementation handoff rule

Implementation may begin only after this readiness contract has been independently reviewed, accepted and merged to `main`, with `docs/PROJECT_STATE.md` marking SLICE-0049 READY.

Use the normal `START_SLICE.bat` workflow after that merge. Claude Code may implement only this slice on its generated isolated worktree/branch.

At handoff it MUST set `**Status:** REVIEW` (or `BLOCKED` when applicable), provide the standard completion report with exact branch HEAD, validation, remote CI/manufacturer state and unresolved findings, push the exact slice branch, and stop.

It MUST NOT mark DONE, owner-accept, merge its own implementation or start SLICE-0050.
