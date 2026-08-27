# SLICE-0028 — Acceptance Closure

**ID:** SLICE-0028  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Independent-review verdict:** ACCEPT — no blocking or material findings remain after two bounded amendments  
**Implementation PR:** #80 — "SLICE-0028: Full-boundary Wikidata Tier-1 evidence rollout (1,770 canonical BoatModels)"  
**Final reviewed implementation head:** `351f607208579c54246e0af3086d9a23f47d5736`  
**Implementation merge commit:** `dc1270f319665f169dab7e994103e358fef4dd6d`  
**Exact-head PR CI:** run `33061796597`, SUCCESS  
**Exact-head PR manufacturer reproducibility:** run `33061796668`, SUCCESS  
**Final independent-review comment:** PR #80 issue comment `5437620494`

## Independent review result

Independent review accepts the SLICE-0028 implementation for Project Owner acceptance. The slice is **not `DONE` yet**; explicit Project Owner acceptance is still required under the normal workflow.

SLICE-0028 scales the accepted SLICE-0027-corrected Wikidata Tier-1 evidence path from the retained 100-BoatModel pilot to the entire accepted canonical BoatModel boundary. It remains an evidence/coverage/persistence rollout only: it does not create canonical technical resolutions, BoatDesign rows, FieldResolution decisions, query-engine behavior, API/frontend behavior or launch-readiness claims.

The first independent review required correction of stale SLICE-0027 operational status, explicit 1,772-vs-1,770 identity reconciliation, same-QID unsupported+normalized disagreement detection, and stronger offline manifest verification. A second bounded amendment was required because the controlling slice contract still retained ambiguous 1,772/1,770 request-set wording and the offline acquisition-completeness verifier still needed exact QID-set/duplicate/failure-count verification. Final re-review of exact head `351f607208579c54246e0af3086d9a23f47d5736` found those issues closed.

## Accepted identity and acquisition boundary

The accepted identity state is explicitly reconciled as:

```text
historical QID -> HullQ-ID registry                 1,772
canonical AUTO_ADMIT QID -> BoatModel linkage      1,770
non-canonical historical reserved mappings             2
```

The two retained non-canonical reserved mappings are:

```text
Q109650429 -> BM_WDT0_6221328c32fe4b43b113c0ffc5e0bec9
              review_required / name_collision

Q2461915   -> BM_WDT0_25df3c46ed4c45c292c817cf4b7eb0b3
              review_required / name_collision
```

They remain auditable historical identity state but are excluded from SLICE-0028 technical acquisition because they do not address canonical BoatModel rows.

The controlling contract now explicitly states:

```text
request-QID derivation
= canonical AUTO_ADMIT linkage keys (1,770)
!= all historical registry keys (1,772)
```

No identity discovery, fuzzy matching, new identity decision or canonical admission was performed by this slice.

### Acquisition result

```text
requested QIDs                  1,770
fetched entities                1,770
acquisition failures                0
retained live HTTP telemetry       36 requests
```

The HTTP request count is retained live acquisition telemetry and is not falsely presented as independently reconstructible offline.

The offline verifier now reuses the accepted `verify_entity_acquisition_completeness()` gate and verifies exact request/entity QID coverage, including missing, unexpected and duplicate QIDs. It also enforces the successful-package consistency condition in both directions: exact completeness requires `acquisition_failure_count == 0`, and a retained zero failure count requires exact completeness.

Focused tamper regressions cover:

- same-cardinality unexpected-QID substitution;
- duplicate QID masking a missing requested QID;
- non-zero acquisition-failure count on an otherwise exactly complete retained package.

## Full-boundary five-field evidence coverage

Coverage is retained at source-QID and canonical-BoatModel level. The accepted boundary is currently bijective, so the measured count tables are identical at both levels.

| field | normalized_candidate_present | source_statement_present | unsupported_or_malformed | no_usable_value |
|---|---:|---:|---:|---:|
| LOA | 888 | 0 | 227 | 655 |
| LWL | 848 | 0 | 227 | 695 |
| beam | 891 | 1 | 0 | 878 |
| draft | 691 | 0 | 11 | 1,068 |
| displacement | 66 | 792 | 155 | 757 |

These are evidence-availability classifications only. Strongest-available-evidence precedence is used only to classify coverage; it does not choose a canonical technical value.

## Candidate multiplicity / disagreement diagnostics

Final retained result:

```text
flagged (BoatModel, field) cases    42
```

The initial implementation incorrectly reported 0 because a normalized per-QID coverage bucket could hide another unsupported/malformed statement on the same QID/property. The amended implementation detects that same-QID coexistence without introducing a second qualifier/unit parser, using retained raw claims plus the existing adapter evidence output.

The final 42 cases remain explicit diagnostics only. No majority/first-seen rule or FieldResolution was invented.

## Basic-searchable evidence precursor

The retained non-canonical diagnostic is:

```text
LOA + beam + (draft OR displacement) normalized-candidate evidence
607 / 1,770 BoatModels = 34.2938%
```

This is explicitly **not CAL-01 D2 basic-searchable coverage**, is not a launch-readiness metric, and does not mean that 607 BoatModels already possess accepted canonical searchable values. It is source-evidence coverage intended to inform later canonical-resolution/source-gap decisions and the still-pending CAL-01 D2b threshold.

## PostgreSQL persistence / replay evidence

The retained SLICE-0028 replay proof records:

```text
bundle count                    1,770
first-pass imported             1,770
first-pass conflicts/errors         0 / 0
readback mismatches                 0
idempotent reimports            1,770
reimport conflicts/errors           0 / 0
canonical BoatModel rows            0
canonical BoatDesign rows           0
clear                             true
```

The exact-head PostgreSQL-18 CI job independently runs the SLICE-0028 offline verifier, persistence/replay and required-condition assertions.

## Validation evidence

Final reviewed implementation head:

`351f607208579c54246e0af3086d9a23f47d5736`

Implementation-agent local validation reported:

- repository validator: PASS;
- Ruff format/lint: PASS;
- mypy: PASS;
- local full test run: **2,244 passed / 2 skipped**;
- local coverage: **92.17%** overall (>=90% gate);
- SLICE-0028 offline verify: PASS against the retained 1,770-entity package;
- local PostgreSQL 18.6 persist/replay: 1,770 imported, 0 conflicts/errors, 0 readback mismatches, 1,770 idempotent reimports, 0 canonical rows.

Independent exact-head remote verification confirmed:

- CI run `33061796597`: SUCCESS;
  - dependency audit: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - db integration PostgreSQL 18: SUCCESS;
  - SLICE-0028 retained offline verify: SUCCESS;
  - SLICE-0028 persist/replay: SUCCESS;
  - SLICE-0028 persistence required-condition assertions: SUCCESS;
- Manufacturer artifact reproducibility run `33061796668`: SUCCESS on Ubuntu and Windows.

The Ubuntu non-DB quality job independently reported 2,031 passed / 215 skipped and 90.70% coverage; the larger skip count is expected in that job because PostgreSQL-backed tests are exercised separately by the dedicated DB-integration job.

Implementation PR #80 was merged as:

`dc1270f319665f169dab7e994103e358fef4dd6d`

## Review amendment trail

- first independent review on head `5c48a0771e43b5d6df591eccdbce0a7add51ca43`: **AMENDMENT REQUIRED**, PR #80 issue comment `5431792190`;
- first amended head `89f52355439ae646b35795ecd4b6b410a04face2`: major findings corrected, but controlling-contract ambiguity and exact offline acquisition-completeness proof remained;
- second independent re-review: **SECOND BOUNDED AMENDMENT REQUIRED**, PR #80 issue comment `5437304387`;
- final reviewed head `351f607208579c54246e0af3086d9a23f47d5736`: **ACCEPT**, PR #80 issue comment `5437620494`.

Evidence contradicting an earlier agent report was treated as authoritative: the initial disagreement claim of 0 was replaced by the reproduced retained result of 42.

## Preserved boundaries

SLICE-0028 did not:

- perform SPARQL or new identity discovery;
- add/remove/merge/split canonical BoatModels;
- create new historical identity decisions;
- mint or infer BoatDesign generations;
- create canonical technical values or FieldResolution decisions;
- broaden the accepted SLICE-0027 qualifier/concept-QID semantics;
- claim the evidence precursor as canonical Search coverage;
- complete Stage 3.2 or declare G4 passed;
- implement query engine, API, frontend, SEO runtime, market/listing, account, monitoring, alert or pricing behavior;
- start SLICE-0029.

**Stage 3.2 remains OPEN.** The accepted canonical identity boundary remains 1,770 BoatModels / 1,772 historical mappings.

## Evidence trail

- controlling contract: `docs/slices/SLICE-0028-full-boundary-wikidata-tier1-evidence-rollout.md`;
- retained package: `research/stage3/sl0028-wikidata-tier1-full-boundary/`;
- implementation PR: #80;
- final reviewed implementation head: `351f607208579c54246e0af3086d9a23f47d5736`;
- implementation merge commit: `dc1270f319665f169dab7e994103e358fef4dd6d`;
- exact-head PR CI run `33061796597`, SUCCESS;
- exact-head PR manufacturer reproducibility run `33061796668`, SUCCESS;
- final independent-review comment: PR #80 issue comment `5437620494`;
- independent-review verdict: **ACCEPT — no blocking or material findings remain**;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records independent acceptance of the implementation but does not itself mark SLICE-0028 `DONE` and does not authorize SLICE-0029. Explicit Project Owner acceptance is required next. After that acceptance, the normal slice-finish/readiness workflow may continue.
