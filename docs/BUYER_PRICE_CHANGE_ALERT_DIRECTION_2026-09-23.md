# HullQ — Buyer Price-Change Alert Direction

**Date:** 2026-09-23  
**Status:** ACCEPTED OWNER PRODUCT DIRECTION; implementation scope/timing remains open  
**Scope:** buyer persistence / monitoring / price-history product  
**Does not modify:** SLICE-0065 scope, Search semantics, ranking, broker pricing, launch gates or current public-listing truth

## 1. Product requirement

HullQ must support buyer-facing alerts when the asking price of a relevant listing changes.

This is not merely a generic notification feature. It is part of HullQ's buyer monitoring value proposition and a natural extension of persistent interest / Saved Search / listing monitoring.

Working product loop:

```text
buyer expresses durable interest
→ HullQ monitors current accepted listing offer truth
→ asking-price state changes
→ HullQ records the price-change event/history
→ eligible buyer receives a factual price-change alert
```

## 2. Why this matters

Price movement is materially useful to yacht buyers because it can change:

- affordability;
- urgency;
- negotiation context;
- shortlist priority;
- perceived seller motivation;
- comparison against similar listings.

For HullQ, price-change monitoring also creates a durable reason for buyers to return after their initial Search.

## 3. Truth boundary

Price alerts MUST be based on observed/accepted offer-state changes, never guessed seller intent.

For native HullQ listings, the natural source is the accepted revisioned NativeListing offer model.

A future alert must distinguish factual transitions such as:

```text
EUR 250,000 → EUR 235,000
EUR 235,000 → EUR 245,000
AMOUNT → POA
POA → AMOUNT
currency/value change where valid
```

HullQ must not label every change a “price reduction”.

Examples:

- lower amount in the same currency = factual decrease;
- higher amount in the same currency = factual increase;
- AMOUNT↔POA = price-mode change;
- simultaneous currency change requires careful factual presentation and MUST NOT invent a converted gain/loss unless an accepted FX-comparison rule exists.

## 4. Historical record

The product direction includes durable listing price history where technically and legally supportable.

Useful future presentation may include:

- current asking price;
- prior observed asking prices;
- timestamps/effective order of price changes;
- explicit AMOUNT / POA transitions;
- price-reduction/increase markers only where mechanically justified;
- Days on Market and related listing-history context where supported by accepted events.

Observed asking price is not achieved sale price.

No achieved sale price may be inferred from listing price history.

## 5. Buyer subscription models to support later

Exact UX remains open, but implementation architecture must preserve the ability to alert buyers who have explicitly subscribed through one or more future surfaces, for example:

- a saved/shortlisted NativeListing;
- a persistent Saved Search;
- another explicit “notify me about this listing” action.

No implementation should assume that every anonymous page visitor may be notified.

Account persistence, consent, notification preferences, unsubscribe behavior and channel rules require a bounded owning slice.

## 6. Notification channels

Exact launch channel is undecided.

Potential channels include:

- in-app notifications;
- email;
- mobile push after an app/push boundary exists.

Channel selection, frequency/digest behavior and quieting/deduplication remain future decisions.

The domain event/history model should not be coupled to one delivery channel.

## 7. Broker/commercial independence

Price-change alerts describe accepted market facts.

Broker payment or plan status MUST NOT suppress, distort or reorder factual organic buyer alerts merely to protect a listing from showing a price change.

Commercial notification products may later exist, but they must remain separate from factual market truth.

## 8. External-market observations

Native HullQ listing history and externally observed marketplace price history are different evidence classes.

Any future use of external marketplace prices requires:

- lawful/contractually permitted source use;
- provenance;
- observation timestamps;
- identity/linkage confidence appropriate to the data;
- no silent merging with native HullQ offer truth.

This direction does not authorize scraping or reuse of third-party marketplace data.

## 9. Relationship to future monetization

Price-change alerts are a plausible HullQ Pro / persistence differentiator because open Search can remain free while durable monitoring provides continuing user value.

No pricing, tier, quota or entitlement is decided by this record.

## 10. Relationship to current roadmap

This feature is intentionally not added to SLICE-0065.

Current dependency direction:

```text
native revisioned offer truth already exists
+ future durable buyer identity/persistence
+ future subscription/monitoring model
+ accepted notification delivery
→ factual price-change alerts
```

It should be reconsidered when persistent Saved Search / account Shortlist / buyer monitoring work becomes due.

## 11. Future acceptance questions

A later owning slice must explicitly decide and test:

1. What durable object owns a price-alert subscription?
2. Does shortlist membership alone imply alerts, or is explicit opt-in required?
3. How are repeated edits/debounce handled?
4. What counts as a material price change, if any threshold exists?
5. Are all factual price changes notified or only reductions by default?
6. How are AMOUNT↔POA transitions communicated?
7. How are currency changes represented without false percentage claims?
8. How are withdrawn/stale/sold listings handled?
9. How are users notified and unsubscribed?
10. What price history is public vs account-only?
11. Which parts belong to Free vs Pro?
12. How are external-market observations kept separate from native offer truth?

## 12. Scope guard

This record preserves an owner-required future product capability.

It does **not**:

- create a new Search criterion;
- alter ranking;
- change NativeListing offer semantics;
- create a buyer account/persistence implementation;
- create Saved Search;
- send notifications;
- define a paid plan;
- authorize third-party data ingestion;
- change SLICE-0065;
- trigger Production Readiness or public launch.
