# HullQ Search Discovery Model v0.1

**Status:** ACCEPTED DECISION BASELINE  
**Related:** OQ-009, ADR-0012, `specs/SEARCH_SEMANTICS_SPEC.v0.1.md`

## Purpose

HullQ is a technical discovery tool, not merely a conventional faceted filter system.

The search model therefore separates:

1. **Requirements** — hard technical constraints that determine semantic qualification;
2. **Preferences** — non-excluding user priorities used for discovery ordering/explanation;
3. **Discovery tolerances** — explicit user-controlled exploration outside a hard boundary, analogous to a travel search that can show dates `+/- 3 days` without changing the originally requested date.

These concepts MUST remain distinct.

## 1. Requirements

A Requirement is a hard constraint.

Every Requirement is evaluated using the accepted OQ-009 states:

```text
MATCH
NO_MATCH
INSUFFICIENT_DATA
```

Confirmed failure of a Requirement remains `NO_MATCH` regardless of preference ranking or discovery relevance.

## 2. Preferences

A Preference expresses what the user would like but does not require.

A Preference MUST NOT exclude a candidate that satisfies all Requirements.

Preference evaluation must preserve uncertainty. Conceptually a Preference may be:

```text
MET
NOT_MET
UNKNOWN
```

`UNKNOWN` MUST NOT be silently treated as `NOT_MET`, because that would penalize sparsely researched boats merely because HullQ lacks data.

Preferences may influence deterministic ranking and explanation only after semantic hard-constraint qualification.

The product SHOULD expose enough information to explain preference ordering rather than presenting an opaque generic suitability percentage.

Example:

```text
REQUIREMENTS
5 / 5 confirmed

PREFERENCES
6 met
1 not met
1 unknown
```

## 3. Hard qualification and discovery ranking are separate operations

HullQ SHALL conceptually evaluate a query in two stages:

```text
STEP 1 — semantic qualification
What can HullQ truthfully establish?

MATCH / NO_MATCH / INSUFFICIENT_DATA

STEP 2 — discovery ordering
Which candidates are most useful for this user's stated preferences and exploration settings?
```

Ranking MUST NOT change the semantic qualification state.

The system MUST NOT collapse both stages into one opaque score that can override hard technical truth.

## 4. User-controlled discovery tolerance

HullQ MAY let a user explicitly widen discovery around a Requirement without changing the original Requirement.

This is analogous to choosing `+/- 3 days` when searching for a flight: the requested date remains the requested date, while the user asks to see nearby alternatives as well.

Example:

```text
Requirement:
draft <= 1.80 m

Discovery tolerance:
show up to +0.05 m
```

A boat with draft `1.82 m` remains:

```text
hard semantic state: NO_MATCH
```

but MAY additionally appear in a clearly separated discovery group such as:

```text
NEAR MATCH
Draft 1.82 m
Your requirement: <= 1.80 m
Difference: +0.02 m
```

A discovery tolerance MUST NOT relabel the candidate as a confirmed Requirement match.

## 5. Tolerance must be explicit

Discovery tolerance MUST be user-visible and user-controlled.

HullQ MUST NOT silently relax Requirements merely to produce more results.

A saved query/monitor MUST preserve whether tolerance/near-match discovery was enabled and the exact versioned tolerance settings used. A strict query must remain strict when replayed.

## 6. Criterion-specific tolerance semantics

Tolerance MUST be defined per criterion type rather than by a universal similarity percentage.

Useful numeric examples may include:

- LOA: `+/- 0.5 m`;
- draft: `+0.05 m` or `+0.10 m` above a maximum;
- price: `+5%` or an explicit currency amount;
- first-built/year: `+/- N years`;
- displacement: explicit absolute or relative range where meaningful.

These are examples, not fixed product defaults.

Categorical requirements MUST NOT receive arbitrary numeric distance semantics.

For example:

```text
required material = aluminium
actual material = GRP
```

is not meaningfully a `small percentage` away from the Requirement.

If HullQ later offers categorical exploration, alternatives must be curated and explicit rather than inferred from an opaque similarity score.

## 7. Range and ideal-zone preferences

A user may have a hard acceptable range and a narrower preferred range.

Example:

```text
REQUIRE LOA: 10-13 m
PREFER LOA:  11-12 m
```

A boat at `10.5 m` remains a confirmed Requirement match but may rank below an otherwise comparable boat at `11.5 m`.

A boat at `13.5 m` remains a hard `NO_MATCH` unless the user separately enabled an applicable discovery tolerance.

## 8. OR groups

Where the later query grammar supports OR groups, three-state semantics MUST be preserved.

For an OR group of hard criteria:

```text
any MATCH        -> MATCH
all NO_MATCH     -> NO_MATCH
otherwise        -> INSUFFICIENT_DATA
```

This allows HullQ to express alternative technical solutions rather than forcing the user to know one exact implementation in advance.

Example:

```text
acceptable rudder protection:
OR
- skeg-hung
- partial-skeg
- keel-hung
```

## 9. Near-match presentation

Near matches are discovery aids, not a fourth hard-query truth state.

A near match is still `NO_MATCH` under the original hard Requirement and MUST expose:

- which Requirement failed;
- the required value/range;
- the observed accepted value;
- the distance outside the boundary;
- the tolerance rule that allowed it to be shown.

Where several Requirements fail, the product MAY decide not to show a candidate as a near match or MAY rank it lower according to a later deterministic near-match policy.

## 10. Epistemic guardrail

Discovery tolerance applies only when HullQ has sufficient accepted data to know that the candidate is outside the hard boundary by a defined amount.

If the relevant value is unknown or conflicting, the candidate remains `INSUFFICIENT_DATA`; tolerance MUST NOT fabricate a distance from the Requirement.

## 11. Product consequence

HullQ search should support a progression such as:

```text
CONFIRMED MATCHES

POTENTIAL MATCHES
insufficient technical data

NEAR MATCHES
outside one or more explicit requirements but within user-selected discovery tolerance
```

Market observations whose canonical identity or technical qualification is unresolved remain a separate market-discovery dimension under the accepted OQ-009/market-discoverability rules.

## 12. Accepted baseline

The accepted discovery model is:

1. a query distinguishes hard **Requirements** from non-excluding **Preferences**;
2. hard semantic qualification and discovery ranking are separate operations;
3. unknown preference data is not equivalent to a failed preference;
4. ranking never overrides a hard semantic state;
5. users may explicitly enable criterion-specific discovery tolerance analogous to a `+/-` date search;
6. tolerance does not change the original Requirement or relabel a `NO_MATCH` as `MATCH`;
7. near matches must explain the failed Requirement and exact deviation;
8. tolerance semantics are criterion-specific and deterministic, not a universal opaque similarity percentage;
9. tolerance cannot be computed from unknown/conflicting values;
10. saved/replayed queries must preserve strict-vs-tolerant behavior exactly.

## 13. Deferred details

This baseline does not yet freeze:

- exact UI controls or wording;
- default tolerance values;
- whether tolerances are offered globally, per criterion, or both;
- exact preference weights/ranking formula;
- exact near-match ranking policy;
- exact public query JSON/schema syntax;
- categorical alternative sets;
- pagination or API representation.

Those later decisions MUST preserve the semantic separation established here.
