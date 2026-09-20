# HullQ — Post-SLICE-0059 Product / Repository Reassessment

**Date:** 2026-09-20  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `c7d3d38e29bbb0217d8808dd84f9487f136e673d`  
**Selected next slice:** SLICE-0060 — Authenticated Professional Inventory Overview

## 1. Reassessment result

Select **SLICE-0060 — Authenticated Professional Inventory Overview**.

SLICE-0059 closed the next anonymous buyer decision-tool gap:

```text
Direct Search
→ Requirement Sensitivity
→ explicit local Shortlist
→ factual whole-Shortlist Compare
```

The professional supply side is now materially less complete than the anonymous buyer side. HullQ already has:

```text
Auth0-compatible authentication
→ durable HullQ Account
→ current Organization/Membership/role authorization
→ protected Broker Workspace landing
```

and independently already has durable professional marketplace truth:

```text
PhysicalBoat
→ MarketEpisode
→ NativeListing
→ current offer revision
→ publication lifecycle
→ freshness/reconfirmation
→ current public read
```

The exact missing bridge is a broker-facing Organization-scoped inventory read surface. Today the protected workspace proves access but cannot show the Organization's own NativeListings.

The smallest high-leverage continuation is therefore:

```text
authenticated Account
+ explicit authorized Organization
→ current Organization-owned NativeListing inventory
→ lifecycle + current offer + freshness facts
→ current public link where actually public
→ no write behavior
```

This creates the first real professional inventory workspace while reusing existing truth and authorization rather than inventing broker CRUD semantics prematurely.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- Auth0-compatible authentication is authentication-only and JIT maps to a durable HullQ Account;
- HullQ owns Organization, Membership, role and authorization truth in PostgreSQL;
- Organization workspace authorization re-reads current membership truth on every request;
- unknown and unauthorized Organization access are externally non-enumerating;
- active privileged membership roles require validated MFA evidence before Organization workspace access;
- professional publishing eligibility is a separate domain decision and is not inferred from authentication alone;
- durable NativeListing creation stores the publishing Organization and creator Account as authoritative envelope fields;
- NativeListing publication lifecycle is exactly `DRAFT -> ACTIVE -> WITHDRAWN` with immutable transition audit;
- `WITHDRAWN != SOLD`, and freshness is separate from lifecycle;
- current offer revisions are durable and revisioned;
- current freshness/reconfirmation state is durable and distinct;
- public listing truth is a separate current read boundary and only public/current listings receive public presentation;
- FastAPI/domain/persistence own marketplace and authorization truth; Astro is presentation;
- Broker Workspace surfaces are personalized, `noindex` and `private, no-store`;
- owner-direct/private-seller draft state is a separate pre-market boundary and must not be merged into professional inventory truth;
- technical Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted Broker Workspace direction requires the professional user to operate real inventory, but current implementation stops at an Organization-context landing page.

The selected 0060 subset is:

> for one explicitly selected and currently authorized professional Organization, show the Organization's current NativeListing inventory factually, with deterministic ordering and current lifecycle/offer/freshness state, without adding create/edit/publish/withdraw/reconfirm controls.

This is a read-only first inventory workspace, not a claim that the Broker Workspace launch baseline is complete.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0060:

- broker listing create/intake UI/API;
- broker listing edit/mutation;
- publish/withdraw/reconfirm controls;
- pre-market professional draft identity or autosave architecture;
- connectivity-resilient client-side draft recovery (REQ-BROKER-024);
- media upload/order/cover selection;
- broker logo/profile/branding completion (REQ-BROKER-023);
- Organization self-service/staff administration;
- leads/contact persistence, attribution, assignment, follow-up or CRM;
- sale/outcome workflow;
- analytics/engagement reporting;
- Search-fit/exclusion/demand insight;
- bulk import/export;
- payments/entitlements;
- owner-direct admission/publication;
- Saved Search/monitoring/alerts;
- buyer account persistence/cross-device Shortlist;
- third Search criterion;
- production pilot or public launch.

### GENUINELY_OPEN

Remain intentionally open for later slices:

- exact professional create/edit draft architecture;
- whether a future shared Seller Platform draft abstraction supersedes or composes the current owner-direct draft model;
- exact broker inventory edit/clone/relist workflow;
- eventual human-readable Organization profile/branding model;
- buyer Free/Pro limits and durable continuity semantics.

None is required for a truthful read-only professional inventory overview.

### CONFLICT_OR_REGRESSION

No current repository conflict blocks this selection.

The existing Broker Workspace access boundary and professional NativeListing persistence/lifecycle semantics are compatible. No current requirement is marked `DUE` in the Broker Mandatory Capability Register.

A deeper implementation check did identify one important non-selection constraint: existing `NativeListing` creation is not a safe substitute for an empty progressive professional draft because its creation envelope is immutable, including its MarketEpisode linkage. 0060 therefore does **not** expose a premature create flow or invent a new pre-market draft identity.

## 3. Existing implementation foundation

The accepted broker access path already provides:

```text
/api/auth/login
→ /api/auth/callback
→ HullQ session
→ AccountId
→ current OrganizationMembership read
→ Organization workspace authorization
```

The Organization workspace currently renders only:

- Organization ID;
- professional category;
- publishing eligibility;
- membership roles;
- MFA status through the existing access outcome.

The accepted professional listing stack already persists the inventory facts needed for an overview:

- `native_listings.publishing_organization_id`;
- `NativeListingId`;
- broker listing reference;
- created timestamp;
- current lifecycle state;
- current offer head;
- freshness/reconfirmation state;
- current public-read eligibility.

No new table or marketplace identity is required to list current Organization-owned inventory.

## 4. Product success / broker leverage

This capability closes the first operational gap after authentication:

```text
login
→ select Organization
→ see actual inventory
```

It is a prerequisite surface for later create/edit/publish/media/reconfirm work and makes authorization/truth behavior inspectable before writes are introduced.

For the serious buyer, there is no behavior change. The benefit is indirect but strategically important: professional inventory operations can now grow on the same truth model buyers already consume.

For the broker, the immediate task improvement is concrete: after login, the workspace can answer “what inventory does this Organization currently have, what is its state, what is the current offer/freshness state, and which listings are actually public?”

## 5. Mandatory Broker Capability Register check

Canonical state remains:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
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

No requirement becomes `DUE` from SLICE-0059 acceptance.

0060 does not mark any pending broker requirement implemented. It is foundational inventory visibility. In particular:

- REQ-BROKER-023 remains PENDING;
- REQ-BROKER-024 remains PENDING;
- the Broker Workspace Launch Gate remains NOT_READY.

This is acceptable because no broker self-service pilot, paid broker plan or public production launch is starting.

## 6. Owner-direct / mixed-supply reconciliation

0060 is professional-only and does not weaken owner-direct direction.

It:

- does not convert owner-direct drafts into professional inventory;
- does not require private sellers to join an Organization;
- does not alter owner-direct publication/admission or trust semantics;
- does not prefer professional inventory in buyer Search;
- does not alter organic Search eligibility/classification/order;
- does not implement broker referral;
- preserves the common downstream NativeListing/public-read truth model for future mixed supply.

## 7. Trigger gates

Canonical trigger state remains:

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

SLICE-0060:

- adds no technical Search criterion;
- creates no new domain/application marketplace persistence; one supporting read-path index migration is allowed/expected;
- introduces no real external production data;
- starts no external broker self-service pilot;
- changes no public launch or paid-plan state.

## 8. Alternatives considered

### A. Authenticated Professional Inventory Overview — SELECTED

Highest current leverage-to-scope ratio.

It turns the accepted Broker Workspace access shell into the first real inventory surface using already-accepted authorization and listing truth. It introduces no write semantics or new identity. A bounded keyset read plus a supporting Organization/sort-key index avoids an unbounded table scan without changing domain truth.

### B. Professional listing create/edit workspace

Not selected yet.

Current NativeListing creation requires an immutable creation envelope and is not a safe empty progressive draft. A low-friction resumable broker creation flow needs an explicit pre-market/progressive-draft architecture rather than pretending an incomplete NativeListing is equivalent. That decision should be made after the Organization inventory read seam exists.

### C. Persistent/account Shortlist continuity

Not selected.

Accepted product direction places persistent Shortlist under Free-account continuity. Buyer login-return, durable shortlist identity, merge/migration semantics and account/entitlement boundaries are broader than this professional read continuation.

### D. Saved Search / monitoring / alerts

Not selected.

Accepted direction places Saved Search in Free-account continuity. It therefore requires buyer auth/persistence decisions, and monitoring/alerts additionally require background/event/notification semantics.

### E. Owner-direct publication/admission

Not selected.

A normal owner-direct publication path must implement verified phone reachability, explicit right-to-list attestation and baseline anti-abuse controls before marketplace promotion, with risk escalation kept separate. That is a materially broader trust/admission boundary than 0060.

### F. Seller/broker contact / durable lead

Not selected.

Lead/contact requires new durable identity/privacy/attribution/workflow semantics and is downstream of usable professional inventory operations.

### G. Third technical Search criterion

Not selected.

Criterion #3 invokes the accepted third-copy abstraction guard and adds buyer breadth while the professional workspace still lacks first-order inventory visibility.

## 9. Selected capability boundary

SLICE-0060 delivers exactly one professional capability:

> An authenticated HullQ Account that is currently authorized for an explicit professional Organization can open a private Organization inventory surface and inspect only that Organization's current NativeListings, with deterministic current lifecycle, offer, freshness and public-link facts.

Hard behavior:

```text
AUTH = current HullQ session
ORG ACCESS = current Organization/Membership authorization
INVENTORY OWNERSHIP = native_listings.publishing_organization_id
ORDER = deterministic repository-defined ordering
LIFECYCLE = current accepted NativeListing lifecycle
OFFER = current accepted offer head or explicit absent state
FRESHNESS = current accepted freshness state or explicit absent/not-applicable state
PUBLIC LINK = only when accepted current public read resolves
OTHER ORG INVENTORY = never visible
READ OVERVIEW != create/edit/publish
```

## 10. Decision

**Selected execution obligation:** `SLICE-0060 — Authenticated Professional Inventory Overview`.

Readiness may proceed on the bounded contract in `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md`.

Implementation may not start until the readiness package is independently exact-head reviewed, remote gates are green and the readiness PR is merged to canonical `main`.
