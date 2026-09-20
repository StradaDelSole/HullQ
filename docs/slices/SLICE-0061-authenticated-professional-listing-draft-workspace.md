# SLICE-0061 — Authenticated Professional Listing Draft Workspace

**ID:** SLICE-0061  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace — private professional listing draft foundation  
**Depends on:** SLICE-0053 authenticated Broker Workspace access; SLICE-0054 private draft pattern; SLICE-0060 professional Organization inventory surface; accepted professional publishing-eligibility boundary  
**Blocks:** later professional draft promotion/publish/edit/media/recovery work only; no later slice is automatically authorized

## Objective

Deliver exactly one professional capability:

> A currently authorized publishing-capable HullQ Account can create, list, reopen, read and update private incomplete listing drafts owned by one explicitly selected professional Organization, without creating marketplace truth.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: private Organization-owned professional listing draft workspace.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can authenticate as a publishing-capable Organization member, create a partial draft, leave/reopen it, update it with version protection, observe a stale-save conflict, and verify that another Organization cannot access it and no NativeListing/PhysicalBoat/MarketEpisode/public Search state was created.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
SLICE-0060 gave brokers factual inventory visibility but no safe self-service creation path. 0061 introduces the smallest private pre-market write boundary required before any promotion/publish/media workflow.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current Broker Workspace authorization/MFA, professional publishing eligibility, NativeListing immutable creation envelope, owner-direct draft identity/persistence/CSRF/concurrency pattern, shared Seller Platform direction, mandatory broker register, owner-direct mixed-supply direction and trigger gates were inspected.

**TRIGGER GATES CHECK:** PASS  
Production Readiness remains `NOT_TRIGGERED`; Broker Workspace Launch Gate remains `NOT_READY`; workflow reassessment remains `PASS`; 0061 adds no Search criterion, external production data, pilot, paid plan or launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0060_REASSESSMENT_2026-09-20.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.

**Production implementation checked:** `src/hullq/domain/publishing_eligibility.py`; `src/hullq/domain/owner_direct_draft.py`; `src/hullq/application/owner_direct_draft.py`; `src/hullq/persistence/owner_direct_draft.py`; `src/hullq/application/listing_intake.py`; `src/hullq/persistence/native_listing.py`; `src/hullq/application/broker_inventory_read.py`; `src/hullq/api/app.py`; relevant Astro broker/owner-direct surfaces, tests, migrations and retained proofs.

**Already implemented / not re-decided:** authentication/account mapping; Organization/Membership/role authorization; MFA; publishing-eligibility evaluator; owner-direct private draft identity/concurrency/CSRF; immutable professional NativeListing creation envelope; lifecycle/offer/freshness/public-read truth; professional inventory read surface.

**Exact remaining gap:** the professional Organization workspace cannot safely start and persist incomplete listing work before NativeListing creation.

**Accepted-but-unimplemented obligation:** REQ-BROKER-003/004 require resumable low-friction professional listing creation/editing. 0061 implements only the private server-persisted draft foundation, not publication/media/offline-recovery.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` auth/authorization + marketplace truth + owner-direct draft pattern; `DECIDED_NOT_YET_IMPLEMENTED` Organization-owned professional private draft workspace; `EXPLICITLY_DEFERRED` promotion/publish/media/offline recovery/leads/analytics and other listed capabilities; `GENUINELY_OPEN` future promotion transaction, future single-table vs channel-specific Seller draft storage, later clone/relist and local recovery/sync design; `CONFLICT_OR_REGRESSION` none found.

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

The current professional workflow stops here:

```text
login
→ Organization
→ current inventory
→ X no safe incomplete create/resume path
```

The accepted operator intake path creates actual marketplace identities in a fixed durable sequence and is not an interactive progressive draft substitute.

The owner-direct draft implementation proves a safe private pre-market pattern, but its account ownership and identity must not be stretched into professional Organization semantics.

0061 therefore introduces the minimum professional draft aggregate required before later promotion/publish/media/recovery work.

## Controlling artifacts

- Normative contract: `specs/PROFESSIONAL_LISTING_DRAFT_WORKSPACE_CONTRACT.v0.1.md`
- Broker access: `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`
- Broker requirements: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`
- Broker product direction: `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`
- Broker mandatory register: `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`
- Broker launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Owner-direct reference: `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- Shared Seller direction: `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`
- Mixed-supply reconciliation: `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md`
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Product quality: `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/PRODUCT_UX_PRINCIPLES.md`
- Trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`

## In scope

- distinct `ProfessionalListingDraftId`;
- Organization-owned private professional draft persistence;
- creator Account audit field;
- current Broker Workspace authorization reuse;
- current professional publishing-eligibility reuse;
- existing MFA/non-enumeration behavior;
- create/list/read/update draft APIs;
- empty/partial drafts;
- same nine common draft fields as owner-direct v0.1;
- optional professional `broker_listing_reference`;
- shared/extracted common draft field validation semantics;
- optimistic versioning;
- deterministic bounded keyset draft listing;
- same-origin CSRF defense for writes;
- private Astro collection/edit surfaces;
- navigation from professional workspace/inventory;
- noindex/private-no-store;
- focused authorization/isolation/concurrency/non-promotion tests;
- one Alembic-managed professional-draft persistence migration plus necessary indexes/constraints;
- retained PostgreSQL + FastAPI + built Astro proof and CI execution.

## Explicitly out of scope

- creating PhysicalBoat/MarketEpisode/NativeListing from a draft;
- NativeListing edit;
- publish/withdraw/reconfirm;
- client-side/offline draft recovery (REQ-BROKER-024 remains PENDING);
- media;
- broker branding/profile completion;
- duplicate/clone/relist;
- Search-fit diagnostics;
- inventory export/import;
- Organization/staff admin;
- leads/contact/CRM;
- sale outcomes;
- analytics/reporting;
- payments;
- owner-direct publication;
- buyer persistence/Saved Search;
- third Search criterion;
- production pilot/public launch.

## Required behavior

### A. Current authorization and publishing eligibility

Every draft request must reuse current signed session + current OrganizationMembership truth and current Broker Workspace MFA/non-enumeration behavior.

After workspace access succeeds, use the accepted professional publishing-eligibility decision. Do not invent a second write-role policy.

### B. Organization ownership

Persist and scope by exact `owner_organization_id`.

Creator Account is audit metadata, not the ongoing ownership boundary.

### C. Distinct draft identity

`ProfessionalListingDraftId` must be runtime-distinct from owner-direct and marketplace identities.

### D. Shared field semantics without duplicated validators

The nine common draft keys and value rules must remain behaviorally identical to owner-direct v0.1.

Extract/reuse a channel-neutral parser/serializer or equivalent common primitive. Owner-direct external behavior must not change.

### E. Professional metadata

Optional `broker_listing_reference` may be saved and changed while still a draft. It never grants ownership or identity equivalence.

### F. Optimistic concurrency

Version starts at 1 and increments exactly once per accepted update. Stale `expected_version` returns conflict and never overwrites.

### G. Bounded list

Order drafts by `updated_at DESC`, then draft ID ascending.

Default page size 50, maximum 100, opaque keyset continuation, malformed cursor bounded failure, no unbounded list.

### H. CSRF

Browser writes require exact allowed Origin plus a fixed non-simple HullQ header. FastAPI remains authoritative.

### I. Private browser boundary

Draft pages are noindex and private/no-store and visibly state that the draft is not public.

### J. No promotion

Draft operations create/mutate no PhysicalBoat, MarketEpisode, NativeListing, offer/lifecycle/freshness/public/Search state.

## Deliverables

1. professional draft domain identity/payload boundary;
2. shared common draft field validation primitive preserving owner-direct behavior;
3. Alembic migration + professional draft persistence;
4. application authorization/create/list/read/update orchestration;
5. FastAPI routes with CSRF enforcement;
6. broker API client support;
7. protected draft collection/edit Astro pages and navigation;
8. focused Python/web regression tests;
9. retained real PostgreSQL/FastAPI/built-Astro proof;
10. CI execution of the retained proof;
11. handoff to `REVIEW`, never `DONE`.

## Acceptance criteria

- [ ] Unauthenticated draft access is blocked.
- [ ] Current authorized publishing-capable member can create a draft.
- [ ] Missing/inactive membership fails closed.
- [ ] Membership without `PUBLISHER` fails through the existing eligibility boundary.
- [ ] Publishing-ineligible/unverified Organization fails closed.
- [ ] Privileged membership without MFA remains blocked.
- [ ] Revocation/role change affects the next request.
- [ ] Other-Organization draft is never observable or mutable.
- [ ] Unknown and foreign draft use the same bounded not-found shape.
- [ ] Empty draft creation is valid.
- [ ] Partial draft survives reload/list/read.
- [ ] All nine common field rules match owner-direct v0.1 behavior.
- [ ] No second inconsistent common-field parser remains.
- [ ] Existing owner-direct tests/API behavior remain unchanged.
- [ ] Optional broker reference round-trips safely.
- [ ] Successful update increments version exactly once.
- [ ] Stale version returns conflict and no overwrite.
- [ ] Invalid field/value writes zero mutation.
- [ ] Draft list is deterministic and bounded.
- [ ] Keyset pagination does not duplicate/leak rows.
- [ ] Malformed cursor fails boundedly.
- [ ] Missing/foreign Origin fails closed.
- [ ] Missing/wrong fixed request header fails closed.
- [ ] Safe rendering handles HTML/script-like draft text as text.
- [ ] Draft pages are noindex/private-no-store.
- [ ] UI clearly states draft is not public.
- [ ] No draft action creates/mutates marketplace truth state.
- [ ] REQ-BROKER-023 and REQ-BROKER-024 remain PENDING.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Search criterion count remains exactly two.
- [ ] Retained proof ends with `PROFESSIONAL LISTING DRAFT WORKSPACE RESULT -> PASS`.
- [ ] Repository validation/lint/type-check/Python tests/web tests/check/build pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if an equivalent smaller implementation is proved:

- new channel-neutral common draft payload module or equivalent;
- compatibility adaptation in `src/hullq/domain/owner_direct_draft.py`;
- new professional draft domain/application/persistence modules;
- one Alembic migration for professional draft persistence;
- `src/hullq/api/app.py`;
- `web/src/lib/brokerApi.ts`;
- new `web/src/pages/broker/organizations/[organization_id]/drafts...` surfaces;
- focused Python/web tests;
- retained proof script;
- `.github/workflows/ci.yml` only if needed to wire the retained proof.

No marketplace-promotion migration/endpoint is authorized.

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

Run/report the exact retained 0061 professional draft vertical-proof command selected by implementation.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation would reuse `OwnerDirectListingDraftId` as the professional identity;
- implementation would use NativeListing as incomplete draft storage;
- authorization cannot reuse current membership/MFA + accepted publishing eligibility;
- a new role vocabulary is proposed;
- owner-direct ownership or API semantics would change;
- draft updates would not be optimistic-concurrency protected;
- browser writes lack explicit CSRF defense;
- professional draft work would create marketplace identities/truth;
- scope expands into publish/media/offline recovery/branding/leads/analytics or another deferred capability;
- a production-data/pilot/paid-plan/launch trigger changes.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED` with the matching explicit handoff line, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0062.
