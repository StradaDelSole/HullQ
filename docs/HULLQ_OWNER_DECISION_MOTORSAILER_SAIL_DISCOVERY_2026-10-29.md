# HullQ — Owner Decision: Motorsailers Belong to Sail Discovery

**Date:** 2026-10-29 (Europe/Vienna)  
**Status:** OWNER-ACCEPTED PRODUCT / DISCOVERY DIRECTION — NOT YET IMPLEMENTED  
**Implementation tracking:** [#372](https://github.com/StradaDelSole/HullQ/issues/372) (future category/buyer/broker parity; **no numbered slice selected**)  
**Checkpoint:** [#397](https://github.com/StradaDelSole/HullQ/issues/397) (post-0095 reassessment)  
**Controlling wider direction:** [Joint Sail+Power Owner Decision, 2026-10-22](HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md)

## 1. Explicit Owner decision

The Owner clarified in conversation on 2026-10-29: **“Motorsegler sind wie der Name schon sagt motor-SEGLER also in erster Linie Segelboote und auch denen zuzuordnen.”**

Binding **public product-family assignment:** a positively and validly classified motorsailer belongs to the **Sail** family. It is discoverable as a **motorsailer subtype within Sail**, not silently treated as a Power boat or removed from Sail merely because its source-qualified category is `MOTORSAILER`. The default product navigation/discovery placement is **Sail only**, not automatically both categories.

This answers the previously open **Sail vs Power product-family placement** question. It does **not** approve the automatic assertion that any offered motorsailer satisfies a technical Sail criterion.

## 2. Preserve existing evidence and identity semantics

- Retain the distinct internal positive `VesselCategory.MOTORSAILER` / `VesselCategoryResolution.MOTORSAILER`; **do not relabel or mass-migrate it to `SAIL`**. The public **family** ("Sail") and exact vessel **subtype** ("Motorsailer") are distinct concepts.
- Preserve the SLICE-0091 design-versus-concrete category assertions, issuer/provenance, immutable revisions, source qualification, `UNKNOWN`, `CONFLICT`, and fail-closed conflicting/missing evidence. Neither boat name nor engine/rig/marketing label alone can assert `MOTORSAILER`.
- Once the Sail-family discovery policy is implemented, a positively qualified motorsailer should be eligible for Sail-family candidate admission; **technical CONFIRMED_MATCH** remains possible *only* when every actual requested Sail criterion is positively supported by the same accepted design/configuration and current PhysicalBoat/qualified publisher-claim evidence. No weakening of MUST/AND, current D29 public eligibility, freshness, authorization, source rights or explicit insufficient/nonmatch reasons.
- Keep Power-only technical discovery admission restricted to independently qualified `POWER`. Motorsailers are **not** added automatically to Power search because they have engines. Any additional cross-family browsing/technical policy would need a separate, explicit Owner decision.
- Legacy absent/UNKNOWN categories keep their accepted compatibility and evidence distinctions until a separately approved change; neither unknown nor conflict is automatically assigned the Sail subtype.

## 3. Decision / implementation reconciliation at main HEAD

**Baseline:** canonical `main` `e9b8a47b2452d512687aae36c6cb47f7c61a6bb2`; latest accepted SLICE-0095, queue 0096 **NOT SELECTED**.

- **DECIDED_AND_IMPLEMENTED:** SLICE-0091's separate source-qualified `MOTORSAILER` type and current deterministic category resolution; existing nine Sail technical and two Power technical Search criteria; category prefilters enforcing the previously conservative exclusion, including tests; D29/public and broker Search-fit evidence requirements.
- **DECIDED_NOT_YET_IMPLEMENTED (this decision):** Sail-family buyer browse/navigation and Sail technical candidate-admission policy for correctly classified `MOTORSAILER` where criterion proof permits, consistent broker-private Sail Search-fit and result presentation, and applicable browser/API regression tests. The current code intentionally **excludes `MOTORSAILER` from confirmed Sail matches**: `src/hullq/domain/vessel_category.py` `is_explicitly_non_sail_or_conflicted` / `VesselCategoryExclusionEvidence`, `src/hullq/application/native_inventory_query.py` design-linked and publisher-claim paths, and `tests/persistence/test_native_inventory_query_vessel_category_slice_0091.py` reflect the older SLICE-0091 safe interim policy. This new accepted direction **supersedes that interim category-placement policy prospectively**; it is not evidence the current code is already changed.
- **EXPLICITLY DEFERRED:** Any runtime/code/migration/test/contract update until an independently reviewed, Owner-selected, bounded slice, including a reviewed supersession of affected 0091/0093/0095 invariants. Power NautiX/other import/export representation and external data rights remain separately controlled under #372/#355; no automatic export rights or category conversion.
- **GENUINELY OPEN:** Detailed subtype UI labels/filters and future mixed/dual-family advanced browsing rules beyond the accepted Sail-first placement. These are implementation-design questions, **not** permission to re-ask the Sail-family decision.
- **CONFLICT_OR_REGRESSION:** None established from this decision alone; current production exclusion is a documented **implementation gap against the new forward product policy**, not an assertion that accepted SLICE-0091 regressed.

## 4. Required execution/review boundaries

The next relevant category/Search readiness MUST reconcile the new Sail-family rule with the existing source-qualified `MOTORSAILER` representation, both Sail search candidate paths, broker Search-fit, Power exclusion, authorized current PhysicalBoat claims, conflicts, legacy UNKNOWN compatibility, public D29 eligibility, and the actual published browser labels/navigation. Include adversarial PostgreSQL18/API/browser tests for design-linked vs design-unresolved motorsailers, nonmatches, missing/conflicting/stale claims and other-Organization attribution; update affected normative specifications/tests *in the same reviewed implementation change* before claiming support.

**No new technical criterion is created by this family assignment:** currently accepted native technical Search count remains **11 = Sail 9 / Power 2**.

This docs-only decision does **not** select/READY SLICE-0096, create an initial Claude prompt, change production code, launch an external pilot or lift #355 (pre-external-data/Search scale), #366 (joint Sail+Power release), #372 (remaining parity) or Production Readiness / Launch Pack gates.
