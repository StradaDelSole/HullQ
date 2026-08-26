# SLICE-0027 — Acceptance Closure

**ID:** SLICE-0027  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Independent-review verdict:** ACCEPT — no blocking or material findings  
**Implementation PR:** #77 — "SLICE-0027: Wikidata qualifier-semantics correction + offline replay"  
**Final reviewed implementation head:** `8c8eaa901f2842fceb228ffb80c78aa46b7e1afb`  
**Implementation merge commit:** `546e8babf5ee3a64e00113e017053b1537873810`  
**Exact-head PR CI:** run `33009791962`, SUCCESS  
**Exact-head PR manufacturer reproducibility:** run `33009792021`, SUCCESS

## Independent review result

Independent review accepts the SLICE-0027 implementation for Project Owner acceptance. The slice is **not `DONE` yet**; explicit Project Owner acceptance is still required under the normal workflow.

SLICE-0027 corrected only the bounded qualifier-property compatibility mismatch exposed by the accepted SLICE-0026 retained 100-BoatModel pilot. The implementation recognizes evidence-backed alternative qualifier-property carriers for already-accepted Wikidata concept QIDs while preserving the existing accepted `P642` path and the existing unqualified beam path.

No broader Wikidata discovery/acquisition, new concept-QID semantics, canonical technical resolution, FieldResolution rollout, canonical identity mutation, Stage-3.2 completion or later-slice work was accepted by this review.

## Accepted evidence boundary

The implementation reuses exactly the retained SLICE-0026 input boundary:

```text
100 distinct accepted canonical BoatModels
100 retained known Wikidata QIDs
canonical identity boundary: 1,770 BoatModels / 1,772 historical QID mappings
```

No live Wikidata acquisition is part of the SLICE-0027 correction/replay proof.

### Retained qualifier-property/value shapes

| statement property | qualifier property | qualifier value QID | retained count | recognized | mapped field |
|---|---|---|---:|---|---|
| P2043 | P1013 | Q2358152 | 2 | no | — |
| P2043 | P518 | Q1817392 | 42 | yes | LWL |
| P2043 | P518 | Q2358152 | 41 | yes | LOA |
| P2048 | P518 | Q244777 | 28 | yes | draft |
| P2048 | P518 | Q331744 | 1 | no | — |
| P2067 | P3831 | Q5636358 | 37 | yes | displacement |

The review confirmed that the implementation does not infer meaning from labels, quantity property alone, arbitrary qualifier properties, or unfamiliar qualifier-value QIDs. In particular, the retained `P1013 + Q2358152` shape remains unsupported and `P3831` is accepted only for the evidenced displacement concept QID, not ballast.

## Before / after coverage — exact retained 100 entities

| field | before: normalized / source-only / unsupported / no-usable | after: normalized / source-only / unsupported / no-usable |
|---|---|---|
| LOA | 0 / 0 / 64 / 36 | 41 / 0 / 16 / 43 |
| LWL | 0 / 0 / 64 / 36 | 42 / 0 / 16 / 42 |
| beam | 41 / 0 / 0 / 59 | 41 / 0 / 0 / 59 |
| draft | 0 / 0 / 29 / 71 | 28 / 0 / 1 / 71 |
| displacement | 0 / 0 / 51 / 49 | 5 / 32 / 14 / 49 |

The 32 displacement `source_statement_present` cases remain explicitly source-only rather than being falsely normalized when the existing measurement normalizer cannot support the retained representation/unit.

## Historical reproducibility safeguard

Independent review specifically checked the adapter-versioning decision introduced by this slice.

- `QUALIFIER_CARRIER_VERSION_SLICE0008` preserves the original P642-only extraction behavior captured by the accepted SLICE-0026 retained package.
- SLICE-0026 offline verify/persist explicitly pin that historical carrier version.
- `QUALIFIER_CARRIER_VERSION_SLICE0027` is the amended default for current callers and adds only the retained-evidence-backed P518/P3831 carrier combinations.
- The existing P642 mappings remain first in carrier precedence.
- The actual qualifier property used is preserved in raw evidence, so P518/P3831-derived mappings remain auditable.

The PR changed no file under `research/stage3/sl0026-wikidata-tier1-enrichment/`; the accepted SLICE-0026 retained package therefore remains untouched.

## PostgreSQL persistence / replay evidence

The retained SLICE-0027 replay result records:

```text
bundle count                    100
first-pass imported             100
first-pass conflicts/errors       0 / 0
readback mismatches               0
idempotent reimports            100
reimport conflicts/errors         0 / 0
canonical BoatModel rows          0
canonical BoatDesign rows         0
clear                           true
```

The exact-head PostgreSQL-18 CI job independently ran both the pinned SLICE-0026 replay and the amended SLICE-0027 offline verify/persist path successfully.

## Validation evidence

Final reviewed implementation head:

`8c8eaa901f2842fceb228ffb80c78aa46b7e1afb`

Implementation-agent local validation reported:

- repository validator: PASS;
- Ruff format/lint: PASS;
- mypy: PASS;
- pytest: **2,196 passed / 2 skipped**;
- coverage: **91.95%** overall (>=90% gate);
- SLICE-0026 pinned offline verifier/persist: PASS;
- SLICE-0027 offline verifier: PASS;
- local PostgreSQL 18.6 SLICE-0027 persist/replay: 100 imported, 0 readback mismatches, 100 idempotent reimports, 0 canonical rows.

Independent exact-head remote verification confirmed:

- CI run `33009791962`: SUCCESS;
  - quality gates: SUCCESS;
  - dependency audit: SUCCESS;
  - db integration (PostgreSQL 18): SUCCESS;
  - SLICE-0026 retained offline verify + pinned persistence replay: SUCCESS;
  - SLICE-0027 retained offline verify + persistence replay + required-condition assertions: SUCCESS;
- Manufacturer artifact reproducibility run `33009792021`: SUCCESS.

Implementation PR #77 was merged as:

`546e8babf5ee3a64e00113e017053b1537873810`

## Preserved boundaries

SLICE-0027 did not:

- perform new live Wikidata acquisition or discovery;
- expand beyond the accepted retained 100-QID primary proof;
- add new field/concept-QID semantics;
- create, modify or delete canonical BoatModel identity/crosswalk rows;
- create a canonical BoatDesign row or mint a BoatDesign ID;
- create FieldResolution decisions;
- broaden to the 1,770-model enrichment universe;
- complete Stage 3.2 or declare G4 passed;
- start SLICE-0028.

**Stage 3.2 remains OPEN.** The canonical identity boundary remains exactly 1,770 BoatModels / 1,772 historical QID mappings.

## Evidence trail

- controlling contract: `docs/slices/SLICE-0027-wikidata-qualifier-semantics-correction-offline-replay.md`;
- retained package: `research/stage3/sl0027-wikidata-qualifier-semantics/`;
- implementation PR: #77;
- final reviewed implementation head: `8c8eaa901f2842fceb228ffb80c78aa46b7e1afb`;
- implementation merge commit: `546e8babf5ee3a64e00113e017053b1537873810`;
- exact-head PR CI run `33009791962`, SUCCESS;
- exact-head PR manufacturer reproducibility run `33009792021`, SUCCESS;
- independent-review verdict: **ACCEPT — no blocking or material findings**;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records independent acceptance of the implementation but does not itself mark SLICE-0027 `DONE` and does not authorize SLICE-0028. Explicit Project Owner acceptance is required next. After that acceptance, normal slice-finish/readiness workflow may continue, with the operational state synchronized in the next authorized docs/readiness change.
