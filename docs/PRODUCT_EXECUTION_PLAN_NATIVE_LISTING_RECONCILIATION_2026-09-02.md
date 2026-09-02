# HullQ Product Execution Reconciliation — Native Listing Market

**Date:** 2026-09-02  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** all work after the terminal closure of SLICE-0039  

## Purpose

This document removes any residual ambiguity between:

- `docs/PRODUCT_EXECUTION_PLAN.md`;
- `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`; and
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`.

The owner has made the strategic decision that HullQ will build a **native sailboat listing/discovery market**. Native HullQ listing supply is therefore the required market foundation for the pre-Gate-1 product. Authorized external marketplace/API/feed integrations are optional coverage supplements and are not a prerequisite for HullQ's core viability or Gate-1 execution.

Where the earlier amendment still refers to an external recurring market-acquisition path as if it were required before Gate 1, this reconciliation supersedes that wording.

## Controlling precedence

For conflicting post-SLICE-0039 execution instructions, use the following precedence:

1. this reconciliation;
2. `PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
3. `PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`;
4. `PRODUCT_EXECUTION_PLAN.md` and older non-normative planning language.

Non-conflicting strict-truth, provenance, fail-closed, configuration-scope, physical-listing-scope, explicit `UNKNOWN`, source/media-rights, ONE-CAPABILITY, VISIBLE-RESULT, exact-head review/gates and slice-isolation rules remain fully in force.

## Specific supersessions

### 1. Market foundation

Any earlier wording equivalent to:

```text
current market inventory through lawful/authorized access paths
```

must be read as:

```text
native HullQ listings as the strategic market foundation
+
optional authorized external inventory integrations where useful
```

External marketplace permission is not a Gate-1 prerequisite.

### 2. External recurring acquisition

Sections of the 2026-09-01 pre-Gate-1 amendment that describe identifying, authorizing, implementing and scheduling a recurring **external** market-acquisition path remain valid only when HullQ later chooses to integrate such an external source.

They are no longer a required dependency for Gate 1.

The required pre-Gate-1 operational loop is instead based on native listing events and native supply intake:

```text
native listing creation/import/update
→ canonical BoatDesign/configuration identity assessment
→ physical-listing truth
→ persistence/change state
→ Saved Search evaluation
→ monitoring/scheduler where needed
→ real alert
```

### 3. Supply acquisition

Before Gate 1, HullQ must prove a realistic native supply path rather than prove access to a third-party marketplace.

Supply capabilities should be built progressively through bounded slices, starting with the smallest real end-to-end path and expanding toward scalable intake such as:

```text
manual listing
→ bulk import
→ XML/JSON/API feed
→ broker inventory feed
→ CRM/DMS/syndication integration
```

This is not permission to build all supply mechanisms at once.

### 4. Gate-2 / external market access

Buyer Value Risk and external Market Access Risk remain analytically distinct, but the absence of a Boats Group/YachtWorld/other marketplace agreement does not block Gate 1 when native HullQ listing supply supports the intended validation experience.

External market-access work may later evaluate authorized APIs, feeds, partnerships, syndication or licensing opportunities as optional coverage expansion.

### 5. Post-0039 sequencing

The earlier amendment's dependency sequence that required resolving and automating an external recurring acquisition path is replaced by the native-listing sequence in `PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`.

The controlling capability order is therefore approximately:

1. lock/formalize the complete HullQ Search Product Contract;
2. implement remaining Search-contract semantics/filters in bounded slices;
3. scale Search-contract data coverage;
4. expose the full Search contract through a simple Validation UI;
5. define the native Listing domain contract;
6. create one native listing end-to-end;
7. attach listing identity/configuration without collapsing truth scopes;
8. add listing read/search surfaces;
9. add listing lifecycle/status handling;
10. add broker/seller identity/contact routing;
11. add media handling only after rights/storage rules are defined;
12. add scalable bulk/feed intake;
13. add dedup/identity handling as multiple intake paths require it;
14. persist exact Saved Searches;
15. connect native listing events to Saved-Search evaluation;
16. send real alerts;
17. expose the slim Pro proposition;
18. run internal burn-in;
19. run external Gate-1 validation.

Dependencies may justify bounded reordering, but later capabilities may not be pulled into an earlier slice merely for convenience.

## SLICE-0039 terminal outcome

SLICE-0039 is already terminally accepted as `BLOCKED` because its locked 3/4 evaluability gate was not met under strict truth. That historical gate is not reopened, relaxed or repaired.

No further work is authorized under SLICE-0039.

## Controlling one-sentence direction

> **HullQ will build a native sailboat listing and discovery market whose core advantage is deterministic, configuration-aware technical Search and monitoring; native HullQ listings are the strategic supply foundation, while authorized external marketplace/feed/API integrations may supplement coverage but are not a prerequisite for core viability or Gate 1.**
