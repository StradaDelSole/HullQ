# SLICE-0060 — Authenticated Professional Inventory Overview

**ID:** SLICE-0060  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace — first Organization inventory surface  
**Depends on:** SLICE-0053 authenticated Broker Workspace access; accepted NativeListing persistence/lifecycle/offer/freshness/public-read boundaries  
**Blocks:** later broker create/edit/publish/media/resilient-draft work only; no later slice is automatically authorized

## Objective

Deliver exactly one professional capability:

> An authenticated HullQ Account can inspect the current NativeListing inventory of one explicitly selected professional Organization for which it currently has authorized Broker Workspace access, without mutating listing state.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: private Organization-scoped professional inventory overview.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can authenticate as an Account with Organization access, open that Organization's inventory route, inspect its own representative DRAFT/ACTIVE/WITHDRAWN listings and current offer/freshness/public-link state, and verify that another Organization's listing never appears.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The anonymous buyer surface now has Search, Sensitivity, Shortlist and Compare, while the Broker Workspace still stops at an access/context landing. 0060 closes the first professional inventory-operations gap with a read-only visible result before introducing higher-risk write/draft semantics.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current Account/Organization/Membership authorization, NativeListing creation envelope, lifecycle, offer, freshness, public read, Broker Mandatory Capability Register, owner-direct mixed-supply direction, architecture and trigger gates were inspected. Existing truth is reused rather than duplicated.

**TRIGGER GATES CHECK:** PASS  
Production Readiness remains `NOT_TRIGGERED`; Broker Workspace Launch Gate remains `NOT_READY`; workflow reassessment remains `PASS`; 0060 adds no Search criterion, real external production data, pilot, paid plan or launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0059_REASSESSMENT_2026-09-20.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; SLICE-0043/0045/0049/0052/0053 acceptance closures and contracts.

**Production implementation checked:** `src/hullq/application/broker_workspace_read.py`; `src/hullq/domain/broker_access.py`; `src/hullq/persistence/broker_identity.py`; `src/hullq/persistence/native_listing.py`; `src/hullq/persistence/native_listing_lifecycle.py`; `src/hullq/persistence/native_listing_offer.py`; `src/hullq/persistence/native_listing_freshness.py`; `src/hullq/application/public_listing_read.py`; `src/hullq/api/app.py`; `web/src/lib/brokerApi.ts`; `web/src/pages/broker/index.astro`; `web/src/pages/broker/organizations/[organization_id].astro`; relevant tests/migrations/retained proofs.

**Already implemented / not re-decided:** provider authentication; HullQ Account; current Organization/Membership authorization; MFA-required workspace access; professional NativeListing publishing-Organization ownership; lifecycle/offer/freshness truth; current public listing read; personalized private Broker Workspace cache/SEO boundary.

**Exact remaining gap:** an authorized professional Organization workspace cannot currently list or inspect its own NativeListing inventory.

**Accepted-but-unimplemented obligation:** the Broker Workspace is a core product surface and must ultimately support practical inventory operations. 0060 implements only the factual Organization inventory read subset.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` auth/authorization + listing truth foundation; `DECIDED_NOT_YET_IMPLEMENTED` Organization inventory overview; `EXPLICITLY_DEFERRED` all writes/drafts/media/leads/analytics and buyer continuity; `GENUINELY_OPEN` future professional progressive-draft/shared Seller Platform architecture; `CONFLICT_OR_REGRESSION` none found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

The accepted professional stack has both ends but no broker-facing bridge:

```text
Broker Workspace access
        X
Organization-owned NativeListing truth
```

0060 closes that gap with the smallest read-only vertical.

A write/create slice is not selected because the existing NativeListing creation envelope is immutable and is not a safe substitute for a progressive pre-market professional draft. Saved Search/persistent Shortlist would require buyer account continuity and persistence decisions; owner-direct publication requires its accepted trust/admission boundary.

## Controlling artifacts

- Normative contract: `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md`
- Broker access contract: `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`
- Broker requirements: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`
- Broker product direction: `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`
- Broker mandatory register: `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`
- Broker launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Owner-direct direction/spec: `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution/quality: `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/PRODUCT_UX_PRINCIPLES.md`

## In scope

- one protected Organization inventory read API/application projection;
- current session + current membership authorization reuse;
- Organization ownership derived from NativeListing publishing Organization;
- factual current lifecycle;
- broker listing reference and listing creation timestamp;
- factual current offer/POA/absent state;
- factual freshness/last-confirmed or bounded absent state;
- current public-link availability through accepted public read;
- deterministic ordering;
- private Organization inventory Astro surface;
- clear navigation from existing Organization workspace;
- empty, unauthorized, MFA-required and service-error states kept distinct;
- noindex/private-no-store boundary;
- focused authorization/isolation/truth tests;
- retained PostgreSQL + FastAPI + built Astro proof and CI execution.

## Explicitly out of scope

- listing create/intake;
- listing edit/mutation;
- publish/withdraw/reconfirm controls;
- professional pre-market draft/autosave/recovery;
- media;
- broker profile/logo/branding completion;
- Organization/staff administration;
- leads/contact/CRM;
- sale outcomes;
- analytics/reporting;
- Search-fit/exclusion/demand intelligence;
- bulk import/export;
- payments/entitlements;
- owner-direct publication/admission;
- buyer account persistence;
- persistent Shortlist;
- Saved Search/monitor/alerts;
- third Search criterion;
- production pilot/public launch.

## Required behavior

### A. Current authorization

Reuse the existing Broker Workspace access decision for the exact requested Organization on every request. Do not trust cached membership state.

### B. Organization isolation

Return only NativeListings whose persisted `publishing_organization_id` equals the exact authorized Organization.

### C. Deterministic current inventory

Order by `created_at DESC`, then `native_listing_id ASC`.

### D. Factual lifecycle

Expose exact DRAFT/ACTIVE/WITHDRAWN state. Never imply SOLD or another commercial state.

### E. Current offer

Expose current amount+currency, POA or explicit no-current-offer. Never convert or value-rank price.

### F. Current freshness

Expose existing freshness + last-confirmed when present; otherwise explicit absent/not-applicable. Never recalculate freshness in web code.

### G. Public navigation

Expose a public listing link only when the existing accepted current public listing read resolves. Do not fabricate a public URL from lifecycle alone.

### H. Empty/error distinction

Authorized empty Organization is not unauthorized and not service failure.

### I. Private web boundary

Inventory surface remains noindex and private/no-store.

### J. No writes/new persistence

Opening or using inventory overview cannot create or mutate NativeListing, lifecycle, offer, freshness, membership or any new inventory/cache row.

## Deliverables

1. FastAPI/application Organization inventory read projection;
2. persistence read support if required, without schema migration;
3. broker API client extension;
4. protected Organization inventory page;
5. Organization workspace navigation into inventory;
6. focused Python/web tests;
7. retained real PostgreSQL/FastAPI/built-Astro proof ending with the required 0060 marker;
8. CI execution of retained proof;
9. primary slice handoff to `REVIEW` only after implementation validation.

## Acceptance criteria

- [ ] Unauthenticated inventory access is blocked.
- [ ] Current authorized active membership can read the exact Organization inventory.
- [ ] Revoked/inactive membership after login fails closed.
- [ ] Unknown and unauthorized existing Organization remain externally non-enumerating.
- [ ] Existing MFA-required semantics are preserved.
- [ ] Other-Organization NativeListings never appear.
- [ ] Authorized zero-listing Organization renders ordinary empty inventory.
- [ ] Multiple items use deterministic `created_at DESC, native_listing_id ASC` order.
- [ ] DRAFT, ACTIVE and WITHDRAWN remain exact and distinct.
- [ ] WITHDRAWN is never labeled SOLD.
- [ ] Current AMOUNT offer preserves amount and original currency.
- [ ] Current POA remains POA.
- [ ] Missing current offer is explicit rather than guessed.
- [ ] Current accepted freshness/last-confirmed state is displayed when present.
- [ ] Missing/not-applicable freshness remains explicit rather than invented.
- [ ] Public navigation is shown only for an item whose accepted current public read resolves.
- [ ] Service failure remains distinct from authorized empty inventory.
- [ ] Inventory page is `noindex` and `private, no-store`.
- [ ] No inventory view action mutates listing/lifecycle/offer/freshness/membership state.
- [ ] No new inventory persistence/table/migration is introduced.
- [ ] Broker mandatory requirement statuses remain unchanged.
- [ ] Owner-direct workspace behavior remains unchanged.
- [ ] Search/public buyer behavior remains unchanged.
- [ ] Retained proof ends with `PROFESSIONAL INVENTORY OVERVIEW RESULT -> PASS`.
- [ ] Repository validation, lint, type-check, Python tests, web tests/check/build all pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if an equivalent smaller implementation is proved:

- new `src/hullq/application/broker_inventory_read.py` or equivalent;
- bounded Organization-scoped list/read query in existing persistence or a new read-only persistence module;
- `src/hullq/api/app.py`;
- `web/src/lib/brokerApi.ts`;
- `web/src/pages/broker/organizations/[organization_id]/inventory.astro`;
- `web/src/pages/broker/organizations/[organization_id].astro`;
- focused broker inventory tests;
- retained proof script;
- `.github/workflows/ci.yml` only if needed to wire the retained proof.

No Alembic migration is expected.

No React island is expected. Server-rendered Astro should be sufficient.

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

Run/report the exact retained 0060 professional inventory overview vertical-proof command selected by implementation.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation requires a new professional pre-market draft identity;
- implementation starts creating/editing/publishing/withdrawing/reconfirming listings;
- authorization cannot reuse the exact accepted current membership/MFA boundary;
- Organization ownership cannot be derived from persisted publishing Organization;
- current lifecycle/offer/freshness truth would need to be reimplemented in Astro;
- public-link eligibility would be inferred instead of reusing current public read;
- a schema migration/new inventory cache is proposed as necessary;
- cross-Organization inventory would become observable;
- owner-direct draft/publication boundaries would be broadened;
- a production-data/pilot/paid-plan/launch trigger changes;
- scope expands into media, branding, leads, analytics, Saved Search or another deferred capability.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED` with the matching explicit handoff line, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0061.
