# HullQ — OQ-018 Valid-but-Non-Canonical Search Redirect Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

A public Search request that is semantically valid and can be normalized deterministically to the already accepted single canonical Search URL MUST NOT remain a second `200 OK` Search identity.

HullQ MUST instead issue a server-side permanent redirect to the exact canonical URL using:

```text
HTTP 308 Permanent Redirect
Location: <exact canonical Search URL>
```

Example:

```text
GET /de/search?draft_max=1.60
```

where `1.60` is accepted as semantically valid but normalizes exactly to the canonical decimal representation `1.6`, becomes:

```text
308 Permanent Redirect
Location: /de/search?draft_max=1.6
```

The canonical target is then the sole public Search URL identity that serves the Search response for that semantic state.

## Critical distinction from invalid requests

This decision preserves the accepted invalid-request policy:

```text
valid + non-canonical
-> deterministic normalization
-> 308 redirect to canonical URL
```

is distinct from:

```text
invalid / ambiguous
-> HTTP 400
-> no Search result evaluation
-> localized recovery UX
```

HullQ MUST NOT use a redirect to guess, delete, reinterpret, or resolve an ambiguous buyer requirement.

Examples such as conflicting single-value duplicates remain invalid:

```text
/de/search?draft_max=1.6&draft_max=1.8
```

and therefore remain HTTP 400 rather than redirect candidates.

## Why 308

`308 Permanent Redirect` is selected because the normalization is a stable identity rule rather than a temporary navigation convenience.

It also preserves request-method semantics rather than implying that a method change is acceptable.

For the initial public Search surface the expected request method is GET, but the redirect rule remains explicit and standards-aligned.

## Canonical-identity consequence

This decision operationalizes the already accepted rule:

```text
same Search semantics
-> one canonical URL identity
```

Therefore HullQ MUST NOT rely only on a `<link rel="canonical">` while continuing to serve arbitrary semantically equivalent Search URLs as independent successful `200 OK` surfaces.

The normal HullQ UI SHOULD generate canonical URLs directly, so the redirect path primarily protects:

- manually edited URLs;
- old or externally generated links;
- semantically equivalent lexical forms;
- parameter-order variations that are valid but non-canonical;
- harmless duplicate single-value parameters that normalize to one semantic value.

## Non-semantic parameter caveat

This decision does **not** yet define the exact allowlist or lifecycle of non-semantic attribution/marketing parameters.

A later bounded OQ-018 decision must ensure that allowed attribution parameters remain non-semantic and do not create Search identity, while avoiding accidental loss of attribution before its intended handling is complete.

This decision therefore fixes the Search-identity behavior without prematurely selecting the exact tracking-parameter implementation.

## Relationship to prior accepted OQ-018 decisions

This decision extends and preserves:

- deterministic public Search state in query parameters;
- locale-prefixed Search routes;
- stable language-neutral semantic parameter names;
- one canonical URL per semantic Search state;
- lexicographic canonical parameter ordering;
- exact Decimal canonicalization with no semantic rounding or float loss;
- sparse canonical Search URLs;
- explicit search-vs-non-semantic parameter classes;
- duplicate single-value normalization only when duplicates are semantically equal;
- HTTP 400 + recovery UX for invalid or ambiguous Search requests.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- exact accepted non-canonical numeric lexical input envelope;
- exact non-semantic parameter allowlist contents and attribution handling;
- future multi-value parameter semantics if needed;
- base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- exact robots/canonical/hreflang mechanics;
- the exact smallest buyer requirement/field/query vertical for SLICE-0051.

Broad all-field URL catalogs, broad multi-value facets, arbitrary faceted-navigation indexation, broad SEO landing-page taxonomies, Saved Search, monitoring and alerts remain deferred unless separately selected.

## Decision / implementation reconciliation

**Accepted records checked:**

- `docs/SLICE_0051_CAPABILITY_SELECTION_2026-09-11.md`;
- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NUMERIC_CANONICALIZATION_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_SPARSE_CANONICAL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_UNKNOWN_PARAMETER_POLICY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_DUPLICATE_SINGLE_VALUE_POLICY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_INVALID_REQUEST_RECOVERY_DECISION_2026-09-11.md`.

**Production implementation checked:**

- no current public Search URL adapter owns canonical redirect behavior;
- the accepted Search kernel remains authoritative for semantic evaluation;
- the first buyer-facing public Search surface is still unimplemented.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- versioned fail-closed Search query contracts;
- all prior bounded OQ-018 decisions listed above.

**Exact remaining gap:**

- a valid but non-canonical public Search URL needs one deterministic protocol outcome that enforces the accepted single canonical Search identity.

**Accepted-but-unimplemented obligation:**

- SLICE-0051 must issue a server-side `308 Permanent Redirect` from a valid-but-non-canonical Search URL to its exact canonical URL before serving the Search response.

**Material classifications:**

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- accepted public Search URL/canonicalization rules
- invalid Search request HTTP 400 + recovery policy
- valid-but-non-canonical 308 redirect policy accepted by this record

GENUINELY_OPEN
- exact non-semantic allowlist / attribution handling
- base Search-route indexability/canonical behavior
- bare `/search` and unsupported-locale behavior
- rendering boundary
- exact robots/canonical/hreflang mechanics
- exact smallest 0051 field/query vertical

EXPLICITLY_DEFERRED
- broad all-field URL parameter catalog
- broad multi-value facet semantics unless required by the selected 0051 vertical
- path-based facet taxonomies
- broad indexable SEO landing-page catalog
- arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## Execution ownership

SLICE-0051 owns implementation of this redirect rule for the bounded public Search URL contract it exposes.

## One-sentence rule

> **If a public Search request is semantically valid but is not the one accepted canonical representation of that Search state, HullQ returns HTTP 308 and redirects to the exact canonical Search URL; only that target serves the Search response.**
