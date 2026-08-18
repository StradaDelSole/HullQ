# HullQ — Canonical Project Context

**Product:** HullQ  
**Tagline:** Find boats by what they are.  
**Role:** Sailboat design search engine + current-market finder; not a marketplace.

## Product definition

HullQ lets users discover sailboat designs by actual technical characteristics even when they do not know a model name, then searches current sales platforms for matching examples for sale.

## Core user flow

```text
USER REQUIREMENTS
length / draft / displacement / hull / keel / rudder / skeg /
construction / rig / ratios / year / etc.
        ↓
HULLQ DESIGN DATABASE
independent sailboat-design dataset
        ↓
MATCHING DESIGNS
        ↓
LIVE / ON-REQUEST MARKET SEARCH
source adapters
        ↓
NORMALIZE + DEDUPLICATE
        ↓
CURRENT BOATS FOR SALE
        ↓
COMPARE / SAVE / ALERT
```

## Vessel scope

From day one:

- monohulls
- catamarans
- trimarans

Multihulls are first-class objects. Do not overload a single legacy `Hull Type` field with hull, keel and rudder semantics.

## Data doctrine

1. Build an independent production dataset with **broad SailboatData-like coverage from the beginning**.
2. Separate **database breadth** from **verification depth**: thousands of identities may exist with partial fields while high-value records are progressively enriched and deeply verified.
3. Treat the 50–100 design research set as a benchmark corpus for the pipeline, not as the product database or launch MVP.
4. Preserve source provenance and confidence.
5. Never invent missing values.
6. Missing/unknown data must never be interpreted as a negative characteristic.
7. Preserve conflicts for review.
8. Keep input identity distinct from verified identity.
9. Store canonical physical values in SI where practical.
10. Calculate derived ratios internally with a documented `formula_version`.
11. Appropriately licensed/open data may bootstrap common factual fields; HullQ research prioritizes gaps, variants and HullQ-critical fields.
12. Treat the existing Sailboatdata scrape as immutable reference/prototype data only.
13. Design research for high-throughput automation with exception-based human review.

Detailed contracts live in `specs/`, the research process in `research/`, and the coverage strategy in `docs/DATABASE_COVERAGE_STRATEGY.md`.

## Search model

Primary search axes:

- LOA / length
- year
- hull configuration
- keel type
- rudder type
- skeg type
- draft
- displacement
- hull material

Advanced search can include dimensions, construction, rig, derived ratios, engine/tanks, designer and builder.

Comparison of normalized design data is a core feature.

## Market strategy

The preferred architecture is live/on-request market search with short-lived, source-dependent caching. HullQ performs the hard technical filtering against its own BoatDesign database; market sources receive simpler make/model/generation lookups.

Every marketplace integration is isolated behind an adapter returning one canonical listing shape. Access method and platform terms must be verified before implementation.

## Accounts, persistent market watch and alerts

HullQ is not designed only for a one-time active purchase cycle. Many sailors continue watching the market while already owning a boat: for curiosity, upgrades, rare opportunities and the possibility that an unusually good match appears. This **owner-watcher / opportunity-hunter** behavior is an explicit retention hypothesis to validate, not an assumed fact.

Accounts support:

- saved technical queries
- favorites
- active monitors
- alert settings
- notifications when **any design matching technical criteria** appears on the market

Alerts should group identical model lookups and notify only on genuinely new matches. A saved technical query should be able to remain useful across purchase and ownership cycles.

## Freemium / subscription thesis

The preferred initial commercial model keeps discovery broadly open and monetizes persistent monitoring rather than basic search. Current product hypothesis:

- **HullQ Free — Search everything. Save 5 searches. Monitor 2.**
- **HullQ Plus — Monitor 10 technical searches across supported markets.**
- **HullQ Pro — Advanced monitoring, faster alerts, price tracking/history intelligence, larger limits.**

These are product defaults/hypotheses, not immutable pricing contracts. Exact limits, pricing, alert cadence and market entitlements must be configurable and validated before paid launch. Domain modeling must keep `Search`, `SavedQuery`, `Monitor`, `Alert` and `SubscriptionEntitlement` separate. Historical market/price intelligence is gated by OQ-017 and source rights; observed asking prices must never be presented as achieved sale prices, and listing disappearance alone is not a sale event.

## Backend / application direction

No backend framework is currently accepted. Strapi was an earlier pragmatic candidate, but OQ-011 must decide whether it remains appropriate; OQ-012 separately decides persistence/search technology. Domain concepts must remain framework-independent. Current core concepts include BoatModel, BoatDesign, NamedVariant, DesignOption, ResolvedConfiguration, Source/provenance records, ResearchJob, Search, SavedQuery, Monitor, Alert, SubscriptionEntitlement, MarketListing and SourcePlatform.

## Explicit scope guardrail

A feature belongs in early HullQ only if it directly strengthens:

```text
FIND DESIGN → FIND BOAT FOR SALE → COMPARE / SAVE → ALERT
```

Out of scope: social features, comments, owner reviews, forums, AI boat advisor, route planning, weather, maintenance logs, generic ownership tools, financing calculator and insurance comparison.

## Business thesis

HullQ is a search layer above existing markets. Technical design data is mostly static; listing data can remain at source. HullQ avoids seller acquisition, listing creation, messaging, payments, contracts, disputes and marketplace moderation.

The current business objective is **not venture scale by default**. The base case is a lean, highly automated niche web property where even a few hundred euros of monthly profit is worthwhile and low-thousands per month would be a strong result if ongoing human maintenance remains minimal. If traction later demonstrates materially larger potential, deliberate scaling can be reconsidered.

Operational economics therefore prioritize **profit-to-maintenance ratio** and low unplanned maintenance hours, especially for market integrations.

## Current priority

Establish a broad design universe and a scalable research pipeline, then build the smallest complete product chain from a technical requirement to an actual boat for sale. The product test must run against sufficiently broad coverage; a 50–100 design corpus is only a research benchmark and cannot validly test unknown-model discovery.

## Search/distribution architecture principle

**Search Architecture and SEO are part of product architecture.** HullQ's technical-query UX, canonical public entity pages, URL/indexation system, rendering, internal linking, sitemaps, faceted-navigation controls and performance requirements MUST be designed together from the outset. SEO is not a post-launch retrofit. Exact public-surface mechanics remain gated by OQ-018 and current primary search-engine guidance.
