# HullQ Marketplace Search Claim Resolution

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION  
**Applies to:** future native-inventory technical search/qualification over `PHYSICAL_BOAT` marketplace claims  
**Does not select or start:** SLICE-0051

## Purpose

Freeze the accepted relationship among broker-declared PhysicalBoat claims, resolution, verification and hard technical search so this behavior is not re-asked or silently strengthened/weakened later.

This decision preserves the accepted marketplace invariant:

```text
BROKER_CLAIM != VERIFIED_FACT
```

while also preserving the accepted future-search rule:

```text
RESOLVED compatible value -> may satisfy Required
UNKNOWN                    -> NO
UNRESOLVED                 -> NO
CONFLICT                   -> NO
```

## Accepted decision — Option C

**Resolution and verification are separate axes.**

For an ordinary searchable `STANDARD` or `MATERIAL` PhysicalBoat technical field, an admissible current broker-declared value MAY be sufficient evidence for the future native-inventory search evaluator to resolve that claim in the applicable listing/PhysicalBoat evaluation context **without** pretending that HullQ independently verified the value.

Hard:

```text
resolved broker-declared claim
!= independently verified fact
```

A value used this way remains attributable to its claim authority and must remain representable/presentable as broker-declared and not independently verified unless a separate accepted verification capability establishes stronger evidence.

## Conflict / uncertainty rule

A broker value does not earn a hard-search match merely because it exists.

The future evaluator must consider the accepted claim/resolution semantics for the applicable evidence set. If the relevant fact is `UNKNOWN`, `UNRESOLVED` or `CONFLICT`, it MUST NOT satisfy a hard `Required` criterion.

Hard examples:

```text
current admissible broker claim: draft = 1.52 m
no relevant unresolved contradiction
query: draft <= 1.60 m

-> may resolve the criterion TRUE for search
-> provenance remains broker-declared
-> verification remains NONE/unverified unless separately established
```

```text
relevant current observations disagree: 1.52 m vs 1.85 m

-> CONFLICT
-> does not satisfy the hard criterion
-> no "pick the matching value" behavior
```

No rule equivalent to these is permitted:

```text
latest Organization always wins
listing-owning Organization always defeats a known conflicting observation
majority wins
BoatDesign baseline wins
unverified means automatically unusable
```

The exact evidence-set/resolution mechanism required by a production native-inventory search capability must be defined in that bounded slice without weakening this decision.

## Design truth remains separate

This decision does not authorize BoatDesign/configuration data to fill missing PhysicalBoat truth.

Hard:

```text
BoatDesign has a matching configuration
+ concrete PhysicalBoat field missing/UNKNOWN
!= confirmed concrete-boat match
```

A future technical native-inventory result may only become a confirmed result from evidence admissible for the concrete offer/PhysicalBoat under the accepted search and marketplace-fact contracts.

## Repository reconciliation performed before this decision was recorded

### DECIDED_AND_IMPLEMENTED

**SLICE-0038 pilot:** the repository already contains accepted executable behavior proving that design-level configuration fit must not be promoted into a concrete sales-offer match without listing-specific evidence.

Relevant production/repository implementation checked:

- `scripts/search_oceanis_30_1_sales.py`
  - invokes the accepted real configuration-aware Search path first;
  - independently admits BoatDesign identity;
  - evaluates listing-specific numeric draft through the existing Search criterion evaluator;
  - explicitly prevents design-level inheritance into a listing with no specific evidence.
- `tests/unit/test_search_oceanis_30_1_sales.py`
  - proves listing-specific shallow draft -> `TruthState.TRUE`;
  - proves listing-specific deeper draft -> `TruthState.FALSE`;
  - proves no listing-specific evidence -> `TruthState.UNKNOWN` even when the BoatDesign has a matching factory configuration;
  - proves conflicts/malformed/nonphysical evidence fail closed.
- `docs/slices/SLICE-0038-acceptance-closure.md`
  - records OWNER_ACCEPTED pilot behavior and the retained real result where all seven admitted real offers stayed `UNKNOWN` because no admissible listing-specific draft evidence existed.

This behavior is not open for re-decision.

**SLICE-0050 production PhysicalBoat claims:** the repository already contains the bounded production claim model required as native inventory input.

Relevant production implementation checked:

- `src/hullq/domain/physical_boat_claims.py`
  - broker-declared concrete-PhysicalBoat claim representation;
  - explicit `UNKNOWN` distinct from omission;
  - Decimal-based numeric values;
  - typed draft/keel/rudder claims;
  - no BoatDesign knowledge/fallback.
- accepted SLICE-0050 persistence/public-read implementation and closure
  - immutable revision/current-head semantics per claiming Organization;
  - no BoatDesign fallback into PhysicalBoat claims;
  - broker claim remains a claim, not verified fact.

This behavior is not open for re-decision.

### DECIDED_NOT_YET_IMPLEMENTED

The generalized **production native-inventory search/qualification path** that consumes accepted PhysicalBoat marketplace claims and applies the Option-C resolution-vs-verification rule is not yet implemented as a production capability.

That is an implementation gap, not an open semantic question.

### EXPLICITLY_DEFERRED

This decision does **not** itself implement:

- a global cross-Organization PhysicalBoat fact resolver;
- independent document/survey verification;
- a generic all-38-field search engine;
- a new search-result UI;
- Saved Search / monitoring / alerts;
- a specific SLICE-0051 capability.

Those remain subject to bounded future capability selection and their controlling accepted contracts.

## Controlling artifacts preserved

This decision must be read together with:

- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/PRODUCT_UX_PRINCIPLES.md`;
- `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md`;
- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`;
- accepted SLICE-0038 and SLICE-0050 closures and implementation.

## Controlling one-sentence rule

> **A sufficiently admissible and resolved broker-declared PhysicalBoat claim may satisfy a hard native-inventory technical search criterion without becoming an independently verified HullQ fact; provenance and verification remain visible/separate, while UNKNOWN, UNRESOLVED or CONFLICT cannot satisfy Required and BoatDesign truth never fills missing concrete-yacht truth.**
