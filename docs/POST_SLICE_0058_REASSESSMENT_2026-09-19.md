# HullQ — Post-SLICE-0058 Product / Repository Reassessment

**Date:** 2026-09-19  
**Status:** RECONCILED EXECUTION SELECTION — accepted Compare direction, bounded anonymous consumer  
**Canonical base inspected:** `f227f0f8689bb807ed2d979304e4ad813365ff58`  
**Selected next slice:** SLICE-0059 — Anonymous Factual Shortlist Compare

## 1. Reassessment result

Select **SLICE-0059 — Anonymous Factual Shortlist Compare**.

SLICE-0058 closed the explicit-interest gap:

```text
Search / public listing
→ explicit buyer Save
→ browser-local NativeListingId shortlist
→ current public truth re-resolved on view
```

The accepted buyer direction already defines factual Compare as the next independent decision tool and the post-SLICE-0057 reassessment explicitly identified Compare as a strong next consumer once shortlist membership existed.

The smallest high-leverage continuation is therefore:

```text
existing anonymous local shortlist
→ compare the saved set
→ re-resolve current public listing truth
→ align current factual offer + concrete-yacht claim fields
→ preserve UNKNOWN / not-supplied / unavailable / service-error distinctions
→ no winner, score or recommendation
```

No account or new durable buyer object is needed.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- one anonymous browser-local Shortlist exists and membership is explicit buyer interest only;
- shortlist persistence is versioned `NativeListingId`-only local state;
- shortlist order is stable buyer-authored/insertion order;
- unavailable listings remain saved until explicit buyer removal;
- opening the shortlist re-resolves current listing truth rather than trusting cached browser facts;
- the same-origin shortlist resolver already distinguishes available, neutral unavailable and service-error outcomes;
- current public listing truth comes from FastAPI `PublicListingReadModel`;
- that projection already contains current offer facts, freshness and the publishing Organization's bounded concrete PhysicalBoat claim snapshot;
- concrete PhysicalBoat claim fields preserve omission/UNKNOWN/VALUE_ASSERTION semantics and never fall back to BoatDesign baseline as yacht truth;
- Direct Search and Requirement Sensitivity remain independent of shortlist membership;
- buyer Decision Tools may not create hidden weights, overall scores, winners, best-fit labels or automatic preference ranking;
- public personalized shortlist surfaces are `noindex` / non-shareable browser-local state;
- FastAPI remains the sole application/domain truth boundary; Astro/TypeScript is presentation/interaction only;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted buyer direction already requires factual Compare:

- Compare is useful independently of guided Buyer Requirements;
- a buyer may compare shortlisted boats side-by-side using factual technical, listing, market and truth/evidence data;
- Compare may expose factual differences but must not declare one value inherently better or worse absent an explicit buyer-defined requirement;
- no winner, overall match score, best-fit label, hidden weighting or automatic fit-based ordering is allowed.

The selected 0059 subset is the smallest implementation of that accepted direction:

> the current anonymous local Shortlist itself is the compare set; all saved IDs remain in buyer-authored order and current public listing/PhysicalBoat claim facts are rendered in one factual comparison surface.

This avoids inventing a second local "compare selection" object before usage justifies it.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0059:

- account/database-backed Shortlist;
- cross-device Shortlist continuity;
- anonymous-to-account migration;
- multiple/named lists;
- a separate persisted compare-selection set;
- arbitrary compare-set sharing or URL tokens;
- BuyerRequirements projection/evaluation against compared boats;
- automatic difference quality judgments;
- price normalization/conversion, cheapest/best-value labels or desirability scoring;
- derived performance/market metrics;
- private notes;
- Saved Search / Monitor / alerts;
- seller/broker contact and lead creation;
- telemetry/preference inference from Compare usage;
- third Search criterion;
- owner-direct publication/admission;
- Broker Workspace expansion.

### GENUINELY_OPEN

Still intentionally open for later capabilities:

- durable/account Shortlist identity, limits and anonymous migration;
- a future explicit subset-selection/reordering model if comparing the whole Shortlist proves insufficient;
- future BuyerRequirements overlay on Compare;
- sharing/privacy token semantics;
- currency conversion methodology and market-comparison semantics.

None is required for a v0.1 factual whole-Shortlist comparison.

### CONFLICT_OR_REGRESSION

One current-facing documentation conflict was found on canonical base:

`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` still described HullQ in its controlling one-sentence architecture as `broker-only-public-supply`, contradicting the later owner-accepted 2026-09-14 broker-first mixed-supply direction and the current `PROJECT_STATE.md`.

The SLICE-0059 readiness package corrects that stale phrase to `broker-first mixed-supply` before readiness can be accepted. No production-code conflict was found.

## 3. Existing implementation foundation

The accepted 0058 implementation already provides the exact transport needed for Compare:

```text
window.localStorage
→ shortlistStore.loadShortlistIds()
→ resolveShortlistListings(ids)
→ POST /api/shortlist/resolve
→ per-id accepted FastAPI public listing read
→ available | unavailable | service_error
```

For each available listing, `PublicListingData` already exposes:

- asking-price mode/amount/currency;
- location country and bounded region claim;
- broker summary/description/history/VAT claim where present;
- publishing Organization identity;
- offer recorded timestamp;
- freshness state / last-confirmed timestamp;
- bounded concrete PhysicalBoat claims:
  - marketed brand;
  - model designation;
  - build year;
  - LOA;
  - draft;
  - keel configuration;
  - rudder configuration.

Therefore 0059 needs no new application/domain listing truth, no migration and no duplicated lifecycle/freshness logic.

A Compare renderer can reuse current resolver results and existing claim/price presentation helpers.

## 4. Product success / buyer leverage

This capability strengthens the accepted serious-buyer loop:

```text
technical discovery
→ current listing truth
→ explicit shortlist
→ factual comparison
→ later monitor/contact action
```

It is more differentiated than generic marketplace card comparison because HullQ can preserve field-level `UNKNOWN`, not-supplied and concrete-yacht claim scope rather than flattening absent evidence into plausible model facts.

The inspectable success signal is straightforward: a buyer can place two or more saved current listings on one surface and understand factual concrete differences without leaving HullQ or accepting a synthetic overall recommendation.

## 5. Mandatory Broker Capability Register check

Canonical broker mandatory state remains OPEN/PENDING except implemented REQ-BROKER-030.

No broker requirement becomes DUE because an anonymous buyer compares saved public listings.

0059 does not waive or implement broker export, branding/media, connectivity-resilient drafts, pre-publication Search diagnostics, bulk import, engagement reporting, demand insight, leads or sale outcomes.

Compare is supply-neutral and may later consume either professional or owner-direct public inventory under the same `NativeListingId`/public-read rules.

## 6. Owner-direct / mixed-supply reconciliation

This reassessment inspected the owner-direct direction because Compare consumes marketplace listings.

0059:

- does not change listing admission/publication;
- does not change seller identity, verification or right-to-list semantics;
- does not prefer broker or owner-direct inventory;
- does not alter organic Search eligibility/classification/order;
- does not use seller payment, verification payment, referral economics or expected revenue as comparison ordering/value judgment;
- preserves one common current public listing-read boundary.

The stale broker-only architecture summary found during reconciliation is corrected in the readiness package.

## 7. Trigger gates

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

SLICE-0059:

- adds no technical native Search criterion;
- creates no account/server buyer persistence;
- introduces no real external production marketplace data;
- starts no production pilot;
- changes no public launch state.

The architecture-reconciliation conflict identified above is corrected by this same readiness package, so the readiness head can substantively retain `POST_0051_ARCHITECTURE_RECONCILIATION: PASS`.

## 8. Alternatives considered

### A. Anonymous Factual Shortlist Compare — SELECTED

Highest immediate leverage.

0058 was intentionally selected before Compare because explicit buyer-authored membership had to exist first. That prerequisite is now accepted and implemented. Compare can reuse the entire accepted 0058 identity/current-truth transport and the existing public concrete-yacht projection without forcing account, persistence or new domain semantics.

### B. Persistent/account Shortlist continuity

Not selected.

Durable Shortlist identity, account limits, anonymous-to-account migration and entitlement semantics remain genuinely open. Building them now would force broader persistence/privacy/product decisions that factual anonymous Compare does not require.

### C. Saved Search / monitoring / alerts

Not selected.

Strategically strong but exact persistence, reactivation, account/Free-Pro limits and background-worker notification semantics remain broader and intentionally unresolved. Compare is already accepted and is directly enabled by 0058.

### D. Seller/broker contact / qualified lead

Not selected.

Contact creates identity/privacy/lead-attribution and provider workflow obligations and is downstream of the buyer decision step. Owner-direct public admission is also not implemented yet.

### E. Broker Workspace inventory/resilient drafts

Not selected now.

Strategically mandatory before a real broker self-service pilot, but no broker requirement is currently triggered/DUE. Compare closes the next already-accepted buyer decision-tool gap with substantially smaller scope.

### F. Third technical Search criterion

Not selected.

Criterion #3 adds breadth, invokes the third-copy abstraction guard and does not close the buyer-action gap that the accepted shortlist/decision-tool sequence now exposes.

## 9. Selected capability boundary

SLICE-0059 delivers exactly one buyer capability:

> An anonymous buyer with at least two saved shortlist entries can open a localized factual Compare surface that uses the whole current browser-local Shortlist as the comparison set, preserves buyer-authored order, re-resolves current public truth, and aligns factual current listing and concrete-yacht claim fields without scoring or recommending a winner.

The compare set is not separately persisted.

Hard behavior:

```text
COMPARE SET = current local Shortlist membership
ORDER = buyer-authored Shortlist order
CURRENT FACTS = accepted public listing read
MISSING/UNKNOWN != guessed BoatDesign fallback
UNAVAILABLE != removed
SERVICE FAILURE != unavailable truth
DIFFERENCE != better/worse
PRICE != normalized desirability
COMPARE != recommendation
```

## 10. Decision

**Selected execution obligation:** `SLICE-0059 — Anonymous Factual Shortlist Compare`.

Readiness may proceed on the bounded contract in `specs/ANONYMOUS_FACTUAL_SHORTLIST_COMPARE_CONTRACT.v0.1.md`.

Implementation may not start until the readiness package is independently exact-head reviewed, remote gates are green and the readiness PR is merged to canonical `main`.
