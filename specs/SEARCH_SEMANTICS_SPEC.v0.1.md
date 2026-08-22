# HullQ Search Semantics Specification v0.1

**Status:** ACCEPTED DECISION BASELINE  
**Decision:** OQ-009  
**Related:** ADR-0012, REQ-SEARCH-001..007, ADR-0004, ADR-0007, ADR-0008, ADR-0011

## Purpose

HullQ search is a technical discovery system, not a Boolean filtering façade over partially populated records.

Search therefore evaluates what is known, what is known not to match, and what remains unknown. Missing or conflicting technical data must not create false negatives, while confirmed failures of hard constraints must remain decisive.

This specification defines the accepted baseline semantics. Query-language syntax, ranking weights, soft-preference combinators and public API representation remain later implementation details unless explicitly fixed below.

## 1. Criterion outcome

Every hard technical criterion is evaluated to one of the following public semantic states:

```text
MATCH
NO_MATCH
INSUFFICIENT_DATA
```

`NOT_APPLICABLE` may exist internally where a criterion or metric is semantically inapplicable to a subject, but it is not a substitute for the three public query outcomes and must be handled according to the criterion's accepted applicability rules.

### MATCH

The available accepted evidence/canonical value confirms that the evaluated subject/configuration satisfies the criterion.

### NO_MATCH

The available accepted evidence/canonical value confirms that the evaluated subject/configuration violates the criterion.

### INSUFFICIENT_DATA

HullQ cannot confirm either satisfaction or failure because the required data is missing, unresolved, conflicting, insufficiently specific, provisional where confirmation is required, or otherwise not safely evaluable.

Unknown data is epistemic uncertainty. It is not false.

## 2. Hard-constraint aggregation

For an AND-connected set of hard criteria:

1. if any criterion is `NO_MATCH`, the overall hard-query outcome is `NO_MATCH`;
2. otherwise, if any criterion is `INSUFFICIENT_DATA`, the overall outcome is `INSUFFICIENT_DATA`;
3. only when every active hard criterion is `MATCH` is the overall outcome `MATCH`.

Formally:

```text
any NO_MATCH
    -> NO_MATCH

no NO_MATCH + any INSUFFICIENT_DATA
    -> INSUFFICIENT_DATA

all MATCH
    -> MATCH
```

Ranking, relevance or preference scores must never override this state.

## 3. Positive and negative predicates

Unknown data satisfies neither positive nor negative predicates.

Examples:

```text
rudder == skeg_hung
rudder = unknown
-> INSUFFICIENT_DATA

rudder != spade
rudder = unknown
-> INSUFFICIENT_DATA
```

HullQ must never interpret missing data as `not X` merely because `X` is unobserved.

## 4. Confirmed failure remains decisive

A record that fails one hard constraint remains `NO_MATCH` even if every other criterion matches strongly or a ranking model would otherwise score the record highly.

Example:

```text
LOA          MATCH
material     MATCH
draft        NO_MATCH
rudder       MATCH
year         MATCH

=> NO_MATCH
```

HullQ may later expose near-miss discovery features, but a near miss must not be relabelled as a confirmed hard-query match.

## 5. Configuration-aware evaluation

Option-sensitive criteria must be evaluated against evidence-supported `ResolvedConfiguration` semantics rather than assuming the BoatDesign baseline applies to every factory configuration.

Example:

```text
query: draft <= 1.80 m

standard keel configuration: 2.05 m -> NO_MATCH
shoal keel configuration:    1.65 m -> MATCH
```

A BoatDesign may therefore qualify as a confirmed design-level match when at least one evidence-supported factory configuration satisfies all hard criteria.

The result must expose which configuration or option path produced the match. The system must not hide the fact that other configurations of the same design fail.

If a potentially relevant factory option is known to exist but the value required to evaluate it is unknown, that option is `INSUFFICIENT_DATA` rather than invented as a match or failure.

Example:

```text
standard draft = 2.05 m                -> NO_MATCH
shallow-draft option exists, value ?   -> INSUFFICIENT_DATA

BoatDesign outcome -> INSUFFICIENT_DATA
```

## 6. Ranges and applicability

A source range must not be used to erase configuration, option, state or applicability semantics.

If a range represents unresolved variation and the criterion boundary falls inside the range, the outcome is `INSUFFICIENT_DATA` unless evidence resolves the applicable value.

If distinct supported configurations explain the range, evaluate those configurations separately.

## 7. Conflicting evidence

Unresolved conflicting evidence must not be averaged, majority-voted or silently resolved for search.

Example:

```text
source A draft = 1.70 m
source B draft = 1.90 m
query draft <= 1.80 m
no accepted canonical resolution

=> INSUFFICIENT_DATA
```

Search consumes accepted canonical/resolution semantics; it does not adjudicate source conflicts by itself.

## 8. Derived metrics

A derived metric may participate in search only according to its accepted method-version and applicability semantics.

- a fully supported computed value may produce `MATCH` or `NO_MATCH`;
- missing required inputs produce `INSUFFICIENT_DATA`;
- a value explicitly marked provisional must remain machine-visible as provisional and must not be presented as an unqualified confirmed technical fact.

Exact public treatment of provisional derived matches may be refined in the query-engine contract, but ranking must not erase their provisional status.

## 9. Result-set separation

Confirmed matches and insufficient-data candidates must remain distinguishable.

A public presentation may conceptually expose:

```text
CONFIRMED MATCHES

POTENTIAL MATCHES
insufficient technical data
```

The product must not flatten both groups into one apparently homogeneous result count without communicating the difference.

## 10. Ranking

Ranking is subordinate to semantic outcome.

Within an outcome group, ranking may use deterministic, versioned signals such as:

- number/fraction of hard criteria confirmed;
- technical-data coverage relevant to the query;
- explicit user preferences introduced by a later query contract;
- market relevance/freshness where the result context is market search;
- deterministic tie-breakers.

A candidate with four confirmed criteria and one unknown may rank above one with one confirmed criterion and four unknowns, while both remain `INSUFFICIENT_DATA`.

Ranking must never convert `NO_MATCH` to `MATCH` or `INSUFFICIENT_DATA` to `MATCH`.

The exact ranking formula is versioned separately and is not fixed by v0.1.

## 11. Explainability

Every evaluated result should retain criterion-level outcome metadata sufficient to explain the result without reconstructing semantics from UI state.

A result should be able to answer:

- which criteria matched;
- which criterion caused a confirmed failure;
- which criteria are unknown/conflicted/provisional;
- which configuration produced a configuration-dependent match;
- which accepted data/method version was used.

Explainability is part of the product contract, not optional debugging output.

## 12. Market presence is orthogonal to technical-query status

The existence of a market listing and the technical-query status of its model/configuration are separate facts.

A permitted market observation may be searchable even when its canonical BoatModel/BoatDesign identity is unresolved.

HullQ must distinguish statements such as:

```text
We found this boat on the market.
```

from:

```text
We have confirmed that this boat satisfies your technical query.
```

An unresolved market listing must not be labelled a confirmed technical match merely from make/model text or seller-entered claims.

Conceptually, market results may later be separated into:

1. confirmed technical market matches;
2. potential market matches with insufficient technical data;
3. unresolved relevant market listings whose technical match is not yet verified.

This principle is compatible with the retained market-discoverability strategy but does not itself authorize any market data source or ingestion method.

## 13. Discovery-tool principle

HullQ is explicitly intended to be a technical discovery tool, not merely a conventional faceted filter UI.

Consequences include:

- unknown data remains visible rather than silently excluding candidates;
- users can discover plausible candidates they did not already know by name;
- configuration-sensitive matches are surfaced with their conditions;
- result explanations reveal why a boat matches or cannot yet be confirmed;
- confirmed constraints and later user preferences remain semantically distinct;
- subjective suitability labels must not replace atomic technical evidence.

The query engine may later support preferences, OR groups, discovery expansion and near-miss exploration, but those features must preserve the hard semantic states defined here.

## 14. Subjective suitability

Search must not depend on opaque canonical suitability facts such as:

```text
bluewater = true
offshore_capable = true
good_for_circumnavigation = true
```

HullQ stores/searches objective technical evidence and lets users compose suitability through criteria and preferences. Derived metrics must not silently become a safety or seaworthiness score.

## 15. Determinism and versioning

Given the same:

- canonical dataset/version;
- query specification;
- taxonomy version;
- derived-method version;
- ranking version where applicable;

HullQ must reproduce the same semantic outcomes and ordering.

## 16. Accepted OQ-009 rules

The binding OQ-009 baseline is:

1. criterion evaluation is epistemic, not Boolean: `MATCH / NO_MATCH / INSUFFICIENT_DATA`;
2. any confirmed failing hard criterion makes the overall hard-query outcome `NO_MATCH`;
3. no failure plus at least one unknown makes the overall outcome `INSUFFICIENT_DATA`;
4. only all-confirmed hard criteria produce `MATCH`;
5. unknown satisfies neither positive nor negative predicates;
6. factory configurations are evaluated independently; one fully matching supported configuration can make the design a confirmed match, with the matching configuration exposed;
7. ranking may order candidates but may never override semantic state;
8. market presence and technical-query status are independent dimensions.

## 17. Deferred implementation details

This specification deliberately does not yet freeze:

- public query JSON/schema syntax;
- AND/OR expression grammar beyond the accepted AND hard-constraint aggregation above;
- exact soft-preference model;
- near-miss behavior;
- exact deterministic ranking formula/weights;
- pagination semantics;
- API response shape;
- frontend presentation copy;
- SEO/faceted-navigation URL behavior governed by OQ-018/ADR-0007.

Those decisions must preserve this accepted baseline.
