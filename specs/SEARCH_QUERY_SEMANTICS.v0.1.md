# HullQ — Search Query Semantics

**Version:** 0.1  
**Status:** ACCEPTED  
**Decision:** resolves OQ-009 D1–D10 accepted by the Project Owner on 2026-08-28/29  
**Scope:** deterministic query truth semantics; not public URL/SEO policy (OQ-018), market geography (OQ-020), auth (OQ-014), public API versioning (OQ-015), listing dedup (OQ-005) or alert cadence (OQ-006).

## 1. Core truth model

Each required criterion evaluates to exactly one semantic truth state:

- `TRUE` — criterion confirmed;
- `FALSE` — criterion contradicted;
- `UNKNOWN` — criterion cannot be established from sufficiently qualified data.

Query-level product outcomes are:

- `CONFIRMED_MATCH`;
- `CONFIRMED_NON_MATCH`;
- `INSUFFICIENT_DATA`.

Unknown is neither match nor non-match. HullQ MUST prefer fewer valid results over false results.

For an AND expression:

- any `FALSE` => `FALSE`;
- all `TRUE` => `TRUE`;
- otherwise => `UNKNOWN`.

For an OR expression:

- any `TRUE` => `TRUE`;
- all `FALSE` => `FALSE`;
- otherwise => `UNKNOWN`.

Negation preserves three-valued semantics:

- `NOT TRUE = FALSE`;
- `NOT FALSE = TRUE`;
- `NOT UNKNOWN = UNKNOWN`.

`UNKNOWN` MUST never be coerced to `TRUE` merely to preserve recall.

## 2. Reason codes

At minimum, criterion evaluation MUST be able to expose these reasons where applicable:

- `VALUE_MISSING`;
- `UNRESOLVED_CONFLICT`;
- `APPLICABILITY_UNKNOWN`;
- `NOT_APPLICABLE`;
- `PROVISIONAL_VALUE`;
- `CONFIGURATION_AMBIGUOUS`;
- `RANGE_OVERLAPS_THRESHOLD`.

`VALUE_MISSING`, `UNRESOLVED_CONFLICT`, `APPLICABILITY_UNKNOWN`, `PROVISIONAL_VALUE`, `CONFIGURATION_AMBIGUOUS` and `RANGE_OVERLAPS_THRESHOLD` yield `UNKNOWN` for a required criterion.

For a criterion that requires applicability, `NOT_APPLICABLE` is a confirmed exclusion (`FALSE`), not an insufficient-data state. Negation MUST NOT turn a not-applicable value into a confirmed match through a double-negation loophole.

## 3. Qualified values only

Only fully qualified canonical or derived values MAY determine confirmed query truth.

A source-backed canonical value with accepted/current resolution may produce `TRUE` or `FALSE`.
A derived value with status `computed` may produce `TRUE` or `FALSE`.
A derived value with status `computed_provisional` MUST NOT by itself produce confirmed inclusion or confirmed exclusion.

Missing, provisional, conflicting, applicability-unknown or otherwise unresolved values are not truth-final.

Search consumes accepted canonical/resolution/derived status. It MUST NOT invent a separate hidden source-trust ranking.

## 4. Primary result set and insufficient-data discovery

Only `CONFIRMED_MATCH` belongs to the primary result set and primary match count.

`INSUFFICIENT_DATA` records MAY be exposed in a clearly separate discovery surface, for example “boats that could not be fully evaluated”. They MUST NOT be counted or presented as matches.

A UI preference to show/hide that secondary surface is view state, not query semantics. It MUST NOT rewrite a criterion to `criterion OR NULL`.

Normal match alerts are based on confirmed matches only. If later evidence changes an item from insufficient-data to confirmed-match, that later confirmed match may trigger the normal match path.

## 5. MUST and PREFER

Query criteria have explicit requirement strength:

- `MUST` determines membership in the valid result set;
- `PREFER` influences ranking only among already-confirmed matches.

HullQ MUST NEVER silently relax a `MUST` into a preference.

A `PREFER` criterion may evaluate `SATISFIED`, `NOT_SATISFIED` or `UNKNOWN`. An unknown preference does not invalidate a design whose MUST expression is confirmed true.

Normal filter controls default to `MUST` unless the user explicitly marks a criterion as a preference/nice-to-have. Requirement strength is part of persisted query semantics.

## 6. Numeric comparison

Numeric hard filters compare canonical values against canonicalized query thresholds.

Boundaries are inclusive by default:

- minimum => `value >= threshold`;
- maximum => `value <= threshold`;
- range => `minimum <= value <= maximum`.

User-entered units MUST be deterministically converted to the canonical unit before comparison. Display rounding MUST NOT alter query truth.

No implicit epsilon, fuzzy boundary or hidden tolerance may change a required criterion.

“Around” semantics, when offered, require an explicit deterministic tolerance and SHOULD normally be represented as a preference rather than a hard requirement.

Derived metrics use their accepted canonical precision rules; the search layer MUST NOT introduce an additional hidden tolerance.

## 7. Configuration-aware and range-safe evaluation

Option-sensitive criteria are evaluated against explicit resolved configurations rather than silently flattening alternatives into a BoatDesign baseline.

A BoatDesign may be discoverable when at least one verified factory configuration satisfies all required criteria, but HullQ MUST identify the matching configuration and MUST NOT imply that all configurations match.

A concrete market listing is a confirmed match only when its applicable configuration is sufficiently resolved. Otherwise an option-sensitive required criterion yields `UNKNOWN`, normally with `CONFIGURATION_AMBIGUOUS`.

For a bounded value range:

- confirm `TRUE` only when the entire known range satisfies the required criterion;
- confirm `FALSE` only when the entire known range contradicts it;
- otherwise yield `UNKNOWN` with `RANGE_OVERLAPS_THRESHOLD`.

## 8. Explicit boolean query structure

Compound queries use an explicit expression tree. AND/OR grouping MUST be represented in the query contract; the system MUST NOT infer ambiguous implicit grouping.

Example:

`(keel = full OR rudder = skeg) AND draft <= 1.8 m`

Leaf criteria evaluate to `TRUE`, `FALSE` or `UNKNOWN`; compound expressions reduce using the truth tables in section 1.

Advanced whole-group negation may be added later only if it preserves the same three-valued semantics. This specification does not require a public UI for arbitrary boolean expressions in v0.1.

## 9. Ranking

Confirmed matches may be ordered only by:

- explicit user sort choices; or
- explainable, versioned query-related signals / satisfied preferences.

General data completeness MUST NOT silently mean “better boat”. Source prestige, model popularity or fame MUST NOT secretly rank confirmed matches.

If the user expresses no ranking preference beyond hard criteria, HullQ MUST NOT invent an opaque generic quality score.

Within the separate insufficient-data group, evaluability/data completeness MAY be used to order items because that ordering means “closest to evaluable”, not “better boat”.

## 10. Explainability and persistence

Evaluation MUST preserve enough criterion-level metadata to explain why a result was confirmed, contradicted or insufficient.

The actual query expression, requirement strength and deterministic thresholds are persistent product semantics independent of transient UI state so the same query can later be saved, reloaded and monitored.

## 11. Initial implementation boundary

The first product implementation MAY implement only the minimal subset needed for an end-to-end trustworthy search vertical slice, provided it does not weaken these semantics.

The preferred first subset is:

- numeric `MUST` criteria;
- explicit AND aggregation;
- inclusive min/max/range comparisons;
- canonical-unit comparisons;
- qualified-value gating;
- criterion reasons;
- separate confirmed-match / insufficient-data outputs;
- deterministic serializable query representation.

PREFER, arbitrary OR/NOT UI, full configuration expansion, public HTTP/API versioning, public frontend/SEO behavior and market geography may follow in later product increments under their controlling decisions.

## 12. Practical re-evaluation

The Project Owner explicitly requires the strict fail-closed semantics to be reviewed again after a practical search run/benchmark. Until empirical evidence justifies an explicit change, this specification remains binding.
