# Roadmap

## Phase 0 — Foundation

Completed or accepted:

- project context and repository authority order;
- broad universe + progressive verification depth;
- source-rights model and Source schema v0.2;
- BoatModel / BoatDesign generation / NamedVariant / DesignOption identity model;
- validation/test baseline;
- minimal 3-column research target input.

Current blockers before pipeline implementation:

- OQ-004 field-level provenance persistence is accepted;
- decide/version OQ-001 ratio formulas;
- decide OQ-010 Python/research toolchain;
- BoatDesign v0.3 is accepted; ResolvedConfiguration remains gated by downstream formula/search decisions.

## Phase 1 — Research benchmark corpus

Research a deliberately difficult 50–100 design benchmark corpus and measure:

- identity-resolution success
- variant/generation ambiguity
- primary/open-source coverage
- field and HullQ-critical completeness
- conflict rate
- keel/rudder/skeg manual-review rate
- automated acceptance rate
- human-review rate
- research time/cost per model
- human minutes per reviewed model

**This is a pipeline benchmark, not the HullQ launch database.**

Use results to refine taxonomy, validation and research automation before high-throughput scaling.

## Phase 2 — Broad design-universe ingestion

Move directly from the benchmark to broad ingestion aimed at **thousands of canonical sailboat identities**.

Directionally target SailboatData-like breadth over time (potentially 5,000–10,000+ identities), while accepting progressive/sparse enrichment.

Build in layers:

1. identity universe
2. basic searchable coverage
3. HullQ-critical fields
4. deep verification

Use appropriately licensed/open data for common factual bootstrap fields where useful; retain provenance. Concentrate independent research on HullQ-critical fields, conflicts, variants and gaps.

Track real-market identification/enrichment coverage as a major KPI while also tracking database breadth.

## Phase 3 — Technical query engine + compare

Search Architecture and SEO are part of product architecture under ADR-0007. Before the public frontend/search surface, resolve OQ-018 so URL/indexation/faceted-navigation/rendering semantics are designed alongside the query UX rather than retrofitted later.

Build the core product against a sufficiently broad database universe:

- curated canonical filters
- confirmed-match vs insufficient-data semantics
- design result pages
- side-by-side comparison
- unit conversion in UI while retaining canonical SI storage
- canonical/indexable BoatModel/BoatDesign discovery surfaces
- controlled curated technical landing-page strategy without indexing arbitrary filter combinations

A tiny sample database is not a valid product test for unknown-model discovery.

## Phase 4 — Market-access validation + one end-to-end source

Before depending on adapters, document for each candidate source:

- official API/feed availability
- partner/commercial access
- permitted retrieval/display/caching
- pricing and account requirements
- deep-link fallback
- expected maintenance burden

Then prove one end-to-end path:

```text
technical query
→ broad matching design set
→ marketplace lookup or permitted market path
→ canonical listings
→ deduplicate where applicable
→ display current boats for sale
```

## Phase 5 — Saved technical queries + monitoring + alerts

- login/account where required
- saved technical queries
- favorites
- explicit Monitor domain object
- alert settings and alert events
- technical-criteria alerts across any matching designs
- configurable SubscriptionEntitlement layer
- instrument owner-watcher / long-lived market-watch retention

The query itself is a first-class product object. Search, SavedQuery, Monitor, Alert and SubscriptionEntitlement remain separate concepts.

Initial freemium hypothesis:

- Free: search everything; save 5; monitor 2
- Plus: monitor 10 technical searches across supported markets
- Pro: advanced monitoring, faster alerts, price tracking/history intelligence, larger limits (subject to OQ-017/source rights)

Exact pricing and entitlement numbers remain configurable and are finalized under OQ-016.

## Phase 6 — Additional market sources + source health

Add sources only where access economics and maintenance fit the project's low-maintenance business objective. Monitor last successful run, errors, result count, latency and parse/schema failures.

## Continuous data track

After broad ingestion begins:

- enrich unknown/partial designs based on real-market frequency
- prioritize missing HullQ-critical fields
- deepen provenance and primary-source verification
- correct conflicts
- add newly observed designs/variants

## Parallel business/legal track

- Keep HullQ optimized first for a lean, highly automated niche business with low ongoing maintenance.
- Hundreds of euros of monthly profit can already be a valid outcome; low-thousands would be strong if maintenance remains minimal.
- Do not architecturally prevent larger scaling if traction later justifies it.
- Independent/open-data route remains the baseline.
- Optional Sailboatdata license inquiry remains separate.
- Obtain targeted Austrian/EU legal review before commercial use of scraped Sailboatdata values or legally uncertain market-access methods.
- Retain the documented dealer/broker marketplace opportunity in `docs/DEALER_MARKETPLACE_OPPORTUNITY.md`: concentrated incumbent marketplace ownership plus publicly documented dealer pricing frustration may create a future low-price supply-side opportunity once HullQ has real buyer traffic and qualified technical-search demand. This is deferred strategic research, not current implementation scope.
