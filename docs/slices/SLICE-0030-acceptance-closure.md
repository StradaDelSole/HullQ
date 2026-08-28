# SLICE-0030 — Acceptance Closure

**ID:** SLICE-0030  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Independent-review verdict:** ACCEPT — the single blocking review finding was closed by a bounded fail-closed identity-validation amendment  
**Implementation PR:** #86 — "SLICE-0030: correct Wikidata mass-unit QID map and replay full boundary"  
**Final reviewed implementation head:** `104f914d4a226d56623534ca8a04107a652fea54`  
**Implementation merge commit:** `149a6436e942a8950b40c8945a8e44e47d917957`  
**Exact-head PR CI:** run `33128096428`, SUCCESS  
**Exact-head PR manufacturer reproducibility:** run `33128100549`, SUCCESS  
**Final independent-review submission:** PR #86 review `5046681448`

## Independent review result

Independent review accepts the SLICE-0030 implementation for Project Owner acceptance. The slice is **not `DONE` yet**; explicit Project Owner acceptance is still required under the normal workflow.

SLICE-0030 corrected a deterministic Wikidata mass-unit identity defect and replayed the exact accepted SLICE-0028 retained full boundary offline. The correction changes the default mass-unit QID map for current/future extraction while preserving the legacy unit-map behavior required to reproduce accepted historical retained packages.

The accepted corrected/default mass-unit identities are:

```text
Q11570   -> kilogram
Q41803   -> gram
Q191118  -> metric tonne
Q100995  -> pound
```

The corrected/default path no longer treats these unrelated legacy QIDs as mass units:

```text
Q12152   myocardial infarction
Q11369   molecule
Q37795   Romanian Raven Shepherd Dog
```

## Historical reproducibility

The adapter now exposes an explicit versioned unit-map compatibility boundary:

```text
UNIT_QID_MAP_VERSION_SLICE0008   legacy historical behavior
UNIT_QID_MAP_VERSION_SLICE0030   corrected/current default
```

Accepted historical replay paths that depend on the former mapping are pinned explicitly to `UNIT_QID_MAP_VERSION_SLICE0008`. Current/future extraction uses the corrected SLICE-0030 map by default.

The implementation preserves the accepted SLICE-0026 / SLICE-0027 / SLICE-0028 retained packages without rewriting them merely to match the new default. Their offline verification paths remain deterministic.

## Fail-closed unit-identity verification

Initial independent review found one blocking defect: the first implementation retained label/P31 snapshots but assigned `correct_existing_mapping` / `corrected_positively_verified_mapping` from static QID tables without mechanically requiring the fetched identity evidence to satisfy a physical-unit criterion. A contradictory response could therefore have been reported as positively verified.

The bounded amendment closes that blocker.

The final implementation uses Wikidata P31 `Q3647172` (`unit of mass`) as the explicit structural criterion. For all seven fixed QIDs:

- the four supported mass-unit QIDs must include `Q3647172` in their retained P31 evidence;
- the three rejected legacy QIDs must not satisfy that criterion;
- label is retained as secondary evidence only and is never the sole verification rule;
- `build_unit_qid_assessment_document()` validates the exact fixed QID set and calls the identity validator before assigning classification or intended HullQ unit;
- contradictory evidence raises `UnitIdentityValidationError` and the live `--identity-check` path refuses to write a contradictory assessment;
- offline verification rebuilds through the same builder/validator, so retained P31 tampering or contradictory snapshots fail verification rather than passing through a weaker replay-only rule.

Negative regressions cover both directions of contradiction and offline tamper detection.

## Fixed replay boundary

The accepted replay uses exactly the already-retained SLICE-0028 raw evidence:

```text
canonical BoatModels             1,770
canonical acquisition QIDs       1,770
historical QID -> HullQ mappings 1,772
```

No new boat discovery or 1,770-entity reacquisition occurs in the primary replay proof.

Coverage is retained for exactly the five accepted Tier-1 fields:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

Measured normalized-candidate coverage before/after:

```text
loa            888 -> 888
lwl            848 -> 848
beam           891 -> 891
draft          691 -> 691
displacement    66 -> 858
```

Therefore:

```text
displacement_normalized_candidate_delta = +792
non_displacement_fields_unchanged       = true
```

The correction exposes previously raw-only, otherwise usable mass observations; it does not make a BoatDesign applicability decision or create a canonical technical value.

## Unit occurrence evidence

On the fixed SLICE-0028 retained P2067 mass claims, the relevant QID occurrences are:

```text
Q11570   kilogram       224
Q191118  metric tonne     1
Q100995  pound           794
Q41803   gram              0
Q12152   legacy invalid    0
Q11369   legacy invalid    0
Q37795   legacy invalid    0
```

The three erroneous legacy mappings were therefore a latent adapter defect rather than a known live misclassification in the accepted retained boat evidence. Correcting them remains necessary because the default identity map itself was wrong.

## Measurement normalization boundary

SLICE-0030 reuses the existing HullQ measurement normalizer and does not introduce alternate unit-conversion formulas.

Focused regression evidence includes exact existing pound conversions:

```text
2490 lb  -> 1129.44500130 kg
10200 lb -> 4626.64217400 kg
```

Cross-dimension guards and unknown-unit fail-closed behavior remain preserved.

## PostgreSQL persistence and canonical mutation boundary

The corrected 1,770-bundle research-evidence replay passed the existing PostgreSQL research boundary:

```text
first import                 1,770 imported
readback mismatches          0
idempotent re-import         1,770 already imported
conflicts/errors             0
canonical BoatModel rows     0
canonical BoatDesign rows    0
clear                        true
```

SLICE-0030 does not:

- create or mutate canonical BoatModel identity;
- create or mutate canonical BoatDesign identity;
- create a FieldResolution;
- promote a Wikidata technical candidate into a canonical BoatDesign value;
- reinterpret the accepted SLICE-0029 applicability result;
- implement Search/API/frontend/SEO behavior;
- start SLICE-0031.

## Validation evidence

Final reviewed implementation head:

`104f914d4a226d56623534ca8a04107a652fea54`

Implementation-agent local validation reported:

- repository governance: PASS;
- Ruff format/lint: PASS;
- mypy: PASS;
- full test run: **2,318 passed / 2 skipped**;
- total coverage: **92.01%** (>=90% gate);
- SLICE-0030 offline verifier: PASS;
- local PostgreSQL 18 persistence proof: PASS / `clear: true`.

Independent exact-head remote verification confirmed:

- CI run `33128096428`: SUCCESS on exact head `104f914d4a226d56623534ca8a04107a652fea54`;
  - dependency audit: SUCCESS;
  - PostgreSQL 18 db integration: SUCCESS, including SLICE-0030 offline verify / persist / zero-mutation proof;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
- Manufacturer artifact reproducibility run `33128100549`: SUCCESS on the same exact head on Ubuntu and Windows.

Implementation PR #86 was merged as:

`149a6436e942a8950b40c8945a8e44e47d917957`

## Review amendment trail

- initial reviewed head `6a6de49f67c3a9104e08264e0e3899ddca9578e6`: **CHANGES REQUIRED** — live unit-identity evidence was retained but not mechanically coupled to the positive physical-unit classification;
- amended/final reviewed head `104f914d4a226d56623534ca8a04107a652fea54`: fail-closed P31 identity criterion added and shared by live and offline verification; exact-head CI/manufacturer gates green; **ACCEPT**, PR #86 review `5046681448`.

## Retained evidence trail

- controlling contract: `docs/slices/SLICE-0030-wikidata-mass-unit-qid-correction-full-boundary-offline-replay.md`;
- retained package: `research/stage3/sl0030-wikidata-mass-unit-correction/`;
- implementation PR: #86;
- final reviewed implementation head: `104f914d4a226d56623534ca8a04107a652fea54`;
- implementation merge commit: `149a6436e942a8950b40c8945a8e44e47d917957`;
- exact-head CI run `33128096428`, SUCCESS;
- exact-head manufacturer reproducibility run `33128100549`, SUCCESS;
- final independent-review submission: PR #86 review `5046681448`;
- independent-review verdict: **ACCEPT — no blocking or material findings remain**;
- Project Owner acceptance: **PENDING**.

## Preserved next-boundary question

The corrected full-boundary replay substantially increases normalized displacement evidence from 66 to 858 BoatModels. SLICE-0030 deliberately does not decide whether that improved evidence changes CAL-01 D2b threshold planning or justifies any canonical BoatDesign technical-promotion step. That decision belongs to a separately readied later slice.

## Next boundary

This closure records independent acceptance of the implementation but does not itself mark SLICE-0030 `DONE` and does not authorize SLICE-0031. Explicit Project Owner acceptance is required next. After that acceptance, the normal `FINISH_SLICE` -> independent readiness -> `START_SLICE` workflow may continue.
