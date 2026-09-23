# SLICE-0064 — Acceptance Closure

**ID:** SLICE-0064  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #244  
**Accepted implementation HEAD:** `beb05bd302523d072b8c0ee7efbe1fb618390d15`  
**Implementation merge commit:** `4fd9f5b1db89c19c77fe8d75df71551f1db76eca`  
**Independent exact-head ACCEPT review:** 2026-09-23  
**Owner acceptance:** explicitly recorded 2026-09-23

## Accepted capability

SLICE-0064 closes the bounded professional Broker Workspace control surface for already-existing NativeListing lifecycle/freshness operations:

```text
authorized current MarketplaceOrganization publisher
+ existing Organization-owned NativeListing
→ DRAFT: Publish
→ ACTIVE: Withdraw / Reconfirm
→ WITHDRAWN: no republish
→ freshly re-read authoritative inventory/public state
```

It exposes existing accepted lifecycle/freshness truth through authenticated Organization-scoped FastAPI and Broker Workspace controls. It does not define a new lifecycle, create a NativeListing, promote a ProfessionalListingDraft, edit an offer, create media, infer SOLD, add Search criteria or alter public/current-market eligibility semantics.

## Accepted implementation behavior

The accepted implementation includes:

- thin application orchestration over the accepted `publish_native_listing()`, `withdraw_native_listing()` and `reconfirm_native_listing()` persistence primitives;
- exact reuse of the current Account/Organization/Membership/MFA Broker Workspace authorization boundary;
- exact reuse of the current PUBLISHER-role and Organization publishing-eligibility decision;
- selected-Organization ownership enforcement for every mutation;
- foreign and unknown NativeListing IDs collapsed to one non-enumerating not-found shape;
- Organization-scoped authenticated routes:
  - `POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/publish`;
  - `POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/withdraw`;
  - `POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/reconfirm`;
- dedicated exact-Origin + fixed non-simple-header CSRF discipline for the inventory-lifecycle write channel;
- Publish only through the accepted DRAFT→ACTIVE transition;
- Withdraw only through the accepted ACTIVE→WITHDRAWN transition;
- no WITHDRAWN→ACTIVE republish path;
- no SOLD/outcome inference from withdrawal;
- ACTIVE-only freshness reconfirmation with a stable canonical operation identity;
- exact reconfirm retry idempotency and fail-closed conflicting operation-ID reuse;
- fresh top-level transaction ownership preserved after authorization reads;
- DRAFT inventory UI shows Publish;
- ACTIVE inventory UI shows Withdraw + Reconfirm;
- WITHDRAWN inventory UI exposes no republish control;
- after every browser action the page re-reads authoritative current server state rather than inventing lifecycle/freshness state client-side;
- browser-visible outcomes remain mechanically distinct for authentication required, MFA required, publishing denied, non-enumerating listing-not-found, incomplete listing, state conflict, invalid reconfirm operation identity and service failure;
- private/no-store/noindex Broker Workspace behavior remains;
- no ProfessionalListingDraft, PhysicalBoat, MarketEpisode, offer, claim, media, lead/outcome/analytics or Search mutation;
- no schema migration and no new lifecycle/freshness table, state or policy.

## Independent review and amendment

Initial implementation exact head:

```text
4648f5177200bd8a85f1b468861d61a7361951ab
```

Independent exact-head review found one contract-level browser outcome defect plus a related 403-classification gap:

1. FastAPI correctly collapsed foreign/unknown NativeListings to the accepted non-enumerating 404, and the TypeScript client exposed `not_found`, but the Astro inventory action surface failed to map that result and rendered the generic service-failure banner instead of the distinct §14 listing-not-found outcome.
2. The TypeScript client declared `mfa_required` but treated every HTTP 403 as publishing denial, even though FastAPI distinguishes `mfa_required`, `publishing_denied` and unrelated/CSRF-shaped 403 failures.

The bounded amendment exact head:

```text
beb05bd302523d072b8c0ee7efbe1fb618390d15
```

closed both findings by:

- adding body-aware 403 classification preserving MFA, publishing-denial and unexpected/service-failure distinctions;
- explicitly mapping authentication, MFA and listing-not-found action outcomes in the Astro inventory surface;
- using identical non-enumerating listing-not-found text for foreign and wholly unknown listing IDs;
- strengthening the retained real-HTTP proof so both foreign and unknown browser action attempts render the same bounded listing-not-found banner and never the generic service-failure message;
- adding focused TypeScript regressions for MFA, CSRF-shaped/unrecognized and unparseable 403 responses across publish/withdraw/reconfirm.

The amendment changed one commit / four files relative to the initially reviewed head and did not alter lifecycle, freshness, ownership, authorization or transaction semantics.

Independent exact-head re-review returned **ACCEPT** with no unresolved implementation finding.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- current Auth0-compatible session / HullQ Account boundary
- current MarketplaceOrganization / OrganizationMembership / roles in PostgreSQL
- current Broker Workspace membership + MFA authorization
- PUBLISHER-role + Organization publishing eligibility for public NativeListing mutations
- NativeListing publishing-Organization ownership
- lifecycle states remain exactly DRAFT / ACTIVE / WITHDRAWN
- lifecycle transitions remain exactly DRAFT→ACTIVE and ACTIVE→WITHDRAWN
- no accepted WITHDRAWN→ACTIVE republish
- immutable publication-transition history
- publication transition as accepted freshness evidence
- manual-native freshness/current-market rules
- ACTIVE-only freshness reconfirmation
- exact retry idempotency and conflicting operation-ID fail-closed behavior
- stale/unknown freshness suppression without lifecycle mutation
- Organization inventory overview
- public publisher identity
- broker-facing Publish / Withdraw / Reconfirm controls for already-existing Organization-owned NativeListings
- browser-visible bounded action outcomes including non-enumerating foreign/unknown listing behavior
- fresh authoritative inventory readback after mutation
- technical native Search criterion count remains exactly 2
- organic Search commercial independence remains mandatory

DECIDED_NOT_YET_IMPLEMENTED
- ProfessionalListingDraft → marketplace promotion transaction
- NativeListing creation from professional draft
- PhysicalBoat / MarketEpisode selection or creation during promotion
- offer / price / listing-detail editing in the Broker Workspace
- WITHDRAWN→ACTIVE relist/republish semantics
- media/gallery
- leads/contact/CRM
- explicit sale/outcome workflow
- broker analytics / engagement reporting
- inventory portability/export
- bulk onboarding/import
- Search exclusion explainability
- pre-publication Search-fit diagnostics
- privacy-safe aggregate demand insights
- Organization/profile self-service administration
- payments/entitlements
- owner-direct marketplace publication/admission
- buyer account persistence / persistent Shortlist
- Saved Search / monitoring / alerts
- third technical Search criterion

EXPLICITLY_DEFERRED
- all draft-promotion identity/field mapping not accepted by 0064
- offer/price/detail editing
- republish/relist semantics
- SOLD/ARCHIVED/deal-state expansion
- media/gallery
- leads/contact/CRM
- outcomes/analytics/reporting
- export/import
- Search-fit/exclusion/demand insights
- Organization/profile admin
- payments
- owner-direct publication
- buyer persistence
- production pilot/public launch

GENUINELY_OPEN
- exact professional draft-to-marketplace promotion transaction
- explicit new-vs-existing PhysicalBoat choice during promotion
- persistence mapping for draft physical_boat.boat_name
- professional draft support for required listing_offer.broker_description
- future WITHDRAWN relist/republish semantics
- future offer-edit workflow
- launch media scope/architecture
- lead/CRM workflow

CONFLICT_OR_REGRESSION
- none found on the accepted exact head
```

## Exact-head verification

Remote verification on exact accepted HEAD `beb05bd302523d072b8c0ee7efbe1fb618390d15`:

```text
CI run 35848545756 / #872 → SUCCESS
Manufacturer artifact reproducibility run 35848545750 / #594 → SUCCESS
```

All exact-head GitHub gates completed successfully:

- `db integration (PostgreSQL 18)`;
- `dependency audit`;
- `quality (ubuntu-latest)`;
- `quality (windows-latest)`;
- `web quality (Astro/Node)`;
- `reproduce (ubuntu-latest)`;
- `reproduce (windows-latest)`.

The implementation agent's amended final local report recorded:

```text
repository validation: PASS
ruff format/check: PASS
mypy: PASS (113 files)
non-DB pytest: 4621 passed / 768 skipped
focused PostgreSQL-dependent lifecycle tests: 58 passed
web tests: 242 passed
Astro check: 0 errors
Astro build: PASS
professional inventory lifecycle controls retained proof: PASS
professional inventory overview sibling retained proof: PASS
```

The retained proof `scripts/inspect_professional_inventory_lifecycle_controls.py` uses a real disposable PostgreSQL 18 schema, deterministic local OIDC/JWKS login, FastAPI and built Astro SSR over real HTTP.

It proves representative DRAFT visibility, browser Publish→ACTIVE, public visibility, foreign/unknown non-enumerating action behavior, browser Withdraw→WITHDRAWN, no SOLD state, stale suppression, ACTIVE reconfirmation restoring current visibility, exact reconfirm retry idempotency, DRAFT/WITHDRAWN reconfirm rejection, CSRF fail-closed behavior, immediate membership-revocation enforcement, state-appropriate controls and fresh authoritative readback.

PR #244 merged the exact accepted implementation to `main` as:

```text
4fd9f5b1db89c19c77fe8d75df71551f1db76eca
```

## Broker mandatory-register state after acceptance

SLICE-0064 changes no REQ-BROKER-022…030 status marker.

Canonical register state remains:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING
SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED
SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS: NOT_REACHED
POST_PILOT_REAL_BROKER_VALIDATION_STATUS: NOT_STARTED

REQ_BROKER_022_STATUS: PENDING
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
REQ_BROKER_025_STATUS: PENDING
REQ_BROKER_026_STATUS: PENDING
REQ_BROKER_027_STATUS: PENDING
REQ_BROKER_028_STATUS: PENDING
REQ_BROKER_029_STATUS: PENDING
REQ_BROKER_030_STATUS: IMPLEMENTED
```

0064 materially advances Broker Workspace Launch Gate §2 evidence because an external professional publisher can now Publish, Withdraw and Reconfirm already-existing inventory without operator/admin intervention.

It does **not** complete the full launch-critical inventory workflow. Draft-to-marketplace promotion/creation, offer editing, media where required and the remaining gate sections are still outstanding. Therefore the Broker Workspace Launch Gate remains `NOT_READY` and the broker self-service pilot remains `NOT_STARTED`.

## Trigger-gate state after acceptance

SLICE-0064 adds no technical Search criterion and introduces no real external production data, pilot, paid plan or public launch.

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

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0064
PROJECT_STATE_QUEUE_SLICE:    0065
```

SLICE-0065 is **UNSELECTED**.

The queue number does not authorize implementation, readiness, `START_SLICE.bat` or a capability choice. Before any 0065 selection or material product/domain/data/architecture decision, a fresh post-SLICE-0064 repository/product reassessment and Decision / Implementation Reconciliation are required.

This closure also repairs stale duplicated state in `docs/PROJECT_STATE.md`: its local Broker Mandatory Capability Register summary still showed REQ-BROKER-023/024 as PENDING even though the canonical register and SLICE-0063 closure already established both as IMPLEMENTED. This is synchronization only; no accepted decision is changed.

## Product execution checkpoint

HullQ's accepted professional provider path now includes:

```text
Auth0-compatible login
→ durable HullQ Account
→ current Organization/Membership/MFA authorization
→ explicit MarketplaceOrganization + current public display identity
→ Organization-owned NativeListing inventory overview
→ private ProfessionalListingDraft workspace
→ resumable create/list/read/update with optimistic concurrency
→ bounded connectivity recovery for recent unsaved edits
→ existing complete DRAFT NativeListing: Publish → ACTIVE
→ existing ACTIVE NativeListing: Withdraw → WITHDRAWN
→ existing ACTIVE NativeListing: Reconfirm freshness
→ fresh authoritative inventory/public readback after every action
→ no implicit ProfessionalListingDraft promotion
→ no republish / SOLD inference / offer edit / media / lead / analytics expansion
```

This closes a concrete Broker Workspace Launch Gate inventory-operation gap while preserving the accepted marketplace truth model.

## Closure decision

```text
SLICE-0064 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0064
PROJECT_STATE_QUEUE_SLICE = 0065
REQ_BROKER_023_STATUS = IMPLEMENTED
REQ_BROKER_024_STATUS = IMPLEMENTED
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
