# HullQ — Search & SEO Architecture

**Status:** ACCEPTED ARCHITECTURAL BASELINE  
**Decision:** ADR-0007  
**Detailed public-surface implementation gate:** OQ-018  
**Accepted product-led distribution strategy:** `docs/PRODUCT_LED_SEO_STRATEGY.md`

## Core principle

> **Search Architecture and SEO are part of product architecture.**

HullQ's organic discoverability is not a marketing layer that may be bolted onto the product after implementation. The technical query engine, public information architecture, URL system, rendering model, internal linking, indexation policy and performance characteristics form one product/distribution architecture.

This principle is particularly important for HullQ because the product intentionally creates a large structured evergreen knowledge/search surface over thousands of sailboat identities and technical characteristics.

## 1. Two related but distinct search surfaces

HullQ MUST distinguish:

1. **interactive technical search** — arbitrary user queries over canonical technical fields;
2. **public organic discovery surface** — intentionally selected canonical/indexable pages useful to humans and search engines.

Every interactive filter combination MUST NOT automatically become an indexable landing page.

## 2. Canonical public entities

Likely public canonical page classes include, subject to OQ-018:

- BoatModel pages;
- BoatDesign/generation pages where distinct enough to warrant a page;
- curated technical-category/search landing pages with substantial unique utility;
- comparison pages only where they have a stable intentional identity and useful content;
- editorial/explanatory pages for HullQ technical concepts.

Arbitrary transient query state, sort orders, pagination variants, empty result sets and near-duplicate faceted combinations SHOULD NOT become an uncontrolled indexable URL universe.

## 3. URL architecture

Before public frontend implementation, OQ-018 MUST define:

- stable public URL grammar;
- canonical identity/slug behavior and rename handling;
- representation of intentional technical landing pages;
- query-parameter handling;
- canonicalization rules;
- redirects/migrations for changed public identifiers;
- which URL classes are crawlable/indexable.

Domain IDs remain stable internal identity. Human-readable slugs MUST NOT become the sole canonical identity key.

## 4. Faceted navigation and crawl control

HullQ's strongest UX capability — multidimensional filtering — can generate a combinatorial URL space. Therefore crawl/index behavior MUST be designed together with filter behavior.

The architecture MUST:

- avoid unbounded crawlable combinations;
- prevent duplicate/sort-only/filter-order URL variants from becoming competing canonical pages;
- explicitly choose which technical combinations deserve persistent organic landing pages;
- retain full interactive filtering for users even when a filter state is intentionally non-indexable.

OQ-018 determines the exact robots/noindex/canonical/linking policy.

## 5. Rendering and crawlability

Framework choice remains OQ-008, but it MUST satisfy the product's search-discovery requirements. Approved indexable pages MUST expose meaningful primary content, crawlable navigation links and metadata reliably.

Bot-specific dynamic rendering is not the baseline architecture. The selected frontend approach SHOULD favor server-rendered, statically generated or otherwise reliably rendered HTML for canonical public discovery surfaces while preserving a rich interactive client experience.

## 6. Canonicalization and sitemaps

HullQ MUST maintain one preferred canonical URL for each intentionally indexable content identity. XML sitemaps MUST be generated from the same canonical page registry rather than from arbitrary observed frontend URLs.

Dataset/model changes that create/remove/migrate public pages MUST update canonical URLs, redirects and sitemap state coherently.

## 7. Internal linking

Organic discovery MUST be supported by the same domain graph users benefit from. Examples include:

- model → generation;
- design → designer/builder where public pages exist;
- design → comparable/similar designs;
- technical category → matching canonical designs;
- compare/discover routes back to stable entity pages.

Internal links MUST NOT depend exclusively on client-side events that crawlers cannot discover as normal links.

## 8. Structured data

Structured data is an optional representation of truthful visible content, not an SEO invention layer. HullQ MAY emit supported JSON-LD/schema mappings when they accurately describe the page. It MUST NOT manufacture achieved sale prices, ratings, reviews or unsupported attributes for search appearance.

The precise schema mapping belongs in OQ-018 because supported search features can change over time.

## 9. Performance and UX

SEO architecture MUST NOT sacrifice HullQ's actual product UX. Public pages and interactive search SHOULD share canonical data/read models while allowing different rendering strategies where justified.

Core Web Vitals and explicit performance budgets are release-quality concerns. Query interactions, filters and comparison views must remain responsive even as the design universe scales.

## 10. Observability

Public release SHOULD make organic-search health observable through:

- indexation/crawl errors;
- sitemap health;
- canonicalization anomalies;
- structured-data errors where used;
- search impressions/clicks;
- page-performance field/lab signals;
- unexpected growth in crawlable faceted URL count.

The exact provider/tooling is implementation-specific and not decided here.

## 11. Docs-to-code consequences

Frontend or routing code MUST NOT silently decide SEO semantics. Changes affecting public URLs, indexation, canonicalization, page taxonomy or rendering MUST trace to REQ-SEO requirements and, when structural, an accepted ADR/spec change.

## 12. External guidance baseline

The baseline is informed by current primary guidance registered in `research/evidence/SOURCE_REGISTER.md`, including Google Search Central guidance on URL structure/faceted navigation, JavaScript SEO, canonicalization, sitemaps and structured data, plus web.dev Core Web Vitals guidance. Exact implementation rules MUST be re-verified when OQ-018 is resolved and before public launch because search-engine guidance can change.

The 2026 product-led SEO research refresh is retained in `docs/research/OQ-018_PRODUCT_LED_SEO_RESEARCH_2026-08-25.md` and includes current Google guidance for faceted navigation, generative-AI search features, Search Console, metadata, internationalization and Core Web Vitals plus Bing/IndexNow discovery guidance.

## 13. Product-led organic-distribution doctrine

ADR-0007's architectural principle is operationalized by `docs/PRODUCT_LED_SEO_STRATEGY.md`.

The accepted strategic direction is:

- HullQ's canonical data/query engine is the primary organic-content moat;
- Product-Led SEO is a primary zero-budget distribution strategy;
- indexability is an intentional promoted page state, not a side effect of generating a route or serializing a user query;
- arbitrary faceted search remains a product feature while only selected stable intents become public organic landing pages;
- Search Console/internal-search demand should later feed landing-page promotion and data-enrichment priorities;
- programmatic pages must provide distinct user utility and must not rely on generic AI filler or doorway behavior;
- segmented sitemaps should support both discovery and page-class indexation measurement;
- AI-search visibility should be pursued through normal search quality, unique data, clear semantics and provenance rather than a speculative separate GEO content layer;
- multilingual expansion must be designed before translation and must not become thin machine-translated index growth;
- zero-budget authority should compound through original HullQ data, shareable search/compare/entity pages, methodology transparency and legitimate community/earned-media use.

These principles do **not** resolve OQ-018's exact URL grammar, indexability thresholds, robots/noindex rules, page taxonomy, schema mapping, language choice or release budgets. Those remain explicit pre-public implementation decisions.

## 14. Truth-backed SEO execution invariants

Competitive review in August 2026 showed that large indexable sailboat corpora can create a damaging split between an SEO page's promise and the actual technical result set. HullQ MUST avoid that split by making public technical/discovery pages projections of the same accepted truth/search semantics used by the product.

The following invariants are architectural requirements for OQ-018 and later public implementation:

1. **One truth engine.** Every indexable technical discovery/selection page MUST be backed by an explicit deterministic controlling HullQ query or equally deterministic accepted data derivation. A separate SEO-only eligibility implementation is not allowed.
2. **Search selects; editorial explains.** Editorial or AI-generated prose MAY explain a result set but MUST NOT widen, substitute, or silently override the controlling candidate set.
3. **Mechanical promise validation.** A hard numeric/categorical promise in a page identity, title, H1 or canonical intent (for example `under 40 ft`, `draft <= 1.50 m`, `full keel`) MUST be mechanically validated against every item presented as satisfying that promise. Known violations block indexability/release of that page state.
4. **Configuration scope survives publication.** Where material factory configurations differ, a public model/design page MUST NOT collapse them into one value in a way that implies universal applicability. Configuration-specific facts, ranges and explicit UNKNOWN/conflict states must remain representable and visible.
5. **No model-to-physical promotion.** Model/design/configuration facts MAY contextualize a market listing but MUST NOT become claims about the concrete physical boat without admissible listing-specific evidence under the market truth contract.
6. **Same truth read model.** Visible technical content, metadata, structured data and the controlling Search transition MUST derive from the same canonical/provenance-aware read model. Structured data cannot contain a stronger claim than the visible page.
7. **Executable continuation.** An indexable technical discovery page SHOULD provide a direct transition into interactive HullQ Search with the same controlling criteria, so the organic landing page is a product entry point rather than a disconnected article.
8. **Original-data preference.** Data studies/linkable assets SHOULD preferentially derive from unique HullQ datasets and accepted relationships — technical/configuration data and, when lawfully available later, market observations, price changes, Days-on-Market and provenance — rather than generic AI prose that merely restates existing web material.
9. **Demand-driven comparisons.** Comparison pages SHOULD be promoted from real external/internal demand and canonical comparable identities, not generated as an uncontrolled Cartesian product of models.
10. **No ranking folklore as architecture.** HullQ MUST NOT encode unsupported assumptions such as `bounce rate directly determines Google ranking`. SEO decisions must trace to current primary search-engine guidance or measured HullQ telemetry.

The implementation maxim is:

> **Do not write content around the product. Make the product generate uniquely useful indexable knowledge.**

And for technical landing pages:

> **Every important HullQ SEO page is backed by the same truth engine that powers HullQ Search.**

These invariants do not authorize early SEO implementation. They constrain later OQ-018/public-surface work when that work becomes the active capability under the Product Execution Plan.
