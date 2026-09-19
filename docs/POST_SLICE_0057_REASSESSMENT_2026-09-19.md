# HullQ — Post-SLICE-0057 Product / Repository Reassessment

**Date:** 2026-09-19  
**Status:** RECONCILED EXECUTION SELECTION — bounded owner-approved capability  
**Canonical base inspected:** `bc3759aa2e7a1df0eea3b669da293f76a3541bde`  
**Selected next slice:** SLICE-0058 — Anonymous Local Shortlist

## 1. Reassessment result

Select **SLICE-0058 — Anonymous Local Shortlist**.

SLICE-0057 completed the first buyer-authored factual sensitivity interaction on top of Direct Search. The next smallest high-leverage buyer capability is not another Search criterion but a durable-in-the-browser expression of buyer interest:

```text
buyer sees a current listing
→ buyer explicitly saves its NativeListingId locally
→ buyer can revisit one personal shortlist
→ HullQ re-resolves current public listing truth when viewed
```

This directly advances the accepted buyer loop from discovery/evaluation toward later Compare / Monitor / Contact while preserving the hard product invariant:

> Shortlisting expresses buyer interest, not HullQ fit.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- public current NativeListing identity is `NativeListingId`;
- public listing reads already resolve only ACTIVE + complete-chain + current-market-eligible inventory;
- DRAFT, WITHDRAWN, missing, incomplete, STALE and freshness-UNKNOWN public reads collapse to the accepted unavailable/not-found boundary rather than leaking lifecycle/existence detail;
- current public listing truth comes from FastAPI/application read models, not browser copies;
- Direct Search returns stable NativeListing identities for confirmed current matches;
- Search and listing truth remain independent of buyer interest state;
- buyer decision tools must not create recommendation scores, winners or hidden ranking;
- Direct Search remains available anonymously;
- signup unlocks continuity rather than discovery;
- FastAPI remains the sole application/domain truth boundary;
- Astro is the main web framework; client-side code may support interaction but may not become a second truth engine;
- public Search commercial independence remains unchanged;
- SLICE-0057 sensitivity remains read-only and creates no buyer persistence.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted buyer direction already requires:

- an ordinary personal Shortlist distinct from Search state and Buyer Requirements;
- shortlist membership only through explicit buyer action;
- no automatic add/remove based on requirement evaluation;
- anonymous/local shortlist behavior where practical;
- persistent account continuity later, not as a prerequisite for anonymous discovery.

The selected 0058 obligation is the smallest implementable subset:

> one anonymous browser-local shortlist of stable NativeListingIds with explicit add/remove and current-truth re-resolution.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0058:

- authenticated/server-persisted Shortlist;
- cross-device continuity;
- anonymous-to-account shortlist migration;
- multiple/named lists;
- shortlist limits as a Free/Pro entitlement;
- Compare;
- private notes;
- sharing/share tokens;
- BuyerRequirements projection against a shortlist;
- Saved Search / Monitor / alerts;
- seller/broker contact and lead creation;
- automatic removal because a listing no longer matches Search/Requirements;
- recommendation/ranking/best-fit semantics;
- third Search criterion;
- owner-direct publication/admission;
- Broker Workspace expansion;
- telemetry/behavioral inference from shortlist actions.

### GENUINELY_OPEN

Broader Shortlist identity/persistence/account limits and migration semantics remain intentionally open for a later account-continuity slice.

They are **not required** for 0058 because the selected boundary is explicitly browser-local and anonymous.

The local-storage serialization/version and technical corruption/size guards are implementation safety details, not a paid-plan/account entitlement decision.

### CONFLICT_OR_REGRESSION

None found on canonical base `bc3759aa2e7a1df0eea3b669da293f76a3541bde`.

## 3. Existing implementation foundation

Current production behavior already provides:

```text
Search result
→ NativeListingId
→ /listings/{NativeListingId}
→ GET /api/listings/{NativeListingId}
→ PublicListingReadModel
```

The public listing read boundary already supplies the exact fail-closed current-state behavior a shortlist needs.

Therefore 0058 does **not** need a new listing truth model and does not need to store offer/price/freshness/claim data in the browser.

The browser-local shortlist stores only identity/order state. On shortlist display, current listing information is resolved through the existing public FastAPI listing-read semantics or a bounded batch/proxy transport that delegates to those same semantics without inventing new availability truth.

## 4. Mandatory Broker Capability Register check

Canonical broker state remains OPEN/PENDING except implemented REQ-BROKER-030.

No broker requirement is currently triggered/DUE merely because an anonymous buyer can save a listing locally.

0058 neither waives nor implements broker export, branding, resilient broker drafts, Search diagnostics, bulk import, engagement reporting or demand insight.

The capability nevertheless improves the buyer side of the eventual qualified-lead loop by creating an explicit buyer-interest step before later contact/lead work.

## 5. Owner-direct / mixed-supply reconciliation

0058 is supply-neutral.

A `NativeListingId` may later represent professional or owner-direct public inventory under the same marketplace identity rules. The shortlist does not:

- change listing admission/publication;
- infer seller type;
- change seller verification/trust;
- prefer professional or private inventory;
- alter organic Search eligibility/classification/order;
- use payment/referral/verification revenue in membership or ordering.

The owner-direct non-commercial organic Search invariant remains unchanged.

## 6. Trigger gates

Canonical trigger state remains:

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

SLICE-0058:

- adds no technical native Search criterion;
- stores no real external seller/listing production data;
- starts no production pilot;
- changes no public production launch marker;
- creates no server-side buyer persistence.

Production Readiness remains `NOT_TRIGGERED`.

## 7. Alternatives considered

### A. Anonymous Local Shortlist — SELECTED

Highest immediate leverage because it creates an explicit buyer action from the already accepted discovery/evidence surfaces and forms a clean prerequisite for factual Compare.

It is user-visible, anonymous-capable, low infrastructure risk and does not require settling the later account/entitlement model.

### B. Third technical Search criterion

Not selected.

The Search kernel is ready for further criteria and LOA is a credible later candidate, but another filter adds breadth rather than closing the next buyer-action gap. Criterion #3 would also invoke the accepted third-copy abstraction guard.

### C. BuyerRequirements persistence

Not selected.

Its domain identity/schema/lifecycle, anonymous transport and account migration remain genuinely open. Introducing durable buyer intent now would force decisions beyond the selected capability.

### D. Factual Compare

Not selected yet.

Compare is a strong next consumer of a shortlist, but 0058 first establishes explicit buyer-selected membership without conflating interest with fit.

### E. Professional Broker Listing workflow / owner-direct publication

Not selected.

Both remain strategically important but carry materially broader permission, publication, trust, media and/or workflow contracts than the bounded buyer-interest capability.

## 8. Selected capability boundary

0058 delivers exactly one buyer capability:

> An anonymous buyer can explicitly add a public listing to one browser-local shortlist, remove it, and revisit the shortlist. Only stable NativeListingIds are retained locally; current listing truth is re-resolved when viewed.

Hard behavior:

```text
ADD = explicit buyer interest
REMOVE = explicit buyer action
SEARCH/REQUIREMENT CHANGE != automatic shortlist mutation
UNAVAILABLE LISTING != automatic deletion
SHORTLIST ORDER != HullQ ranking
```

A currently unavailable saved ID may be shown only as a neutral unavailable entry. It remains locally saved until the buyer removes it, so transient availability/freshness changes do not silently rewrite buyer intent.

## 9. Product execution checkpoint

This is directly inspectable in the public buyer journey:

```text
Search / Listing
→ Save to shortlist
→ open /{locale}/shortlist
→ current available listings + neutral unavailable saved entries
→ Remove
```

It strengthens the accepted Product Success requirement that HullQ create a clear bridge from technical discovery to useful buyer action.

## 10. Decision

**Selected execution obligation:** `SLICE-0058 — Anonymous Local Shortlist`.

Readiness may proceed on the bounded local-ID-only contract below.

Implementation may not start until the readiness package is independently exact-head reviewed, remote gates are green and the readiness PR is merged to canonical `main`.
