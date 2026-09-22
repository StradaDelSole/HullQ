# HullQ — Post-SLICE-0063 Product / Repository Reassessment

**Date:** 2026-09-22  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `d482698a9ae468cf2a50145c1f21909ecd116963`  
**Selected next slice:** SLICE-0064 — Professional Publication Input Alignment

## 1. Reassessment result

Select **SLICE-0064 — Professional Publication Input Alignment**.

SLICE-0063 closed REQ-BROKER-023. Together with SLICE-0062, both addendum launch/pilot-baseline commitments are implemented:

```text
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
```

The Broker Workspace Launch Gate nevertheless remains `NOT_READY`. Its next highest-priority blocker is Launch Gate §2: a broker can create/resume a private ProfessionalListingDraft but cannot yet turn it into truthful marketplace inventory without operator/admin intervention.

The accepted post-0061 reconciliation already identified two concrete data-shape gaps that make immediate promotion unsafe:

- current professional draft input includes `physical_boat.boat_name`, but the accepted PhysicalBoat claim writer does not persist that field;
- every real `NativeListingOfferSnapshot` requires `listing_offer.broker_description`, but the ProfessionalListingDraft cannot currently store that required professional offer field.

Those facts remain true on canonical main after SLICE-0063.

The OwnerDirectListingDraft contract explicitly does **not** reuse broker-specific narrative fields for private sellers. Therefore 0064 must not silently widen the shared owner-direct/common draft vocabulary with `broker_description`.

SLICE-0064 closes the professional publication-input alignment gap only. It does **not** perform promotion, NativeListing creation or publication.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already accepted and implemented; do not reopen:

- Auth0-compatible authentication is authentication-only;
- HullQ Account/MarketplaceOrganization/Membership/roles remain authorization truth;
- MarketplaceOrganizationId is the professional publishing principal;
- ProfessionalListingDraft is private Organization-owned pre-market state;
- professional draft authoring requires current ACTIVE membership + PUBLISHER + MFA;
- server draft persistence, optimistic versioning, CSRF, private/no-store/noindex and 24h browser-local recovery are implemented;
- OwnerDirectListingDraft remains a separate Account-owned seller path and its current common payload semantics remain unchanged;
- NativeListing, PhysicalBoat, MarketEpisode, offer revisions, PhysicalBoat claim revisions and publication lifecycle remain separate marketplace truth;
- NativeListingOfferSnapshot requires a real nonblank `broker_description`;
- current PhysicalBoat claim persistence supports seven buyer-critical fields but not `physical_boat.boat_name`;
- `physical_boat.boat_name` is an accepted field-registry field, PUBLIC + DISPLAY_ONLY + GATE_1_OPTIONAL;
- `listing_offer.broker_description` is PUBLIC + DISPLAY_ONLY + GATE_1_REQUIRED;
- technical native Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted but not yet implemented:

- lossless professional draft → marketplace promotion;
- professional publish/withdraw/reconfirm controls;
- professional-draft storage/editing for required `listing_offer.broker_description`;
- PhysicalBoat claim persistence for `physical_boat.boat_name`;
- media workflow;
- durable leads/attribution/lead workflow;
- sale/outcome workflow;
- broker analytics/reporting;
- export/import and other later broker commitments.

The selected 0064 subset is:

> give the ProfessionalListingDraft a bounded professional-only offer-description input and give the existing PhysicalBoat claim revision model a truthful boat-name destination, so the two repository-proven promotion mapping holes are closed before promotion itself is specified.

### EXPLICITLY_DEFERRED

Outside SLICE-0064:

- creating PhysicalBoat, MarketEpisode or NativeListing from a professional draft;
- writing claim/offer marketplace truth automatically from a draft;
- DRAFT→ACTIVE publication;
- withdraw/reconfirm/edit of NativeListings;
- promotion idempotency/mapping transaction;
- generated marketplace IDs for promotion;
- any change to OwnerDirectListingDraft narrative vocabulary;
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
- how later UI captures allowed explicit UNKNOWN/ABSENT responses not represented by the current professional draft vocabulary;
- whether promotion materializes marketplace DRAFT only or may optionally continue into publication after separate confirmation;
- later NativeListing edit/clone/relist semantics;
- future media asset model;
- lead workflow sequencing relative to publication.

### CONFLICT_OR_REGRESSION

No production regression exists.

The readiness review found one normative conflict in an earlier draft of 0064: OwnerDirect v0.1 explicitly says broker-specific narrative fields are not reused for private sellers. That conflict is resolved here by keeping `listing_offer.broker_description` professional-only.

The existing ProfessionalListingDraft and Recovery contracts are amended in the same readiness package so no later spec silently contradicts the accepted nine-key shared payload or recovery field envelope.

## 3. Existing implementation foundation

### Shared draft vocabulary

Current common draft keys remain exactly:

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

Professional draft currently adds only:

```text
broker_listing_reference
```

Owner-direct keeps exactly the current common payload. 0064 does not add broker-specific narrative fields there.

### Current NativeListing offer requirement

`NativeListingOfferSnapshot` requires:

```text
asking_price_mode
location_country
broker_description
```

plus amount/currency when mode is AMOUNT.

The professional draft can express the first two but not `broker_description`.

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

It does not persist `boat_name`, even though the professional/common draft already accepts it and the field registry defines it as PUBLIC/DISPLAY_ONLY.

## 4. Selected v0.1 architecture

### 4.1 Professional-only draft offer description

ProfessionalListingDraft gains exactly one additional professional draft input:

```text
listing_offer.broker_description
```

It is professional-only because the accepted owner-direct contract explicitly does not repurpose broker-specific narrative fields for private sellers.

It is **not** broker metadata like `broker_listing_reference`; it is pre-market LISTING_OFFER input.

The existing nine-key common seller payload remains unchanged.

Implementation may persist it as a dedicated nullable professional-draft field or an equivalently bounded professional extension. It MUST NOT silently inject it into OwnerDirectListingDraft.

### 4.2 Description semantics

Professional draft `listing_offer.broker_description`:

- plain text string;
- trimmed non-empty when durably present;
- no placeholder generation;
- no HTML trust;
- omission remains valid for an incomplete draft;
- later promotion may require it before constructing a real offer.

### 4.3 Professional recovery

The professional browser-local recovery envelope expands to include the new editable form string with exactly the accepted 0062 scope/version/retention/failure rules.

### 4.4 PhysicalBoat boat-name claim destination

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

The claim is optional, PUBLIC, DISPLAY_ONLY, Organization-attributed concrete-yacht truth, never BoatDesign/reference truth, and never a Search criterion.

A missing draft boat_name MUST NOT be silently converted into ABSENT or UNKNOWN.

### 4.5 Revision integrity

The existing immutable PhysicalBoat claim revision + per-Organization head model remains authoritative.

Adding boat name MUST preserve:

- immutable revision history;
- optimistic current-head semantics;
- content-hash/idempotency behavior;
- Organization claim isolation;
- no cross-Organization supersession;
- existing seven fields unchanged.

### 4.6 Public/read projection

0064 creates the truthful persistence/read destination required for later promotion.

If current PhysicalBoat claim serializers represent the full current snapshot, they should include boat-name assertion/value consistently. No new Search/filter criterion is authorized.

## 5. Why 0064 is selected over other launch gaps

### A. Publication input alignment — SELECTED

It is the explicit blocker already recorded against later professional promotion and directly advances Launch Gate §2 without inventing marketplace data.

### B. Immediate professional promotion/publication

Still premature because the two named mapping gaps remain unresolved before 0064.

### C. Durable leads and lead workflow

Launch-critical, but the broker-first product should first make its primary inventory authoring path truthfully promotable rather than switch to CRM while listing creation remains structurally blocked.

### D. Media

Launch-critical if launch inventory includes media, but it requires a materially larger rights/security/storage contract and is not the current promotion data-shape blocker.

### E. Inventory export / Search-fit diagnostics / bulk onboarding / engagement reporting

Committed later capabilities, but their timing classes do not outrank the current launch-critical inventory path.

## 6. Product success checks

### Broker

A broker can enter, save, reopen and locally recover the required broker description in the existing ProfessionalListingDraft workflow.

### Owner-direct

No owner-direct API, parser, persistence or browser vocabulary changes.

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

0064 advances REQ-BROKER-003/004 evidence but does not satisfy the full low-friction inventory launch section.

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
