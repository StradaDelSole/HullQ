# HullQ — Market and Business-Model Validation Reclassification

**Date:** 2026-09-06  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** product/business interpretation after SLICE-0049  

## Purpose

This document corrects an increasingly misleading shorthand in older planning language.

HullQ is not entering an unproven category. Online boat/yacht marketplaces are already a proven business model with large incumbent operators, meaningful broker participation and substantial buyer traffic. HullQ therefore does **not** need to prove that buyers search for boats online or that brokers will ever use online marketplaces in principle.

What remains unproven is narrower and HullQ-specific.

## Canonical validation classification

```text
MARKET VALIDATION                  = YES
ONLINE BOAT MARKETPLACE MODEL      = YES
DEMAND FOR ONLINE BOAT SEARCH      = YES

STILL TO VALIDATE:
HullQ-specific product advantage,
buyer adoption/behavior,
native inventory acquisition/access,
broker participation,
and sustainable unit economics at HullQ scale.
```

Preferred project-overview wording:

> **Business model and market demand: validated by the existing category. HullQ-specific product advantage, inventory acquisition and user adoption: not yet validated at scale.**

Do not use unqualified wording such as:

```text
business model unvalidated
market demand unvalidated
commercial validation substantially behind because nobody has proved online boat search
```

Those statements conflate category validation with HullQ-specific execution risk.

## Relationship to older execution documents

This document does not replace the native-marketplace direction in:

- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`.

It only supersedes older wording where the unresolved question is described as whether the online boat-marketplace category or base marketplace model itself has demand.

All non-conflicting strict-truth, provenance, fail-closed, ONE-CAPABILITY, VISIBLE-RESULT, exact-head review, broker-first supply and architecture rules remain controlling.

## Gate interpretation after this reclassification

### HullQ product-value / adoption gate

The relevant buyer-side question is now:

> **Is HullQ sufficiently better for serious sailboat buyers that its deterministic technical Search, configuration awareness, PhysicalBoat truth and explicit UNKNOWN semantics materially change decisions, monitoring behavior or product preference?**

This is a HullQ-specific product-advantage/adoption test, not a test of whether online boat search is a viable category.

### Native inventory / broker-participation gate

The relevant supply-side question is:

> **Can HullQ obtain enough useful native professional inventory, with sufficiently low broker friction and sustainable economics, to make the differentiated buyer product useful?**

This is not the same as proving that brokers use online marketplaces in general; that behavior is already category-proven.

### Unit economics

Pricing, lead economics and operating costs remain HullQ-specific and must be tested at HullQ scale. Existing incumbent economics do not prove HullQ's own sustainable CAC, broker acquisition cost, lead value, paid conversion or support burden.

## Competitive implication

HullQ does not initially need to replace the dominant incumbent or match its full inventory density.

A credible early wedge is:

```text
Buyer starts at HullQ
→ expresses technically meaningful constraints
→ sees which designs/configurations can fit
→ sees what is actually known about each physical offered boat
→ understands UNKNOWN rather than receiving a plausible guess
→ monitors / follows the relevant inventory
→ contacts the broker
```

Incumbent strengths include enormous reach, inventory density, broker entrenchment and continuously improving consumer UX.

HullQ therefore should **not** assume that generic marketplace presence, nicer cards or a broad clone of incumbent filters is sufficient differentiation.

The differentiated product thesis remains:

```text
deterministic technically precise Search
+ configuration-aware matching
+ individual-boat truth
+ explicit UNKNOWN semantics
+ provenance
+ better buyer decision UX
+ monitoring / alerts / intelligence
```

## Execution consequence

Post-0049 slices should optimize for proving and strengthening that differentiated loop.

Do not spend product slices proving that online boat listings have demand. Prefer capabilities that let a serious buyer experience the HullQ-specific advantage on real native inventory.

This directly supports the post-0049 priority order:

```text
public listing exists
→ make concrete-boat truth useful
→ let buyers discover/filter native inventory using that truth
→ save / monitor
→ fit-confirmed alerts
→ broker contact / qualified lead
```

Broker-operating surfaces, media and feed automation remain important, but they should move ahead of buyer-truth/search work only when they are the actual bottleneck to obtaining representative inventory or running the next product test.

## Current evidence interpretation

Current incumbent evidence is used only to classify the category, not to claim HullQ success:

- Boats Group publicly describes YachtWorld as the leading global yacht/luxury-vessel marketplace and reports more than 65 million annual visitors across its marketplaces;
- Boats Group reported in August 2026 that YachtWorld's new site increased lead conversion and search click-through, demonstrating that the incumbent is actively improving rather than standing still;
- user-review evidence still contains concrete complaints about search precision, strict dimensional filtering, keyword discovery and navigation.

The strategic conclusion is therefore not "the incumbent is bad". It is:

> **The category is large and validated; the incumbent is strong and improving; HullQ must win on a sharper buyer problem that the incumbent's listing-centric model still handles imperfectly.**

## Controlling one-sentence direction

> **HullQ operates in a validated online boat-marketplace category; the remaining business risk is whether HullQ's technically precise, configuration-aware, PhysicalBoat-truth product is sufficiently better to drive buyer adoption and broker inventory participation at sustainable HullQ economics.**
