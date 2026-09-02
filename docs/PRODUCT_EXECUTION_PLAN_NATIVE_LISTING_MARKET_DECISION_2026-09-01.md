# HullQ Product Execution Decision — Native Listing Market

**Date:** 2026-09-01  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** work after SLICE-0039  
**Relationship to existing policy:** This decision supplements `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md` and supersedes any conflicting assumption that HullQ's core market proposition depends on recurring access to an external marketplace. All non-conflicting strict-truth, provenance, fail-closed, ONE-CAPABILITY, VISIBLE-RESULT, review, slice-isolation and exact-head governance rules remain in force.  
**SLICE-0039:** unchanged. Finish and review SLICE-0039 exactly as already accepted; do not widen it to implement this decision.

## 1. Strategic decision

HullQ will build a **native sailboat listing and discovery market** as a first-class product capability.

The core product will not depend on permission from YachtWorld, Boats Group, Scanboat or any other single external marketplace for viability.

The strategic product loop becomes:

```text
complete technical Search
→ canonical BoatDesign/configuration truth
→ native HullQ listings
→ physical-listing truth
→ Saved Search
→ monitoring
→ alerts
→ broker/seller contact
```

Authorized external APIs, feeds, syndication relationships or marketplace integrations may later supplement HullQ inventory. They are optional coverage channels, not a prerequisite for the core business.

## 2. Meaning of "listing market"

HullQ is not initially a transaction/closing platform.

HullQ may provide:

- listing publication;
- technical discovery/search;
- configuration-aware qualification;
- listing detail pages;
- buyer matching;
- Saved Search;
- monitoring and alerts;
- broker/seller contact routing;
- feed/syndication intake.

HullQ does not need to provide before Gate 1:

- escrow;
- purchase-contract execution;
- ownership transfer;
- financing;
- closing;
- boat-payment processing;
- brokerage execution.

The commercial boat transaction may occur directly between buyer and seller/broker outside HullQ.

## 3. Market-access dependency removed

A bespoke external-marketplace agreement may still be commercially useful, but HullQ must not make such an agreement a single point of failure.

Therefore the previous pre-Gate-1 assumption:

```text
at least one legally usable recurring external market-acquisition path
```

is no longer a required foundation of the product.

For Gate-1 readiness, the market proposition may be demonstrated through native HullQ listing supply.

If an external source is later integrated, that source must still have a lawful/authorized access basis. No technical workaround may mean circumvention of contractual, legal or access restrictions.

## 4. Native listing truth model

The existing truth separation remains mandatory:

```text
DESIGN / CONFIGURATION TRUTH
!=
PHYSICAL LISTING TRUTH
```

Canonical BoatDesign/configuration facts may inform discovery but may not silently become observations about a specific physical boat.

Native listings must preserve listing-specific observations separately, including where applicable:

- physical boat identity;
- year;
- asking price/currency;
- location;
- seller/broker identity;
- availability/status;
- claimed configuration;
- engine/equipment/refit information;
- condition descriptions;
- photos/media;
- contact information.

A missing or unverified listing-specific fact remains `UNKNOWN` or otherwise unresolved under accepted semantics.

## 5. Supply strategy

The primary new business risk is:

> **Can HullQ acquire enough native listing supply to make the market useful?**

HullQ must not rely on thousands of brokers manually recreating listings one by one.

The product should progressively support low-friction supply paths such as:

```text
manual listing
CSV bulk import
XML feed
JSON/API feed
broker inventory feed
CRM/DMS integration
syndication integration
```

The long-term preferred model is for HullQ to become an **authorized syndication destination** so a broker can maintain inventory once and distribute it to HullQ alongside other marketplaces.

## 6. Broker/seller proposition

Early supply acquisition should be optimized for low friction, not immediate broker monetization.

A suitable early proposition is:

> **List your inventory on HullQ and reach buyers whose technical requirements already match the boat.**

Native listings may initially be free or otherwise very low-friction.

Potential later B2B monetization may include:

- enhanced broker profiles;
- promoted inventory;
- lead-management tools;
- analytics;
- CRM integrations;
- configuration verification/enrichment;
- feed/API services;
- premium inventory tooling.

These later B2B features are not automatically authorized for pre-Gate-1 scope.

## 7. Buyer monetization remains distinct

The current early buyer-side proposition remains:

```text
HullQ Free
→ technical Search
→ current native listings
→ comparison/discovery

HullQ Pro
→ Saved Searches
→ continuous monitoring
→ new-match alerts
→ later price/status alerts where appropriate
```

Product Pull and Pay Pull remain separate validation signals.

A full custom billing platform is not required before Gate 1.

## 8. Monitoring architecture changes

With native listings, the monitoring loop becomes:

```text
native listing created/updated/status-changed
→ canonical identity/configuration assessment
→ physical-listing truth evaluation
→ Saved Search evaluation
→ matching users
→ alert
```

HullQ can legitimately maintain native listing lifecycle state such as:

```text
created
updated
price_changed
status_changed
withdrawn
sold
relisted
```

This supports idempotency, alert suppression, price/status history, Days on Market and dedup where later product scope requires them.

## 9. Gate-1 Slim MVP implication

Gate 1 remains End-to-End Product Proposition Validation.

The pre-Gate-1 slim product should now include, through bounded slices:

```text
complete Search Product Contract
→ broad realistic BoatDesign data coverage
→ simple browser Validation UI
→ native HullQ listing capability
→ listing identity / physical-listing truth
→ Saved Search
→ monitoring/scheduler
→ real alerts
→ slim Pro proposition
→ internal burn-in
→ external product validation
```

"Slim" means minimal polish and minimal non-essential infrastructure. It does not mean removing core value-producing functionality.

## 10. Corpus and coverage policy remains

The prior approximately 20–30-design Seed-Corpus ceiling is not the Gate-1 target.

Use:

> **Coverage, not arbitrary design count.**

Track at least:

- **Catalog Coverage:** canonical BoatDesigns evaluable against the accepted Search Product Contract;
- **Native Market Coverage:** relevant native HullQ listing supply mapped to canonical designs/configurations and usable by real target-user searches.

The existing approximately 1,700 identity-resolved/canonical models remain a legitimate enrichment target where the scalable data pipeline can process them at acceptable marginal cost.

`UNKNOWN`, `CONFLICT`, ambiguity and incomplete configuration coverage remain valid outcomes. Do not manually perfect every model before use.

## 11. Search completeness remains mandatory

Before Gate 1, the accepted HullQ Search Product Contract must be fully exposed in the Validation UI and work through deterministic semantics.

Hard requirements remain hard. Near misses remain structurally separate from confirmed matches. Explicit `UNKNOWN` remains first-class.

## 12. Slice sequencing after SLICE-0039

Do not widen SLICE-0039.

After SLICE-0039 is accepted and closed, re-plan subsequent slices against this decision.

The full native listing market is a program outcome composed of bounded capabilities, not one oversized slice.

Likely capability sequence includes, subject to dependency review:

1. lock/formalize the complete HullQ Search Product Contract;
2. implement remaining Search-contract semantics/filters in bounded slices;
3. scale Search-contract data coverage;
4. expose the full Search contract through a simple Validation UI;
5. define the native Listing domain contract;
6. create one native listing end-to-end;
7. attach a listing to canonical BoatDesign/configuration identity without collapsing truth scopes;
8. add listing read/search surfaces;
9. add listing update/status lifecycle;
10. add broker/seller identity/contact routing;
11. add media handling only when rights/storage rules are defined;
12. add bulk/feed import capability;
13. add dedup/identity handling where multiple listing intake paths require it;
14. persist exact Saved Searches;
15. connect native listing events to Saved-Search evaluation;
16. send real alerts;
17. expose the slim Pro proposition;
18. run internal burn-in;
19. run external Gate-1 validation.

This list is a dependency-oriented planning guide, not permission to start later capabilities early.

## 13. Governance remains intact

The pivot does not relax:

- strict truth;
- provenance;
- fail-closed behavior;
- configuration scope;
- physical-listing scope;
- explicit `UNKNOWN`;
- source/media rights;
- ONE-CAPABILITY CHECK;
- VISIBLE-RESULT CHECK;
- PRODUCT EXECUTION PLAN ALIGNMENT;
- exact-head review/gates;
- slice isolation.

## 14. Controlling one-sentence direction

> **HullQ will become a technically differentiated native sailboat listing and discovery market whose core advantage is deterministic, configuration-aware technical Search and monitoring; authorized external marketplaces may supplement inventory, but HullQ's viability must not depend on permission from any single external marketplace.**
