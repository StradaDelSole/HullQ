# HullQ — OQ-018 Search Indexability and SEO-Readiness Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or the future SEO surface has been fully designed

## Decision

For SLICE-0051, all locale-prefixed Search surfaces are public and usable but initially non-indexable.

```text
/en/search          -> public, usable, noindex
/de/search          -> public, usable, noindex
/fr/search          -> public, usable, noindex
/pt/search          -> public, usable, noindex
/es/search          -> public, usable, noindex

/{locale}/search?<supported-search-state>
                    -> public, usable, noindex
```

This preserves the previously accepted rule that parameterized Search-result URLs are not indexable in the initial public Search vertical and extends the same initial `noindex` boundary to the locale-specific base Search routes.

## Business-critical SEO direction

The Project Owner additionally confirms that HullQ is expected to be highly dependent on organic discovery and that SEO quality is therefore a business-critical product and architecture concern.

The initial `noindex` decision MUST NOT be interpreted as de-prioritizing SEO.

Instead, SLICE-0051 and its readiness work MUST avoid architectural choices that would make a later high-quality SEO surface difficult, brittle, duplicative, or dependent on a rewrite.

The controlling direction is:

```text
initial Search application surfaces
-> intentionally noindex

future HullQ SEO surface
-> deliberately indexable
-> architecturally prepared
-> high quality
-> not inferred automatically from arbitrary buyer Search URLs
```

## SEO-readiness obligation for SLICE-0051

SLICE-0051 does not need to ship the full future SEO program, but it MUST preserve the architectural seams required for it.

At minimum, readiness and implementation must not block later support for:

- deliberate indexable locale-specific landing pages;
- stable canonical URL ownership;
- deterministic locale routing;
- correct future `hreflang` relationships;
- sitemap generation for explicitly indexable surfaces;
- intentional robots/indexability controls by route class;
- crawlable server-delivered content where future indexable surfaces require it;
- internal-linking architecture that can point to deliberate landing pages rather than arbitrary facet states;
- structured-data support where later product/page classes justify it;
- strong performance/Core Web Vitals characteristics rather than SEO-hostile client-only rendering by default;
- explicit separation between buyer Search application URLs and future SEO landing-page URLs;
- SEO release checks and tests when indexable page classes are introduced.

This is a preparedness requirement, not an instruction to prematurely implement every SEO mechanism in SLICE-0051.

## Why the initial Search routes remain noindex

The first Search route is primarily a product interaction surface, not yet a deliberately authored search-engine landing page.

Indexing it immediately would create little defensible organic value while risking:

- thin or utility-only indexed pages;
- duplicate or near-duplicate locale/search states;
- accidental coupling between buyer facet state and SEO taxonomy;
- future canonicalization debt;
- crawl-budget waste from arbitrary Search combinations;
- premature commitment to a landing-page taxonomy without evidence.

HullQ therefore chooses deliberate SEO surfaces later instead of treating public Search URLs as SEO pages merely because they are addressable.

## What this does not prohibit

This decision does not prohibit future indexation of selected HullQ pages.

Future deliberate indexable surfaces may include, where later justified and accepted:

- model or design pages;
- manufacturer pages;
- generation/configuration pages;
- curated technical-requirement landing pages;
- category or use-case landing pages;
- editorial or market-intelligence pages;
- other high-value search-intent pages with distinct content and product utility.

Those future surfaces must be introduced explicitly under accepted SEO/search architecture rather than by removing `noindex` from arbitrary Search-result URLs.

## Relationship to prior accepted OQ-018 decisions

This decision preserves:

- locale-prefixed Search routes `/en|de|fr|pt|es/search`;
- deterministic URL Search state;
- stable semantic language-neutral query parameters;
- one canonical URL identity per semantic Search state;
- lexicographic canonical parameter ordering;
- exact Decimal canonicalization;
- sparse canonical Search URLs;
- fail-closed unknown-parameter handling;
- equal duplicate single-value normalization and conflicting-duplicate rejection;
- HTTP 400 for invalid/ambiguous Search requests;
- HTTP 308 for valid-but-non-canonical Search URLs;
- empty initial non-semantic parameter allowlist;
- previously accepted non-indexability of parameterized Search-result URLs.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- bare `/search` and unsupported-locale behavior;
- rendering boundary for the first Search surface;
- the exact smallest buyer requirement/field/query vertical for SLICE-0051.

The exact robots/canonical/hreflang mechanics for the noindex Search surface may be derived during readiness from this accepted decision unless reconciliation exposes a material ambiguity.

The future indexable SEO taxonomy, content model, sitemap inventory, structured-data mapping and organic-growth program remain future explicit capabilities. They are not excluded or deprioritized by this decision.

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
- `docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`.

**Production implementation checked:**

- no current buyer-facing public Search URL adapter exists;
- no existing production Search page currently owns the future SEO taxonomy;
- parameterized Search-result URLs were already accepted as initially non-indexable.

**Already implemented / not re-decided:**

- deterministic Search truth semantics;
- versioned fail-closed Search query contracts;
- prior accepted bounded OQ-018 URL/canonicalization decisions.

**Exact remaining gap:**

- the base locale Search routes needed an explicit initial indexability rule;
- the project's dependence on future organic discovery needed to be captured so `noindex` could not be misread as permission to ignore SEO architecture.

**Accepted-but-unimplemented obligation:**

- SLICE-0051 must keep all first Search surfaces `noindex`;
- SLICE-0051 readiness/implementation must preserve the seams required for a later deliberate high-quality indexable SEO architecture and must not create avoidable rewrite debt.

**Material classifications:**

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and evaluation kernel
- versioned fail-closed Search query contracts

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat -> Search bridge selected for SLICE-0051
- accepted public Search URL/canonicalization rules
- all locale Search surfaces initially noindex
- SEO-readiness / no-architectural-dead-end obligation accepted by this record

GENUINELY_OPEN
- bare /search and unsupported-locale behavior
- rendering boundary
- exact smallest 0051 field/query vertical

EXPLICITLY_DEFERRED
- future deliberate indexable SEO landing-page taxonomy
- broad arbitrary faceted-navigation indexation
- future structured-data mapping by indexable page class
- future SEO sitemap inventory beyond what is needed to keep Search noindex
- Saved Search / monitoring / alerts implementation
```

## Execution ownership

SLICE-0051 owns implementation of the initial `noindex` boundary and the architectural preparedness required not to block the later SEO program.

A later dedicated SEO/search-surface capability may introduce explicit indexable page classes, sitemaps, structured data, content taxonomy and organic-growth release gates without reusing arbitrary Search-result URLs as SEO pages.

## One-sentence rule

> **All first HullQ Search surfaces remain `noindex`, but SEO is a business-critical architecture requirement: SLICE-0051 must preserve the canonical, locale, rendering, performance and routing seams needed for a later deliberately indexable, exceptionally strong SEO surface without requiring a structural rewrite.**