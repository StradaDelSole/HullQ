# SLICE-0048 — First browser-visible listing preview vertical

**Type:** IMPLEMENTATION  
**Status:** READY  
**Base main:** `8418c99dd7d766dff78293bafe898cc180e8812e`  
**Product horizon:** this is the committed first-visible-listing vertical; no foundation-only slice may be inserted ahead of it.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
**VISIBLE-RESULT CHECK:** PASS  
**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  

## 1. One capability

Given one explicit operator-supplied eligible professional publishing principal and one complete accepted `LISTING_OFFER` snapshot, create/reuse the already-accepted durable marketplace identity chain and produce a shareable, time-bounded browser preview of that real persisted listing through FastAPI + Astro:

```text
operator-assisted intake
→ PhysicalBoat
→ MarketEpisode
→ NativeListing
→ first/current LISTING_OFFER revision
→ signed preview capability
→ FastAPI preview read model
→ Astro SSR preview page
→ another human can view the listing in a browser
```

This is one deliberately narrow vertical capability. It is not a production broker workspace and it is not final public-publication/lifecycle semantics.

## 2. Why the visible surface is a preview, not implicit publication

Accepted SLICE-0043/0047 persistence explicitly distinguishes durable listing creation from public publication. `NativeListing` currently has no accepted publication/lifecycle state.

Therefore 0048 MUST NOT introduce this false rule:

```text
NativeListing exists durably
→ anyone knowing NativeListingId may read it publicly
```

That would silently collapse persistence into publication and make every durable unresolved/testing/operator listing de facto public.

The minimum safe visible proof is instead a capability-gated preview:

```text
valid signed time-bounded preview token
+ complete durable listing chain
+ current offer head
→ preview may be read/rendered
```

Hard:

```text
PREVIEWABLE != PUBLISHED
PREVIEW TOKEN != AUTHENTICATED BROKER SESSION
PREVIEW TOKEN != CANONICAL PUBLIC LISTING URL
DURABLE CREATION != PUBLICATION
```

A later slice must explicitly design real publication/lifecycle, withdrawal/freshness, canonical public URL/indexability and production authorization. 0048 MUST NOT pretend those decisions are already made.

## 3. Existing accepted inputs and boundaries

0048 reuses, and MUST NOT duplicate or reinterpret, these accepted capabilities:

- SLICE-0041: professional publishing eligibility evaluator;
- SLICE-0043/0047: immutable authorized `NativeListing` creation;
- SLICE-0045: immutable revisioned current `LISTING_OFFER` head;
- SLICE-0046: durable `PhysicalBoat` identity;
- SLICE-0047: durable `MarketEpisode -> PhysicalBoat` and nullable `NativeListing -> MarketEpisode` integrity.

Identity remains:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId
```

Truth remains:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

0048 MUST NOT join canonical BoatDesign baseline facts and display them as facts about the individual yacht.

## 4. Minimal operator-assisted intake

Add one explicit operator/CLI-assisted intake path. A browser broker form, Auth0 wiring and persisted marketplace-actor directory remain out of scope.

The intake input MUST explicitly provide the values needed to construct the already-accepted runtime objects, including:

```text
AccountId
MarketplaceOrganization
OrganizationMembership
PhysicalBoatId
optional BoatDesignRef
MarketEpisodeId
NativeListingId
optional broker_listing_reference
NativeListingOfferRevisionId
exact nine-field NativeListingOfferSnapshot
```

Stable identity IDs and offer revision ID MUST be supplied explicitly in the intake payload; retries must not silently generate new identities.

The temporary operator input may construct the 0041 Account/Organization/Membership domain records from explicit JSON/CLI data because actor persistence/Auth0 is not yet accepted. It MUST still call the real accepted 0041 evaluator through the existing persistence operations; a caller-supplied `authorized=true` shortcut is forbidden.

### 4.1 Intake orchestration order

The operator path MUST call the accepted persistence boundaries in this order:

```text
1. create/reuse PhysicalBoat
2. create/reuse MarketEpisode bound to that PhysicalBoat
3. create/reuse authorized NativeListing already linked to that MarketEpisode
4. create/reuse the first offer revision with expected_current_revision_id = NONE
5. only after all four stages are successful/idempotently identical, emit a preview URL/token
```

Accepted continuation statuses for the first three identity stages are their existing exact `CREATED` / `ALREADY_EXISTS` success cases. Any existing-domain `CONFLICT`, missing referenced identity, authorization denial or other failure stops the orchestration and returns a non-zero operator result.

For the offer stage, this first-visible intake path is intentionally first-revision-only:

```text
expected_current_revision_id = NONE
```

Success is only:

```text
CREATED
or
ALREADY_EXISTS for the exact same immutable revision
```

A pre-existing different current head, stale expectation, reused revision ID with different content, cross-Organization denial or other existing failure is not silently repaired/revised by the intake command.

### 4.2 Retry and partial-progress semantics

Do NOT wrap the four accepted self-committing persistence operations in a fake aggregate transaction.

Earlier slices deliberately guarantee that each returned `CREATED` is already durably committed from an IDLE caller connection. Therefore an operator intake interrupted after stage 1/2/3 may leave valid partial durable state.

Required behavior:

```text
retry same exact input
→ reuse CREATED/ALREADY_EXISTS semantics
→ continue safely from durable partial progress
```

Hard:

```text
partial durable progress after operator interruption
!= corruption
```

The intake command MUST report stage-by-stage status and MUST NOT claim all-or-nothing rollback across already committed boundaries.

### 4.3 Intake payload handling

The operator input format may be one versioned JSON document read from a file. It must be schema/typed validated before values are converted into accepted domain objects.

Secrets MUST NOT be present in retained example payloads or committed fixtures.

The command MUST NOT:

- create placeholder BoatDesign records;
- auto-match/deduplicate yachts;
- infer PhysicalBoat technical facts from BoatDesign;
- invent missing offer facts;
- parse broker prose into structured yacht facts;
- bypass 0041 eligibility;
- mutate an existing NativeListing creation envelope;
- mutate an existing offer revision.

## 5. Preview capability token

After successful/idempotent intake, generate a time-bounded signed preview capability using only standard-library cryptography primitives unless an already-accepted dependency is more appropriate.

Minimum token security contract:

- HMAC-SHA-256 or stronger keyed MAC;
- signing secret loaded from environment, never hard-coded or committed;
- signing secret minimum 32 bytes after decoding/normalization;
- token binds at least:
  - token format/version;
  - exact `NativeListingId`;
  - expiry timestamp;
- signature verification uses constant-time comparison;
- tampered token fails closed;
- expired token fails closed;
- malformed token fails closed;
- token must be URL-safe;
- preview token value MUST NOT be written to ordinary application logs;
- a token is a bearer capability: anyone possessing it may view that preview until expiry.

The intake CLI may default to a short proof-oriented TTL (for example 24 hours) and MAY allow a bounded operator override, but MUST enforce a finite expiry and a documented maximum no greater than seven days for 0048.

Token generation is stateless; 0048 does not add a preview-token database table, revocation UI or session system. Rotating the preview signing secret invalidates outstanding preview links. These are deliberate proof-stage limitations, not production authentication semantics.

## 6. FastAPI application boundary

0048 introduces the repository's first FastAPI application surface.

Add FastAPI as the sole Python HTTP backend in accordance with the accepted application architecture. Do not introduce Flask/Django/Node business-logic backend or a second API service.

Route handlers MUST remain thin. The listing-preview composition belongs in an application/use-case module which calls accepted persistence read functions.

### 6.1 Deliberately unstable preview route

Because the final public API version contract remains a separate product/API decision, 0048 MUST NOT pretend to freeze the stable public API namespace.

Use an explicitly non-stable preview namespace, equivalent to:

```text
GET /api/_preview/listings/{preview_token}
```

The exact spelling may vary only if it remains mechanically and visibly non-canonical/non-stable. A route such as `/api/v1/listings/...` is NOT authorized by this slice.

### 6.2 Previewable read predicate

A valid token alone is insufficient. The application read model must fail closed unless all of the following durable state exists and agrees:

```text
NativeListing exists
AND NativeListing.market_episode_id is non-null
AND referenced MarketEpisode exists
AND referenced PhysicalBoat exists
AND explicit current LISTING_OFFER head exists
AND current head resolves to a typed offer revision for that NativeListing
```

If any element is missing/inconsistent, the preview is not renderable.

Do not infer current offer from timestamps or history order. Use the explicit accepted `native_listing_offer_heads` relationship through the accepted read boundary.

Invalid/tampered/expired tokens, missing listings and incomplete/non-previewable chains SHOULD collapse to the same ordinary not-found response at the HTTP boundary so the preview endpoint does not become a general listing-ID existence oracle.

### 6.3 Read model scope

The preview API may expose only the accepted `PUBLIC` presentation fields from the current nine-field `LISTING_OFFER` snapshot plus the minimal attribution/disclosure metadata required by accepted presentation policy.

Minimum visible payload:

```text
asking_price_mode
asking_price_amount (decimal serialized losslessly; never binary float)
currency
location_country
location_region assertion/value when present
broker_summary assertion/value when present
broker_description
known_history_narrative assertion/value when present
vat_tax_status_claim assertion/value when present
```

Omitted field stays omitted/null as defined by the API model and MUST remain distinct from explicit `UNKNOWN`, `NOT_APPLICABLE` or `NO_KNOWN_HISTORY_DECLARED` assertions.

The API MUST NOT flatten these distinctions into a single empty string/boolean.

Not authorized for preview output:

- creator Account identity;
- full immutable revision history;
- internal content hashes;
- internal transaction metadata;
- inferred PhysicalBoat facts;
- BoatDesign baseline values presented as yacht facts;
- search/ranking scores;
- verification booleans that do not exist.

The response MAY carry opaque listing/preview identifiers needed by the page, but internal IDs are not required simply for display.

### 6.4 Sensitive VAT/tax presentation

`listing_offer.vat_tax_status_claim` is accepted as `PUBLIC + SENSITIVE + DISPLAY_ONLY` with a presentation policy requiring qualification, attribution, last-confirmed/recorded disclosure and verification-status disclosure.

If a VAT/tax claim is rendered, the FastAPI/Astro surface MUST preserve this meaning, equivalent to:

```text
VAT/tax status: broker-declared <value>
Publishing organization: <persisted organization attribution>
Broker declaration recorded/last confirmed in HullQ: <revision recorded_at>
HullQ legal verification: none
```

For explicit `UNKNOWN`, render it as unknown broker-declared status with the same attribution/timestamp/verification-none disclosure.

Never render:

```text
VAT paid ✓
verified VAT
HullQ verified
```

unless a later accepted verification capability actually exists.

## 7. Astro browser surface

0048 introduces the repository's first web package using the already-accepted frontend baseline:

```text
Astro + TypeScript
```

React is not justified for this page and SHOULD NOT be added merely because the architecture permits bounded React islands.

The preview route should be equivalent to:

```text
/_preview/listings/{preview_token}
```

It must be server-rendered and obtain listing data through the FastAPI boundary. The Astro server MUST NOT query PostgreSQL directly and MUST NOT reimplement Python domain rules.

### 7.1 Explicit non-indexability

The preview page is not a canonical public listing page.

Required:

- `<meta name="robots" content="noindex,nofollow,noarchive">` or stronger equivalent;
- `X-Robots-Tag: noindex, nofollow, noarchive` where practical at the app response boundary;
- no canonical-link claim for this preview URL;
- no sitemap entry;
- no internal public-search link architecture built around preview tokens.

This keeps the accepted SEO principle intact: arbitrary/provisional routes must not accidentally become indexable product URLs.

### 7.2 Minimum page content

The browser page should visibly render, without requiring developer tools:

- clear `HullQ listing preview` / `Preview — not a published listing` status;
- asking price or `Price on application`;
- country and region assertion where available;
- broker summary when it has a value assertion;
- broker description;
- known-history narrative semantics without converting `NO_KNOWN_HISTORY_DECLARED` into proof that no event occurred;
- qualified VAT/tax disclosure when present;
- preview expiry or a concise preview-status notice.

The page does not need media, polished design system, filters, contact lead form or yacht technical-spec cards.

Because this route is explicitly non-canonical/non-indexed proof infrastructure, 0048 does not freeze final multilingual canonical URL grammar. Do not create a fake production i18n routing scheme merely to satisfy the preview. Final canonical public listing pages remain subject to the accepted mandatory language/product SEO architecture.

## 8. Configuration

Use environment configuration; no credentials/secrets committed.

Minimum runtime configuration may include equivalents of:

```text
HULLQ_DATABASE_URL
HULLQ_PREVIEW_SIGNING_SECRET
HULLQ_API_BASE_URL / web server-side API origin
HULLQ_PREVIEW_BASE_URL (operator output convenience)
```

Names may follow existing project conventions if an equivalent configuration layer is introduced, but there must be one clear documented source of truth.

Missing/invalid signing secret or DB URL must fail fast with a useful startup/operator error, not silently fall back to insecure defaults.

## 9. Dependencies and package boundaries

Python:

- add FastAPI;
- add the minimal ASGI server dependency required for owner-visible local execution (e.g. Uvicorn);
- do not add an ORM or alternate persistence framework merely for this slice.

Web:

- add one bounded Astro + TypeScript package;
- use the minimal Node adapter required for SSR/local preview runtime;
- commit the package lockfile;
- no React dependency unless a concrete need emerges during implementation and is documented as an amendment.

The existing Python `uv.lock` must remain valid and reproducible after dependency changes.

## 10. Owner-visible end-to-end proof

The slice is not complete merely because unit tests can instantiate a response model.

Add one retained owner inspection path that proves the vertical against real PostgreSQL 18 and real HTTP rendering.

The proof must, from a clean/known test database state:

1. run Alembic to the single current head;
2. create/ensure any required canonical BoatDesign fixture only when the chosen PhysicalBoat references one, otherwise use `BoatDesignRef = NONE`;
3. execute the operator intake with an explicitly eligible 0041 principal;
4. prove the durable PhysicalBoat / MarketEpisode / NativeListing / current offer head exist;
5. generate a finite signed preview capability;
6. serve the FastAPI preview endpoint;
7. serve/build the Astro SSR preview surface;
8. fetch the preview page over HTTP using the generated capability;
9. assert HTTP success and visible listing content;
10. assert the rendered page is `noindex`;
11. assert an invalid/tampered token does not reveal the listing;
12. end with an unmistakable result such as:

```text
FIRST VISIBLE LISTING PREVIEW RESULT -> PASS
```

The proof may use loopback/local HTTP; production VPS/Cloudflare deployment is not required for 0048 acceptance. The accepted result is the first real browser/HTTP product surface backed by real durable marketplace data, not yet a production internet publication rollout.

## 11. Testing requirements

At minimum cover:

### Intake

- happy path from empty marketplace chain to complete previewable listing;
- exact retry is idempotent and emits a valid preview again;
- PhysicalBoat conflict stops later stages;
- missing BoatDesign for a new referenced PhysicalBoat stops later stages;
- MarketEpisode conflict/missing PhysicalBoat stops later stages;
- denied publisher creates no NativeListing/offer;
- NativeListing collision stops offer creation;
- existing different offer head conflicts under first-revision-only intake;
- interruption/partial durable progress can be retried safely;
- no preview token emitted on failed/incomplete intake.

### Token

- valid token round-trip;
- expiry enforced;
- maximum TTL enforced;
- tamper rejected;
- malformed token rejected;
- wrong signing secret rejected;
- short/invalid signing secret rejected;
- constant-time comparison path used;
- token/secret absent from ordinary logs in tested request/operator paths.

### API/read model

- valid preview returns current explicit offer head;
- no timestamp-derived current selection;
- invalid/expired token returns not-found equivalent;
- nonexistent listing returns same external not-found class;
- listing with `market_episode_id = NONE` is not previewable;
- missing/inconsistent chain is not previewable;
- listing without current offer head is not previewable;
- decimal price is lossless/no binary float;
- omission vs explicit assertions preserved;
- `NO_KNOWN_HISTORY_DECLARED` not rendered/serialized as proven no history;
- VAT claim includes required qualification/attribution/time/verification-none disclosure;
- internal revision history/account/hash metadata not exposed.

### Web

- Astro build/check succeeds;
- valid preview page visibly renders price/location/description from FastAPI;
- preview-only status visible;
- VAT/history wording remains conservative;
- noindex/nofollow/noarchive present;
- invalid preview returns 404/not-found page rather than listing content;
- no direct DB access exists in web package.

## 12. CI / reproducibility

Existing Python quality, PostgreSQL 18 full-suite coverage, historical replay and manufacturer-reproducibility gates remain mandatory and must not be weakened.

Because 0048 adds the first Node/Astro package, CI must add a deterministic web gate equivalent to:

```text
Node pinned/supported version
npm ci (or accepted locked package-manager equivalent)
Astro/type check
web build
bounded web tests/smoke proof
```

Do not remove or reduce the existing Python 90% coverage threshold to accommodate web work.

The owner-visible end-to-end proof should run in CI where reasonably deterministic. If starting both HTTP services inside CI is platform-sensitive, at minimum one canonical Linux/PostgreSQL job must execute the real HTTP proof; cross-platform Python quality and deterministic web build remain separate required gates.

## 13. Explicit out of scope

Not authorized in SLICE-0048:

- production publication/lifecycle state;
- publish/unpublish/withdraw/sold workflows;
- Auth0 login/session implementation;
- persisted Account/Organization/Membership directory;
- broker browser workspace/form;
- media/image upload;
- PhysicalBoat marketplace fact persistence;
- contact/lead submission;
- public search/list results/ranking;
- saved searches/alerts;
- price-history product;
- canonical SEO listing URL grammar;
- sitemap generation;
- final multilingual production routing;
- external feed/API ingestion;
- dedup/merge engine;
- LLM extraction;
- deployment automation, VPS provisioning, Cloudflare/DNS changes;
- mobile app.

## 14. Expected touch points

Implementation is expected to touch only the smallest coherent set, likely including:

- `pyproject.toml`
- `uv.lock`
- new FastAPI/application modules under `src/hullq/`
- one operator intake script/module under `scripts/` and/or `src/hullq/application/`
- tests under `tests/`
- one bounded `web/` Astro package with lockfile/config/page
- `.github/workflows/ci.yml` only as required to install/check/build/test the new web package and run the vertical proof
- this slice document for handoff evidence/status only.

No Alembic migration is expected: the preview token is stateless and 0048 uses the already-accepted durable marketplace tables. A new migration requires an explicit material amendment explaining why the vertical cannot be completed without it.

## 15. Acceptance criteria

SLICE-0048 is acceptable only if all are true on exact final PR HEAD:

1. one operator-assisted command can create/reuse the accepted durable chain through the first offer head without bypassing 0041 authorization;
2. exact retries are safe; conflicts/failures stop fail-closed;
3. no aggregate transaction falsely claims rollback of already self-committed stages;
4. only a valid finite signed preview capability can expose the preview;
5. persisted NativeListing existence alone does not make a listing anonymously readable;
6. FastAPI is the sole backend and route handlers do not own business/domain rules;
7. the preview read model uses the explicit current offer head;
8. only accepted public offer fields + required sensitive-claim disclosure are rendered;
9. money remains lossless decimal/string, never binary float;
10. claim omission/assertion distinctions remain intact;
11. VAT/tax presentation is broker-attributed and explicitly unverified by HullQ;
12. Astro SSR obtains data from FastAPI, never PostgreSQL directly;
13. a real browser/HTTP preview visibly renders the persisted listing;
14. preview is mechanically non-indexable and clearly marked not published;
15. final stable API versioning/canonical URL/i18n/publication semantics are not silently frozen;
16. all new dependencies are locked/reproducible;
17. existing Python CI/coverage/replay/manufacturer gates remain intact;
18. deterministic web build/check/smoke gates are green;
19. retained owner inspection ends `FIRST VISIBLE LISTING PREVIEW RESULT -> PASS`;
20. exact-head independent review has no unresolved material finding;
21. explicit Project Owner acceptance occurs before merge.

## 16. Handoff rule

Claude Code may implement only this slice after `START_SLICE 0048` creates the isolated worktree/branch.

At implementation handoff it must set this document to `**Status:** REVIEW` and provide the standard slice completion report with exact branch HEAD, local validation, remote CI/manufacturer status and unresolved findings.

It MUST NOT mark the slice DONE, merge its own PR or start SLICE-0049.
