# HullQ — Post-SLICE-0066 Repository / Product Reassessment

**Date:** 2026-09-27  
**Canonical base:** `origin/main` at `48b2959d9b9edcaeeb8641219e6b6e10eeb82fa4`  
**Accepted through:** SLICE-0066  
**Queue:** SLICE-0067 — selected below, not yet implementation-authorized

## 1. Purpose

SLICE-0066 is owner-accepted, closure-complete and locally finished.

This reassessment applies:

- canonical repository truth on `origin/main`;
- `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`;
- `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`;
- the Broker Workspace Launch Gate / Mandatory Capability Register;
- the risk-based slice-sizing amendment in `docs/PRODUCT_EXECUTION_PLAN.md`.

The goal is to select the smallest safe **vertical** capability that materially advances the professional Broker → Listing → Buyer path.

## 2. Repository-proven state after SLICE-0066

HullQ now has accepted durable primitives for:

```text
ProfessionalListingDraft
PhysicalBoat
MarketEpisode
NativeListing
NativeListing lifecycle (DRAFT / ACTIVE / WITHDRAWN)
NativeListingOfferRevision + current head
Organization-scoped PhysicalBoatClaimRevision + current head
professional Account / Organization / Membership / MFA authorization
publishing eligibility
Broker Workspace inventory overview
existing-listing Publish / Withdraw / Reconfirm
public NativeListing read surface
```

Professional drafts now contain every response required by accepted D07 for minimum promotion readiness:

- concrete marketed brand;
- concrete model designation;
- explicit build-year VALUE_ASSERTION or UNKNOWN;
- asking-price mode;
- location country;
- broker description;
- amount + currency when mode is AMOUNT.

Optional boat name, location region and broker reference are also representable.

No ProfessionalListingDraft → marketplace promotion exists.

## 3. Promotion is now the shortest launch-critical capability

The broker-launch execution focus requires ordinary post-0066 selection to prefer work that advances:

```text
broker creates
→ adds media
→ publishes
→ buyer contacts
→ broker operates inventory/leads
```

The direct next missing edge is:

```text
ProfessionalListingDraft
→ PROMOTION_READY
→ NativeListing DRAFT
```

Media cannot be attached under the accepted D13 architecture until a real NativeListing exists. Publication also remains correctly separate under D03/D06.

Therefore media/publication before promotion would invert the accepted dependency.

## 4. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

- DRAFT and marketplace identity kinds are structurally distinct.
- Server-side PhysicalBoat, MarketEpisode and NativeListing identities already exist as runtime-distinct types.
- PhysicalBoat persistence is durable and FK-safe.
- MarketEpisode persistence is durable and requires a real PhysicalBoat.
- NativeListing persistence is durable and supports nullable/resolved MarketEpisode-at-creation provenance.
- every newly created NativeListing begins lifecycle `DRAFT` through the accepted schema default.
- NativeListing offer revisions and explicit current heads exist.
- Organization-scoped PhysicalBoat claim revisions and explicit current heads exist.
- brand/model/build-year marketplace claim types can be built from accepted draft responses.
- optional draft boat name can map to a concrete VALUE_ASSERTION claim when present.
- offer domain types support AMOUNT/POA, country, region and broker description.
- current professional auth/MFA/PUBLISHER workspace boundary exists.
- publishing eligibility evaluator exists.
- professional draft optimistic versioning exists.
- all D07 input-shape blockers identified before 0066 are closed.
- no external production inventory/pilot is active.
- technical native Search criterion count remains exactly 2.

### DECIDED_NOT_YET_IMPLEMENTED

- one canonical PromotionReadiness evaluator.
- ProfessionalListingDraft `EDITABLE -> PROMOTED` state/provenance link.
- exact expected-version promotion CAS / retry behavior.
- one atomic D03 materialization transaction.
- transaction-composable persistence internals for the already-existing PhysicalBoat / MarketEpisode / NativeListing / offer / claim writes.
- browser/API Promote action.
- D09 race-safe uniqueness for resolved `(publishing_organization_id, market_episode_id)`.
- duplicate conflict classification at that database boundary.
- later media, PublicationReadiness, buyer lead and editing paths.
- D19 separately revisioned current operational broker reference.
- D20 post-creation MarketEpisode resolution-revision authority.

### EXPLICITLY DEFERRED FROM SLICE-0067

The first launch-critical promotion path will implement the already-decided **no safely proven existing identity** branch:

```text
no safely resolved existing PhysicalBoat
→ mint new PhysicalBoatId
→ create new MarketEpisode
→ create new NativeListing DRAFT
```

The following remain separate because they are higher-risk identity/editing capabilities rather than prerequisites for the first safe broker-created listing:

- safely resolved existing PhysicalBoat reuse;
- same/new/unresolved episode reconciliation for an existing PhysicalBoat;
- relist / republish / clone workflows;
- D19 editable operational broker-reference history;
- D20 post-creation MarketEpisode resolution corrections;
- media;
- publication;
- leads;
- marketplace editing;
- outcomes/import/export/analytics/alerts.

This is consistent with D01/D02: under identity uncertainty HullQ prefers a duplicate PhysicalBoat over a false merge, and a newly minted PhysicalBoat receives a new MarketEpisode.

### GENUINELY_OPEN

None that blocks the fresh-identity promotion path.

No new Owner policy decision is required.

### CONFLICT_OR_REGRESSION TO RESOLVE IN 0067

1. **Atomicity composition conflict:** existing public PhysicalBoat, MarketEpisode, NativeListing, offer and claim write primitives intentionally require an IDLE connection and each own/commit their own top-level transaction. Calling them sequentially cannot satisfy D03's one atomic promotion transaction.

   SLICE-0067 must introduce/reuse transaction-scoped internal write primitives while preserving the existing public standalone commit guarantees.

2. **Draft-state gap:** `professional_listing_drafts` has no EDITABLE/PROMOTED state, promotion provenance link or retry result. A successfully promoted version could currently still be edited.

3. **Resolved listing uniqueness gap:** `native_listings` has no race-safe uniqueness on resolved `(publishing_organization_id, market_episode_id)`, although accepted D09 requires it.

4. **Normative wording drift:** `MARKET_IDENTITY_CONTRACT.v0.1.md` contains older singular wording that can be read as globally one NativeListing per MarketEpisode. D09 supersedes that interpretation: uniqueness is per publishing Organization, while different Organizations may list the same resolved MarketEpisode.

## 5. Selected capability

SLICE-0067:

```text
Professional Draft → Atomic Marketplace Promotion
```

One coherent user-visible outcome:

> An authorized broker can take one promotion-ready ProfessionalListingDraft and create exactly one durable NativeListing DRAFT with its fresh PhysicalBoat, fresh MarketEpisode, initial Organization claim and initial offer, atomically and retry-safely.

This is one capability even though it crosses domain/application/API/persistence/UI layers. The material semantics were already accepted in D01–D09/D18; the remaining work is primarily safe composition plus draft-provenance state.

## 6. Fresh-identity boundary for 0067

SLICE-0067 does **not** add a yacht/episode resolver UI or accept client-supplied PhysicalBoatId, MarketEpisodeId or NativeListingId.

For this slice:

```text
no explicit trusted existing-identity resolution input exists
→ D01 default applies
→ server mints a new PhysicalBoatId
→ D02 new-PhysicalBoat branch applies
→ server mints a new MarketEpisodeId
→ server mints a new NativeListingId
```

`BoatDesignRef` remains NULL unless a later capability supplies a confirmed resolver. No BoatDesign facts are copied into PhysicalBoat truth.

## 7. Directional distance after selection

If SLICE-0067 is accepted, the shortest current route to the first normal broker-created **publicly visible** listing is approximately:

```text
0067 atomic promotion
→ minimum media/gallery
→ canonical PublicationReadiness + publish integration
```

This is a planning estimate only. No later slice number or capability is authorized in advance.

Post-0067 reassessment remains mandatory.
