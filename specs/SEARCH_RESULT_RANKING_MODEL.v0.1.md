# HullQ Search Result Ranking Model v0.1

**Status:** ACCEPTED DECISION BASELINE  
**Related:** OQ-009, ADR-0012, `specs/SEARCH_SEMANTICS_SPEC.v0.1.md`, `specs/SEARCH_DISCOVERY_MODEL.v0.1.md`

## Purpose

HullQ ranking orders results inside already established semantic result groups. Ranking never determines whether a candidate is a confirmed technical match.

The product must remain explainable and must not collapse technical truth, evidence coverage, user preference and near-match distance into one opaque public percentage.

## 1. Semantic groups remain primary

Results are first separated by semantic status:

```text
1. CONFIRMED MATCHES
2. POTENTIAL MATCHES
3. WITHIN FLEXIBILITY / NEAR MATCHES
```

Ranking MUST NOT mix these groups in a way that causes a high-ranking potential or near match to appear as stronger than a confirmed hard-query match.

A near match remains `NO_MATCH` under the original Requirements. A potential match remains `INSUFFICIENT_DATA`. Ranking never changes either state.

## 2. Preference importance must never be inferred

HullQ does not know which user preference is personally more important merely from the technical subject of that preference.

The system MUST NOT assume, for example, that a rudder preference is inherently more important than an interior, rig, tankage, age or other preference.

Preference importance exists only when the user expresses it.

Therefore:

> **HullQ may evaluate whether a preference is met, not met or unknown, but it may not invent the user's priority between preferences.**

## 3. Two user-controlled preference tiers

The accepted default model uses two simple non-excluding preference-priority tiers and no finer default weighting scale.

Conceptually:

```text
PREFERRED / IMPORTANT

NICE TO HAVE / BONUS
```

Final public wording remains a UX decision, but the semantic distinction is two-tier.

Both tiers remain Preferences, not Requirements:

- failure to meet either tier MUST NOT exclude a candidate that satisfies the hard Requirements;
- `UNKNOWN` MUST remain distinct from `NOT_MET`;
- the higher tier may influence ranking more strongly only because the user explicitly placed the preference there;
- HullQ MUST NOT silently move a preference between tiers.

A 1–5 star weighting system or similarly granular mandatory weighting UI is rejected as the default because it adds interaction cost and false precision.

## 4. Ranking confirmed matches

Within `CONFIRMED MATCHES`, all hard Requirements are already confirmed.

Ranking SHOULD therefore primarily reflect the user's explicit Preferences, respecting:

1. user-selected preference tier;
2. `MET / NOT_MET / UNKNOWN` state;
3. deterministic tie-breakers defined by a later versioned ranking contract.

Public presentation SHOULD explain the preference fit rather than expose a generic opaque match percentage.

Example:

```text
CONFIRMED MATCH
Requirements: 6 / 6 confirmed

Preferences:
4 met
1 unknown

Why this ranks highly:
✓ protected rudder
✓ preferred tankage
✓ preferred displacement
? cutter option not verified
```

## 5. Ranking potential matches

Within `POTENTIAL MATCHES`, evidence coverage is an important ranking signal because the candidates differ in how close HullQ is to being able to confirm them.

Example:

```text
Boat A
5 / 6 Requirements confirmed
1 unknown
4 Preferences met

Boat B
3 / 6 Requirements confirmed
3 unknown
5 Preferences met
```

Boat A may rank above Boat B because HullQ has materially stronger technical evidence relevant to the hard query, even though Boat B currently appears to meet more Preferences.

This MUST NOT mean that unknown values are treated as failed Requirements. Both boats remain `POTENTIAL` until the hard-query semantics can be resolved.

The public explanation should expose the missing or unresolved Requirement data rather than hiding it behind ranking.

## 6. Ranking within flexibility / near matches

Within the `WITHIN FLEXIBILITY / NEAR MATCHES` group, ranking may consider transparent distance outside the original Requirement boundary, but only for criteria with accepted distance semantics.

Example:

```text
Requirement: draft <= 1.80 m

Boat A: 1.82 m -> +0.02 m
Boat B: 1.88 m -> +0.08 m
```

All else equal, Boat A may rank above Boat B because it is closer to the explicit boundary.

Where multiple Requirements fail, later policy may account for the number and magnitude of failures, but it must remain deterministic and explainable.

Categorical mismatches MUST NOT be converted into invented percentage distances. Hull material, rudder type, keel type and similar categorical values do not have a universal numerical mismatch distance.

## 7. Accepted ranking hierarchy

The accepted conceptual hierarchy is:

```text
SEMANTIC GROUP
Confirmed > Potential > Near

        ↓

EVIDENCE QUALITY / QUERY-RELEVANT COVERAGE
especially within Potential

        ↓

USER-EXPRESSED PREFERENCES
with two explicit priority tiers

        ↓

DISCOVERY DISTANCE
within Near Matches only and only where semantically valid

        ↓

DETERMINISTIC TIE-BREAKER
```

The exact mathematical implementation may differ by semantic group. HullQ MUST NOT force these signals into one universal public score.

## 8. No opaque public match score

HullQ SHOULD NOT present a generic result such as:

```text
92% MATCH
```

when that number mixes hard Requirements, unknown data, user Preferences, evidence coverage and near-match tolerance.

Internally, versioned numerical scores may be used for efficient deterministic ordering, provided the public result remains explainable and the score never changes semantic status.

Preferred public explanations include:

```text
CONFIRMED MATCH
6 / 6 Requirements confirmed
4 / 5 Preferences met
1 Preference unknown
```

or:

```text
POTENTIAL MATCH
5 / 6 Requirements confirmed
1 Requirement lacks sufficient data
```

## 9. Research-feedback consequence

Potential-match ranking and explanation may expose high-value data gaps.

If a candidate would become confirmable once one missing technical value is researched, HullQ may use aggregated search demand and unresolved criterion importance as a later research-priority signal.

This is a research prioritization aid, not permission to infer the missing value or weaken the query semantics.

## 10. Accepted baseline

The binding baseline is:

1. semantic result groups are established before ranking and are never overridden by ranking;
2. HullQ MUST NOT infer which Preferences matter more to a user;
3. preference importance comes only from explicit user input;
4. the default preference-priority model has exactly two simple tiers: higher-priority `Preferred/Important` and lower-priority `Nice to have/Bonus` semantics;
5. both tiers remain non-excluding Preferences;
6. `UNKNOWN` preference data is not equivalent to `NOT_MET`;
7. confirmed matches are primarily ordered by explicit user preference fit plus deterministic tie-breakers;
8. potential matches may additionally prioritize query-relevant evidence coverage without treating unknown as failure;
9. near matches may use criterion-specific, explainable boundary distance where such distance is semantically valid;
10. categorical mismatches do not receive invented universal percentage distances;
11. HullQ does not expose a single opaque generic match percentage as the primary explanation of ranking;
12. every ranking decision must remain compatible with criterion-level explanation and deterministic/versioned behavior.

## 11. Deferred details

This decision does not yet freeze:

- final UI wording for the two preference tiers;
- exact numerical weights between the two tiers;
- exact tie-breaker sequence;
- exact evidence-coverage formula within `POTENTIAL`;
- exact multi-failure near-match ranking formula;
- pagination interaction with ranking;
- market-specific freshness/relevance signals;
- API representation of ranking explanations.

Those details must preserve the accepted baseline above.
