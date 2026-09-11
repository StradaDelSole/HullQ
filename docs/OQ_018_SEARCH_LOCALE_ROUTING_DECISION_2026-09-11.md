# HullQ — OQ-018 Search Locale Routing Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

The Project Owner accepts locale-prefixed public Search routes for HullQ's mandatory public languages:

```text
/en/search
/de/search
/fr/search
/pt/search
/es/search
```

The locale prefix controls presentation language only. Search meaning remains language-neutral.

For equivalent buyer requirements, changing locale MUST preserve the same deterministic Search state and technical semantics. Example:

```text
/de/search?draft_max=1.60
/en/search?draft_max=1.60
```

must represent the same technical requirement, differing only in user-facing language.

The locale MUST NOT be encoded as a Search-state query parameter such as `?lang=de`, and the canonical public Search representation must not rely only on browser language, cookie state or opaque client/session state.

## Buyer behavior

A language switch on the Search surface must preserve the active technical Search state rather than silently resetting or reinterpreting the buyer's requirements.

This supports:

- stable language-specific URLs;
- bookmark/share/reload behavior;
- deterministic language switching;
- future `hreflang`/international SEO handling without mixing language selection into technical Search semantics;
- the accepted principle that exact hard constraints shown in the UI are exactly the constraints enforced by Search.

## Relationship to the accepted URL-state decision

This decision extends, and does not replace, `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`.

The combined accepted route pattern is now:

```text
/{locale}/search?<deterministic-language-neutral-search-state>
```

for `locale ∈ {en, de, fr, pt, es}`.

Parameterized Search-result URLs remain initially non-indexable as already accepted. This locale decision does not convert arbitrary query combinations into SEO landing pages.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- exact query-parameter names, grammar, ordering and repeated-value rules;
- canonicalization of equivalent parameter forms;
- default omission rules and invalid/unknown parameter behavior;
- indexability/canonical behavior of the locale-specific base Search routes such as `/en/search`;
- handling of bare `/search` and unsupported locale prefixes;
- redirect vs negotiation behavior for first arrival without a locale;
- rendering boundary for the first Search surface;
- exact robots/canonical/hreflang handling needed for parameterized non-indexable results.

This record also does not impose locale-prefixed routing on every existing HullQ public page class; broader site-wide international route migration remains separate unless already controlled by another accepted artifact.

## Preserved constraints

This decision preserves:

```text
hard MUST remains hard
UNKNOWN / UNRESOLVED / CONFLICT do not become matches
only CONFIRMED_MATCH is primary
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

It also preserves:

- one stable Search route class with deterministic URL query state;
- mandatory public languages EN, DE, FR, PT and ES;
- language-neutral canonical technical identifiers, values and Search semantics;
- public does not automatically mean indexable;
- purpose-built SEO landing pages as a later deliberate capability;
- Astro + FastAPI application boundaries;
- accepted buyer/broker/success/quality standards.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and query evaluation kernel
- existing bounded public NativeListing page class

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat → Search bridge selected for SLICE-0051
- deterministic URL Search state
- locale-prefixed Search routes accepted by this record

GENUINELY_OPEN within OQ-018 before SLICE-0051 readiness
- exact query-parameter grammar/canonicalization
- locale-specific base Search-route indexability/canonical behavior
- bare `/search` and unsupported-locale behavior
- rendering boundary
- robots/canonical/hreflang mechanics for parameterized non-indexable Search results

EXPLICITLY_DEFERRED
- path-based facet taxonomies
- broad indexable SEO landing-page catalog
- arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## One-sentence rule

> **HullQ's first public Search uses stable locale-prefixed routes `/en|de|fr|pt|es/search`; locale changes presentation language only and must preserve the same language-neutral deterministic Search state and truth semantics.**
