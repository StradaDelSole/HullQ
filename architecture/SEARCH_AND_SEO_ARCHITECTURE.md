# HullQ — Search & SEO Architecture

**Status:** ACCEPTED ARCHITECTURAL BASELINE — amended by owner-direct marketplace pivot when merged  
**Decision:** ADR-0007 + 2026-09-14 owner-direct product direction  
**Detailed broad/indexable public-discovery gate:** OQ-018 and later accepted page-class decisions  
**Accepted product-led distribution strategy:** `docs/PRODUCT_LED_SEO_STRATEGY.md`

## Core principle

> **Search Architecture and SEO are part of product architecture.**

HullQ's organic discoverability is not a marketing layer that may be bolted onto the product after implementation. The technical query engine, public information architecture, URL system, rendering model, internal linking, indexation policy and performance characteristics form one product/distribution architecture.

This principle is particularly important for HullQ because the product intentionally creates a large structured evergreen knowledge/search surface over thousands of sailboat identities and technical characteristics.

The existence of bounded public `noindex` listing/Search surfaces does not itself authorize broad organic indexation. OQ-018 and later accepted page-class decisions gate the broader indexable discovery system, not the mere existence of any public SSR route.

## 1. Two related but distinct search surfaces

HullQ MUST distinguish:

1. **interactive technical search** — arbitrary user queries over canonical technical fields;
2. **public organic discovery surface** — intentionally selected canonical/indexable pages useful to humans and search engines.

Every interactive filter combination MUST NOT automatically become an indexable landing page.

SLICE-0049/0051 public listing/Search page classes remain deliberately bounded and `noindex` under their accepted contracts. They are product surfaces, not an implicit decision to index arbitrary search state.

## 2. Canonical public entities

Potential indexable canonical page classes include, subject to the accepted detailed public-surface gate:

- BoatModel pages;
- BoatDesign/generation pages where distinct enough to warrant a page;
- curated technical-category/search landing pages with substantial unique utility;
- comparison pages only where they have a stable intentional identity and useful content;
- editorial/explanatory pages for HullQ technical concepts.

Arbitrary transient query state, sort orders, pagination variants, empty result sets and near-duplicate faceted combinations SHOULD NOT become an uncontrolled indexable URL universe.

## 3. URL architecture

Before **broad/indexable organic-discovery implementation**, the controlling detailed public-surface decision MUST define or explicitly preserve:

- stable indexable public URL grammar;
- canonical identity/slug behavior and rename handling;
- representation of intentional technical landing pages;
- query-parameter handling for indexable/crawlable states;
- canonicalization rules;
- redirects/migrations for changed public identifiers;
- which URL classes are crawlable/indexable.

This requirement does not invalidate already accepted bounded public `noindex` listing/Search routes whose URL/canonicalization behavior is defined by their own accepted slice/page-class contracts.

Domain IDs remain stable internal identity. Human-readable slugs MUST NOT become the sole canonical identity key.

## 4. Faceted navigation and crawl control

HullQ's strongest UX capability — multidimensional filtering — can generate a combinatorial URL space. Therefore crawl/index behavior MUST be designed together with filter behavior.

The architecture MUST:

- avoid unbounded crawlable combinations;
- prevent duplicate/sort-only/filter-order URL variants from becoming competing canonical pages;
- explicitly choose which technical combinations deserve persistent organic landing pages;
- retain full interactive filtering for users even when a filter state is intentionally non-indexable.

The detailed public-surface decision determines the exact robots/noindex/canonical/linking policy for broad/indexable discovery states. Accepted bounded page-class decisions may keep specific routes `noindex` before that broader system exists.

## 5. Rendering and crawlability

Astro is the accepted main public-web framework, with React islands only where interaction justifies them. Approved indexable pages MUST expose meaningful primary content, crawlable navigation links and metadata reliably.

Bot-specific dynamic rendering is not the baseline architecture. Public discovery surfaces SHOULD favor server-rendered, statically generated or otherwise reliably rendered HTML while preserving a rich interactive client experience where justified.

FastAPI remains the sole application/domain API boundary; SEO/public rendering must not create a second implementation of HullQ Search or truth semantics.

## 6. Canonicalization and sitemaps

HullQ MUST maintain one preferred canonical URL for each intentionally indexable content identity. XML sitemaps MUST be generated from the same canonical page registry rather than from arbitrary observed frontend URLs.

Dataset/model changes that create/remove/migrate indexable public pages MUST update canonical URLs, redirects and sitemap state coherently.

Current bounded `noindex` listing/Search surfaces do not authorize inclusion of arbitrary Search combinations in sitemaps.

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

The precise broad schema mapping belongs to the detailed public-surface gate because supported search features can change over time. A slice may introduce only the structured data explicitly authorized for its accepted page class.

## 9. Performance and UX

SEO architecture MUST NOT sacrifice HullQ's actual product UX. Public pages and interactive Search SHOULD share canonical data/read models while allowing different rendering strategies where justified.

Core Web Vitals and explicit performance budgets are release-quality concerns. Query interactions, filters and comparison views must remain responsive even as the design universe scales.

## 10. Observability

Public organic release SHOULD make search-discovery health observable through:

- indexation/crawl errors;
- sitemap health;
- canonicalization anomalies;
- structured-data errors where used;
- search impressions/clicks;
- page-performance field/lab signals;
- unexpected growth in crawlable faceted URL count.

The exact provider/tooling is implementation-specific and not decided here. General production operational observability is separately governed by `docs/governance/PRODUCTION_READINESS_GATE.md`.

## 11. Docs-to-code consequences

Frontend or routing code MUST NOT silently decide SEO semantics. Changes affecting public URLs, indexation, canonicalization, page taxonomy or rendering MUST trace to accepted requirements/page-class decisions and, when structural, an accepted ADR/spec change.

A public route can be implemented while deliberately `noindex`; that does not silently settle the later broad/indexable taxonomy.

## 12. External guidance baseline

The baseline is informed by current primary guidance registered in `research/evidence/SOURCE_REGISTER.md`, including Google Search Central guidance on URL structure/faceted navigation, JavaScript SEO, canonicalization, sitemaps and structured data, plus web.dev Core Web Vitals guidance. Exact implementation rules MUST be re-verified before broad public organic launch because search-engine guidance can change.

The 2026 product-led SEO research refresh is retained in `docs/research/OQ-018_PRODUCT_LED_SEO_RESEARCH_2026-08-25.md` and includes Google guidance for faceted navigation, generative-AI search features, Search Console, metadata, internationalization and Core Web Vitals plus Bing/IndexNow discovery guidance.

## 13. Product-led organic-distribution doctrine

ADR-0007's architectural principle is operationalized by `docs/PRODUCT_LED_SEO_STRATEGY.md`.

The accepted strategic direction is:

- HullQ's canonical data/query engine is the primary organic-content moat;
- Product-Led SEO is a primary zero-budget distribution strategy;
- indexability is an intentional promoted page state, not a side effect of generating a route or serializing a user query;
- arbitrary faceted Search remains a product feature while only selected stable intents become public organic landing pages;
- Search Console/internal-search demand should later feed landing-page promotion and data-enrichment priorities;
- programmatic pages must provide distinct user utility and must not rely on generic AI filler or doorway behavior;
- segmented sitemaps should support both discovery and page-class indexation measurement;
- AI-search visibility should be pursued through normal search quality, unique data, clear semantics and provenance rather than a speculative separate GEO content layer;
- multilingual expansion must be designed before translation and must not become thin machine-translated index growth;
- zero-budget authority should compound through original HullQ data, shareable search/compare/entity pages, methodology transparency and legitimate community/earned-media use.

These principles do **not** by themselves resolve every exact URL grammar, indexability threshold, robots/noindex rule, page taxonomy, schema mapping, language choice or release budget. Those details remain explicit decisions for the relevant broad/indexable page classes.

## 14. Truth-backed SEO execution invariants

Competitive review in August 2026 showed that large indexable sailboat corpora can create a damaging split between an SEO page's promise and the actual technical result set. HullQ MUST avoid that split by making public technical/discovery pages projections of the same accepted truth/Search semantics used by the product.

The following invariants constrain later broad/indexable public implementation:

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

These invariants do not authorize broad SEO implementation merely because bounded public routes exist. They constrain the relevant broad/indexable page-class work when that work becomes the active capability under accepted product execution governance.

## 15. Organic Search commercial independence

The 2026-09-14 owner-direct marketplace pivot adds a permanent Search governance invariant across professional and private supply:

```text
commercial consideration MUST NOT affect
organic eligibility
organic match classification
organic ordering
```

The following MUST NOT be inputs to organic Search truth/order:

- broker subscription/plan tier;
- private-seller fees;
- payment for verification/inspection/document processing;
- referral economics or expected commission;
- affiliate value;
- advertising relationship;
- any other HullQ revenue opportunity tied to the seller/listing.

Payment may fund a genuine service that produces/processes evidence. The resulting evidence is evaluated under the same accepted rules as materially equivalent evidence supplied without payment. Payment does not buy `CONFIRMED`, eligibility or position.

Future organic ordering may use accepted non-commercial logic such as explicit user sort, objective fit, price, location/distance, recency or another product-justified factor, but any such algorithm requires its own accepted semantics and must remain revenue-independent.

A future sponsored/featured advertising surface is not categorically prohibited, but it is outside the organic result set. If later accepted, it must be mechanically and visually separate: it cannot change organic eligibility/classification/ordering, replace an organic result, consume organic pagination positions or masquerade as an organic recommendation.

Changing the no-pay-to-rank/no-pay-to-organic-truth invariant requires an explicit Project Owner decision that acknowledges it is superseding this architecture rule; an ordinary pricing or growth experiment is insufficient.
