# HullQ — Post-SLICE-0055 Capability Reassessment

**Date:** 2026-09-18  
**Status:** RECONCILED EXECUTION SELECTION — no new product/domain decision required  
**Canonical base inspected:** `8f3a76eebabfba5c17af7d3026f22d1f4dc292da`  
**Selected next slice:** SLICE-0056 — Public Multi-Criterion Direct Search Browser Completion

## 1. Reassessment result

Select **SLICE-0056 — Public Multi-Criterion Direct Search Browser Completion**.

This is a corrective execution slice, not a new Search-semantic decision.

SLICE-0055 was owner-accepted as a visible buyer capability:

```text
keel_configuration
alone
or
draft_max + keel_configuration
→ deterministic native-inventory Direct Search
→ confirmed matching listings only in the primary result set
```

Canonical production code now implements that meaning through FastAPI/application Search, but the public Astro Search surface still uses the old SLICE-0051 browser contract and therefore cannot faithfully execute/render the accepted SLICE-0055 capability.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- exact `draft_max` semantics and canonical Decimal handling;
- accepted six-value `keel_configuration` v0.1 vocabulary;
- keel-only and draft+keel FastAPI/native-inventory evaluation;
- deterministic hard MUST/AND truth semantics;
- FieldResolution-qualified BoatDesign/configuration truth;
- concrete PhysicalBoat contradiction/missing-data fail-closed behavior;
- typed design/configuration and concrete criterion evidence retained by the SLICE-0055 application outcome;
- listing freshness gating from SLICE-0052;
- public locale-prefixed SSR Search routes;
- deterministic query-parameter Search state;
- FastAPI-owned canonicalization/400/308 behavior;
- Search routes remain public/usable but `noindex`;
- organic Search commercial independence.

### CONFLICT_OR_REGRESSION

The accepted visible SLICE-0055 buyer capability is not fully represented by the canonical browser implementation.

Current `web/src/components/SearchPageBody.astro`:

- exposes only a `draft_max` input;
- summarizes only `activeRequirement.draft_max`;
- renders every confirmed result through `match.resolved_draft_m`.

Current `web/src/lib/searchApi.ts` and `searchPageData.ts` type:

```text
active_requirement = { draft_max: string } | null
confirmed match = resolved_draft_m + ...
```

But canonical FastAPI now returns for keel-only/mixed Search:

```text
active_requirement = {
  draft_max?: string,
  keel_configuration?: string
}

confirmed match = {
  native_listing_id,
  freshness_status,
  design_evaluation,
  design_configuration_evidence,
  criterion_evidence,
  ...
}
```

The existing browser therefore cannot submit keel through its form and a direct keel/mixed URL is rendered through a stale SLICE-0051-only result model.

This is a repository conflict/regression against the already accepted SLICE-0055 visible-result contract. It does **not** create a new owner question about whether keel belongs in Direct Search.

### DECIDED_NOT_YET_IMPLEMENTED

The remaining corrective obligation is:

> make the existing public SSR Search surface faithfully support the already accepted keel-only and draft+keel Direct Search states and their confirmed-match evidence without duplicating Search truth or canonicalization in TypeScript/Astro.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0056:

- a third technical Search criterion;
- BuyerRequirements persistence or guided requirement authoring;
- PREFER / DONT_CARE semantics;
- buyer `Why no match?` sensitivity analysis;
- individualized non-match/insufficient explainability beyond the already accepted separate count/state;
- shortlist/Compare/sharing;
- Saved Search/alerts/monitoring;
- broker aggregate Search intelligence;
- owner-direct publication/admission;
- Broker Workspace inventory/media/lead expansion;
- broad/indexable SEO landing pages.

### GENUINELY_OPEN

No material product/domain/architecture decision blocks this corrective slice.

## 3. Mandatory Capability Register check

The Broker Workspace Mandatory Capability Register was inspected.

Current launch/mandatory state remains:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING

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

No broker requirement is currently `DUE`. REQ-BROKER-023/024 remain mandatory before the Broker Workspace Launch Gate can pass, but correcting a known accepted buyer-facing regression has higher immediate integrity/product leverage than beginning an unrelated broker baseline slice while the current public Search surface is inconsistent.

## 4. Trigger gates

Canonical trigger state:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: NOT_DUE

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

SLICE-0056 adds no new technical criterion and introduces no external production data/pilot/launch.

The workflow reassessment remains `NOT_DUE` during SLICE-0056 execution. **If SLICE-0056 becomes owner-accepted, its acceptance closure must atomically move `WORKFLOW_REASSESSMENT_STATUS` to `DUE`; SLICE-0057 readiness/start is then blocked until the required evidence-based workflow reassessment is owner-accepted and the marker becomes `PASS`.**

## 5. Alternatives considered

### A. Public Multi-Criterion Direct Search Browser Completion — SELECTED

Closes a known accepted buyer-surface regression with no new Search semantics and makes the just-built criterion #2 genuinely usable from the canonical public Search UI.

### B. Third technical Search criterion

Not selected. It would add breadth while the browser cannot yet faithfully expose criterion #2, and criterion #3 would additionally invoke the third-copy abstraction guard.

### C. BuyerRequirements / sensitivity / `Why no match?`

Not selected. SLICE-0055 intentionally retained evidence to enable these later, but the basic Direct Search browser must first represent the accepted two-criterion Search correctly.

### D. Broker Workspace inventory/resilient drafts/branding

Strategically important and still mandatory before broker pilot/launch. No item is currently DUE, and leaving a known public Search regression unresolved would violate the decision/implementation reconciliation rule.

### E. Owner-direct publication

Accepted future direction, but it requires a separate publication/trust boundary (phone reachability, right-to-list attestation, anti-abuse and ordinary marketplace admission). It is materially broader and riskier than the bounded corrective browser gap.

## 6. Selected capability boundary

SLICE-0056 delivers exactly one visible capability:

> A buyer using the canonical public HullQ Search page can enter `draft_max`, `keel_configuration`, or both; the URL, active-requirement summary and confirmed-result evidence faithfully represent the same already-accepted FastAPI Search state.

No new Search truth is implemented in Astro/TypeScript.

## 7. Product execution checkpoint

Remaining slice distance to the first externally visible listing remains:

```text
0
```

That threshold was reached earlier. SLICE-0056 instead closes the mismatch between the accepted two-criterion production Search engine and its public buyer browser surface.

## 8. Decision

**Selected execution obligation:** `SLICE-0056 — Public Multi-Criterion Direct Search Browser Completion`.

Readiness may proceed without re-deciding criterion semantics. Implementation may not start until the readiness contract is independently reviewed, green and merged to canonical `main`.
