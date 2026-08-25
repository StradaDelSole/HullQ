# OQ-018 Research — Product-Led SEO / Organic Discovery, 2026-08-25

**Status:** RESEARCH INPUT — supports the accepted ADR-0007 architecture and future OQ-018 decision; does not by itself resolve OQ-018.  
**Reviewed:** 2026-08-25  
**Scope:** current primary search-engine/web standards relevant to HullQ's zero-budget, data-driven organic-growth strategy.

## Research question

How should HullQ optimize its already accepted "Search Architecture and SEO are product architecture" doctrine for a product with effectively no paid marketing budget, a large structured sailboat dataset, multidimensional faceted search, thousands of potential entity pages, comparisons and technical landing pages?

## Executive finding

HullQ is unusually well suited to **product-led SEO** because its useful product output and its useful public search surface can be generated from the same canonical data and query semantics.

The highest-leverage strategy is not a traditional high-volume blog. It is:

```text
canonical HullQ data
        ↓
useful product/search functionality
        ↓
intentional public entity + discovery pages
        ↓
organic discovery
        ↓
search/user demand signals
        ↓
enrichment + page-promotion priorities
        ↓
better data and product
        ↺
```

This must remain constrained by an explicit **indexability promotion gate**. HullQ's faceted search can create effectively unbounded URL combinations; the interactive search surface and the indexable organic surface must therefore remain deliberately separate.

## Primary-source findings

### 1. Faceted search is HullQ's largest technical SEO opportunity and largest crawl risk

Google's dedicated faceted-navigation guidance states that parameterized filters can create extremely large or effectively infinite URL spaces, wasting crawl resources and slowing discovery of useful URLs. If filtered URLs are not intended for indexing, Google recommends preventing unnecessary crawling; if selected filter URLs are intended to be indexed, they need disciplined URL/canonical behavior.

Implication for HullQ:

- arbitrary technical searches remain available to users;
- arbitrary search/filter state must not automatically become indexable;
- selected high-value technical intents should be promoted into intentional, stable landing pages;
- OQ-018 must choose the exact crawl/noindex/robots/canonical/link policy for each URL class rather than relying on one generic rule.

Source:
- Google Search Central / Crawling Infrastructure — Managing crawling of faceted navigation URLs: https://developers.google.com/crawling/docs/faceted-navigation

### 2. Canonicalization must be coherent across redirects, canonical tags and sitemaps

Google identifies redirects and `rel=canonical` as strong canonicalization signals and sitemap inclusion as a weaker supporting signal. Google also recommends self-referential canonicals on canonical pages and warns against contradictory canonical signals.

Implication for HullQ:

- a public-page registry should be the source of truth for canonical URLs;
- sitemaps, page metadata and redirects must derive from that same registry;
- slug changes must not change the underlying HullQ identity;
- old public URLs need deterministic redirect/retirement behavior.

Sources:
- Google Search Central — Canonicalization: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- Google Search Central — Canonicalization troubleshooting: https://developers.google.com/search/docs/crawling-indexing/canonicalization-troubleshooting

### 3. Programmatic pages are viable only when they provide distinct user value

Google's spam guidance treats large-scale pages created primarily to manipulate rankings and offering little original value as scaled-content abuse. Google's people-first guidance emphasizes content that is useful to an intended audience.

For HullQ, this argues strongly **for data-rich programmatic pages and against AI filler**.

A technical landing page should exist because the page itself is useful: it should expose a meaningful query result, counts, comparable designs, relevant technical context and internal navigation. A page should not exist merely because a keyword combination can be generated.

Sources:
- Google Search Central — Spam policies / scaled content abuse and doorway abuse: https://developers.google.com/search/docs/essentials/spam-policies
- Google Search Central — Creating helpful, reliable, people-first content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content

### 4. Google's 2026 generative-AI guidance reinforces normal SEO rather than introducing a separate GEO system

In May 2026 Google added guidance specifically for generative AI features in Search. Google's position is that the same core SEO and quality systems remain relevant for AI Overviews and AI Mode, and that distinctive/non-commodity content is particularly valuable.

Implication for HullQ:

- do not create a separate "AI SEO" content layer;
- make canonical HullQ facts, comparisons, methodology, uncertainty and technical relationships clear in visible HTML;
- unique, queryable HullQ data is strategically more defensible than generic prose;
- AI-search visibility should be measured, but no invented AEO/GEO schema or keyword-stuffing system is justified.

Sources:
- Google Search Central — optimizing for generative AI features: https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- Google Search documentation updates, May/August 2026: https://developers.google.com/search/updates

### 5. Internal links are a domain-graph feature, not merely an SEO tactic

Google recommends normal crawlable `<a href>` links with descriptive anchor text and says that every important page should be linked from another page on the site.

HullQ's domain relationships naturally create high-quality internal links:

- BoatModel → BoatDesign/generation;
- model/design → Brand/builder where canonical relationships exist;
- model/design → technical category pages;
- model/design → comparable models;
- technical category → matching models;
- methodology/field definition → pages using that field.

Implication: internal linking should be generated from canonical domain/query relationships, not from a manually maintained SEO link farm.

Source:
- Google Search Central — Link best practices: https://developers.google.com/search/docs/crawling-indexing/links-crawlable

### 6. Database-generated metadata is acceptable when it is specific and useful

Google explicitly notes that on large database-driven sites, manually writing every meta description is not realistic and that programmatically generated descriptions can be appropriate when they use page-specific, human-readable data. Google's title guidance similarly emphasizes unique, concise and page-specific titles over boilerplate or keyword repetition.

Implication for HullQ:

- titles and descriptions should be deterministic templates fed by actual page-specific canonical facts;
- missing facts must not be invented to make metadata sound complete;
- title/description uniqueness should be testable by page class;
- visible page content remains more important than a meta-description-only strategy.

Sources:
- Google Search Central — title links: https://developers.google.com/search/docs/appearance/title-link
- Google Search Central — snippets/meta descriptions: https://developers.google.com/search/docs/appearance/snippet

### 7. Sitemaps should be segmented by page class for both crawl hygiene and measurement

Google limits an individual sitemap to 50,000 URLs / 50 MB uncompressed and explicitly notes that multiple sitemaps can help monitor separate groups in Search Console. Sitemaps should contain preferred canonical URLs.

Implication for HullQ:

Prefer a sitemap index with page-class segmentation, for example:

```text
sitemap-index.xml
  boats-*.xml
  designs-*.xml
  builders.xml
  designers.xml          # only if/when canonical designer pages exist
  technical-pages.xml
  comparisons-*.xml
  methodology.xml
```

Exact taxonomy remains OQ-018 work. Splitting by page class makes indexation quality measurable rather than hiding all URLs in one giant sitemap.

Source:
- Google Search Central — Build and submit a sitemap: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap

### 8. Search Console should become a product-feedback input

Google Search Console exposes query/page/country performance, indexing state, sitemap state and Core Web Vitals. For HullQ this data should not be treated only as a marketing report.

Useful product feedback examples:

- impressions for a technical query with no dedicated landing page → landing-page candidate;
- repeated organic demand around a field with poor data completeness → enrichment priority;
- strong impressions / weak CTR on a useful page → title/snippet/intent mismatch investigation;
- poor indexation within one sitemap class → page-class or crawl-quality problem;
- organic arrivals that then use compare/search/save → evidence of high-quality acquisition.

Source:
- Google Search Central — Get started with Search Console: https://developers.google.com/search/docs/monitor-debug/search-console-start

### 9. Core Web Vitals are a release concern, not a vanity score

Google's current good thresholds remain:

- LCP <= 2.5 seconds;
- INP < 200 ms;
- CLS < 0.1.

Google also warns against reducing page experience to one score. HullQ should use these as field-performance quality thresholds while keeping the primary goal a fast, usable search/compare experience.

Sources:
- Google Search Central — Core Web Vitals: https://developers.google.com/search/docs/appearance/core-web-vitals
- Google Search Central — Page experience: https://developers.google.com/search/docs/appearance/page-experience

### 10. Astro/server-rendered HTML remains a strong fit

Google can render JavaScript, but its JavaScript SEO guidance still favors making canonical URL, title, metadata and meaningful crawlable content reliable in HTML. HullQ has already selected Astro + TypeScript with selective React islands.

Implication:

- public entity/discovery pages should deliver their primary content and metadata without requiring client-side reconstruction;
- React islands should enhance filters, comparisons, charts and saved-search interactions rather than make the public page a client-only shell.

Source:
- Google Search Central — JavaScript SEO basics: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics

### 11. Structured data must be conservative

Google supports specific structured-data search features, but unsupported markup does not create a rich result by itself. Schema.org has `Vehicle` and `ProductModel`, yet a historical/reference sailboat-model page is not automatically a Google merchant-product page.

Implication:

Safe early candidates include truthful site/page semantics such as:

- `Organization` for HullQ itself where appropriate;
- `BreadcrumbList` for page hierarchy;
- `WebSite`/general page identity where appropriate.

Whether BoatModel/BoatDesign pages should use `ProductModel`, `Vehicle`, another schema.org representation or only generic semantic markup must be decided at OQ-018 against then-current Google support. HullQ must not add fake `Offer`, `Review`, `AggregateRating`, price or other fields merely to qualify for rich results.

Sources:
- Google Search Central — structured-data search gallery: https://developers.google.com/search/docs/appearance/structured-data/search-gallery
- Google Search Central — Organization: https://developers.google.com/search/docs/appearance/structured-data/organization
- Google Search Central — BreadcrumbList: https://developers.google.com/search/docs/appearance/structured-data/breadcrumb
- Schema.org — Vehicle: https://schema.org/Vehicle
- Schema.org — ProductModel: https://schema.org/ProductModel

### 12. Internationalization should be designed before translation, not after

Google recommends distinct localized URLs and reciprocal alternate-version declarations when multiple localized versions exist. Translating only navigation/template elements does not create genuinely localized main content.

Zero-budget implication for HullQ:

- prefer one strong launch language over prematurely maintaining many thin translations;
- if multilingual expansion is justified later, use stable language URLs plus one consistent hreflang implementation and translated main content;
- do not create mass machine-translated pages solely to enlarge the index.

Source:
- Google Search Central — localized versions / hreflang: https://developers.google.com/search/docs/specialty/international/localized-versions

### 13. Bing/AI discovery is worth a low-cost secondary implementation path

Bing's current webmaster guidance recommends crawlable internal links, XML sitemaps and IndexNow. Bing also exposes AI Performance reporting in Webmaster Tools and explicitly connects freshness/indexing hygiene with Copilot/AI visibility.

Implication:

- Google remains the primary organic architecture reference;
- Bing Webmaster Tools should be configured at launch;
- IndexNow is a low-complexity optional notification mechanism for canonical URL additions/updates/deletions, particularly useful when HullQ pages materially change;
- IndexNow does not replace sitemaps and is not a Google indexing mechanism.

Sources:
- Bing Webmaster Guidelines: https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a
- IndexNow documentation: https://www.indexnow.org/documentation
- Bing Webmaster Blog — AI Performance, 2026: https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview

### 14. Google Preferred Sources is interesting but not a core launch dependency

Google's Preferred Sources feature expanded in 2026 and can influence how a user sees sources in Top Stories and, where available, AI Mode/AI Overviews after the user explicitly selects a source.

HullQ should evaluate this only after it has an established audience and if the domain is eligible. It does not substitute for technical SEO, authority or useful pages.

Source:
- Google Search Central — Preferred Sources: https://developers.google.com/search/docs/appearance/preferred-sources

## Optimized strategic conclusions for HullQ

The research changes the earlier strategy in six useful ways:

1. **Introduce an explicit page/indexability registry.** Indexability is a promoted product state, not a side effect of routing.
2. **Treat Search Console/Bing Webmaster data as product research.** Organic query demand should inform data enrichment and landing-page promotion.
3. **Create sitemap classes for measurement, not merely discovery.** This lets HullQ compare indexation quality by page type.
4. **Make AI visibility an outcome of good SEO + unique data.** Do not build a separate speculative GEO content system.
5. **Design multilingual URL/hreflang rules before the second language.** With a zero budget, launch-language depth is more valuable than premature translation breadth.
6. **Use change notification selectively.** Sitemaps remain the canonical inventory; IndexNow can supplement freshness for participating engines.

## Items deliberately left for OQ-018

This research does not choose the exact:

- public URL grammar;
- slug collision/rename syntax;
- page-type list;
- minimum data/result thresholds for indexability;
- robots.txt vs noindex vs link-behavior policy for interactive facets;
- pagination strategy;
- comparison-page identity/creation threshold;
- schema.org mapping for BoatModel/BoatDesign;
- sitemap shard sizes/names;
- initial launch language;
- exact performance budgets beyond the current Core Web Vitals good thresholds;
- analytics/provider implementation details.

Those choices require the query contract, public read models and then-current search-engine guidance and therefore remain correctly gated by OQ-018.
