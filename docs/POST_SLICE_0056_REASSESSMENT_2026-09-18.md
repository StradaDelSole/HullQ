# HullQ — Post-SLICE-0056 Product / Repository Reassessment

**Date:** 2026-09-18  
**Status:** RECONCILED EXECUTION SELECTION — no new product/domain decision required  
**Canonical base inspected:** `3b6391cf478b877d6a165e94642af32e4c714f37`  
**Selected next slice:** SLICE-0057 — Buyer Requirement Sensitivity

## 1. Reassessment result

Select **SLICE-0057 — Buyer Requirement Sensitivity**.

This is the smallest high-leverage buyer capability that directly uses the evidence-preserving Search foundation now completed through SLICE-0056.

The accepted buyer-product direction already says that a buyer may ask a factual one-change-at-a-time question such as:

```text
If maximum draft changed from 1.60 m to 1.70 m,
what would change in the confirmed result set?
```

The accepted direction is explicitly:

- buyer initiated;
- one requirement change at a time;
- deterministic;
- reversible;
- factual;
- no automatic optimization;
- no recommendation about which criterion should change;
- no score/winner/hidden preference model.

SLICE-0055 deliberately retained typed design/configuration and concrete criterion evidence for confirmed match, confirmed non-match and insufficient-data outcomes. SLICE-0056 then made the accepted two-criterion Direct Search faithfully usable from the canonical public browser surface.

The remaining gap is a buyer-visible projection of that already accepted evaluation capability.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- Direct Search remains the primary low-friction buyer entry point;
- current hard public criteria are exactly `draft_max` and `keel_configuration`;
- either criterion may be used alone and both may be combined as deterministic hard MUST/AND;
- exact Decimal/canonical `draft_max` semantics;
- exact six-value public `keel_configuration` vocabulary;
- BoatDesign/configuration truth remains separate from PhysicalBoat/listing truth;
- `CONFIRMED_MATCH`, `CONFIRMED_NON_MATCH` and `INSUFFICIENT_DATA` remain mechanically distinct;
- missing/UNKNOWN evidence never becomes a match;
- FastAPI is the sole Search/application truth boundary;
- public locale-prefixed Search routes exist for `en`, `de`, `fr`, `pt`, `es`;
- public Search state is deterministic/canonical and remains `noindex`;
- SLICE-0055 retains full typed evidence for keel-involving Search outcomes;
- SLICE-0056 browser/API projection now faithfully represents both accepted criteria;
- organic Search eligibility, match classification and ordering remain commercially independent;
- buyer decision tools must not produce a winner, score, best-fit claim or hidden preference weighting.

### DECIDED_NOT_YET_IMPLEMENTED

The accepted-but-unimplemented buyer obligation selected here is:

> A buyer may explicitly change exactly one active hard requirement and inspect the factual delta in deterministic Search results without HullQ recommending that change.

The owning accepted direction is `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`, especially Requirement Sensitivity Analysis / `Why no match?`.

### EXPLICITLY DEFERRED

Remain outside SLICE-0057:

- persisted `BuyerRequirements`;
- MUST_HAVE/PREFER/DONT_CARE authoring;
- anonymous-to-account requirement migration;
- automatic suggestion of alternative values;
- HullQ-generated relaxation strategy;
- multi-criterion optimization;
- preference weighting/ranking;
- overall fit scores / winners / recommendations;
- Shortlist / Compare / sharing;
- Saved Search / Monitor / alerts;
- Rare Match;
- a third Search criterion;
- broker Search-exclusion intelligence;
- owner-direct publication/admission;
- Broker Workspace listing/media/lead expansion;
- broad/indexable SEO.

### GENUINELY_OPEN

The broader BuyerRequirements domain identity/schema/lifecycle remains open, but it is **not required** for this slice.

SLICE-0057 operates only on the two already-active Direct Search criteria and one buyer-supplied proposed replacement value. It creates no persisted buyer object.

No new owner product decision is required for this bounded capability.

### CONFLICT_OR_REGRESSION

None found after accepted SLICE-0056 and the post-0056 workflow reassessment.

## 3. Existing implementation foundation

Canonical implementation already provides:

```text
search_read.evaluate_search_request
→ existing request parsing/canonicalization
→ DraftMaxSearchOutcome OR NativeInventorySearchOutcome
```

For keel-only/mixed Search, `NativeInventorySearchOutcome` retains:

- exact evaluated query;
- confirmed matches;
- confirmed non-matches;
- insufficient-data candidates;
- complete design evaluation;
- design/configuration evidence;
- concrete criterion evidence.

For pure `draft_max`, the accepted legacy result retains confirmed listing identities plus separate non-match/insufficient counts.

Therefore a one-change sensitivity result can be derived by executing the **same accepted Search evaluation** twice — current requirements and buyer-supplied alternative — and comparing only stable confirmed `NativeListingId` result sets.

No second Search truth/evaluation engine is required or authorized.

## 4. Mandatory Broker Capability Register check

Canonical broker state remains:

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

No broker requirement is currently `DUE`.

REQ-BROKER-023/024 remain mandatory before Broker Workspace Launch Gate PASS. They are not silently waived.

A Broker Listing Draft Workspace is strategically important, but current accepted requirements do not yet define the professional draft-edit role matrix (for example whether only `PUBLISHER`, or also other Organization roles, may mutate pre-publication draft state) or whether Organization publishing eligibility must gate drafting versus only publication. Those semantics should be reconciled in the owning professional inventory slice rather than invented inside this buyer slice.

The current buyer-value risk therefore has higher immediate product leverage than prematurely choosing that professional permission model.

## 5. Owner-direct / mixed-supply reconciliation

The owner-direct direction was inspected because this slice touches Search.

SLICE-0057:

- does not change listing/supply admission;
- does not change seller trust/verification;
- does not create referral economics;
- does not change Search eligibility/classification/order;
- does not use seller/broker payment or HullQ revenue as a Search input.

Therefore all `REQ-PRIVATE-003` organic Search independence obligations remain unchanged.

Owner-direct publication remains a later accepted direction but requires its own phone reachability, right-to-list attestation, anti-abuse and marketplace-admission boundary. That is materially broader than the selected buyer sensitivity projection.

## 6. Trigger gates

Canonical trigger state:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

SLICE-0057:

- adds **no** technical native Search criterion;
- does not trigger the criterion #3 abstraction gate;
- uses synthetic/internal retained proof only;
- introduces no real external production seller/listing data;
- starts no production pilot;
- changes no public production launch marker.

Production Readiness remains `NOT_TRIGGERED`.

## 7. Alternatives considered

### A. Buyer Requirement Sensitivity — SELECTED

Highest immediate product leverage after the two-criterion Direct Search became coherent.

It exposes HullQ's differentiating deterministic evidence to a buyer **before signup**, directly matching the accepted product principle:

> signup unlocks continuity, not discovery.

It also advances the Product UX baseline requirement for a concise `why`/evidence path without inventing recommendation semantics.

### B. Professional Broker Listing Draft Workspace

Not selected now.

Strategically important and required before a coherent broker pilot, but exact professional pre-publication draft mutation permissions remain insufficiently specified. No broker requirement is currently `DUE`.

### C. Owner-direct publication/admission

Not selected now.

Accepted direction exists, but publication requires a broader trust/admission boundary: verified phone reachability, right-to-list attestation, baseline anti-abuse and explicit marketplace promotion from private draft state.

### D. Third technical Search criterion

Not selected.

The existing two criteria are sufficient to deliver/test a more differentiated buyer experience. Criterion #3 would increase breadth and invoke the accepted third-copy abstraction guard without addressing the more immediate explainability/value layer.

### E. Saved Search / monitoring / alerts

Not selected.

Strong strategic candidate, but exact persistence/alert/reactivation/account-limit semantics remain intentionally open. Sensitivity has a fully accepted product boundary and requires no persistence/account work.

## 8. Selected capability boundary

SLICE-0057 delivers exactly one public buyer capability:

> From a valid current Direct Search, the buyer may explicitly choose one currently active hard criterion, supply one alternative value, and see the factual change in confirmed matching listings while all other active criteria remain unchanged.

Examples:

```text
current:
draft_max=1.6
keel_configuration=FIN

buyer changes only:
draft_max -> 1.7

HullQ shows:
current confirmed set
alternative confirmed set
newly confirmed set
no-longer-confirmed count/set
current vs alternative insufficient-data count
canonical link to apply the buyer-selected alternative
```

or:

```text
current:
keel_configuration=FIN

buyer changes only:
keel_configuration -> TWIN_KEEL
```

HullQ does **not** say which value is better and does not suggest a value.

## 9. Product execution checkpoint

Remaining slice distance to the first externally visible listing remains:

```text
0
```

That threshold was reached earlier.

This slice is not foundation-only. Its result is directly visible and executable by a buyer in the public Search journey.

It advances the currently accepted pre-Gate-1 buyer-value objective by exposing a distinctive factual decision-support interaction before requiring signup.

## 10. Decision

**Selected execution obligation:** `SLICE-0057 — Buyer Requirement Sensitivity`.

Readiness may proceed without a new product/domain decision.

Implementation may not start until the readiness package is independently exact-head reviewed, remote gates are green and the readiness PR is merged to canonical `main`.
