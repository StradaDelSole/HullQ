# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0054 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0055 -->

**Updated:** 2026-09-17  
**Latest owner-accepted / DONE slice:** SLICE-0054  
**Current queue:** SLICE-0055 — **Second Technical Native Inventory Search Criterion: Keel Configuration + Multi-Criterion Evaluation Evidence**; readiness contract prepared, implementation not started.  
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

Direct technical Search remains the primary low-friction buyer entry point. The post-0054 accepted guided Buyer Requirements journey is optional and must reuse the same deterministic Search/evaluation semantics.

## Accepted provider surfaces

Professional provider direction remains the best-in-class Broker Workspace. SLICE-0053 provides its accepted authentication/account/Organization/Membership/role/MFA access boundary. Auth0 remains authentication-only; HullQ PostgreSQL/domain state owns authorization truth.

SLICE-0054 adds the first accepted owner-direct provider surface:

```text
authenticated ordinary HullQ Account
→ private OwnerDirectListingDraft
→ create / list / reopen / update own drafts
→ incomplete pre-market state may persist
→ NOT PUBLIC
```

An owner-direct Account does not require a professional Organization or Membership. Ownership is derived from the authenticated session/account, not client input. Draft persistence is private workspace state, not marketplace truth.

## Hard truth and identity boundaries

Accepted marketplace identity remains:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

Hard truth rule remains:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

SLICE-0054 adds:

```text
OwnerDirectListingDraftId != NativeListingId != PhysicalBoatId != MarketEpisodeId
```

## Owner-direct trust direction

Future normal publication baseline remains intentionally low-friction:

```text
HullQ account
+ verified phone reachability
+ explicit right-to-list attestation
+ baseline anti-abuse checks
```

Trust scopes remain separate: `PHONE VERIFIED`, `IDENTITY VERIFIED`, `RIGHT-TO-LIST ATTESTED`, `SALE AUTHORITY VERIFIED`. None promotes yacht technical fields. SLICE-0054 implements none of publication/admission, verification escalation, representation-conflict handling, media, enquiries, broker referral, sale outcome, Search eligibility/ranking, payments or production pilot.

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
```

Latest closures remain `docs/slices/SLICE-0051-acceptance-closure.md` through `SLICE-0054-acceptance-closure.md`.

## Accepted technical Search result

SLICE-0051 still defines exactly one **accepted/closed** public hard technical buyer requirement:

```text
draft_max=<exact decimal metres>
```

Accepted technical native Search criteria count remains `1` until SLICE-0055 is implemented, independently reviewed, owner-accepted and acceptance-closed.

SLICE-0055 is now selected to add criterion #2: bounded categorical `keel_configuration`, alone or AND-combined with `draft_max`, while preserving criterion-level evaluation evidence and satisfying the accepted second-criterion abstraction guard. Controlling readiness artifacts are `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md` and `docs/slices/SLICE-0055-second-technical-native-search-keel.md`.

## Post-SLICE-0051 trigger gates

Canonical records remain `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md` and `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`.

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 1
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: NOT_DUE

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

SLICE-0055 uses internal/synthetic retained proof and does not itself introduce external production seller/listing data or a production pilot. The Production Readiness gate therefore remains untriggered by readiness selection alone.

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

SLICE-0055 changes none of these statuses. Broker Search-exclusion intelligence remains tied to REQ-BROKER-025 and its sufficient-Search-volume/privacy trigger; criterion-level evidence created by 0055 does not itself implement that broker feature.

## Architecture and production direction

Current accepted application direction remains Astro as primary web framework with React only for justified interactive islands, FastAPI as sole application/domain API boundary, PostgreSQL 18 production target in DigitalOcean FRA1, Auth0 Public Cloud EU as authentication-only, and immutable container deployment through GHCR/versioned Docker Compose. Production app hosts remain stateless/replaceable; independent encrypted backup plus restore testing remains required.

## Post-0054 buyer/seller reconciliation

`docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md` records the accepted optional Buyer Requirements/Decision Tools direction and shared Seller Platform direction. Those ideas are not collapsed into SLICE-0055. Direct Search remains primary; Buyer Requirements remain optional; `UNKNOWN != NOT_SATISFIED`; no match scores/winners/hidden weights are authorized; shortlist remains buyer interest rather than HullQ fit.

## What remains unbuilt

Important future work includes owner-direct marketplace admission/publication and trust escalation; representation-conflict handling; seller-choice/broker referral; broker inventory workflow, branding/media and resilient drafts; leads/CRM/outcomes/analytics; export/bulk onboarding; buyer-facing Search explainability and sensitivity; BuyerRequirements persistence; shortlist/Compare/sharing; Rare Match and comparable-vessel semantics; Saved Search/alerts/price history; independent vessel-claim verification; production operations; broader SEO; payment/subscription enforcement; and future transaction/escrow integration.

None except the explicitly selected keel Search capability is allocated to SLICE-0055.

## Next capability selection

Next queue number:

```text
SLICE-0055
```

**Selected capability:** Second Technical Native Inventory Search Criterion — Keel Configuration + Multi-Criterion Evaluation Evidence.

Readiness must be independently reviewed and merged before the Project Owner runs `START_SLICE.bat`. Implementation has not started.

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
- workflow reassessment becomes mandatory after accepted SLICE-0056 or before an earlier real production pilot, whichever comes first.
