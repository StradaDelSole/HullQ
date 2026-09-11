# HullQ — OQ-018 Sparse Canonical Search State Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

HullQ canonical public Search URLs MUST contain only semantically active buyer Search constraints.

Unset, default, no-op and unconstrained UI states MUST be omitted from canonical Search URL state.

Examples of states that do not create canonical query parameters:

- a filter that the buyer has not set;
- an explicit UI choice such as `All`, `Any`, `No preference` or equivalent when it means “no Search constraint”;
- an empty filter control with no semantic criterion;
- a system/UI default that does not represent a buyer requirement.

Therefore:

```text
/de/search?draft_max=1.6
```

is preferred over forms such as:

```text
/de/search?draft_max=1.6&keel=all&loa_min=&loa_max=
```

and an unconstrained Search state canonicalizes to the locale-prefixed base Search route rather than a query string full of defaults.

## Semantic identity rule

Canonical identity is based on Search semantics, not on widget state or raw query-string bytes.

If these UI states all mean “no keel requirement”:

```text
Keel = unset
Keel = All
Keel = Any
```

then they MUST represent the same semantic Search state and MUST NOT create different canonical URLs.

The public Search facade therefore follows:

```text
canonical URL state = semantically active buyer constraints only
```

## Empty values and pseudo-values

An omitted criterion is the canonical representation of “no constraint”.

Canonical URLs MUST NOT use pseudo-values such as:

```text
field=
field=null
field=none
field=all
```

merely to encode absence of a Search constraint.

This decision does not yet determine how inbound non-canonical empty/default forms are handled at request time. Reject-vs-redirect behavior remains a separate OQ-018 decision.

## Buyer-experience boundary

The UI MAY show useful default labels, placeholders or unconstrained choices for buyer comprehension.

Those presentation choices MUST NOT pollute canonical Search identity.

Removing an active filter from the UI MUST remove its semantic criterion from canonical URL state.

The rule is intended to keep Search URLs:

- shorter;
- easier to read and share;
- stable across UI redesigns;
- independent of presentation-only defaults;
- suitable for future Saved Search identity, cache keys and analytics deduplication.

## Relationship to accepted OQ-018 decisions

This decision extends:

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NUMERIC_CANONICALIZATION_DECISION_2026-09-11.md`.

It preserves the rule that one semantic Search state within a locale has one deterministic canonical URL representation.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- duplicate parameter handling;
- repeated-value behavior for future multi-value criteria;
- invalid and unknown parameter behavior;
- exact accepted non-canonical numeric lexical input envelope;
- redirect vs canonical-link response behavior for semantically valid but non-canonical forms;
- locale-specific base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- exact robots/canonical/hreflang mechanics.

This record does not freeze the broad future all-field public parameter catalog.

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
- lexicographic canonical parameter ordering;
- exact decimal canonical numeric values with no semantic rounding or float loss;
- the existing versioned Search query as authoritative semantic model;
- parameterized Search-result URLs initially non-indexable;
- accepted buyer/broker/success/quality standards.

## Decision / implementation reconciliation

**Accepted records checked:**

- accepted OQ-018 partial decision records listed above;
- accepted Search query semantics and marketplace truth constraints already controlling SLICE-0051.

**Production implementation checked:**

- existing Search query/evaluation kernel and versioned fail-closed query contracts;
- no existing public URL adapter currently fixes default/empty canonical Search behavior.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- versioned Search query representation;
- accepted locale route class, public semantic parameter facade, canonical Search identity, lexicographic parameter ordering and exact decimal canonicalization.

**Exact remaining gap:**

- the public Search URL adapter must omit inactive/default/no-op criteria when serializing canonical Search state.

**Accepted-but-unimplemented obligations:**

- SLICE-0051 must implement sparse canonical Search URL state for its bounded public Search surface.

**Material classifications:**

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- deterministic public URL Search state
- locale-prefixed Search routes
- semantic language-neutral query-parameter facade
- one canonical URL identity per semantic Search
- lexicographic canonical parameter ordering
- exact decimal public numeric canonicalization
- sparse canonical Search state accepted by this record

GENUINELY_OPEN
- duplicate / repeated / invalid / unknown parameter handling
- exact non-canonical numeric lexical acceptance envelope
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

## Execution ownership

SLICE-0051 owns implementation of sparse canonical Search URL state for the bounded first buyer-facing Search vertical.

Broader parameter catalogs and future multi-value semantics may remain deferred until separately selected and owned.

## One-sentence rule

> **HullQ canonical Search URLs contain only semantically active buyer constraints; unset, default, no-op and unconstrained UI states are omitted from canonical URL identity.**
