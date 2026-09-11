# HullQ — OQ-018 Bare Search and Unsupported-Locale Routing Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

The Project Owner accepts the following deterministic first-arrival routing rule for the public Search surface.

### Bare locale-less Search

A request to the locale-less Search entry point redirects permanently to the English locale route:

```text
/search
-> 308 /en/search
```

Any supported, valid Search state supplied on the locale-less route MUST be preserved through the redirect and canonicalized under the already accepted Search URL rules:

```text
/search?draft_max=1.6
-> 308 /en/search?draft_max=1.6
```

The fallback is deliberately deterministic. It MUST NOT vary according to browser `Accept-Language`, cookies, session state, inferred geography, account state, or other client-specific negotiation.

### Unsupported locale prefix

A Search request carrying a locale prefix outside HullQ's accepted public locale set `{en, de, fr, pt, es}` is not a locale-less request and MUST NOT be silently rewritten to English.

Examples:

```text
/it/search
/xx/search
/des/search
```

must return a real HTTP 404 response.

No Search evaluation is performed for an unsupported-locale route.

## Rationale

The accepted public Search identity uses explicit locale-prefixed routes:

```text
/en/search
/de/search
/fr/search
/pt/search
/es/search
```

A stable `/search` fallback is useful as a neutral first-arrival entry point, but using language negotiation for that fallback would make the same request resolve differently across clients and would complicate:

- canonical identity;
- cache behavior;
- reproducibility;
- support/debugging;
- analytics interpretation;
- international routing tests;
- future SEO behavior.

English is therefore the deterministic fallback locale for the locale-less Search entry point.

An unsupported locale prefix is materially different. It asserts a concrete route variant that HullQ does not support. Returning 404 makes broken links, spelling mistakes and unsupported locale assumptions visible rather than masking them through a fallback redirect.

## Buyer behavior

Normal HullQ navigation SHOULD link directly to the active locale route rather than relying on `/search` as the ordinary navigation target.

The bare `/search` route exists as a robust neutral entry point.

Once on a supported locale route, the already accepted language-switch behavior applies: changing language preserves the same language-neutral deterministic Search state.

## Relationship to accepted canonicalization rules

This routing decision does not replace the accepted Search canonicalization rules.

The processing boundary is:

```text
locale-less /search
-> deterministic locale routing to /en/search
-> accepted Search URL validation/canonicalization rules

supported locale route
-> accepted Search URL validation/canonicalization rules

unsupported locale route
-> 404
-> no Search evaluation
```

A locale-less Search request that contains an invalid or ambiguous Search state does not gain permission to become semantically valid through locale routing. Readiness/implementation MUST preserve the previously accepted fail-closed Search semantics and must define processing order consistently so locale routing cannot bypass invalid-request handling.

The exact low-level ordering of route recognition, query parsing and canonical redirect composition is an implementation/readiness detail so long as externally observable behavior preserves all accepted rules.

## SEO and indexability relationship

This decision preserves the accepted SLICE-0051 indexability boundary:

- all first locale-prefixed Search surfaces remain public/usable but `noindex`;
- `/search` is only a redirecting entry point and is not an independently indexable Search page;
- unsupported locale routes return real 404 responses rather than soft-fallback content;
- SEO remains a business-critical architecture requirement and future deliberate indexable locale-specific pages remain explicitly supported.

This behavior therefore avoids creating duplicate locale-less Search content while preserving deterministic canonical locale ownership.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- rendering boundary for the first Search surface;
- the exact smallest buyer requirement/field/query vertical for SLICE-0051.

The exact robots/canonical/hreflang mechanics and low-level routing implementation may be derived during readiness from the accepted decisions unless reconciliation exposes a material ambiguity.

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
- `docs/OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_INDEXABILITY_AND_SEO_READINESS_DECISION_2026-09-11.md`.

**Production implementation checked:**

- no current buyer-facing public Search route exists;
- no existing production route already defines `/search` first-arrival negotiation;
- no existing production Search route defines unsupported-locale behavior.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- versioned fail-closed Search query contracts;
- previously accepted locale-prefixed Search route set;
- previously accepted URL/canonicalization and noindex rules.

**Exact remaining gap:**

- bare `/search` and unsupported locale-prefix behavior needed an explicit deterministic contract before SLICE-0051 readiness.

**Accepted-but-unimplemented obligation:**

- SLICE-0051 must redirect locale-less `/search` requests with HTTP 308 to `/en/search`, preserving supported valid Search state;
- SLICE-0051 must return HTTP 404 for unsupported locale-prefixed Search routes and perform no Search evaluation for them;
- implementation must not use `Accept-Language`, cookies, session state, geography or account state to choose the `/search` redirect target.

**Material classifications:**

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- accepted public Search URL/canonicalization rules
- locale-less /search -> 308 /en/search fallback accepted by this record
- unsupported locale Search route -> HTTP 404 accepted by this record

GENUINELY_OPEN
- rendering boundary
- exact smallest 0051 field/query vertical

EXPLICITLY_DEFERRED
- browser-language or account-aware automatic locale negotiation
- broader site-wide locale routing beyond accepted Search scope
- future deliberate indexable SEO landing-page taxonomy
- broad arbitrary faceted-navigation indexation
- Saved Search / monitoring / alerts implementation
```

## Execution ownership

SLICE-0051 owns implementation of the bounded Search routing behavior accepted by this record.

Broader site-wide locale negotiation or personalization remains a separate future capability and must not silently alter Search canonical identity.

## One-sentence rule

> **Bare `/search` deterministically 308-redirects to `/en/search` while preserving valid Search state; explicit unsupported locale-prefixed Search routes return real HTTP 404 responses with no Search evaluation, and no browser/cookie/session/geography negotiation may change that canonical behavior.**
