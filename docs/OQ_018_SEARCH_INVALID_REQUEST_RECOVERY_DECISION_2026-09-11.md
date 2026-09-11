# HullQ — OQ-018 Invalid Search Request Recovery Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

A public Search request that cannot be mapped unambiguously to one valid HullQ Search state after applying the already accepted normalization rules is **invalid**.

For such a request HullQ MUST:

```text
return HTTP 400
+ do not execute Search result evaluation
+ do not silently delete, reinterpret, or guess the problematic requirement
+ render a localized, buyer-friendly recovery surface
+ identify the problematic parameter/requirement clearly enough for correction
```

Examples include:

```text
/de/search?draft_max=1.6&draft_max=1.8
```

where a single-valued Search parameter has conflicting duplicate values, and:

```text
/de/search?draft_max=1.6&drafft_min=1.2
```

where a non-allowlisted unknown parameter is present.

HullQ MUST NOT execute a partial Search using only the subset it happened to understand.

## Recovery UX

HTTP 400 is a protocol outcome, not permission to expose a technical error page.

The buyer-facing response MUST remain an intentional HullQ Search experience and SHOULD:

- explain in the active locale that one or more Search requirements could not be understood unambiguously;
- identify the specific problematic field or conflict when safely possible;
- offer a direct path to correct or remove the invalid requirement;
- preserve all other unambiguous buyer-entered Search state where doing so does not alter Search semantics;
- avoid implementation jargon, stack traces, parser internals, or raw exception text.

Example buyer-facing explanation:

```text
Tiefgang ist zweimal mit unterschiedlichen Werten angegeben.
Bitte wähle einen Wert.
```

The response MUST NOT claim that matching results were evaluated when Search evaluation was not run.

## Critical distinction: invalid vs valid-but-non-canonical

This decision does **not** classify every non-canonical URL as invalid.

For example:

```text
/de/search?draft_max=1.60
```

may be semantically valid even though its canonical numeric representation is:

```text
/de/search?draft_max=1.6
```

A request is invalid only when accepted parsing/normalization cannot produce one unambiguous valid Search state without guessing or changing buyer intent.

Therefore:

```text
valid + non-canonical
!=
invalid / ambiguous
```

The redirect/canonical-link behavior for valid-but-non-canonical requests remains a separate OQ-018 decision.

## Relationship to accepted OQ-018 decisions

This decision extends the accepted rules that:

- Search state is represented in deterministic public query parameters;
- semantically identical Search states have one canonical URL identity;
- exact Decimal normalization must not round or lose meaning;
- canonical Search URLs are sparse;
- unknown Search parameters fail closed except for an explicit non-semantic allowlist;
- semantically equal duplicates of a single-valued parameter may normalize to one value;
- semantically conflicting duplicates of a single-valued parameter are invalid.

This record defines the buyer-facing protocol/recovery consequence of the invalid state; it does not weaken any of those decisions.

## Buyer-trust rationale

HullQ's product advantage depends on buyers being able to trust that technical requirements were actually applied.

The unsafe alternatives are therefore forbidden:

```text
invalid input
-> silently drop requirement
-> show results anyway
```

and:

```text
ambiguous input
-> choose first/last/arbitrary value
-> show results anyway
```

A clear recoverable 400 response is intentionally more customer-friendly than silently returning results for a Search the buyer did not actually specify.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- exact redirect vs canonical-link mechanics for valid-but-non-canonical Search URLs;
- exact accepted non-canonical numeric lexical input envelope;
- exact non-semantic parameter allowlist contents;
- future multi-value parameter semantics;
- exact visual design/copy of the recovery component beyond the requirements above;
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

Invalid public URL input is an input-contract failure and MUST NOT be converted into Search truth-state semantics such as UNKNOWN.

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
- `docs/OQ_018_SEARCH_DUPLICATE_SINGLE_VALUE_POLICY_DECISION_2026-09-11.md`;
- accepted Search query semantics and marketplace truth constraints controlling SLICE-0051.

**Production implementation checked:**

- existing versioned Search query contracts remain fail-closed;
- existing Search evaluation semantics separate query validity from TRUE/FALSE/UNKNOWN evaluation;
- no existing public Search URL adapter or buyer-facing Search recovery surface currently owns invalid-request behavior.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- fail-closed versioned Search query representation;
- previously accepted public Search URL and canonicalization decisions listed above.

**Exact remaining gap:**

- the first public Search surface needs a deterministic protocol and buyer recovery response when public URL input is invalid or ambiguous.

**Accepted-but-unimplemented obligations:**

- SLICE-0051 must return HTTP 400 for invalid/ambiguous public Search requests in its bounded URL contract;
- SLICE-0051 must not execute result evaluation for those requests;
- SLICE-0051 must provide localized buyer-friendly recovery guidance and must not silently delete, choose, or reinterpret the invalid requirement.

**Material classifications:**

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- accepted public Search URL state and canonicalization rules
- invalid Search request HTTP 400 + recovery policy accepted by this record

GENUINELY_OPEN
- valid-but-non-canonical redirect/canonical-link mechanics
- exact non-canonical numeric lexical acceptance envelope
- exact non-semantic allowlist contents
- future multi-value parameter semantics
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

SLICE-0051 owns implementation of this invalid-request protocol/recovery policy for the bounded public Search URL contract it exposes.

## One-sentence rule

> **If HullQ cannot map a public Search request to one valid, unambiguous Search state without guessing or changing buyer intent, it returns HTTP 400, runs no result evaluation, and gives the buyer a clear localized path to correct the request.**
