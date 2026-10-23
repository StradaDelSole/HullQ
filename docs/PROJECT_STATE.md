# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0088 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0089 -->
<!-- PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED -->

**Updated:** 2026-10-23  
**Latest owner-accepted / DONE slice:** SLICE-0088  
**Current queue:** SLICE-0089 — **UNSELECTED / NOT READY**. Owner-accepted SLICE-0088 Broker Inventory Portability Export is completed through independently reviewed code, all-green exact-HEAD CI/manufacturer, implementation PR #368 merge `4cb5ec3ca03190575df1f8e753668c89d6d597f4`, and the separate acceptance closure `docs/slices/SLICE-0088-acceptance-closure.md`. Its seven supported outbound formats are CSV, TSV, XLSX, XLS, ODS, JSON and pinned NautiX 1.4 XML; XLSB export is deferred under issue #362, while inbound XLSB from SLICE-0083 remains. `REQ-BROKER-022`/`MVP-BROKER-009` are IMPLEMENTED within this scope. No external portal feeds, real external broker upload, pilot, production deploy, or public launch authorized. Search retains nine hard technical dimensions; Production Readiness IN_PROGRESS, Launch Pack NOT_STARTED. Owner-local `FINISH_SLICE.bat 0088` remains PENDING until this closure PR is merged.

**Pre-0088 external code-review triage (2026-10-16):** Owner-supplied Claude v0.3 dump review was independently checked against current `origin/main`; primary operational concerns are single-worker async-import synchronous parsing/DB, ZIP decompression resource limits, trusted proxy/client-IP, bounded DB/concurrent rate limiting, supervised import retention and lead notification work, broker onboarding and scaled Search. Explicit code-vs-inference classifications and answers to five technical questions: `docs/POST_SLICE_0087_EXTERNAL_CODE_REVIEW_RECONCILIATION_2026-10-16.md`, issue #355. **Pre-external-broker-upload / pre-pilot safety evidence NOT YET PASS**; the `docs/operations/PRODUCTION_LAUNCH_CHECKLIST.md` now points to it. **At this historical pre-implementation point SLICE-0088 was selected for eight formats (the subsequent Owner-accepted writer-feasibility amendment limits output to seven);** its READY contract has been tightened so the new exporter cannot repeat a single-worker blocking event loop, but the separate existing-import hardening is NOT silently smuggled into 0088. No change to already accepted or launch markers.

**Boats Group/YachtWorld feature utilization directive:** Each studied external brokerage, reporting, optimizer, trust, lead, market, portal syndication, referral, co-brokerage, transaction, messaging, website and financing capability is inventoried with its existing HullQ status, Owner-directed adoption/conditional/rejection disposition, trigger and acceptance boundary under `docs/governance/BOATS_GROUP_COMPETITIVE_CAPABILITY_REGISTER_2026-10-16.md` (issue #356; separate #357 reporting, #358 optimizer, #359 contracted portal profiles). This is a maintained roadmap **not a claim of implemented feature parity**. YachtWorld/BoatWizard provider agreements, licensed datasets, user consent/legal obligations and the prohibition of paid organic search influence remain binding. No SLICE-0089 selected.

**Exceptional historical state:** SLICE-0039 remains terminal `BLOCKED` and is not to be reopened.

This is the compact current-state entry point for HullQ. Historical implementation/review detail belongs in slice contracts, acceptance closures, retained research packages and Git history. Normative specs and accepted decisions remain authoritative where they apply.

**Owner direction supersession (2026-10-22/23):** Owner accepted a **joint Sail+Power** native marketplace with **independent, equally trustworthy specialist technical searches** for both categories, Sail first only as internal reference, **no external Sail-only/C-light market release or broker product pilot**. This supersedes historical Sail-only target scope without altering the nine accepted Sail hard criteria, code, real-data STOP gates or explicit future slice/Owner governance. Canonical [decision](HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md), Owner tracking [#366](https://github.com/StradaDelSole/HullQ/issues/366), and **post-0088 source-checked claim/category implementation tracker** [#372](https://github.com/StradaDelSole/HullQ/issues/372) / [reconciliation](POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md). The reconciled Sail+Power decision has not implemented Power Technical Search. Mandatory prior broker reporting #357 and pre-external-upload STOP #355 remain independent.

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

SLICE-0064 adds the accepted broker-facing lifecycle/freshness controls for already-existing Organization-owned NativeListings. Authorized professional publishers can Publish complete DRAFT listings through the existing DRAFT→ACTIVE transition, Withdraw ACTIVE listings through ACTIVE→WITHDRAWN, and Reconfirm ACTIVE freshness with retry-safe operation identity. Foreign/unknown listings remain non-enumerating, MFA/publishing-denial/service failures remain visibly distinct, every action re-reads authoritative server state, and WITHDRAWN exposes no republish path. The slice creates no NativeListing, does not promote ProfessionalListingDraft state, edits no offer, adds no lifecycle state and does not change Search/public eligibility semantics.

SLICE-0065 closes two publication-input shape gaps without creating marketplace truth. ProfessionalListingDraft now stores professional-only `listing_offer.broker_description` outside the shared nine-key owner-direct/professional common payload, including durable reopen and bounded local recovery, while OwnerDirectListingDraft remains unchanged. The existing PhysicalBoat claim revision/head model now carries optional `physical_boat.boat_name` with VALUE_ASSERTION / ABSENT / UNKNOWN semantics and omission kept distinct; historic pre-0065 exact retries remain idempotent when boat_name is omitted. Boat name remains PhysicalBoat DISPLAY_ONLY truth, not BoatDesign/Search truth. No draft promotion, NativeListing creation/publication, offer editing, media, leads, outcomes, analytics, import/export or Search change occurs.

SLICE-0066 closes the remaining shared draft required-response gap for `physical_boat.build_year`. Owner-direct and professional drafts now preserve OMITTED, explicit UNKNOWN and VALUE_ASSERTION(year) as mechanically distinct states under the same existing nine-key common payload. Historical bare-integer input remains compatible and canonical serialization/readback is structured. Both browser editors use one strict build-year form parser; invalid Known-year/mode submissions fail with visible invalid-save state and zero mutation. Professional local recovery preserves the bounded assertion-kind control and rejects malformed assertion-kind values fail-closed. No schema migration, promotion, marketplace fact creation, publication or Search change occurs.

SLICE-0067 adds the accepted fresh-identity professional promotion path. An authorized, promotion-ready Organization-owned ProfessionalListingDraft can atomically mint a fresh PhysicalBoat, MarketEpisode and lifecycle-DRAFT NativeListing, write the initial Organization PhysicalBoat claim and NativeListing offer, and freeze the source draft as PROMOTED with immutable NativeListing provenance in one PostgreSQL transaction. Exact-version retry is idempotent, D09 Organization+resolved-episode uniqueness is database-enforced, and browser recovery is deterministically cleared only after successful promotion. The resulting listing remains DRAFT/not public; existing-boat reconciliation and publication remain deferred.

SLICE-0068 adds the accepted Organization-controlled mixed-media gallery for existing NativeListings: private original/quarantine image storage, safely processed derivatives, provenance/rights state, durable MediaAsset/MediaPlacement ordering and explicit cover, same-Organization reuse, structured YouTube references, bounded streaming broker uploads, ACTIVE-listing media protection and race-safe retirement/reuse/cover locking. Cloudflare R2 Standard is the initial primary media store behind HullQ's S3-compatible boundary.

SLICE-0069 adds canonical D22 PublicationReadiness and D29 CurrentPublicEligibility. Broker Workspace preflight and authoritative publish-time re-evaluation now share one readiness authority; DRAFT→ACTIVE publication consumes current Organization eligibility, episode/PhysicalBoat chain, current offer, current PhysicalBoat claim and accepted media/cover truth. Buyer/public exact-listing and both accepted Direct Search paths reuse one current-public eligibility authority, so ACTIVE alone no longer implies current-market visibility. Suppression does not rewrite lifecycle. Public listings now expose the accepted bounded IMAGE/YOUTUBE gallery with listing-scoped processed-derivative delivery; private originals/object-storage identity remain hidden. Technical Search criteria remain exactly 2.

SLICE-0082 adds the accepted post-promotion broker first-time canonical BoatDesign association to the existing Organization-controlled inventory editor, closing the source-to-technical-Search gap identified after SLICE-0081. A broker can inspect bounded canonical design candidates (including recorded generation and aliases), explicitly confirm one existing identity and persist a first NULL→BoatDesignRef PhysicalBoat link plus one durable audit event in the same PostgreSQL transaction. Organization/Membership/PUBLISHER authorization and listing→episode→boat ownership are revalidated under transaction locks; no cross-Organization shared PhysicalBoat unilateral linking, fuzzy model inference, existing-link correction or copy of design facts into concrete physical-yacht truth is permitted. Normal broker-created eligible NativeListings can now qualify for existing **two-criterion** buyer technical Search when existing current-public and concrete claim/design evidence warrants it. Owner acceptance and exact review/CI evidence reside in `docs/slices/SLICE-0082-acceptance-closure.md`.

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
→ SLICE-0063 publishing Organization public identity
→ SLICE-0064 professional inventory lifecycle controls
→ SLICE-0065 professional publication input alignment
→ SLICE-0066 required-response / assertion input alignment
→ SLICE-0067 professional draft → atomic marketplace promotion
→ SLICE-0068 broker mixed-media gallery
→ SLICE-0069 canonical publication readiness + current public eligibility
→ SLICE-0070 durable buyer contact / Lead creation
→ SLICE-0071 Broker Lead Operating Surface + Durable Email Notification
→ SLICE-0072 Professional Inventory Editing & Maintenance
→ SLICE-0073 Test / CI Throughput Optimization
→ SLICE-0074 Broker Sale / Outcome Close-out
→ SLICE-0075 Broker Performance & Funnel Snapshot
→ SLICE-0076 Broker Workspace Launch Validation: Usability & Competitive Benchmark
→ SLICE-0077 Broker Lead Assignment Discoverability Remediation
→ SLICE-0078 Holistic Security Hardening & Adversarial Validation
→ SLICE-0079 Production Readiness & External Broker Pilot Foundation
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
docs/slices/SLICE-0063-acceptance-closure.md
docs/slices/SLICE-0064-acceptance-closure.md
docs/slices/SLICE-0065-acceptance-closure.md
docs/slices/SLICE-0066-acceptance-closure.md
docs/slices/SLICE-0067-acceptance-closure.md
docs/slices/SLICE-0072-acceptance-closure.md
docs/slices/SLICE-0073-acceptance-closure.md
docs/slices/SLICE-0074-acceptance-closure.md
docs/slices/SLICE-0075-acceptance-closure.md
docs/slices/SLICE-0076-acceptance-closure.md
docs/slices/SLICE-0077-acceptance-closure.md
docs/slices/SLICE-0078-acceptance-closure.md
docs/slices/SLICE-0079-acceptance-closure.md
```

## Accepted technical Search result

HullQ has exactly **nine** Owner-accepted native public hard technical Search dimensions through SLICE-0087, counting semantic dimensions rather than URL parameter keys:

```text
1 — draft_max (maximum draft, positive SI metres)
2 — keel_configuration (accepted public positive keel taxonomy)
3 — loa (loa_min and/or loa_max inclusive, ONE range dimension)
4 — rudder_configuration (qualified SKEG_HUNG/TRANSOM_HUNG/SPADE/TWIN)
5 — hull_configuration (MONOHULL/CATAMARAN/TRIMARAN)
6 — cockpit_position (AFT/CENTER/FORWARD/MULTIPLE)
7 — deck_saloon (DECK_SALOON/PILOTHOUSE)
8 — beam (beam_min and/or beam_max inclusive, ONE range dimension)
9 — hull_material (GRP_FIBERGLASS/STEEL/ALUMINUM/WOOD)
```

SLICE-0085 added qualified LOA and rudder; SLICE-0086 added independent first-level hull/cockpit/deck facets; Owner-accepted SLICE-0087 added bounded exact overall beam and conservative hull-material search. **Eleven technical public URL keys are nine dimensions**: LOA min/max and Beam min/max each count as ONE. All are combinable via the one accepted static typed `CriterionDefinition` + FieldResolution/NamedVariant same-configuration MUST/AND query and independently asserted current nonconflicting PhysicalBoat actual claims. No import/advertisement/photo or design-only fact manufactures actual seller claims. Omission, explicit UNKNOWN and truthful known-OTHER remain distinct. Existing D29 public eligibility, authorized private illustrative MFA/PUBLISHER DRAFT Broker Search-fit, canonical five-locale URLs, actual-vs-qualified-design evidence and organic Search commercial independence remain unchanged.

SLICE-0087's actual PhysicalBoat `hull_material` claim also truthfully admits FERROCEMENT, CARBON_COMPOSITE and OTHER, but these are NOT public positive Search filter values, nor are unproved design `wood_composite`/carbon synonyms inferred. `LONG_KEEL` is still public Search **UNSUPPORTED** without further evidence-backed taxonomy proof; public `OTHER`/deck `NONE` remains unsupported. Buyer sensitivity still only applies to the original draft/keel-only forms; with LOA, rudder, structural, beam or material criteria active it is explicitly unavailable rather than silently dropping hard requirements. Old-revision exact retry semantics and cross-Organization conflicts fail closed. See `docs/slices/SLICE-0085-acceptance-closure.md`, `SLICE-0086-acceptance-closure.md` and `SLICE-0087-acceptance-closure.md`.

The `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` advances **7 → 9 in the separately reviewed Owner-accepted SLICE-0087 closure**; the common no-third-copy abstraction and owner-direct Search ranking invariants remain binding under `docs/governance/POST_0051_TRIGGER_GATES.md`.

The canonical Gate/Production state remains:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: PASS
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

## Security hardening direction

The dedicated holistic security hardening and adversarial-validation pass required before the first real external broker self-service pilot is owner-accepted and complete through SLICE-0078.

Canonical gate:

```text
docs/governance/SECURITY_HARDENING_GATE.md
```

The accepted gate required threat-model coverage, cross-tenant/auth/MFA/media/privacy/supply-chain/deployment adversarial testing, retained proof, independent exact-head review and explicit Project Owner acceptance. SLICE-0078 satisfied that gate. SEC-0078-07 is retained as an explicit Owner-risk-accepted currently-unreachable upstream advisory with mandatory re-review triggers.

## Post-SLICE-0051 trigger gates

Canonical records remain `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md` and `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`.

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: PASS
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

SLICE-0079 is owner-accepted and merged. It implements and locally proves the repository-owned production deployment, rollback, recoverability, observability and release mechanisms. Canonical-main Deploy run #28 (`37868264887`) subsequently real-executed API/web GHCR publication successfully, closing that provider-observation gap. SLICE-0080 is also Owner-accepted and merged: broker-uploaded original/source media now has a truthful synchronous independent-copy mechanism using primary Cloudflare R2 plus Backblaze B2 EU Central before durable MediaAsset redundancy truth may commit. The Production Readiness gate remains `IN_PROGRESS` because the real B2 account/bucket/key and live proof, VPS/database/R2/alert/deploy-secret and later exposure-specific provider evidence are still incomplete. No real external marketplace production data, broker self-service pilot, production pilot or public launch has started. Before real external marketplace inventory is exposed to external buyers, the accepted PostgreSQL HA rule remains mandatory.

## Broker Mandatory Capability Register

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: IMPLEMENTED
SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED
SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS: NOT_REACHED
POST_PILOT_REAL_BROKER_VALIDATION_STATUS: NOT_STARTED

REQ_BROKER_022_STATUS: IMPLEMENTED
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
REQ_BROKER_025_STATUS: PENDING
REQ_BROKER_026_STATUS: IMPLEMENTED
REQ_BROKER_027_STATUS: IMPLEMENTED
REQ_BROKER_028_STATUS: PENDING
REQ_BROKER_029_STATUS: PENDING
REQ_BROKER_030_STATUS: IMPLEMENTED
```

REQ-BROKER-023 and REQ-BROKER-024 were implemented by accepted SLICE-0063 and SLICE-0062. SLICE-0066 historically changed none of the REQ-BROKER-022…030 status markers; SLICE-0076/0077 subsequently closed the Broker Workspace Launch Gate at PASS. SLICE-0083 implemented REQ-BROKER-027 private multi-format intake; SLICE-0084 implemented REQ-BROKER-026 pre-publication Search-fit. The remaining mandatory export, reports, search-volume-triggered insights and production/trust commitments remain OPEN; a passed Broker Workspace Launch Gate does not authorize external production or make the full broker product COMPLETE.

## Architecture and production direction

Current accepted application direction remains Astro as primary web framework with React only for justified interactive islands, FastAPI as sole application/domain API boundary, PostgreSQL 18 production target at PlanetScale per accepted ADR-0012 (verified EU region and sizing required before purchase), Auth0 Public Cloud EU as authentication-only, and immutable container deployment through GHCR/versioned Docker Compose. Production app hosts remain stateless/replaceable; independent encrypted backup plus restore testing remains required.

The SLICE-0053 same-host session-topology invariant remains in force for browser-visible FastAPI auth/callback and authenticated Astro workspace surfaces. SLICE-0054 reuses this session boundary rather than creating a second authentication stack.

## Post-0054 buyer/seller reconciliation

`docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md` records the accepted optional Buyer Requirements/Decision Tools direction and shared Seller Platform direction. Direct Search remains primary; Buyer Requirements remain optional; `UNKNOWN != NOT_SATISFIED`; no match scores/winners/hidden weights are authorized. SLICE-0058 implements the bounded anonymous/local form of one ordinary personal Shortlist, and SLICE-0059 adds a factual whole-Shortlist Compare over current public truth while preserving the invariant that shortlist membership is buyer interest rather than HullQ fit.

## Help & Support direction

The Project Owner accepted **Zammad Hosted Professional v2** as HullQ's external commodity helpdesk / support platform. The controlling decision is:

```text
docs/HULLQ_HELP_SUPPORT_ZAMMAD_DECISION_2026-09-30.md
```

Zammad is intended for branded customer support, tickets/conversations, agent workflow and Help Center delivery. It is not HullQ marketplace, verification or Trust & Safety authority. Provisioning, privacy/retention configuration, branding validation, support integration and HullQ-native Trust & Safety linkage remain not yet implemented.

## Overall MVP completeness register

The Project Owner accepted the cross-cutting overall-MVP register:

```text
docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md
```

Every primary slice selected after SLICE-0072 must reconcile that register before readiness. The pre-pilot usability/competitive benchmark and the dedicated Security Hardening & Adversarial Validation gate are now accepted as complete. Remaining Overall MVP obligations continue to be governed by their existing triggers and readiness rules.

## What remains unbuilt

Important future work includes owner-direct marketplace admission/publication and trust escalation; representation-conflict handling; seller-choice/broker referral; production email-provider activation; buyer-contact email verification; periodic/broader broker analytics beyond the accepted factual SLICE-0075 snapshot; broker XLSB export (deferred, issue #362) and separately authorized third-party portal feeds; extension beyond the nine accepted qualified public technical Search dimensions (displacement/basis, rig, broader material classes and further safely proven facets; `LONG_KEEL` remains publicly unsupported pending its own evidence-backed taxonomy decision), plus buyer-facing Search explainability and sensitivity beyond the original draft/keel-only accepted one-change comparison; BuyerRequirements persistence; persistent/account Shortlist continuity and anonymous-to-account migration; sharing and persisted Compare subset/reorder; Rare Match and comparable-vessel semantics; Saved Search/alerts/price history; independent vessel-claim verification; production operations; broader SEO; payment/subscription enforcement; and any future transaction/escrow integration.

SLICE-0078 is owner-accepted and merged. The dedicated pre-pilot Security Hardening & Adversarial Validation gate is PASS after exact-head independent review, remediation of all reachable Critical/High findings, explicit Owner risk acceptance of SEC-0078-07, and successful CI/reproducibility. Broker Workspace Launch Gate is also PASS.

SLICE-0079 is owner-accepted and merged. The production-readiness mechanisms are implemented with all independent-review Findings A–P closed, but `PRODUCTION_READINESS_GATE_STATUS` remains `IN_PROGRESS` until the required real GHCR/VPS/Managed-PostgreSQL and other provider evidence is observed. No broker self-service pilot, paid plan, real external production data or public launch has started.

## Broker launch execution focus

The 2026-09-26 execution recalibration is recorded in:

```text
docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md
```

It does not reopen accepted SLICE-0067 or waive existing launch gates. It changes prioritization and slice-sizing discipline after the current capability:

```text
strict truth / auth / provenance stay fixed
+
micro-slicing is no longer a goal
+
vertical broker-launch progress becomes the default where risk permits
```

Post-0067 reassessment should strongly prefer the shortest safe path through media, canonical publication readiness/publish integration, durable buyer contact/leads, broker lead handling and inventory editing before unrelated product expansion, unless a higher-leverage blocker or triggered mandatory capability requires interruption.

The existing public NativeListing read path is already implemented; near-term work is to let normal broker-created inventory reach that path truthfully rather than to invent a second public-listing architecture.

Structured bulk/source import is implemented by Owner-accepted SLICE-0083 (REQ-BROKER-027/MVP-BROKER-011). Broker pre-publication Search-fit for a promoted lifecycle-DRAFT NativeListing was initially accepted in SLICE-0084 (REQ-BROKER-026/MVP-BROKER-010) with two technical hard criteria, extended by accepted SLICE-0085 to four, by accepted SLICE-0086 to seven and by Owner-accepted SLICE-0087 to all nine accepted public hard Search dimensions, within the same authorized synthetic-read-only and no-real-demand scope. Neither capability authorizes external broker production data or publication/eligibility bypass; broker export is now Owner-accepted as SLICE-0088; periodic reporting and production operation remain separately governed.

Large retained research artifacts are acknowledged as repository-hygiene debt, not a launch blocker. They remain in-repo for now because they support deterministic evidence replay/auditability; any later externalization must preserve immutable hashes, provenance and reproducibility.

## Next capability selection

Current queued slice:

```text
SLICE-0089 — UNSELECTED / NOT READY
```

**Completed SLICE-0088:** The Owner accepted the seven-format broker-owned inventory export on 2026-10-23. Implementation PR #368 merged as `4cb5ec3ca03190575df1f8e753668c89d6d597f4` after exact merged-head CI `40018867760`, manufacturer reproducibility `40018869140`, and independent technical review closure of the semaphore/cancellation race. Genuine CSV, TSV, XLSX, XLS, ODS, JSON and NautiX 1.4 XML output support select → per-row completeness/provenance/loss preview → confirmed bounded download; `XLSB` export remains deferred (issue #362). Its inbound parser from 0083 is unchanged. No direct push/feed, third-party platform acceptance or customer rollout is claimed.

**Remaining gates:** Production Readiness `IN_PROGRESS`, Launch Pack `NOT_STARTED`, the pre-external-broker-upload safety STOP tracked in issue #355, external provider/HA/backup/restore, the mandatory periodic broker engagement reports (`REQ-BROKER-028`), owner-direct trust/publication, buyer persistence/alerts and appropriate compliance remain separately open. No real external pilot or public Sail-only/Power-only launch is authorized. No SLICE-0089 implementation is preselected.

**Prior accepted state:** SLICE-0087 and the nine technical hard Search dimensions remain unchanged. The Owner has not yet run the local `FINISH_SLICE.bat 0088`; do not claim the local worktree is closed before its observed success.

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
- the mandatory post-SLICE-0056 workflow reassessment remains PASS; SLICE-0079 through SLICE-0088 are Owner-accepted with reviewed implementation and separate closure. Owner-local `FINISH_SLICE.bat 0088` must be performed only after this closure merges; its completion is not asserted. All real provider/data/pilot/launch gates remain unchanged; `LONG_KEEL` stays publicly unsupported and nine public technical Search dimensions remain accepted. No later slice starts automatically.

For exact hashes, amendments, gate runs and review history, read the corresponding acceptance closure rather than expanding this file into a second historical log.
