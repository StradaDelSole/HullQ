# SLICE-0058 — Anonymous Local Shortlist

**ID:** SLICE-0058  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Buyer Decision Tools — anonymous explicit-interest continuity  
**Depends on:** SLICE-0057 owner-accepted / acceptance-closed; accepted public listing read/freshness boundary; accepted Direct Search public browser surface  
**Blocks:** later factual Compare and later account-backed shortlist continuity only; no later slice is automatically authorized

## Objective

Deliver exactly one public buyer capability:

> An anonymous buyer can explicitly add/remove a current NativeListing to one browser-local shortlist and revisit that shortlist; the browser persists only stable NativeListingIds, while current listing truth is re-resolved from the accepted public FastAPI listing-read boundary.

No account, database shortlist, recommendation, Compare, sharing, monitoring, contact/lead flow or new Search criterion is introduced.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: explicit anonymous browser-local shortlist membership plus its one viewing surface.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can add a listing from Search or the public listing page, open `/{locale}/shortlist`, see the current listing or neutral unavailable state, remove it, refresh/reopen the browser surface and observe local continuity without an account.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The slice creates a direct buyer action after technical discovery, preserves strict current-listing truth, keeps discovery open before signup and avoids premature server persistence/monetization. It is not generic infrastructure.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical accepted buyer direction, marketplace identity/public-read/freshness implementation, Search/web surfaces, owner-direct direction, broker obligations and trigger gates were inspected. Shortlist direction is accepted-but-unimplemented; broader persistence semantics remain deferred/open rather than silently invented.

**TRIGGER GATES CHECK:** PASS  
Production Readiness is `NOT_TRIGGERED`; workflow reassessment is `PASS`; 0058 adds no technical Search criterion and no real external production data/pilot/launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/PRODUCT_SCOPE.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; SLICE-0049/0050/0052/0056/0057 acceptance closures; `docs/POST_SLICE_0057_REASSESSMENT_2026-09-19.md`.

**Production implementation checked:** `src/hullq/application/public_listing_read.py`; `src/hullq/api/app.py`; `web/src/pages/listings/[native_listing_id].astro`; `web/src/lib/publicListingApi.ts`; `web/src/components/SearchPageBody.astro`; `web/src/lib/searchApi.ts`; current public-listing/Search/freshness tests and retained vertical proofs.

**Already implemented / not re-decided:** stable NativeListing identity; public listing ACTIVE+complete+freshness current-read boundary; non-enumerating unavailable public behavior; public Search listing IDs; FastAPI application/domain ownership; anonymous Direct Search; no score/winner recommendation semantics; SLICE-0057 sensitivity; organic commercial independence.

**Exact remaining gap:** no buyer-visible mechanism currently lets an anonymous buyer explicitly retain interest in selected NativeListings across ordinary page navigation/revisit without account persistence.

**Accepted-but-unimplemented obligations:** one ordinary personal Shortlist; buyer-authored membership only; Shortlist distinct from Search/BuyerRequirements; anonymous/local behavior where practical; later persistent/account continuity separately.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` current listing/Search truth and identities; `DECIDED_NOT_YET_IMPLEMENTED` anonymous personal Shortlist; `EXPLICITLY_DEFERRED` Compare/sharing/notes/monitoring/account persistence/multiple lists; `GENUINELY_OPEN` durable Shortlist identity/account migration/entitlement limits beyond this local v0.1; no `CONFLICT_OR_REGRESSION` found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

HullQ can now help a buyer discover confirmed current listings and inspect one-change Search sensitivity, but the buyer cannot yet perform the next basic agency-preserving action: explicitly retain interest in a concrete listing.

The accepted buyer product direction already defines Shortlist as buyer interest, not HullQ fit, and explicitly anticipates anonymous/local behavior before account continuity.

0058 implements only that accepted minimum. It deliberately avoids settling server persistence, account limits, migration, Compare or monitoring.

## Controlling artifacts

- Requirement IDs: accepted product direction in `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; existing `REQ-PROD-005` remains relevant only to later persistent query/monitor work, not local shortlist membership.
- Specifications: `specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`; `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_FRESHNESS_REQUIREMENTS.v0.1.md`.
- Accepted ADRs: current Astro/FastAPI architecture rebaseline.
- Governance / research protocols: `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`
- Current owner-direct/private-seller direction: `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`
- Current owner-direct/private-seller requirements: `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`
- Native listing market decision: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`
- Relevant open questions: durable Shortlist identity/persistence/account limits/migration remain later work and are not solved by this browser-local slice.

## In scope

- one versioned browser-local shortlist;
- stable `NativeListingId` membership only;
- explicit idempotent add/remove;
- add/remove affordance on localized Search confirmed results;
- add/remove affordance on the existing public listing page without redesigning listing URL localization;
- localized `/{locale}/shortlist` pages for `en/de/fr/pt/es`;
- empty, available and neutral unavailable states;
- current public listing truth re-resolution;
- deterministic buyer-authored/insertion order;
- safe handling of malformed/tampered/oversized local storage;
- noindex/personalized SEO boundary;
- retained built-web proof and CI coverage.

## Explicitly out of scope

- authenticated/database Shortlist;
- cross-device sync;
- anonymous-to-account migration;
- multiple/named lists;
- paid/free shortlist limits;
- Compare;
- private notes;
- sharing;
- BuyerRequirements application to shortlist;
- Saved Search/Monitor/alerts;
- background checks/notifications;
- seller/broker contact or lead creation;
- telemetry-based preference inference;
- recommendation/ranking;
- third Search criterion;
- owner-direct publication/admission;
- Broker Workspace expansion;
- public-listing localization redesign.

## Required behavior

### A. Explicit membership only

Only explicit buyer add/remove changes membership.

No Search, Requirement Sensitivity, freshness or fit state may mutate membership automatically.

### B. ID-only local persistence

Browser persistence stores only versioned shortlist structure and stable NativeListingId strings.

No listing truth is cached as authoritative shortlist state.

### C. Idempotent deterministic local store

Add existing/remove missing are no-ops. Duplicate IDs normalize safely. Buyer-authored insertion order remains stable.

Malformed/wrong-version/unsafe storage must not crash or inject HTML.

### D. Current truth re-resolution

Opening the shortlist resolves current public listing data from FastAPI/application truth.

Do not copy lifecycle/freshness logic into TypeScript.

### E. Preserve unavailable non-enumeration

All non-public/non-current causes remain one neutral unavailable state.

Do not expose DRAFT vs WITHDRAWN vs STALE vs missing distinctions.

### F. Unavailable does not erase interest

An unavailable saved ID remains in local membership until explicit buyer removal.

No automatic cleanup.

### G. Service failure is not listing truth

Transport/database/API outage must not be presented as all listings unavailable or an empty shortlist. The user gets a bounded service-error/retry state while local membership remains unchanged.

### H. No ranking

Render buyer-authored order. Do not sort by inferred fit, seller type, payment, price desirability or revenue.

### I. Localized public interaction

`/{locale}/shortlist` exists for all five accepted public locales and is `noindex`.

Localized Search results expose equivalent add/remove semantics.

The existing nonlocalized listing page may use its existing language convention; no public listing URL/i18n redesign is authorized.

### J. No account/server persistence

No migration or buyer table is introduced.

A resolver request may necessarily carry saved IDs, but the server does not store them as buyer-interest state.

### K. Safe bounded transport

If a new batch/proxy resolver is used, it is read-only, bounded, validates untrusted IDs and delegates each listing to the accepted public listing read model.

A per-ID reuse of the current API is acceptable if browser topology/performance and error distinction are proven.

### L. Commercial independence

Payment/referral/verification economics do not affect membership/order or current listing truth.

## Deliverables

1. versioned browser-local shortlist store module with focused tests;
2. add/remove controls on Search results;
3. add/remove control on public listing page;
4. five locale shortlist pages;
5. current-listing resolution transport reusing accepted public listing truth;
6. neutral unavailable and service-error handling;
7. localized shortlist copy for five locales;
8. retained browser-faithful built Astro + FastAPI/PostgreSQL proof;
9. CI execution of retained proof;
10. primary slice document handoff to `REVIEW` only after implementation validation.

## Acceptance criteria

- [ ] Anonymous buyer can add a Search-result listing to the shortlist. (button renders correctly with the identical mechanism verified on the listing page and via `addToShortlist`; not exercised by an actual browser click against a live Search confirmed-match fixture -- no browser-automation tool is available in this repository. See Findings.)
- [ ] Anonymous buyer can add the public listing page's NativeListingId. (button rendering verified live via the retained proof; `addToShortlist` itself verified via the Node store harness; the click interaction itself was not driven by a real browser. See Findings.)
- [x] Add existing ID is idempotent.
- [x] Remove saved ID works and remove absent ID is idempotent.
- [ ] Refresh/revisit preserves membership in the same browser storage. (storage get/set round-trip verified by unit tests and the store harness; an actual browser reload was not performed.)
- [x] Local persistence contains NativeListingIds/version metadata only, no listing truth payload.
- [x] Buyer-authored/insertion order is stable.
- [ ] Search/Requirement Sensitivity changes never auto-mutate shortlist membership. (structurally true by construction -- no Search/Sensitivity code path references the shortlist store -- but not exercised by a live combined scenario.)
- [ ] All five locale Search surfaces expose equivalent shortlist controls. (identical shared `SearchPageBody.astro` markup verified by `astro check`/build for all five locale pages; not exercised against a live confirmed-match fixture. See Findings.)
- [ ] All five `/{locale}/shortlist` pages render empty/current/unavailable states. (all five pages verified live: 200, `noindex`, `private, no-store`; the client-rendered empty/current/unavailable states themselves were not observed under real browser JS execution.)
- [x] Shortlist re-resolves current listing truth through the accepted FastAPI public listing read semantics.
- [x] DRAFT/WITHDRAWN/missing/incomplete/STALE/freshness-UNKNOWN saved IDs are not distinguishable in the shortlist UI. (proof: WITHDRAWN and never-created ids resolve to the byte-identical `{"state":"unavailable"}` shape.)
- [x] Unavailable saved IDs remain stored until explicit buyer removal.
- [x] An upstream resolver/API failure is not rendered as normal unavailable or empty truth.
- [x] Malformed/wrong-version/non-string/duplicate/oversized local data is handled safely.
- [ ] No unsafe HTML injection from local storage is possible. (structurally guaranteed: all shortlist DOM code uses `textContent`/`createElement` only, never `innerHTML`/`set:html`, verified by code inspection; not probed with a live XSS payload under a real browser.)
- [x] Shortlist order is not fit/revenue/payment ranking.
- [x] `/{locale}/shortlist` is noindex and saved IDs never appear in URL/canonical metadata.
- [x] No account is required.
- [x] No shortlist/BuyerRequirements/Saved Search/Monitor persistence row is written.
- [x] No Compare/sharing/notes/alerts/contact/recommendation capability is introduced.
- [x] Ordinary Search, Sensitivity and public listing truth remain unchanged.
- [x] Retained proof ends with `ANONYMOUS LOCAL SHORTLIST RESULT -> PASS`.
- [x] Repository validation, lint, type-check, Python tests, web tests/check/build all pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if an equivalent smaller implementation is proved:

- `web/src/lib/shortlistStore.ts` (new);
- `web/src/lib/__tests__/shortlistStore.test.ts` (new);
- `web/src/lib/shortlistText.ts` or equivalent localized copy;
- `web/src/components/SearchPageBody.astro`;
- `web/src/pages/listings/[native_listing_id].astro`;
- `web/src/pages/{en,de,fr,pt,es}/shortlist.astro`;
- a bounded shortlist current-read client/proxy module if needed;
- `src/hullq/api/app.py` only if a bounded batch current-read endpoint is the smallest safe transport;
- focused FastAPI tests only if such endpoint is added;
- retained shortlist proof script or bounded extension of an existing real HTTP proof;
- `.github/workflows/ci.yml` only if needed to wire the proof.

No Alembic migration is expected.

No React dependency is expected or required; a small client-side TypeScript/browser script is sufficient unless implementation proves otherwise.

## Validation

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python -m pytest
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
```

Run/report the exact retained shortlist vertical-proof command selected by implementation.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation requires server/database-backed shortlist persistence;
- authenticated account semantics or anonymous-to-account migration become necessary;
- current listing truth cannot be reused without duplicating lifecycle/freshness logic in web code;
- unavailable IDs would need internal lifecycle/status disclosure;
- the browser must persist current price/offer/claim/freshness truth to make the capability work;
- a resolver cannot distinguish infrastructure failure from normal listing unavailability;
- implementation starts ranking/recommending/inferencing fit;
- Search or Requirement Sensitivity begins auto-mutating shortlist membership;
- scope expands into Compare, sharing, notes, monitoring/alerts, contact/leads or another deferred capability;
- a production-data/pilot/launch trigger changes;
- accepted source-rights/provenance/identity/owner-direct/commercial-independence boundaries would be weakened.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED` with the matching explicit handoff line, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0059.
