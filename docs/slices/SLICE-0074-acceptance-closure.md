# SLICE-0074 — Acceptance Closure

**ID:** SLICE-0074  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #287  
**Accepted implementation HEAD:** `0984a7f792003f816fccdd8601b4e9bf0a543ffd`  
**Implementation merge commit:** `1c4a586b83ff4a7016a325a556a6a4bb97d8352d`  
**Independent exact-head ACCEPT review:** 2026-10-01  
**Owner acceptance:** explicitly recorded 2026-10-01

## Accepted capability

SLICE-0074 delivers the explicit broker sale/outcome close-out:

```text
existing Organization-owned NativeListing
→ explicit Close as SOLD
→ immutable publisher-scoped SaleOutcome revision
→ optional sold date / achieved price / originating Lead
→ ACTIVE listing atomically becomes WITHDRAWN
→ authoritative current outcome re-read
```

WITHDRAWN alone never means SOLD.

## Accepted implementation behavior

- durable `native_listing_sale_outcome_revisions` + explicit current-head persistence;
- immutable superseding correction history;
- exact optimistic concurrency;
- retry-safe revision-id/content-hash idempotency;
- ACTIVE + SOLD atomically appends outcome and transitions ACTIVE→WITHDRAWN;
- already-WITHDRAWN + SOLD records/corrects outcome without rewriting lifecycle;
- DRAFT close-as-SOLD is rejected;
- sold_date remains distinct from recorded_at;
- achieved sale price is optional and never copied from asking price;
- currency is required iff achieved amount is present;
- optional originating Lead must belong to the same Organization and NativeListing;
- another Organization's listing for the same MarketEpisode is untouched;
- publisher SOLD report does not become canonical global MarketEpisode outcome truth;
- Broker Workspace exposes current outcome and bounded close/correction UI;
- foreign/unknown listing access remains non-enumerating;
- no new technical Search criterion.

## Independent review / amendment

Initial implementation HEAD:

`12e56a13d1f32bbf7a00457ab924feb0f9562d25`

Independent review found one material authorization defect: SaleOutcome mutation was incorrectly coupled to current `OrganizationPublishingEligibility`.

Accepted correction:

- SaleOutcome mutation requires current ACTIVE matching membership + PUBLISHER role;
- privileged PUBLISHER still requires MFA through the existing Broker Workspace boundary;
- current Organization publishing eligibility does not gate historical/commercial close-out truth;
- Organization/listing ownership, Lead linkage, concurrency and lifecycle invariants remain enforced;
- member-only / inactive / foreign access fail closed;
- reason-bearing `publishing_denied` semantics were removed from this boundary.

Final accepted HEAD:

`0984a7f792003f816fccdd8601b4e9bf0a543ffd`

No unresolved material finding remains.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- explicit publisher-scoped SOLD outcome
- immutable SaleOutcome revision/current-head history
- correction/superseding revisions
- optional sold_date
- optional achieved sale price/currency
- optional originating Lead linkage
- ACTIVE→WITHDRAWN atomic close-on-SOLD
- SOLD recording/correction on already-WITHDRAWN listing
- PUBLISHER/current-membership/MFA mutation boundary
- SaleOutcome independence from OrganizationPublishingEligibility
- cross-Organization MarketEpisode isolation
- authoritative current broker read surface

DECIDED_NOT_YET_IMPLEMENTED
- canonical global ResolvedMarketEpisodeOutcome
- responsible broker/member field
- inventory export
- pre-publication Search-fit diagnostics
- engagement/performance reporting
- structured bulk import
- volume-dependent exclusion/demand insights

EXPLICITLY_DEFERRED
- global automatic propagation of one publisher SOLD report
- generalized CRM/deal pipeline
- payment activation
- owner-direct sale outcome
- new Search criteria

GENUINELY_OPEN
- later canonical episode-outcome evidence resolution
- future additional explicit outcome vocabulary if separately decided

CONFLICT_OR_REGRESSION
- none remain
```

## Exact-head verification

Accepted exact HEAD `0984a7f792003f816fccdd8601b4e9bf0a543ffd`:

```text
db integration (PostgreSQL 18): SUCCESS
quality (ubuntu-latest): SUCCESS
quality (windows-latest): SUCCESS
historical research/bootstrap replay: SUCCESS
web quality: SUCCESS
dependency audit: SUCCESS
reproduce (ubuntu-latest): SUCCESS
reproduce (windows-latest): SUCCESS
```

Focused local validation covered the new SaleOutcome unit/API/PostgreSQL behavior plus affected lifecycle/authorization/web paths. The full local backend suite was intentionally not rerun under the accepted focused-local / authoritative-remote policy.

## Mandatory capability register consequence

SLICE-0074 satisfies the already-normative REQ-BROKER-006 explicit sale/outcome obligation.

Therefore closure updates:

```text
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: IMPLEMENTED
```

This does not make the Broker Workspace Launch Gate PASS and does not activate paid/public launch.

## Trigger-gate state

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

## PROJECT_STATE freshness closure

```text
PROJECT_STATE_ACCEPTED_SLICE: 0074
PROJECT_STATE_QUEUE_SLICE:    0075
```

SLICE-0075 remains UNSELECTED until fresh post-SLICE-0074 reconciliation.

## Closure decision

```text
SLICE-0074 = OWNER_ACCEPTED
BROKER_SALE_OUTCOME_WORKFLOW_STATUS = IMPLEMENTED
PROJECT_STATE_ACCEPTED_SLICE = 0074
PROJECT_STATE_QUEUE_SLICE = 0075
```

Implementation is merged. `FINISH_SLICE.bat` may run only after this closure PR passes exact-head closure review, required remote gates and merge.
