# ADR-0008 — Versioned Derived-Metric Methodology

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Decision:** OQ-001

## Context

HullQ intends to calculate several familiar yacht-design ratios plus a legacy hull-speed estimate rather than trusting externally copied derived values. The historical formulas are well known, but reproducibility depends on more than the formula text: unit conversion, load-state meaning, sail-area basis, hull-type applicability, rounding, missing/conflicting inputs and derivation lineage all affect the result.

The current accepted BoatDesign contract contains `displacement_kg` and `sail_area_m2` without explicit calculation-basis metadata, and the draft ResolvedConfiguration groups Hull Speed under `derived_ratios` even though it is not a ratio.

## Decision

Adopt `specs/DERIVED_METRICS_SPEC.v1.0.md` as HullQ Derived Metrics methodology `hullq-derived-1.0.0`.

Specifically:

1. keep physical canonical source values in SI;
2. evaluate legacy yacht formulas according to their traditional Imperial definitions after deterministic conversion;
3. add explicit displacement/sail-area basis metadata;
4. permit provisional calculations when source basis is unknown/unspecified rather than destroying broad coverage, while preserving the provisional status;
5. reject nonstandard loaded/sail-plan bases from the single canonical v1 metric slot;
6. treat Ballast/Displacement, Brewer Comfort Ratio, CSF and legacy Hull Speed as monohull-only in v1;
7. allow SA/D and D/L for monohulls, catamarans and trimarans but prohibit implied cross-type equivalence;
8. rename the draft projection `derived_ratios` to `derived_metrics`;
9. store direct numeric metrics plus parallel machine-readable statuses;
10. create DerivationRecords for populated derived values;
11. quantize canonical outputs to six decimals using round-half-even;
12. prohibit opaque safety/“bluewater” conclusions from these metrics.

## Consequences

### Positive

- calculations become reproducible and versioned;
- HullQ remains compatible with established yacht-ratio definitions;
- load/sail-area ambiguity is no longer silently hidden;
- broad-coverage records may still provide explicitly provisional metrics;
- multihulls are not forced into monohull-specific heuristics;
- queryable numeric fields stay simple while calculation status remains explicit;
- future corrected methodologies can coexist by version.

### Negative

- BoatDesign requires a schema revision to carry ratio-input basis;
- some records that currently expose a generic sail-area number will not qualify for an unqualified SA/D result;
- OQ-009 must later decide how provisional results affect search matching;
- a future multi-profile metric model may be needed for loaded-vs-lightship comparisons.

## Rejected alternatives

### Copy source-published ratios

Rejected because formula/input semantics differ across sources and provenance would not imply methodological consistency.

### Require perfect input-basis knowledge before any calculation

Rejected because it conflicts with HullQ's broad-coverage/progressive-depth strategy and would create excessive null coverage. Provisional status preserves uncertainty without fabricating certainty.

### Treat every load state and sail plan as one canonical value

Rejected because it silently mixes non-comparable inputs.

### Compute monohull heuristics for multihulls anyway

Rejected in v1 because a mathematically computable number can still be product-semantically misleading.

## Acceptance evidence

OQ-001 was explicitly accepted by the project owner on 2026-08-18.

Closure evidence:

- JSON Schemas validate under Draft 2020-12;
- golden formula fixtures pass;
- status/negative fixtures pass;
- BoatDesign v0.4 and ResolvedConfiguration v0.2 validate;
- requirements, schema status, project state, traceability and changelog were reconciled.
