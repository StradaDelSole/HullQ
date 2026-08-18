# ADR-0007 — Search Architecture and SEO Are First-Class Product Architecture

**Status:** ACCEPTED  
**Date:** 2026-08-18

## Context

HullQ's product value depends on technical discovery across a broad, mostly evergreen sailboat-design universe. Organic discovery is a plausible compounding distribution channel, but the same multidimensional filtering that creates product value can also generate unstable/duplicate/unbounded URL spaces if SEO is treated as a later optimization.

Retrofitting canonical URLs, crawl behavior, rendering, internal links and indexable page taxonomy after frontend implementation would create avoidable migration risk and could force product/search compromises.

## Decision

Search Architecture and SEO are part of HullQ product architecture from the beginning.

The project MUST design interactive search and public organic discovery together while keeping their semantics distinct:

- arbitrary user filter states remain a product capability;
- only intentional, canonical, useful public surfaces become indexable;
- URL/canonical/rendering/linking/sitemap/performance consequences are considered before public frontend implementation;
- exact public-surface mechanics are gated by OQ-018 and current primary search-engine guidance.

`architecture/SEARCH_AND_SEO_ARCHITECTURE.md` is the accepted architectural baseline.

## Consequences

### Positive

- distribution requirements influence architecture before routing/data contracts harden;
- faceted search can remain powerful without creating an uncontrolled crawl space;
- canonical entity pages, internal linking and sitemap generation can share domain identity;
- future programmatic/technical landing pages are deliberate product surfaces rather than mass-generated SEO artifacts;
- frontend technology must demonstrate reliable crawlability and performance, not only interactive UX.

### Negative

- frontend/routing decisions require an additional architectural review dimension;
- not every useful interactive query can be an indexable page;
- URL/indexation migrations become versioned product concerns.

## Rejected alternative

Treat SEO as a post-launch marketing/optimization project after the application architecture and routing are fixed.

Rejected because it risks expensive URL/rendering migrations and fails to account for HullQ's combinatorial faceted-search surface.
