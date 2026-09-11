# HullQ — OQ-018 Duplicate Single-Value Search Parameter Policy Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

For a public Search parameter whose contract is explicitly **single-valued**, duplicate occurrences are handled by semantic equivalence, not by raw occurrence order.

```text
same single-value parameter repeated
+ values normalize to the same semantic value
-> accept as harmless redundancy
-> reduce to one semantic criterion
-> canonicalize to one parameter occurrence

same single-value parameter repeated
+ values normalize to different semantic values
-> INVALID
-> fail closed
-> never first-wins
-> never last-wins
```

Example:

```text
/de/search?draft_max=1.60&draft_max=1.6
```

normalizes to the same exact Decimal value and therefore represents one Search criterion:

```text
draft_max = 1.6
```

with canonical URL:

```text
/de/search?draft_max=1.6
```

By contrast:

```text
/de/search?draft_max=1.6&draft_max=1.8
```

is ambiguous and therefore invalid.

HullQ MUST NOT silently select the first or last conflicting occurrence.

## Boundary: single-value vs multi-value

This decision applies only to parameters whose public Search contract declares them single-valued.

Repeated occurrences MUST NOT silently create multi-select semantics.

Future genuinely multi-valued criteria require an explicit separately reviewed contract for:

- value-set semantics;
- duplicate handling within a set;
- ordering/canonicalization;
- empty-set behavior;
- mapping into the authoritative Search query model.

## Relationship to accepted OQ-018 decisions

This decision extends the accepted OQ-018 records for:

- locale-prefixed Search routes;
- semantic language-neutral query parameters;
- one canonical URL identity per semantic Search state;
- lexicographic canonical parameter ordering;
- exact Decimal canonicalization without semantic rounding or float loss;
- sparse canonical Search state;
- fail-closed unknown-parameter handling with an explicit non-semantic allowlist.

Semantic equivalence for duplicate numeric values MUST use the same exact normalization rules already accepted for canonical numeric Search values.

## Buyer-experience rationale

The rule intentionally combines tolerance and safety:

```text
harmless duplicate representation
-> normalize without punishing the buyer

conflicting duplicate requirement
-> do not guess buyer intent
-> fail closed
```

This preserves buyer trust while avoiding unnecessary errors for URLs that redundantly repeat the same requirement.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- repeated-value semantics for future multi-value parameters;
- exact invalid-response and recovery UX;
- exact non-semantic parameter allowlist contents;
- exact accepted non-canonical numeric lexical input envelope;
- redirect vs canonical-link mechanics for valid but non-canonical URLs;
- base Search-route indexability/canonical behavior;
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

It also preserves the accepted rule that unsupported or ambiguous public Search input is never silently reinterpreted into a different buyer requirement.

## Decision / implementation reconciliation

**Accepted records checked:**

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NUMERIC_CANONICALIZATION_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_SPARSE_CANONICAL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_UNKNOWN_PARAMETER_POLICY_DECISION_2026-09-11.md`;
- accepted Search query semantics and marketplace truth constraints controlling SLICE-0051.

**Production implementation checked:**

- existing versioned Search query contracts remain fail-closed;
- no existing public Search URL adapter defines duplicate single-value parameter behavior.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- fail-closed versioned Search query representation;
- previously accepted public Search URL and canonicalization decisions listed above.

**Exact remaining gap:**

- the public Search URL adapter needs deterministic duplicate handling for parameters declared single-valued.

**Accepted-but-unimplemented obligations:**

- SLICE-0051 must accept semantically equivalent duplicates for its bounded single-value Search parameters and canonicalize them to one occurrence;
- SLICE-0051 must reject semantically conflicting duplicates fail-closed;
- SLICE-0051 must not implement first-wins or last-wins semantics.

**Material classifications:**

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- accepted public Search URL state and canonicalization rules
- duplicate single-value parameter policy accepted by this record

GENUINELY_OPEN
- future multi-value repeated-parameter semantics
- exact invalid-response/recovery UX
- exact non-semantic allowlist contents
- exact non-canonical numeric lexical acceptance envelope
- canonical redirect mechanics
- base Search-route indexability/canonical behavior
- bare `/search` behavior
- rendering boundary
- robots/canonical/hreflang mechanics

EXPLICITLY_DEFERRED
- broad all-field URL parameter catalog
- broad multi-value facet semantics
- path-based facet taxonomies
- broad indexable SEO landing-page catalog
- arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## Execution ownership

SLICE-0051 owns implementation of this duplicate policy for the bounded single-value public Search parameters it exposes.

Future multi-valued parameters remain deferred until their semantics are explicitly defined.

## One-sentence rule

> **For single-valued HullQ Search parameters, semantically equivalent duplicates normalize to one value; semantically conflicting duplicates are invalid and fail closed, with neither first-wins nor last-wins behavior.**
