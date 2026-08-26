# SLICE-0028 — Full-Boundary Wikidata Tier-1 Evidence Rollout

**ID:** SLICE-0028  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0027 owner-accepted / DONE  
**Blocks:** any evidence-based conclusion about Wikidata Tier-1 coverage across the full accepted canonical identity boundary, and any broader canonical technical-resolution rollout that would rely on that unmeasured full-boundary evidence

## Objective

Scale the now-accepted Wikidata Tier-1 evidence path from the corrected SLICE-0026/0027 100-BoatModel pilot to the **entire accepted SLICE-0017+0018 canonical identity boundary**, using only already-accepted historical Wikidata QID -> HullQ-ID mappings and the accepted SLICE-0027 qualifier-carrier semantics.

This slice is a **full-boundary evidence acquisition, normalization, coverage and persistence rollout**. It is still **not** a canonical technical-resolution rollout.

The accepted boundary entering this slice is:

```text
canonical BoatModels                 1,770
historical QID -> HullQ-ID mappings  1,772
canonical BoatDesign rows                0
```

SLICE-0028 must determine, with retained reproducible evidence, how much of that full accepted BoatModel universe has usable Wikidata evidence for the five already-proven Tier-1-compatible fields:

- LOA;
- LWL;
- beam;
- draft;
- displacement.

It must not infer a BoatDesign generation, create FieldResolution decisions, or convert evidence availability into a claim that a model is canonically searchable.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `CLAUDE.md`;
- `docs/slices/SLICE-0027-acceptance-closure.md` plus the recorded Project Owner acceptance on PR #78;
- `docs/slices/SLICE-0027-wikidata-qualifier-semantics-correction-offline-replay.md`;
- `research/stage3/sl0027-wikidata-qualifier-semantics/`;
- accepted SLICE-0017/0018 identity manifests/replay helpers needed to reproduce the 1,770 / 1,772 boundary;
- `src/hullq/sources/wikidata.py`;
- accepted source-rights, measurement, provenance and research-persistence contracts only where implementation requires them.

Do not preload unrelated frontend, SEO, market, account, alert, pricing, monetization or later-stage documents.

## Evidence/reporting law

All factual completion-report claims MUST be evidence-backed by actually executed commands, retained artifacts, repository state or actually observed external checks.

- Do not report an expected or inferred result as measured fact.
- Do not mark an acceptance criterion passed unless it was actually verified.
- If a required external/remote gate cannot be observed, report `NOT VERIFIED` rather than PASS.
- If a required measurement cannot be obtained truthfully, report `BLOCKED` or the exact unresolved state rather than filling the gap with an assumption.
- The implementation agent's evidence-backed completion report is still subject to independent review; it is not self-acceptance and does not make the slice `DONE`.

This restates the existing `CLAUDE.md` acceptance/verification rule; it does not create a weaker alternative reporting standard.

## Fixed identity boundary

Before acquisition, reproduce the accepted SLICE-0017+0018 identity state from retained artifacts and fail closed on drift.

Required accepted counts:

```text
canonical BoatModels                 1,770
historical QID -> HullQ-ID mappings  1,772
```

Derive the acquisition request set **only** from the accepted historical QID -> HullQ-ID mapping keys.

Requirements:

- retain all accepted QID -> BoatModel links;
- preserve multiple accepted QIDs mapping to the same BoatModel rather than silently selecting one and discarding another;
- report the exact distinct requested-QID count derived from the accepted mappings;
- verify that the mapping value set covers exactly the accepted 1,770 canonical BoatModel IDs;
- do not add a QID by discovery, fuzzy matching, label search or a new identity decision;
- if the accepted artifacts no longer reproduce the 1,770 / 1,772 boundary, stop `BLOCKED`.

## Source and acquisition boundary

Use only:

```text
SRC_WIKIDATA_API_2026
```

Acquisition must use the already-accepted rights-gated Wikidata `wbgetentities` path for **known retained QIDs only**.

No SPARQL discovery query is permitted in this slice.

Before every network request, the existing accepted source-use gate must allow the requested use. Do not add or reinterpret source rights.

Fetch each distinct accepted request QID at most once per acquisition run, using the existing adapter batching/retry behavior rather than a second acquisition implementation.

Retain enough compact raw source payload to reproduce the five allowed fields offline. Irrelevant claims need not be retained merely to maximize artifact size, but any filtering/truncation must be deterministic, explicit and unable to erase the provenance or qualifier semantics required to reproduce the accepted five-field extraction.

### Acquisition failure semantics

A retrieval failure, throttle exhaustion, malformed entity response or other acquisition failure MUST NOT be reclassified as `no_usable_value`.

The retained result must separately report acquisition completeness/failures.

The full-boundary coverage baseline may be claimed complete only if every distinct accepted request QID has a deterministically classified acquisition result. If truthful completion requires missing network results, stop `BLOCKED` or clearly retain an incomplete acquisition state rather than overstating coverage.

## Allowed technical fields

Only these five existing field pointers are in scope:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

Do not add first/last built, hull configuration, material, rig, ballast, sail area, keel/rudder/skeg, builder/designer or any other technical field to the SLICE-0028 retained result merely because a source or adapter exposes it.

## Extraction and normalization semantics

Reuse the accepted Wikidata extraction path with the current accepted qualifier-carrier default established by SLICE-0027.

Required invariants:

- existing accepted `P642` qualifier behavior remains valid;
- accepted SLICE-0027 `P518` carriers remain limited to the already-accepted LOA/LWL/draft concept QIDs;
- accepted SLICE-0027 `P3831` remains limited to the already-accepted displacement concept QID;
- arbitrary/unrecognized qualifier property-value combinations remain unsupported;
- beam remains on its existing unqualified extraction path;
- existing SLICE-0004 measurement normalization is reused;
- unsupported units/raw-only states remain explicit;
- raw source representation, source locator/QID, qualifier-property identity and normalized candidate remain recoverable;
- no label/fuzzy/property-only semantic inference is introduced.

Do not broaden the accepted concept-QID vocabulary in this slice.

## Full-boundary coverage measurement

Retain coverage at two levels:

1. source-QID level;
2. canonical BoatModel aggregation level using every accepted mapped QID for that BoatModel.

For each of the five fields, BoatModel-level coverage must use a deterministic, mutually exclusive availability classification based on all mapped QIDs:

```text
normalized_candidate_present
source_statement_present
unsupported_or_malformed
no_usable_value
```

Use strongest-available evidence precedence only for the coverage bucket:

1. `normalized_candidate_present` if any accepted mapped QID yields at least one normalized candidate for the field;
2. otherwise `source_statement_present` if at least one accepted mapped QID retains a relevant source statement/raw-only candidate;
3. otherwise `unsupported_or_malformed` if at least one accepted mapped QID has a relevant unsupported/malformed statement;
4. otherwise `no_usable_value`.

This aggregation is a **coverage classification only**. It MUST NOT silently choose one canonical technical value.

### Candidate multiplicity / disagreement diagnostics

Separately retain diagnostics for BoatModel+field cases with:

- more than one normalized candidate;
- more than one distinct normalized candidate value;
- evidence arriving through multiple accepted mapped QIDs;
- unsupported evidence coexisting with a normalized candidate.

Do not call a candidate disagreement resolved merely because one value appears more often. Do not create a FieldResolution in this slice.

## Basic-searchable evidence precursor

Retain a diagnostic count for canonical BoatModels that have normalized-candidate evidence availability for:

```text
LOA
AND beam
AND (draft OR displacement)
```

Call this metric explicitly something equivalent to:

```text
basic_searchable_evidence_precursor
```

It is **not** CAL-01 D2 basic-searchable coverage and MUST NOT be reported as launch-readiness coverage, because canonical BoatDesign/FieldResolution/searchable-value decisions have not yet been made.

The purpose is to provide real full-boundary evidence that can later inform the still-pending CAL-01 D2b threshold and the next canonical-resolution/source-gap decision without conflating source evidence with accepted production values.

## Persistence / replay

Persist the SLICE-0028 research evidence through the existing accepted PostgreSQL research-evidence boundary.

The persistence design must preserve source-QID subject identity and the accepted QID -> canonical BoatModel linkage without inventing a BoatDesign ID.

Prove at minimum:

- expected full-boundary research bundle count from the retained request set;
- first import success;
- exact readback fidelity for persisted evidence;
- exact re-import/idempotency;
- zero canonical BoatDesign creation;
- zero FieldResolution creation;
- no mutation/deletion/reassignment of the accepted 1,770 BoatModel / 1,772 historical-mapping identity boundary.

If the existing research persistence contract cannot truthfully represent multiple accepted QIDs mapping to one BoatModel, stop `BLOCKED` rather than modifying canonical identity semantics inside this slice.

## Retained package

Retain a compact reproducible package under:

```text
research/stage3/sl0028-wikidata-tier1-full-boundary/
```

containing at minimum:

- reproduced input-boundary / QID->BoatModel linkage document;
- compact retained raw/evidence manifest sufficient for exact offline five-field replay;
- full-boundary source-QID and BoatModel coverage results;
- candidate-multiplicity/disagreement diagnostics;
- `basic_searchable_evidence_precursor` result;
- compact `REPORT.md`;
- machine-readable JSON schemas for retained JSON artifacts;
- PostgreSQL replay result/report;
- integrity digests covering every retained package file except the digest document itself.

The package must be reproducible offline from its retained inputs after the one bounded live acquisition has completed.

Do not mutate the accepted SLICE-0026 or SLICE-0027 retained packages.

## Required behavior

1. Reproduce the accepted 1,770 BoatModel / 1,772 historical-QID-mapping identity boundary before acquisition.
2. Derive and retain the exact accepted QID -> BoatModel acquisition/linkage set without discovery or new identity decisions.
3. Pass the accepted source-use gate before every Wikidata request.
4. Acquire every distinct accepted mapped QID through the existing known-QID entity API path, with acquisition failures separate from data-missing states.
5. Reuse the accepted SLICE-0027 qualifier-carrier semantics and existing SLICE-0004 normalization.
6. Admit only the five allowed technical fields to the retained SLICE-0028 result.
7. Preserve raw/source/qualifier/normalized evidence needed for audit and offline replay.
8. Measure deterministic coverage at source-QID and canonical-BoatModel level.
9. Retain multi-candidate/value-disagreement diagnostics without canonical adjudication.
10. Retain the explicitly non-canonical `basic_searchable_evidence_precursor` metric.
11. Persist/replay the full-boundary research evidence through the existing PostgreSQL research boundary and prove readback/idempotency.
12. Preserve the accepted canonical identity state exactly; create no BoatDesign and no FieldResolution.
13. Retain schema-valid, integrity-digested artifacts and an offline verifier.
14. Update compact operational handoff docs only to the extent required to record SLICE-0028 `REVIEW`; do not mark it `DONE`.

## Required regressions

Tests must cover at least:

- accepted identity-boundary drift fails closed;
- multiple accepted QIDs mapping to one BoatModel are all preserved in the full-boundary linkage input;
- acquisition failures cannot become `no_usable_value`;
- existing accepted P642 extraction remains valid;
- accepted P518 LOA/LWL/draft extraction remains valid;
- accepted P3831 displacement extraction remains valid;
- arbitrary qualifier carrier/QID combinations remain unsupported;
- beam extraction remains unchanged;
- supported units normalize through the accepted normalizer;
- unsupported/raw-only units remain explicit;
- BoatModel coverage aggregation follows the documented deterministic precedence;
- candidate disagreement is retained and never silently resolved;
- `basic_searchable_evidence_precursor` requires LOA + beam + (draft or displacement) normalized-candidate availability and is not represented as canonical D2/searchable state;
- PostgreSQL replay is exact/idempotent and does not create BoatDesign/FieldResolution or mutate accepted BoatModel/crosswalk identity;
- retained package offline verification is deterministic.

## In scope

- full accepted-boundary known-QID Wikidata acquisition;
- five-field evidence extraction/normalization using already-accepted semantics;
- full-boundary coverage and disagreement diagnostics;
- non-canonical D2 evidence-precursor measurement;
- research persistence/readback/idempotency;
- retained artifacts/offline verification;
- focused tests and CI integration needed to make the retained proof externally reproducible;
- compact project-state/index synchronization at handoff.

## Explicitly out of scope

- any new SPARQL/identity discovery;
- new canonical BoatModel admission/removal/merge/split;
- new historical QID mapping decisions;
- minting or inferring BoatDesign generations;
- canonical technical-value writes;
- FieldResolution creation/adjudication;
- claiming any BoatModel is fully Tier-1 searchable merely because source evidence exists;
- freezing CAL-01 D2b or any launch threshold;
- adding years, hull configuration, material, rig or other Stage-3.3 fields;
- keel/rudder/skeg or Stage-3.4 enrichment;
- derived metrics;
- query engine/API/frontend/SEO runtime;
- market/listing/account/monitoring/alert/pricing implementation;
- Stage 3.2 completion or G4 passage;
- creating or starting SLICE-0029.

## Acceptance criteria

- [ ] Accepted SLICE-0017+0018 identity artifacts reproduce exactly at 1,770 canonical BoatModels / 1,772 historical QID -> HullQ-ID mappings before acquisition.
- [ ] The retained mapping values cover exactly the accepted 1,770 canonical BoatModel IDs; all accepted mapped QIDs are preserved.
- [ ] The distinct request-QID cardinality is derived from retained accepted mappings and reported exactly rather than assumed.
- [ ] No discovery/new identity lookup is performed.
- [ ] Existing source-rights/use gate is enforced before every live request.
- [ ] Every distinct accepted request QID receives a deterministically classified acquisition result; acquisition failures are not misreported as missing boat data.
- [ ] Only the five allowed fields are admitted to SLICE-0028 coverage/evidence output.
- [ ] Accepted P642/P518/P3831/beam semantics and existing measurement normalization are reused without broadening concept semantics.
- [ ] Source-QID and BoatModel-level coverage reproduce deterministically offline.
- [ ] Multi-candidate/value-disagreement cases are retained explicitly and no canonical resolution is invented.
- [ ] `basic_searchable_evidence_precursor` is retained with the exact documented logic and clearly labelled non-canonical/non-launch-readiness.
- [ ] Research persistence/readback is exact and idempotent.
- [ ] Accepted 1,770 / 1,772 canonical identity state is unchanged; zero BoatDesign and zero FieldResolution are created by this slice.
- [ ] SLICE-0026 and SLICE-0027 retained artifacts remain untouched.
- [ ] SLICE-0028 retained artifacts are schema-valid, integrity-digested and offline-verifiable.
- [ ] Repository validation, Ruff, mypy and full pytest/coverage gates pass.
- [ ] Required remote CI is actually observed on the exact final branch HEAD before claiming PASS.
- [ ] Completion report contains only actually verified factual results; any unobserved required gate is labelled `NOT VERIFIED`.
- [ ] No later slice is started automatically.

## Expected touch points

Expected only where needed:

- a small full-boundary Stage-3 rollout helper under `src/hullq/bootstrap/` and/or `scripts/bootstrap/`;
- `research/stage3/sl0028-wikidata-tier1-full-boundary/`;
- focused unit/persistence integration tests;
- `.github/workflows/ci.yml` only if needed for offline retained-package/PostgreSQL external verification;
- compact `PROJECT_STATE` / slice-index synchronization at handoff.

Reuse existing SLICE-0017/0018 identity reproduction, SLICE-0026/0027 Wikidata evidence and SLICE-0013 research-persistence helpers where coherent. Do not redesign identity, provenance or persistence architecture inside this slice.

## Validation

At final handoff run the normal repository gates once:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Also run:

- the SLICE-0028 retained-package offline verifier;
- the PostgreSQL replay/integration path required by this contract;
- any explicit deterministic boundary/coverage validator implemented for the retained full-boundary package.

The bounded live acquisition/build must be executed only as needed to create the retained package; normal CI should reproduce/verify retained results offline rather than repeatedly reacquiring Wikidata.

## Stop conditions

Stop `BLOCKED` instead of inventing results if:

- the accepted 1,770 / 1,772 identity boundary does not reproduce;
- accepted source rights/use gate rejects the full-boundary known-QID acquisition;
- the full accepted QID->BoatModel mapping cannot be preserved truthfully;
- acquisition cannot classify every requested QID without conflating network failure and missing source data;
- a newly observed claim shape requires a new qualifier/concept semantic decision;
- truthful persistence would require inventing a BoatDesign, changing accepted identity semantics or creating canonical technical resolutions;
- implementation requires a new field/source/product decision outside this contract.

## Status handoff rule

Claude may move this slice `READY -> IN_PROGRESS -> REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

## Required completion report

Use the concise structure from `docs/slices/SLICE_TEMPLATE.md` and include only verified facts.

Include at minimum:

- exact final branch HEAD SHA;
- reproduced canonical BoatModel and historical mapping counts;
- exact distinct requested-QID count;
- acquisition request/entity/failure counts;
- exact source-QID and BoatModel coverage counts for all five fields;
- candidate-multiplicity/value-disagreement counts;
- exact `basic_searchable_evidence_precursor` count/percentage, explicitly labelled non-canonical;
- PostgreSQL persistence/readback/idempotency result;
- confirmation of zero BoatDesign/FieldResolution/canonical identity mutation;
- local validation summary;
- exact-head remote CI/reproducibility state actually observed;
- unresolved findings / `NOT VERIFIED` items if any;
- declaration that SLICE-0029 was not started.
