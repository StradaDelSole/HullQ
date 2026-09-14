# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0052 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0053 -->

**Updated:** 2026-09-14  
**Latest owner-accepted / DONE slice:** SLICE-0052  
**Current queue:** SLICE-0053 — capability **not yet selected**; selection requires the normal post-slice product/architecture reassessment and repository reconciliation before readiness.  
**Exceptional historical state:** SLICE-0039 remains terminal `BLOCKED` and is not to be reopened.

This is the compact current-state entry point for HullQ. Historical implementation/review detail belongs in slice contracts, acceptance closures, retained research packages and Git history. Normative specs and accepted decisions remain authoritative where they apply.

## Product direction

HullQ is a native broker-first sailboat listing and technical-discovery marketplace.

Primary buyer loop:

```text
technical requirements
→ deterministic BoatDesign/configuration evaluation
→ native professional inventory
→ physical-boat/listing truth
→ save / monitor / alert
→ broker contact / qualified lead
```

Phase-1 public supply remains broker/dealer/eligible-professional only. Independent private FSBO remains out of scope; any later owner-to-broker referral path is separate future work.

Two core product surfaces now control prioritization:

```text
Buyer side
→ trustworthy technical discovery

Provider side
→ best-in-class Broker Workspace
```

## Broker Workspace — launch-critical direction

Owner-accepted direction on 2026-09-13 makes the professional Broker Workspace a core HullQ product surface, not an admin panel or optional later polish.

Controlling records:

```text
docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md
specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md
docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md
docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md
```

Core operating principle:

> A broker should never have to enter information twice, search for information HullQ already knows, or wonder what happened to a lead.

The Broker Workspace must ultimately provide low-friction inventory creation/editing, safe reuse of known HullQ information without truth collapse, practical media operations, clear publication/freshness/commercial/sale state separation, explicit sale/outcome handling, durable first-class leads, source/campaign/Search attribution, assignment/follow-up workflow, response/performance analytics, portability/no lock-in and later triggered differentiators such as Search explainability and privacy-safe demand insight.

Current hard gate state remains:

```text
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

No real external broker self-service production pilot, paid broker activation or broad public production launch may bypass the accepted launch-gate rules.

Every normal post-slice capability reassessment must inspect the Mandatory Capability Register before selecting the next primary capability. `PENDING` does not mean optional; any `DUE` commitment must be explicitly accounted for and may be deferred only with recorded rationale.

## Current architecture and precedence

`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` is the accepted post-SLICE-0039 architecture direction. `architecture/SYSTEM_ARCHITECTURE.md` is the current architecture snapshot. Older ADR-0010 / application-stack-baseline text remains historical where superseded.

Current application/production direction:

```text
Cloudflare edge
      |
      v
replaceable Linux app host / Caddy
      |
      +-- Astro + TypeScript web
      |     \-- React islands where justified
      +-- FastAPI / CPython 3.14
      +-- scheduled/background Python worker when justified
      |
      v
DigitalOcean Managed PostgreSQL 18 / FRA1
```

Accepted boundaries:

- FastAPI is the sole application/domain API boundary; Astro must not access PostgreSQL directly or become a second semantic Search/domain implementation;
- Auth0 Public Cloud EU is authentication-only; HullQ owns Account IDs, Organizations, Memberships, roles, listing ownership, verification and authorization in PostgreSQL/domain state;
- privileged broker publishing requires MFA, preferably passkeys/WebAuthn, with step-up for high-risk actions when those actions exist;
- deployment uses CI-verified immutable Docker images, GHCR, versioned Docker Compose and controlled deploy/health-check/rollback; no initial Coolify/Dokploy control plane;
- production application hosts are stateless/replaceable with respect to canonical application data;
- independent encrypted backup plus tested restore is required in addition to provider DB backup;
- before real broker inventory is exposed to real external buyers, production PostgreSQL must have automatic failover with at least one standby.

Do not introduce a second business-logic backend, dedicated external Search engine, Kubernetes/distributed infrastructure or other operational layer without measured need and an accepted decision.

## Hard truth and identity boundaries

Accepted marketplace identity boundary:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

Relationships:

```text
PhysicalBoat → optional BoatDesignRef
MarketEpisode → PhysicalBoatId
NativeListing → optional MarketEpisodeId
ExternalMarketObservation → optional MarketEpisodeId
```

Hard truth rule:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

A design/configuration can establish technical eligibility without establishing a fact about one offered yacht. No BoatDesign value becomes individual-yacht truth merely because a PhysicalBoat references that design.

## What is already built and accepted

The repository has accepted, tested foundations/product verticals for:

- canonical sailboat identity/data contracts and PostgreSQL persistence;
- deterministic technical normalization/Search behavior and provenance boundaries;
- source-rights gating and retained research/reproducibility paths;
- marketplace identity and strict design-vs-concrete-boat truth separation (SLICE-0040);
- Account / Organization / Membership professional publishing eligibility (SLICE-0041);
- Alembic as the sole forward migration path (SLICE-0042);
- durable immutable NativeListing identity persistence (SLICE-0043);
- Gate-1 marketplace fact/claim semantics and bounded field registry (SLICE-0044);
- durable revisioned NativeListing offer-fact persistence for the nine `LISTING_OFFER` fields (SLICE-0045);
- durable PhysicalBoat identity persistence with optional validated canonical `BoatDesignRef` (SLICE-0046);
- durable MarketEpisode identity and NativeListing→MarketEpisode linkage (SLICE-0047);
- first browser-visible real listing preview vertical (SLICE-0048);
- first production-public NativeListing lifecycle/read/page vertical (SLICE-0049);
- first buyer-critical concrete PhysicalBoat truth vertical with exactly seven broker-declared fields and no BoatDesign fallback (SLICE-0050);
- first production buyer-facing Requirements → Native Inventory Search vertical over exactly `draft_max` plus bounded production FieldResolution persistence (SLICE-0051);
- evidence-backed NativeListing freshness/reconfirmation with 30-day TTL + 7-day grace, buyer-surface suppression of STALE/UNKNOWN inventory and authorized immutable reconfirmation (SLICE-0052).

Acceptance closures:

```text
docs/slices/SLICE-0051-acceptance-closure.md
docs/slices/SLICE-0052-acceptance-closure.md
```

## NativeListing lifecycle and freshness

Public lifecycle remains intentionally:

```text
DRAFT → ACTIVE → WITHDRAWN
```

Republish, `SOLD` and `ARCHIVED` remain future lifecycle capabilities.

Freshness is now separately implemented and accepted under `MANUAL_NATIVE_V1`:

```text
confirmation TTL = 30 days
grace period     = 7 days

CONFIRMED
DUE_FOR_CONFIRMATION
STALE
UNKNOWN
```

Initial confirmation evidence is the immutable successful `DRAFT → ACTIVE` publication transition timestamp. Later reconfirmation is an explicit authorized immutable event with database/system timestamp and stable retry-safe `FreshnessConfirmationId`.

Current buyer eligibility is:

```text
ACTIVE + CONFIRMED/DUE_FOR_CONFIRMATION
→ current buyer eligible

ACTIVE + STALE/UNKNOWN
→ suppressed from current listing/Search surfaces
→ lifecycle remains ACTIVE
→ never inferred SOLD/WITHDRAWN
```

No scheduler is required merely to advance freshness with elapsed time; status is derived from immutable evidence plus explicit evaluation time.

The public listing and Search projection carry `freshness_status` and `last_confirmed_at`. Buyer-facing freshness wording uses `last_confirmed_at`; `offer_recorded_at` remains only the LISTING_OFFER revision-recorded timestamp.

## Accepted technical Search result

SLICE-0051 still defines exactly one public hard technical buyer requirement:

```text
draft_max=<exact decimal metres>
```

Public routes:

```text
/en/search
/de/search
/fr/search
/pt/search
/es/search
```

Production path:

```text
buyer draft_max
→ exact Decimal request parsing/canonicalization
→ qualified deterministic BoatDesign/configuration Search
→ ACTIVE native professional inventory
→ freshness admission
→ NativeListing → MarketEpisode → PhysicalBoat
→ publishing Organization's current physical_boat.draft claim
→ same-PhysicalBoat current-observation contradiction guard
→ CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA
→ buyer-visible Search result
→ /listings/{NativeListingId}
```

Only `CONFIRMED_MATCH` is returned in the primary result surface. Insufficient/conflicting technical data is separate and never presented as a match. STALE/UNKNOWN inventory is excluded before technical classification and therefore is not counted as technical insufficient data.

A raw value merely present in canonical BoatDesign JSON is not confirmed Search truth. The bounded design/configuration path requires admissible active FieldResolution plus exact canonical-value agreement and accepted production-use evidence/source rights.

SLICE-0052 adds no second technical Search criterion.

## Post-SLICE-0051 trigger gates

Canonical records:

```text
docs/governance/POST_0051_TRIGGER_GATES.md
docs/governance/PRODUCTION_READINESS_GATE.md
docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md
```

Current trigger state:

```text
architecture/current-state reconciliation: PASS
accepted technical native Search criteria: 1 (draft_max)
workflow reassessment: NOT_DUE; mandatory after SLICE-0056 or before first real production pilot, whichever comes first
production readiness: NOT_TRIGGERED
external broker production data: NOT_PRESENT
production pilot: NOT_STARTED
public production launch: NOT_STARTED
broker workspace launch gate: NOT_READY
```

From SLICE-0052 onward every primary readiness contract must contain `**TRIGGER GATES CHECK:** PASS` and the machine-checked `## Trigger gates` evidence section.

Technical Search expansion rule:

```text
criterion #1 -> concrete path proved by SLICE-0051
criterion #2 -> mandatory explicit comparison with the 0051 bridge/path
criterion #3+ -> no third structural copy without PASS abstraction guard
```

Production-readiness rule:

```text
first real external broker data stored/relied upon as HullQ production data
OR first real external production pilot
OR public production launch
→ PRODUCTION_READINESS_GATE_STATUS MUST be PASS
```

The older HA minimum remains separately hard before real broker inventory is exposed to real external buyers.

## Broker mandatory commitments after SLICE-0052

The accepted Mandatory Capability Register remains open. Current high-level state remains:

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

Trigger-specific requirements in the register remain controlling. In particular, first external broker pilot, scaled onboarding, paid activation and broad public launch each have explicit prerequisite relationships that may not be bypassed.

## What is not built yet

Important remaining marketplace/product capabilities include:

- launch-grade Broker Workspace capabilities required by the accepted direction/register, including authenticated self-service, low-friction inventory workflow, media operations, commercial/sale outcomes, durable leads, attribution, lead workflow and broker analytics;
- persisted marketplace actor directory beyond accepted runtime eligibility types;
- PhysicalBoat marketplace fact coverage beyond the seven accepted SLICE-0050 fields, including broader field-specific verification/resolution;
- broader multi-criterion native-inventory Search and any ranking/recommendation layer beyond the bounded deterministic `draft_max` surface;
- Saved Search persistence, monitoring/alerts and price-history intelligence;
- independent verification of broker claims;
- broad/global canonical-field resolution/backfill;
- payment/subscription implementation and entitlement enforcement for future paid broker/buyer plans;
- production deployment/operations capabilities required to make the Production Readiness Gate PASS;
- full listing/Search SEO indexation, faceted landing-page taxonomy, sitemap/hreflang expansion and broad structured-data strategy beyond current noindex page classes.

These items are not automatically assigned to SLICE-0053. The next capability must be selected through reassessment and repository reconciliation. Broker commitments recorded as mandatory may not be silently dropped.

## Search and SEO boundary

Search architecture and SEO remain product architecture, not later marketing.

Stable public listing route:

```text
/listings/{NativeListingId}
```

Current public listing/Search page classes remain deliberately `noindex`. Arbitrary facet paths, indexable Search-result combinations, Search sitemap publication and broad structured-data expansion are not yet authorized.

Mandatory public languages remain English, German, French, Portuguese and Spanish. Canonical IDs, technical values, provenance and Search semantics remain language-neutral.

## Monetization direction

Search remains broadly open; persistence, monitoring and intelligence remain preferred monetization surfaces.

Current framing remains:

```text
HullQ Free — Search everything. Save 5 searches.
```

Potential Pro surfaces include expanded saved searches, monitoring/alerts and, where rights/data permit, listing price history, price-change alerts, model/generation/configuration market trends, Days-on-Market and price-reduction signals.

No paid broker plan may be activated while the Broker Workspace launch/mandatory prerequisite gates remain unsatisfied.

## Execution checkpoint

Completed product threshold remains:

```text
PERSISTED REAL LISTING
→ PRODUCTION PUBLIC LISTING
→ CONCRETE-YACHT BROKER TRUTH
→ FIRST PRODUCTION BUYER TECHNICAL SEARCH
→ EVIDENCE-BACKED CURRENT-INVENTORY FRESHNESS
= BUILT THROUGH SLICE-0052
```

Current queue only:

```text
SLICE-0053
= capability NOT YET SELECTED
```

Before selecting SLICE-0053, perform the normal post-SLICE-0052 product/architecture reassessment, reconcile actual repository state, inspect all trigger gates and explicitly inspect `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`.

Do not run `START_SLICE.bat` for 0053 until capability selection/readiness has passed the required review/merge workflow. `START_SLICE.bat` remains the sole initial Claude implementation prompt.

## Development workflow

- `origin/main` is canonical shared truth;
- one implementation slice per isolated worktree/branch;
- Claude Code implements; independent reviewer verifies exact implementation HEAD;
- material finding → `AMEND` on the same branch;
- clean exact-head review → `ACCEPT`;
- explicit Project Owner acceptance is mandatory before implementation merge;
- acceptance closure follows implementation merge and advances `PROJECT_STATE_ACCEPTED_SLICE` atomically;
- `FINISH_SLICE.bat` closes the local slice only after remote closure is reviewed and merged;
- the next slice starts only after post-slice reassessment/readiness and uses a fresh Claude conversation;
- workflow overhead reassessment becomes mandatory after accepted SLICE-0056 or before an earlier real production pilot, whichever comes first.

For exact hashes, amendments, gate runs and review history, read the corresponding slice acceptance closure rather than expanding this file into a second historical log.
