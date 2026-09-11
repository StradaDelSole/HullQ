# HullQ — OQ-018 Search Query-Parameter Decision

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION — PARTIAL OQ-018 RESOLUTION  
**Applies to:** SLICE-0051 readiness and the first buyer-facing public Search surface  
**Does not mean:** OQ-018 is fully resolved, SLICE-0051 is READY, or implementation has started

## Decision

The Project Owner accepts a stable, semantic, language-neutral query-parameter facade for HullQ's public Search URLs.

Example route shape:

```text
/de/search?draft_max=1.60
/en/search?draft_max=1.60
```

The public URL grammar MUST use readable semantic parameters rather than:

- an opaque encoded query blob; or
- generic `field` / `operator` / `value` triplets as the primary public representation.

Parameter names remain language-neutral across all supported locales. Translation applies only to user-facing labels, not to technical parameter names or Search semantics.

Example:

```text
/de/search?draft_max=1.60
/en/search?draft_max=1.60
```

represents the same technical Search requirement in both locales.

## Architectural boundary

The URL grammar is a public stable interface. It is NOT a second Search semantic model.

The required relationship is:

```text
public semantic query parameters
→ strict URL-query adapter
→ existing versioned HullQ Search query contract
→ existing deterministic Search evaluator
```

The existing internal versioned query representation remains authoritative for Search semantics. The public URL facade must map deterministically into that representation and may not silently invent, weaken or reinterpret criteria.

Therefore:

```text
URL grammar = stable public interface
internal Search query = authoritative semantic model
```

Internal Search query schema evolution must not by itself force previously valid public Search URLs to change meaning.

## Buyer experience

The accepted public parameter style should make Search URLs:

- readable enough to understand at a glance;
- bookmarkable and shareable;
- stable across supported languages;
- suitable for browser reload/back-forward behavior;
- suitable as a future basis for Saved Search / monitoring identity;
- easier to debug and support than opaque encoded payloads.

The UI must continue to display active Search requirements in human-readable localized controls/chips, while the underlying technical URL parameter names remain language-neutral.

## Relationship to existing Search contracts

HullQ already has versioned, fail-closed Search query contracts:

- numeric query contract v0.1;
- mixed numeric/categorical query contract v0.2;
- unknown keys and unsupported query schema forms fail closed rather than being silently discarded.

This decision does not replace those contracts. It defines only the public URL facade that adapts into them.

## Explicitly not decided here

The following remain genuinely open before SLICE-0051 readiness:

- exact canonical parameter names for the bounded first vertical beyond illustrative examples such as `draft_max`;
- canonical ordering of parameters;
- numeric serialization/normalization rules;
- duplicate parameter behavior;
- repeated-value behavior for future multi-value criteria;
- invalid or unknown parameter handling;
- omission of defaults / empty values;
- canonical redirect vs canonical-link behavior for equivalent URL forms;
- locale-specific base Search-route indexability/canonical behavior;
- bare `/search` and unsupported-locale behavior;
- rendering boundary;
- robots/canonical/hreflang mechanics for parameterized non-indexable Search results.

The examples in this record illustrate the accepted semantic style; they do not silently freeze the complete future all-field parameter catalog.

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
- language-neutral technical Search semantics;
- parameterized Search-result URLs initially non-indexable;
- purpose-built SEO landing pages as a later deliberate capability;
- FastAPI as sole application/domain API boundary;
- accepted buyer/broker/success/quality standards.

## Reconciliation classification

```text
DECIDED_AND_IMPLEMENTED
- deterministic Search semantics and query evaluation kernel
- versioned numeric and mixed query contracts with fail-closed parsing

DECIDED_NOT_YET_IMPLEMENTED
- buyer-facing public Search surface
- production NativeListing/PhysicalBoat → Search bridge selected for SLICE-0051
- deterministic public URL Search state
- locale-prefixed Search routes
- stable semantic language-neutral query-parameter facade accepted by this record

GENUINELY_OPEN within OQ-018 before SLICE-0051 readiness
- exact bounded first-vertical parameter catalog
- canonical ordering/normalization/default omission
- duplicate/repeated/unknown/invalid parameter behavior
- canonicalization mechanics for equivalent URL forms
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

## One-sentence rule

> **HullQ's public Search exposes stable semantic language-neutral query parameters as a readable URL facade, which must adapt deterministically into the existing versioned Search query contract rather than becoming a second independent Search semantic model.**
