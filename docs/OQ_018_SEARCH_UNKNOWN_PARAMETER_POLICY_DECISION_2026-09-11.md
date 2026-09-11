# HullQ — OQ-018 Search Unknown Parameter Policy Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

HullQ public Search URLs MUST distinguish between:

1. explicitly supported Search-semantic parameters;
2. explicitly allowlisted non-semantic parameters such as approved attribution/marketing parameters;
3. every other parameter.

The policy is:

```text
known Search parameter
-> participates in Search semantics

explicitly allowlisted non-semantic parameter
-> does not participate in Search semantics
-> does not participate in canonical Search identity

anything else
-> invalid
-> never silently ignored as if it were irrelevant
```

An unknown parameter that is not explicitly allowlisted MUST fail closed rather than being silently dropped from Search semantics.

## Why this matters for buyer trust

HullQ's buyer-facing differentiation depends on technical requirements being evaluated exactly as represented.

For example:

```text
/de/search?draft_max=1.6&drafft_min=1.2
```

MUST NOT be interpreted as if the buyer had supplied only:

```text
/de/search?draft_max=1.6
```

by silently ignoring the misspelled `drafft_min` key.

A buyer could reasonably believe that both constraints were applied. Returning results while silently discarding one apparent technical requirement would undermine HullQ's accepted truth, quality and buyer-experience standards.

## Explicitly allowlisted non-semantic parameters

HullQ MAY support a small explicit allowlist of non-semantic parameters needed for attribution, marketing, campaign measurement, affiliate or equivalent operational purposes.

For example, if an approved parameter such as `utm_source` is allowlisted:

```text
/de/search?draft_max=1.6&utm_source=newsletter
```

has the same Search semantics and canonical Search identity as:

```text
/de/search?draft_max=1.6
```

The canonical Search URL therefore excludes the non-semantic parameter:

```text
/de/search?draft_max=1.6
```

Allowlisting a non-semantic parameter MUST NOT:

- alter Search requirements;
- alter Search result classification;
- alter canonical Search identity;
- turn tracking state into buyer requirement state;
- create a second Search-semantic parser;
- permit arbitrary unknown parameters to be ignored.

The allowlist itself MUST be explicit and bounded. Pattern-based permissiveness that effectively makes arbitrary unknown keys acceptable is not sufficient unless separately reviewed and accepted.

## Relationship to the authoritative Search model

The existing versioned HullQ Search query remains the authoritative semantic model.

The public URL facade therefore follows:

```text
public URL
-> validate parameter class
-> extract supported Search-semantic state
-> normalize to canonical Search state
-> map into the existing authoritative Search query contract
```

Non-semantic parameters remain outside that semantic model.

This preserves the existing fail-closed character of HullQ Search rather than weakening it at the public URL boundary.

## Canonical identity boundary

Canonical Search identity is based only on normalized semantic Search state within the accepted locale route.

Therefore:

```text
/de/search?draft_max=1.6&utm_source=newsletter
/de/search?draft_max=1.6&utm_source=partner
/de/search?draft_max=1.6
```

all share the same canonical Search identity if the attribution parameters are explicitly allowlisted as non-semantic.

By contrast:

```text
/de/search?draft_max=1.6&unknown_filter=foo
```

is not simply another spelling of that Search state. It is invalid unless `unknown_filter` later becomes an explicitly supported semantic or non-semantic parameter through the accepted parameter contract.

## Buyer- and broker-experience boundary

This rule protects buyer trust without unnecessarily blocking legitimate campaign, attribution or affiliate workflows that can matter for broker acquisition and marketplace growth.

The governing principle is:

```text
be strict about Search meaning
be explicit about approved non-Search metadata
never confuse the two
```

The visible UX for invalid parameters SHOULD be clear and actionable, but the exact HTTP/status-page/redirect behavior is not decided by this record.

## Relationship to accepted OQ-018 decisions

This decision extends:

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NUMERIC_CANONICALIZATION_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_SPARSE_CANONICAL_STATE_DECISION_2026-09-11.md`.

It preserves one deterministic canonical URL identity per semantic Search state within a locale.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- exact duplicate-parameter handling;
- repeated-value behavior for future multi-value criteria;
- exact invalid-parameter response behavior, including HTTP status and user-facing recovery UX;
- exact allowlisted attribution/marketing parameter catalog;
- exact accepted non-canonical numeric lexical input envelope;
- redirect vs canonical-link behavior for semantically valid but non-canonical forms;
- locale-specific base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- exact robots/canonical/hreflang mechanics.

This record does not freeze the broad future all-field public Search parameter catalog.

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
- semantic language-neutral public Search parameter names;
- one canonical URL identity per semantic Search;
- lexicographic canonical parameter ordering;
- exact decimal canonical numeric values with no semantic rounding or float loss;
- sparse canonical Search state containing only active buyer constraints;
- the existing versioned Search query as authoritative semantic model;
- parameterized Search-result URLs initially non-indexable;
- accepted buyer/broker/success/quality standards.

## Decision / implementation reconciliation

**Accepted records checked:**

- accepted OQ-018 partial decision records listed above;
- accepted Search query semantics;
- accepted marketplace truth and fail-closed Search constraints controlling SLICE-0051.

**Production implementation checked:**

- existing versioned Search query parsers and evaluation kernel reject unsupported semantic query shapes rather than silently treating unknown Search fields as valid;
- no existing public Search URL adapter currently defines a separate unknown/non-semantic parameter policy.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- fail-closed versioned Search query representation;
- accepted locale route class, semantic parameter facade, canonical identity, lexicographic ordering, decimal canonicalization and sparse canonical state.

**Exact remaining gap:**

- the first public Search URL adapter must classify inbound parameters against an explicit semantic/non-semantic contract and must not silently ignore unrecognized non-allowlisted keys.

**Accepted-but-unimplemented obligations:**

- SLICE-0051 must implement the bounded parameter-class validation needed by its first buyer-facing Search vertical;
- any non-semantic parameter support introduced by 0051 must be explicitly allowlisted and excluded from Search semantics/canonical identity.

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
- sparse canonical Search state
- fail-closed unknown-parameter policy with explicit non-semantic allowlist accepted by this record

GENUINELY_OPEN
- duplicate / repeated-value handling
- exact invalid-parameter response/recovery behavior
- exact non-semantic allowlist contents
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

SLICE-0051 owns implementation of the smallest parameter-validation layer required for its bounded first buyer-facing Search vertical.

Broader marketing/affiliate parameter catalogs MAY remain deferred until needed, but unsupported unknown parameters MUST NOT be silently accepted merely because a future expansion is anticipated.

## One-sentence rule

> **HullQ public Search accepts explicit Search-semantic parameters and explicitly allowlisted non-semantic metadata; every other parameter is invalid and must never be silently ignored as though it could not affect buyer intent.**
