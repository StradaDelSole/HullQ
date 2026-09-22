# HullQ — Post-SLICE-0063 Product / Repository Reassessment

**Date:** 2026-09-22  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `d482698a9ae468cf2a50145c1f21909ecd116963`  
**Selected next slice:** SLICE-0064 — Professional Inventory Lifecycle Controls

## 1. Reassessment result

Select **SLICE-0064 — Professional Inventory Lifecycle Controls**.

SLICE-0063 closed REQ-BROKER-023 and SLICE-0062 already closed REQ-BROKER-024. Both launch/pilot-baseline addendum commitments are therefore implemented, but the Broker Workspace Launch Gate remains `NOT_READY`.

The next product gap should now be selected from the gate's core operating workflow rather than from the addendum register.

The current repository has:

```text
authorized Broker Workspace
+ Organization inventory overview
+ private ProfessionalListingDraft workspace
+ browser-local draft recovery
+ accepted NativeListing publication lifecycle persistence
+ accepted NativeListing freshness reconfirmation persistence
```

but no broker-facing write surface for an existing Organization-owned NativeListing.

An external broker therefore still cannot perform these already-modelled launch-critical inventory jobs from the workspace:

```text
DRAFT -> ACTIVE
ACTIVE -> WITHDRAWN
ACTIVE -> reconfirm current-market freshness
```

SLICE-0064 exposes exactly those accepted operations through the authenticated Broker Workspace without changing their domain semantics.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already accepted and implemented; do not reopen:

- current Auth0-compatible session/account boundary;
- authoritative MarketplaceOrganization / OrganizationMembership / roles in PostgreSQL;
- Broker Workspace MFA/current-membership authorization;
- PUBLISHER role and OrganizationPublishingEligibility gates for public NativeListing operations;
- NativeListing publishing Organization ownership;
- NativeListing lifecycle states `DRAFT`, `ACTIVE`, `WITHDRAWN`;
- accepted lifecycle transitions:
  - `DRAFT -> ACTIVE`;
  - `ACTIVE -> WITHDRAWN`;
- no accepted `WITHDRAWN -> ACTIVE` republish transition;
- publication completeness predicate: NativeListing -> MarketEpisode -> PhysicalBoat + current offer;
- immutable publication-transition audit history;
- publication transition as admissible freshness confirmation evidence;
- manual-native freshness model and `ACTIVE` reconfirmation persistence;
- stale/unknown suppression from current public listing/Search surfaces without lifecycle mutation;
- Organization-scoped inventory overview showing lifecycle, offer, freshness and actual public-link state;
- professional draft and connectivity-recovery boundaries;
- public publisher identity from SLICE-0063;
- technical native Search criterion count exactly two;
- organic Search commercial independence.

### DECIDED_NOT_YET_IMPLEMENTED

The following accepted behavior is not yet available to a broker through the authenticated workspace:

- publish an already-existing complete DRAFT NativeListing;
- withdraw an already-existing ACTIVE NativeListing;
- reconfirm an ACTIVE NativeListing's freshness;
- receive bounded, visible results for denied/incomplete/stale-state attempts.

This exact subset is selected for 0064.

### EXPLICITLY_DEFERRED

Outside SLICE-0064:

- ProfessionalListingDraft -> marketplace promotion;
- minting/linking PhysicalBoat or MarketEpisode from a draft;
- NativeListing creation from a professional draft;
- offer/price edit;
- physical-boat claim editing;
- `WITHDRAWN -> ACTIVE` republish;
- SOLD/ARCHIVED or commercial/deal states;
- media/gallery operations;
- leads/contact/CRM;
- sale/outcome;
- analytics/reporting;
- export/import;
- Search-fit diagnostics;
- Organization/profile administration;
- payments/entitlements;
- production pilot/public launch.

### GENUINELY_OPEN

Remain open after 0064:

- exact professional draft-to-marketplace promotion transaction;
- explicit vessel-identity choice during promotion: new PhysicalBoat vs existing PhysicalBoat;
- target persistence for currently drafted `physical_boat.boat_name`;
- professional draft support for required `listing_offer.broker_description`;
- future `WITHDRAWN -> ACTIVE` relist/republish semantics;
- later NativeListing offer-edit workflow;
- launch media scope and architecture;
- lead/CRM workflow.

### CONFLICT_OR_REGRESSION

No blocking conflict exists on canonical main.

A material constraint prevents selecting direct draft promotion as 0064:

1. the draft vocabulary contains `physical_boat.boat_name`, but the currently implemented SLICE-0050 PhysicalBoat claim snapshot/persistence covers seven fields and does not persist boat name;
2. `NativeListingOfferSnapshot` requires non-empty `broker_description`, but the current professional draft vocabulary does not contain it;
3. the current draft contains no accepted decision for whether promotion should mint a new PhysicalBoat or link an existing concrete PhysicalBoat.

Therefore a direct promotion slice would bundle new field persistence, draft vocabulary expansion, concrete-vessel identity policy and a cross-aggregate promotion transaction. That is not a safe one-capability continuation.

By contrast, lifecycle/freshness operations on already-existing NativeListings are fully decided and already implemented below the HTTP/UI boundary.

## 3. Existing implementation foundation

Current accepted write primitives:

```text
publish_native_listing
  DRAFT -> ACTIVE
  requires existing complete chain
  requires accepted publishing eligibility
  appends immutable transition

withdraw_native_listing
  ACTIVE -> WITHDRAWN
  requires accepted publishing eligibility
  appends immutable transition

reconfirm_native_listing
  ACTIVE -> immutable freshness confirmation event
  requires accepted publishing eligibility + exact listing ownership
```

Current Broker Workspace inventory read already exposes:

```text
native_listing_id
lifecycle_state
current offer summary
freshness_status
last_confirmed_at
is_publicly_listed
```

No authenticated browser/API mutation route currently invokes the three write primitives.

## 4. Selected v0.1 architecture

### 4.1 One bounded application capability

Add a thin application/API/browser orchestration layer over existing accepted lifecycle/freshness persistence.

No new lifecycle state, freshness policy, listing identity or marketplace table is authorized.

### 4.2 Canonical operations

Preferred API family:

```text
POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/publish
POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/withdraw
POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/reconfirm
```

Equivalent naming is acceptable if mechanically unambiguous and Organization-scoped.

### 4.3 Authorization

Every operation MUST:

1. require the current signed HullQ session;
2. resolve the exact requested MarketplaceOrganization and current matching OrganizationMembership from PostgreSQL;
3. preserve existing Broker Workspace non-enumeration and MFA behavior;
4. pass the real Account + candidate Organization + current membership into the existing accepted publishing-eligibility decision/persistence primitive;
5. act only on a NativeListing whose persisted `publishing_organization_id` matches the selected Organization.

No client-supplied authorization boolean, Organization ownership assertion, role claim or publishing-eligibility result is accepted.

### 4.4 CSRF

Browser mutations must use the accepted same-origin write model:

```text
exact Origin match
+ fixed non-simple HullQ request header
+ cookie session
```

No permissive credentialed CORS.

### 4.5 Transaction ownership

The application layer must preserve the existing persistence guarantee that successful lifecycle/reconfirmation operations own and commit their top-level PostgreSQL transaction.

Authorization/read queries on the same connection must be completed/closed before invoking a primitive that requires `TransactionStatus.IDLE`.

### 4.6 Publish

Publish means only:

```text
DRAFT -> ACTIVE
```

The existing publication-completeness and publishing-eligibility rules remain authoritative.

An incomplete listing remains DRAFT and yields a visible bounded failure.

Successful publication creates no new PhysicalBoat, MarketEpisode, offer revision or draft mapping.

### 4.7 Withdraw

Withdraw means only:

```text
ACTIVE -> WITHDRAWN
```

It never means SOLD.

No `WITHDRAWN -> ACTIVE` action is introduced.

### 4.8 Reconfirm

Reconfirm is allowed only through the existing ACTIVE-listing reconfirmation primitive.

The HTTP boundary must carry a stable caller operation/confirmation identity so a genuine retry can exercise the accepted idempotent reconfirmation semantics rather than creating accidental duplicate logical actions.

A UUID-shaped request operation ID is preferred; it maps to the existing `FreshnessConfirmationId`.

### 4.9 UI

The existing private Organization inventory page is the primary surface.

Minimum action presentation:

```text
DRAFT      -> Publish
ACTIVE     -> Withdraw + Reconfirm
WITHDRAWN  -> no republish control
```

The server remains authoritative; hidden/disabled UI is never authorization.

After an action, the UI must render/reload factual current lifecycle, freshness and public-link state from the accepted inventory read model.

### 4.10 Bounded outcomes

The browser/API must distinguish at least:

- success;
- authentication required;
- MFA required;
- publishing eligibility denied;
- listing unknown/foreign Organization (non-enumerating);
- incomplete listing for publish;
- current-state conflict;
- invalid reconfirm operation ID;
- service failure.

A stale browser view must never overwrite or invent state.

## 5. Why lifecycle controls are selected before draft promotion

This is the smallest launch-gate inventory write vertical whose semantics are already complete.

It closes a real gap without deciding:

- PhysicalBoat identity creation/linking;
- draft field expansion;
- offer-description requirements;
- cross-aggregate promotion transaction design.

It also provides the actual broker-facing controls needed later to operate listings produced by a future promotion capability.

## 6. Product success checks

### Broker

An authorized PUBLISHER can operate an existing listing's publication/freshness state from the Broker Workspace without repository scripts or operator assistance.

### Buyer

Publishing/withdrawing/reconfirming immediately affects buyer visibility only through the already accepted lifecycle + freshness + public-read rules.

### Truth

No operation fabricates SOLD, offer changes, vessel identity or Search truth.

### Security

Foreign listings, revoked membership, missing MFA, ineligible Organizations and CSRF failures cannot mutate state.

## 7. Launch-gate effect

0064 advances Broker Workspace Launch Gate §2 low-friction inventory operations:

- publish;
- withdraw;
- reconfirm.

It does not by itself make the gate PASS.

Still missing after 0064 include at least:

- end-to-end professional listing creation/promotion;
- offer/price/detail editing on marketplace truth;
- media where applicable;
- durable leads + attribution;
- broker lead workflow;
- operational/source analytics;
- usability benchmark;
- competitive benchmark;
- production-readiness evidence before any real external production pilot.

## 8. Trigger gates

No trigger changes are caused by 0064:

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS
PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

0064 uses only synthetic/internal test data.

## 9. Decision

**Selected execution obligation:** `SLICE-0064 — Professional Inventory Lifecycle Controls`.

Readiness proceeds on `specs/PROFESSIONAL_INVENTORY_LIFECYCLE_CONTROLS_CONTRACT.v0.1.md`.

Implementation may not begin until the readiness package is independently exact-head reviewed, required remote gates are green and the readiness PR is merged to canonical `main`.
