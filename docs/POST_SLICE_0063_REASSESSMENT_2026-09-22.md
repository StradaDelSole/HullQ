# HullQ — Post-SLICE-0063 Product / Repository Reassessment

**Date:** 2026-09-22  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `d482698a9ae468cf2a50145c1f21909ecd116963`  
**Selected next slice:** SLICE-0064 — Professional Publication Input Alignment

## 1. Reassessment result

Select **SLICE-0064 — Professional Publication Input Alignment**.

SLICE-0063 closed REQ-BROKER-023. Together with SLICE-0062, both addendum launch/pilot-baseline commitments are now implemented:

```text
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
```

The Broker Workspace Launch Gate nevertheless remains `NOT_READY`. Its next highest-priority blocker is the low-friction inventory workflow: a broker can create/resume a private ProfessionalListingDraft but cannot yet turn it into truthful marketplace inventory without operator/admin intervention.

The accepted post-0061 reconciliation already identified two concrete data-shape gaps that make immediate draft promotion unsafe:

- current professional/common draft input includes `physical_boat.boat_name`, but the accepted PhysicalBoat claim writer does not persist that field;
- every real `NativeListingOfferSnapshot` requires `listing_offer.broker_description`, but the shared draft payload cannot currently store that required offer field.

Those facts remain true on canonical main after SLICE-0063.

Therefore SLICE-0064 closes exactly this publication-input alignment gap. It does **not** perform promotion, NativeListing creation or publication.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already accepted and implemented; do not reopen:

- Auth0-compatible authentication is authentication-only;
- HullQ Account/MarketplaceOrganization/Membership/roles remain authorization truth;
- MarketplaceOrganizationId is the professional publishing principal;
- ProfessionalListingDraft is private Organization-owned pre-market state;
- professional draft authoring requires current ACTIVE membership + PUBLISHER + MFA;
- server draft persistence, optimistic versioning, CSRF, private/no-store/noindex and 24h browser-local recovery are implemented;
- NativeListing, PhysicalBoat, MarketEpisode, offer revisions, PhysicalBoat claim revisions and publication lifecycle remain separate marketplace truth;
- current offer persistence requires a real `broker_description`;
- current PhysicalBoat claim persistence supports seven buyer-critical fields but not `physical_boat.boat_name`;
- `physical_boat.boat_name` is an accepted MARKETPLACE_FIELD_REGISTRY field, PUBLIC + DISPLAY_ONLY + GATE_1_OPTIONAL;
- `listing_offer.broker_description` is PUBLIC + DISPLAY_ONLY + GATE_1_REQUIRED;
- technical native Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted but not yet implemented:

- lossless professional draft → marketplace promotion;
- professional publish/withdraw/reconfirm controls;
- shared draft support for required `listing_offer.broker_description`;
- PhysicalBoat claim persistence for `physical_boat.boat_name`;
- media workflow;
- durable leads/attribution/lead workflow;
- sale/outcome workflow;
- broker analytics/reporting;
- export/import and other later broker commitments.

The selected 0064 subset is:

> align the accepted seller draft vocabulary and PhysicalBoat claim persistence so every currently accepted professional draft value has a truthful marketplace destination and the required offer description can be collected before any later promotion transaction exists.

### EXPLICITLY_DEFERRED

Outside SLICE-0064:

- creating PhysicalBoat, MarketEpisode or NativeListing from a professional draft;
- writing claim/offer marketplace truth automatically from a draft;
- DRAFT→ACTIVE publication;
- withdraw/reconfirm/edit of NativeListings;
- promotion idempotency/mapping transaction;
- generated marketplace IDs for promotion;
- media upload/storage/gallery;
- leads/CRM/outcomes/analytics;
- Search-fit diagnostics;
- inventory export/import;
- Organization profile/admin;
- payments;
- owner-direct publication;
- production pilot/public launch.

### GENUINELY_OPEN

Remain open after 0064:

- exact professional draft-to-marketplace promotion transaction and transaction/idempotency model;
- exact promotion preflight completeness rules;
- how a later UI captures allowed explicit UNKNOWN/ABSENT responses not represented by the current simple draft vocabulary;
- whether promotion materializes marketplace DRAFT only or may optionally continue into publication after separate confirmation;
- later NativeListing edit/clone/relist semantics;
- future media asset model;
- lead workflow sequencing relative to publication.

### CONFLICT_OR_REGRESSION

No repository regression exists.

There is one sequencing constraint already accepted in `docs/POST_SLICE_0061_REASSESSMENT_2026-09-21.md`:

```text
immediate promotion
→ would drop boat_name, invent broker_description, or silently widen contracts
→ therefore must not be implicit
```

0064 resolves that named mismatch explicitly rather than hiding it inside promotion.

## 3. Existing implementation foundation

### Shared draft vocabulary

Current common draft keys:

```text
physical_boat.marketed_brand_claim
physical_boat.model_designation_claim
physical_boat.build_year
physical_boat.boat_name
listing_offer.asking_price_mode
listing_offer.asking_price_amount
listing_offer.currency
listing_offer.location_country
listing_offer.location_region
```

Professional draft adds only:

```text
broker_listing_reference
```

The common payload is shared by professional and owner-direct draft channels to avoid divergent field validation.

### Current NativeListing offer requirement

`NativeListingOfferSnapshot` requires:

```text
asking_price_mode
location_country
broker_description
```

plus amount/currency when mode is AMOUNT.

The current draft can express the first two but not `broker_description`.

### Current PhysicalBoat claim destination

`PhysicalBoatClaimSnapshot` currently persists:

```text
marketed_brand_claim
model_designation_claim
build_year
loa_length
draft
keel_configuration
rudder_configuration
```

It does not persist `boat_name`, even though the draft already accepts it and the field registry defines it as PUBLIC/DISPLAY_ONLY.

## 4. Selected v0.1 architecture

### 4.1 One shared draft vocabulary expansion

Add exactly one common draft key:

```text
listing_offer.broker_description
```

It belongs in the shared seller-draft payload rather than professional-only metadata because it is LISTING_OFFER truth, not broker-workspace metadata.

Consequences:

- professional and owner-direct draft parsers use the same validation;
- both server draft persistence paths can round-trip it;
- professional Astro editing exposes it;
- owner-direct draft surfaces must not regress and should expose the same common field where the shared form contract requires it;
- professional local-recovery capture must include it.

This does **not** publish or promote either channel.

### 4.2 Description semantics

Draft `listing_offer.broker_description`:

- plain text string;
- trimmed non-empty when durably present;
- no placeholder generation;
- no HTML trust;
- omission remains valid for an incomplete draft;
- later promotion may require it before constructing a real offer.

0064 must reuse semantics compatible with the existing `NativeListingOfferSnapshot.broker_description` requirement rather than inventing a second contradictory field.

### 4.3 PhysicalBoat boat-name claim destination

Extend the accepted PhysicalBoat claim snapshot/persistence with the field-registry semantics for:

```text
physical_boat.boat_name
```

Allowed assertion kinds:

```text
VALUE_ASSERTION(string)
ABSENT
UNKNOWN
```

The claim is:

- optional within a revision;
- PUBLIC;
- DISPLAY_ONLY;
- Organization-attributed concrete-yacht truth;
- never BoatDesign/reference truth;
- not searchable and not a new Search criterion.

A missing draft `boat_name` must **not** be silently converted into ABSENT or UNKNOWN. Later promotion may only map an explicit present draft string to VALUE_ASSERTION unless a later accepted UI/contract captures another assertion kind.

### 4.4 Revision integrity

The existing immutable PhysicalBoat claim revision + per-Organization head model remains authoritative.

Adding boat name MUST preserve:

- immutable revision history;
- optimistic current-head semantics;
- content-hash/idempotency behavior;
- Organization claim isolation;
- no cross-Organization supersession;
- existing seven fields unchanged.

### 4.5 Public presentation

0064 creates the truthful persistence/read destination required for later promotion.

If existing PhysicalBoat claim public-read serializers already project the whole accepted current snapshot, they should include boat-name state consistently. No new Search/filter criterion is authorized.

A separate buyer-page redesign is not required.

## 5. Why 0064 is selected over other launch gaps

### A. Publication input alignment — SELECTED

It is the explicit blocker already recorded against later professional promotion and directly advances Launch Gate §2 without inventing marketplace data.

### B. Immediate professional promotion/publication

Still premature on current main because the two named mapping gaps remain unresolved before 0064.

### C. Durable leads and lead workflow

Launch-critical, but a broker-first product should first make its primary inventory authoring path truthfully promotable rather than switching to CRM while listing creation remains structurally blocked.

### D. Media

Launch-critical if launch inventory includes media, but requires a materially larger rights/security/storage contract and is not the current promotion data-shape blocker.

### E. Inventory export / Search-fit diagnostics / bulk onboarding / engagement reporting

Committed later capabilities, but their timing classes do not outrank the current launch-critical inventory path.

## 6. Product success checks

### Broker

A broker can enter and durably resume the required listing description in the existing professional draft workflow, including local recovery.

### Seller-platform consistency

The shared draft parser/storage model carries the same LISTING_OFFER description field across professional and owner-direct draft channels instead of creating two validation dialects.

### Truth

A concrete-yacht boat name has an accepted Organization-attributed PhysicalBoat claim destination with correct VALUE/ABSENT/UNKNOWN semantics.

### No false promotion

No action in 0064 creates a PhysicalBoat, MarketEpisode, NativeListing, offer revision, publication transition or Search/public marketplace state from a draft.

## 7. Mandatory register and launch-gate effect

No register status changes in 0064.

```text
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
```

0064 advances REQ-BROKER-002/003/004 implementation evidence but does not by itself satisfy the entire low-friction inventory launch section.

## 8. Trigger gates

No trigger changes:

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

0064 uses internal/synthetic proof only.

## 9. Decision

**Selected execution obligation:** `SLICE-0064 — Professional Publication Input Alignment`.

Readiness proceeds on `specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md`.

Implementation may not begin until readiness receives independent exact-head ACCEPT, required remote gates are green and the readiness PR is merged to canonical `main`.
