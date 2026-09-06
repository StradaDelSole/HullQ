# SLICE-0048 — Acceptance closure

**Slice:** SLICE-0048  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #156  
**Accepted implementation HEAD:** `7fd92cd00eec9caf7146477546f216e6637bc4cc`  
**Implementation merge commit:** `0aa027b325042e4f21339c186dc035c6de85707b`  
**Independent final ACCEPT review:** `5123867811`  
**Owner acceptance:** explicitly recorded 2026-09-06

## Accepted capability

SLICE-0048 completes HullQ's first browser-visible real listing vertical while preserving the accepted distinction between durable listing creation and production publication.

Accepted end-to-end capability:

```text
operator-assisted intake
→ PhysicalBoat
→ MarketEpisode
→ NativeListing
→ first/current LISTING_OFFER revision
→ finite signed preview capability
→ FastAPI preview read model
→ Astro SSR preview page
→ another human can view persisted listing data in a browser
```

This is the first accepted application surface spanning PostgreSQL, the Python application layer, FastAPI and Astro.

Hard boundary retained:

```text
PREVIEWABLE != PUBLISHED
DURABLE CREATION != PUBLICATION
PREVIEW TOKEN != AUTHENTICATED BROKER SESSION
PREVIEW TOKEN != CANONICAL PUBLIC LISTING URL
```

No production publication/lifecycle model was invented merely to make a listing visible.

## Operator-assisted intake

The accepted intake orchestration reuses the existing marketplace persistence capabilities in fixed order:

```text
1. create/reuse PhysicalBoat
2. create/reuse MarketEpisode bound to that PhysicalBoat
3. create/reuse authorized NativeListing linked to that MarketEpisode
4. create/reuse the first LISTING_OFFER revision with expected_current_revision_id = NONE
5. mint a preview capability only after every stage succeeds/idempotently matches
```

The orchestration does not create a fake aggregate transaction around already self-committing persistence operations. Partial durable progress after interruption is valid and exact-input retry continues through existing `CREATED` / `ALREADY_EXISTS` semantics.

The real SLICE-0041 publishing-eligibility evaluator remains in the write path. No caller-provided authorization boolean or bypass was introduced.

A different current offer head, stale first-revision expectation, identity conflict, missing referenced identity or authorization denial stops the intake and mints no preview token.

## Offer-head amendment resolved before acceptance

The original handoff HEAD `aa989eed302ff0625ae932ce134906f1d92944ef` incorrectly treated every SLICE-0045 `ALREADY_EXISTS` offer result as intake success.

Independent AMEND review `5123788117` identified the case:

```text
REV-A originally created
→ current head later advances to REV-B
→ retry original REV-A input
```

The accepted implementation now succeeds on offer-stage `ALREADY_EXISTS` only when:

```text
current_revision_id == requested offer_revision_id
```

Therefore the stale REV-A retry after current head advanced to REV-B resolves:

```text
OFFER_FAILED
preview token = NONE
current head remains REV-B
```

A companion regression proves an exact retry still succeeds when the original revision remains the actual current head.

## Preview capability security

The accepted preview token is stateless and binds:

- token format/version;
- exact `NativeListingId`;
- finite expiry timestamp.

It uses HMAC-SHA-256 with constant-time signature comparison.

`HULLQ_PREVIEW_SIGNING_SECRET` is environment-only, strict base64url and must decode to at least 32 bytes. There is no default/development fallback.

Token TTL is finite; the proof default is 24 hours and the accepted override ceiling is seven days.

### Canonical base64url amendment

Independent AMEND review `5123788117` also identified that Python's lax URL-safe Base64 decoder could ignore invalid characters and therefore accept malformed aliases of a valid bearer token.

The accepted verifier now requires each token segment to be:

```text
strict URL-safe alphabet
+ unpadded
+ decoder validate=True
+ canonical round-trip re-encoding equality
```

The canonical round-trip requirement additionally closes Base64 trailing don't-care-bit aliases: multiple alphabet-valid last characters can otherwise decode to identical bytes for non-3-byte-aligned payloads such as a 32-byte HMAC digest.

Regression coverage proves junk-character injection, stray padding, non-ASCII lookalikes and every alternative final signature character are rejected while the one canonical token still verifies.

Malformed, tampered, expired, wrong-secret, nonexistent-listing and incomplete-chain cases all remain externally not-found-equivalent.

## Bearer-token confidentiality / browser transport

Preview-token-bearing routes are explicitly non-canonical and secret-bearing.

Accepted protections include:

```text
Cache-Control: private, no-store
Referrer-Policy: no-referrer
X-Robots-Tag: noindex, nofollow, noarchive
```

The HTML includes an equivalent robots meta directive.

The retained real-HTTP proof starts Uvicorn with token-safe access logging and proves ordinary captured API/web logs contain neither preview token nor signing secret.

No third-party analytics/tracker/subresource, canonical URL or sitemap linkage was added to the preview surface.

## Previewable read predicate

A valid token alone is insufficient.

The accepted application read path returns a preview only if the full durable chain resolves:

```text
NativeListing exists
AND NativeListing.market_episode_id is non-null
AND referenced MarketEpisode exists
AND referenced PhysicalBoat exists
AND explicit current LISTING_OFFER head exists
```

The current offer is read through the accepted explicit offer-head relationship; timestamp/row-order inference is forbidden.

The public projection is bounded to the accepted nine `LISTING_OFFER` fields plus minimal attribution/disclosure metadata. It does not expose internal identities, creator account identity, hashes, transaction metadata, revision history, search scores or inferred yacht facts.

Decimal prices remain lossless strings rather than binary floats.

## Truth / presentation boundaries retained

SLICE-0048 does not join canonical BoatDesign baseline data and present it as individual-yacht truth.

The accepted truth distinctions remain:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
BROKER_CLAIM != VERIFIED_FACT
UNKNOWN != ABSENT != NO_KNOWN_HISTORY_DECLARED
```

VAT/tax remains a broker-declared sensitive/display-only claim. When present, the preview includes publishing-organization attribution, revision recorded/last-confirmed time and explicit:

```text
HullQ legal verification: none
```

`NO_KNOWN_HISTORY_DECLARED` is rendered conservatively as a broker declaration and never as proof that no event occurred.

All broker/operator-controlled strings are rendered through escaped Astro text interpolation; raw HTML mechanisms are not used. The retained E2E proof includes malicious script-like broker text and proves it remains inert/escaped.

## FastAPI / Astro application boundary

SLICE-0048 introduces HullQ's first accepted FastAPI surface and first bounded Astro + TypeScript web package.

Accepted unstable preview routes are equivalent to:

```text
GET /api/_preview/listings/{preview_token}
GET /_preview/listings/{preview_token}
```

No stable-looking `/api/v1/...` contract was frozen.

Astro obtains listing data only through FastAPI and does not connect to PostgreSQL or reimplement Python domain/business rules.

The underscore-prefixed Astro route is wired with Astro `injectRoute` because underscore path segments are excluded by normal file routing; this retains the exact accepted preview URL without introducing another backend.

React was not added because the preview page does not justify an island/client framework.

## Dependencies / schema

SLICE-0048 adds the minimal Python HTTP dependencies required for the accepted surface:

- FastAPI;
- Uvicorn.

It adds one locked Astro + TypeScript package with the Node SSR adapter.

No ORM, second business-logic backend, React dependency or additional persistence framework was introduced.

No Alembic migration was required. Preview capability state is stateless and the accepted SLICE-0043/0045/0046/0047 marketplace tables are sufficient.

## Independent review and remote verification

Initial implementation HEAD:

```text
aa989eed302ff0625ae932ce134906f1d92944ef
```

Independent AMEND review:

```text
5123788117
```

Material findings fixed on the same slice branch:

1. stale original offer revision could be treated as success after current head advanced;
2. token Base64url verification accepted non-strict/non-canonical aliases;
3. required implementation-handoff marker was missing, causing repository-validation failure.

Final accepted implementation HEAD:

```text
7fd92cd00eec9caf7146477546f216e6637bc4cc
```

Independent final ACCEPT review:

```text
5123867811
```

Exact-head remote verification:

```text
CI run 34007011190
→ SUCCESS
→ quality ubuntu: SUCCESS
→ quality windows: SUCCESS
→ web quality (Astro/Node): SUCCESS
→ dependency audit: SUCCESS
→ PostgreSQL 18 full-suite coverage: SUCCESS
→ repository validation: SUCCESS
→ SLICE-0048 real HTTP vertical proof: SUCCESS
→ complete retained PostgreSQL replay chain: SUCCESS

Manufacturer artifact reproducibility run 34007011219
→ SUCCESS
→ Ubuntu: SUCCESS
→ Windows: SUCCESS
```

Claude's final local validation reported:

```text
4502 passed
2 skipped (live-network only)
coverage 93.44%
Astro check/build PASS
8/8 web tests PASS
FIRST VISIBLE LISTING PREVIEW RESULT -> PASS
```

The remote database job independently executed the retained real PostgreSQL + real HTTP proof on the final exact HEAD.

## Scope retained

SLICE-0048 deliberately did not add:

- production publish/unpublish/withdraw/sold lifecycle;
- canonical public listing URL/indexability grammar;
- Auth0/session implementation;
- persisted production Account/Organization/Membership directory;
- broker browser workspace/form;
- media upload/storage;
- PhysicalBoat marketplace fact persistence beyond identity;
- leads/contact workflow;
- public search/list/ranking over native inventory;
- saved searches/alerts/monitoring;
- price-history intelligence;
- external feeds;
- dedup/merge;
- deployment/VPS/Cloudflare/DNS automation.

These remain post-0048 product-prioritization decisions.

## PROJECT_STATE freshness closure

This acceptance closure advances the highest owner-accepted slice from 0047 to 0048.

In the same closure PR, `docs/PROJECT_STATE.md` is updated to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0048
PROJECT_STATE_QUEUE_SLICE:    0049
```

SLICE-0049 is intentionally not assigned a capability in this closure. Its content must be selected by the required post-0048 architecture/product reassessment after the first browser-visible listing target has been achieved.

The old controlling horizon:

```text
how many slices to first visible listing?
```

is now complete rather than deferred:

```text
FIRST BROWSER-VISIBLE REAL LISTING = BUILT
```

`scripts/validate_repository.py` must fail this closure if the PROJECT_STATE accepted marker and highest acceptance-closure file are not identical.

## Product execution checkpoint

After SLICE-0048, HullQ has crossed the prior product-execution boundary from persistence-only foundations to an actual application surface.

The next reassessment should compare the smallest high-leverage continuation of the buyer/broker loop, especially:

```text
production publication/lifecycle + canonical public listing page
vs
broker workspace/authenticated intake
vs
minimal native-inventory search/discovery
vs
PhysicalBoat marketplace fact capture for useful filtering
```

Media should be prioritized only if it materially blocks the chosen next product loop.

Do not automatically return to foundation completeness. The next slice should make the accepted 0048 vertical more usable, discoverable, publishable or operable.

## Closure decision

```text
SLICE-0048 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
