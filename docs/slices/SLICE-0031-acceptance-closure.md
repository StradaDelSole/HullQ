# SLICE-0031 — Acceptance Closure

**ID:** SLICE-0031  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Independent-review verdict:** ACCEPT — no blocking or material findings remain  
**Implementation PR:** #89 — "SLICE-0031: corrected Tier-1 evidence profile + positive-control candidate selection"  
**Final reviewed implementation head:** `c52360703b11d69fc9993d8fe9b8f7ce559fddc5`  
**Implementation merge commit:** `7a20ed0759b89ded8ce845ea88dc9b32c55e5eff`  
**Exact-head PR CI:** run `33155871659`, SUCCESS  
**Exact-head PR manufacturer reproducibility:** run `33155871690`, SUCCESS  
**Final independent-review submission:** PR #89 review `5049491620`

## Independent review result

Independent review accepts the SLICE-0031 implementation for Project Owner acceptance. The slice is **not `DONE` yet**; explicit Project Owner acceptance is still required under the normal workflow.

SLICE-0031 remains a validation/selection slice only. It measures corrected Tier-1 source-evidence maturity over the exact accepted full boundary and deterministically selects a bounded positive-control candidate pool for a later, separately readied BoatDesign/applicability pilot. It does not perform that later research and does not promote any canonical technical value.

## Fixed identity boundary

The accepted implementation reproduces exactly:

```text
canonical BoatModels             1,770
canonical acquisition QIDs       1,770
historical QID -> HullQ mappings 1,772
```

The two historical non-canonical reserved mappings remain excluded from the canonical BoatModel boundary exactly as in the accepted SLICE-0028/0030 inputs.

## Corrected Tier-1 evidence profile

The fixed five-field corrected/current normalized-candidate marginals reproduce the accepted SLICE-0030 result:

```text
LOA            888
LWL            848
beam           891
draft          691
displacement   858
```

The normalized-field-count distribution over exactly 1,770 canonical BoatModels is:

```text
0 fields   787
1 field     28
2 fields    65
3 fields    53
4 fields   326
5 fields   511
```

Therefore:

```text
>=3 fields  890
>=4 fields  837
all 5       511
```

The distribution sums exactly to 1,770.

## Predecessor and corrected precursor

The accepted predecessor evidence precursor was independently recomputed from the pre-correction retained evidence as:

```text
LOA + beam + (draft OR displacement)
607 / 1770 = 34.2938%
```

Under the corrected SLICE-0030 evidence path, the same joint BoatModel-level condition measures:

```text
817 / 1770 = 46.1582%
```

Delta:

```text
absolute                +210 BoatModels
percentage-point delta  +11.8644 pp
```

The corrected precursor-positive models decompose exactly as:

```text
draft only          55
displacement only  213
both                549
-----------------------
total               817
```

The corrected precursor is computed from joint per-BoatModel evidence; it is not inferred arithmetically from marginal field totals.

## Strong technical-evidence subsets

The retained strong evidence diagnostics are:

```text
LOA + beam + draft + displacement                 549
LOA + LWL + beam + (draft OR displacement)        753
all five fixed fields                             511
>=4/5 normalized with no disagreement diagnostic 831
```

These remain evidence diagnostics only and do not define canonical production coverage.

## Positive-control candidate pool

The fixed deterministic eligibility/ranking rule produced:

```text
eligible candidate count       784
retained candidate pool size    20
pool result                     POSITIVE_CONTROL_POOL_AVAILABLE
```

The two already-researched SLICE-0029 Catalina negative controls are excluded:

```text
Q5051252  Catalina 22
Q5051253  Catalina 30
```

The retained ranked pool is:

```text
01  Q104861437  BM_WDT0_003ba28d4cd143d68c28e57899a3ed73
02  Q104829866  BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb
03  Q60521258   BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60
04  Q85753944   BM_WDT0_041b206a55fe490785620b29a2af443a
05  Q85753415   BM_WDT0_074f8ccc869342d2b392e9a315709b1b
06  Q60755809   BM_WDT0_0773da973b2c47dd84dc1e271b3c16fd
07  Q105742651  BM_WDT0_07e7ebd154244b9cb8ccaa61589af3e4
08  Q60521277   BM_WDT0_08f47683f0b9435ca508cc7cc7e1e602
09  Q55071986   BM_WDT0_090a42a1e08641da98a840cd97b671ce
10  Q5463514    BM_WDT0_0aeb784a1cef4706982266379b9cc1e0
11  Q105474389  BM_WDT0_0b14fb0af9f643d993fc30f395cb32d8
12  Q7321000    BM_WDT0_0bd15dbd17cf44eea09203f4a6bac262
13  Q65076969   BM_WDT0_0c19ffaccdae401180f2d6ebeae99c39
14  Q105753294  BM_WDT0_0cdf302bff774223b68cf610ea754ea8
15  Q60521224   BM_WDT0_0d3dc025a4f64baea4f61b644fb94722
16  Q104902894  BM_WDT0_0d7b18ff7c14471e8dbc17ae665dcfaf
17  Q106075875  BM_WDT0_0e8528d46b5b44caa5e2eae217215c8a
18  Q60740478   BM_WDT0_10717b8f0c114505aed1bd2011f7f38e
19  Q66737997   BM_WDT0_11226d16987e4d86bf35fbcced51fc0f
20  Q60743939   BM_WDT0_1184b9a1439c42689b3147977632c75f
```

All retained top-20 candidates have five normalized Tier-1 fields, both draft and displacement present, and LWL present; final stable ordering is canonical `hullq_id` ascending after the earlier fixed ranking keys tie.

The candidate pool is evidence-selection only. It does **not** establish a BoatDesign generation boundary, source-right clearance, applicability or a promotable canonical value for any candidate, and it does not authorize external research without a separately readied later slice.

## CAL-01 / launch-threshold boundary

The implementation preserves the required interpretation boundary:

- corrected measurements may be used as calibration input;
- normalized research evidence is not relabeled as canonical basic-searchable coverage;
- no CAL-01 D2/D2b threshold is declared met;
- no G4 pass is declared;
- no launch percentage threshold is invented or frozen;
- the evidence precursor is not substituted for BoatDesign applicability + FieldResolution/canonical promotion.

## Canonical mutation and network boundary

SLICE-0031 creates/mutates zero canonical BoatModel, BoatDesign or FieldResolution data and writes no canonical technical value.

The accepted primary replay/verification path is fully offline and uses only the already-accepted SLICE-0028/0030 retained inputs. No new discovery query or 1,770-entity reacquisition is performed.

Accepted prior retained packages are not modified.

## Retained evidence package

The bounded retained package is:

`research/stage3/sl0031-corrected-tier1-evidence-profile/`

It contains:

- `boatmodel_evidence_profile.json` + schema;
- `aggregate_profile.json` + schema;
- `positive_control_candidates.json` + schema;
- `REPORT.md`;
- `ARTIFACT-DIGESTS.json` + schema.

`ARTIFACT-DIGESTS.json` covers every retained SLICE-0031 package file except the digest manifest itself. The offline verifier re-verifies accepted SLICE-0028/0030 inputs, independently re-derives the corrected/predecessor state, validates schemas, checks self-consistency and checks artifact digests.

## Validation evidence

Final reviewed implementation head:

`c52360703b11d69fc9993d8fe9b8f7ce559fddc5`

Implementation-agent local validation reported:

- repository governance: PASS;
- Ruff format/lint: PASS;
- mypy: PASS (45 source files);
- full test run: **2,126 passed / 217 skipped**;
- total coverage: **90.80%** (>=90% gate);
- SLICE-0031 offline verifier: PASS.

Independent exact-head remote verification confirmed:

- CI run `33155871659`: SUCCESS on exact head `c52360703b11d69fc9993d8fe9b8f7ce559fddc5`;
  - dependency audit: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - PostgreSQL 18 db integration: SUCCESS, including the SLICE-0031 offline-verification step;
- Manufacturer artifact reproducibility run `33155871690`: SUCCESS on the same exact head on Ubuntu and Windows.

Implementation PR #89 was merged as:

`7a20ed0759b89ded8ce845ea88dc9b32c55e5eff`

## Retained evidence trail

- controlling contract: `docs/slices/SLICE-0031-corrected-tier1-evidence-profile-positive-control-selection.md`;
- retained package: `research/stage3/sl0031-corrected-tier1-evidence-profile/`;
- implementation PR: #89;
- final reviewed implementation head: `c52360703b11d69fc9993d8fe9b8f7ce559fddc5`;
- implementation merge commit: `7a20ed0759b89ded8ce845ea88dc9b32c55e5eff`;
- exact-head CI run `33155871659`, SUCCESS;
- exact-head manufacturer reproducibility run `33155871690`, SUCCESS;
- final independent-review submission: PR #89 review `5049491620`;
- independent-review verdict: **ACCEPT — no blocking or material findings remain**;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records independent acceptance of the SLICE-0031 implementation but does not itself mark SLICE-0031 `DONE` and does not authorize SLICE-0032.

The retained positive-control pool is input to a later independent readiness decision only. Any external manufacturer/source research, BoatDesign/applicability pilot, canonical promotion or SLICE-0032 work remains separately gated.

Explicit Project Owner acceptance is required next. After that acceptance, the normal `FINISH_SLICE` -> independent readiness -> `START_SLICE` workflow may continue.
