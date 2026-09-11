# HullQ — SLICE-0051 Capability Selection

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION  
**Applies to:** post-SLICE-0050 reassessment and SLICE-0051 readiness  
**Does not mean:** SLICE-0051 is READY or started

## Selected capability

The Project Owner accepts the buyer-facing option for SLICE-0051:

```text
technical buyer requirement
→ deterministic BoatDesign/configuration Search
→ ACTIVE native professional inventory
→ concrete PhysicalBoat/listing truth
→ accepted claim resolution / contradiction guard
→ buyer-visible confirmed-fit vs insufficient-data result
→ concrete NativeListing next action
```

SLICE-0051 is therefore selected as the **first production buyer-facing Requirements → Native Inventory Search vertical**.

The purpose is not generic marketplace filtering. The product must make HullQ's accepted distinction visible and useful:

```text
this design/configuration can satisfy the requirement
!=
this concrete offered boat is confirmed to satisfy it
```

## Relationship to the backend-first alternative

The backend-first alternative is **not rejected**.

What is rejected is only sequencing it as a separate preceding slice whose result is production infrastructure without the buyer-facing vertical.

The minimum production backend bridge required by the selected vertical remains mandatory inside SLICE-0051:

```text
ACTIVE NativeListing
→ MarketEpisode
→ PhysicalBoat
→ applicable current PhysicalBoat claims / observations
→ accepted Option-B same-PhysicalBoat contradiction guard
→ accepted Option-C resolution-vs-verification semantics
→ existing deterministic Search criterion semantics
→ listing-level result classification
```

Therefore:

```text
A as standalone backend-first SLICE-0051
→ NOT SELECTED

minimum A functionality required to make B truthful and production-capable
→ REQUIRED INSIDE SLICE-0051

broader generic/reusable all-field native-inventory search infrastructure
→ EXPLICITLY DEFERRED until justified by subsequent product needs
```

This protects one-capability slicing: the implementation may build only the backend path necessary to deliver the selected buyer-facing vertical. It must not expand into a generic all-fields search platform merely because such infrastructure could be useful later.

## Accepted search obligations carried into 0051

The following are already decided and MUST NOT be reopened during readiness:

- hard `MUST` criteria remain fail-closed;
- `UNKNOWN`, `UNRESOLVED` and `CONFLICT` do not satisfy Required;
- only `CONFIRMED_MATCH` belongs in the primary match set/count;
- insufficient-data records may be exposed only as a clearly separate discovery surface and never represented as matches;
- BoatDesign/configuration truth never backfills missing concrete PhysicalBoat truth;
- resolution and verification are separate axes;
- the publishing Organization's current admissible claim is the candidate listing value;
- relevant current admissible observations for the same field on the same durable `PhysicalBoatId` act as the accepted contradiction guard;
- a contradictory current observation produces `CONFLICT` and blocks confirmed hard-search fit;
- another Organization's claim may block confirmation through conflict but does not overwrite the publishing Organization's displayed claim.

Controlling record: `docs/MARKETPLACE_SEARCH_CLAIM_RESOLUTION_2026-09-11.md`.

## Product-success constraint

SLICE-0051 must satisfy the accepted `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md` standard.

In particular, readiness must identify evidence for all five dimensions:

1. **Buyer:** the serious-buyer task made materially easier or safer;
2. **Broker:** effect on professional supply friction/value;
3. **Advantage:** why this experience is meaningfully better than generic marketplace filtering;
4. **Success evidence:** an inspectable user-facing outcome showing the primary marketplace loop advanced;
5. **Quality:** proof that accepted truth, provenance, architecture and UX boundaries remain intact.

## OQ-018 prerequisite before readiness

The selected capability is buyer-facing and introduces a public Search surface. `OQ-018` is still OPEN and explicitly gates public frontend/search-surface implementation.

Therefore SLICE-0051 MUST NOT become `READY` until the bounded OQ-018 decisions necessary for this first public Search surface have been resolved and durably recorded, including at least the applicable URL/canonical/indexability/query-parameter/rendering boundary.

Resolving OQ-018 for 0051 does not require designing every future SEO landing page or every possible faceted-navigation rule. It requires the smallest accepted public-search architecture that prevents accidental URL/SEO debt while allowing this vertical to ship.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- deterministic numeric/categorical MUST Search kernel and separated result classes
- configuration-aware Search behavior
- SLICE-0038 proof that concrete listing truth must not inherit design-level fit
- ACTIVE NativeListing/public listing path
- bounded current PhysicalBoat claim persistence from SLICE-0050

DECIDED_NOT_YET_IMPLEMENTED
- Option-B same-PhysicalBoat contradiction guard in generalized production native-inventory Search
- Option-C claim-resolution-to-Search bridge
- production NativeListing/PhysicalBoat → Search evaluation path

GENUINELY_OPEN
- bounded OQ-018 public Search/SEO surface decisions required before 0051 readiness
- exact smallest field/query vertical for 0051 after OQ-018 is bounded

EXPLICITLY_DEFERRED
- generic all-field native-inventory search infrastructure beyond what 0051 needs
- Saved Search / monitoring / alerts
- broad ranking, media, broker workspace and remaining marketplace-field expansion
```

## Controlling one-sentence rule

> **SLICE-0051 will ship HullQ's first buyer-facing technical Requirements → ACTIVE Native Inventory vertical; the minimum production backend bridge needed to make that vertical truthful is required within the slice, while a separate backend-first slice and broader generic search infrastructure are deferred rather than discarded.**
