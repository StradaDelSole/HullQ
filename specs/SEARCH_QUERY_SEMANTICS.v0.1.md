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

Query-level product outcomes are `CONFIRMED_MATCH`, `CONFIRMED_NON_MATCH` and `INSUFFICIENT_DATA`.

Unknown is neither match nor non-match. HullQ MUST prefer fewer valid results over false results.

AND: any FALSE => FALSE; all TRUE => TRUE; otherwise UNKNOWN.
OR: any TRUE => TRUE; all FALSE => FALSE; otherwise UNKNOWN.
NOT: TRUE => FALSE; FALSE => TRUE; UNKNOWN => UNKNOWN.

UNKNOWN MUST never be coerced to TRUE merely to preserve recall.

## 2. Reason codes

At minimum the evaluator MUST be able to expose, where applicable:

- `VALUE_MISSING`
- `UNRESOLVED_CONFLICT`
- `APPLICABILITY_UNKNOWN`
- `NOT_APPLICABLE`
- `PROVISIONAL_VALUE`
- `CONFIGURATION_AMBIGUOUS`
- `RANGE_OVERLAPS_THRESHOLD`

All except `NOT_APPLICABLE` yield UNKNOWN for a required criterion. For a criterion requiring applicability, `NOT_APPLICABLE` is confirmed exclusion/FALSE, not insufficient data. Negation MUST NOT turn not-applicable into a confirmed match through a double-negation loophole.

## 3. Qualified values only

Only fully qualified canonical or derived values MAY determine confirmed truth.

A source-backed canonical value with accepted/current resolution may produce TRUE or FALSE. A derived value with status `computed` may produce TRUE or FALSE. A `computed_provisional` derived value MUST NOT by itself produce confirmed inclusion or confirmed exclusion.

Missing, provisional, conflicting, applicability-unknown or otherwise unresolved values are not truth-final. Search consumes accepted canonical/resolution/derived status and MUST NOT invent a hidden source-trust ranking.

## 4. Result surfaces

Only `CONFIRMED_MATCH` belongs to the primary result set and primary match count.

`INSUFFICIENT_DATA` records MAY be exposed in a clearly separate discovery surface and MUST NOT be counted or presented as matches. Showing/hiding that surface is view state, not query semantics, and MUST NOT rewrite a criterion as `criterion OR NULL`.

Normal match alerts are based on confirmed matches only. A later evidence change from insufficient-data to confirmed-match may enter the normal match path.

## 5. MUST and PREFER

`MUST` determines membership in the valid result set. `PREFER` influences ranking only among already-confirmed matches. HullQ MUST NEVER silently relax a MUST into a preference.

A preference may be SATISFIED, NOT_SATISFIED or UNKNOWN. Unknown preference data does not invalidate a design whose MUST expression is confirmed true. Normal filter controls default to MUST unless the user explicitly chooses preference/nice-to-have. Requirement strength is persistent query semantics.

## 6. Numeric comparison

Numeric hard filters compare canonical values against canonicalized query thresholds. Boundaries are inclusive by default:

- minimum => `value >= threshold`
- maximum => `value <= threshold`
- range => `minimum <= value <= maximum`

User-entered units MUST be deterministically converted to canonical units before comparison. Display rounding MUST NOT alter query truth. No implicit epsilon, fuzzy boundary or hidden tolerance may change a required criterion. “Around” requires explicit deterministic tolerance and SHOULD normally be represented as a preference.

## 7. Configuration-aware and range-safe evaluation

Option-sensitive criteria are evaluated against explicit resolved configurations rather than silently flattening alternatives into a BoatDesign baseline.

A BoatDesign may be discoverable when at least one verified factory configuration satisfies all required criteria, but HullQ MUST identify the matching configuration and MUST NOT imply that all configurations match. A concrete market listing is a confirmed match only when its applicable configuration is sufficiently resolved; otherwise the relevant required criterion is UNKNOWN, normally `CONFIGURATION_AMBIGUOUS`.

For a bounded value range: TRUE only when the entire range satisfies; FALSE only when the entire range contradicts; otherwise UNKNOWN with `RANGE_OVERLAPS_THRESHOLD`.

## 8. Explicit boolean structure

Compound queries use an explicit expression tree. AND/OR grouping MUST be represented in the query contract; the system MUST NOT infer ambiguous grouping. Leaves evaluate TRUE/FALSE/UNKNOWN and groups reduce using section 1.

Advanced whole-group negation may be added later only while preserving these semantics. This spec does not require a public arbitrary-boolean UI in v0.1.

## 9. Ranking

Confirmed matches may be ordered only by explicit user sort choices or explainable/versioned query-related signals and satisfied preferences.

General data completeness MUST NOT silently mean “better boat”. Source prestige, model popularity or fame MUST NOT secretly rank confirmed matches. If no ranking preference exists beyond hard criteria, HullQ MUST NOT invent an opaque generic quality score.

Within the separate insufficient-data group, evaluability/data completeness MAY order records because that means “closest to evaluable”, not “better boat”.

## 10. Explainability and persistence

Evaluation MUST preserve criterion-level metadata sufficient to explain why an item was confirmed, contradicted or insufficient. The query expression, requirement strength and deterministic thresholds are persistent semantics independent of transient UI state so the same query can later be saved, reloaded and monitored.

## 11. Initial implementation boundary

The first implementation MAY implement only the minimum trustworthy vertical slice, provided it does not weaken this spec. Preferred first subset:

- numeric MUST criteria
- explicit AND aggregation
- inclusive min/max/range comparisons
- canonical-unit comparisons
- qualified-value gating
- criterion reason metadata
- separate confirmed-match / insufficient-data outputs
- deterministic serializable query representation

PREFER, arbitrary OR/NOT UI, full configuration expansion, public HTTP/API versioning, public frontend/SEO behavior and market geography may follow under their controlling decisions.

## 12. Practical re-evaluation

The Project Owner requires these strict fail-closed semantics to be reviewed again after a practical search run/benchmark. Until empirical evidence justifies an explicit change, this specification remains binding.
