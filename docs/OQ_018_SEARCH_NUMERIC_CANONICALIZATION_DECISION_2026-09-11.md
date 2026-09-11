# HullQ — OQ-018 Search Numeric Canonicalization Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

HullQ canonical public Search URLs MUST represent numeric Search values with an exact decimal technical form that preserves the accepted semantic value without rounding and without routing canonicalization through binary floating-point.

Canonical numeric URL representation MUST use:

- `.` as the decimal separator in every locale;
- no thousands separators;
- ordinary decimal notation, not exponent/scientific notation;
- no unnecessary leading integer zeros;
- no unnecessary trailing fractional zeros;
- no trailing decimal point;
- no semantic rounding during canonicalization.

Examples:

```text
1.600  -> 1.6
01.60  -> 1.6
10.0   -> 10
10.000 -> 10
```

Therefore a canonical Search URL may contain:

```text
/de/search?draft_max=1.6
```

while the localized German UI may display the same semantic value as:

```text
Max. Tiefgang: 1,60 m
```

Localized presentation and canonical technical serialization are separate concerns.

## Exactness boundary

The public URL adapter MUST preserve numeric semantics exactly across parsing, normalization and serialization.

For SLICE-0051 production Native Inventory Search, the accepted boundary is:

```text
public URL decimal
-> exact decimal semantic value
-> Search requirement / production adapter
-> exact PhysicalBoat Decimal claim value
```

The implementation MUST NOT use an intermediate binary floating-point conversion if that conversion can alter the accepted decimal value or comparison semantics.

In particular, an implementation pattern equivalent to the following is not acceptable for the 0051 production bridge:

```text
URL text
-> float
-> reconstructed Decimal / comparison value
```

when an exact decimal path is available.

## Relationship to existing Search query code

The existing versioned Search query contracts in:

- `src/hullq/search/query.py`;
- `src/hullq/search/query_mixed.py`;

currently accept finite numeric values and construct numeric criteria through Python `float` conversion.

That existing implementation remains valid historical/accepted Search-kernel behavior for the capabilities that already use it. This record does not silently rewrite prior slice history and does not declare those accepted slices defective.

However, SLICE-0051 MUST NOT treat the existence of that float conversion as authority to weaken the now-accepted production decimal boundary for buyer-facing Native Inventory Search.

If the selected 0051 vertical cannot preserve exact decimal semantics while reusing the existing numeric query path unchanged, then 0051 owns the smallest required adaptation/refactor so that the public URL → Search requirement → PhysicalBoat comparison path is decimal-safe and deterministic.

No silent precision loss, rounding or float-mediated semantic drift is permitted.

## PhysicalBoat truth compatibility

This decision is aligned with `src/hullq/domain/physical_boat_claims.py`, where accepted PhysicalBoat length claims use `decimal.Decimal` and explicitly reject binary-floating-point representation at the domain boundary.

For buyer-critical numeric Search criteria over concrete native inventory, URL normalization MUST preserve that exact-value contract rather than weakening it at the Search facade.

## Buyer-experience boundary

The technical canonical representation MUST NOT dictate the visible localized format.

The UI MAY present values using locale-appropriate conventions, units and formatting, provided conversion back to the canonical Search state is exact and deterministic.

Examples:

```text
German UI: 1,60 m
English UI: 1.60 m
canonical URL: draft_max=1.6
```

The buyer should see familiar formatting; HullQ's internal/public URL identity should remain language-neutral, stable and unambiguous.

## Why this rule

The exact decimal rule is accepted because it:

- preserves buyer-entered technical requirements without hidden numeric drift;
- aligns public Search state with accepted PhysicalBoat Decimal truth;
- avoids locale-dependent numeric ambiguity in URLs;
- gives semantically equal values one deterministic canonical representation;
- improves Saved Search, cache, analytics and sharing identity later;
- makes boundary and regression testing straightforward;
- avoids presenting apparently precise yacht specifications while comparing altered binary approximations underneath;
- supports HullQ's accepted quality standard for buyer-facing technical Search.

## Relationship to accepted OQ-018 decisions

This decision extends:

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`.

The canonical URL identity remains derived from accepted Search semantics rather than raw query-string bytes.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- default and empty-value omission;
- duplicate parameter handling;
- repeated-value behavior for future multi-value criteria;
- invalid and unknown parameter behavior;
- exact accepted numeric lexical input envelope before normalization, beyond the canonical output rules above;
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
- lexicographic canonical parameter ordering;
- the existing versioned Search query as authoritative semantic model;
- parameterized Search-result URLs initially non-indexable;
- accepted buyer/broker/success/quality standards.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and query evaluation kernel
- versioned fail-closed Search query contracts
- Decimal-based PhysicalBoat buyer-critical length claim representation from SLICE-0050

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- deterministic public URL Search state
- locale-prefixed Search routes
- semantic language-neutral query-parameter facade
- one canonical URL identity per semantic Search
- lexicographic canonical parameter ordering
- exact decimal public numeric canonicalization accepted by this record
- decimal-safe 0051 production bridge where concrete PhysicalBoat numeric truth is evaluated

GENUINELY_OPEN within OQ-018 before SLICE-0051 readiness
- defaults / empty values
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

The first selected production buyer-facing Native Inventory Search slice is SLICE-0051. Therefore SLICE-0051 owns implementation of the smallest decimal-safe adapter/refactor required by this decision for its bounded numeric Search criteria.

This obligation MUST NOT be silently deferred merely because the pre-existing Search query serializer/deserializer uses `float` internally.

Broader numeric-contract modernization outside the bounded 0051 vertical may be deferred to a later explicitly owned slice if it is not required to satisfy the 0051 acceptance criteria.

## One-sentence rule

> **HullQ canonical Search URLs serialize numeric values as minimal exact decimals with no semantic rounding or binary-float loss, while localized UI formatting remains a separate presentation concern.**
