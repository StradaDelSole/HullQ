# HullQ — Product-Led SEO Strategy

**Status:** ACCEPTED PRODUCT STRATEGY / strategic input to ADR-0007 and future OQ-018 implementation  
**Date:** 2026-08-25  
**Budget assumption:** effectively zero paid marketing budget  
**Detailed technical gate:** OQ-018 remains OPEN and must convert this strategy into exact URL/index/crawl/rendering/tests before public frontend/search release.

## 1. Strategic thesis

HullQ should treat organic discovery as a **product distribution system**, not as a separate content-marketing department.

The central doctrine is:

> **HullQ's data, search engine and public knowledge surface should compound each other's value.**

HullQ should not attempt to win organic search by publishing a large generic sailing blog or mass-generating keyword pages. Its defensible SEO asset is the structured, provenance-aware sailboat dataset plus the ability to query, compare and explain it.

The ideal loop is:

```text
better canonical data
        ↓
better technical search + compare
        ↓
more useful public entity/discovery pages
        ↓
more organic impressions and qualified visits
        ↓
real query/search behavior
        ↓
new landing-page and enrichment priorities
        ↓
better canonical data
        ↺
```

This is the primary zero-budget organic-growth doctrine for HullQ.

## 2. What HullQ should optimize for

HullQ should optimize for **qualified technical intent**, not raw traffic volume.

A user searching for:

```text
Hallberg-Rassy 352 draft
Najad 34 displacement
Hallberg-Rassy 352 vs Najad 34
sailboats with skeg-supported rudders
35-40 ft center-cockpit sailboats
aluminium sailboats under 40 ft
full-keel sailboats with shallow draft
```

is substantially more valuable than a large volume of generic traffic for terms such as `boats`, `sailing` or `yachts`.

The preferred acquisition profile is therefore:

- long-tail;
- technically specific;
- model/design research intent;
- comparison intent;
- characteristic-first discovery intent;
- high likelihood of continuing into HullQ search/compare/save/monitor behavior.

## 3. The public surface is a selected product surface

HullQ must keep two systems distinct:

```text
INTERACTIVE SEARCH
arbitrary user criteria and filter combinations
        ↓
very large / combinatorial state space
        ↓
useful to users
        ↓
NOT automatically indexable

PUBLIC ORGANIC SURFACE
intentional stable page identities
        ↓
quality/indexability gate
        ↓
canonical/indexable only when useful
```

Indexability must be a **promoted state**, not an accidental consequence of a router producing a URL.

OQ-018 should therefore define a machine-readable or otherwise deterministic **public-page/indexability registry** from which canonical tags, sitemap membership, page generation and retirement behavior can be derived.

## 4. Page-class strategy

### Tier A — canonical entity pages

These are the highest-priority evergreen pages because their identity comes from HullQ's canonical domain model.

Likely page classes include:

- BoatModel;
- BoatDesign / generation where a separate public page is useful and evidence-supported;
- Brand;
- builder/manufacturer Organization;
- designer only if/when HullQ has an accepted canonical designer identity/relationship model;
- later market/listing identities only after their own rights/identity decisions.

No entity may be invented only to create an SEO page.

A BoatModel page should eventually be capable of exposing, when supported:

- canonical preferred name and safe aliases;
- model/design relationship;
- builder/brand relationships where known;
- first/last built where supported;
- LOA/LWL/beam/draft/displacement and other technical fields;
- configuration/variant/generation distinctions;
- HullQ-derived metrics with method/version context;
- explicit unknown/conflict states rather than fabricated completeness;
- evidence/source provenance appropriate for public presentation;
- related technical collection pages;
- comparable models;
- links into live HullQ technical search.

The page's primary value must be the data/product itself. Introductory prose is secondary.

### Tier B — intentional technical discovery pages

HullQ's strongest product-led SEO opportunity is to turn selected stable technical intents into public discovery pages.

Examples, not yet binding URL grammar:

```text
/sailboats/skeg-supported-rudder
/sailboats/full-keel
/sailboats/center-cockpit
/sailboats/aluminium
/sailboats/35-to-40-feet
/sailboats/35-to-40-feet/skeg-supported-rudder
```

These pages must be backed by an explicit versioned HullQ query definition, not by hand-maintained lists.

A useful technical discovery page should provide more than a search-results dump. Depending on the intent it may expose:

- exact query meaning;
- confirmed-match count;
- insufficient-data count where OQ-009 semantics require it;
- matching canonical models/designs;
- distribution/context from HullQ's dataset;
- relevant field-definition/methodology links;
- adjacent useful discovery pages;
- a direct path to continue/refine the query interactively.

### Tier C — comparison pages

Stable model/design comparisons can be high-intent organic surfaces, for example:

```text
Hallberg-Rassy 352 vs Najad 34
Contessa 32 vs Albin Vega
```

Comparison pages should exist only where:

- both compared identities are canonical;
- the comparison has stable identity/order semantics;
- enough comparable supported fields exist to make the page independently useful;
- the page is not simply two thin entity pages stitched together;
- permutations do not create duplicate URLs.

The comparison should emphasize truthful data differences and explicit unknowns. Automated qualitative claims such as "better bluewater boat" must not be inferred without an accepted methodology.

### Tier D — methodology and technical concept pages

HullQ should publish high-quality explanatory pages where they directly support the product, for example:

- how HullQ defines draft;
- what `skeg_supported` means in HullQ taxonomy;
- displacement basis;
- SA/D and D/L methodology;
- unknown vs confirmed non-match semantics;
- how provenance/conflicts are handled;
- model vs generation vs option identity.

These pages should use HullQ's own data/examples where useful rather than becoming generic SEO articles.

### Tier E — original data studies / linkable assets

As dataset breadth grows, HullQ can periodically publish original analyses such as:

- distribution of displacement by length and decade;
- keel/rudder trends by era;
- design/builder production timelines;
- technical completeness/coverage reports;
- model-family comparisons.

These are useful for organic links, community discussion and earned media because the underlying analysis cannot be reproduced by generic content writers without the HullQ dataset.

## 5. Indexability promotion gate

No programmatic page should become indexable merely because it can be generated.

OQ-018 must convert the following into exact machine-testable rules. Strategically, an indexable page should satisfy all applicable conditions:

1. **Stable intent** — the page represents a durable user information need, not transient UI state.
2. **Stable identity/query definition** — it has a deterministic canonical meaning.
3. **Distinct utility** — it provides meaningfully different data/results/context from neighboring pages.
4. **Sufficient evidence/data** — the page is not mostly empty, unknown or boilerplate.
5. **No near-duplicate intent** — an existing canonical page does not already satisfy effectively the same need.
6. **Useful internal position** — the page can be reached naturally from the domain/search graph.
7. **Truthful metadata** — title/description/structured data can be generated from actual page content.
8. **Performance eligibility** — the page can meet the public release performance budget.
9. **Lifecycle support** — HullQ knows how the page redirects, retires or changes when underlying identity/query semantics change.
10. **Search policy compliance** — the page is useful if a user reaches it directly, not merely a doorway into the actual product.

Exact numeric thresholds, such as minimum confirmed results or completeness, are deliberately left to OQ-018 because different page classes may require different thresholds.

## 6. URL and canonical doctrine

Exact URL grammar remains an OQ-018 decision, but the strategy requires:

- one preferred public URL per indexable page identity;
- human-readable slugs that are presentation identifiers, not primary database identity;
- deterministic slug collision handling;
- self-canonicalization for canonical pages;
- one canonical order for comparison identities;
- normalized query semantics for intentional technical pages;
- no URL variants caused only by filter order, sort order, tracking parameters or UI presentation;
- permanent redirects for legitimate canonical URL migrations;
- appropriate 404/410 behavior for removed identities with no successor;
- redirects, canonical tags and sitemap membership derived from the same page registry.

HullQ should avoid changing mature public URLs for cosmetic reasons.

## 7. Faceted-navigation doctrine

HullQ's interactive filter system may eventually combine dimensions such as:

- LOA/LWL/beam;
- draft/displacement;
- keel/rudder/skeg;
- material;
- rig;
- builder/brand;
- year range;
- derived ratios;
- configuration-sensitive fields.

This creates an enormous combinatorial URL space.

Therefore:

> **Search-state serialization and SEO-page identity are separate concepts.**

Users may share/save an arbitrary search without that search becoming crawl/index inventory.

OQ-018 must choose exact behavior for:

- filter query parameters;
- sort parameters;
- pagination;
- tracking parameters;
- search states with zero results;
- search states dominated by unknown data;
- canonical links;
- `robots.txt` and/or `noindex` where applicable;
- which filter links are emitted as crawlable anchors;
- promoted technical landing pages.

No implementation team should improvise this later inside frontend components.

## 8. Data is the content moat

HullQ should not compete primarily by writing more prose than established sailing sites.

The defensible content layer is:

```text
canonical identities
+ technical fields
+ explicit unknown/conflict semantics
+ configurations/variants
+ provenance
+ derived metrics
+ comparisons
+ searchable relationships
+ aggregate dataset insights
```

Programmatically generated prose should be used only where it improves comprehension. It must never hide weak data or create factual claims not present in the canonical/evidence system.

A page with excellent structured data and no filler is preferable to a page padded with generic AI paragraphs.

## 9. Metadata generation

Because HullQ will be database-driven, titles and descriptions should be generated deterministically from real page-specific data.

Examples of patterns, not final copy:

```text
Hallberg-Rassy 352 — Specs, Dimensions & Technical Data | HullQ
Najad 34 vs Hallberg-Rassy 352 — Technical Comparison | HullQ
Sailboats with Skeg-Supported Rudders — HullQ Technical Search
```

Rules:

- every indexable page must have a meaningful page-specific `<title>`;
- visible H1 and title should agree on page identity;
- avoid keyword repetition and long boilerplate;
- meta descriptions may be programmatically generated from page-specific facts;
- metadata must preserve unknowns and never invent specifications;
- metadata templates should be tested for duplicates at representative dataset scale;
- changes to titles/descriptions should be measured by page class rather than churned continuously without evidence.

## 10. Internal linking as a product graph

Every important indexable page should be naturally discoverable from at least one other crawlable public page.

Internal links should emerge from canonical relationships and useful user paths, such as:

```text
BoatModel
 ├─ BoatDesign/generations
 ├─ Brand
 ├─ builder/manufacturer
 ├─ technical characteristics
 ├─ comparable models
 ├─ methodology for displayed metrics
 └─ interactive HullQ search

Technical discovery page
 ├─ matching models
 ├─ related/adjacent technical pages
 ├─ field definitions
 └─ refine in search
```

Use normal `<a href>` links with meaningful anchor text for important navigational relationships. Do not make the crawlable graph dependent on JavaScript click handlers.

Avoid artificial sitewide keyword link blocks whose only purpose is ranking manipulation.

## 11. Sitemap and freshness architecture

Sitemaps should be generated only from the canonical page registry and contain only URLs HullQ intends search engines to consider for indexing.

Prefer a sitemap index segmented by page class so Search Console/Bing Webmaster Tools can expose indexation problems separately.

Conceptual structure:

```text
/sitemap-index.xml
    /sitemaps/boat-models-*.xml
    /sitemaps/boat-designs-*.xml
    /sitemaps/brands.xml
    /sitemaps/builders.xml
    /sitemaps/technical-discovery-*.xml
    /sitemaps/comparisons-*.xml
    /sitemaps/methodology.xml
```

Only create a class when that public page class actually exists.

Rules:

- canonical URLs only;
- accurate `lastmod` only when meaningful page content changed;
- removed/redirected URLs leave active sitemaps promptly;
- shard below protocol limits;
- sitemap generation is deterministic and testable;
- sitemap page-class segmentation doubles as an observability mechanism.

Bing/participating-engine freshness may later be supplemented with IndexNow for material URL additions/updates/deletions. IndexNow does not replace sitemaps and is not a Google indexing mechanism.

## 12. Structured-data doctrine

Structured data exists to describe truthful visible page content, not to manufacture search features.

Likely safe candidates to evaluate at OQ-018 include:

- `Organization` for HullQ itself;
- `BreadcrumbList` for genuine navigation hierarchy;
- `WebSite`/page identity where appropriate;
- schema.org representations for model/design entities only after semantic and search-feature review.

Schema.org currently includes `Vehicle` and `ProductModel`, but HullQ must not assume that a reference page about a sailboat model qualifies for Google's merchant/product rich results.

Never invent:

- `Offer` or current price when there is no qualifying offer;
- aggregate ratings;
- reviews;
- achieved sale prices;
- availability;
- manufacturer/brand relationships not supported by canonical data.

Structured-data output should be generated from the same canonical read model as visible content and covered by fixtures/release checks.

## 13. Rendering strategy

The accepted Astro + TypeScript architecture is a strong fit for this strategy.

Canonical/indexable public pages should deliver in initial/server/static HTML:

- page identity/H1;
- primary technical data/context;
- meaningful internal links;
- title/meta/canonical tags;
- applicable structured data;
- breadcrumbs/navigation.

React islands may enhance:

- filtering;
- comparison interactions;
- charts;
- unit switching;
- save/search/monitor controls;
- other stateful UX.

The site's organic surface must not degrade into a client-only shell waiting for JavaScript to reconstruct its primary meaning.

## 14. Performance doctrine

At launch, HullQ should target at least Google's current `good` Core Web Vitals thresholds at the 75th percentile where field data is available:

- LCP <= 2.5 s;
- INP < 200 ms;
- CLS < 0.1.

OQ-018 / frontend implementation should define stricter engineering budgets where practical for:

- HTML/document weight;
- JavaScript shipped by page class;
- image payload;
- font behavior;
- server response/cache behavior;
- interactive search response;
- comparison rendering.

Performance is simultaneously UX, hosting-cost and crawl-quality work, which is particularly important under HullQ's zero-budget constraint.

## 15. Search Console as a product-research loop

Google Search Console must be treated as product telemetry, not a dashboard checked only by marketing.

At minimum monitor by page class:

- impressions;
- clicks;
- CTR;
- query groups;
- landing pages;
- countries/devices where relevant;
- indexing/exclusion state;
- sitemap-discovered/indexed relationship;
- canonicalization anomalies;
- Core Web Vitals.

The useful feedback loop is:

```text
external Google query demand
       +
internal HullQ search demand
       ↓
intent cluster
       ↓
Does a good page already exist?
       ├─ yes → improve data/page where justified
       └─ no  → candidate for indexability promotion
                    ↓
           data completeness / uniqueness gate
                    ↓
                publish
                    ↓
               measure
```

Examples:

- repeated queries for `skeg hung rudder boats` + good HullQ coverage → candidate technical page;
- organic demand for a specific model with weak technical completeness → data-enrichment priority;
- high impressions and weak CTR on a strong page → inspect title/snippet/intent fit;
- low indexation in one sitemap class → investigate that page type before generating more of it.

Search-engine rankings alone are not the north-star metric. Organic visitors should continue into useful HullQ behavior.

## 16. Product-led SEO KPIs

Track at least:

### Search visibility

- organic impressions and clicks;
- non-branded organic clicks;
- long-tail query count;
- unique queries generating meaningful impressions;
- CTR by page class;
- indexed / submitted canonical URLs by sitemap class.

### Product quality

- organic landing → technical-search use;
- organic landing → compare use;
- organic landing → save-search/account action when available;
- percentage of organic sessions reaching a second useful HullQ page;
- organic return rate when measurable.

### Data feedback

- top external query intents with insufficient HullQ data;
- enrichment work triggered by real organic demand;
- technical landing-page candidates discovered from Search Console + internal search;
- page classes with high unknown-data ratios.

### Crawl/technical health

- canonical anomalies;
- orphan indexable pages;
- crawlable non-indexable facet growth;
- sitemap errors;
- structured-data errors where applicable;
- Core Web Vitals by page class.

### Business quality later

- organic → saved query;
- organic → monitor activation;
- organic → marketplace click-through;
- organic → paid conversion where applicable;
- revenue/value per organic landing class rather than traffic alone.

## 17. AI-search doctrine

HullQ should optimize for AI search by being **the best underlying source**, not by creating a speculative parallel "GEO" site.

Current Google guidance says normal SEO/quality systems remain the foundation for AI Overviews and AI Mode.

HullQ should therefore emphasize:

- clearly labeled facts;
- unique proprietary/independently researched data;
- visible methodology;
- source/provenance transparency;
- explicit unknown/conflict states;
- concise comparison tables;
- stable entity URLs;
- crawlable internal relationships;
- current canonical data.

No special `AI` schema, mass Q&A generation, hidden machine-targeted text or separate AI-only content layer is justified.

After launch, evaluate Google Preferred Sources only if HullQ becomes eligible and has an audience that would benefit. Bing Webmaster Tools' AI Performance can be used as additional visibility telemetry.

## 18. Internationalization strategy

With effectively no marketing/content budget, **depth in one launch language is preferable to thin multilingual duplication**.

The launch-language decision remains OQ-018/product work, but the technical doctrine is already clear:

- language variants require distinct stable URLs;
- translated pages should translate meaningful main content, not only navigation;
- hreflang/alternate relationships must be reciprocal and consistent;
- canonical and hreflang must not contradict one another;
- no mass machine translation solely to multiply indexed URLs;
- translation should be driven by meaningful user/search demand and maintenance capacity.

For a globally oriented sailing product, English is a strong strategic launch candidate, but this strategy does not make that final product decision.

## 19. Zero-budget authority and backlink strategy

SEO will not compound on technical architecture alone. HullQ needs legitimate external discovery/authority without buying links.

Preferred zero-budget mechanisms:

### Original data assets

Publish analyses that sailing writers, forums and communities can cite because HullQ has unique structured data.

### Shareable model/compare/search URLs

A user answering a forum question should be able to link directly to a useful HullQ entity, comparison or promoted technical page.

### Methodology transparency

Public methodology/provenance/correction pages make HullQ more credible to technically serious sailors and potential referring sites.

### Community participation

When genuinely relevant, answer questions in sailing communities with useful data and a HullQ link. Do not mass-post or seed links where they do not answer the question.

### Source/correction relationships

Make it easy for class associations, designers, yards, owners and researchers to report corrections or point HullQ to primary sources. This can create both better data and natural awareness.

### Earned-media hooks

Original dataset findings can be pitched to sailing publications/blogs without paid placement. The value proposition should be the finding/data, not "please link to HullQ".

Do not buy low-quality backlinks, run link exchanges at scale or create satellite sites.

## 20. Content/SEO anti-patterns HullQ should reject

Do not build:

- thousands of generic AI-written sailing articles;
- a page for every mechanically possible filter combination;
- doorway pages that merely redirect users to the real search tool;
- near-identical pages differing by one arbitrary range value;
- unsupported "best bluewater boat" or safety rankings;
- fabricated pros/cons generated from model memory;
- fake reviews/ratings;
- scraped third-party specifications republished as HullQ content without rights/provenance;
- SEO-only identities that diverge from HullQ's domain model;
- separate SEO databases/read models that silently disagree with canonical data;
- indexable empty/zero-value pages retained only to keep URL count high;
- client-only public pages whose primary content is absent from the initial/server-rendered page;
- automatic translation fleets created only for keyword coverage.

## 21. Practical release gates

Before public launch, OQ-018 and implementation slices should produce automated checks covering at least:

### Public-page registry

- every indexable page has exactly one canonical identity/URL;
- no duplicate canonical URL maps to different page identities;
- every sitemap URL belongs to the indexable registry;
- non-indexable interactive search states are excluded from sitemap inventory.

### Rendering

- indexable fixture pages return meaningful HTML without authenticated/session state;
- exactly one clear primary page heading;
- crawlable internal links use real `href` URLs;
- canonical/title/description are present and coherent.

### Canonical lifecycle

- slug rename preserves stable identity and produces accepted redirect behavior;
- retired page returns the approved redirect/404/410 behavior;
- tracking/sort/filter variants cannot become competing sitemap canonicals.

### Programmatic-page quality

- an indexability gate must pass before a technical landing/comparison page enters the sitemap;
- page-specific data is present;
- duplicate-intent/query definitions are rejected;
- pages dominated by unsupported/unknown content can fail promotion.

### Metadata

- no empty titles/descriptions for approved indexable pages;
- representative-scale duplicate-title/reporting gate;
- metadata never materializes unavailable facts.

### Structured data

- JSON-LD generated only for approved page types;
- schema validation in CI where feasible;
- values agree with visible canonical data;
- no fake price/rating/review fields.

### Sitemaps

- canonical URLs only;
- protocol size limits respected;
- deterministic output;
- removed/redirected URLs absent;
- `lastmod` semantics tested.

### Internationalization when introduced

- reciprocal hreflang relationships;
- language URL/canonical consistency;
- no template-only pseudo-localization.

### Performance

- representative public pages pass agreed lab budgets;
- production monitoring captures field Core Web Vitals after launch.

## 22. Phased execution

### Now — before public implementation

- retain this strategy as product doctrine;
- keep OQ-018 open;
- continue building canonical breadth/technical data;
- ensure identity/query decisions preserve future stable public-page semantics;
- do not build speculative frontend SEO routes during Stage 3.

### Before Stage 4/5 hardening

- ensure OQ-009 query semantics can support promoted technical pages, especially unknown/insufficient-data results;
- ensure API/read-model architecture can return page-relevant data without duplicating business rules in Astro.

### OQ-018 decision

Must freeze at minimum:

1. public page taxonomy;
2. canonical URL grammar and slug lifecycle;
3. public-page/indexability registry;
4. indexability promotion/demotion criteria by page class;
5. faceted URL crawl/index/link rules;
6. pagination rules;
7. comparison-page identity/order rules;
8. rendering requirements;
9. internal-link graph rules;
10. title/meta generation contracts;
11. structured-data mapping;
12. sitemap segmentation and `lastmod` semantics;
13. robots/noindex/canonical rules;
14. redirect/404/410 behavior;
15. launch-language and future hreflang architecture;
16. performance budgets;
17. Search Console/Bing Webmaster observability;
18. IndexNow decision;
19. SEO release-gate fixtures/tests;
20. anti-scaled-content safeguards.

### Stage 6 implementation

Implement the OQ-018 contract using Astro server/static HTML with selective React islands.

### Post-launch organic loop

- verify Search Console and Bing Webmaster properties;
- submit segmented sitemaps;
- monitor indexing by page class;
- collect Search Console/internal-search intent signals;
- promote only qualified new landing-page intents;
- enrich high-demand low-completeness entities/fields;
- test title/snippet improvements where evidence justifies it;
- publish periodic original data studies;
- review official search-engine guidance before major surface changes.

## 23. Relationship to monetization

The open-search / paid-persistence strategy and Product-Led SEO reinforce each other:

```text
organic technical query or model page
        ↓
free HullQ search / compare
        ↓
user discovers value
        ↓
Save this search / monitor / alerts
        ↓
permission-based returning relationship
        ↓
paid persistence/monitoring features where justified
```

SEO should therefore not be crippled by hiding the searchable knowledge surface behind an account or paywall. Monetization should focus on persistence, monitoring, advanced intelligence and convenience rather than blocking the organic acquisition engine.

## 24. Strategic rule of thumb

When considering any SEO idea, ask:

> **Would this page/tool still be useful if Google did not exist?**

If the answer is yes, it is likely compatible with HullQ's Product-Led SEO strategy.

If the only reason the page exists is to capture a keyword and funnel the user elsewhere, it should normally not be built or indexed.

## Research basis

Current detailed research and primary-source references are retained in:

`docs/research/OQ-018_PRODUCT_LED_SEO_RESEARCH_2026-08-25.md`

This strategy extends, but does not replace:

- ADR-0007 — Search Architecture and SEO Are First-Class Product Architecture;
- `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`;
- REQ-SEO-001 through REQ-SEO-007;
- OQ-018, which remains the mandatory detailed implementation gate.
