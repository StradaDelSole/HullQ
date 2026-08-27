# SLICE-0030 — Wikidata Mass-Unit QID Correction + Full-Boundary Offline Replay

**ID:** SLICE-0030  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0029 owner-accepted / DONE (Project Owner acceptance recorded on PR #84, issue comment `5443542633`)  
**Blocks:** trustworthy Wikidata mass/displacement normalization, accurate Tier-1 evidence coverage measurement, and any later canonical technical-promotion decision that depends on mass-valued evidence

## Objective

Correct the Wikidata adapter's mass-unit QID compatibility defect exposed by the accepted SLICE-0029 result, then replay the already-retained SLICE-0028 full-boundary raw entity evidence offline to measure the exact coverage effect without reacquiring the 1,770-QID dataset and without creating any canonical technical value.

SLICE-0029 demonstrated that the Catalina 22 / Catalina 30 retained Wikidata displacement statements exist but carry `normalized_candidate = null` even where the raw amounts are ordinary pound values. Independent readiness review of the current adapter found the underlying unit-identity defect in `src/hullq/sources/wikidata.py`:

```text
current adapter mapping          actual Wikidata entity
Q12152 -> gram                  Q12152 = myocardial infarction
Q11369 -> metric tonne          Q11369 = molecule
Q37795 -> pound                 Q37795 = Romanian Raven Shepherd Dog
```

The corresponding current Wikidata mass-unit entity identities are:

```text
Q41803   gram
Q191118  tonne / metric tonne
Q100995  pound / avoirdupois pound
Q11570   kilogram (existing mapping already correct)
```

The accepted HullQ measurement normalizer already supports `MassUnit.GRAM`, `MassUnit.METRIC_TONNE`, `MassUnit.POUND` and exact SI conversion. Therefore this slice is a **unit-identity compatibility correction**, not a new conversion-formula decision.

The main question is not merely whether the three constants can be changed. The slice must preserve reproducibility of already-accepted retained packages while making the corrected map the default for future extraction, and it must measure the corrected result over the exact accepted SLICE-0028 full-boundary raw evidence.

## Why this slice is next

SLICE-0029 correctly ended with:

```text
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

That result prohibits forcing canonical BoatDesign promotion. It also exposed a separate, concrete adapter defect that suppresses otherwise-usable mass observations before the later BoatDesign/applicability gate is even reached.

The accepted SLICE-0028 full-boundary coverage currently records a large gap between displacement source statements and normalized displacement candidates. Correcting a deterministic unit-identity bug is therefore a higher-confidence next step than immediately performing another manual manufacturer-source applicability campaign.

This slice does **not** reinterpret the SLICE-0029 applicability result. Better normalized evidence remains BoatModel/QID-scoped research evidence until a later separately readied slice positively establishes canonical BoatDesign applicability.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `CLAUDE.md`;
- `docs/slices/SLICE-0029-acceptance-closure.md` plus Project Owner acceptance on PR #84;
- `research/stage3/sl0029-primary-source-boatdesign-applicability/REPORT.md` only for the measured displacement-normalization finding and preserved applicability boundary;
- `docs/slices/SLICE-0028-acceptance-closure.md` plus accepted owner-acceptance record;
- `research/stage3/sl0028-wikidata-tier1-full-boundary/` as the fixed retained raw-evidence input and before-state;
- `docs/slices/SLICE-0027-wikidata-qualifier-semantics-correction-offline-replay.md` and its retained package only where needed to preserve historical qualifier-carrier replay/versioning behavior;
- `src/hullq/sources/wikidata.py`;
- `src/hullq/domain/measurements.py`;
- existing provenance/persistence contracts only where implementation requires them.

Do not preload unrelated frontend, SEO, marketplace, account, alert, pricing, monetization or query-engine documents.

## Evidence/reporting law

All completion-report claims must be evidence-backed by executed commands, retained artifacts, repository state or actually observed external checks.

- Do not report expected coverage gain as measured coverage gain.
- Do not claim a unit QID is correct merely because a label seems plausible.
- Do not mark old retained packages reproducible unless the exact offline verifier actually passes.
- If current unit identity evidence contradicts the readiness assumptions, stop `BLOCKED` rather than inventing a mapping.
- The implementation agent's report is not independent review and does not make the slice `DONE`.

## Fixed input boundary

### Full-boundary replay input

Use exactly the accepted SLICE-0028 retained raw entity package:

```text
canonical BoatModels             1,770
canonical acquisition QIDs        1,770
historical QID -> HullQ mappings  1,772
```

The primary correction/replay proof must use the already-retained SLICE-0028 raw claims. Do **not** reacquire the 1,770 entities and do not run a new discovery query.

Before deriving the after-state, offline-verify the accepted SLICE-0028 retained package and fail closed on schema/digest/self-consistency drift.

### Allowed coverage fields

Retain before/after coverage for exactly the existing five Tier-1 pointers:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

The unit-map implementation is shared infrastructure and may correctly affect other mass evidence such as ballast when that adapter path is exercised by focused tests, but SLICE-0030 must not expand its retained full-boundary coverage product beyond these five existing fields.

## Unit-identity correction boundary

### Required corrected mass-unit identities

The corrected/default Wikidata mass-unit map must positively support:

```text
Q11570   -> MassUnit.KILOGRAM
Q41803   -> MassUnit.GRAM
Q191118  -> MassUnit.METRIC_TONNE
Q100995  -> MassUnit.POUND
```

The corrected/default map must **not** treat these unrelated entities as units:

```text
Q12152
Q11369
Q37795
```

Do not add additional mass-unit QIDs in this slice merely because they could be useful later. A new unit is in scope only if it is required by the fixed retained full-boundary evidence and its physical identity is positively established.

### Unit-identity evidence

Retain a compact machine-readable assessment for every corrected QID containing at minimum:

- QID;
- intended HullQ unit enum;
- authoritative Wikidata entity locator;
- positively verified entity label/type or equivalent unit-identity evidence;
- verification/retrieval date;
- whether the unit occurs in the fixed SLICE-0028 retained raw claims;
- observed retained-statement count where deterministically measurable.

The slice may use a **strictly bounded direct Wikidata entity-identity check** for the small fixed unit-QID set if needed to establish current unit identities, using the existing rights-cleared Wikidata path. No SPARQL discovery, boat reacquisition or broad unit discovery is permitted. After the retained package is created, its primary verifier must run offline.

## Historical reproducibility requirement

This is a correction to accepted adapter behavior, so historical retained-package reproducibility is mandatory.

Do not silently replace one global map in a way that makes accepted SLICE-0026 / SLICE-0027 / SLICE-0028 packages impossible to reproduce.

Use a small explicit versioned unit-map compatibility mechanism analogous in spirit to the accepted qualifier-carrier versioning, or another equally deterministic mechanism that satisfies all of the following:

1. the exact historical unit-map behavior needed by accepted retained-package verifiers remains reproducible;
2. the corrected mass-unit map becomes the default for new/current extraction after SLICE-0030;
3. callers can tell which unit-map version produced retained evidence;
4. old package verification does not depend on today's default changing back;
5. no accepted retained package is rewritten merely to match the new default.

If investigation proves that accepted historical verifiers do not actually depend on the old map, retain evidence of that fact and use the smallest coherent implementation. Do not introduce versioning ceremony that has no reproducibility purpose.

## Required implementation behavior

1. Verify SLICE-0028 retained artifacts offline before using them.
2. Reproduce the exact 1,770-QID / 1,770-canonical-BoatModel acquisition boundary with zero identity drift.
3. Deterministically characterize mass-unit QIDs present in the retained P2067/mass evidence relevant to the accepted displacement extraction path.
4. Retain a compact unit-QID assessment distinguishing:
   - correct existing mapping;
   - incorrect legacy mapping;
   - corrected positively verified mapping;
   - observed but unsupported unit QIDs, if any.
5. Correct the Wikidata mass-unit identity mapping with the smallest coherent adapter change.
6. Reuse `MeasurementObservation` + `normalize_measurement`; do not implement alternate pound/gram/tonne conversion formulas.
7. Preserve the existing cross-dimension guard: a mass unit must never normalize a length field, and a length unit must never normalize a mass field.
8. Preserve the accepted SLICE-0027 qualifier-property/concept-QID semantics unchanged.
9. Preserve accepted raw observation representation, source locator, qualifier evidence, evidence IDs/identity semantics and unsupported-unit behavior except where the corrected unit identity now legitimately creates a normalized candidate.
10. Replay the exact retained 1,770 entities offline through the corrected/current adapter path.
11. Retain deterministic before/after coverage for all five fixed fields.
12. Prove that LOA/LWL/beam/draft coverage and normalized values do not change as a side effect of this mass-unit-only correction, except where an independently demonstrated existing shared bug makes such a claim impossible; if so, stop and report the exact boundary.
13. Measure the exact displacement delta rather than assuming every raw mass statement becomes normalized.
14. Preserve unresolved qualifier/basis/semantic failures as unresolved; a recognized mass unit alone must not make an unsupported displacement statement valid.
15. Persist/replay the corrected full-boundary research evidence through the existing PostgreSQL research-evidence boundary and prove first import/readback/idempotent reimport with zero canonical BoatModel/BoatDesign mutation.
16. Retain tamper-resistant artifacts plus an offline verifier for the SLICE-0030 package.
17. Do not mutate the accepted SLICE-0026, SLICE-0027, SLICE-0028 or SLICE-0029 retained packages.

## Required regressions

Tests must cover at least:

- `Q11570` continues to normalize kilogram mass through the existing measurement normalizer;
- `Q41803` normalizes gram mass through the existing measurement normalizer;
- `Q191118` normalizes metric-tonne mass through the existing measurement normalizer;
- `Q100995` normalizes avoirdupois-pound mass through the existing measurement normalizer;
- the existing exact pound factor remains `0.45359237 kg/lb` via `normalize_measurement`, not a second adapter formula;
- a representative `2490 lb` mass observation normalizes exactly to `1129.44500130 kg`;
- a representative `10200 lb` mass observation normalizes exactly to `4626.64217400 kg`;
- `Q12152`, `Q11369` and `Q37795` do not normalize as mass units under the corrected/default map;
- recognized mass units on a length field do not produce a normalized candidate;
- recognized length units on a mass field do not produce a normalized candidate;
- unknown unit QIDs remain raw-only and are not guessed from labels;
- accepted qualifier-carrier behavior from SLICE-0027 remains unchanged;
- historical retained-package verification remains deterministic under the explicitly preserved compatibility path;
- exact SLICE-0028 full-boundary replay is deterministic and network-free;
- non-displacement Tier-1 before/after outputs remain unchanged for the fixed retained boundary;
- PostgreSQL replay preserves exact normalized values/types and remains idempotent;
- zero canonical BoatModel/BoatDesign rows are created or mutated.

## Retained package

Retain the bounded result under:

```text
research/stage3/sl0030-wikidata-mass-unit-correction/
```

At minimum include:

- `unit_qid_assessment.json` + schema;
- `coverage_before_after.json` + schema for exactly the five fixed fields;
- a compact machine-readable replay/verification result;
- `REPORT.md` with the measured unit-use counts, exact displacement coverage delta, compatibility/versioning result and unresolved unit/semantic cases;
- PostgreSQL replay result/report where applicable;
- `ARTIFACT-DIGESTS.json` + schema covering every retained package file except the digest document itself.

Do not copy or regenerate accepted prior-slice retained packages into this directory.

## Acceptance criteria

SLICE-0030 is ready for independent review when all of the following are truthfully satisfied or explicitly reported `BLOCKED` where required:

- [ ] accepted SLICE-0028 retained package verifies offline before derivation;
- [ ] exact 1,770 canonical BoatModel / 1,770 acquisition-QID / 1,772 historical mapping boundary reproduces with zero drift;
- [ ] current retained mass-unit usage is deterministically characterized;
- [ ] every corrected unit QID is positively evidenced as the intended physical unit;
- [ ] `Q12152`, `Q11369`, `Q37795` are not accepted as units by the corrected/default path;
- [ ] corrected/default map supports `Q11570`, `Q41803`, `Q191118`, `Q100995` with the existing HullQ MassUnit enums;
- [ ] existing measurement normalization is reused with no duplicate conversion formulas;
- [ ] historical accepted package reproducibility is preserved or a simpler verified compatibility result is retained;
- [ ] exact retained 1,770 entities replay offline through the corrected path with no live boat-data acquisition;
- [ ] before/after coverage is retained for exactly the five Tier-1 fields;
- [ ] non-displacement Tier-1 output is unchanged by the mass-unit-only correction;
- [ ] exact displacement coverage delta is measured and reported without overclaim;
- [ ] unresolved qualifier/basis/semantic cases remain fail-closed;
- [ ] research persistence/readback/idempotency passes with zero canonical BoatModel/BoatDesign mutation;
- [ ] SLICE-0026/0027/0028/0029 retained artifacts are untouched;
- [ ] SLICE-0030 retained artifacts are schema-valid, integrity-digested and offline-verifiable;
- [ ] repository validation, Ruff, mypy and full pytest/coverage gates pass;
- [ ] required remote CI is observed on the exact final branch HEAD before claiming PASS;
- [ ] Manufacturer artifact reproducibility is observed on the exact final branch HEAD when triggered;
- [ ] slice remains `REVIEW` or `BLOCKED`, never `DONE`;
- [ ] no SLICE-0031 is started automatically.

## Explicit non-goals

SLICE-0030 does **not**:

- reacquire the full Wikidata boat universe;
- run SPARQL discovery;
- add new canonical BoatModels;
- infer or mint BoatDesign generations;
- resolve the SLICE-0029 Catalina applicability gaps;
- turn newly normalized BoatModel/QID evidence into a canonical BoatDesign value;
- create FieldResolution decisions;
- add new search/query semantics;
- expand beyond the five retained Tier-1 coverage fields;
- add arbitrary new unit families;
- change ratio methodology;
- implement Search/API/frontend/SEO runtime;
- implement marketplace/listing/account/monitoring/alert/pricing behavior;
- declare Stage 3.2 complete or G4 passed;
- start SLICE-0031.

## Expected touch points

Expected only where needed:

- `src/hullq/sources/wikidata.py`;
- a small SLICE-0030 replay/analysis helper under `src/hullq/bootstrap/` and/or `scripts/bootstrap/`;
- `research/stage3/sl0030-wikidata-mass-unit-correction/`;
- focused unit/integration/persistence tests;
- `.github/workflows/ci.yml` only if needed to make the exact retained SLICE-0030 offline/PostgreSQL proof externally verifiable;
- compact operational state/index synchronization at implementation handoff if required by the normal slice process.

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

Also provide and execute a deterministic offline SLICE-0030 verifier and PostgreSQL replay/integration proof. The primary offline verifier must require no live Wikidata or Catalina access after the retained SLICE-0030 package is created.

## Stop conditions

Stop `BLOCKED` instead of inventing behavior if:

- accepted SLICE-0028 retained artifacts do not verify;
- the fixed identity/acquisition boundary drifts;
- a proposed corrected QID cannot be positively established as the intended mass unit;
- retained mass statements require a new displacement/ballast/basis semantic decision rather than merely a unit-identity correction;
- correcting the map would require label/fuzzy inference at runtime;
- historical package reproducibility cannot be preserved without rewriting accepted retained evidence;
- non-mass Tier-1 output changes unexpectedly and the cause cannot be bounded within this slice;
- implementation requires canonical technical promotion or another product decision outside this contract.

## Status handoff rule

Claude may move this slice `READY -> IN_PROGRESS -> REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

## Required completion report

Use the concise structure from `docs/slices/SLICE_TEMPLATE.md`. Include:

- exact final branch HEAD SHA;
- unit QIDs assessed and final corrected/default mapping;
- observed retained full-boundary mass-unit counts;
- exact five-field before/after coverage, highlighting displacement delta and confirming non-displacement stability;
- historical reproducibility/version-compatibility result;
- PostgreSQL persistence/readback/idempotency result;
- local validation summary;
- exact-head remote CI / Manufacturer reproducibility state;
- unresolved unit/qualifier/basis cases;
- explicit confirmation of zero canonical mutation;
- declaration that SLICE-0031 was not started.
