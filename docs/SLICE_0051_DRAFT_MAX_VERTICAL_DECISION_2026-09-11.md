# HullQ — SLICE-0051 Draft-Max Vertical Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION  
**Applies to:** SLICE-0051 readiness and implementation scope  
**Does not mean:** SLICE-0051 is READY or started

## Decision

The Project Owner accepts `draft_max` as the **only public buyer requirement** in SLICE-0051.

Canonical example:

```text
/de/search?draft_max=1.6
```

The buyer meaning is:

> maximum acceptable draft = 1.6 metres

SLICE-0051 MUST deliver this bounded production vertical:

```text
buyer draft_max requirement
→ deterministic BoatDesign/configuration Search
→ potentially compatible designs/configurations
→ ACTIVE NativeListings
→ concrete PhysicalBoat
→ applicable current broker-declared physical_boat.draft claim
→ accepted same-PhysicalBoat contradiction guard
→ listing-level CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA
→ concrete /listings/{NativeListingId} next action
```

## Public requirement semantics

For SLICE-0051:

```text
parameter: draft_max
unit: metres
value type: exact positive finite Decimal
criterion: concrete PhysicalBoat draft <= draft_max
strength: Required
comparison: inclusive
implicit epsilon/tolerance: none
```

The already accepted OQ-018 public-search rules remain controlling, including exact decimal canonicalization, locale-neutral parameter semantics, canonical parameter ordering, sparse omission of inactive constraints, accepted handling of duplicates/invalid values/noncanonical forms, locale-prefixed Search routes, noindex behavior for parameterized Search results, and the accepted Astro SSR / FastAPI / React-Islands rendering boundary.

## Concrete PhysicalBoat truth rule

The decisive buyer-facing distinction remains:

```text
this BoatDesign/configuration can satisfy the requirement
!=
this concrete offered PhysicalBoat is confirmed to satisfy it
```

BoatDesign/configuration Search may identify candidate designs/configurations, but it MUST NOT backfill or infer the concrete offered boat's `physical_boat.draft`.

For a Required `draft_max` criterion:

- resolved concrete draft `<= draft_max` → `CONFIRMED_MATCH`;
- resolved concrete draft `> draft_max` → `CONFIRMED_NON_MATCH`;
- omitted draft → `INSUFFICIENT_DATA`;
- explicit `UNKNOWN` → `INSUFFICIENT_DATA`;
- `UNRESOLVED` → `INSUFFICIENT_DATA`;
- applicable `CONFLICT` from the accepted same-PhysicalBoat contradiction guard → `INSUFFICIENT_DATA` and MUST block hard-search confirmation.

Only `CONFIRMED_MATCH` belongs in the primary match set/count. `INSUFFICIENT_DATA` may be exposed only as a clearly separate discovery surface and MUST NOT be represented as satisfying the requirement.

Example invariant:

```text
BoatDesign/configuration draft = 1.55 m
+
concrete PhysicalBoat draft unknown
=
INSUFFICIENT_DATA
```

No factory/design/configuration value may silently become concrete PhysicalBoat truth.

## Decimal integrity

`physical_boat.draft` is already represented as exact `decimal.Decimal` SI metres in the accepted SLICE-0050 domain model. SLICE-0051 MUST preserve exact decimal semantics across the public Search facade, FastAPI/application boundary, requirement evaluation and PhysicalBoat-claim comparison.

No binary-float-mediated conversion, semantic rounding or hidden tolerance may weaken the accepted comparison semantics merely because historical Search query code currently uses Python `float` internally. If the bounded 0051 path cannot preserve exact Decimal semantics through unchanged reuse, 0051 owns the smallest required adapter/refactor.

## Explicit scope exclusions

SLICE-0051 MUST NOT expand the public requirement surface to any additional criterion merely for completeness.

The following are outside this slice unless mechanically required to support `draft_max` without broadening product scope:

```text
draft_min
loa_min
loa_max
build_year
keel_configuration
rudder_configuration
all seven SLICE-0050 fields
generic all-field native-inventory Search infrastructure
Saved Search / monitoring / alerts
broad ranking or recommendation systems
```

These capabilities are **deferred, not rejected**.

## Why this field is selected

`draft_max` is the smallest field that proves HullQ's intended product advantage rather than merely generic marketplace filtering:

1. Draft is materially relevant to serious yacht buyers.
2. It is configuration-sensitive at design level.
3. SLICE-0038 already proved that design/configuration compatibility alone cannot truthfully qualify a concrete listing.
4. SLICE-0050 now provides concrete PhysicalBoat draft claims as exact Decimal values or explicit unknowns.
5. The vertical therefore exercises the complete truth-safe bridge from technical requirement to native inventory and concrete offered-boat evidence.

The slice remains intentionally one-capability: a narrow field can still prove the full production chain.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- configuration-aware deterministic Search kernel and hard Required semantics
- inclusive numeric comparison semantics with no implicit tolerance
- separated CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA result classes
- SLICE-0038 proof that design/configuration fit does not establish concrete listing fit
- ACTIVE NativeListing/public listing path
- SLICE-0050 concrete PhysicalBoat draft claim representation/persistence as Decimal or UNKNOWN
- accepted OQ-018 public Search route/query/canonical/rendering decisions required for this first vertical

DECIDED_NOT_YET_IMPLEMENTED
- production public `draft_max` facade and exact-Decimal adapter path
- production BoatDesign/configuration → ACTIVE NativeListing → PhysicalBoat Search bridge
- accepted claim-resolution / same-PhysicalBoat contradiction-guard integration for listing qualification
- buyer-visible first production Requirements → Native Inventory Search result surface

EXPLICITLY_DEFERRED
- every public Search requirement beyond `draft_max`
- generic all-field native-inventory Search infrastructure
- Saved Search / monitoring / alerts
- broader SEO landing-page taxonomy and future faceted-search expansion outside the bounded first Search surface

GENUINELY_OPEN
- none for field selection or buyer requirement semantics needed to begin SLICE-0051 readiness
```

## Readiness consequence

This decision closes the previously open **exact smallest field/query vertical** prerequisite for SLICE-0051.

It does **not** itself mark SLICE-0051 READY. The next phase is the governed SLICE-0051 readiness branch, reconciliation and independent exact-head readiness review. Only after that readiness work is merged may the Project Owner run `START_SLICE.bat` for SLICE-0051.

## Controlling one-sentence rule

> **SLICE-0051 ships exactly one public buyer requirement, `draft_max`, and qualifies a native listing as a hard match only when the concrete PhysicalBoat's admissible resolved draft truth confirms `draft <= draft_max`; design/configuration compatibility alone never establishes concrete offered-boat fit.**
