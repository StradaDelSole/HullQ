# ADR-0012 — Epistemic Technical Search Semantics

**Status:** ACCEPTED  
**Date:** 2026-08-22  
**Related:** OQ-009, `specs/SEARCH_SEMANTICS_SPEC.v0.1.md`, REQ-SEARCH-001..007, ADR-0004, ADR-0007, ADR-0008, ADR-0011

## Context

HullQ is intended to help users discover technically suitable sailboats even when they do not know a make/model in advance. Its production universe is deliberately broad and progressively enriched, so many valid BoatModels/BoatDesigns will have incomplete technical coverage for some time.

A conventional Boolean filter model would turn missing data into false negatives or force HullQ to fabricate completeness. Both outcomes conflict with the accepted project principles that unknown remains unknown, conflicts are preserved, configuration-sensitive values are not flattened and canonical confidence must remain evidence-bounded.

The same issue appears in market search. A real boat can exist on the market even when HullQ has not yet resolved or deeply researched the corresponding canonical model. Market presence therefore cannot be treated as equivalent to technical-query confirmation.

## Decision

HullQ SHALL use epistemic, explainable technical-query semantics rather than ordinary Boolean filtering.

For every hard technical criterion the public semantic outcome is:

```text
MATCH
NO_MATCH
INSUFFICIENT_DATA
```

For AND-connected hard criteria:

```text
any NO_MATCH
    -> NO_MATCH

no NO_MATCH + any INSUFFICIENT_DATA
    -> INSUFFICIENT_DATA

all MATCH
    -> MATCH
```

Unknown data satisfies neither positive nor negative predicates.

Ranking is subordinate to these semantic states and MUST NOT promote a `NO_MATCH` or `INSUFFICIENT_DATA` result into a confirmed `MATCH`.

## Configuration-aware search

Option-sensitive fields SHALL be evaluated against evidence-supported configuration semantics.

If at least one supported factory configuration satisfies every hard criterion, the design may be a confirmed match, but the matching configuration/option path must be exposed.

If a potentially matching factory option is known to exist but lacks the value required for evaluation, the result remains `INSUFFICIENT_DATA` rather than being guessed.

## Conflict and derived-value behavior

Unresolved conflicting evidence SHALL produce `INSUFFICIENT_DATA` for criteria that depend on the disputed value. Search does not silently average or adjudicate evidence.

Derived metrics may participate only according to their accepted methodology/applicability status. Provisional results remain visibly provisional and must not be presented as unqualified confirmed facts.

## Result presentation

Confirmed matches and insufficient-data candidates SHALL remain distinguishable. A product presentation may group them conceptually as:

```text
CONFIRMED MATCHES

POTENTIAL MATCHES
insufficient technical data
```

Criterion-level outcome metadata must support explanations of why a result matched, failed or could not yet be confirmed.

## Market independence

Market presence and technical-query status are independent dimensions.

A permitted market listing may remain discoverable with unresolved canonical identity. Such a listing must not be labelled a confirmed technical match merely because its make/model text appears relevant or because seller-entered specifications claim a value.

Conceptually, later market results may distinguish:

1. confirmed technical market matches;
2. potential market matches with insufficient technical data;
3. unresolved relevant market listings whose technical match is not yet verified.

## Product consequence

HullQ is explicitly a **technical discovery tool**, not merely a faceted filter system.

The system should help users discover unknown candidates while making uncertainty visible. It should prefer an honest potential match over a false negative caused by missing data and prefer an honest unknown over an invented technical fact.

Subjective suitability concepts such as `bluewater`, `offshore capable` or `good for circumnavigation` must not become opaque canonical hard facts. Users compose suitability from objective technical criteria and later explicit preferences.

## Consequences

### Positive

- sparse but valid records remain useful in discovery;
- missing data does not silently remove potentially suitable boats;
- confirmed hard failures remain deterministic;
- option-sensitive boats are handled without duplicating BoatDesign identity;
- search explanations reflect actual epistemic confidence;
- market discovery can surface real boats even before canonical research is complete;
- ranking can improve usefulness without corrupting truth-state semantics.

### Complexity cost

- the query engine must retain criterion-level outcomes rather than a single Boolean;
- result grouping and ranking require explicit state-aware behavior;
- configuration-aware evaluation is more complex than flat-field filtering;
- public UI/API contracts must communicate uncertainty clearly;
- future OR/preference/near-miss semantics must preserve this baseline.

## Rejected alternatives

### Treat unknown as non-match

Rejected because it creates systematic false negatives in a progressively enriched database.

### Treat unknown as match

Rejected because absence of evidence is not evidence that a criterion is satisfied.

### Use a relevance score to override hard constraints

Rejected because ranking confidence cannot turn a confirmed hard failure into a match.

### Flatten factory options into one design-level scalar

Rejected because different legitimate factory configurations can produce different query outcomes.

### Treat market listing presence as proof of technical suitability

Rejected because market observation and canonical technical verification are separate facts.

## Follow-up

`specs/SEARCH_SEMANTICS_SPEC.v0.1.md` is the normative decision baseline for OQ-009.

A later bounded query-engine slice must add executable query contracts and golden semantic tests covering at least:

- all three criterion states;
- AND aggregation;
- positive and negative predicates with unknown data;
- confirmed hard failure;
- configuration-dependent match/failure/unknown;
- unresolved conflicts;
- provisional derived values;
- deterministic ordering within state groups;
- separation of market presence from technical-query confirmation.

AND/OR grammar, soft-preference semantics, near-miss exploration and exact ranking weights remain later bounded design decisions but MUST preserve this ADR.
