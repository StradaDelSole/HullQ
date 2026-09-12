# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0051 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0052 -->

**Updated:** 2026-09-13  
**Latest owner-accepted / DONE slice:** SLICE-0051  
**Current queue:** SLICE-0052 — queue number reserved for the next post-SLICE-0051 capability; capability is **not selected**, no readiness contract exists, and implementation is not authorized until post-slice reassessment/reconciliation/readiness completes.  
**Exceptional historical state:** SLICE-0039 remains terminal `BLOCKED` and is not to be reopened.

This is the compact current-state entry point for HullQ. Historical implementation/review detail belongs in slice contracts, acceptance closures, retained research packages and Git history. Normative specs/accepted decisions remain authoritative where they apply; current architecture precedence is explicit below.

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

The category/business-model baseline remains externally validated; HullQ-specific product advantage, buyer adoption, native inventory acquisition, broker participation and sustainable unit economics still require validation at HullQ scale.

## Current architecture and precedence

`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` is the accepted post-SLICE-0039 architecture direction. `architecture/SYSTEM_ARCHITECTURE.md` is the current architecture snapshot. Older ADR-0010 / application-stack-baseline text remains historical and is superseded where it conflicts with that later accepted direction.

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

Additional accepted boundaries:

- FastAPI is the sole application/domain API boundary; Astro does not access PostgreSQL directly or reimplement Search/domain semantics;
- Auth0 Public Cloud EU is authentication-only; HullQ owns Account IDs, Organizations, Memberships, roles, listing ownership, verification and authorization in PostgreSQL/domain state;
- privileged broker publishing requires MFA, preferably passkeys/WebAuthn where supported, with step-up for high-risk actions when those actions exist;
- deployment uses CI-verified immutable Docker images, GHCR, versioned Docker Compose and controlled deploy/health-check/rollback; Coolify/Dokploy are not the initial control plane;
- application hosts remain stateless/replaceable with respect to canonical application data;
- provider DB backup alone is insufficient: independently stored encrypted backup plus tested restore is required;
- before the first real external broker production inventory is exposed to real external buyers, production PostgreSQL must have automatic failover with at least one standby.

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
- durable MarketEpisode identity and optional NativeListing→MarketEpisode linkage (SLICE-0047);
- first browser-visible real listing preview vertical (SLICE-0048);
- first production-public NativeListing lifecycle/read/page vertical (SLICE-0049);
- first buyer-critical concrete PhysicalBoat truth vertical with exactly seven broker-declared fields and no BoatDesign fallback (SLICE-0050);
- first production buyer-facing Requirements → Native Inventory Search vertical over exactly `draft_max` (SLICE-0051);
- durable versioned/current `FieldResolution` PostgreSQL persistence for the bounded 0051 technical qualification path, including evidence/source-rights admission, canonical-value consistency, exact Decimal preservation and concurrency/rollback guarantees (SLICE-0051 blocker resolution + implementation).

SLICE-0049 public lifecycle remains intentionally only:

```text
DRAFT → ACTIVE → WITHDRAWN
```

Republish, `SOLD`, `ARCHIVED` and freshness/staleness semantics remain future capabilities.

SLICE-0050 concrete-yacht claims remain immutable revisions with explicit current head per `(PhysicalBoatId, claiming OrganizationId)`. The public listing uses only the publishing Organization's current claims. Omitted and explicit `UNKNOWN` are distinct; numeric values are lossless decimals; BoatDesign facts never backfill concrete-yacht claims.

## Accepted SLICE-0051 Search result

SLICE-0051 delivers exactly one public hard buyer requirement:

```text
draft_max=<exact decimal metres>
```

Accepted public Search routes:

```text
/en/search
/de/search
/fr/search
/pt/search
/es/search
```

Accepted production path:

```text
buyer draft_max
→ exact Decimal request parsing/canonicalization
→ qualified deterministic BoatDesign/configuration Search
→ ACTIVE native professional inventory
→ NativeListing → MarketEpisode → PhysicalBoat
→ publishing Organization's current physical_boat.draft claim
→ same-PhysicalBoat current-observation contradiction guard
→ CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA
→ buyer-visible Search result
→ /listings/{NativeListingId}
```

Only `CONFIRMED_MATCH` is returned in the primary result surface. Insufficient/conflicting data is separate and never presented as a match.

A raw value merely present in `canonical_boat_designs` is not confirmed Search truth. For the bounded 0051 path, the relevant design/configuration field requires an admissible active `FieldResolution`, exact canonical-value agreement and accepted production-use evidence/source rights.

SLICE-0051 Search consumption is bounded to:

```text
BoatDesign /baseline/dimensions/draft_max_m
NamedVariant /overrides/dimensions/draft_max_m
```

No generic source winner, global fact resolver, all-field FieldResolution backfill or generic all-field native Search was introduced.

Public Search URL semantics are deterministic and the current Search/listing page classes remain deliberately `noindex`.

Acceptance closure: `docs/slices/SLICE-0051-acceptance-closure.md`.

## Post-SLICE-0051 trigger gates

Canonical trigger record:

```text
docs/governance/POST_0051_TRIGGER_GATES.md
```

Canonical operational release gate:

```text
docs/governance/PRODUCTION_READINESS_GATE.md
```

Current trigger state:

```text
architecture/current-state reconciliation before 0052: PASS
accepted technical native Search criteria: 1 (draft_max)
workflow reassessment: NOT_DUE; mandatory after SLICE-0056 or before first real production pilot, whichever comes first
production readiness: NOT_TRIGGERED while no real external broker production pilot/public production launch has begun
```

From SLICE-0052 onward every primary readiness contract must contain `**TRIGGER GATES CHECK:** PASS` and the machine-checked `## Trigger gates` evidence section.

Technical Search expansion rule:

```text
criterion #1 -> concrete path proved by SLICE-0051
criterion #2 -> mandatory explicit comparison with the 0051 bridge/path
criterion #3+ -> no third structural copy without PASS abstraction guard
```

This does not preselect a Search capability for SLICE-0052 and does not authorize speculative generic resolution infrastructure.

Production-readiness rule:

```text
first real external broker inventory shown to real external buyers
OR public production launch
→ PRODUCTION_READINESS_GATE_STATUS MUST be PASS
```

The gate covers controlled deploy/rollback, DB HA/recoverability/restore proof, observability/alerting, abuse protection, secrets/privileged access, applicable Auth0/MFA controls, applicable media durability and release verification.

The repository validator and `START_SLICE` enforce the deterministic trigger relationships; independent readiness review remains responsible for semantic truth.

## What is not built yet

Important remaining marketplace/product capabilities include:

- authenticated Auth0-backed broker workspace/form;
- persisted marketplace actor directory beyond accepted runtime eligibility types;
- PhysicalBoat marketplace fact coverage beyond the seven accepted SLICE-0050 fields, including broader field-specific verification/resolution;
- media upload/storage/presentation;
- broader multi-criterion native-inventory Search and any ranking/recommendation layer beyond the bounded deterministic 0051 result surface;
- Saved Search persistence, monitoring/alerts and price-history intelligence;
- lead/contact workflow;
- republish, SOLD/ARCHIVED and freshness/staleness lifecycle behavior;
- independent verification of broker claims;
- broad/global canonical-field resolution/backfill;
- production deployment/operations capabilities required to make the Production Readiness Gate PASS;
- full listing/Search SEO indexation, faceted landing-page taxonomy, sitemap/hreflang expansion and broad structured-data strategy beyond the accepted noindex page classes.

These are not silently queued. The post-0051 reassessment must select the next capability by product leverage and repository reconciliation.

## Search and SEO boundary

Search architecture and SEO remain product architecture, not later marketing.

The stable public listing route remains:

```text
/listings/{NativeListingId}
```

with no slug and deliberate `noindex` under the currently accepted bounded page-class decision.

SLICE-0051 adds locale-prefixed public Astro SSR Search over the existing FastAPI boundary. Its canonical parameterized identities are deterministic but remain `noindex`. Arbitrary facet paths, indexable Search-result combinations, Search sitemap publication and broad structured-data expansion are not authorized.

Mandatory public languages remain English, German, French, Portuguese and Spanish. Canonical IDs, technical values, provenance and Search semantics remain language-neutral.

## Monetization direction

Search remains broadly open; persistence, monitoring and intelligence remain preferred monetization surfaces.

Current framing remains:

```text
HullQ Free — Search everything. Save 5 searches.
```

Potential Pro surfaces include expanded saved searches, monitoring/alerts and, where rights/data permit, listing price history, price-change alerts, model/generation/configuration market trends, Days-on-Market and price-reduction signals.

## Execution checkpoint

Completed product threshold:

```text
PERSISTED REAL LISTING
→ PRODUCTION PUBLIC LISTING
→ CONCRETE-YACHT BROKER TRUTH
→ FIRST PRODUCTION BUYER TECHNICAL SEARCH
= BUILT
```

Estimated remaining slice distance to the first externally visible listing:

```text
0
```

**SLICE-0052 still has no selected capability.** After this maintenance/reconciliation change is accepted and merged, the next action is the post-SLICE-0051 product/architecture reassessment against canonical `origin/main`, using both `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md` and the post-0051 trigger gates.

That reassessment must select the smallest highest-leverage continuation of the buyer/broker loop rather than automatically broadening Search or inserting a foundation-only slice.

No SLICE-0052 implementation may start until capability selection, readiness, independent readiness review and readiness merge are complete and the Project Owner runs `START_SLICE.bat`.

## Development workflow

- `origin/main` is canonical shared truth;
- one implementation slice per isolated worktree/branch;
- Claude Code implements; independent reviewer verifies exact implementation HEAD;
- material finding → `AMEND` on the same branch;
- clean exact-head review → `ACCEPT`;
- explicit Project Owner acceptance is mandatory before implementation merge;
- acceptance closure follows the implementation merge and advances `PROJECT_STATE_ACCEPTED_SLICE` atomically;
- `FINISH_SLICE.bat` closes the local slice only after remote closure is reviewed and merged;
- the next slice starts only after post-slice reassessment/readiness and uses a fresh Claude conversation;
- the current review workflow remains unchanged until the mandatory evidence-based reassessment trigger is satisfied and any change is owner-accepted.

For exact hashes, amendments, gate runs and review history, read the corresponding slice acceptance closure rather than expanding this file into a second historical log.
