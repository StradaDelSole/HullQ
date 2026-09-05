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

Given one explicit trusted-operator-supplied eligible professional publishing principal and one complete accepted `LISTING_OFFER` snapshot, create/reuse the already-accepted durable marketplace identity chain and produce a shareable, finite browser preview of that real persisted listing through FastAPI + Astro:

```text
operator-assisted intake
→ PhysicalBoat
→ MarketEpisode
→ NativeListing
→ first/current LISTING_OFFER revision
→ signed finite preview capability
→ FastAPI preview read model
→ Astro SSR preview page
→ another human can view the listing in a browser
```

This is one deliberately narrow vertical capability. It is not a production broker workspace and it is not final public-publication/lifecycle semantics.

## 2. Preview is not publication

Accepted SLICE-0043/0047 persistence explicitly distinguishes durable listing creation from public publication. `NativeListing` currently has no accepted publication/lifecycle state.

0048 MUST NOT introduce this false rule:

```text
NativeListing exists durably
→ anyone knowing NativeListingId may read it publicly
```

The minimum safe visible proof is capability-gated:

```text
valid finite signed preview token
+ complete durable listing chain
+ explicit current offer head
→ preview may be read/rendered
```

Hard:

```text
PREVIEWABLE != PUBLISHED
PREVIEW TOKEN != AUTHENTICATED BROKER SESSION
PREVIEW TOKEN != CANONICAL PUBLIC LISTING URL
DURABLE CREATION != PUBLICATION
```

A later slice must explicitly design real publication/lifecycle, withdrawal/freshness, canonical public URL/indexability and production authorization.

## 3. Existing accepted boundaries

0048 reuses and MUST NOT duplicate or reinterpret:

- SLICE-0041 professional publishing eligibility evaluator;
- SLICE-0043/0047 immutable authorized `NativeListing` creation;
- SLICE-0045 immutable revisioned current `LISTING_OFFER` head;
- SLICE-0046 durable `PhysicalBoat` identity;
- SLICE-0047 durable `MarketEpisode -> PhysicalBoat` and nullable `NativeListing -> MarketEpisode` integrity.

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

Add one explicit operator/CLI-assisted intake path. Browser broker form, Auth0 wiring and persisted marketplace-actor directory remain out of scope.

The input MUST explicitly provide values needed to construct accepted runtime objects:

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

Stable identity IDs and offer revision ID MUST be supplied explicitly; retries must not generate replacement identities.

The temporary Account/Organization/Membership records are trusted operator/bootstrap inputs for this proof only. They are NOT an authenticated browser session, persisted actor authority, external broker verification or future production authorization design. The orchestration MUST still exercise the real accepted SLICE-0041 evaluator through existing persistence operations; `authorized=true` or equivalent bypass is forbidden.

### 4.1 Orchestration order

```text
1. create/reuse PhysicalBoat
2. create/reuse MarketEpisode bound to that PhysicalBoat
3. create/reuse authorized NativeListing already linked to that MarketEpisode
4. create/reuse first offer revision with expected_current_revision_id = NONE
5. only after all four stages succeed/idempotently match, emit preview capability
```

For identity stages, only their existing exact `CREATED` / `ALREADY_EXISTS` success cases may continue. Existing `CONFLICT`, missing referenced identity, authorization denial or other failure stops the orchestration.

The offer path is first-revision-only:

```text
expected_current_revision_id = NONE
```

Success is only `CREATED` or exact immutable `ALREADY_EXISTS`. A different current head, stale expectation, revision-ID collision, cross-Organization denial or other failure is not repaired or revised by this intake command.

### 4.2 Retry / partial progress

Do NOT wrap accepted self-committing persistence operations in a fake aggregate transaction.

Earlier slices guarantee returned `CREATED` is already durably committed. Interruption after stage 1/2/3 may therefore leave valid partial durable state.

Required:

```text
retry exact same input
→ reuse existing CREATED/ALREADY_EXISTS semantics
→ continue safely from durable partial progress
```

Hard:

```text
partial durable progress after interruption != corruption
```

The operator result MUST report stage-by-stage status and MUST NOT claim all-or-nothing rollback across already committed boundaries.

### 4.3 Input handling

One versioned JSON file is acceptable. It MUST be structurally/typed validated before accepted domain objects are constructed. Retained examples/fixtures contain no secrets.

The intake MUST NOT create placeholder BoatDesigns, auto-deduplicate yachts, infer PhysicalBoat facts from BoatDesign, invent offer facts, promote broker prose into structured facts, bypass 0041, mutate a NativeListing creation envelope or mutate an existing offer revision.

## 5. Preview capability security

After successful/idempotent intake, generate a finite signed bearer capability using standard-library primitives unless an already-accepted dependency is more appropriate.

### 5.1 Signing contract

Use HMAC-SHA-256 or stronger keyed MAC.

`HULLQ_PREVIEW_SIGNING_SECRET` MUST be a strict base64url-encoded secret representing at least 32 bytes of cryptographically random key material. Invalid base64url, decoded length below 32 bytes or absent configuration MUST fail fast. No hard-coded/default/development fallback secret is authorized.

The token MUST bind at least token format/version, exact `NativeListingId` and expiry timestamp.

Required:

- signature verification uses constant-time comparison;
- tampered, expired and malformed tokens fail closed;
- token is URL-safe;
- finite expiry mandatory;
- default proof TTL may be 24 hours;
- operator override, if supported, capped at seven days;
- token generation is stateless;
- rotating signing secret invalidates outstanding tokens.

0048 adds no token table, revocation UI, session system or production authentication semantics.

### 5.2 Bearer-token confidentiality boundary

A preview token is a bearer capability and MUST be treated as a secret even though it appears in a shareable URL.

Token values and signing secrets MUST NOT appear in ordinary application logs, access logs, client-visible tracebacks, analytics events or retained test artifacts.

Because the token is carried in the URL path for SSR/shareability, default unredacted request-path access logging is forbidden on token-bearing preview routes. In particular, ordinary Uvicorn access logging MUST NOT remain enabled in a form that records the complete preview path. The implementation MUST disable such logging for the proof/runtime or redact the token before any request-path log is emitted. Astro must provide equivalent protection.

Preview responses MUST send where applicable:

```text
Cache-Control: private, no-store
Referrer-Policy: no-referrer
X-Robots-Tag: noindex, nofollow, noarchive
```

HTML MUST contain an equivalent robots meta directive. The page MUST NOT load third-party analytics, trackers or other third-party subresources in 0048. No canonical link, sitemap entry or public internal-link architecture may point at preview URLs.

## 6. FastAPI application boundary

0048 introduces the repository's first FastAPI surface. FastAPI remains the sole Python HTTP backend; no Flask/Django/Node business-logic backend or second API service.

Route handlers stay thin. Preview composition belongs in an application/use-case module that calls accepted persistence read functions.

### 6.1 Explicitly unstable route

0048 MUST NOT freeze the still-unresolved stable API version contract. Use an explicitly preview/non-canonical route equivalent to:

```text
GET /api/_preview/listings/{preview_token}
```

A stable-looking `/api/v1/listings/...` route is not authorized.

### 6.2 Previewable read predicate

A valid token alone is insufficient. Fail closed unless:

```text
NativeListing exists
AND NativeListing.market_episode_id is non-null
AND referenced MarketEpisode exists
AND referenced PhysicalBoat exists
AND explicit current LISTING_OFFER head exists
AND current head resolves to a typed offer revision for that NativeListing
```

Do not infer current offer from timestamp/history ordering. Use accepted explicit head readback.

Invalid/tampered/expired token, missing listing and incomplete chain MUST collapse to the same ordinary external not-found class so this endpoint is not a listing-ID existence oracle.

### 6.3 Read-model scope

Expose only accepted `PUBLIC` fields from the current nine-field `LISTING_OFFER` plus minimal attribution/disclosure metadata required by accepted presentation policy:

```text
asking_price_mode
asking_price_amount (lossless decimal/string; never binary float)
currency
location_country
location_region assertion/value when present
broker_summary assertion/value when present
broker_description
known_history_narrative assertion/value when present
vat_tax_status_claim assertion/value when present
```

Omission remains distinct from explicit `UNKNOWN`, `NOT_APPLICABLE` and `NO_KNOWN_HISTORY_DECLARED`; do not flatten to empty string/boolean.

Do not expose creator Account identity, full revision history, internal hashes/transaction metadata, inferred PhysicalBoat facts, BoatDesign baseline-as-yacht-facts, search/ranking scores or verification booleans that do not exist.

### 6.4 VAT/tax presentation

`listing_offer.vat_tax_status_claim` is `PUBLIC + SENSITIVE + DISPLAY_ONLY`. If present, API/page wording MUST preserve qualification, attribution, recorded/last-confirmed time and verification status, equivalent to:

```text
VAT/tax status: broker-declared <value>
Publishing organization: <persisted organization attribution>
Broker declaration recorded/last confirmed in HullQ: <revision recorded_at>
HullQ legal verification: none
```

Until a display-name directory exists, exact persisted `MarketplaceOrganizationId` is sufficient attribution for this proof; 0048 MUST NOT invent or persist an unverified organization display name merely for presentation.

Explicit `UNKNOWN` remains unknown with the same attribution/time/verification-none disclosure. Never render `VAT paid ✓`, `verified VAT`, `HullQ verified` or equivalent without a later accepted verification capability.

### 6.5 Untrusted broker text / XSS boundary

All broker/operator-controlled strings are untrusted presentation data, including broker description, summary, location-region value, known-history narrative, broker listing reference and any future text accidentally carried into this preview.

FastAPI returns them as data only. Astro MUST render them through normal escaped text interpolation. Raw-HTML mechanisms such as Astro `set:html`, DOM `innerHTML` or equivalent are forbidden for these fields in 0048.

A value such as:

```text
<script>alert('x')</script>
```

MUST appear only as escaped/inert text if displayed; it must never create executable markup. Do not solve this by silently mutating the durable broker text. Escaping is a presentation responsibility.

## 7. Astro browser surface

0048 introduces one bounded Astro + TypeScript web package. React is not justified for this page and SHOULD NOT be added without a material amendment.

Use an SSR preview route equivalent to:

```text
/_preview/listings/{preview_token}
```

Astro obtains listing data through FastAPI only. It MUST NOT connect directly to PostgreSQL or reimplement Python domain rules.

The page visibly renders:

- `HullQ listing preview` / `Preview — not a published listing`;
- asking price or `Price on application`;
- country and region assertion where available;
- broker summary when value-asserted;
- broker description;
- known-history semantics without turning `NO_KNOWN_HISTORY_DECLARED` into proof no event occurred;
- qualified VAT/tax disclosure when present;
- preview expiry/status notice.

No media, polished design system, filters, lead form or yacht technical-spec cards are required.

This preview does not freeze final multilingual canonical URL grammar. Final production public listing pages remain subject to the accepted language/SEO architecture.

## 8. Configuration

Use environment configuration only. One documented source of truth may include:

```text
HULLQ_DATABASE_URL
HULLQ_PREVIEW_SIGNING_SECRET   # strict base64url, >=32 decoded random bytes
HULLQ_API_BASE_URL
HULLQ_PREVIEW_BASE_URL
```

Missing/invalid DB URL or signing secret fails fast; no insecure fallback.

## 9. Dependencies / package boundaries

Python:

- add FastAPI;
- add minimal ASGI runtime needed for local proof, e.g. Uvicorn;
- no ORM or alternate persistence framework.

Web:

- one Astro + TypeScript package;
- minimal Node adapter needed for SSR/local preview;
- package lockfile committed;
- no React unless a concrete amendment is accepted.

Existing `uv.lock` remains reproducible.

No Alembic migration is expected: preview capability is stateless and existing marketplace tables are sufficient. A migration requires a material amendment explaining why this vertical cannot complete without it.

## 10. Owner-visible end-to-end proof

A unit-only response model is insufficient. Add a retained inspection path using real PostgreSQL 18 and real local HTTP:

1. Alembic to single current head;
2. create/ensure PhysicalBoat (prefer `BoatDesignRef = NONE` unless real canonical fixture needed);
3. operator intake with explicit eligible 0041 principal;
4. prove durable PhysicalBoat / MarketEpisode / NativeListing / current offer head;
5. generate finite signed preview capability;
6. serve FastAPI with token-safe logging;
7. serve Astro SSR with token-safe logging;
8. fetch preview page over HTTP;
9. assert success and visible persisted content;
10. assert `noindex`, `no-store`, `no-referrer` protections;
11. assert tampered token reveals no listing;
12. assert a malicious HTML-like broker value remains inert/escaped;
13. assert captured ordinary API/web/application logs contain neither preview token nor signing secret;
14. end:

```text
FIRST VISIBLE LISTING PREVIEW RESULT -> PASS
```

Loopback/local HTTP is sufficient. Production VPS/Cloudflare deployment is not required for 0048 acceptance.

## 11. Testing requirements

### Intake

Cover happy path; exact idempotent retry; PhysicalBoat conflict; missing BoatDesign; MarketEpisode conflict/missing PhysicalBoat; denied publisher; NativeListing collision; different existing offer head under first-revision-only intake; retry after partial durable progress; no token emitted on failure.

### Token/security

Cover valid round-trip; expiry; max TTL; tamper; malformed token; wrong secret; invalid base64url secret; decoded secret shorter than 32 bytes; constant-time comparison path; token/secret absent from ordinary app/access logs; `Cache-Control: private, no-store`; `Referrer-Policy: no-referrer`; robots protections; no third-party preview subresources.

### API/read model

Cover explicit current-head use; invalid/expired/nonexistent/incomplete all externally not-found-equivalent; unresolved listing not previewable; no current offer not previewable; decimal lossless/no float; omission/assertion distinctions; conservative history language; required VAT qualification/attribution/time/verification-none; no internal metadata exposure.

### Web

Cover Astro check/build; valid SSR preview content from FastAPI; visible preview-only status; conservative VAT/history wording; noindex/nofollow/noarchive; no-store/no-referrer behavior; invalid preview 404/not-found; no direct DB access; token-safe web logs; malicious HTML/script-like text rendered escaped/inert with no raw-HTML mechanism used for broker fields.

## 12. CI / reproducibility

All existing Python quality, PostgreSQL 18 full-suite coverage, historical replay and manufacturer-reproducibility gates remain mandatory and MUST NOT be weakened.

Add deterministic web gates equivalent to:

```text
pinned/supported Node
npm ci (or accepted locked equivalent)
Astro/type check
web build
bounded web tests/smoke
```

Do not reduce the existing Python 90% coverage threshold.

At least one canonical Linux/PostgreSQL job MUST execute the real HTTP vertical proof if deterministic. Cross-platform Python quality and deterministic web build remain required separately.

## 13. Explicit out of scope

Not authorized: production publication/lifecycle; publish/unpublish/withdraw/sold workflow; Auth0/session implementation; persisted Account/Organization/Membership directory; broker browser workspace/form; media; PhysicalBoat marketplace facts; leads; public search/list/ranking; saved searches/alerts; price history; canonical SEO listing URL grammar; sitemap; final multilingual production routing; external feeds; dedup/merge; LLM extraction; deployment/VPS/Cloudflare/DNS automation; mobile app.

## 14. Expected touch points

Likely smallest coherent set:

- `pyproject.toml`, `uv.lock`;
- FastAPI/application modules under `src/hullq/`;
- operator intake/inspection under `scripts/` and/or `src/hullq/application/`;
- tests under `tests/`;
- bounded `web/` Astro package + lockfile/config/page;
- `.github/workflows/ci.yml` only for deterministic web gates/vertical proof;
- this slice document for handoff status/evidence.

## 15. Acceptance criteria

Accept only if all are true on exact final PR HEAD:

1. operator command creates/reuses durable chain through first offer head without bypassing 0041;
2. retries safe; conflicts/failures stop fail-closed;
3. no fake aggregate rollback claim;
4. only valid finite signed bearer capability exposes preview;
5. persisted NativeListing existence alone does not create anonymous readability;
6. signing secret is strict base64url >=32 decoded random bytes with no fallback;
7. token/secret do not appear in ordinary API/web/application logs;
8. token-bearing responses are no-store/no-referrer/noindex and preview has no third-party telemetry/subresources;
9. FastAPI is sole backend and routes remain thin;
10. preview read uses explicit current offer head;
11. only accepted public offer fields + required sensitive disclosure render;
12. money is lossless decimal/string, never binary float;
13. omission/assertion distinctions remain intact;
14. VAT is broker-attributed and explicitly unverified by HullQ;
15. all broker/operator-controlled text is rendered escaped/inert, never as raw HTML;
16. Astro SSR reads through FastAPI only;
17. real HTTP/browser preview visibly renders persisted listing;
18. preview is clearly not published and mechanically non-indexable;
19. stable API/canonical URL/i18n/publication semantics are not silently frozen;
20. dependencies are locked/reproducible; no unjustified migration;
21. existing Python CI/coverage/replay/manufacturer gates remain intact;
22. deterministic web gates are green;
23. retained inspection ends `FIRST VISIBLE LISTING PREVIEW RESULT -> PASS`;
24. exact-head independent review has no material finding;
25. explicit Project Owner acceptance occurs before merge.

## 16. Handoff rule

Claude Code may implement only this slice after `START_SLICE 0048` creates the isolated worktree/branch.

At handoff it MUST set `**Status:** REVIEW` and provide the standard completion report with exact branch HEAD, validation, remote CI/manufacturer status and unresolved findings.

It MUST NOT mark DONE, merge its own PR or start SLICE-0049.
