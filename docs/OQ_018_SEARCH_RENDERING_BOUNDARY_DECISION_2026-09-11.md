# HullQ — OQ-018 Search Rendering Boundary Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

The Project Owner accepts the following rendering and application boundary for the first public Search surface:

```text
Browser
  -> Astro SSR web layer
      -> localized presentation / route handling / HTTP response concerns
      -> server-rendered initial Search HTML
      -> optional React islands only for bounded progressive interaction
        -> FastAPI
            -> sole application/domain API boundary
            -> Search semantic validation and canonical Search state
            -> claim resolution and Search evaluation
            -> inventory/result classification
              -> PostgreSQL
```

The controlling rule is:

> **Astro owns Web and presentation; FastAPI owns all Search/domain semantics; initial Search results are server-rendered; React may enhance bounded interactions but must not become a second owner of Search state or Search meaning.**

## Astro responsibilities

For the public Search surface, Astro owns web-facing concerns including:

- locale-prefixed Search page routing;
- localized labels and buyer-facing copy;
- server-rendered initial HTML;
- presentation of applied requirements, confirmed matches and insufficient-data states;
- HTTP response status and headers at the web boundary;
- `noindex`/canonical/meta output required by the accepted Search URL rules;
- buyer-facing HTTP 400 recovery presentation;
- buyer-facing 404 presentation;
- composition of accepted HTTP 308 redirects from canonical Search state returned by the application boundary;
- progressive enhancement hooks where interaction materially benefits the buyer.

Astro MUST NOT:

- access PostgreSQL directly for Search truth;
- reimplement Python domain rules;
- independently decide Search truth semantics;
- silently invent alternate canonicalization rules;
- independently resolve PhysicalBoat claims;
- independently classify a result as `CONFIRMED_MATCH`, `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA`.

## FastAPI responsibilities

FastAPI remains the sole application/domain API boundary and owns all behavior that can alter Search meaning, including:

- accepted public Search parameter semantic contracts;
- exact Decimal parsing/normalization semantics;
- duplicate, unknown, invalid and ambiguous parameter handling;
- construction/validation of canonical language-neutral Search state;
- compatibility with the existing versioned Search query contracts;
- PhysicalBoat/listing claim-resolution behavior required by the selected 0051 vertical;
- Search evaluation against concrete ACTIVE native professional inventory;
- result classification and truth-safe explanation data;
- preservation of existing `UNKNOWN`, `UNRESOLVED` and `CONFLICT` behavior.

The web layer may render or localize application results but MUST NOT alter their technical meaning.

## Server-rendered initial results

A direct request to a canonical Search URL such as:

```text
/de/search?draft_max=1.6
```

must return meaningful initial HTML from the server rather than an empty client shell that requires a second browser API call before Search results exist.

The first response should be capable of containing, within the exact selected 0051 vertical:

- Search controls/state;
- applied buyer requirement(s);
- result classification;
- confirmed native inventory matches;
- insufficient-data outcome where applicable;
- buyer-facing next action links to concrete NativeListing pages.

This requirement preserves good first-load behavior, accessibility, deterministic route rendering and the accepted SEO-readiness obligation.

## React boundary

React remains allowed only where an interactive island materially improves the buyer experience, for example:

- bounded filter-control interaction;
- mobile filter-panel behavior;
- sliders or selection widgets;
- other local UI interaction that does not own Search semantics.

React MUST NOT become the primary first-load Search renderer or a second semantic Search implementation.

The persistent public URL remains the shareable/reloadable Search-state representation.

An interactive enhancement may update/navigate Search state, but final accepted state and evaluation continue to pass through the canonical public Search contract and FastAPI boundary.

## Progressive-enhancement principle

The preferred direction is:

```text
canonical URL Search state
-> server request
-> Astro SSR
-> FastAPI semantic evaluation
-> meaningful HTML
-> optional bounded React enhancement
```

rather than:

```text
empty/client-heavy shell
-> React owns Search state
-> browser-only API request
-> duplicate semantic state machine
```

This does not require every future Search interaction to perform a full-page reload. More advanced client interaction may later be introduced if it preserves one canonical Search semantic owner and server-renderable/crawlable page classes where required.

## Relationship to accepted architecture

This decision preserves the accepted architecture rebaseline:

- Astro is the main web framework;
- React is for interactive app surfaces/islands;
- FastAPI is the sole application/domain API boundary;
- production PostgreSQL is not accessed directly from the public web page layer;
- the public listing precedent already uses Astro SSR and a FastAPI fetch boundary.

This record therefore does not create a second backend or redefine the accepted stack.

## SEO relationship

All SLICE-0051 Search surfaces remain `noindex` as already accepted.

However, the rendering boundary must satisfy the accepted business-critical SEO preparedness requirement:

- future deliberately indexable page classes can receive crawlable server-delivered content;
- later locale-specific SEO landing pages need not be rebuilt from a client-only SPA architecture;
- canonical/locale/rendering/performance responsibilities remain separable;
- Core Web Vitals and first-load performance are not sacrificed by default to unnecessary client-side rendering.

This record does not decide the future indexable SEO taxonomy or content model.

## Relationship to prior accepted OQ-018 decisions

This decision preserves all accepted Search URL and routing decisions, including:

- locale routes `/en|de|fr|pt|es/search`;
- deterministic language-neutral URL Search state;
- one canonical Search URL identity per locale and semantic state;
- exact Decimal canonicalization;
- sparse canonical URLs;
- fail-closed unknown/invalid handling;
- accepted duplicate single-value policy;
- HTTP 400 for invalid/ambiguous Search requests;
- HTTP 308 for valid-but-non-canonical Search URLs;
- empty initial non-semantic allowlist;
- all first Search surfaces `noindex`;
- bare `/search` -> deterministic HTTP 308 `/en/search` fallback;
- unsupported locale-prefixed Search routes -> HTTP 404.

## Explicitly not decided here

Exactly one material Owner decision remains before SLICE-0051 readiness:

- the exact smallest buyer requirement / field / query vertical that SLICE-0051 will implement end to end.

This record does not mark SLICE-0051 READY and does not start implementation.

## Decision / implementation reconciliation

**Already implemented / not re-decided:**

- deterministic Search truth semantics and evaluation kernel;
- versioned fail-closed Search query contracts;
- Astro public listing SSR precedent using FastAPI rather than direct PostgreSQL access;
- accepted Astro + React-islands + FastAPI stack boundary.

**Accepted but not yet implemented:**

- first buyer-facing public Search surface;
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051;
- accepted public Search URL/routing/canonicalization rules;
- rendering boundary accepted by this record.

**Genuinely open:**

- exact smallest SLICE-0051 buyer requirement / field / query vertical.

**Explicitly deferred:**

- broad client-side Search SPA architecture;
- future advanced client navigation optimizations that preserve the semantic boundary;
- future deliberate indexable SEO landing-page taxonomy;
- broad all-field Search implementation;
- Saved Search / monitoring / alerts.

## Execution ownership

SLICE-0051 owns implementation of this bounded Search rendering boundary for its selected vertical.

Future UI sophistication may build on it without moving domain/Search truth ownership out of FastAPI or making React the second semantic owner.

## One-sentence rule

> **HullQ Search uses Astro SSR for web/presentation and meaningful initial HTML, FastAPI as the sole Search/domain semantic owner, and React only as bounded progressive enhancement rather than as a second Search state machine or client-only primary renderer.**
