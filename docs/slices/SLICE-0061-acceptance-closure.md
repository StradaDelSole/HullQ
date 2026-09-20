# SLICE-0061 — Acceptance Closure

**ID:** SLICE-0061  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #230  
**Accepted implementation HEAD:** `0823fabed2c975acda5ec241248fe86cf104c4f6`  
**Implementation merge commit:** `02682c952e3db2a47b0c4738974aa8ff7a5e9df7`  
**Independent exact-head ACCEPT review:** 2026-09-20  
**Owner acceptance:** explicitly recorded 2026-09-20

## Accepted capability

SLICE-0061 adds one bounded private professional Seller/Broker Workspace capability:

```text
authenticated HullQ Account
+ explicit Organization
+ exact current ACTIVE OrganizationMembership
+ PUBLISHER role
+ required MFA state
→ Organization-owned ProfessionalListingDraft
→ create / list / reopen / read / update
→ incomplete pre-market state may persist
→ NOT PUBLIC
```

The authoritative ownership boundary is `owner_organization_id`. The creator Account is retained as audit metadata only and does not become the continuing ownership key.

Professional draft identity remains distinct from owner-direct draft and marketplace identities:

```text
ProfessionalListingDraftId
!= OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

Private draft authoring intentionally does **not** require `OrganizationPublishingEligibility == ELIGIBLE`. The accepted public NativeListing publishing-eligibility evaluator remains a separate publication/promotion gate and is not bypassed by this slice.

## Accepted implementation behavior

The accepted implementation includes:

- dedicated `professional_listing_drafts` PostgreSQL persistence with Organization ownership, creator-account audit metadata, optional broker listing reference, bounded payload, version and timestamps;
- one new Alembic migration with a supporting Organization + deterministic keyset-order index;
- a distinct runtime `ProfessionalListingDraftId`;
- a channel-neutral shared nine-common-field draft payload parser/serializer used by both professional and owner-direct draft flows;
- unchanged owner-direct external names and behavior through compatibility re-exports;
- current-session/current-membership/current-role authorization reuse;
- exact current ACTIVE matching OrganizationMembership plus `PUBLISHER` required uniformly for list/read/create/update;
- existing privileged-role MFA semantics preserved;
- unknown/unauthorized Organization and foreign/unknown draft access remain non-enumerating;
- no private-draft authoring dependency on Organization publishing eligibility;
- create/read/list/update API family:
  - `GET /api/broker/organizations/{organization_id}/drafts`
  - `POST /api/broker/organizations/{organization_id}/drafts`
  - `GET /api/broker/organizations/{organization_id}/drafts/{draft_id}`
  - `PUT /api/broker/organizations/{organization_id}/drafts/{draft_id}`;
- valid empty and partial draft persistence;
- optional `broker_listing_reference`;
- optimistic concurrency with version 1 at creation and atomic compare-and-increment updates;
- stale `expected_version` conflict with zero overwrite;
- deterministic order `updated_at DESC, professional_listing_draft_id ASC`;
- bounded opaque keyset pagination, default page size 50 and maximum 100;
- malformed cursor bounded failure;
- explicit same-origin write defense using exact configured Origin plus fixed non-simple `X-HullQ-Requested-With: professional-listing-draft-v1`;
- private Astro routes:
  - `/broker/organizations/{organization_id}/drafts`
  - `/broker/organizations/{organization_id}/drafts/{draft_id}`;
- browser-visible `Draft — not public` language;
- `Cache-Control: private, no-store` and `X-Robots-Tag: noindex`;
- no Publish, Withdraw, Reconfirm, media, Search-fit or public-preview action;
- no draft operation creates or mutates PhysicalBoat, MarketEpisode, NativeListing, offer, lifecycle, freshness, public-read or Search truth;
- retained PostgreSQL 18 + FastAPI + built Astro real-HTTP proof wired into normal CI.

## Independent review and amendment

Initial implementation exact head:

```text
0dcaadd890cf1b3fd3ab49da4c8a6e5cef45a042
```

Independent exact-head review found one blocking contract gap:

1. FastAPI/persistence already implemented bounded keyset pagination, but the required Astro collection surface did not consume the opaque browser `cursor` and did not render `next_cursor`. Drafts after the first default page were therefore unreachable through the required browser route, violating the contract's bounded-browser-pagination requirement.

The review also resolved the implementation agent's stated PUBLISHER ambiguity: the normative contract and slice objective require `PUBLISHER` uniformly for **list/read/create/update**. That implementation choice was correct and was left unchanged.

Targeted amendment exact head:

```text
0823fabed2c975acda5ec241248fe86cf104c4f6
```

The amendment:

- reads the collection-page `cursor` directly from the browser query string;
- forwards the opaque cursor unchanged through the existing professional draft client to FastAPI;
- never decodes or reinterprets the cursor in Astro;
- renders a safe `Next page` continuation link when `next_cursor` exists;
- extends the retained proof with a dedicated Organization containing 51 drafts;
- proves the built Astro collection surface traverses 50 + 1 rows across two pages;
- proves the rendered cursor is byte-identical to FastAPI's opaque `next_cursor`;
- proves no duplicate/missing draft IDs across pages;
- proves no cross-Organization leakage;
- proves malformed cursor still reaches the bounded browser 400 invalid-link state.

Delta-first exact-head re-review returned **ACCEPT** with no unresolved blocking finding.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- authentication remains authentication-only; HullQ Account/Organization/Membership/roles/authorization remain PostgreSQL/domain truth
- current Organization authorization re-reads current membership on each request
- exact current ACTIVE membership + PUBLISHER gates professional draft list/read/create/update
- privileged Organization access retains existing MFA semantics
- private professional draft ownership is exact owner_organization_id; creator Account is audit metadata only
- ProfessionalListingDraftId is distinct from OwnerDirectListingDraftId and all marketplace identities
- professional draft persistence is private pre-market state, not NativeListing/PhysicalBoat/MarketEpisode truth
- professional and owner-direct draft channels share one implementation of the nine common draft-field rules
- optimistic versioning with stale-write conflict/no overwrite
- deterministic bounded opaque-keyset list pagination
- explicit same-origin Origin + fixed non-simple-header CSRF defense
- private noindex/no-store Astro collection/edit surfaces
- Organization publishing eligibility is not a private-draft-authoring requirement
- existing public NativeListing publishing eligibility remains separate and unchanged
- no professional draft operation promotes/mutates marketplace/public/Search truth
- technical native Search criterion count remains exactly 2
- organic Search commercial independence remains mandatory

DECIDED_NOT_YET_IMPLEMENTED
- professional draft → marketplace promotion transaction
- professional NativeListing publication from draft
- publish/withdraw/reconfirm controls in the draft workspace
- connectivity-resilient professional draft recovery/offline recovery
- media workflow
- broker profile/logo/branding completion
- Organization/staff administration
- leads/contact/CRM/outcomes/analytics
- Search-fit/exclusion/demand insight
- bulk import/export
- payments/entitlements
- owner-direct marketplace publication/admission
- buyer account persistence / persistent Shortlist
- Saved Search / monitoring / alerts
- third technical Search criterion

EXPLICITLY_DEFERRED
- all additional deferred items listed by the SLICE-0061 readiness contract and professional listing workspace contract

GENUINELY_OPEN
- exact future professional draft-to-marketplace promotion transaction design
- future shared Seller Platform storage composition beyond the accepted shared common-field primitive
- exact future clone/relist flow
- exact connectivity-resilient local recovery/synchronization design
- eventual human-readable Organization profile/branding model
- buyer Free/Pro durable continuity semantics

CONFLICT_OR_REGRESSION
- none found on the accepted exact head
```

## Exact-head verification

Remote verification on exact accepted HEAD `0823fabed2c975acda5ec241248fe86cf104c4f6`:

```text
CI run 35526149135 / #834 → SUCCESS
Manufacturer artifact reproducibility run 35526149208 / #556 → SUCCESS
```

All exact-head GitHub gates completed successfully:

- `dependency audit`;
- `web quality (Astro/Node)`;
- `quality (ubuntu-latest)`;
- `quality (windows-latest)`;
- `db integration (PostgreSQL 18)`;
- `reproduce (ubuntu-latest)`;
- `reproduce (windows-latest)`.

The PostgreSQL-18 integration job `106118527626` explicitly executed and passed:

```text
SLICE-0048 first-visible-listing-preview real HTTP vertical proof
SLICE-0049 first-production-public-listing real HTTP vertical proof
SLICE-0052 native-listing-freshness real HTTP vertical proof
SLICE-0053 authenticated-broker-workspace-access real HTTP vertical proof
SLICE-0054 authenticated-owner-direct-draft-workspace real HTTP vertical proof
SLICE-0056 public multi-criterion Search browser completion real HTTP vertical proof
SLICE-0058 anonymous local shortlist real HTTP vertical proof
SLICE-0059 anonymous factual shortlist compare real HTTP vertical proof
SLICE-0060 authenticated professional inventory overview real HTTP vertical proof
SLICE-0061 authenticated professional listing draft workspace real HTTP vertical proof
```

The implementation agent's final local report recorded:

```text
repository validation: PASS
ruff format/check: PASS
mypy: PASS (111 files)
non-DB pytest: 4566 passed / 720 skipped
PostgreSQL integration suite: 717 passed / 1 skipped
web tests: 145 passed
Astro check/build: PASS
professional draft retained proof: PASS
owner-direct retained proof: PASS
professional inventory retained proof: PASS
```

PR #230 merged the exact accepted implementation to `main` as:

```text
02682c952e3db2a47b0c4738974aa8ff7a5e9df7
```

## Verification-depth disclosure retained

The retained professional-draft vertical proof uses real PostgreSQL 18, real FastAPI, a deterministic local OIDC/JWKS issuer and the built Astro/Node SSR server over real HTTP.

It exercises actual authenticated browser-style HTTP/session/form flows and built Astro SSR output, but it does not drive a separate graphical/headless browser DOM engine. This remains a transparent verification-depth limit, not a claim that browser automation was performed where it was not.

## Scope retained / explicitly deferred

SLICE-0061 does **not** add:

- professional draft-to-NativeListing promotion;
- public publication from a professional draft;
- publish, withdraw or reconfirm controls;
- connectivity-resilient/offline draft recovery;
- media upload/order/cover selection;
- broker logo/profile/branding completion;
- Organization/staff self-service administration;
- lead/contact persistence, attribution, assignment or CRM;
- sale/outcome workflow;
- analytics/engagement reporting;
- Search-fit/exclusion/demand insight;
- bulk import/export;
- payments/entitlements;
- owner-direct publication/admission;
- buyer account persistence or cross-device Shortlist;
- Saved Search / monitoring / alerts;
- a third technical Search criterion;
- real external marketplace production data;
- broker self-service pilot, paid broker plan, production pilot or public production launch.

The accepted technical native Search criterion count therefore remains exactly `2`.

## Broker mandatory-register state after acceptance

SLICE-0061 adds a safe Organization-owned private professional draft foundation but does not close the still-pending mandatory Broker Workspace commitments tracked in the current register.

Canonical state remains:

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

In particular, REQ-BROKER-023 branding and REQ-BROKER-024 connectivity-resilient draft recovery remain PENDING. The Broker Workspace Launch Gate remains `NOT_READY`.

## Trigger-gate state after acceptance

SLICE-0061 adds no technical Search criterion and uses internal/synthetic retained proof only.

Canonical trigger state remains:

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

Production Readiness remains `NOT_TRIGGERED`: no real external marketplace production data was introduced, no broker self-service or production pilot started, and no public production launch occurred.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0061
PROJECT_STATE_QUEUE_SLICE:    0062
```

The queue number does **not** select or authorize a SLICE-0062 capability.

SLICE-0062 requires fresh post-SLICE-0061 repository/product reassessment and the normal Decision / Implementation Reconciliation before capability selection/readiness. No SLICE-0062 readiness or `START_SLICE.bat` action is authorized by this closure.

## Product execution checkpoint

HullQ's accepted professional provider path now includes:

```text
Auth0-compatible login
→ durable HullQ Account
→ current Organization/Membership/MFA authorization
→ explicit Organization workspace
→ current Organization-owned NativeListing inventory
→ private Organization-owned ProfessionalListingDraft workspace
→ resumable create/list/read/update with optimistic concurrency
→ no implicit promotion to marketplace truth
```

The professional draft workspace is private pre-market authoring state. It composes with the accepted Broker Workspace but remains structurally and behaviorally separate from NativeListing/PhysicalBoat/MarketEpisode/public Search truth.

## Closure decision

```text
SLICE-0061 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0061
PROJECT_STATE_QUEUE_SLICE = 0062
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
