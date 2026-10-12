# SLICE-0081 — Broker Workspace Operational Dashboard

**ID:** SLICE-0081  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace product-completion / daily-operations UI  
**Depends on:** SLICE-0080 Owner-accepted/DONE; accepted Broker Workspace and performance/lead/inventory/draft read paths (SLICE-0053, -0060, -0061, -0071, -0075, -0077); Owner's 2026-10-12 product-building priority decision  
**Blocks:** a practical central daily-operations entry point; does not independently close REQ-BROKER-022/026/027/028

## Objective

Replace the authorized, mostly link-only Organization workspace landing with a coherent **read-only operational dashboard** that brings together existing Organization-scoped lead workload, recent listing drafts and inventory, and factual performance; each actionable item opens the already-authorized existing workflow.

## Plain-language capability

A broker signs in, opens the Organization workspace and immediately sees what needs attention: unread/unassigned/overdue Leads, links to recent Leads, editable draft listings and existing inventory, plus the current 30-day factual performance snapshot. Nothing is guessed or calculated from a truncated list. Every section can open its existing detailed page. A partial outage is visibly an unavailable section, never “zero activity.”

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One observable outcome: a useful Organization home dashboard assembled from **existing** read-only work surfaces. Do not smuggle in a new Lead status workflow, reporting engine, inventory importer/exporter, domain counter or autonomous scheduler.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can open `/broker/organizations/{organization_id}` in the built Astro app and inspect bounded, source-truthful operational sections, direct navigation, empty/error states, authorization states and mobile/keyboard behavior using representative synthetic data.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
`docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md` §§1,8,9 and `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md` require broker daily-work clarity. `docs/PRODUCT_EXECUTION_PLAN.md` permits one coherent cross-layer capability rather than micro-slices. Existing workflow remains the authority.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current `web/src/pages/broker/organizations/[organization_id].astro` shows Organization presentation fields and links only; existing `inventory.astro`, `drafts/index.astro`, `leads/index.astro`, `performance.astro` and their FastAPI-backed `web/src/lib/*Api.ts` provide bounded Organization read paths. `fetchOrganizationLeadCounts` already exposes `new_unread`, `unassigned`, `follow_up_due`, `follow_up_overdue`; `fetchOrganizationPerformance` exposes exact selected-window observed views/Leads/SOLD facts. No second aggregator, database table or new source of truth is necessary.

**TRIGGER GATES CHECK:** PASS  
Existing broker pilot product gate PASS and security gate PASS remain facts, but Production Readiness `IN_PROGRESS` still blocks real external production data/pilot. Dashboard implementation/fixture testing is offline/internal only; no extra technical Search criterion, public exposure, paid plan or production phase change.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
No MVP marker is upgraded at readiness: broker inventory/lead/snapshot primitives already IMPLEMENTED; existing `MVP-BROKER-008` remains PARTIAL because periodic delivery is still missing. `MVP-BROKER-009` export, `010` Search-fit, `011` bulk import, Owner-Direct `002–007`, Buyer persistence/alerts, Trust/Safety, legal/privacy/admin/comms/support and applicable launch-gated obligations remain PENDING. The dashboard comes first as a short, low-dependency composition of already accepted services, making subsequent importer/Search-fit work accessible. No currently DUE security/trust requirement is waived; all external-data/public-use triggers retain their authority.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS  

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0080_REASSESSMENT_2026-10-09.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; accepted SLICE-0053/-0060/-0061/-0071/-0075/-0077 closures.
**Production implementation checked:** `web/src/pages/broker/index.astro`; `web/src/pages/broker/organizations/[organization_id].astro`; `web/src/pages/broker/organizations/[organization_id]/inventory.astro`; `web/src/pages/broker/organizations/[organization_id]/drafts/index.astro`; `web/src/pages/broker/organizations/[organization_id]/leads/index.astro`; `web/src/pages/broker/organizations/[organization_id]/performance.astro`; `web/src/lib/brokerApi.ts`; `web/src/lib/professionalDraftApi.ts`; `web/src/lib/brokerLeadOpsApi.ts`; `web/src/lib/brokerPerformanceApi.ts`; `src/hullq/api/app.py`; `src/hullq/application/broker_workspace_read.py`; `broker_inventory_read.py`; `lead_operations.py`; `broker_performance_read.py`; existing corresponding persistence/API/web tests.
**Already implemented / not re-decided:** HullQ Account/Organization/Membership/MFA/role authority; broker-draft authoring, inventory management, lead operations/counts and factual performance; no UI-owned listing eligibility, Lead state, revenue attribution or data-derived truth; browser server-to-server Cookie forwarding and private/no-store/noindex workspace pages.
**Exact remaining gap:** Organization workspace landing currently cannot show the existing operational readouts together; user must navigate separate pages to discover Leads requiring action, recent drafts/inventory or 30-day activity.
**Accepted-but-unimplemented obligations:** Source-of-truth-preserving unified daily workspace remains an accepted product direction but lacks a concrete implementation. Other distinct `REQ-BROKER-022/026/027/028`, Owner-Direct, Buyer, Trust/Support/Legal/Admin obligations remain separately PENDING under accepted triggers; this slice does not claim to close them.
**Material classifications:** `DECIDED_AND_IMPLEMENTED` all underlying auth/read/data services; `DECIDED_NOT_YET_IMPLEMENTED` dashboard composition on the Organization landing; `EXPLICITLY_DEFERRED` new import/export, Search-fit, new counters, periodic reporting, team admin, owner-direct surface and provider deployment; `GENUINELY_OPEN` no material product/domain decision (local HTML layout and code factoring only); `CONFLICT_OR_REGRESSION` the 2026-10-09 production-account-work *priority* is explicitly superseded for current execution by the Owner's 2026-10-12 instruction to build product first. Production readiness obligations are not superseded.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  

This slice is development/testing only. The canonical `PRODUCTION_LAUNCH_PACK_PHASE` stays `NOT_STARTED`. Provider ownership, paid database/VPS provisioning, external user data/pilot and public launch are not part of this work and remain separately gated.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  

Existing Broker Workspace Launch Gate: PASS. Security Hardening & Adversarial Validation Gate: PASS. Neither authorizes real external production data while Production Readiness remains `IN_PROGRESS`.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** Although the page is read-only, composing five Organization-scoped private read services creates a cross-tenant/authorization leak risk and misleading business-count risk if one service fails or returns only a page.
**Must-never-change invariant:** Render data only from the exact requested Organization's independently authorized server results. Never translate a denied, expired-session, MFA or role-required result into a public/empty/zero metric; no data from another Organization; no client-created analytics or total-count claims from a bounded page. No write requests on dashboard GET.
**Durable source of truth / loss boundary:** Existing FastAPI read models backed by PostgreSQL own Organization, Lead, draft, inventory and performance truth. Dashboard composition is derived read-only SSR, never durable state, cached identity or a secondary authority; loss of Astro process/client state cannot change underlying facts.
**Retry / replay / partial-failure behavior:** Refresh simply re-fetches authorized current snapshots. Each panel is bounded (e.g. five recent rows, never an unbounded scan) and independently error-aware. Partial failure leaves intact already authorized sections, unless top-level Organization auth/tenant boundary has failed; it never fabricates all-zero organization activity, mutates underlying state or masks 401/403/404 as successful widgets. Concurrent source updates may produce non-atomic cross-widget snapshots; the UI must not claim a single atomic timestamp/transaction.
**Absence-vs-error / fail-closed behavior:** Successful empty `items: []` is distinguishable from API outage; `next_cursor` means more rows exist, not total count. `403` publisher/MFA denial for drafts must render an unavailable/permission message, never leak drafts. `404` must remain the canonical non-enumerating outcome. No private widget is fetched/rendered before exact Organization access is resolved. Exception and bad JSON must not leak Cookie/Origin or raw server details to the browser.
**Executable adversarial proof:** Real FastAPI+PostgreSQL+Astro SSR fixture must prove authorized same-Organization data, foreign/nonexistent Organization equivalence, unauthenticated/MFA/role-dependent states, separately failing Lead/Inventory/Draft/Performance read paths, empty-success vs unavailable, pagination/large-data limits, no cross-Organization leakage, no mutation on GET, no caching of personalized HTML and functional keyboard/mobile navigation.
**Slice sizing assessment:** COHERENT — one read-only central page wiring existing bounded read endpoints. New aggregation tables, write operations or a second reporting pipeline would be an independently testable capability and must be excluded or brought back for reconciliation.

## Why this slice exists

SLICE-0080 closed provider-independent broker original-media redundancy, and 2026-10-09 reconciliation prioritized Phase-1 production accounts **for a narrow broker pilot**. The Project Owner then expressly instructed on 2026-10-12 to stop further provider purchasing/planning and prioritize completing missing product functions rapidly. The Owner accepted the Broker Operational Dashboard as the next product step. That later instruction changes work priority only; no launch gate, accepted data policy or production-safety requirement is repealed. Reusing four existing read API clients makes this the smallest high-visible-impact broker improvement and creates a practical home for later Search-fit and import features.

## Controlling artifacts

- `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`.
- `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`.
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`.
- `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md` (preserve scope separation).
- Relevant accepted FastAPI/Astro reads and focused `tests/persistence/test_broker_workspace_access_api.py`, `test_broker_inventory_read_api.py`, `test_broker_lead_operations_api.py`, `test_broker_performance_api.py`, `test_professional_listing_draft_api.py`; `web/src/lib/__tests__/brokerInventoryApi.test.ts`, `brokerLeadOpsApi.test.ts`, `brokerPerformanceApi.test.ts`, `professionalDraftApi.test.ts`.

## In scope

1. Replace the Organization workspace main body with accessible, responsive, keyboard-operable, server-rendered overview. Preserve its existing login/not-found/MFA routing, Organization identity and authorization context, private/no-store/noindex headers.
2. Show factual **server-authoritative** Lead workload counters `new_unread`, `unassigned`, `follow_up_due`, `follow_up_overdue`, and links into the existing Leads inbox. Optionally show up to five recent Leads from the existing bounded inbox projection without leaking buyer PII in unnecessary previews.
3. Show at most five recent/editable `ProfessionalListingDraft` rows with the existing server-evaluated `promotion_readiness` result and link to the editor; role-based denial is explicit and safe, not silently empty.
4. Show at most five existing NativeListing inventory rows with current status/freshness/readiness from existing projections, linking into the authorized inventory workflows. Do not claim the displayed page is a whole-Organization total.
5. Show existing factual `LAST_30_DAYS` performance snapshot values (views/Leads/known SOLD outcomes), labeled with its actual window and without inventing rankings, total stock or daily trend; detailed analytics remains at the established route.
6. Keep existing routes fully accessible; no new first-party session, API write, domain migration, SQL, report-scheduler or client-derived qualification logic. If SSR composition needs a tiny pure presentation helper to make testing feasible, keep it bounded to this page.

## Explicitly out of scope

New Lead/inventory/draft mutation, aggregate or historical counter truth, multi-office cross-Organization dashboard, real-time polling/WebSockets, bulk operations/import/export, Search-fit, redesign of unrelated broker pages, general new component framework, new database tables, owner-direct dashboard, billing, production provisioning, service-provider changes, new Search criteria or changing the Broker Launch Gate.

## Required behavior

- Resolve exact Organization context first; no private API fan-out or item rendering on unauthenticated/not-found/MFA result.
- For authorized Organization render independent small read sections from existing FastAPI clients with bounded requests; preserve endpoint-specific auth and error semantics and never infer zero from absent/failed results.
- Label previews **recent items** or **sample**, not total inventory/drafts/leads. Use authoritative total-like Lead-count and performance endpoints only for the exact corresponding metric and time window; do not synthesize general totals from paginated arrays.
- Display actionable shortcuts to existing paths; avoid direct GET-triggered mutations. Safe HTML escaping is provided by Astro templating; no raw HTML injection or Cookie/session secret exposure.
- Preserve current no-store/noindex and ensure client/browser caching cannot reuse one Account/Organization page for another.
- Handle absent data and partial service failures with actionable ordinary labels rather than false success; retain readable error/empty/permission states on narrow screens and keyboard navigation.

## Deliverables

- Revised `web/src/pages/broker/organizations/[organization_id].astro` and any narrowly necessary read-only presentation helper.
- Focused web component/client tests for source-truth and error/empty/auth composition, links, and no invented totals; if existing read API clients suffice unchanged, do not edit them merely to create more code.
- Retained built Astro SSR + real PostgreSQL/FastAPI synthetic-tenant proof documenting panel isolation, bounded requests, invalid-session/MFA/non-publisher and partial-dependency behavior.

## Acceptance criteria

- [ ] Authorized broker sees current 30-day factual performance, exact Lead workload counters, recent draft/inventory previews and direct links to existing detailed workflows.
- [ ] Dashboard GET performs zero business mutations and introduces no new domain truth, schema, database migration or provider dependency.
- [ ] New/unread/unassigned/overdue semantics are read from the existing Lead-count endpoint; periodic report delivery is not falsely claimed implemented.
- [ ] Five-item previews disclose boundedness and never claim total Organization inventory/draft/Lead counts; all real total/snapshot metrics are source-truthful and correctly labeled.
- [ ] Unknown/unauthorized organizations remain non-enumerating; unauthenticated, MFA and non-Publisher access never display forbidden private data.
- [ ] Each private read-path outage is distinct from successful zero/empty state, without exposing internal errors, raw PII or session material.
- [ ] All existing routes and controls still operate; built Astro SSR proof and focused/full relevant tests show no regression, accessible keyboard/responsive behavior and safe private/no-store/noindex headers.
- [ ] Exact-HEAD independent implementation review and relevant remote CI/reproducibility PASS; explicit Owner acceptance **before** implementation merge and closure.
- [ ] Production Launch Pack marker stays `NOT_STARTED`, Production Readiness stays `IN_PROGRESS`, and no real external production data/pilot or infrastructure purchase occurs.

## Expected touch points

Primary: `web/src/pages/broker/organizations/[organization_id].astro`. Optional narrow presentation function/test in `web/src/lib/` and `web/src/lib/__tests__/`. Retained proof within `scripts/` or focused web/DB test harness. Reuse unmodified `brokerApi.ts`, `professionalDraftApi.ts`, `brokerLeadOpsApi.ts` and `brokerPerformanceApi.ts` by default. No migration or Python persistence change anticipated.

## Validation

- `uv run python scripts/validate_repository.py`.
- `npm test --prefix web`, `npm run check --prefix web`, `npm run build --prefix web` (plus focused new dashboard tests).
- Real PostgreSQL 18 + FastAPI + built Astro SSR synthetic fixtures through retained broker-workspace/inventory/draft/lead/performance harness; include all adversarial cases above and preserved existing route behavior.
- Exact-pushed-HEAD GitHub CI/dependency checks and Ubuntu/Windows reproducibility before implementation acceptance. Only actually executed commands may be reported PASS.

## Stop conditions

Stop if the desired dashboard requires new authoritative aggregate/data counters not already exposed, a cross-Organization privilege model, a new role/authorization decision or substantial performance-query redesign; define a separately reviewable slice or obtain an explicit Owner decision. Never invent count/missing-state behavior for convenience. Stop if the build/real-fixture verification or non-enumeration boundary cannot be proven.

**Handoff:** The readiness contract must be independently reviewed and merged to canonical `main` before the Owner uses `START_SLICE.bat`. Claude Code implements on its isolated slice branch. Exact-HEAD independent implementation review and explicit Owner acceptance remain mandatory before merging implementation.
