# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0056 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0057 -->

**Updated:** 2026-09-18  
**Latest owner-accepted / DONE slice:** SLICE-0056  
**Current queue:** SLICE-0057 — **Buyer Requirement Sensitivity**; readiness prepared on the accepted one-change factual sensitivity boundary. Implementation remains unauthorized until independent exact-head readiness review/CI and readiness merge to `main`.  
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

SLICE-0054 adds a separate pre-market identity:

```text
OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

Draft persistence is not marketplace truth. The accepted retained proof establishes that owner-direct draft operations do not create or mutate `physical_boats`, `market_episodes`, `native_listings`, NativeListing offer revision/head state, publication-transition state or freshness-confirmation state. No public Search promotion occurs.

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
```

Latest closures:

```text
docs/slices/SLICE-0052-acceptance-closure.md
docs/slices/SLICE-0053-acceptance-closure.md
docs/slices/SLICE-0054-acceptance-closure.md
docs/slices/SLICE-0055-acceptance-closure.md
docs/slices/SLICE-0056-acceptance-closure.md
```

## Accepted technical Search result

HullQ now has exactly two accepted/closed public hard technical native-inventory Search criteria:

```text
1 — draft_max=<exact positive decimal metres>
2 — keel_configuration=<canonical v0.1 value>
```

Accepted public `keel_configuration` values are exactly `FIN`, `FIN_WITH_BULB`, `WING`, `CENTERBOARD`, `LIFTING_KEEL` and `TWIN_KEEL`.

The two criteria may be evaluated alone or together as deterministic hard MUST/AND requirements. SLICE-0055 preserves typed criterion/configuration evidence for confirmed match, confirmed non-match and insufficient-data application outcomes while keeping BoatDesign/configuration truth separate from concrete PhysicalBoat/listing truth.

The accepted technical native Search criteria count is now `2`. Any future criterion #3+ readiness is subject to the accepted third-copy abstraction guard in `docs/governance/POST_0051_TRIGGER_GATES.md`.

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

SLICE-0056 used internal/synthetic retained proof and introduced no real external marketplace production data, production pilot or public production launch. The Production Readiness gate therefore remains untriggered after acceptance. The mandatory post-0056 workflow reassessment is complete and `PASS`; it does not select SLICE-0057. Before real external marketplace inventory is exposed to external buyers, the accepted PostgreSQL HA/production-readiness rules remain mandatory.

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

SLICE-0056 changes none of these statuses and waives no professional-product obligation. Broker Search-exclusion intelligence remains tied to REQ-BROKER-025 and its sufficient-Search-volume/privacy trigger; criterion-level evidence created by 0055 does not itself implement that broker feature.

## Architecture and production direction

Current accepted application direction remains Astro as primary web framework with React only for justified interactive islands, FastAPI as sole application/domain API boundary, PostgreSQL 18 production target in DigitalOcean FRA1, Auth0 Public Cloud EU as authentication-only, and immutable container deployment through GHCR/versioned Docker Compose. Production app hosts remain stateless/replaceable; independent encrypted backup plus restore testing remains required.

The SLICE-0053 same-host session-topology invariant remains in force for browser-visible FastAPI auth/callback and authenticated Astro workspace surfaces. SLICE-0054 reuses this session boundary rather than creating a second authentication stack.

## Post-0054 buyer/seller reconciliation

`docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md` records the accepted optional Buyer Requirements/Decision Tools direction and shared Seller Platform direction. Those ideas are not collapsed into SLICE-0055. Direct Search remains primary; Buyer Requirements remain optional; `UNKNOWN != NOT_SATISFIED`; no match scores/winners/hidden weights are authorized; shortlist remains buyer interest rather than HullQ fit.

## What remains unbuilt

Important future work includes owner-direct marketplace admission/publication and trust escalation; representation-conflict handling; seller-choice/broker referral; broker inventory workflow, branding/media and resilient drafts; leads/CRM/outcomes/analytics; export/bulk onboarding; buyer-facing Search explainability and sensitivity; BuyerRequirements persistence; shortlist/Compare/sharing; Rare Match and comparable-vessel semantics; Saved Search/alerts/price history; independent vessel-claim verification; production operations; broader SEO; payment/subscription enforcement; and any future transaction/escrow integration.

SLICE-0056 is now accepted. Post-SLICE-0056 reconciliation selects SLICE-0057 Buyer Requirement Sensitivity as the next bounded capability. No implementation is authorized until readiness is independently accepted and merged.

## Next capability selection

Next queue number:

```text
SLICE-0057
```

**Selected capability:** Buyer Requirement Sensitivity.

Selection record: `docs/POST_SLICE_0056_REASSESSMENT_2026-09-18.md`.

Readiness artifact: `docs/slices/SLICE-0057-buyer-requirement-sensitivity.md`.

Normative bounded contract: `specs/BUYER_REQUIREMENT_SENSITIVITY_CONTRACT.v0.1.md`.

The capability lets a buyer replace exactly one currently active `draft_max` or `keel_configuration` value with one buyer-supplied alternative and inspect the factual confirmed-result-set delta through the same accepted Search truth.

It adds no Search criterion, recommendation, persistence, account requirement or indexable Search URL class.

Implementation remains unauthorized until the readiness package passes independent exact-head review/CI and is merged to canonical `main`; only then may the Project Owner run `START_SLICE.bat`.

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
- the mandatory post-SLICE-0056 workflow reassessment is complete and `PASS`; SLICE-0057 still requires normal post-slice reconciliation/capability selection/readiness before `START_SLICE`.

For exact hashes, amendments, gate runs and review history, read the corresponding acceptance closure rather than expanding this file into a second historical log.
