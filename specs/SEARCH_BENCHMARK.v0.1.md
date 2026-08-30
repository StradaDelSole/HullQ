# HullQ — Practical Search Benchmark

**Version:** 0.1  
**Status:** ACCEPTED  
**Decision basis:** Project Owner decisions TB-01 D1–D10, completed 2026-08-30  
**Scope:** first locked practical search benchmark for canonical BoatDesign technical profiles and OQ-009 re-evaluation

## 1. Purpose

This benchmark tests whether HullQ's strict search-truth semantics remain practically useful when run against a small real, provenance-backed BoatDesign corpus.

It is deliberately designed to prevent query overfitting and corpus overfitting:

> Benchmark queries are fixed before final corpus results are known.

A weak or inconvenient result does not authorize changing the benchmark after the fact.

## 2. Locked primary query suite

The following ten queries are the `PRIMARY` benchmark suite. They MUST NOT be rewritten, re-thresholded, replaced or silently relaxed after lock. Later additive queries may be introduced only as `SECONDARY` and MUST remain analytically separate from the original suite.

### USER_INTENT

Q1. `LOA 8–11 m AND Draft <= 1.80 m`

Q2. `LOA 9–12 m AND Beam <= 3.60 m AND Draft <= 2.00 m`

Q3. `Displacement >= 4,000 kg AND LOA <= 12 m`

Q4. `Masthead rig AND Draft <= 1.80 m`

Q5. `Aft cockpit AND Fin keel AND Draft <= 1.70 m`

Q6. `Skeg-supported rudder AND LOA 9–12 m`

Q7. `Center cockpit AND Draft <= 1.80 m`

Q8. `Cutter AND Skeg-supported rudder`

These are intended to represent plausible real technical buyer searches. Specialized does not mean artificial: a technically informed user may legitimately search by cockpit, rig, keel or rudder support.

### SYSTEM_CHALLENGE

Q9. `Center cockpit AND Cutter AND Skeg-supported rudder AND Draft <= 1.80 m`

Q10. `Draft <= 1.60 m`

Q9 deliberately stresses compound categorical + numeric truth. Q10 is intentionally simple in visible syntax but is configuration-aware: a design with standard/deep/shallow alternatives MUST be evaluated through explicit resolved configurations rather than a design-wide averaged or arbitrary draft.

## 3. Query roles and lock classes

Every benchmark query carries both:

- `role`: `USER_INTENT` or `SYSTEM_CHALLENGE`;
- `lock_class`: `PRIMARY` or `SECONDARY`.

The ten queries in §2 are all `PRIMARY`.

`USER_INTENT` evaluates practical product usability. `SYSTEM_CHALLENGE` evaluates semantic robustness under configuration, compound-filter and uncertainty pressure. These roles MUST be reported separately; strong USER_INTENT usability cannot compensate for semantic failure on SYSTEM_CHALLENGE cases.

## 4. Locked benchmark corpus

The v0.1 benchmark corpus consists of twelve BoatDesigns:

1. Rustler 36
2. Contessa 32
3. Bavaria Cruiser 34
4. Sun Odyssey 36i
5. Albin Vega
6. Rival 34
7. Najad 451 CC — primary diversity slot `CENTER_COCKPIT`
8. Lagoon 42 — primary diversity slot `MULTIHULL`
9. Beneteau Oceanis 30.1 — primary diversity slot `MOVABLE_APPENDAGE`
10. AMEL Super Maramu — primary diversity slot `ALTERNATIVE_RIG`
11. Hallberg-Rassy 400 — primary diversity slot `TWIN_RUDDER`
12. Sirius 35 DS — primary diversity slot `DECK_SALOON`

The six diversity controls were selected for structural diversity, footprint and realistic canonicalizability, not to manufacture desired benchmark matches.

A locked corpus member MUST NOT be replaced merely because research becomes difficult, sparse, rights-blocked, applicability-ambiguous or conflict-heavy. Replacement requires a genuine hard exclusion such as wrong identity or inability to establish any permissible source basis, and the original candidate plus replacement reason MUST be retained in the benchmark record.

## 5. Canonical field admission

Benchmark truth consumes field-level canonical/resolved data, not source count or whole-profile confidence.

Rules:

1. In the conflict-free normal case, one sufficiently authoritative, rights-cleared, applicability-matched source MAY confirm a field.
2. Applicability is assessed before conflict. Different design/configuration/spec-epoch/measurement scopes produce an applicability split, not a same-scope conflict.
3. A true same-scope conflict becomes `UNRESOLVED_CONFLICT` and follows the accepted 6/8-eye confirmation protocol in `TECHNICAL_PROFILE_SPEC.v0.1.md`.
4. Independence is evaluated by information lineage, not document count.
5. `UNKNOWN` is a valid retained outcome. A BoatDesign is not removed merely because a field cannot be confirmed.
6. Negative structural assertions require positive evidence. Absence of mention does not prove `count=0`, `skeg=none`, `mast_count=1`, `cockpit_count=1`, etc.
7. Whole-profile status/coverage is diagnostic only and MUST NOT alter search truth or ranking.
8. A known conflict, weak-only evidence or unresolved applicability MUST NOT be converted into a confirmed value merely to improve benchmark evaluability.

## 6. Research passes

The corpus is researched breadth-first in three bounded passes.

### Pass 1 — P0 Search Coverage

Across all twelve BoatDesigns, resolve the search-defining fields needed by the Technical Profile contract, including at least:

- hull configuration/count;
- LOA;
- beam;
- draft / draft options;
- keel;
- centerboard/daggerboard;
- rudder position/support/count;
- skeg;
- cockpit position/count;
- sailplan;
- masthead/fractional character;
- mast count.

Every researched P0 field ends the pass in an explicit state such as `CONFIRMED`, `UNKNOWN`, `UNRESOLVED_CONFLICT`, `APPLICABILITY_UNKNOWN` or `NOT_APPLICABLE`. An unresolved field does not block progress to the next field/design.

Run **Snapshot A** after all twelve designs have completed the P0 pass.

### Pass 2 — P1 Technical Depth

After all twelve have a P0 pass, research P1 breadth-first, including LWL, displacement, ballast, sail area, I/J/P/E, construction and other Technical Depth fields needed for comparison/derived value quality.

Run **Snapshot B** after all twelve designs have completed the P1 pass.

### Pass 3 — Targeted closure

Prioritize:

1. unresolved P0 conflicts;
2. P0 applicability problems;
3. P0 UNKNOWN values blocking benchmark evaluability;
4. unresolved P1 conflicts;
5. remaining P1 gaps;
6. P2/P3 enrichment only after the above.

Run the final v0.1 benchmark after this targeted pass.

## 7. Suggested research waves

The wave order is operational only; all twelve designs remain mandatory.

**Wave 1:** Bavaria Cruiser 34; Contessa 32; Beneteau Oceanis 30.1; Lagoon 42.

**Wave 2:** Sun Odyssey 36i; Hallberg-Rassy 400; Najad 451 CC; Sirius 35 DS.

**Wave 3:** Rustler 36; Albin Vega; Rival 34; AMEL Super Maramu.

## 8. Metrics

The benchmark reports six core metrics.

### M1 — Query Result Distribution

Per query:

- `confirmed_match_count`;
- `confirmed_non_match_count`;
- `insufficient_data_count`;
- corpus size.

### M2 — Evaluability Rate

`(CONFIRMED_MATCH + CONFIRMED_NON_MATCH) / corpus_size`

Zero matches is not inherently failure. A query with zero matches and twelve confirmed non-matches is fully evaluable.

### M3 — Insufficient Reason Distribution

Track reasons including where applicable:

- `VALUE_MISSING`;
- `UNRESOLVED_CONFLICT`;
- `APPLICABILITY_UNKNOWN`;
- `PROVISIONAL_VALUE`;
- `CONFIGURATION_AMBIGUOUS`;
- `RANGE_OVERLAPS_THRESHOLD`.

### M4 — Blocking Field Frequency

Report which fields most often prevent evaluability, e.g. cockpit position, rig fraction, rudder support or draft applicability.

### M5 — Configuration Resolution Rate

For configuration-sensitive evaluation report:

- configuration resolved;
- configuration ambiguous;
- not configuration-sensitive.

A confirmed BoatDesign match MUST identify at least one matching configuration; the engine MUST NOT silently infer that every configuration matches.

### M6 — Coverage Gain by Research Pass

Compare Snapshot A, Snapshot B and final targeted closure to measure the marginal search utility of deeper research.

## 9. Semantic-integrity hard gate

The benchmark hard invariant is:

`FALSE_CONFIRMED_RESULT = 0`

A known `UNKNOWN`, `UNRESOLVED_CONFLICT`, `PROVISIONAL_VALUE`, `APPLICABILITY_UNKNOWN` or `CONFIGURATION_AMBIGUOUS` case MUST NOT become confirmed match or confirmed non-match where the accepted three-valued semantics require insufficient data.

High match rate is not a success metric. Source count and generic profile completeness are not quality proxies. Classic ML precision/recall MUST NOT be reported unless a genuinely independent ground-truth label set exists.

## 10. Report structure

Every benchmark snapshot separates:

### PRODUCT_UTILITY

- evaluability;
- result distribution;
- blocking fields;
- P0→P1→Final coverage/evaluability gain.

### SEMANTIC_INTEGRITY

- insufficient-reason correctness;
- configuration-resolution correctness;
- conflict/applicability handling;
- `FALSE_CONFIRMED_RESULT`.

## 11. OQ-009 re-evaluation

Benchmark results may produce one of four conclusions:

1. `IMPLEMENTATION_FAIL` — false confirmed truth exists. Fix implementation; do not relax semantics.
2. `KEEP_STRICT` — truth behavior is sound and insufficiency is primarily a data/applicability/conflict problem.
3. `KEEP_TRUTH_CHANGE_UX` — truth behavior is sound but product presentation/discovery needs improvement; separate insufficient/possible-candidate UX may evolve without mixing it into confirmed results.
4. `OPEN_SEMANTICS_REVIEW` — a specific accepted semantic rule appears to cause material, repeatable USER_INTENT product loss even with strong applicability-matched evidence.

Low evaluability alone is never evidence that HullQ's truth semantics are too strict.

A semantics review requires a systematic issue affecting at least two PRIMARY USER_INTENT queries and at least three independent BoatDesigns, and it must not be primarily explained by missing evidence, unresolved conflicts, applicability ambiguity or incomplete configuration research. This is a review trigger, not an automatic rule change.

The twelve-design v0.1 corpus alone MUST NOT authorize a normative Truth-Semantics change. Any proposed change requires a larger independent validation set, explicit/versioned semantics, rerunning the original locked PRIMARY suite and retaining the zero-false-confirmed invariant or explicitly creating a separate non-confirmed query mode.

## 12. Explicit non-goals

This benchmark does not:

- weaken `SEARCH_QUERY_SEMANTICS.v0.1.md` before evidence exists;
- turn insufficient records into matches;
- authorize SailboatData/reference values as canonical truth;
- require all twelve profiles to be complete;
- define public API/URL/SEO behavior;
- define market-listing geography, dedup, monitoring, auth or pricing;
- create a hidden boat quality/seaworthiness score.
