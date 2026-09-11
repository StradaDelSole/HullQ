# HullQ — OQ-018 Search Canonical Identity Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

For HullQ public Search, one semantic Search meaning MUST have one deterministic canonical URL representation within a locale.

Semantically equivalent URL spellings MUST NOT become distinct Search identities merely because parameter order, numeric formatting, omitted defaults, or another syntactic form differs.

Illustrative non-canonical equivalents:

```text
/de/search?loa_min=10&draft_max=1.60
/de/search?draft_max=1.60&loa_min=10
/de/search?draft_max=1.600&loa_min=10.0
```

Once the bounded canonicalization rules are defined, all such forms that mean the same accepted Search query must resolve to one canonical representation, for example:

```text
/de/search?draft_max=1.6&loa_min=10
```

The exact ordering and numeric formatting shown above are illustrative only and are not frozen by this record.

## Identity rule

```text
same locale + same accepted Search semantics
→ same canonical Search URL identity
```

Different locales remain distinct localized URL representations of the same language-neutral Search state, as already accepted:

```text
/de/search?<state>
/en/search?<same-state>
```

The locale changes presentation language, not technical Search meaning.

## Product and platform consequences

The canonical Search identity is intended to provide one stable representation for:

- buyer bookmarks and sharing;
- browser reload/back-forward behavior;
- future Saved Search identity;
- analytics deduplication;
- cache identity;
- support/debugging;
- future SEO/canonical handling.

A `rel=canonical` declaration alone is not sufficient as the product identity model if HullQ itself continues treating equivalent Search spellings as separate searches.

## Relationship to existing Search contracts

This decision extends:

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`.

The existing versioned HullQ Search query contract remains authoritative for semantics. Canonical URL identity is derived from accepted Search meaning, not from raw incoming query-string bytes.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- exact canonical parameter ordering;
- numeric serialization/normalization;
- default and empty-value omission;
- duplicate parameter handling;
- repeated-value handling for future multi-value criteria;
- invalid and unknown parameter behavior;
- redirect vs canonical-link response behavior for non-canonical but semantically valid forms;
- locale-specific base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- exact robots/canonical/hreflang mechanics.

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
- semantic, language-neutral public query parameters;
- the existing versioned Search query as authoritative semantic model;
- parameterized Search-result URLs initially non-indexable;
- purpose-built SEO landing pages as a separate deliberate future capability;
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
- one-canonical-URL-per-semantic-Search identity accepted by this record

GENUINELY_OPEN within OQ-018 before SLICE-0051 readiness
- concrete canonicalization mechanics: ordering, numeric normalization, defaults, duplicates, invalid/unknown handling
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

> **HullQ treats semantically identical Search state within a locale as one Search identity with one deterministic canonical URL representation; syntactic differences must not create duplicate Searches.**
