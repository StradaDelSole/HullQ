# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0053 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0054 -->

**Updated:** 2026-09-14  
**Latest owner-accepted / DONE slice:** SLICE-0053  
**Current queue:** SLICE-0054 — capability **not yet selected**; selection requires post-SLICE-0053 reassessment, repository reconciliation, trigger-gate inspection and Broker Workspace Mandatory Capability Register inspection before readiness.  
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

Two core product surfaces control prioritization:

```text
Buyer side
→ trustworthy technical discovery

Provider side
→ best-in-class Broker Workspace
```

## Broker Workspace — accepted direction and current baseline

Controlling records:

```text
docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md
specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md
docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md
docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md
specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md
```

Core operating principle:

> A broker should never have to enter information twice, search for information HullQ already knows, or wonder what happened to a lead.

SLICE-0053 now provides the first accepted professional access vertical:

```text
Auth0-compatible authentication
→ provider-agnostic HullQ Account
→ durable Organization / Membership / roles
→ server-side tenant authorization
→ privileged-role MFA gate
→ protected Astro Broker Workspace landing
```

Auth0 remains authentication-only. HullQ PostgreSQL/domain state remains authoritative for Organization membership, roles and authorization. Email is not the immutable identity key.

Current hard Broker Workspace gate state remains:

```text
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

The access boundary does not make the Broker Workspace launch-ready. `REQ-BROKER-023` broker identity/branding and `REQ-BROKER-024` connectivity-resilient draft recovery remain PENDING and mandatory before Launch Gate PASS, alongside the other trigger-specific mandatory commitments.

## Current architecture and precedence

`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` remains the accepted post-SLICE-0039 architecture direction. `architecture/SYSTEM_ARCHITECTURE.md` is the current architecture snapshot.

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

Accepted boundaries include:

- FastAPI is the sole application/domain API boundary; Astro must not access PostgreSQL directly or become a second semantic backend;
- Auth0 Public Cloud EU is authentication-only; HullQ owns account/tenant/role/authorization truth;
- publishing-capable, Owner and Admin broker memberships require validated MFA evidence;
- deployment uses CI-verified immutable Docker images, GHCR, versioned Docker Compose and controlled deploy/rollback;
- production app hosts are stateless/replaceable with respect to canonical application data;
- independent encrypted backup plus tested restore is required beyond provider DB backup;
- before real broker inventory is exposed to real external buyers, production PostgreSQL must have automatic failover with at least one standby.

SLICE-0053 adds a current session-topology invariant: the browser-visible FastAPI auth/callback and Astro Broker Workspace must share the same hostname while the session remains a host-only cookie. Cross-host configuration fails closed; any later redesign must be explicit.

## Hard truth and identity boundaries

Accepted marketplace identity boundary:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

Hard truth rule:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

A design/configuration can establish technical eligibility without establishing a fact about one offered yacht.

## Built and owner-accepted product threshold

The repository now includes accepted, tested verticals through:

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
```

Latest closures:

```text
docs/slices/SLICE-0051-acceptance-closure.md
docs/slices/SLICE-0052-acceptance-closure.md
docs/slices/SLICE-0053-acceptance-closure.md
```

## NativeListing lifecycle and freshness

Public lifecycle remains intentionally:

```text
DRAFT → ACTIVE → WITHDRAWN
```

Freshness remains separate under `MANUAL_NATIVE_V1`:

```text
confirmation TTL = 30 days
grace period     = 7 days

CONFIRMED
DUE_FOR_CONFIRMATION
STALE
UNKNOWN
```

Current buyer eligibility:

```text
ACTIVE + CONFIRMED/DUE_FOR_CONFIRMATION
→ current buyer eligible

ACTIVE + STALE/UNKNOWN
→ suppressed from current listing/Search surfaces
→ lifecycle remains ACTIVE
→ never inferred SOLD/WITHDRAWN
```

## Accepted technical Search result

SLICE-0051 still defines exactly one public hard technical buyer requirement:

```text
draft_max=<exact decimal metres>
```

Public routes remain `/en/search`, `/de/search`, `/fr/search`, `/pt/search`, `/es/search`.

Only `CONFIRMED_MATCH` is returned in the primary result surface. Insufficient/conflicting technical data is separate and never presented as a match. STALE/UNKNOWN inventory is excluded before technical classification.

Accepted technical native Search criteria count remains:

```text
1
```

## Post-SLICE-0051 trigger gates

Canonical records:

```text
docs/governance/POST_0051_TRIGGER_GATES.md
docs/governance/PRODUCTION_READINESS_GATE.md
docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md
```

Current state:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 1
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: NOT_DUE

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

From SLICE-0052 onward every primary readiness contract must contain the canonical trigger-gate evidence. Technical Search criterion #2 must explicitly compare its bridge/path to SLICE-0051; criterion #3+ may not introduce a third structural copy without the abstraction guard PASS.

Production Readiness must be PASS before real external broker data becomes HullQ production data, before the first real external production pilot, or before public production launch, whichever occurs first. The older PostgreSQL HA minimum remains separately hard before real broker inventory is exposed to real external buyers.

## Broker Mandatory Capability Register

Current high-level state remains:

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

SLICE-0053 directly implements REQ-BROKER-014 and REQ-BROKER-015; it does not change the mandatory-register statuses above. Every normal post-slice reassessment must inspect the register before selecting the next capability.

## What is not built yet

Important remaining product capabilities include:

- low-friction broker inventory create/edit/publish/reconfirm workflow;
- broker identity/branding completion and media operations;
- connectivity-resilient broker drafts/recovery;
- explicit commercial/sale outcome workflow;
- durable leads/contact requests, attribution, assignment/follow-up and broker analytics;
- inventory export/portability and later bulk import/feed paths;
- Search-fit diagnostics, exclusion explainability and privacy-safe demand insight when applicable/triggered;
- broader PhysicalBoat marketplace fact coverage;
- broader multi-criterion native-inventory Search and any later ranking/recommendation layer;
- Saved Search persistence, monitoring/alerts and price-history intelligence;
- independent verification of broker claims;
- production deployment/operations required for Production Readiness PASS;
- broad listing/Search SEO indexation beyond current noindex page classes;
- future payment/subscription entitlement enforcement.

These are not automatically assigned to SLICE-0054. Mandatory commitments may not be silently dropped.

## Search / SEO and monetization boundaries

Search architecture and SEO remain product architecture, not later marketing. Stable public listing route remains `/listings/{NativeListingId}`; current public listing/Search page classes remain deliberately `noindex`. Mandatory public languages remain English, German, French, Portuguese and Spanish.

Search remains broadly open; persistence, monitoring and intelligence remain preferred buyer monetization surfaces. No paid broker plan may activate while Broker Workspace launch/mandatory prerequisites remain unsatisfied.

## Execution checkpoint

Current product position:

```text
Buyer
→ production public listing
→ concrete-yacht broker truth
→ deterministic technical native Search
→ evidence-backed current-inventory freshness

Broker
→ external authentication
→ stable HullQ Account
→ durable Organization/Membership/roles
→ tenant-safe + MFA-gated authorization
→ protected Broker Workspace landing
```

Next queue number:

```text
SLICE-0054
```

No SLICE-0054 capability has been selected or authorized by this closure. Selection must begin with post-SLICE-0053 repository reconciliation, trigger-gate inspection and Mandatory Capability Register inspection, then choose the smallest highest-leverage visible continuation.

## Development workflow

- `origin/main` is canonical shared truth;
- one implementation slice per isolated worktree/branch;
- Claude Code implements; independent reviewer verifies exact implementation HEAD;
- material finding → amendment on the same branch;
- clean exact-head review → ACCEPT;
- explicit Project Owner acceptance is mandatory before implementation merge;
- acceptance closure follows implementation merge and advances `PROJECT_STATE_ACCEPTED_SLICE` atomically;
- `FINISH_SLICE.bat` closes the local slice only after remote closure is independently reviewed and merged;
- the next slice begins only after reassessment/readiness and uses a fresh Claude conversation;
- workflow reassessment becomes mandatory after accepted SLICE-0056 or before an earlier real production pilot, whichever comes first.

For exact hashes, amendments, gate runs and review history, read the corresponding acceptance closure rather than expanding this file into a second historical log.
