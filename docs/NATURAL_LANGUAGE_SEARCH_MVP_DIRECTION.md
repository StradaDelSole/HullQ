# HullQ — Natural-Language Search MVP Direction

**Status:** STRATEGIC PRODUCT DIRECTION  
**Related:** OQ-009, ADR-0012, `specs/SEARCH_DISCOVERY_MODEL.v0.1.md`, `docs/SEARCH_DISCOVERY_PRODUCT_PRINCIPLE.md`

## Decision direction

Natural-language search SHOULD be part of the HullQ MVP, provided it remains an optional input layer over the same deterministic structured-query engine used by manual search.

The reason for MVP inclusion is not novelty or an `AI` label. The product hypothesis is that a natural-language entry point can materially lower first-use friction, make HullQ's technical-discovery value understandable immediately, and therefore help the product gain early traction.

The working product belief is:

> A user should be able to describe the boat they want in ordinary language, see exactly how HullQ interpreted that request, and immediately enter the same explainable technical discovery flow as a user who built the query manually.

## Desired first-use experience

A prominent entry point may look conceptually like:

```text
Describe the boat you're looking for

"GRP sailing boat around 36–40 ft, under EUR 100k,
draft max 1.8 m. I would prefer a protected rudder
and at least 300 l water."

[ Build my search ]
```

HullQ then produces a visible, editable structured interpretation, for example:

```text
REQUIREMENTS
Length          36–40 ft
Material        GRP
Price           <= EUR 100,000
Draft           <= 1.80 m

PREFERENCES
Protected rudder
Water           >= 300 l
```

The user must be able to inspect and edit this interpretation before or while using it. Natural-language interpretation MUST NOT become an opaque recommendation path.

## Architectural rule

The natural-language layer is an adapter, not the search engine.

```text
human language
      ↓
Natural-language query adapter
      ↓
structured HullQ query candidate
      ↓
HullQ validation / normalization
      ↓
visible editable query
      ↓
deterministic HullQ query engine
```

Binding principle:

> **AI may propose the query. HullQ owns semantics and executes the query.**

The LLM MUST NOT decide which boats match, invent canonical technical facts, override `MATCH / NO_MATCH / INSUFFICIENT_DATA`, or bypass configuration/provenance semantics.

If the AI service is unavailable or disabled, normal HullQ search MUST continue to work.

## No model training required for MVP

HullQ does not need to train a dedicated model for this task initially.

A small general-purpose API model with strict structured output is sufficient to test the hypothesis because the task is primarily:

- intent classification;
- entity/field extraction;
- Requirement vs Preference interpretation;
- operator extraction (`<=`, `>=`, range, equality, exclusion);
- unit/currency capture;
- mapping recognized language into the HullQ query contract;
- explicit surfacing of unresolved ambiguity.

Fine-tuning should only be considered later if real usage reveals repeatable failure modes that cannot be solved adequately through schema design, vocabulary, prompting and validation.

## HullQ owns vocabulary and semantics

The LLM may recognize language, but HullQ defines accepted technical meaning.

Example:

```text
"protected rudder"
      ↓
HullQ-curated concept
      ↓
OR
- skeg-hung
- partial-skeg
- keel-hung
```

The exact mapping must be versioned/curated by HullQ rather than invented ad hoc by the model.

Likewise, aliases such as:

```text
GRP / GFK / fiberglass
```

must normalize through HullQ taxonomy.

Units and numeric normalization SHOULD remain in HullQ domain code wherever practical rather than trusting model arithmetic.

## Ambiguity behavior

The adapter must be allowed to return unresolved intent instead of guessing.

Example:

```text
"not too much draft"
```

should not silently become an arbitrary numeric maximum.

A structured unresolved result may drive UI such as:

```text
What do you mean by shallow draft?

[ <= 1.5 m ] [ <= 1.8 m ] [ <= 2.0 m ] [ Custom ]
```

The product should prefer an explicit clarification to false precision.

## Live updates after interpretation

The LLM call is intended primarily to convert the initial human-language request into the structured query.

Once that query exists, subsequent interactive changes SHOULD run directly through the HullQ query engine:

```text
natural-language request
      ↓
1 interpretation call
      ↓
structured query
      ↓
user changes draft 1.8 -> 1.9
      ↓
NO new AI call required
      ↓
instant HullQ result update
```

This keeps interaction fast, deterministic and inexpensive while supporting the live-feedback discovery UX.

## Infrastructure and operating model

MVP natural-language interpretation SHOULD use an external model API rather than self-hosted LLM inference.

Consequences:

- no GPU is required on the HullQ VPS;
- the existing small application VPS can remain responsible for FastAPI, PostgreSQL, validation and the query engine;
- the VPS sends a small HTTPS request to the model provider and receives structured output;
- model hardware is operated by the external provider;
- no dedicated AI server is required for launch.

This keeps the AI feature compatible with HullQ's lean infrastructure strategy.

## Cost posture

Natural-language query interpretation is expected to use short prompts and short structured outputs. The feature should therefore be treated as a low marginal-cost input mechanism rather than a major infrastructure expense.

Exact provider/model pricing must be revalidated at implementation time. The strategic conclusion is that launch can begin with a very small API budget, and usage costs should scale approximately with actual natural-language-search activity rather than requiring fixed GPU capacity.

If usage ever grows enough for API cost to become material, that same volume is also strong evidence of product traffic and provides a later basis for evaluating provider optimization, local parsing, caching or dedicated inference.

## MVP scope discipline

The first MVP implementation SHOULD be deliberately simple:

```text
one small external LLM
+ strict structured output
+ HullQ validation
+ editable interpreted query
+ deterministic search engine
```

Do not require for first launch:

- custom model training;
- self-hosted LLM hardware;
- multiple-provider routing;
- local-parser/LLM cascades;
- autonomous tool use;
- web-enabled model research during query parsing;
- AI-generated technical suitability scores.

Those are later optimizations only if usage evidence justifies them.

## Model-selection principle

Do not select a production model solely from public benchmark reputation or lowest token price.

HullQ SHOULD maintain a representative Golden Test corpus of natural-language boat-search prompts covering at least:

- English and German;
- nautical terminology and aliases;
- mixed metric/imperial units;
- currencies;
- typos and shorthand;
- ranges and one-sided boundaries;
- Requirement vs Preference language;
- negation;
- OR/alternative concepts;
- ambiguous phrases that should remain unresolved.

Candidate models should be evaluated against the same expected structured query outputs. Production choice should favor semantic parsing accuracy, deterministic schema behavior, latency and cost in that order appropriate to the MVP.

The adapter architecture SHOULD make the model provider replaceable without changing the HullQ query contract.

## Traction hypothesis

Natural-language search is intentionally proposed for the MVP because it may improve traction from the first public version.

The mechanism is expected to be:

```text
lower initial cognitive load
        ↓
user can describe a boat before understanding HullQ's taxonomy
        ↓
HullQ instantly converts intent into visible technical criteria
        ↓
live confirmed / potential / flexibility results react
        ↓
user experiences HullQ's differentiation immediately
```

This matters because HullQ's underlying query engine is unusually powerful. A conventional technical-filter interface could hide that value behind setup friction. Natural-language input can make the capability legible immediately without compromising deterministic search semantics.

The traction hypothesis must still be measured. Natural-language search should have instrumentation for adoption, parse success, correction rate, abandonment, conversion into result exploration, and repeated use.

## Priority relative to core search

Natural-language search is part of the desired MVP, but it MUST NOT block or weaken the core structured search engine.

Preferred implementation order:

```text
1. query contract
2. deterministic query engine
3. live search/result semantics
4. basic structured search UX
5. natural-language -> query adapter
```

If schedule pressure forces a choice, the deterministic query engine remains the non-negotiable core. The natural-language adapter is valuable because it accelerates adoption of that core, not because the product depends on AI to function.
