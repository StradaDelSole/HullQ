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

## Accepted bounded evidence-set rule — Option B

For native-inventory technical evaluation of a concrete NativeListing, the accepted bounded mechanism is:

```text
publishing Organization's current claim
→ candidate listing/PhysicalBoat value

all relevant current admissible observations
for the same field on the same PhysicalBoat
→ contradiction guard
```

The publishing Organization's current non-superseded claim is the candidate value attributable to that listing. It is never silently replaced by another Organization's claim.

Search resolution then checks relevant current admissible observations for that same field on the same durable `PhysicalBoatId`:

```text
publisher claim = admissible concrete value
+ no contradictory current admissible observation
→ may be RESOLVED for this listing evaluation context
→ provenance remains the publishing Organization
→ verification remains unchanged / unverified unless separately established
```

```text
publisher claim = admissible concrete value
+ contradictory current admissible observation for same PhysicalBoat/field
→ CONFLICT
→ hard Required criterion cannot be satisfied
→ listing must not appear as CONFIRMED_MATCH on that criterion
```

Semantically equivalent corroborating current observations do not create a conflict. An omitted/UNKNOWN observation does not defeat a concrete publisher value or manufacture a conflicting value; it remains absence of corroboration, not a contradictory assertion.

Hard boundaries:

- the conflict guard MUST use the same durable `PhysicalBoatId`; fuzzy cross-listing identity inference is not authorized here;
- another Organization's observation can block a confirmed hard-search match through `CONFLICT`, but it does not overwrite the publishing Organization's displayed claim;
- no source winner, majority vote, recency winner, broker-priority winner or hidden confidence score is introduced;
- this is a bounded listing-evaluation conflict guard, **not** a global canonical PhysicalBoat fact resolver;
- historical superseded revisions from the same authority are audit history, not current contradictory observations;
- BoatDesign/configuration truth still cannot backfill missing or unresolved PhysicalBoat truth.

This accepted rule is `DECIDED_NOT_YET_IMPLEMENTED` in the generalized production native-inventory search path. Its implementation must remain bounded to the selected search capability rather than expanding into a generic cross-source resolver.

## Product-success and customer-experience priority

For SLICE-0051 selection/readiness and subsequent native-marketplace execution, the Project Owner has reaffirmed that **buyer friendliness, broker friendliness, competitive advantage, commercial success and exceptional implementation quality are first-order product constraints, not polish to add later**.

This preserves the existing `docs/PRODUCT_UX_PRINCIPLES.md` direction of reference-grade truth with consumer-grade clarity and adds an explicit execution-priority rule:

```text
truth-safe
+ materially easier for serious buyers
+ materially easier for professional brokers
+ meaningfully differentiated from generic boat marketplaces
+ visible/actionable product value
+ exceptional implementation quality
→ preferred execution path
```

For buyers, native Search should reduce work and uncertainty: explain why an offer qualifies, distinguish confirmed truth from missing/conflicting evidence, and make the next useful action obvious without requiring database expertise.

For brokers, HullQ should minimize unnecessary data-entry/reconciliation friction, preserve attribution and correction rights, never silently overwrite their claims, and make missing/conflicting information understandable and remediable rather than punitive or opaque.

For prioritization, commodity marketplace parity work MUST NOT outrank a bounded capability that materially strengthens HullQ's accepted technical-search/concrete-boat-truth advantage unless that parity work is a demonstrated prerequisite for the buyer/broker loop.

Success-oriented slices should prefer an inspectable user-facing outcome and evidence that the capability advances the primary buyer/broker loop rather than merely adding infrastructure. Quality does not permit weakening truth semantics: customer friendliness must be achieved through clearer interaction and better data handling, not by converting UNKNOWN/CONFLICT into convenient matches.

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
- `src/hullq/persistence/physical_boat_claims.py`
  - immutable revision history plus explicit current head per `(PhysicalBoatId, claiming Organization)`;
  - authorized same-Organization correction/supersession semantics;
  - stale predecessor/conflict handling and transaction-owned atomic writes;
  - typed current/revision/history readback without BoatDesign fallback.
- `almbic/versions/9c2e6b4a1d80_physical_boat_claim_facts.py`
  - durable revision/head schema and same-boat/same-Organization integrity constraints.
- `tests/unit/test_physical_boat_claims_domain_unit.py`
  - typed assertion-kind/value, omission-vs-UNKNOWN and Decimal/categorical guards.
- `tests/unit/test_physical_boat_claims_persistence_unit.py`
  - persistence-path authorization, conflict/idempotency/transaction behavior and typed readback unit coverage.
- `docs/slices/SLICE-0050-acceptance-closure.md`
  - records OWNER_ACCEPTED production behavior, including retained history, explicit head, rollback/concurrency proof and the hard no-BoatDesign-fallback boundary.

This behavior is not open for re-decision.

### DECIDED_NOT_YET_IMPLEMENTED

The generalized **production native-inventory search/qualification path** that consumes accepted PhysicalBoat marketplace claims and applies the Option-C resolution-vs-verification rule plus the Option-B same-PhysicalBoat conflict guard is not yet implemented as a production capability.

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

> **A sufficiently admissible current broker-declared PhysicalBoat claim may resolve and satisfy a hard native-inventory technical search criterion for its listing when the same-PhysicalBoat current-observation conflict guard finds no contradictory admissible value; provenance and verification remain separate, contradictory observations produce CONFLICT, UNKNOWN/UNRESOLVED/CONFLICT cannot satisfy Required, and BoatDesign truth never fills missing concrete-yacht truth.**
