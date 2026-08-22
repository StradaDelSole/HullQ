# HullQ — Search Discovery Product Principle

**Status:** STRATEGIC PRODUCT DIRECTION  
**Related:** OQ-009, ADR-0012, `specs/SEARCH_SEMANTICS_SPEC.v0.1.md`, `specs/SEARCH_DISCOVERY_MODEL.v0.1.md`

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

## Discovery over filtering

A useful HullQ result should make it possible to explain why a boat appears:

- confirmed against all hard Requirements;
- potentially suitable because nothing is disproven but some relevant data is unknown;
- near the requested solution because it misses a known numeric boundary only within an explicitly selected tolerance;
- relevant through an alternative technical solution to the same user need.

This supports HullQ's core product promise:

> **Find the right boat even if you do not know its name yet.**

The intended advantage is not simply a larger number of filters. It is a more truthful and useful way to navigate technical uncertainty and alternatives.

## Preferred search-building interaction

The default experience SHOULD avoid a permanently visible wall of technical filters. Only criteria the user has selected should consume interface space.

A simple initial state may expose only a small number of high-value fields plus an additive action:

```text
FIND A BOAT

Length        10–13 m
Budget        <= EUR 100k
Market        Europe

[ + Add requirement ]
[ Search ]
```

As criteria are added, the active query remains compact:

```text
10–13 m
Draft <= 1.80 m
GRP
Skeg-hung rudder
Built after 1985
Price <= EUR 100k

Preferences: 3

[ + Add criterion ]
```

### Searchable criterion picker

`+ Add criterion` SHOULD open a searchable, grouped picker rather than reveal every possible technical field at once. A user may browse by domain or search directly for terms such as `rudder`, `tank`, `rig`, or `draft`.

The system may ultimately support a large technical criterion universe without forcing the ordinary user to confront that complexity simultaneously.

### Requirement and Preference editing

A selected criterion may be marked as `Required` or `Preferred`. This distinction should be available when needed but should not create persistent visual noise. Compact chips/rows can summarize the current query and reveal detailed semantics on edit.

## Live search feedback

HullQ SHOULD update result counts interactively as the structured query changes. This is a first-class discovery behavior, not merely UI animation.

Example:

```text
1,842 known designs

Draft <= 1.80 m
-> 1,106

+ GRP
-> 827

+ Skeg-hung rudder
-> 214 confirmed
   96 potential
```

The purpose is to let the user learn the shape of the market while constructing the query. HullQ should make restrictive criteria visible and, where useful, explain which requirement most constrains the result universe.

A future result explanation may support patterns such as:

```text
214 confirmed
96 potential

Most restrictive:
Skeg-hung rudder
```

or, where deterministic and explainable:

```text
Relaxing draft by 8 cm adds 6 nearby candidates.
```

Live updates after the structured query exists SHOULD be executed by the HullQ query engine and MUST NOT require a generative-AI call for every field edit or keystroke.

## Multiple entry modes, one query model

HullQ may expose multiple ways to construct a search, but they MUST converge on the same structured query contract and deterministic engine.

Conceptually:

```text
QUICK
small set of common fields + Add criterion

GUIDED / NATURAL LANGUAGE
Describe the boat you are looking for

ADVANCED
explicit Requirements / Preferences / OR groups / detailed controls
```

These are different interaction surfaces, not different search engines.

```text
input method
    ↓
structured HullQ query
    ↓
deterministic query engine
```

This separation allows the UI to remain approachable while preserving a powerful technical model underneath.

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

The preferred product behavior is therefore:

> **The engine may be complex; the interaction should feel simple, immediate and exploratory.**
