# HullQ — OQ-018 Non-Semantic Search Parameter Allowlist Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

For the initial SLICE-0051 public Search URL contract, the allowlist of non-semantic query parameters is intentionally empty.

```text
allowed non-semantic Search URL parameters in SLICE-0051
= none
```

Therefore the initial public Search URL accepts only parameters that are part of the explicitly supported Search semantics for the bounded SLICE-0051 vertical.

Example valid Search URL:

```text
/de/search?draft_max=1.6
```

Example not accepted in the initial contract:

```text
/de/search?draft_max=1.6&utm_source=newsletter
```

Because `utm_source` is not in the initial non-semantic allowlist, it is handled by the already accepted unknown-parameter policy rather than silently ignored.

## Rationale

HullQ has not yet accepted or implemented a dedicated attribution, analytics, consent/privacy, click-ID, or campaign-parameter lifecycle contract.

Allowing marketing parameters before that contract exists would create unresolved behavior around:

- when attribution is captured;
- whether attribution survives the accepted 308 canonicalization redirect;
- whether and where attribution is persisted;
- consent/privacy handling;
- interaction with future analytics infrastructure;
- whether third-party click identifiers are accepted, retained, or discarded.

The first public Search surface therefore stays intentionally small and deterministic instead of introducing tracking behavior without a governing contract.

## Future extension remains allowed

This decision does **not** prohibit future support for non-semantic attribution parameters.

A later explicit decision may allow parameters such as selected `utm_*` fields or other campaign identifiers once HullQ has an accepted attribution/privacy lifecycle.

Any such future parameter MUST remain outside Search semantics and MUST NOT create a different Search identity.

```text
Search semantics
!=
attribution / marketing metadata
```

The later contract must also define how attribution is handled before any canonical redirect removes non-semantic URL state.

## Relationship to accepted OQ-018 decisions

This decision preserves:

- deterministic public Search state in query parameters;
- locale-prefixed Search routes;
- stable language-neutral semantic parameter names;
- one canonical URL per semantic Search state;
- lexicographic canonical parameter ordering;
- exact Decimal canonicalization without semantic rounding or float loss;
- sparse canonical Search URLs;
- unknown Search parameters fail closed except for explicitly allowlisted non-semantic parameters;
- equal single-value duplicates may normalize, conflicting duplicates are invalid;
- invalid/ambiguous requests return HTTP 400 with no Search evaluation;
- valid-but-non-canonical requests return HTTP 308 to the exact canonical Search URL.

With this record, the exception set for non-semantic parameters in SLICE-0051 is explicitly empty.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- exact robots/canonical/hreflang mechanics as readiness detail derived from the accepted public-search architecture;
- the exact smallest buyer requirement/field/query vertical for SLICE-0051.

The exact non-canonical numeric lexical acceptance envelope can be derived as an implementation/readiness detail from the already accepted exact Decimal semantics and does not require a separate owner decision unless reconciliation exposes a material ambiguity.

Future multi-value parameter semantics remain deferred unless the selected SLICE-0051 vertical actually requires them.

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
- `docs/OQ_018_SEARCH_INVALID_REQUEST_RECOVERY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md`.

**Production implementation checked:**

- no current public Search URL adapter exists;
- no accepted production attribution/UTM/click-ID lifecycle currently exists;
- no current public Search implementation depends on non-semantic URL parameters.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- versioned fail-closed Search query contracts;
- previously accepted bounded OQ-018 decisions listed above.

**Exact remaining gap:**

- the first public Search URL contract needed an explicit initial answer for the non-semantic parameter exception set.

**Accepted-but-unimplemented obligation:**

- SLICE-0051 must expose no non-semantic public Search query parameters unless a later accepted record explicitly expands this allowlist.

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
- valid-but-non-canonical HTTP 308 redirect policy
- empty initial non-semantic parameter allowlist accepted by this record

GENUINELY_OPEN
- base Search-route indexability/canonical behavior
- bare `/search` and unsupported-locale behavior
- rendering boundary
- exact smallest 0051 field/query vertical

EXPLICITLY_DEFERRED
- attribution/marketing parameter support until an explicit attribution/privacy contract exists
- future multi-value parameter semantics unless required by the selected 0051 vertical
- broad all-field URL parameter catalog
- path-based facet taxonomies
- broad indexable SEO landing-page catalog
- arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## Execution ownership

SLICE-0051 owns implementation of the empty initial non-semantic allowlist in its bounded public Search URL contract.

A future attribution/analytics slice or accepted OQ amendment may expand the allowlist without changing Search semantics or canonical Search identity.

## One-sentence rule

> **SLICE-0051 accepts no non-semantic public Search query parameters; attribution and marketing parameters remain unsupported until HullQ adopts an explicit attribution/privacy lifecycle, while future controlled support remains allowed.**
