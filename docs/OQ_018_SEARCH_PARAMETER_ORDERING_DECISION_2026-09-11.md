# HullQ — OQ-018 Search Parameter Ordering Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

HullQ canonical public Search URLs MUST order technical query parameters lexicographically by their canonical language-neutral parameter name.

Example:

```text
/de/search?loa_min=10&draft_max=1.6
```

normalizes to:

```text
/de/search?draft_max=1.6&loa_min=10
```

The ordering rule applies to the technical canonical URL identity only.

## Buyer-experience boundary

Canonical URL ordering and UI presentation ordering are deliberately separate concerns:

```text
UI order = optimized for buyer comprehension and task flow
canonical URL order = lexicographic by canonical technical parameter name
```

The Search UI MUST remain free to group and order controls according to buyer usability, product clarity and conversion quality. URL canonicalization MUST NOT force the visible filter UI into alphabetical order.

## Why this rule

The lexicographic rule is accepted because it is:

- deterministic;
- simple to implement consistently in web and API adapters;
- independent of UI layout;
- independent of a separate manually maintained field-order registry;
- stable as new public Search parameters are added;
- straightforward to test;
- suitable for canonical URL identity, bookmarks, sharing, future Saved Search identity, analytics and cache deduplication.

## Relationship to accepted OQ-018 decisions

This decision extends:

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`.

The canonical URL identity remains derived from accepted Search semantics rather than raw query-string bytes.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- numeric serialization/normalization;
- default and empty-value omission;
- duplicate parameter handling;
- repeated-value behavior for future multi-value criteria;
- invalid and unknown parameter behavior;
- redirect vs canonical-link response behavior for semantically valid non-canonical forms;
- locale-specific base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- exact robots/canonical/hreflang mechanics.

This record also does not freeze the broad future all-field public parameter catalog.

## Preserved constraints

This decision preserves:

```text
hard MUST remains hard
UNKNOWN / UNRESOLVED / CONFLICT do not become matches
only CONFIRMED_MATCH is primary
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

It also preserves:

- locale-prefixed Search routes `/en|de|fr|pt|es/search`;
- deterministic Search state in URL query parameters;
- semantic language-neutral public parameter names;
- one canonical URL identity per semantic Search state within a locale;
- the existing versioned Search query as authoritative semantic model;
- parameterized Search-result URLs initially non-indexable;
- accepted buyer/broker/success/quality standards.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and query evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat → Search bridge selected for SLICE-0051
- deterministic public URL Search state
- locale-prefixed Search routes
- semantic language-neutral query-parameter facade
- one canonical URL identity per semantic Search
- lexicographic canonical parameter ordering accepted by this record

GENUINELY_OPEN within OQ-018 before SLICE-0051 readiness
- numeric normalization
- defaults / empty values
- duplicate / repeated / invalid / unknown parameter handling
- canonical redirect mechanics
- base Search-route indexability/canonical behavior
- bare `/search` behavior
- rendering boundary
- robots/canonical/hreflang mechanics

EXPLICITLY_DEFERRED
- broad all-field URL parameter catalog
- path-based facet taxonomies
- broad indexable SEO landing-page catalog
- arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## One-sentence rule

> **HullQ canonical Search URLs sort canonical technical query-parameter names lexicographically, while visible filter ordering remains independently optimized for buyer UX.**
