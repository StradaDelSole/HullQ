# HullQ — Post-SLICE-0095 Search Foundation and M1a Buyer Workflow Reassessment

**Date:** 2026-10-29 (Europe/Vienna)  
**Status:** PROPOSED — docs-only reassessment for independent review and explicit Owner capability selection; **NOT READY / NOT SELECTED**  
**Source-of-truth baseline:** canonical `main` `e28b2b7a998694131164d51519fef198b5c3ca3c` (Owner-accepted SLICE-0095 plus reviewed docs-only #401 and #402).  
**Current execution queue:** SLICE-0096 is **NOT SELECTED / NOT READY**. This document is not a numbered slice, implementation prompt or release gate.

## 1. Source reconciliation and mandate

Owner-directed next sequence after the 2026-10-29 post-0095 local visual walkthrough and Claude overall review:

1. **Measured, scalable Search foundation**: first-page/result retrieval safety, performance/SQL shape, realistic synthetic Sail+Power inventory; no speculative replacement architecture.
2. **M1a usable Buyer Search workflow**: useful basic selection, result cards with genuine listing facts, navigation, pagination, clear evidence and a browser-visible buyer journey for Sail and Power.
3. **Progressive Sail / Power / equipment technical depth** against the *314-item candidate longlist* discussed in the Owner checkpoint, subject to real field definitions, usefulness and source rights. **314 is a proposed planning inventory, not 314 accepted/implemented Search criteria, nor an exact repo-verified file.** Do not invent or authorize missing longlist entries.

This order retains equal Buyer Excellence and Broker Productivity Excellence. The Owner already deferred concrete broker/private-seller tariff, premium-packaging and optional referral-fee choices pending market validation; **do not reopen them as a dependency**. The accepted free truthful core, normal leads, lawful portability, conditional free simple inbound feed and paid advanced time-saving work remain controlling: `docs/HULLQ_OWNER_DECISION_BROKER_PRODUCTIVITY_EXCELLENCE_2026-10-29.md`, #400.

**Specific accepted records reconciled:** `docs/PROJECT_STATE.md`; `docs/PRODUCT_EXECUTION_PLAN.md` (one capability, visible result, risk-based sizing); `docs/PRODUCT_UX_PRINCIPLES.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`; accepted 0091/0093/0094/0095 closures, joint Sail+Power decision #366, source/parity #372, critical search/intake runtime gate #355, post-0095 checkpoint #397.

## 2. What current production code actually does

**Search candidate discovery (confirmed code):** `src/hullq/persistence/inventory_search.py` defines two disjoint `ACTIVE` candidate enumerations, one with `pb.boat_design_ref IS NOT NULL`, one with `IS NULL`. Each `SELECT ... ORDER BY nl.native_listing_id` has **no SQL `LIMIT` / `OFFSET` or cursor** and loads all fetched rows. D29 eligibility and detailed technical/evidence evaluation happen in downstream application logic. This is a **verified unbounded enumeration risk**, not evidence of a particular hosted response time.

**Already existing real-PG synthetic performance evidence:** accepted `docs/slices/SLICE-0093-acceptance-closure.md` reports Power claim-only 0/40/200 synthetic candidates at **2/169/809 SQL statements** and 0/10 design-linked at **2/98**. `tests/persistence/test_power_engine_count_performance_slice_0094.py` retains 0/40/200 mixed Sail+Power populations, three fixed qualified design-linked candidates, count-only/drive-only/combined comparisons and a separate 0/10 design-linked stress case; `tests/persistence/test_power_inventory_query_performance_slice_0093.py` is a predecessor. These are **retained reported/tested prior slices**; no new test was executed in this docs-only reassessment. The accepted closure expressly keeps hosted/production-scale Search #355 OPEN. Do not extrapolate milliseconds as measured server latency.

**Existing core to preserve, not rebuild:** nine Sail + two Power accepted hard Search criteria; typed per-domain `CriterionDefinition`; shared MUST/AND and FieldResolution/configuration-aware design truth; current immutable PhysicalBoat/publisher claim truth and other-Organization conflict guard; D29 public admission and freshness; five-locale browser routes; privacy-safe source/evidence labels; anonymous shortlist and compare; broker Sail/Power private draft Search-fit. Current accepted search-count marker **11** is unchanged.

**Visible Buyer gap (confirmed Astro):** `web/src/components/SearchPageBody.astro` and `web/src/components/PowerSearchPageBody.astro` provide direct technical forms, source evidence and listing links, but current results are chiefly bare `native_listing_id` labels, not complete scannable cards with buyer facts (title, price, build year, location, cover image, dimensions). Both surfaces lack a coherent general price/year/location/manufacturer basic browse/filter and result pagination. Verify the actual available authoritative offer/media/location fields and D29 permissions before designing presentation/DTOs; do not fill empty fields with invented values.

**Motorsegler direction (accepted but NOT implemented):** the Owner-accepted docs-only #402 policy assigns source-qualified `MOTORSAILER` to the public Sail family/subtype, not Power; the 0091 conservative technical Sail exclusion still exists in code and tests. Its actual category-admission and broker Search-fit correction remains a separate scoped implementation under #372. Do not silently change category truth while optimizing the Search pipeline.

## 3. Decision / implementation reconciliation (not a READY contract)

- **DECIDED_AND_IMPLEMENTED:** nine Sail/two Power evidence-based technical facets, two active-listing candidate source planes, current deterministic match semantics, D29 eligibility, Broker Search-fit, anonymous shortlist/compare and prior mixed synthetic performance tests.
- **DECIDED_NOT_YET_IMPLEMENTED:** a **measured, safely bounded public Search results service** over both qualified planes, useful first-page/result pagination, buyer-friendly basic listing cards/filter/navigation, complete Power specialist parity, Owner-approved motorsailer Sail-family runtime discovery and broader field coverage.
- **EXPLICITLY_DEFERRED:** concrete broker/private tariffs and optional referral commercial terms pending market validation; vendor/hosted procurement, real external broker/owner production data, pilot and external public release; wholesale declarative field registry rewrite pending design proof and Owner-specific selection.
- **GENUINELY_OPEN:** cheapest correct Search read strategy (batched observations/qualified SQL preselection/indexes, bounded staged scan, projection/read model or combination) and precise measurable nonproduction performance acceptance budgets **based on actual baseline**, not guessed targets. Cross-surface field registry remains an architecture candidate, not accepted.
- **CONFLICT_OR_REGRESSION to avoid:** `LIMIT` **before** evaluating all eligible candidates and then claiming global page exhaustiveness can silently drop true matches; stale positive search projections; multiplying BoatDesign evidence across different named variants or physical-claim revisions; leaking cross-organization evidence; pulling DRAFT/non-D29 listings into public results; collapsing `PUBLISHER_CLAIM` into independent verification; reclassifying motorsailers by marketing names; weakening legacy UNKNOWN compatibility or commercial Search neutrality.

## 4. Proposed next-capability options (NOT selected)

### Option A — recommended first: Measured bounded native Search result retrieval (Sail + Power)

**One observable outcome:** a reproducibly measured, correct, **bounded** first-page technical Search result retrieval path for both categories, over genuine qualifying synthetic ACTIVE/D29-eligible listings, with truthful continuation/end-of-results semantics and matching source evidence. This is a Search safety/product capability, **not** a blanket data-model refactor.

**Before READY/implementation design:** inspect existing 0093/0094 performance fixtures and current API/DTO/SSR result shapes; run a nonproduction baseline with real PG18 and seeded mixed Sail+Power workloads (including design-linked vs unresolved, many nonmatches, no matches, UNKNOWN/conflicts). Record SQL statement counts, `EXPLAIN (ANALYZE, BUFFERS)`, wall latency distribution, app/server CPU or memory where observable, HTTP/SSR latency, request concurrency and cancellations, per-path source classification, deterministic result identities, and D29 admission. Use small and larger populations feasible with verified, qualified fixture costs; 0/40/200 already exist, 1,000+ is a **candidate stress scenario**, not a measured baseline or compulsory 1,000 real FieldResolution constructions. Distinguish locally measured figures from provider-latency hypotheses.

**Engineering acceptance boundary, to be finalized in independently reviewed READY:**
- Never perform an unbounded full-population materialization as the cost of *one public result page*; do not call a simple pre-evaluation SQL `LIMIT` a correct global Search result page.
- Stable deterministic pagination/continuation for both result evidence classes and technical Sail/Power criteria, with no false-negative due to insufficient examined candidates; explicitly handle concurrent withdraw/reconfirm/claim revision and stale tokens with safe, documented semantics (snapshot/version, defensible continuation or restart) rather than asserting an impossible cross-request snapshot.
- Bounded memory/DB work and safe nonproduction concurrency; measurable comparative baseline and acceptance limits selected from evidence, with adversarial safety tests for cancellation, large negative populations and same-configuration/cross-Organization truth. State honestly if remaining hosted target-load proof prevents closing #355.
- Reuse accepted `CriterionDefinition`, existing application evaluators and FieldResolution truth wherever sound; a read projection is **conditional on profiling**, not automatically selected by Claude's architecture suggestion.
- Provide Owner-executable real PG18/FastAPI/built Astro synthetic end-to-end demonstration and readable performance evidence. Any UI in this capability is limited to what is necessary to exercise/verify bounded retrieval; **no broad styling/cards/filter family** hidden in it.
- Retain privacy, current eligibility, source rights, noncommercial ordering, five locales and query canonicalization. Tests compare eligible listing sets and evidence under simple/unbounded reference evaluation vs the proposed bounded path for tractable test corpora; include failure and no-results cases.

**Sizing/selection caution:** This is a proposed single functional risk boundary, **not** an automatic authorization for a giant generic Search refactor. If measured evidence reveals disjoint blocker causes (e.g. only profiling reproducibility first, then a separate runtime performance mechanism), split through the Owner-selected readiness process.

### Option B — next: Buyer M1a basic inventory journey

One visibly usable Sail+Power path: real basic listing fields (price, build year, manufacturer/model when actually sourced, length, location where known, cover where rights-approved), filter/navigation/results presentation and read-only evidence badges linked to detail/shortlist/compare. Apply actual authoritative offer vs Design-vs-PhysicalBoat proof and visible missing values. **Reuse** A's bounded result/continuation semantics. Split into smaller one-capability UI slices if basic browse, sorting, filters and cards introduce independent data/SEO/policy risk; do not require all in one PR. User-testing synthetic built Astro/headless or Owner local-browser verification; UX acceptance follows `docs/PRODUCT_UX_PRINCIPLES.md`.

### Option C — later: Sail / Power / equipment field expansion

Only after a useful and scalable result pathway: prioritize useful existing neutral dimensions for Power, specialist Sail/Power and equipment, with typed source qualification, broker entry and import/export compatibility. The 314 candidate longlist is discovery input, not accepted schema. Architecture decision on one shared multi-surface semantic field catalog requires separate evaluation of existing two registries, per-format loss, physical vs design and conditional measurements; no automatic global rewrite.

## 5. Mandatory gates and next workflow action

- **One capability:** Option A addresses **one** public Search retrieval performance/correctness property. The other options are successor capability choices, **not** bundled into this slice.
- **Visible result:** Owner can run a synthetic nonproduction first-page buyer Search and inspect evidence, continuation and measured performance; the accepted blocker exception, if needed for preparatory profiling, must be stated precisely in readiness.
- **Trigger-gate count:** **11** unchanged, no new technical facet. Search-scale #355 remains OPEN until actual gate evidence, regardless of this docs-only plan. Buyer contact verification and other external production gates remain unaffected.
- **Production:** `PRODUCTION_READINESS_GATE_STATUS=IN_PROGRESS`; no external broker/owner production data, no external pilot, no public launch, no production provider purchase; joint full Sail+Power external launch #366 preserved. `PRODUCTION_LAUNCH_PACK_PHASE=NOT_STARTED`.
- **Workflow:** First independently review/merge this docs-only **PROPOSED** reassessment as appropriate. **Owner then explicitly selects** the next bounded capability. Only then author a separate fully reconciled `SLICE-0096` READY candidate, independently review/reconcile/CI and merge, then obtain actual Owner-local `START_SLICE.bat` output. **No hand-written initial implementation prompt; no shortcut around exact-head review, Owner acceptance, separate acceptance closure and FINISH.**
