# HullQ — Post-SLICE-0064 Repository / Product Reassessment

**Date:** 2026-09-23  
**Canonical base:** `origin/main` at `8ffb49949161ee204ab7090b3d31ce8484bfa9d9`  
**Accepted through:** SLICE-0064  
**Queue:** SLICE-0065 — selected below, not yet implementation-authorized

## 1. Reassessment purpose

SLICE-0064 is owner-accepted, merged and closure-complete. This reassessment determines the next highest-leverage bounded capability from canonical repository truth before any new readiness or implementation work begins.

No prior abandoned/readiness branch is treated as canonical. Earlier alternative SLICE-0064 drafts were inspected only as non-canonical prior analysis and were independently reconciled against current `main`.

## 2. Canonical product state after SLICE-0064

Accepted professional path now includes:

```text
Auth0-compatible account/session boundary
→ current Organization / Membership / role / MFA authorization
→ private ProfessionalListingDraft create/list/read/update
→ optimistic concurrency
→ connectivity-resilient local recovery
→ public publishing Organization identity
→ Organization inventory overview
→ existing complete DRAFT NativeListing: Publish
→ existing ACTIVE NativeListing: Withdraw
→ existing ACTIVE NativeListing: Reconfirm freshness
```

The Broker Workspace Launch Gate remains `NOT_READY`.

The current launch-critical inventory gap is no longer lifecycle controls. It is the bridge from professional pre-market draft data into accepted marketplace truth.

## 3. Repository-proven publication-input mismatch

Canonical `main` currently proves two concrete mismatches.

### 3.1 Draft boat name has no current accepted PhysicalBoat claim destination

The accepted shared draft payload contains:

```text
physical_boat.boat_name
```

But `PhysicalBoatClaimSnapshot` remains intentionally bounded to the seven SLICE-0050 fields and does not contain boat name.

The marketplace field registry already defines `physical_boat.boat_name` as:

- PHYSICAL_BOAT truth;
- PUBLIC;
- DISPLAY_ONLY;
- OPTIONAL;
- allowed assertion kinds `VALUE_ASSERTION`, `ABSENT`, `UNKNOWN`.

Therefore a current professional draft can contain an accepted concrete-yacht input that cannot yet be represented in the accepted PhysicalBoat broker-claim persistence model.

### 3.2 NativeListing offer requires broker_description but professional draft cannot store it

`NativeListingOfferSnapshot` requires:

```text
broker_description: str
```

and the accepted registry marks `listing_offer.broker_description` as a required LISTING_OFFER response.

Current `ProfessionalListingDraft` supports the nine shared draft fields plus `broker_listing_reference`, but has no `listing_offer.broker_description` input.

Therefore an immediate draft-to-marketplace promotion would have to invent required offer text or fail after the broker has otherwise completed the current form.

Both outcomes are unacceptable.

## 4. Decision / Implementation Reconciliation

### DECIDED_AND_IMPLEMENTED

- Account / Organization / Membership / role / MFA Broker Workspace boundary;
- professional draft identity, Organization ownership and private authoring;
- exact nine-key shared seller draft payload;
- professional-only `broker_listing_reference`;
- optimistic draft versioning;
- connectivity-resilient professional draft recovery;
- marketplace identity separation;
- NativeListing creation envelope;
- MarketEpisode / PhysicalBoat persistence;
- seven-field PhysicalBoat claim revision/current-head model;
- nine-field NativeListing offer revision model;
- required marketplace `broker_description`;
- field-registry definition of `physical_boat.boat_name`;
- NativeListing lifecycle/freshness/public truth;
- broker Publish / Withdraw / Reconfirm controls for already-existing NativeListings;
- public publishing Organization identity;
- technical native Search criterion count exactly two.

### DECIDED_NOT_YET_IMPLEMENTED

- professional-only draft input for `listing_offer.broker_description`;
- PhysicalBoat claim representation/persistence for `physical_boat.boat_name`;
- lossless professional-draft publication mapping;
- actual ProfessionalListingDraft → marketplace promotion;
- broker editing of marketplace offer/listing facts;
- structured CSV/bulk onboarding/import;
- media;
- durable leads/CRM;
- broker analytics;
- sale/outcome workflow;
- inventory portability/export;
- Search exclusion explainability / Search-fit diagnostics / demand insights;
- buyer persistent Saved Search / monitoring / price-change alerts.

### EXPLICITLY_DEFERRED FROM SLICE-0065

- any draft→PhysicalBoat / MarketEpisode / NativeListing promotion;
- automatic marketplace writes caused by draft save;
- marketplace-ID allocation;
- actual publication;
- offer editing;
- media;
- leads/CRM;
- sale/outcome;
- analytics;
- import/export;
- Search changes;
- payments;
- buyer persistence / Saved Search / price-change alert implementation;
- owner-direct publication;
- production pilot / public launch.

### GENUINELY_OPEN

- exact future atomic promotion transaction;
- future choice and UX for linking to an existing PhysicalBoat vs creating a new PhysicalBoat;
- promoted identity allocation/idempotency;
- post-promotion ProfessionalListingDraft retention/provenance semantics;
- future relist/republish semantics;
- future edit/clone/reuse semantics;
- launch media architecture;
- lead/CRM workflow;
- final buyer price-alert persistence, notification-channel and subscription semantics.

### CONFLICT_OR_REGRESSION

None found on canonical `main`.

The two publication-input mismatches above are missing capability, not a regression.

## 5. Candidate comparison

### A. Professional Publication Input Alignment

Closes the exact repository-proven data-shape blockers before promotion.

Advantages:

- directly advances Launch Gate §2;
- makes later promotion specifiable without dropping or inventing data;
- preserves one-capability scope;
- keeps OwnerDirect vocabulary unchanged;
- requires no premature identity-allocation decision;
- enables later import/onboarding work to terminate in a valid marketplace pipeline.

### B. Direct professional draft promotion now

Rejected for the next slice.

It would combine field-model expansion, PhysicalBoat identity choice, MarketEpisode creation, NativeListing creation, claim write, offer write, publication eligibility, transaction/idempotency and draft provenance in one capability boundary.

That is too much unresolved policy and implementation scope for one slice.

### C. Structured CSV / bulk import now

Strategically important but premature as the immediate next implementation.

The Broker Workspace product direction and REQ-BROKER-027 correctly require bulk onboarding before scaled broker acquisition. The newly retained Founding Broker direction increases this capability's commercial importance.

However importing inventory into ProfessionalListingDraft does not solve the current inability to map a completed draft losslessly into accepted marketplace targets.

Correct dependency order:

```text
publication-input alignment
→ lossless publication readiness / promotion
→ repeatable native marketplace creation
→ bulk import / feed onboarding without dead-end drafts
```

### D. Leads/CRM or buyer feature expansion now

Not selected. Both remain important, but the current professional inventory creation path is still incomplete and blocks the supply-side launch baseline.

## 6. Selected next capability

```text
SLICE-0065 — Professional Publication Input Alignment
```

Objective:

> Close the two repository-proven input/destination mismatches that currently make later professional draft promotion lossy: add required `listing_offer.broker_description` as a professional-only draft offer input, and add `physical_boat.boat_name` to the existing PhysicalBoat claim revision model.

No promotion occurs in SLICE-0065.

## 7. Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One bounded bridge capability: align professional pre-market input with already-accepted marketplace target vocabulary.

**VISIBLE-RESULT CHECK:** PASS  
A broker can enter/save/reopen/recover broker description in the existing professional draft UI; the accepted PhysicalBoat claim model can durably represent boat-name claim state.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Launch Gate §2 requires practical create/publish inventory and no duplicate work. This slice removes data-shape blockers without hiding unresolved promotion policy in implementation.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Professional and owner-direct draft contracts/implementation, professional recovery, NativeListing offer domain/persistence, PhysicalBoat claims, field registry, lifecycle, launch gate and mandatory register were reconciled on current `main`.

**TRIGGER GATES CHECK:** PASS  
No Search criterion, real external production data, broker pilot, paid plan or public launch is introduced.

## 8. Trigger state

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS

PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS = NOT_STARTED
PAID_BROKER_PLAN_STATUS = NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS = NOT_STARTED
```

SLICE-0065 changes no Mandatory Capability Register item merely by being selected/readied.

## 9. Buyer price-change alert direction retained separately

Owner additionally requires buyer-facing alerts when a listing's asking price changes.

This is strategically accepted as a future buyer persistence/monitoring capability and is retained separately so it cannot be lost or accidentally folded into SLICE-0065.

It is not selected as the next slice because the professional marketplace inventory creation path is still incomplete.

## 10. Next workflow step

Prepare a bounded SLICE-0065 readiness package and normative contract.

Implementation remains unauthorized until:

1. readiness package exists on a dedicated docs branch;
2. independent exact-head readiness review returns ACCEPT;
3. required remote gates pass;
4. readiness is merged to canonical `main`;
5. only then may the Project Owner run `START_SLICE.bat`.
