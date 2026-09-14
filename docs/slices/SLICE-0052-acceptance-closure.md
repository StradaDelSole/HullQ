# SLICE-0052 — Acceptance closure

**Slice:** SLICE-0052  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #193  
**Original implementation HEAD:** `3c2f1fed28146751352ee7ac02fc8ac8952b2b88`  
**First exact review HEAD after canonical-main reconciliation:** `b09c63641cb7f2b88c8daf1cd2180ff3e5039064`  
**Accepted implementation HEAD:** `510d392ecb4267fdecebb95073bcc6a4595c6cfb`  
**Implementation merge commit:** `bb36c29dee1b633474b7153539b8135f4b57b110`  
**Owner acceptance:** explicitly recorded 2026-09-14

## Accepted capability

SLICE-0052 adds evidence-backed NativeListing freshness / reconfirmation for manual/operator-assisted professional native listings.

It closes the current-inventory trust gap that previously allowed an `ACTIVE` listing to remain buyer-visible indefinitely merely because no later withdrawal had been recorded.

The accepted production policy is exactly:

```text
MANUAL_NATIVE_V1
confirmation TTL = 30 days
grace period     = 7 days
stale boundary   = 37 days after effective confirmation
```

Freshness remains a state dimension separate from lifecycle:

```text
LifecycleState != FreshnessStatus
```

Accepted freshness vocabulary:

```text
CONFIRMED
DUE_FOR_CONFIRMATION
STALE
UNKNOWN
```

The accepted lifecycle remains unchanged:

```text
DRAFT → ACTIVE → WITHDRAWN
```

Time passage never creates `WITHDRAWN`, `SOLD` or any other lifecycle transition.

## Evidence and deterministic evaluation

Freshness derives from immutable evidence only:

1. the accepted `DRAFT → ACTIVE` publication transition timestamp; and
2. later successful explicit reconfirmation events.

No migration/deployment-time freshness reset is allowed. An ACTIVE listing with no admissible confirmation evidence resolves `UNKNOWN` and is suppressed from current buyer inventory.

Given effective `confirmed_at` and an explicit timezone-aware `as_of`:

```text
as_of < confirmed_at + 30d
→ CONFIRMED

confirmed_at + 30d <= as_of < confirmed_at + 37d
→ DUE_FOR_CONFIRMATION

as_of >= confirmed_at + 37d
→ STALE

no admissible evidence
→ UNKNOWN

confirmed_at > as_of
→ UNKNOWN
```

The exact +30-day and +37-day boundaries are covered by retained tests/proof.

## Reconfirmation contract

A successful reconfirmation:

- requires explicit Account, Organization, Membership and NativeListing identities;
- reuses the accepted professional publishing-eligibility evaluator;
- requires the candidate Organization to own the listing;
- requires lifecycle `ACTIVE`;
- appends one immutable reconfirmation event;
- records `occurred_at` system/database-side;
- accepts no arbitrary caller confirmation timestamp;
- uses a stable caller-supplied `FreshnessConfirmationId` for retry semantics.

Accepted retry behavior:

```text
same id + same immutable envelope
→ ALREADY_EXISTS

same id + different immutable envelope
→ CONFLICT
```

Denied, cross-Organization, missing, DRAFT, WITHDRAWN and conflicting-ID attempts append no new confirmation event and do not mutate listing lifecycle/facts.

Real PostgreSQL concurrency coverage proves distinct concurrent valid reconfirmations can both become true immutable events without corrupting lifecycle or each other.

## Current buyer-surface eligibility

Accepted current-market predicate:

```text
ACTIVE + CONFIRMED
ACTIVE + DUE_FOR_CONFIRMATION
→ current buyer eligible

ACTIVE + STALE
ACTIVE + UNKNOWN
→ suppressed from current buyer listing/Search surfaces
```

Suppression does not alter durable lifecycle/history and does not infer sale/withdrawal.

Visible public listing and Search projections carry:

```text
freshness_status
last_confirmed_at
```

`DUE_FOR_CONFIRMATION` is buyer-visible and must not be rendered as simply confirmed.

## Native-inventory Search interaction

SLICE-0052 adds no new technical Search criterion.

The existing SLICE-0051 `draft_max` candidate path now excludes STALE/UNKNOWN inventory before technical classification. Freshness exclusion therefore does not increment technical `INSUFFICIENT_DATA` counts.

CONFIRMED and DUE listings retain all accepted SLICE-0051 design/configuration, FieldResolution, exact Decimal, PhysicalBoat and contradiction-guard semantics.

The accepted technical native Search criteria count remains:

```text
1
```

## Buyer-facing amendment and truth wording

The first exact-head review identified one buyer-facing truth-semantics issue: the public listing page still described `offer_recorded_at` as "recorded/last confirmed" even though a reconfirmation can advance `last_confirmed_at` without creating a new offer revision.

That wording could expose two different timestamps as "last confirmed" on the same listing.

The accepted amendment separates the semantics:

```text
offer_recorded_at
→ LISTING_OFFER revision recorded time only

last_confirmed_at
→ sole buyer-facing freshness confirmation time
```

The final wording no longer assigns freshness semantics to `offer_recorded_at`, and focused web regression tests prove differing offer-recorded and freshness-confirmed timestamps are not conflated.

## Retained real vertical proof

The committed retained proof runs against real PostgreSQL 18, real FastAPI and built Astro SSR and demonstrates:

```text
publish
→ ACTIVE + CONFIRMED
→ public listing visible
→ matching Search result visible

exact +30d
→ DUE_FOR_CONFIRMATION
→ still visible with due disclosure

exact +37d
→ STALE
→ absent from public current-listing content
→ absent from Search
→ lifecycle remains ACTIVE

authorized reconfirmation
→ CONFIRMED
→ listing and Search visibility restored
```

It additionally proves UNKNOWN suppression, cross-Organization/DRAFT denial with zero reconfirmation rows, exact-retry idempotency, conflicting-ID fail-closed behavior and preservation of the SLICE-0051 technical result shape.

The proof is wired into PostgreSQL-18 CI.

## Exact-head review history

Original implementation-agent handoff:

```text
3c2f1fed28146751352ee7ac02fc8ac8952b2b88
```

Before implementation review, the already owner-accepted Broker Workspace governance PR #192 was merged to canonical `main`. Because SLICE-0052 had been started from the preceding main head, the implementation branch was reconciled with canonical main without changing slice logic.

First exact review head:

```text
b09c63641cb7f2b88c8daf1cd2180ff3e5039064
```

Remote verification on that head passed, but independent review returned `REQUEST_CHANGES` for the `offer_recorded_at` / `last_confirmed_at` buyer-facing wording conflict.

Final amended head:

```text
510d392ecb4267fdecebb95073bcc6a4595c6cfb
```

The amendment touched only:

- `web/src/pages/listings/[native_listing_id].astro`;
- `web/src/lib/previewText.ts`;
- `web/src/lib/__tests__/previewText.test.ts`.

The fresh independent exact-head review returned:

```text
ACCEPT
```

Review ID: `5196363598`.

The Project Owner explicitly accepted that exact implementation head on 2026-09-14.

## Exact-head verification

Exact accepted implementation HEAD:

```text
510d392ecb4267fdecebb95073bcc6a4595c6cfb
```

Remote verification on that exact SHA:

```text
CI run #695 / 34791506791
→ SUCCESS

Manufacturer artifact reproducibility run #417 / 34791506808
→ SUCCESS
```

The PostgreSQL 18 CI path successfully executed the retained SLICE-0052 NativeListing freshness real HTTP vertical proof.

Implementation-agent final amendment validation reported:

```text
web npm test: 30/30 PASS
web npm run check: PASS
web npm run build: PASS
mypy src: PASS
```

The broader historical `mypy src tests scripts` command is not claimed as a passing gate; repository CI intentionally uses `mypy src`.

Implementation PR #193 merged the exact owner-accepted head to `main` as:

```text
bb36c29dee1b633474b7153539b8135f4b57b110
```

## Scope retained / explicitly deferred

SLICE-0052 deliberately does not add:

- Auth0 integration or broker workspace UI;
- persisted general actor directory;
- email/push/browser freshness reminders;
- a scheduler/background mutation merely to advance freshness;
- feed-driven freshness/source-health semantics;
- `WITHDRAWN → ACTIVE` republish;
- `SOLD` or `ARCHIVED` lifecycle states;
- Saved Search / Monitor / Alert persistence;
- price/status history intelligence;
- media;
- a second technical Search criterion;
- generic all-field Search/FieldResolution infrastructure;
- broad/indexable SEO.

Those remain subject to later bounded capability selection, except where the accepted Broker Workspace Mandatory Capability Register makes a later capability explicitly mandatory.

## Trigger-gate state after acceptance

SLICE-0052 does not activate a production/pilot trigger and does not add a technical Search criterion.

Current gate state remains:

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

The Broker Workspace Mandatory Capability Register remains controlling for mandatory-but-not-yet-implemented broker commitments. Every normal post-slice capability reassessment must inspect that register and explicitly account for any `DUE` requirement, changed trigger, sale/outcome gate and evidence needed by still-PENDING commitments.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0052
PROJECT_STATE_QUEUE_SLICE:    0053
```

`SLICE-0053` is only the next queue number. **This closure does not select a SLICE-0053 capability and does not authorize implementation.**

The next capability must be selected through post-SLICE-0052 product/architecture reassessment and repository reconciliation. That reassessment must inspect `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md` before choosing the next primary capability.

Repository validation must fail this closure if the `PROJECT_STATE_ACCEPTED_SLICE` marker and highest acceptance-closure filename are not identical.

## Product execution checkpoint

HullQ now has a bounded end-to-end buyer path in which public native inventory is not only lifecycle-active and technically searchable, but also time-bounded by explicit professional confirmation evidence.

The next reassessment should choose the smallest highest-leverage continuation across the two core product surfaces:

```text
Buyer side
→ trustworthy technical discovery

Provider side
→ best-in-class Broker Workspace
```

It must not assume that broader Search, Saved Search, Auth0, media, contact/leads or another technical criterion is automatically next. It must reconcile actual repository state, trigger gates and the Broker Workspace Mandatory Capability Register first.

No future slice number beyond queue `0053` is allocated by this closure.

## Closure decision

```text
SLICE-0052 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
