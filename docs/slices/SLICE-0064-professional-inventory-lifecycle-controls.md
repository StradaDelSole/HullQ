# SLICE-0064 — Professional Inventory Lifecycle Controls

**ID:** SLICE-0064  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace — existing NativeListing state operations  
**Depends on:** SLICE-0053 Broker Workspace access; SLICE-0049 lifecycle; SLICE-0052 freshness; SLICE-0060 inventory overview; SLICE-0063 publisher identity  
**Blocks:** no later slice automatically; advances Broker Workspace Launch Gate inventory-operation evidence only

## Objective

Deliver exactly one capability:

> An authenticated, currently authorized professional publisher can Publish, Withdraw or Reconfirm an already-existing NativeListing owned by the selected MarketplaceOrganization from the private Broker Workspace.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: broker-facing lifecycle/freshness state controls for existing NativeListings.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can log in as an authorized PUBLISHER, operate representative DRAFT/ACTIVE listings from the Organization inventory surface, and observe factual lifecycle/freshness/public visibility changes through existing accepted read models.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The Broker Workspace Launch Gate explicitly requires publish/withdraw/reconfirm inventory jobs. Their domain/persistence semantics already exist; 0064 closes the missing broker-facing orchestration layer before attempting the materially larger unresolved draft-promotion transaction.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Existing Broker Workspace auth/MFA, Organization actor directory, inventory overview, publishing eligibility, lifecycle transition persistence, freshness/reconfirmation persistence, public listing read, Search freshness gating, professional drafts/recovery, owner-direct boundaries and launch/trigger gates were inspected.

**TRIGGER GATES CHECK:** PASS  
Production Readiness remains `NOT_TRIGGERED`; Broker Workspace Launch Gate remains `NOT_READY`; workflow reassessment remains `PASS`; 0064 adds no Search criterion, real external production data, pilot, paid plan or launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0063-acceptance-closure.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; owner-direct direction/requirements where supply boundaries could be affected.

**Production implementation checked:** `src/hullq/application/broker_workspace_read.py`; `src/hullq/application/broker_inventory_read.py`; `src/hullq/domain/publishing_eligibility.py`; `src/hullq/persistence/broker_identity.py`; `src/hullq/persistence/native_listing.py`; `src/hullq/persistence/native_listing_lifecycle.py`; `src/hullq/application/native_listing_freshness.py`; `src/hullq/persistence/native_listing_freshness.py`; `src/hullq/application/public_listing_read.py`; `src/hullq/api/app.py`; current broker web/API clients/pages; relevant tests, migrations and retained proofs.

**Already implemented / not re-decided:** exact current Account/Organization/Membership/MFA boundary; PUBLISHER + eligible Organization publishing decision; NativeListing Organization ownership; DRAFT/ACTIVE/WITHDRAWN lifecycle; DRAFT→ACTIVE publish; ACTIVE→WITHDRAWN withdraw; ACTIVE-only reconfirmation; immutable transition/freshness evidence; current public/Search freshness behavior.

**Exact remaining gap:** these accepted operations are callable only below the authenticated Broker Workspace surface (repository/operator paths); no broker-facing Organization-scoped HTTP/UI action exists for existing inventory.

**Accepted-but-unimplemented obligations:** Broker Workspace Launch Gate §2 requires practical publish/withdraw/reconfirm operations without admin intervention. 0064 implements only those controls; draft promotion, offer edit, media, leads and analytics remain separate obligations.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` lifecycle/freshness/auth semantics; `DECIDED_NOT_YET_IMPLEMENTED` broker HTTP/UI controls for those operations; `EXPLICITLY_DEFERRED` promotion/offer/media/leads/outcomes/analytics and republish; `GENUINELY_OPEN` draft-to-marketplace identity/field mapping and future republish semantics; `CONFLICT_OR_REGRESSION` none found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

Current accepted path:

```text
Broker inventory page
→ factual DRAFT / ACTIVE / WITHDRAWN / freshness state
→ NO broker mutation controls
```

Accepted persistence already supports:

```text
DRAFT -> ACTIVE
ACTIVE -> WITHDRAWN
ACTIVE -> reconfirm
```

0064 exposes exactly this existing truth through the Broker Workspace.

Direct draft promotion is not selected because it currently requires unresolved decisions/expansions:

- `physical_boat.boat_name` exists in draft input but not the implemented seven-field PhysicalBoat claim snapshot;
- NativeListing offer requires `broker_description`, absent from current professional draft;
- no accepted choice exists for new-vs-existing PhysicalBoat identity during promotion.

## Controlling artifacts

- Normative contract: `specs/PROFESSIONAL_INVENTORY_LIFECYCLE_CONTROLS_CONTRACT.v0.1.md`
- Broker access: `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`
- Inventory overview: `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md`
- Lifecycle persistence: accepted SLICE-0049 contract/implementation
- Freshness: `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md`
- Broker product direction: `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`
- Broker requirements: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`
- Launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Decision reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`

## In scope

- thin application orchestration over existing publish/withdraw/reconfirm primitives;
- Organization-scoped authenticated FastAPI write routes;
- exact current Organization/Membership/MFA/publishing-eligibility checks;
- own-listing ownership enforcement and non-enumeration;
- accepted same-origin CSRF boundary;
- stable reconfirm operation/confirmation identity;
- state-appropriate controls on existing private Organization inventory page;
- visible bounded success/failure outcomes;
- fresh inventory state after action;
- focused authorization/state/idempotency/CSRF tests;
- retained PostgreSQL 18 + OIDC/JWKS + FastAPI + built Astro proof;
- CI execution of retained proof.

## Explicitly out of scope

- ProfessionalListingDraft promotion;
- NativeListing creation;
- PhysicalBoat/MarketEpisode creation/linking;
- draft vocabulary expansion;
- physical-boat claim expansion;
- offer/price/detail edit;
- WITHDRAWN→ACTIVE republish;
- SOLD/ARCHIVED/deal state;
- media/gallery;
- leads/contact/CRM;
- analytics/reporting;
- export/import;
- Search-fit/exclusion/demand insight;
- Organization/profile admin;
- payments;
- owner-direct publication;
- buyer persistence;
- third Search criterion;
- production pilot/public launch.

## Required behavior

### A. Authorization

Reuse exact current Broker Workspace Organization/Membership/MFA truth and existing public publishing-eligibility evaluator. Never trust UI state.

### B. Tenant isolation

Selected Organization may mutate only its own persisted NativeListings. Foreign and unknown listing IDs are externally non-enumerating.

### C. Publish

Only existing complete own DRAFT listing may transition to ACTIVE through the existing persistence primitive.

### D. Withdraw

Only own ACTIVE listing may transition to WITHDRAWN. Withdrawal never means SOLD.

### E. Reconfirm

Only own ACTIVE listing may append accepted reconfirmation evidence. Stable operation ID is required for exact retry/idempotency behavior.

### F. No republish

WITHDRAWN listings have no republish control and no new transition is added.

### G. CSRF

Every browser write requires exact Origin + fixed non-simple HullQ header; failure writes nothing.

### H. Transaction safety

Application orchestration must invoke lifecycle/freshness persistence on an IDLE/fresh top-level transaction boundary after authorization reads.

### I. UI truth

After action, render current state from existing inventory/public/freshness reads; never set lifecycle/freshness only in client memory.

### J. No adjacent truth mutation

No create/promotion/offer/claim/media/lead/outcome/Search mutation.

## Deliverables

1. application orchestration/result model for existing inventory lifecycle controls;
2. Organization-scoped FastAPI mutation routes;
3. broker web API/client support;
4. lifecycle/reconfirm action controls on Organization inventory surface;
5. focused Python/web tests;
6. retained real PostgreSQL 18 + local OIDC/JWKS + FastAPI + built Astro proof;
7. CI execution of retained proof;
8. handoff to REVIEW, never DONE.

## Acceptance criteria

- [ ] Unauthenticated action is blocked.
- [ ] Unknown/unauthorized Organization remains non-enumerating.
- [ ] MFA-required session writes nothing.
- [ ] Missing PUBLISHER role writes nothing.
- [ ] Inactive/revoked membership writes nothing.
- [ ] UNVERIFIED/INELIGIBLE Organization writes nothing under existing evaluator.
- [ ] Foreign and unknown listing IDs use the same bounded not-found shape.
- [ ] Complete own DRAFT Publish transitions exactly once to ACTIVE.
- [ ] Incomplete DRAFT Publish returns bounded failure and remains DRAFT.
- [ ] Publish on ACTIVE/WITHDRAWN returns state conflict with no extra transition.
- [ ] Publish creates no offer/PhysicalBoat/MarketEpisode/claim revision.
- [ ] Own ACTIVE Withdraw transitions exactly once to WITHDRAWN.
- [ ] Withdraw on DRAFT/WITHDRAWN returns conflict.
- [ ] Withdraw never creates SOLD/outcome state.
- [ ] Own ACTIVE Reconfirm succeeds with stable operation ID.
- [ ] Exact reconfirm retry is idempotent.
- [ ] Conflicting reconfirm operation-ID reuse fails closed.
- [ ] DRAFT/WITHDRAWN reconfirm writes no confirmation.
- [ ] Reconfirm does not change lifecycle.
- [ ] Stale ACTIVE reconfirm restores accepted current freshness/public eligibility where all other conditions hold.
- [ ] Valid browser Origin + fixed header succeeds.
- [ ] Missing/foreign Origin fails with zero mutation.
- [ ] Missing/wrong fixed header fails with zero mutation.
- [ ] Inventory UI shows Publish for DRAFT, Withdraw+Reconfirm for ACTIVE, no republish for WITHDRAWN.
- [ ] After action UI displays freshly read server state.
- [ ] Private/no-store/noindex boundary remains.
- [ ] Professional draft/recovery behavior remains unchanged.
- [ ] Publisher display identity remains unchanged.
- [ ] Owner-direct behavior remains unchanged.
- [ ] Search criterion count remains exactly two and technical Search semantics are unchanged.
- [ ] No new lifecycle/freshness/domain table/state is introduced.
- [ ] Broker mandatory requirement statuses remain unchanged.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Repository validation/lint/type-check/Python tests/web tests/check/build pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if an equivalent smaller implementation proves the contract:

- new `src/hullq/application/broker_inventory_lifecycle.py` or equivalent;
- `src/hullq/api/app.py`;
- `web/src/lib/brokerApi.ts`;
- `web/src/pages/broker/organizations/[organization_id]/inventory.astro`;
- focused API/application/web tests;
- new retained proof script;
- `.github/workflows/ci.yml` to run retained proof.

No Alembic migration is expected.

No new lifecycle/freshness table, state or policy is authorized.

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

Run/report the exact retained 0064 professional inventory lifecycle controls proof selected by implementation.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation needs a new lifecycle state or transition;
- implementation needs WITHDRAWN→ACTIVE republish;
- implementation needs draft promotion or a new NativeListing;
- implementation needs new PhysicalBoat/MarketEpisode identity policy;
- application would bypass current membership/MFA/publishing eligibility;
- browser write cannot preserve accepted same-origin CSRF behavior;
- successful mutation cannot preserve top-level transaction ownership;
- foreign listing existence would become observable;
- re-confirmation cannot preserve accepted idempotency/conflict semantics;
- a schema migration is proposed;
- scope expands into offer edit, media, leads, analytics, Search or production pilot.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, successful remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0065.
