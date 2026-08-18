# HullQ — Search & SEO Architecture

**Status:** ACCEPTED ARCHITECTURAL BASELINE  
**Decision:** ADR-0007  
**Detailed public-surface implementation gate:** OQ-018

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
