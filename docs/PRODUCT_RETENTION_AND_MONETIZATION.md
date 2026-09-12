# HullQ — Retention and Monetization Strategy

**Status:** ACTIVE product strategy
**Updated:** 2026-08-22
**Related:** REQ-PROD-004..005, REQ-ALERT-001..002, REQ-SUB-001..006, REQ-MARKET-005..006, OQ-006, OQ-016, OQ-017

## 1. Retention correction

HullQ MUST NOT model the user lifecycle as simply `search → purchase → churn`. Sailboat ownership does not necessarily end market interest. A meaningful segment of sailors may continue to follow the used-boat market while owning a boat because they remain emotionally engaged with boat designs, compare alternatives, consider upgrades, or would act on a rare opportunity.

This is a **product hypothesis to validate empirically**, but it materially changes how HullQ should be designed and evaluated. Purchase frequency alone is therefore not a sufficient proxy for retention potential.

## 2. Retention segments

### Active Buyer
Actively intends to buy and searches frequently over a bounded period.

### Owner-Watcher
Already owns a boat but continues to monitor preferred technical profiles and the broader market.

### Upgrade / Opportunity Hunter
Would change boats if an unusually strong match, price or configuration appears.

### Design Enthusiast
Uses HullQ for discovery, comparison and market awareness even without an immediate transaction.

These segments may overlap and a single user may move between them over time.

## 3. Product implication

The durable object is the **technical preference/query**, not only the current purchase session. HullQ should be able to persist a query for months or years and evaluate new market inventory against it.

Recommended conceptual separation:

```text
Search
  ↓ optionally persist
SavedQuery
  ↓ optionally activate
Monitor
  ↓ detects an event
Alert

SubscriptionEntitlement
  └─ controls capacity/frequency/features, not query semantics
```

A SavedQuery is a user's durable technical preference. A Monitor is an active background evaluation of that query. An Alert is a notification event produced by a Monitor. Subscription entitlements decide how many monitors may be active and what monitoring capabilities they receive.

## 4. Preferred freemium thesis

The search/discovery engine should remain generous because it is the acquisition, trust and SEO surface. Monetization should attach primarily to persistent monitoring and convenience.

Initial product hypothesis:

### HullQ Free
**Search everything. Save 5 searches. Monitor 2.**

Purpose: make the core product genuinely useful, permit users to form a HullQ habit, and demonstrate the value of persistent technical queries without giving away all ongoing monitoring value.

### HullQ Plus
**Monitor 10 technical searches across supported markets.**

Likely additional entitlement dimensions may include higher monitoring frequency and broader supported-market coverage. Exact packaging remains open.

### HullQ Pro
**Advanced monitoring, faster alerts, price tracking, larger limits.**

Potential premium capabilities include higher monitor limits, faster event delivery, broader market coverage, price-change tracking and advanced market-watch intelligence. Subject to OQ-017 and source rights, this may include observed asking-price history, model/generation/configuration trend summaries, days-on-market style observations and alerts when an asking price changes.

HullQ MUST distinguish observed **asking prices** from achieved **sale prices**. A listing disappearing is not evidence that it sold, nor evidence of the achieved transaction price.

## 5. What is accepted vs open

### Accepted product direction

- core search stays available on Free in the initial freemium model;
- persistence/monitoring is the primary subscription lever;
- Free / Plus / Pro tiers are supported;
- Search, SavedQuery, Monitor, Alert and SubscriptionEntitlement are separate domain concepts;
- entitlement limits and monitoring capabilities are configurable rather than hard-coded;
- post-purchase owner-watch behavior is a first-class retention hypothesis.

### Still open / must be validated

- final prices;
- whether Free uses exactly 5 saved queries and 2 monitors;
- whether Plus uses exactly 10 monitors;
- exact alert cadence by tier;
- market-count limits;
- what belongs in Pro;
- exact historical price-intelligence retention/aggregation semantics under OQ-017;
- willingness to pay;
- long-term owner-watcher retention rate;
- conversion/churn economics.

These items are governed by OQ-006 and OQ-016 rather than being silently fixed in code.

## 6. Key metrics

Do not judge retention solely by boat purchases. Track at minimum:

- SavedQuery creation rate;
- Monitor activation rate;
- number of active monitors per user;
- 30/90/180/365-day monitor survival;
- post-purchase continuation of monitoring where observable/consented;
- alert open/click rate;
- Free → Plus conversion;
- Plus → Pro conversion;
- monitor-limit hit rate;
- churn after purchase vs continued owner-watch usage;
- revenue per active monitor;
- profit per maintenance hour.

## 7. Guardrail

HullQ MUST NOT deliberately cripple the free technical search merely to manufacture conversion. Paid value should come from persistent automated work HullQ performs for the user: continued monitoring, faster notification, broader monitoring capacity and additional market-watch intelligence.

## 8. Deferred dealer / broker marketplace opportunity

A separate supply-side commercial hypothesis is retained in `docs/DEALER_MARKETPLACE_OPPORTUNITY.md`.

Public industry evidence shows both material concentration among major marine marketplace brands and documented dealer frustration over escalating marketplace costs. This creates a potentially important future opportunity for HullQ to offer inexpensive, transparent dealer inventory participation linked to technically qualified buyer searches rather than compete as a generic classified portal.

This opportunity is explicitly **not current scope**. It does not alter the accepted Free / Plus / Pro buyer-side thesis, authorize marketplace implementation, or set dealer prices. It should be revisited only after HullQ has a sufficiently broad canonical universe, a working technical query product, measurable buyer intent and at least one permitted market-access path.

Acquisition by an incumbent is retained only as optional strategic upside. HullQ MUST NOT make early product or architecture decisions on the assumption that an incumbent will acquire the project.

## 9. Deferred merchandise / physical brand-extension hypothesis

A small HullQ merchandise shop is retained as a **later, low-priority brand/community extension**, not as a core revenue pillar and not as current implementation scope.

The preferred direction is deliberately narrow and low-maintenance:

- high-quality, restrained apparel or headwear rather than generic novelty sailing merchandise;
- stickers and a small number of practical marine-adjacent items where they fit the brand;
- especially HullQ-native technical prints/posters derived from the product's own design and data language, such as model profiles, construction/configuration typologies or well-designed data visualizations;
- print-on-demand or external fulfilment wherever practical;
- no inventory-heavy retail operation, warehousing or fulfilment burden unless later demand clearly justifies it.

The strategic purpose is primarily **brand affinity, community identity and modest ancillary revenue**. Even small revenue can be worthwhile if operational cost and maintenance remain negligible.

The sequencing guardrail is explicit: **quality and usability of the HullQ core product come first**. A merchandise shop should only be considered once HullQ has an actual audience and recognizable product/brand identity. Merchandise work MUST NOT delay canonical data quality, the query/search product, market integration or other core product milestones.
