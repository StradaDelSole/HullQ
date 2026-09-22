# HullQ — Post-SLICE-0063 Product / Repository Reassessment

**Date:** 2026-09-22  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `d482698a9ae468cf2a50145c1f21909ecd116963`  
**Selected next slice:** SLICE-0064 — Professional Draft Publication Readiness

## 1. Reassessment result

Select **SLICE-0064 — Professional Draft Publication Readiness**.

SLICE-0063 closed REQ-BROKER-023 and, together with SLICE-0062, leaves both explicit launch/pilot-baseline addendum commitments implemented:

```text
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
```

The Broker Workspace Launch Gate nevertheless remains `NOT_READY`.

The most immediate unresolved launch-critical gap is now the professional inventory creation path:

```text
private ProfessionalListingDraft
→ ??? lossless deterministic mapping
→ marketplace PhysicalBoat / MarketEpisode / NativeListing / offer
→ publication lifecycle
```

The current repository is not yet safe to bridge this boundary.

Two concrete accepted-state mismatches block a correct promotion implementation:

1. `NativeListingOfferSnapshot` requires a non-empty `broker_description`, but the accepted ProfessionalListingDraft vocabulary does not carry `listing_offer.broker_description`;
2. `physical_boat.boat_name` is an accepted ProfessionalListingDraft field and accepted marketplace registry field, but the current bounded PhysicalBoat claim snapshot from SLICE-0050 explicitly excludes boat name.

A promotion implementation today would therefore have to silently discard accepted draft data, synthesize required offer content, reject legitimate current draft fields through ad-hoc rules, or expand truth semantics inside the promotion transaction.

SLICE-0064 closes the publication-readiness/mapping gap before any marketplace mutation is authorized.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Do not reopen:

- Auth0-compatible authentication remains authentication-only;
- HullQ Account/MarketplaceOrganization/OrganizationMembership/roles/MFA remain PostgreSQL/domain authorization truth;
- ProfessionalListingDraft is Organization-owned private pre-market state;
- current draft create/list/read/update/recovery behavior is accepted;
- ProfessionalListingDraftId remains distinct from NativeListingId/PhysicalBoatId/MarketEpisodeId;
- private draft authoring does not require OrganizationPublishingEligibility;
- actual marketplace creation/publication MUST re-apply accepted public publishing eligibility;
- MarketplaceOrganizationId is the publishing principal;
- PhysicalBoat / MarketEpisode / NativeListing identity separation is accepted;
- NativeListing immutable creation envelope is accepted;
- NativeListing offer revisions/current-head semantics are accepted;
- public lifecycle/freshness/public-read semantics are accepted;
- PhysicalBoat claim revisions are Organization-attributed broker claims, not verified BoatDesign truth;
- `DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH`;
- `UNKNOWN != omitted`;
- technical native Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Still accepted but not implemented:

- professional draft → marketplace promotion transaction;
- broker-facing publish/withdraw/reconfirm controls;
- broker media workflow;
- durable leads/attribution and lead operating workflow;
- broker analytics/performance reporting;
- sale/outcome workflow;
- inventory portability/export;
- pre-publication Search-fit diagnostics;
- bulk onboarding/import;
- remaining registered broker obligations.

The selected 0064 subset is:

> make the existing professional draft vocabulary and production claim/offer mapping complete enough to determine mechanically whether one draft can be promoted losslessly, while performing zero marketplace promotion.

### EXPLICITLY_DEFERRED

Outside SLICE-0064:

- creation of PhysicalBoat, MarketEpisode or NativeListing from a professional draft;
- NativeListing publication/lifecycle transition;
- NativeListing offer write caused by draft promotion;
- freshness confirmation;
- draft deletion/archival after promotion;
- assigning promoted NativeListingId back to the draft;
- publish/withdraw/reconfirm UI;
- media;
- leads/CRM;
- analytics;
- sale/outcome;
- payments;
- Search changes;
- public launch/pilot;
- owner-direct publication.

### GENUINELY_OPEN

Remain open after 0064:

- exact transaction/composition strategy for the future lossless promotion write;
- exact server-generated identity allocation sequence for PhysicalBoatId / MarketEpisodeId / NativeListingId / revision IDs;
- whether promotion consumes the draft or retains it as provenance after success;
- whether promotion requires a user confirmation step after readiness becomes READY;
- later NativeListing edit/clone/relist semantics;
- eventual richer PhysicalBoat claim vocabulary beyond fields required for current draft mapping.

### CONFLICT_OR_REGRESSION

No accepted behavior conflict is present on canonical main.

There is an explicit implementation gap between accepted draft state and accepted marketplace target models:

```text
Professional draft field exists:
  physical_boat.boat_name

Current PhysicalBoatClaimSnapshot:
  explicitly excludes boat_name

Required NativeListingOfferSnapshot field:
  broker_description

Current ProfessionalListingDraft:
  no listing_offer.broker_description
```

This is a gap, not a regression: earlier slices deliberately deferred promotion.

## 3. Repository foundation checked

Accepted records checked:

- `docs/PROJECT_STATE.md`;
- `docs/slices/SLICE-0063-acceptance-closure.md`;
- `docs/slices/SLICE-0061-authenticated-professional-listing-draft-workspace.md`;
- `docs/slices/SLICE-0050-first-buyer-critical-physical-boat-truth.md`;
- `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`;
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`;
- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`;
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`;
- `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`;
- `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`;
- `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`;
- `docs/governance/POST_0051_TRIGGER_GATES.md`;
- `docs/governance/PRODUCTION_READINESS_GATE.md`.

Production implementation checked:

- `src/hullq/domain/listing_draft_payload.py`;
- `src/hullq/domain/professional_listing_draft.py`;
- `src/hullq/application/professional_listing_draft.py`;
- `src/hullq/persistence/professional_listing_draft.py`;
- `src/hullq/domain/physical_boat_claims.py`;
- `src/hullq/persistence/physical_boat_claims.py`;
- `src/hullq/domain/native_listing_offer.py`;
- `src/hullq/persistence/native_listing_offer.py`;
- `src/hullq/persistence/physical_boat.py`;
- `src/hullq/persistence/market_episode.py`;
- `src/hullq/persistence/native_listing.py`;
- `src/hullq/persistence/native_listing_lifecycle.py`;
- Broker Workspace/Astro professional draft surfaces and retained proofs.

## 4. Selected v0.1 capability

### 4.1 Publication readiness, not promotion

0064 introduces one deterministic question:

```text
Can this exact current ProfessionalListingDraft be mapped losslessly
into the already-accepted marketplace input models required by a later promotion?
```

Result:

```text
READY
or
BLOCKED + structured blocker codes
```

No marketplace row may be created or mutated by the readiness evaluation.

### 4.2 Complete current professional offer input

Add professional-only draft support for:

```text
listing_offer.broker_description
```

Semantics:

- optional while the object remains an incomplete draft;
- when present: trimmed non-empty plain text;
- bounded length;
- safely escaped in browser rendering;
- not added to owner-direct shared common vocabulary by this slice;
- required for `READY`.

### 4.3 Complete current PhysicalBoat mapping for boat name

Extend the bounded production PhysicalBoat broker-claim model to represent the already-accepted registry field:

```text
physical_boat.boat_name
```

Required assertion semantics follow the registry:

```text
omitted
VALUE_ASSERTION(non-blank string)
ABSENT
UNKNOWN
```

Current professional draft maps concrete string to VALUE_ASSERTION and omission to omitted.

### 4.4 Readiness mapping

READY requires at minimum:

```text
physical_boat.marketed_brand_claim
physical_boat.model_designation_claim
physical_boat.build_year
listing_offer.asking_price_mode
listing_offer.location_country
listing_offer.broker_description
```

Conditional:

```text
AMOUNT -> asking_price_amount + currency
POA    -> amount absent + currency absent
```

Optional current draft values map losslessly:

```text
physical_boat.boat_name -> boat-name VALUE_ASSERTION
listing_offer.location_region -> LocationRegionClaim(VALUE_ASSERTION)
broker_listing_reference -> NativeListing creation envelope
```

Absent build year is a structured blocker; it MUST NOT be guessed or converted to UNKNOWN.

### 4.5 Browser visibility

The existing professional draft edit page must show READY or actionable BLOCKED reasons while retaining clear `Draft — not public` language. No Publish button is authorized.

## 5. Why this slice is selected

This is the smallest coherent bridge between accepted private draft state and accepted marketplace target models. Immediate promotion is not selected because it would otherwise bundle field-model completion with multi-aggregate mutation/transaction design.

Media, durable leads and analytics remain launch-critical but do not remove the current inability to map Broker Workspace draft state safely into marketplace truth.

## 6. Trigger gates

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

## 7. Decision

**Selected execution obligation:** `SLICE-0064 — Professional Draft Publication Readiness`.

Readiness proceeds on `specs/PROFESSIONAL_PUBLICATION_READINESS_CONTRACT.v0.1.md`.

Implementation may not begin until the readiness package is independently exact-head reviewed, required remote gates are green and the readiness PR is merged to canonical `main`.
