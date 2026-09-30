# SLICE-0072 — Acceptance Closure

**ID:** SLICE-0072  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #278  
**Accepted implementation HEAD:** `bc9e2987ae7b6ea44b2ba4336f4eece8751897fe`  
**Implementation merge commit:** `7929e418488de8dc8a3ff1a179b6d0624b044ca3`  
**Independent exact-head ACCEPT review:** 2026-09-30  
**Owner acceptance:** explicitly recorded 2026-09-30

## Accepted capability

SLICE-0072 closes the post-promotion professional inventory maintenance loop for existing Organization-owned NativeListings:

```text
existing Organization-owned NativeListing
→ authoritative private inventory detail
→ edit current offer / price
→ edit current Organization PhysicalBoat claims
→ append immutable revision
→ atomically advance authoritative head
→ authoritative re-read
→ current public/Search truth reflects accepted claim/offer effects
```

Lifecycle operations remain separate. Editing a WITHDRAWN listing does not republish it, offer edits do not refresh freshness/lifecycle state, and ACTIVE edits may not violate canonical current-public hard invariants.

## Accepted implementation behavior

- private Broker Workspace inventory editor for existing Organization-owned NativeListings;
- current offer and Organization PhysicalBoat claim heads are authoritative;
- offer editing supports existing bounded price/location/narrative/tax-claim semantics;
- PhysicalBoat claim editing supports marketed brand/model, build year, LOA, draft, keel, rudder and boat name under the accepted assertion model;
- each successful mutation appends an immutable revision and advances exactly one authoritative current head;
- stale expected-head writes reject via exact optimistic concurrency;
- retry identity is idempotent and reused identity with different payload conflicts;
- cross-Organization and unknown inventory remain non-enumerating;
- current ACTIVE public/Search projections consume accepted current truth without creating a second truth store;
- ACTIVE edits are checked inside the same transaction against canonical current-public hard invariants and reject atomically if invalid;
- WITHDRAWN editing remains editing only and exposes no republish shortcut;
- offer/price edits do not touch freshness, lifecycle or sale/outcome state;
- media and Lead state remain unchanged;
- technical native Search criteria remain exactly two: `draft_max` and `keel_configuration`;
- browser/API surface remains private, no-store/noindex and reuses accepted session/CSRF/MFA/current-membership authorization;
- frozen promoted-draft truth is not rewritten.

## Independent review and amendments

Initial implementation HEAD `f599e745a90a62f57a183ecc747b26a9519e46dc` implemented the vertical. Independent exact-head review found two missing acceptance proofs: the retained real PostgreSQL + FastAPI + built-Astro proof and true concurrent-write proof.

Amendment HEAD `d851efb4b51f649744a864363fb3f34f47d76d59` added the retained end-to-end inspection script and synchronized two-connection offer/claim concurrency tests proving one winner, one conflict, correct final head and immutable history.

Amendment HEAD `b22e3c9a37b2216016d1c30b29fe7152648bec8c` fixed remote format/type gates and upgraded `urllib3` from 2.7.0 to 2.8.0 for CVE-2026-97687 / CVE-2026-97688 / CVE-2026-97689. The formatter exposed a genuine mypy generic-return typing defect, corrected without behavior change.

Docs-sync HEAD `677a2066a6ea61cce9a4c456f302bbd58dfa68c2` recorded those amendment reports.

Dependency amendment HEAD `5494981ee9ff99cc55d2474c9b5c6710fe05b5f2`, followed by docs-sync HEAD `acdad5ffdbf1f09b6fd44cd46676c3dc34a0481c`, upgraded direct dependency `pyjwt` from 2.14.0 to 2.15.1 after newly published CVE-2026-101918 / GHSA-42vr-xj54-vc7v. Focused JWT/session-token tests and the full backend suite remained green.

Coverage amendment HEAD `f663f20c04ab5b8be6b9f2e095b411bed26dc972`, followed by docs-sync final HEAD `bc9e2987ae7b6ea44b2ba4336f4eece8751897fe`, closed a real coverage deficit in the new SLICE-0072 modules with behavioral tests only. No production code changed, `fail_under=90` was not lowered and no production file was excluded.

No material implementation finding remains.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- authoritative post-promotion professional inventory detail
- immutable NativeListing offer editing
- immutable Organization PhysicalBoat claim editing
- exact optimistic concurrency for both mutation families
- idempotent retry / reused-identity conflict semantics
- atomic ACTIVE hard-invariant protection
- authoritative post-save re-read
- current public offer propagation
- current PhysicalBoat claim propagation into accepted public/Search truth
- lifecycle/freshness/media/Lead separation
- private Broker Workspace authorization / MFA / CSRF / no-store / noindex
- technical native Search criteria remain exactly 2

DECIDED_NOT_YET_IMPLEMENTED
- production email-provider activation
- buyer-contact email verification
- sale/outcome workflow
- broker performance/source-to-outcome analytics
- inventory export / portability
- structured bulk onboarding/import
- Search exclusion explainability
- pre-publication Search-fit diagnostics
- privacy-safe aggregate demand insights
- SavedSearch / Monitor / Alert / price-change alerts
- payments / entitlements
- owner-direct publication/trust path

EXPLICITLY_DEFERRED
- lifecycle redesign
- media redesign
- additional Search criteria
- rewriting frozen promoted-draft truth
- generalized second inventory truth store

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

## Exact-head verification

Remote verification on accepted HEAD `bc9e2987ae7b6ea44b2ba4336f4eece8751897fe`:

```text
quality (ubuntu-latest): SUCCESS
quality (windows-latest): SUCCESS
web quality (Astro/Node): SUCCESS
dependency audit: SUCCESS
reproduce (ubuntu-latest): SUCCESS
reproduce (windows-latest): SUCCESS
db integration (PostgreSQL 18): SUCCESS
```

Implementation-agent final validation recorded:

```text
repository validator: PASS
ruff format / lint: PASS
mypy src: PASS
focused 0072 coverage tests: 88 passed
full backend suite: 5900 passed / 3 skipped / 0 failed
full coverage: 90.84% (threshold 90.00%)
focused JWT/session-token tests: 33 passed
pip-audit: clean
retained SLICE-0072 real PostgreSQL + FastAPI + built Astro proof: PASS
concurrent offer/claim write proof: PASS
```

PR #278 merged the exact accepted implementation to `main` as `7929e418488de8dc8a3ff1a179b6d0624b044ca3`.

## Trigger-gate state after acceptance

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

No real external broker/buyer production traffic, production pilot, paid plan or public production launch begins in 0072.

## Broker launch execution checkpoint

```text
BROKER CREATES               [implemented]
→ BROKER ADDS MEDIA          [implemented]
→ BROKER PUBLISHES           [implemented]
→ BUYER CONTACTS             [implemented]
→ BROKER HANDLES LEAD        [implemented]
→ BROKER EDITS / MAINTAINS INVENTORY [implemented through SLICE-0072]
→ BROKER CLOSES / RECORDS OUTCOME
```

The Broker Workspace Launch Gate remains NOT_READY. Sale/outcome handling, launch-level performance/source-to-outcome analytics, usability/competitive benchmark evidence and other remaining mandatory commitments still require reconciliation.

## PROJECT_STATE freshness closure

```text
PROJECT_STATE_ACCEPTED_SLICE: 0072
PROJECT_STATE_QUEUE_SLICE:    0073
```

SLICE-0073 is **UNSELECTED** until fresh post-SLICE-0072 reassessment completes.

The owner has separately directed that test/CI throughput optimization occur at the earliest safe opportunity after SLICE-0072 closure and before the next normal feature slice. That engineering-priority record is not part of the accepted SLICE-0072 implementation itself.

## Closure decision

```text
SLICE-0072 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0072
PROJECT_STATE_QUEUE_SLICE = 0073
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. `FINISH_SLICE.bat` may run only after this closure PR passes independent exact-head closure review, required remote gates and guarded merge.
