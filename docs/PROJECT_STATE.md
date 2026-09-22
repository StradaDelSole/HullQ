# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0063 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0064 -->

**Updated:** 2026-09-22  
**Latest owner-accepted / DONE slice:** SLICE-0063  
**Current queue:** SLICE-0064 — **Professional Draft Publication Readiness**; post-SLICE-0063 repository/product reassessment and readiness are prepared on the accepted professional draft, PhysicalBoat claim and NativeListing offer boundaries. Implementation remains unauthorized until independent exact-head readiness review, required remote gates and readiness merge to `main`.  
**Exceptional historical state:** SLICE-0039 remains terminal `BLOCKED` and is not to be reopened.

This is the compact current-state entry point for HullQ. Historical implementation/review detail belongs in slice contracts, acceptance closures, retained research packages and Git history. Normative specs and accepted decisions remain authoritative where they apply.

## Product direction

HullQ is a native **broker-first mixed-supply** sailboat listing and technical-discovery marketplace:

```text
professional broker/dealer inventory
+
bounded owner-direct/private seller inventory
```

Private sellers may self-list directly or later voluntarily choose a broker-referral path. Neither route may be forced as a substitute for the other. Organic Search eligibility, match classification and ordering remain commercially independent; payment may buy a verification service but never truth, Search eligibility or organic position.

Primary buyer loop remains:

```text
technical requirements
→ deterministic BoatDesign/configuration evaluation
→ native marketplace inventory
→ physical-boat/listing truth
→ save / monitor / alert
→ seller/broker contact / qualified lead
```

Direct technical Search remains the primary low-friction buyer entry point. The post-0054 accepted guided Buyer Requirements path is optional and must reuse the same deterministic Search/evaluation semantics.

## Accepted provider surfaces

Professional provider direction remains the best-in-class Broker Workspace. SLICE-0053 provides its accepted authentication/account/Organization/Membership/role/MFA access boundary. Auth0 remains authentication-only; HullQ PostgreSQL/domain state owns authorization truth.

SLICE-0060 adds the first accepted professional inventory read surface: an authenticated Account with current authorized Organization access can inspect only that Organization's current NativeListings with factual lifecycle, current offer, freshness and actual public-link state. The surface is read-only, bounded/keyset-paginated, private/no-store/noindex, and reuses existing FastAPI/domain/persistence truth rather than creating a second inventory model.

SLICE-0061 adds the first accepted professional incomplete-listing authoring surface: an authenticated Account with the exact current ACTIVE matching OrganizationMembership containing `PUBLISHER` may create, list, reopen, read and update private `ProfessionalListingDraft` state owned by that Organization. Draft authoring reuses existing MFA/current-membership authorization, uses optimistic versioning and bounded keyset pagination, remains private/no-store/noindex, and intentionally does not require public `OrganizationPublishingEligibility`. No draft action creates or mutates PhysicalBoat, MarketEpisode, NativeListing, offer/lifecycle/freshness/public/Search truth.

SLICE-0062 adds accepted connectivity-resilient recovery to that existing professional draft edit surface. Recent unsaved browser form input is held only in a short-lived Account/Organization/ProfessionalListingDraft/version-scoped local recovery envelope; exact bounded form strings, including intentional cleared values, are preserved. Same-version recovery may restore visibly, but stale recovery never auto-applies over newer server state. Browser storage failures degrade to a visible unavailable state without breaking ordinary server-backed drafting, untouched page navigation does not manufacture recovery state, and explicit Save remains the only durable mutation. The recovery layer is not authorization, server draft truth or marketplace truth.

SLICE-0063 adds accepted human-readable public identity for the existing MarketplaceOrganization publishing principal. A bounded `public_display_name` is persisted on the same authoritative Organization row, shown in authorized Broker Workspace context and on every readable public NativeListing independently of optional VAT/tax claims. Existing rows receive deterministic exact-ID display fallback, legacy unresolved publisher IDs remain readable, display-name changes are presentation-only and do not mutate NativeListing/listing/Search truth, and Astro renders the value as escaped plain text. `MarketplaceOrganizationId` remains the authorization/identity key; SLICE-0063 adds no second Organization identity, logo/media system or public broker profile.

SLICE-0054 now adds the first accepted owner-direct provider surface:

```text
authenticated ordinary HullQ Account
→ private OwnerDirectListingDraft
→ create / list / reopen / update own drafts
→ incomplete pre-market state may persist
→ NOT PUBLIC
```

An owner-direct Account does not require a professional Organization or Membership. Ownership is derived from the authenticated session/account, not client input. Foreign/unknown draft access is non-enumerating, updates use optimistic versioning, login-next is bounded to the owner-direct surface, mutating browser requests use the accepted Origin + non-simple-header CSRF boundary, and private pages remain no-store/noindex.

## Hard truth and identity boundaries

Accepted marketplace identity remains:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

Hard truth rule remains:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

SLICE-0054 and SLICE-0061 add separate pre-market identities:

```text
OwnerDirectListingDraftId
!= ProfessionalListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

Owner-direct draft ownership is the authenticated Account. Professional draft ownership is exact persisted `owner_organization_id`; `created_by_account_id` is audit metadata only. Draft persistence is not marketplace truth. The accepted retained proof establishes that owner-direct draft operations do not create or mutate `physical_boats`, `market_episodes`, `native_listings`, NativeListing offer revision/head state, publication-transition state or freshness-confirmation state. No public Search promotion occurs.

## Owner-direct trust direction

Future normal publication baseline remains intentionally low-friction:

```text
HullQ account
+ verified phone reachability
+ explicit right-to-list attestation
+ baseline anti-abuse checks
```

Trust scopes remain separate:

```text
PHONE VERIFIED
IDENTITY VERIFIED
RIGHT-TO-LIST ATTESTED
SALE AUTHORITY VERIFIED
```

None promotes yacht technical fields. Strong identity/documentary sale-authority verification remains a separate future trust layer and should minimize HullQ retention of raw ID/selfie/biometric material.

SLICE-0054 implements none of publication/admission, phone verification, right-to-list attestation, identity verification, Sale Authority Verification, representation-conflict handling, media, enquiries/leads, broker referral, sale outcome, Search eligibility/ranking, delete/archive, payments or production pilot.

## Built and owner-accepted product threshold

```text
SLICE-0040 marketplace identity/truth separation
→ SLICE-0041 professional publishing eligibility
→ SLICE-0042 Alembic migration baseline
→ SLICE-0043 NativeListing persistence
→ SLICE-0044 marketplace field contract
→ SLICE-0045 revisioned offer facts
→ SLICE-0046 PhysicalBoat persistence
→ SLICE-0047 MarketEpisode linkage
→ SLICE-0048 browser-visible listing preview
→ SLICE-0049 production-public listing
→ SLICE-0050 concrete-yacht broker truth
→ SLICE-0051 first production technical native Search (`draft_max`)
→ SLICE-0052 evidence-backed listing freshness/reconfirmation
→ SLICE-0053 authenticated Broker Workspace access boundary
→ SLICE-0054 authenticated Owner-Direct Listing Draft Workspace
→ SLICE-0055 second technical native Search criterion (`keel_configuration`) + mixed-criterion typed evidence
→ SLICE-0056 public multi-criterion Direct Search browser completion
→ SLICE-0057 buyer-authored one-change Requirement Sensitivity
→ SLICE-0058 anonymous browser-local Shortlist
→ SLICE-0059 anonymous factual whole-Shortlist Compare
→ SLICE-0060 authenticated professional Organization inventory overview
→ SLICE-0061 authenticated professional Organization listing draft workspace
→ SLICE-0062 professional draft connectivity recovery
```

Latest closures:

```text
docs/slices/SLICE-0052-acceptance-closure.md
docs/slices/SLICE-0053-acceptance-closure.md
docs/slices/SLICE-0054-acceptance-closure.md
docs/slices/SLICE-0055-acceptance-closure.md
docs/slices/SLICE-0056-acceptance-closure.md
docs/slices/SLICE-0057-acceptance-closure.md
docs/slices/SLICE-0058-acceptance-closure.md
docs/slices/SLICE-0059-acceptance-closure.md
docs/slices/SLICE-0060-acceptance-closure.md
docs/slices/SLICE-0061-acceptance-closure.md
docs/slices/SLICE-0062-acceptance-closure.md
```

## Accepted technical Search result

HullQ now has exactly two accepted/closed public hard technical native-inventory Search criteria:

```text
1 — draft_max=<exact positive decimal metres>
2 — keel_configuration=<canonical v0.1 value>
```

Accepted public `keel_configuration` values are exactly `FIN`, `FIN_WITH_BULB`, `WING`, `CENTERBOARD`, `LIFTING_KEEL` and `TWIN_KEEL`.

The two criteria may be evaluated alone or together as deterministic hard MUST/AND requirements. SLICE-0055 preserves typed criterion/configuration evidence for confirmed match, confirmed non-match and insufficient-data application outcomes while keeping BoatDesign/configuration truth separate from concrete PhysicalBoat/listing truth.

The accepted technical native Search criteria count remains `2`. SLICE-0057 adds no criterion: it re-evaluates one buyer-selected replacement value for an already active accepted criterion through the same Search truth, in one coherent comparison snapshot, and exposes only factual set-difference counts plus the backend-owned canonical alternative Search path. SLICE-0058 likewise adds no Search criterion: it records explicit buyer interest locally by stable `NativeListingId` and re-resolves current public listing truth when viewed. SLICE-0059 adds no Search criterion: it uses that existing explicit Shortlist as the whole Compare set and re-resolves current public listing/PhysicalBoat claim truth into a factual side-by-side matrix without score, winner, recommendation or hidden weighting. SLICE-0060 adds no Search criterion: it is a private professional Organization inventory projection over accepted NativeListing truth. SLICE-0061 likewise adds no Search criterion: it is private Organization-owned pre-market draft authoring state and has no Search/public promotion path. Any future criterion #3+ readiness is subject to the accepted third-copy abstraction guard in `docs/governance/POST_0051_TRIGGER_GATES.md`.

## Post-SLICE-0051 trigger gates

Canonical records remain `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md` and `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`.

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

SLICE-0061 used internal/synthetic retained proof and introduced no real external marketplace production data, broker self-service pilot, production pilot or public production launch. The Production Readiness gate therefore remains untriggered after acceptance. The mandatory post-0056 workflow reassessment remains `PASS`; SLICE-0061 acceptance does not alter that gate. Before real external marketplace inventory is exposed to external buyers, the accepted PostgreSQL HA/production-readiness rules remain mandatory.

## Broker Mandatory Capability Register

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING
SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED
SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS: NOT_REACHED
POST_PILOT_REAL_BROKER_VALIDATION_STATUS: NOT_STARTED

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

SLICE-0061 changes none of these statuses and waives no professional-product obligation. It adds a safe Organization-owned private professional draft foundation; REQ-BROKER-023 branding and REQ-BROKER-024 connectivity-resilient draft recovery remain PENDING, and the Broker Workspace Launch Gate remains NOT_READY.

## Architecture and production direction

Current accepted application direction remains Astro as primary web framework with React only for justified interactive islands, FastAPI as sole application/domain API boundary, PostgreSQL 18 production target in DigitalOcean FRA1, Auth0 Public Cloud EU as authentication-only, and immutable container deployment through GHCR/versioned Docker Compose. Production app hosts remain stateless/replaceable; independent encrypted backup plus restore testing remains required.

The SLICE-0053 same-host session-topology invariant remains in force for browser-visible FastAPI auth/callback and authenticated Astro workspace surfaces. SLICE-0054 reuses this session boundary rather than creating a second authentication stack.

## Post-0054 buyer/seller reconciliation

`docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md` records the accepted optional Buyer Requirements/Decision Tools direction and shared Seller Platform direction. Direct Search remains primary; Buyer Requirements remain optional; `UNKNOWN != NOT_SATISFIED`; no match scores/winners/hidden weights are authorized. SLICE-0058 implements the bounded anonymous/local form of one ordinary personal Shortlist, and SLICE-0059 adds a factual whole-Shortlist Compare over current public truth while preserving the invariant that shortlist membership is buyer interest rather than HullQ fit.

## What remains unbuilt

Important future work includes owner-direct marketplace admission/publication and trust escalation; representation-conflict handling; seller-choice/broker referral; professional draft-to-marketplace promotion/publication and media; leads/CRM/outcomes/analytics; export/bulk onboarding; buyer-facing Search explainability beyond the accepted one-change sensitivity capability; BuyerRequirements persistence; persistent/account Shortlist continuity and anonymous-to-account migration; sharing and persisted Compare subset/reorder; Rare Match and comparable-vessel semantics; Saved Search/alerts/price history; independent vessel-claim verification; production operations; broader SEO; payment/subscription enforcement; and any future transaction/escrow integration.

SLICE-0063 is owner-accepted and merged. It adds bounded human-readable public identity to the existing authoritative MarketplaceOrganization publishing principal and surfaces that identity consistently in Broker Workspace and public NativeListing presentation. REQ-BROKER-023 and REQ-BROKER-024 are both implemented. This satisfies the two addendum launch/pilot-baseline commitment statuses but does not by itself make the Broker Workspace Launch Gate PASS; the remaining launch-gate capability/evidence checklist stays controlling.

## Next capability selection

Next queue number:

```text
SLICE-0064
```

**Selected capability:** Professional Draft Publication Readiness.

Selection record: `docs/POST_SLICE_0063_REASSESSMENT_2026-09-22.md`.

Readiness artifact: `docs/slices/SLICE-0064-professional-draft-publication-readiness.md`.

Normative bounded contract: `specs/PROFESSIONAL_PUBLICATION_READINESS_CONTRACT.v0.1.md`.

The capability adds the missing professional `listing_offer.broker_description`, extends the bounded PhysicalBoat broker-claim model to the already-accepted `physical_boat.boat_name`, and produces one deterministic server-side READY/BLOCKED mapping of the current professional draft into candidate marketplace input values. It creates no marketplace identities/truth and exposes no Publish action.

Implementation remains unauthorized until the readiness package passes independent exact-head review, required remote gates and is merged to canonical `main`; only then may the Project Owner run `START_SLICE.bat`.

## Development workflow

- `origin/main` is canonical shared truth;
- one implementation slice per isolated worktree/branch;
- readiness/specification is independently reviewed and merged before implementation start;
- Project Owner runs `START_SLICE.bat` only after readiness is accepted;
- Claude Code implements; independent reviewer verifies exact implementation HEAD;
- material finding → amendment on the same branch;
- clean exact-head review → ACCEPT;
- explicit Project Owner acceptance is mandatory before implementation merge;
- acceptance closure follows implementation merge and advances `PROJECT_STATE_ACCEPTED_SLICE` atomically;
- `FINISH_SLICE.bat` closes the local slice only after remote closure is independently reviewed and merged;
- the next slice begins only after reassessment/readiness and uses a fresh Claude conversation;
- the mandatory post-SLICE-0056 workflow reassessment remains complete and `PASS`; SLICE-0064 Professional Draft Publication Readiness is selected/readied but may not start until independent readiness review/remote gates/readiness merge are complete.

For exact hashes, amendments, gate runs and review history, read the corresponding acceptance closure rather than expanding this file into a second historical log.
