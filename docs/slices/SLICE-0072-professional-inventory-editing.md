# SLICE-0072 — Post-Promotion Inventory Editing & Maintenance

**Type:** IMPLEMENTATION  
**Status:** READY CANDIDATE  
**Stage:** Broker launch path — broker edits / maintains inventory  
**Depends on:** SLICE-0071 owner-accepted / DONE  
**Normative contract:** `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md`

## Capability

Deliver one coherent recurring broker outcome:

```text
existing Organization-owned NativeListing
→ open inventory detail editor
→ revise offer / price
→ revise concrete-yacht claims
→ immutable revision history + current heads
→ authoritative readiness/public/Search re-read
```

No second listing truth store is introduced.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One recurring broker job: maintain an existing professional listing.

**VISIBLE-RESULT CHECK:** PASS  
The broker can change price/details safely and immediately see the authoritative result.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Directly advances Broker Workspace Launch Gate §2 after creation/media/publication/leads are already implemented.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Existing revisioned NativeListing offer and Organization PhysicalBoat claim persistence are reused. Lifecycle/media/draft paths remain separate.

**TRIGGER GATES CHECK:** PASS  
No production pilot/provider/payment activation and no Search criterion are introduced.

## Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED foundations

- professional inventory ownership/auth/MFA;
- revisioned current NativeListing offer truth;
- revisioned current Organization PhysicalBoat claim truth;
- draft promotion;
- lifecycle/freshness controls;
- publication readiness/current-public eligibility;
- media management;
- Lead operations.

### DECIDED_NOT_YET_IMPLEMENTED — owned by 0072

- private existing-inventory detail editor;
- current offer read/edit through existing offer revisions;
- asking-price change workflow;
- current Organization PhysicalBoat claim read/edit through existing claim revisions;
- optimistic-concurrency browser/API handling;
- ACTIVE hard-invariant protection;
- authoritative post-save readiness/public/Search re-read;
- retained end-to-end edit proof.

### DECIDED_NOT_YET_IMPLEMENTED — mandatory later

- buyer-contact email verification;
- production email provider;
- sale/outcome;
- broker engagement/performance reporting;
- portability/export;
- Search-fit diagnostics;
- bulk onboarding/import;
- usability and competitive benchmark evidence.

### EXPLICITLY DEFERRED

- media redesign;
- lifecycle redesign;
- MarketEpisode correction/reassignment;
- duplicate/relist/clone;
- owner-direct publication/editing;
- bulk editing/import/export;
- price alerts;
- generalized analytics;
- new Search criteria.

### GENUINELY_OPEN

Implementation-local route/module names, form grouping, exact mutation DTOs, bounded page composition and revision-id minting details.

### CONFLICT_OR_REGRESSION

None found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Buyer contact email verification:** PENDING  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY

## Mandatory invariants

1. Existing revision stores remain authoritative.
2. Prior revisions remain immutable.
3. Current heads are explicit, never inferred from row order.
4. Cross-Organization access/mutation remains non-enumerating.
5. Current membership/MFA truth is checked fresh.
6. Draft truth is not rewritten after promotion.
7. Offer edits do not mutate PhysicalBoat claims and vice versa except through explicit separate accepted writes.
8. Price change does not alter lifecycle/freshness/sale outcome.
9. WITHDRAWN is not republished by editing.
10. ACTIVE edits may not knowingly leave a broken hard current-public invariant.
11. Valid technical claim edits may legitimately change deterministic Search results.
12. Media truth remains untouched.
13. Lead truth remains untouched.
14. Technical native Search criterion count remains exactly 2.

## Scope

Implementation may span:

- inventory detail read projection;
- authorized offer revision application path;
- authorized PhysicalBoat claim revision application path;
- ACTIVE candidate/current-public safety evaluation;
- FastAPI private broker routes;
- Astro Broker Workspace inventory detail/editor;
- browser API/CSRF helpers;
- concurrency/idempotency tests;
- retained PostgreSQL + FastAPI + built Astro proof.

## Readiness stop conditions

Stop for reassessment if implementation requires:

- new marketplace truth model;
- lifecycle or sale/outcome redesign;
- MarketEpisode/PhysicalBoat identity reassignment;
- weakening optimistic concurrency;
- bypassing D22/D29;
- direct Search-result mutation;
- owner-direct publication changes;
- a third technical Search criterion.

## Acceptance

Independent exact-head review must verify authorization/tenancy, revision concurrency/idempotency, ACTIVE invariant safety, draft/media/Lead isolation and retained vertical proof.

Owner Acceptance remains mandatory before implementation merge.

Initial implementation prompt must come only from `START_SLICE.bat` after readiness review, remote gates and readiness merge.
