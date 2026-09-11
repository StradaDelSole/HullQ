# HullQ — OQ-018 Public Search URL-State Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

For the first buyer-facing HullQ Search surface, the accepted URL-state pattern is:

```text
one stable public Search route
+ deterministic Search state in URL query parameters
```

The working route class is `/search`; exact locale routing remains a separate OQ-018 decision because HullQ has mandatory public languages and this record does not silently choose a locale-prefix strategy.

The Search state MUST be represented in the URL rather than existing only in client/session memory, so a buyer can reliably:

- bookmark a Search;
- share a Search;
- reload without losing the applied requirements;
- use browser back/forward navigation without silently changing Search meaning;
- later bridge the same deterministic Search representation into Saved Search / monitoring without inventing a second query grammar.

## Initial indexability boundary

Parameterized Search-result URLs are **not indexable in the initial public Search vertical**.

This means the first Search surface must not turn arbitrary buyer facet combinations into SEO landing pages merely because they are URL-addressable.

Purpose-built indexable SEO landing pages remain a separate future capability and must be introduced deliberately under accepted OQ-018 rules rather than inferred from arbitrary Search query strings.

The base Search route's exact indexability/canonical behavior is not decided by this record and remains part of the bounded OQ-018 work before SLICE-0051 readiness.

## Explicitly rejected for the first Search surface

### Facet values encoded as route hierarchy

Not selected:

```text
/boats/draft-under-1-60/skeg-rudder/...
```

Reason: this would prematurely bind product Search to a large path taxonomy and create faceted-navigation/canonical/indexation debt before HullQ has evidence for which combinations deserve durable public landing pages.

### Client/session-only Search state

Not selected:

```text
/search
+ opaque client/session state only
```

Reason: it is materially worse for buyer usability, sharing, reload/back behavior, reproducibility and later Saved Search / alert continuity.

## Preserved constraints

This decision does not alter any accepted Search truth semantics:

```text
hard MUST remains hard
UNKNOWN / UNRESOLVED / CONFLICT do not become matches
only CONFIRMED_MATCH is primary
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

It also preserves:

- Astro as the public web framework with React only where justified;
- FastAPI as the sole application/domain API boundary;
- stable internal IDs as canonical domain identity;
- public does not automatically mean indexable;
- mandatory public languages EN, DE, FR, PT and ES;
- `docs/PRODUCT_UX_PRINCIPLES.md` requirement that the user can see and edit what HullQ actually applied;
- `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md` buyer/broker/success/quality standard.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and query evaluation kernel
- existing bounded public NativeListing page class

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat → Search bridge selected for SLICE-0051
- this accepted URL-state behavior

GENUINELY_OPEN within OQ-018 before SLICE-0051 readiness
- exact locale/language routing shape for Search
- exact canonicalization rules for equivalent query-parameter forms
- exact query-parameter grammar/names/order/default omission
- base `/search` indexability and canonical target
- rendering boundary needed for the first public Search surface
- robots/canonical handling required to guarantee parameterized result URLs remain non-indexable

EXPLICITLY DEFERRED
- path-based facet taxonomies
- broad indexable SEO landing-page catalog
- arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## One-sentence rule

> **HullQ's first buyer-facing Search uses one stable public Search route with deterministic URL query parameters so Searches are shareable and reproducible; parameterized Search-result URLs are initially non-indexable, while purpose-built SEO landing pages remain a separate deliberate future capability.**
