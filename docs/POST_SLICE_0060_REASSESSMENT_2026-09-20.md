# HullQ — Post-SLICE-0060 Product / Repository Reassessment

**Date:** 2026-09-20  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `e0c26945544ffab42efbf58be5b3e73a3349e08e`  
**Selected next slice:** SLICE-0061 — Authenticated Professional Listing Draft Workspace

## 1. Reassessment result

Select **SLICE-0061 — Authenticated Professional Listing Draft Workspace**.

SLICE-0060 closed the first professional inventory-read gap:

```text
authenticated Account
→ current Organization/Membership/MFA authorization
→ Organization-owned current NativeListing inventory
→ factual lifecycle / offer / freshness / public-link state
```

The next highest-leverage professional gap is now the absence of a safe, resumable write surface before marketplace identities are minted.

HullQ already has:

```text
professional auth/Organization authorization
+ private Organization inventory read
+ immutable NativeListing creation envelope
+ lifecycle / offer / freshness / public read
```

but does **not** yet have:

```text
authorized broker
→ start incomplete listing work
→ save partial work
→ reopen later
→ update safely
→ remain private / not yet marketplace truth
```

The existing `NativeListing` creation envelope is deliberately immutable and is not a safe substitute for a progressive broker draft. The existing `OwnerDirectListingDraft` proves the private pre-market pattern, but its identity and ownership are intentionally account/owner-direct specific.

The smallest coherent continuation is therefore a separate professional pre-market draft aggregate owned by the selected Organization, while sharing field/value semantics with the owner-direct draft where the semantics are genuinely common.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- Auth0-compatible authentication is authentication-only;
- HullQ Account, Organization, Membership, roles and authorization remain PostgreSQL/domain truth;
- current membership truth is re-read on every Organization workspace request;
- unknown/unauthorized Organization access remains externally non-enumerating;
- privileged broker roles retain the accepted MFA requirement;
- professional publication authority requires the accepted publishing-eligibility decision, including active matching membership, `PUBLISHER` role and eligible/verified Organization;
- `OwnerDirectListingDraftId != NativeListingId != PhysicalBoatId != MarketEpisodeId`;
- owner-direct drafts are private pre-market state and do not create marketplace truth;
- NativeListing creation stores an immutable publishing Organization / creator Account / optional MarketEpisode link / broker reference envelope;
- NativeListing lifecycle is `DRAFT -> ACTIVE -> WITHDRAWN`, with `WITHDRAWN != SOLD`;
- current offer and freshness/reconfirmation are separate durable truth;
- public listing truth is a separate current-read boundary;
- SLICE-0060 Organization inventory is a read-only projection over existing NativeListing truth;
- FastAPI/domain/persistence own authorization and marketplace truth; Astro remains presentation;
- Broker Workspace private surfaces are noindex and private/no-store;
- Direct Search remains primary; technical Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory;
- mixed-supply direction remains professional broker/dealer inventory plus bounded owner-direct/private seller inventory;
- shared Seller Platform direction means shared primitives where semantics overlap, without forcing unrelated channel ownership/identity into one unsafe aggregate.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted professional requirements already require:

- resumable low-friction listing creation/editing;
- practical recurring inventory operations;
- protection from duplicate/repeated input;
- later publish/withdraw/reconfirm/media flows;
- launch-bounded connectivity-resilient draft recovery.

The selected 0061 subset is:

> for one explicitly selected professional Organization, allow a currently authorized publishing-capable Account to create, list, reopen, read and update private incomplete professional listing drafts with optimistic concurrency, while creating no PhysicalBoat, MarketEpisode, NativeListing, offer revision, lifecycle transition, freshness state or public Search state.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0061:

- promotion of a professional draft into PhysicalBoat/MarketEpisode/NativeListing truth;
- publication/withdraw/reconfirm controls;
- current NativeListing edit semantics;
- local/offline connectivity recovery required by REQ-BROKER-024;
- media upload/order/cover selection;
- broker logo/profile/branding completion (REQ-BROKER-023);
- duplicate/clone/relist workflow;
- Organization/staff administration;
- leads/contact persistence/attribution/assignment/CRM;
- sale/outcome workflow;
- analytics/reporting;
- Search-fit diagnostics (REQ-BROKER-026);
- Search-exclusion/demand intelligence;
- bulk import/export;
- inventory export portability;
- payments/entitlements;
- owner-direct publication/admission;
- buyer account continuity/persistent Shortlist/Saved Search;
- third Search criterion;
- production pilot, paid broker plan or public launch.

### GENUINELY_OPEN

Remain open after 0061:

- the exact later promotion transaction from professional draft into durable marketplace identities;
- whether future Owner-Direct and Professional drafts converge onto one physical table or remain channel-specific aggregates over shared field primitives;
- later safe edit/clone/relist semantics after a NativeListing already exists;
- exact browser-local recovery/synchronization design for REQ-BROKER-024;
- eventual human-readable Organization profile/branding model;
- buyer Free/Pro continuity semantics.

0061 does **not** need to settle those later boundaries.

### CONFLICT_OR_REGRESSION

No blocking conflict is present on canonical main.

One architecture constraint is decisive:

- `OwnerDirectListingDraft` cannot simply be reused as a professional Organization draft because its identity, owner-account scoping and API semantics are intentionally owner-direct specific;
- `NativeListing` cannot serve as an incomplete progressive draft because its creation envelope is immutable and marketplace-scoped.

Therefore 0061 introduces a distinct `ProfessionalListingDraftId` and Organization-owned private draft persistence, while reusing/extracting shared field validation semantics where safe. This is compatible with the accepted shared Seller Platform direction because shared platform does not require unsafe identity/ownership conflation.

## 3. Existing implementation foundation

Accepted broker access already provides:

```text
signed HullQ session
→ AccountId
→ current OrganizationMembership
→ role/MFA authorization
→ current Organization context
```

Accepted professional publication eligibility already provides a strict decision requiring:

```text
matching Account
+ matching Organization
+ ACTIVE membership
+ PUBLISHER role
+ eligible Organization
+ verified Organization
```

Accepted owner-direct draft work already proves:

- distinct pre-market identity;
- private PostgreSQL persistence;
- partial/empty drafts;
- full-payload validation;
- optimistic versioning;
- same-account ownership scoping;
- list/read/create/update;
- Origin + non-simple-header CSRF protection;
- no marketplace promotion;
- private/no-store/noindex web behavior.

0061 may reuse those **patterns and common field/value semantics**, but must not reinterpret owner-direct ownership as Organization ownership.

## 4. Selected v0.1 professional draft architecture

### 4.1 Identity

Introduce:

```text
ProfessionalListingDraftId
!= OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

A draft ID is private pre-market workflow identity only.

### 4.2 Ownership

Authoritative professional draft ownership is:

```text
owner_organization_id
```

Creation also records:

```text
created_by_account_id
```

for audit, but creator Account is not the ongoing ownership boundary.

Current authorized publishing-capable members of the same Organization may access that Organization's drafts. A client-supplied Organization or Account identity never substitutes for the signed session + current membership authorization.

### 4.3 Authorization

All list/read/create/update requests:

1. validate current HullQ session;
2. read current Organization/Membership state;
3. apply existing Broker Workspace non-enumeration/MFA behavior;
4. require current professional publishing eligibility through the accepted publishing-eligibility decision;
5. only then read or mutate that Organization's professional drafts.

0061 creates no new role vocabulary.

### 4.4 Shared Seller field semantics

The initial professional draft uses the same bounded common draft field vocabulary already accepted for owner-direct v0.1:

- `physical_boat.marketed_brand_claim`;
- `physical_boat.model_designation_claim`;
- `physical_boat.build_year`;
- `physical_boat.boat_name`;
- `listing_offer.asking_price_mode`;
- `listing_offer.asking_price_amount`;
- `listing_offer.currency`;
- `listing_offer.location_country`;
- `listing_offer.location_region`.

Professional-only draft metadata may additionally include an optional trimmed non-empty `broker_listing_reference`.

Implementation must not create a second inconsistent parser for the nine common fields. It should extract/reuse a channel-neutral field/value validation primitive while preserving the existing owner-direct external contract and behavior.

### 4.5 Persistence

A dedicated professional draft persistence boundary is permitted/expected.

Conceptually:

```text
professional_listing_drafts
  draft_id
  owner_organization_id
  created_by_account_id
  broker_listing_reference nullable
  payload
  version
  created_at
  updated_at
```

The exact physical JSON/column representation is implementation detail if the contract is preserved.

No migration of existing owner-direct draft rows is required by 0061.

### 4.6 Concurrency

Updates use optimistic concurrency with `expected_version`.

A stale version fails with a conflict and must not silently overwrite newer broker work.

## 5. Why 0061 is selected over other gaps

### A. Professional Listing Draft Workspace — SELECTED

Highest current dependency leverage.

It turns the read-only professional workspace into a real, safe write workflow without yet contaminating marketplace truth. It is also the necessary server-side foundation for later REQ-BROKER-024 connectivity recovery and for eventual create/publish promotion.

### B. REQ-BROKER-023 branding

Mandatory before Broker Workspace Launch Gate PASS, but lower dependency leverage than listing creation. Branding becomes more meaningful once a broker can actually create/manage professional listing work.

### C. REQ-BROKER-024 connectivity-resilient recovery

Mandatory before gate PASS, but it depends on an actual broker draft/edit surface to recover. 0061 establishes that surface; 0061 does not claim REQ-BROKER-024 implemented.

### D. Lead/contact persistence

Launch-critical but downstream of usable supply operations. A broker currently cannot create new professional inventory through the self-service workspace.

### E. Owner-direct publication/admission

Still requires verified phone reachability, right-to-list attestation and anti-abuse/admission semantics. It is broader than the current professional continuation.

### F. Buyer account continuity / Saved Search

Accepted future value, but professional supply operations are now the larger product gap after Search/Sensitivity/Shortlist/Compare.

### G. Third Search criterion

Still subject to the third-copy abstraction guard and currently lower leverage than professional supply creation.

## 6. Product success checks

### Buyer

No direct buyer behavior changes in 0061. Buyer safety improves indirectly because incomplete broker work remains private until a later explicit promotion/publication capability proves marketplace truth.

### Broker

A broker can finally start incomplete listing work, save it, leave, return and continue without forcing incomplete data into NativeListing truth.

### Advantage

The architecture supports the accepted “do not enter information twice” / progressive-completion direction while preserving HullQ's strict truth boundaries.

### Success evidence

Retained proof must show an authorized publishing-capable member can create/reopen/update a partial draft; another Organization cannot access it; revoked authorization fails on the next request; version conflicts do not overwrite; and draft actions create no marketplace truth rows.

### Quality

The implementation must preserve current auth/MFA, Organization isolation, owner-direct behavior, marketplace identities, Search behavior and private-cache/indexing boundaries.

## 7. Broker Mandatory Capability Register check

Canonical register remains:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING

REQ_BROKER_022_STATUS: PENDING
REQ_BROKER_023_STATUS: PENDING
REQ_BROKER_024_STATUS: PENDING
REQ_BROKER_025_STATUS: PENDING
REQ_BROKER_026_STATUS: PENDING
REQ_BROKER_027_STATUS: PENDING
REQ_BROKER_028_STATUS: PENDING
REQ_BROKER_029_STATUS: PENDING
REQ_BROKER_030_STATUS: IMPLEMENTED
```

No requirement became `DUE` from SLICE-0060.

0061 advances REQ-BROKER-003/004 foundationally but does **not** mark any register item 022–029 implemented.

In particular:

- REQ-BROKER-023 remains PENDING;
- REQ-BROKER-024 remains PENDING because ordinary connectivity-loss recovery/client-side draft protection is not yet part of 0061;
- Broker Workspace Launch Gate remains NOT_READY.

## 8. Owner-direct / shared Seller Platform reconciliation

0061 preserves owner-direct semantics.

It does not:

- migrate or reinterpret `OwnerDirectListingDraftId`;
- change owner-direct account ownership;
- add Organization requirements to owner-direct sellers;
- publish owner-direct drafts;
- promote either draft kind to marketplace truth;
- prefer professional inventory in buyer Search.

Shared Seller Platform direction is advanced narrowly by sharing common field/value validation semantics rather than duplicating them. Channel-specific identity and authorization remain separate because they encode genuinely different ownership.

## 9. Trigger gates

Canonical state remains:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

0061:

- adds no technical Search criterion;
- uses internal/synthetic retained proof only;
- introduces private draft persistence but no real external production data;
- starts no external broker pilot;
- activates no paid plan;
- causes no public launch.

## 10. Decision

**Selected execution obligation:** `SLICE-0061 — Authenticated Professional Listing Draft Workspace`.

Readiness may proceed on `specs/PROFESSIONAL_LISTING_DRAFT_WORKSPACE_CONTRACT.v0.1.md`.

Implementation may not start until the readiness package is independently exact-head reviewed, all required remote gates are green and the readiness PR is merged to canonical `main`.
