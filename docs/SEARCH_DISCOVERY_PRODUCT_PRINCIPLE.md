# HullQ — Search Discovery Product Principle

**Status:** STRATEGIC PRODUCT DIRECTION  
**Related:** OQ-009, ADR-0012, `specs/SEARCH_SEMANTICS_SPEC.v0.1.md`, `specs/SEARCH_DISCOVERY_MODEL.v0.1.md`, `specs/SEARCH_RESULT_RANKING_MODEL.v0.1.md`

## Core principle

HullQ is not intended to be a conventional sailboat filter interface. Its search experience should help a user understand and explore the relevant **technical solution space**, even when the user does not already know the make/model or the exact technical implementation that can satisfy the underlying need.

The product should therefore answer more than:

```text
Which records satisfy these filters?
```

It should also help answer:

```text
What do we know for sure?
What remains unknown?
Which boats are technically plausible but insufficiently researched?
Which boats sit just outside my explicit requirements?
Which alternative technical solutions satisfy the same underlying need?
What single requirement is constraining my search most?
```

## Product differentiation

This behavior is a deliberate HullQ differentiator, not presentation polish added after the query engine.

It depends on the combination of:

- epistemic `MATCH / NO_MATCH / INSUFFICIENT_DATA` semantics;
- explicit preservation of unknown technical data;
- configuration-aware evaluation;
- separation of Requirements and Preferences;
- explainable, subordinate discovery ranking;
- explicit near-match/flexibility exploration;
- separation of market presence from canonical technical confirmation;
- provenance-aware technical data.

The value is architectural: a normal Boolean/faceted system cannot reproduce the same behavior merely by adding more filters to the UI.

## Preferred result experience

A compact default result summary should support a direction such as:

```text
23 confirmed matches
17 potential matches

Flexibility: [ Strict | 5% | 10% ]

+ 11 boats within 5%
```

The interface should remain simple even when the underlying engine is sophisticated. Engine capabilities MUST NOT be exposed one-for-one as controls.

`Strict` remains the default truth boundary. Selecting a flexibility preset expands only the separate discovery set; it never rewrites the original Requirement or relabels a hard `NO_MATCH` as a confirmed match.

## Interactive search direction

The preferred interaction model avoids a permanent wall of filters.

Only selected criteria should consume persistent UI space. Users should be able to add criteria through a searchable, grouped `+ Add criterion` interaction covering technical domains such as dimensions, hull/keel, steering, construction, rig, capacities and market constraints.

Requirements and Preferences should remain editable without exposing every engine capability as a permanent control.

Result counts should update live as the structured query changes. This live feedback is not merely decorative: it should help the user understand which criteria materially constrain the technical solution space.

Conceptually, HullQ may support multiple entry modes:

```text
Quick structured search
Guided / natural-language search
Advanced structured search
```

All modes MUST compile into the same structured HullQ query and deterministic search engine rather than becoming separate search semantics.

## Discovery over filtering

A useful HullQ result should make it possible to explain why a boat appears:

- confirmed against all hard Requirements;
- potentially suitable because nothing is disproven but some relevant data is unknown;
- near the requested solution because it misses a known numeric boundary only within an explicitly selected tolerance;
- relevant through an alternative technical solution to the same user need.

This supports HullQ's core product promise:

> **Find the right boat even if you do not know its name yet.**

The intended advantage is not simply a larger number of filters. It is a more truthful and useful way to navigate technical uncertainty and alternatives.

## Preference-priority principle

HullQ does not know which Preference is personally more important merely from the technical subject of that Preference and must not pretend otherwise.

Preference priority therefore comes only from explicit user input. The preferred default model is deliberately simple: two non-excluding tiers, conceptually `Preferred / Important` and `Nice to have / Bonus`, with final wording deferred to UX work.

A more granular 1–5 weighting cockpit is not part of the default direction because it adds interaction burden and false precision. Detailed ranking semantics are defined in `specs/SEARCH_RESULT_RANKING_MODEL.v0.1.md`.

## UX guardrail

The query engine may support sophisticated criterion-specific rules, OR groups, configuration evaluation, preference scoring and tolerance semantics. The default UI should reveal complexity progressively rather than presenting a dense technical cockpit.

A future advanced mode may expose more control, but ordinary discovery should remain comprehensible without requiring the user to understand the internal query model.

## Implementation implication

Future query-engine, API and frontend slices must preserve the distinction between:

```text
semantic qualification
        vs
user-specific discovery ordering/expansion
```

and must not collapse the product into an opaque percentage-match score or a conventional Boolean filter system.
