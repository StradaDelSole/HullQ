# SLICE-0031 — Corrected Tier-1 Evidence Profile + Positive-Control Candidate Selection

**ID:** SLICE-0031  
**Type:** VALIDATION  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0030 owner-accepted / DONE (Project Owner acceptance recorded on PR #87, issue comment `5446772597`)  
**Blocks:** an evidence-based choice of the next bounded BoatDesign/applicability positive-control pilot and any trustworthy use of the corrected SLICE-0030 full-boundary Tier-1 evidence as a calibration input

## Objective

Measure, fully offline and over the exact accepted 1,770-canonical-BoatModel boundary, what the SLICE-0030 mass-unit correction actually changes at the **BoatModel evidence-maturity/profile level**, then deterministically identify a small technically strong candidate pool for a later separately readied BoatDesign/applicability positive-control pilot.

SLICE-0028 retained the following explicitly non-canonical evidence precursor:

```text
LOA + beam + (draft OR displacement) normalized-candidate evidence
607 / 1,770 BoatModels = 34.2938%
```

At that time displacement normalization was severely suppressed by the Wikidata mass-unit QID defect. SLICE-0030 corrected that defect and measured displacement normalized-candidate coverage changing from:

```text
66 -> 858
```

while LOA/LWL/beam/draft remained unchanged.

The project must now quantify the resulting **joint per-BoatModel evidence profile**, not infer it from marginal field totals. In particular, 858 displacement candidates do not imply that all of them add new BoatModels to the earlier 607-model precursor; overlap with draft/LOA/beam must be measured from the retained evidence.

This slice therefore answers two bounded questions:

1. What is the exact corrected full-boundary Tier-1 evidence-maturity distribution after SLICE-0030, including the updated value of the same SLICE-0028 basic-searchable evidence precursor?
2. Which already-canonical BoatModels form the strongest deterministic technical candidate pool for a later **positive-control BoatDesign/applicability research pilot**, without yet performing that research or promoting any canonical technical value?

This is a validation/selection slice only. It does **not** create BoatDesigns, FieldResolutions, canonical technical values, launch-readiness claims or a query engine.

## Why this slice is next

SLICE-0029 correctly demonstrated on Catalina 22 / Catalina 30 that BoatModel-scoped Wikidata technical candidates cannot be promoted merely because values exist. The accepted result was:

```text
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

SLICE-0030 then fixed a separate deterministic adapter defect and increased normalized displacement evidence by +792 BoatModels without changing the other four Tier-1 fields.

The next decision should therefore not be another arbitrary manufacturer research attempt and should not be premature canonical promotion. The highest-information low-risk step is to use the now-corrected retained evidence to identify where the strongest technical positive controls actually are.

The accepted database strategy is breadth first with progressive depth: broad canonical identity, then basic searchable evidence, then HullQ-critical enrichment and deeper verification. This slice measures the current evidence layer and prepares the next bounded depth step without confusing evidence availability with canonical searchability.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `CLAUDE.md`;
- `docs/slices/SLICE-0030-acceptance-closure.md` plus Project Owner acceptance on PR #87;
- `research/stage3/sl0030-wikidata-mass-unit-correction/` as the corrected/current five-field evidence result and integrity-verified input;
- `docs/slices/SLICE-0028-acceptance-closure.md` and `research/stage3/sl0028-wikidata-tier1-full-boundary/` only to reproduce the predecessor precursor and fixed linkage/raw-evidence boundary;
- `docs/slices/SLICE-0029-acceptance-closure.md` only for the preserved BoatModel-vs-BoatDesign applicability boundary and the two Catalina negative-control outcomes;
- `docs/DATABASE_COVERAGE_STRATEGY.md` for the breadth/progressive-depth interpretation;
- accepted identity/provenance contracts only where necessary to prevent overclaim.

Do not preload unrelated frontend, SEO, marketplace, account, alert, pricing, monetization or query-engine documents.

## Evidence/reporting law

All completion-report claims must be backed by executed deterministic computation, retained artifacts, repository state or observed CI results.

- Do not infer joint BoatModel coverage from marginal field counts.
- Do not call evidence "canonical", "searchable production data" or "launch-ready" merely because a normalized candidate exists.
- Do not use labels, popularity, personal familiarity or external source reputation to choose positive-control candidates.
- Do not perform live web/manufacturer/Wikidata acquisition in the primary analysis path.
- Do not reinterpret SLICE-0029's negative applicability result.
- If accepted retained inputs fail verification or the fixed identity boundary drifts, stop `BLOCKED`.
- The implementation agent's report is not independent review and does not make the slice `DONE`.

## Fixed input boundary

Use exactly the already-accepted retained evidence boundary:

```text
canonical BoatModels             1,770
canonical acquisition QIDs        1,770
historical QID -> HullQ mappings  1,772
```

The two non-canonical historical reserved mappings remain excluded exactly as in SLICE-0028/0030.

Before any derived profile is created:

1. offline-verify the accepted SLICE-0028 retained package;
2. offline-verify the accepted SLICE-0030 retained package;
3. reproduce the exact canonical QID -> BoatModel linkage and fail closed on any missing, unexpected or duplicate canonical linkage;
4. confirm that the corrected/current extraction path reproduces the accepted SLICE-0030 five-field after-state.

No discovery query and no reacquisition of the 1,770 Wikidata entities is permitted.

## Fixed field boundary

The profile is limited to exactly the existing five Tier-1 field pointers:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

Do not add ballast, sail area, material, rig, keel/rudder/skeg or year fields merely to improve candidate ranking. Those belong to later enrichment/readiness decisions.

## Corrected evidence-profile requirements

For every one of the 1,770 canonical BoatModels, derive a deterministic profile from the accepted corrected/current evidence containing at minimum:

- canonical `hullq_id`;
- accepted Wikidata QID(s) from the fixed canonical linkage;
- for each of the five fixed fields, the strongest-available **evidence coverage state** already defined by the accepted SLICE-0026/0028 path;
- boolean `normalized_candidate_present` for each of the five fields;
- `normalized_field_count` in the closed range 0..5;
- whether the model satisfies the exact predecessor precursor condition `LOA + beam + (draft OR displacement)`;
- whether both draft and displacement have normalized candidates;
- whether the model has any retained SLICE-0028/0030 disagreement/unsupported-coexistence diagnostic relevant to the five fixed fields, where deterministically available from the accepted retained evidence;
- no canonical-value or FieldResolution assertion.

The profile must be reconstructed from accepted retained evidence, not from a copied manually authored list.

## Required aggregate measurements

Retain exact counts and percentages for at least:

### Per-field corrected coverage

The corrected/current five-field normalized-candidate totals must reproduce the accepted SLICE-0030 result before any new interpretation is made.

Expected accepted reference values, to be verified rather than trusted blindly:

```text
LOA            888
LWL            848
beam           891
draft          691
displacement   858
```

### Normalized-field-count distribution

Count BoatModels with exactly:

```text
0 / 1 / 2 / 3 / 4 / 5
```

normalized candidates across the five fixed fields.

Also retain cumulative counts for:

```text
>= 3 fields
>= 4 fields
all 5 fields
```

### Corrected predecessor precursor

Recompute exactly:

```text
LOA + beam + (draft OR displacement)
```

at BoatModel level under the corrected SLICE-0030 evidence path.

Retain:

- accepted predecessor count: `607 / 1770`;
- corrected count;
- exact absolute delta;
- exact percentage-point delta;
- overlap decomposition showing how many precursor-positive models are supported by:
  - draft only;
  - displacement only;
  - both draft and displacement.

Do not assume the corrected precursor count in the readiness document; measure it.

### Strong technical-evidence subsets

Retain counts for at least:

- LOA + beam + draft + displacement;
- LOA + LWL + beam + (draft OR displacement);
- all five fixed fields;
- `>=4/5` normalized fields with no relevant retained disagreement diagnostic.

These are evidence diagnostics, not new production coverage definitions.

## Positive-control candidate-pool selection

Create one deterministic ranked candidate pool of **at most 20** already-canonical BoatModels for a later separately readied BoatDesign/applicability positive-control pilot.

### Eligibility

A BoatModel is eligible only when all of the following are true:

1. it is within the exact accepted 1,770 canonical BoatModel boundary;
2. it satisfies `LOA + beam + (draft OR displacement)` under the corrected/current evidence path;
3. it has at least **4 of the 5** fixed fields as normalized candidates;
4. it has no retained disagreement/unsupported-coexistence diagnostic on the normalized fields used to establish eligibility;
5. it is not either of the already-researched SLICE-0029 Catalina negative-control QIDs:
   - `Q5051252` Catalina 22;
   - `Q5051253` Catalina 30.

This exclusion prevents the selection slice from simply returning the already-known negative controls as the next positive-control candidates.

### Ranking

Rank eligible candidates deterministically by the following ordered keys only:

1. `normalized_field_count` descending;
2. both draft **and** displacement normalized before only one of them;
3. LWL normalized before LWL missing;
4. canonical `hullq_id` ascending as the final stable tie-break.

Do not rank by model fame, manufacturer reputation, web-search convenience, presumed source availability or agent preference.

Retain the first 20 eligible candidates, or all eligible candidates if fewer than 20 exist.

The retained candidate pool is **not** authorization to research all 20 externally. A later readiness decision may choose a much smaller bounded subset after explicitly defining its source/right/retrieval boundary.

## Candidate-pool interpretation

The slice must report whether the fixed selection rule produced:

```text
POSITIVE_CONTROL_POOL_AVAILABLE
NO_POSITIVE_CONTROL_POOL
```

Use only this mechanical rule:

- `POSITIVE_CONTROL_POOL_AVAILABLE` when at least one BoatModel satisfies every eligibility rule above;
- `NO_POSITIVE_CONTROL_POOL` when zero BoatModels satisfy them.

Do not invent an arbitrary minimum pool size merely to obtain a preferred result.

A positive pool means only that technically strong BoatModel-scoped evidence exists for later applicability research. It does not mean any selected model has a proven BoatDesign generation boundary, a cleared primary source or a promotable canonical value.

## CAL-01 / launch-threshold boundary

The accepted SLICE-0028 closure explicitly stated that its 607/1,770 precursor was **not** CAL-01 D2 canonical basic-searchable coverage and did not resolve the pending D2b threshold.

SLICE-0030 likewise did not decide whether the improved displacement evidence should change CAL-01 D2b planning.

SLICE-0031 may therefore retain the corrected evidence measurements as a **calibration input**, but it MUST NOT:

- relabel normalized research evidence as canonical basic-searchable coverage;
- declare the D2/D2b launch threshold met;
- declare G4 passed;
- invent or silently freeze a launch percentage threshold;
- treat the evidence precursor as a substitute for BoatDesign applicability + FieldResolution/canonical promotion.

If an authoritative CAL-01 artifact is required to make a stronger decision and is not part of the accepted controlling artifacts, report the calibration decision as deferred rather than inventing missing semantics.

## Canonical mutation boundary

SLICE-0031 must create/mutate **zero** canonical production identities or technical values.

Specifically prohibited:

- minting a BoatDesign ID;
- inserting/updating a canonical BoatDesign row;
- modifying a canonical BoatModel row;
- creating a FieldResolution;
- writing any canonical baseline technical value;
- creating DesignOption/NamedVariant canonical entities;
- changing the 1,770 / 1,772 accepted identity boundary;
- changing Wikidata adapter semantics already accepted in SLICE-0030;
- implementing search/query/API/frontend behavior.

## Retained package

Retain the bounded deterministic result under:

```text
research/stage3/sl0031-corrected-tier1-evidence-profile/
```

At minimum include:

- `boatmodel_evidence_profile.json` + schema;
- `aggregate_profile.json` + schema;
- `positive_control_candidates.json` + schema;
- `REPORT.md` with exact predecessor/corrected precursor delta, field-count distribution, strong-subset counts, selection result and preserved non-canonical interpretation;
- `ARTIFACT-DIGESTS.json` + schema covering every retained package file except the digest document itself.

The package must be reproducible by a deterministic offline verifier with no network access.

Do not copy or modify accepted prior-slice retained packages.

## Required implementation behavior

1. Verify accepted SLICE-0028 and SLICE-0030 retained packages offline before derivation.
2. Reproduce the exact 1,770 canonical / 1,772 historical identity boundary with zero drift.
3. Reproduce the accepted corrected SLICE-0030 five-field marginal coverage totals.
4. Build one per-BoatModel evidence profile for all 1,770 canonical models.
5. Recompute the exact SLICE-0028 predecessor precursor under both predecessor and corrected semantics from retained evidence rather than copying only the published count.
6. Retain exact overlap decomposition for draft/displacement within the corrected precursor.
7. Retain the normalized-field-count and strong-evidence-subset distributions.
8. Select the positive-control pool using only the fixed eligibility/ranking rules above.
9. Exclude the two SLICE-0029 Catalina negative controls from the positive-control pool.
10. Keep all outputs explicitly evidence-level and non-canonical.
11. Add schema validation, integrity digests and an offline self-consistency verifier.
12. Add focused tamper/negative tests for boundary drift, profile drift, precursor drift and candidate-ranking drift.
13. Do not mutate accepted SLICE-0028/0029/0030 artifacts.
14. Do not perform live network acquisition.
15. Do not create or mutate canonical BoatModel/BoatDesign/FieldResolution data.

## Required regressions

Tests must cover at least:

- exact five-field normalized marginal totals reproduce the accepted corrected SLICE-0030 result;
- predecessor precursor recomputes to exactly `607 / 1770` from the accepted pre-correction evidence;
- corrected precursor is computed from per-BoatModel joint evidence, not derived arithmetically from marginal totals;
- a model with LOA+beam+draft and no displacement satisfies the precursor;
- a model with LOA+beam+displacement and no draft satisfies the precursor;
- a model missing LOA or beam does not satisfy the precursor even when draft/displacement exist;
- `normalized_field_count` is deterministic and bounded 0..5;
- disagreement-bearing eligible-looking models are excluded by the candidate rule;
- `Q5051252` and `Q5051253` are excluded even if they otherwise meet eligibility;
- candidate ordering follows the exact ranking keys and stable `hullq_id` tie-break;
- tampering with accepted linkage/input digests or a retained profile causes offline verification failure;
- no live network call is required by the primary verifier;
- no canonical persistence mutation occurs.

## Acceptance criteria

SLICE-0031 is ready for independent review when all of the following are truthfully satisfied or explicitly reported `BLOCKED` where required:

- [ ] accepted SLICE-0028 retained package verifies offline;
- [ ] accepted SLICE-0030 retained package verifies offline;
- [ ] exact 1,770 canonical / 1,772 historical identity boundary reproduces with zero drift;
- [ ] corrected five-field marginal coverage reproduces the accepted SLICE-0030 result;
- [ ] all 1,770 canonical BoatModels have exactly one deterministic retained evidence profile row;
- [ ] normalized-field-count distribution 0..5 is retained and sums exactly to 1,770;
- [ ] predecessor `607 / 1770` precursor recomputes from accepted pre-correction evidence;
- [ ] corrected precursor is measured exactly from joint BoatModel evidence;
- [ ] draft-only / displacement-only / both overlap decomposition is retained and self-consistent;
- [ ] strong technical-evidence subset counts are retained;
- [ ] positive-control candidate eligibility and ranking are deterministic and tested;
- [ ] Catalina 22 / Catalina 30 negative controls are excluded from the positive-control pool;
- [ ] top-level pool result is exactly `POSITIVE_CONTROL_POOL_AVAILABLE` or `NO_POSITIVE_CONTROL_POOL` according to the fixed rule;
- [ ] no result is mislabeled canonical Search coverage or launch readiness;
- [ ] no CAL-01 D2/D2b threshold or G4 claim is invented;
- [ ] no external acquisition occurred;
- [ ] zero canonical BoatModel/BoatDesign/FieldResolution/technical-value mutation occurred;
- [ ] accepted SLICE-0028/0029/0030 retained packages are untouched;
- [ ] retained SLICE-0031 artifacts are schema-valid, integrity-digested and offline-verifiable;
- [ ] repository validation, Ruff, mypy and full pytest/coverage gates pass;
- [ ] required remote CI is observed on the exact final branch HEAD before claiming PASS;
- [ ] Manufacturer artifact reproducibility is observed on the exact final branch HEAD when triggered;
- [ ] slice remains `REVIEW` or `BLOCKED`, never `DONE`;
- [ ] no SLICE-0032 is started automatically.

## Explicit non-goals

SLICE-0031 does **not**:

- query Wikidata or any manufacturer website;
- discover or admit new BoatModels;
- expand Stage-3.2 breadth;
- change unit or qualifier semantics;
- resolve BoatDesign generation/applicability;
- research the selected positive-control candidates externally;
- create canonical BoatDesigns or DesignOptions;
- create FieldResolution decisions;
- write canonical technical values;
- compute derived metrics from unpromoted evidence;
- define query-engine semantics;
- define or implement public Search/API/frontend/SEO behavior;
- implement market/listing/deduplication/freshness/account/monitoring/alert/pricing behavior;
- declare the evidence precursor to be production basic-searchable coverage;
- declare CAL-01 D2/D2b or G4 passed;
- start SLICE-0032.

## Expected touch points

Expected only where needed:

- a small SLICE-0031 analysis helper under `src/hullq/bootstrap/` and/or `scripts/bootstrap/`;
- `research/stage3/sl0031-corrected-tier1-evidence-profile/`;
- focused unit tests;
- `.github/workflows/ci.yml` only if needed to make the exact retained offline verification externally observable.

Do not redesign the Wikidata adapter, identity model, applicability model, provenance model or persistence architecture.

## Validation

At final handoff run the normal repository gates:

```text
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Also provide and execute a deterministic SLICE-0031 offline verifier. The primary verifier must require no live Wikidata, Catalina or other external web access.

## Stop conditions

Stop `BLOCKED` instead of inventing behavior if:

- accepted SLICE-0028 or SLICE-0030 retained artifacts fail offline verification;
- the fixed 1,770 / 1,772 identity boundary drifts;
- the accepted corrected five-field marginal totals cannot be reproduced;
- the predecessor 607-model precursor cannot be independently recomputed from retained accepted evidence;
- candidate eligibility would require using non-fixed fields, web popularity, assumed source availability or undocumented model knowledge;
- deterministic disagreement exclusion cannot be derived from accepted retained evidence without inventing a second incompatible parser;
- the only way to claim launch/basic-searchable readiness is to equate research evidence with canonical production values.

A negative result (`NO_POSITIVE_CONTROL_POOL`) is a valid completed validation outcome when correctly measured and retained.

## Handoff

The implementation agent must return a concise completion report containing:

- exact final branch HEAD SHA;
- slice state recommendation (`REVIEW` or `BLOCKED`);
- exact reproduced identity boundary;
- exact corrected five-field marginal totals;
- predecessor and corrected precursor counts/percentages/delta;
- normalized-field-count distribution;
- strong technical-evidence subset counts;
- candidate-pool count and exact selected QID/HullQ-ID list;
- deterministic pool result;
- explicit confirmation of zero network acquisition and zero canonical mutation;
- retained-package/offline-verifier result;
- repository validation / Ruff / mypy / pytest / coverage result;
- exact-head remote CI result;
- exact-head Manufacturer reproducibility result;
- unresolved findings or scope deviations;
- explicit statement that SLICE-0032 was not started automatically.
