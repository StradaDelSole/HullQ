# SLICE-0059 — Anonymous Factual Shortlist Compare

**ID:** SLICE-0059  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Buyer Decision Tools — factual shortlist comparison  
**Depends on:** SLICE-0058 owner-accepted / acceptance-closed; accepted public listing/current-truth boundary  
**Blocks:** later BuyerRequirements overlay, explicit compare-subset selection, sharing and downstream monitor/contact work only; no later slice is automatically authorized

## Objective

Deliver exactly one public buyer capability:

> An anonymous buyer can compare the whole current browser-local Shortlist on one localized factual surface using freshly re-resolved current public listing and concrete PhysicalBoat claim data, without scoring, recommending, persisting another compare set or requiring an account.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: factual anonymous comparison of the existing local Shortlist.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can save at least two listings, open `/{locale}/shortlist/compare`, inspect aligned current factual yacht/listing fields and neutral unavailable/service-error states, and confirm that Compare does not change shortlist membership.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Compare is an accepted Buyer Decision Tool and the next consumer explicitly deferred until Shortlist existed. The slice advances the serious-buyer loop after 0058 without forcing account/persistence/monitoring/contact semantics and preserves truth-safe non-recommendation behavior.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical post-0054 buyer/seller direction, accepted 0058 closure/contract, public listing read model, shortlist resolver/store/runtime, UX baseline, broker/owner-direct obligations, architecture and trigger gates were inspected. Existing 0058 identity/current-truth transport is reused rather than duplicated.

**TRIGGER GATES CHECK:** PASS  
Production Readiness remains `NOT_TRIGGERED`; workflow reassessment remains `PASS`; 0059 adds no technical Search criterion and no real external production data/pilot/launch. The stale broker-only architecture summary found during reassessment is corrected in this readiness package before READY acceptance.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0058_REASSESSMENT_2026-09-19.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/PRODUCT_UX_PRINCIPLES.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; SLICE-0058 acceptance closure/contract; current architecture baseline/rebaseline.

**Production implementation checked:** `src/hullq/application/public_listing_read.py`; `web/src/lib/publicListingApi.ts`; `web/src/lib/shortlistStore.ts`; `web/src/lib/shortlistResolutionApi.ts`; `web/src/lib/shortlistPageRuntime.ts`; `web/src/components/ShortlistPageBody.astro`; `web/src/pages/api/shortlist/resolve.ts`; existing shortlist/public-listing tests and retained proof.

**Already implemented / not re-decided:** browser-local NativeListingId-only Shortlist; explicit buyer membership; insertion order; current truth re-resolution; available/unavailable/service-error distinction; public current offer + bounded concrete PhysicalBoat claim projection; UNKNOWN/not-supplied claim semantics; no BoatDesign fallback as concrete truth; no score/winner/recommendation; FastAPI truth boundary; noindex/private personalized Shortlist.

**Exact remaining gap:** HullQ has no buyer-visible factual side-by-side view of the already explicitly shortlisted current listings.

**Accepted-but-unimplemented obligations:** accepted Compare direction allows shortlisted boats to be compared factually using technical/listing/truth data while forbidding winner/overall score/best-fit/hidden weighting; 0059 implements only the anonymous whole-Shortlist factual subset.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` shortlist/current public truth foundation; `DECIDED_NOT_YET_IMPLEMENTED` factual Compare; `EXPLICITLY_DEFERRED` persistence/subset-selection/requirements overlay/sharing/monitor/contact; `GENUINELY_OPEN` later durable compare-selection/account/currency-market semantics; `CONFLICT_OR_REGRESSION` stale broker-only one-sentence architecture corrected by this readiness package.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

0058 deliberately established explicit buyer-selected membership before Compare.

The accepted product direction already says Compare is useful independently of guided Requirements and may compare shortlisted boats using factual technical/listing/truth data. The 0058 implementation now provides the exact stable IDs, current resolver and public concrete-yacht facts required to deliver that value without new domain truth.

Choosing account persistence, monitoring or contact first would force broader open decisions. Choosing another Search criterion would add breadth rather than closing the next buyer decision-tool gap.

## Controlling artifacts

- Requirement IDs: accepted Compare/Shortlist direction in `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; no new Broker/Owner-Direct requirement is claimed implemented.
- Specifications: `specs/ANONYMOUS_FACTUAL_SHORTLIST_COMPARE_CONTRACT.v0.1.md`; `specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_FRESHNESS_REQUIREMENTS.v0.1.md`.
- Accepted ADRs: current Astro/FastAPI application architecture and accepted public listing/Search boundaries.
- Governance / research protocols: `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`.
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`
- Current owner-direct/private-seller direction: `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`
- Current owner-direct/private-seller requirements: `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`
- Native listing market decision: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`
- Pre-Gate-1 execution amendment: `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`
- Relevant open questions: future explicit compare-subset state, BuyerRequirements overlay, durable/account Shortlist migration/limits, sharing, currency/market comparison semantics remain deferred/open.

## In scope

- one localized anonymous factual Compare surface for `en/de/fr/pt/es`;
- compare set equals current local Shortlist membership;
- zero/one/two-plus saved-item states;
- buyer-authored Shortlist order preserved;
- current public truth re-resolution through accepted shortlist resolver;
- factual current offer and bounded concrete PhysicalBoat claim matrix/cards;
- explicit UNKNOWN/not-supplied/unavailable/service-error distinctions;
- original-currency price/POA display only;
- navigation to available listing pages and back to Shortlist;
- Compare navigation/action from the Shortlist surface;
- safe DOM/text rendering;
- noindex/private-no-store personalized SEO boundary;
- retained built-web proof and CI coverage.

## Explicitly out of scope

- new compare-selection storage/key;
- subset selection/pinning/reordering independent of Shortlist;
- account/database Compare or Shortlist persistence;
- anonymous-to-account migration;
- BuyerRequirements evaluation layer;
- scoring, winner, best-fit or recommendation;
- better/worse difference judgments;
- currency conversion/normalization;
- derived market-value/performance metrics;
- private notes;
- sharing;
- Saved Search/monitoring/alerts;
- seller/broker contact/leads;
- telemetry/preference inference;
- third Search criterion;
- owner-direct publication/admission;
- Broker Workspace expansion.

## Required behavior

### A. Compare set is the existing Shortlist

Read the accepted local Shortlist IDs and compare that exact set in buyer-authored order.

Compare MUST NOT add/remove/reorder Shortlist membership.

No second compare-selection persistence object is introduced.

### B. Zero / one / two-plus state

Zero IDs: factual empty Compare state.

One ID: factual need-at-least-one-more state.

Two or more IDs: resolve/render the compare set.

### C. Current truth

Use the existing accepted shortlist/public-listing current-read transport.

Never use browser-stored listing facts as current truth and never duplicate lifecycle/freshness logic in Astro/TypeScript.

### D. Factual matrix

Align at least current identity, asking price/currency or POA, location, build year, LOA, draft, keel configuration, rudder configuration and freshness/last-confirmed disclosure where current public data supports them.

### E. Claim semantics

Preserve VALUE_ASSERTION vs explicit UNKNOWN vs omitted/not supplied.

Never fill a concrete-yacht gap from BoatDesign baseline truth.

### F. Unavailable and service failure

Neutral unavailable remains non-enumerating and saved.

Service error remains distinct.

One unavailable/error item does not suppress other current resolved entries.

### G. Decision neutrality

No winner, score, best-fit, recommended, better/worse field judgment, hidden weight or inferred preference ordering.

Do not normalize currencies or present cheapest/best-value semantics.

### H. Localized personalized surface

`/{locale}/shortlist/compare` exists for all five public locales, remains `noindex` and `private, no-store`, and contains no saved IDs in URL/query/canonical metadata.

### I. Safe browser rendering

Stored IDs and returned text are untrusted presentation input. Use safe DOM/text APIs only.

### J. No new persistence or telemetry

No Compare row/table/account association, new cookie/server intent object, analytics or behavioral-preference state.

## Deliverables

1. localized Compare page/shell for five locales;
2. Compare runtime/rendering reusing local shortlist + existing resolution transport;
3. localized Compare copy;
4. Shortlist navigation/action into Compare;
5. focused web tests for compare-set/state/truth-safe rendering semantics;
6. retained built Astro + FastAPI/PostgreSQL proof ending with the required 0059 marker;
7. CI execution of retained proof;
8. primary slice handoff to `REVIEW` only after implementation validation.

## Acceptance criteria

- [ ] Zero saved IDs render a bounded Compare empty state.
- [ ] One saved ID renders a bounded need-one-more state.
- [ ] Two or more saved IDs render one comparison set in buyer-authored Shortlist order.
- [ ] Opening/using Compare does not mutate Shortlist membership or create a second compare-selection store.
- [ ] Current available facts are re-resolved through the accepted existing shortlist/public listing read transport.
- [ ] Later current offer/claim changes are reflected without rewriting local shortlist payload.
- [ ] Available entries expose current factual identity, price/POA, location and bounded concrete PhysicalBoat comparison fields.
- [ ] VALUE_ASSERTION, explicit UNKNOWN and omitted/not-supplied concrete claim states remain distinguishable.
- [ ] BoatDesign baseline truth is never used to fill a missing concrete PhysicalBoat comparison cell.
- [ ] Unavailable saved IDs use one neutral non-enumerating state and remain saved.
- [ ] Service failure remains distinct from ordinary unavailable.
- [ ] One unavailable/service-error item does not hide other available compared entries.
- [ ] No currency conversion, price desirability, winner, best-fit, recommendation, score or hidden weighting is introduced.
- [ ] All five `/{locale}/shortlist/compare` routes exist and use equivalent factual semantics.
- [ ] Compare is reachable from the Shortlist surface.
- [ ] Compare pages are `noindex` and `private, no-store`.
- [ ] Saved IDs never appear in URL/query/canonical metadata.
- [ ] No unsafe HTML injection from local storage/resolved public text is possible.
- [ ] No account/database Compare persistence, buyer profile, telemetry or preference-inference state is created.
- [ ] Ordinary Shortlist, Search, Sensitivity and public listing truth remain unchanged.
- [ ] Retained proof ends with `ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> PASS`.
- [ ] Repository validation, lint, type-check, Python tests, web tests/check/build all pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if an equivalent smaller implementation is proved:

- `web/src/components/ShortlistPageBody.astro`;
- `web/src/components/ShortlistComparePageBody.astro` or equivalent;
- `web/src/lib/shortlistCompareRuntime.ts`;
- `web/src/lib/shortlistCompareText.ts` or bounded extension of current shortlist copy;
- `web/src/lib/__tests__/...` focused Compare tests;
- `web/src/pages/{en,de,fr,pt,es}/shortlist/compare.astro`;
- existing `web/src/lib/shortlistStore.ts`, `shortlistResolutionApi.ts`, `publicListingApi.ts` reused rather than semantically duplicated;
- existing claim/price presentation helpers reused where safe;
- retained proof script (new or bounded extension of the current shortlist proof);
- `.github/workflows/ci.yml` only if needed to wire a new retained proof command.

No Alembic migration is expected.

No FastAPI/domain change is expected unless implementation proves a current transport deficiency; any proposed backend change must remain read-only and reuse the same accepted `PublicListingReadModel`.

React is not expected unless the comparison interaction demonstrably requires an island; Astro + small TypeScript remains preferred for this bounded v0.1.

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

Run/report the exact retained 0059 Compare vertical-proof command selected by implementation.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation requires account/database-backed Shortlist or Compare persistence;
- a separate compare-selection state becomes necessary to make the slice useful;
- current public listing truth cannot be reused without duplicating lifecycle/freshness logic;
- Compare requires BoatDesign facts to masquerade as concrete-yacht facts;
- a current public claim/value lacks enough semantics to distinguish UNKNOWN from omission safely;
- unavailable IDs would require internal lifecycle/status disclosure;
- backend failure would be collapsed into ordinary unavailable/empty truth;
- implementation starts evaluating BuyerRequirements, ranking, scoring or recommending boats;
- implementation requires currency conversion/market valuation methodology;
- scope expands into sharing, notes, monitoring/alerts, contact/leads or another deferred capability;
- a production-data/pilot/launch trigger changes;
- accepted source-rights/provenance/identity/owner-direct/commercial-independence boundaries would be weakened.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED` with the matching explicit handoff line, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0060.
