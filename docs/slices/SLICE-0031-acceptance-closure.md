# SLICE-0031 — Acceptance Closure

**ID:** SLICE-0031  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Final independent-review verdict:** ACCEPT — implementation plus bounded fail-closed amendment reviewed; no blocking or material findings remain  

## Implementation and amendment trail

Initial implementation:

- implementation PR: #89 — `SLICE-0031: corrected Tier-1 evidence profile + positive-control candidate selection`;
- reviewed implementation head: `c52360703b11d69fc9993d8fe9b8f7ce559fddc5`;
- implementation merge commit: `7a20ed0759b89ded8ce845ea88dc9b32c55e5eff`;
- exact-head CI: run `33155871659`, SUCCESS;
- exact-head Manufacturer artifact reproducibility: run `33155871690`, SUCCESS;
- initial independent-review submission: PR #89 review `5049491620`.

Before Project Owner acceptance, a stricter adversarial re-review identified a fail-closed verifier defect in the retained positive-control pool contract. The stale first closure PR #90 was therefore closed unmerged and superseded rather than being accepted against an implementation state that no longer represented the final reviewed result.

Bounded amendment:

- amendment PR: #91 — `SLICE-0031 amendment: fail-closed positive-control pool verification`;
- final amendment head: `1c988fc9dda421ac79951bd76ee231e7ae65c342`;
- amendment merge commit: `cfe953d45da4de255eb7d92b11ebb060105694f3`;
- exact-head CI: run `33160513986`, SUCCESS;
- exact-head Manufacturer artifact reproducibility: run `33160513847`, SUCCESS;
- final independent-review submission: PR #91 review `5049949512`;
- final verdict: **ACCEPT**.

The effective SLICE-0031 implementation state for owner acceptance is therefore the original implementation plus the merged bounded amendment at main commit `cfe953d45da4de255eb7d92b11ebb060105694f3`.

## Final independent review result

Independent review accepts SLICE-0031 for explicit Project Owner acceptance. The slice is **not DONE yet**. Project Owner acceptance remains a separate required governance action.

The final review explicitly included a contract-matrix pass, invariant/fail-closed review, adversarial verifier review, tamper/counterexample review, exact-head CI confirmation and Manufacturer reproducibility confirmation.

The key adversarial question was tested directly: whether a coherently falsified retained artifact could control its own verification parameters and still validate. The amended verifier now fails closed for that attack.

## Fixed identity boundary

The final accepted result reproduces exactly:

```text
canonical BoatModels             1,770
canonical acquisition QIDs       1,770
historical QID -> HullQ mappings 1,772
```

The two historical non-canonical reserved mappings remain excluded from the canonical BoatModel boundary exactly as in the accepted SLICE-0028/0030 inputs.

## Corrected Tier-1 evidence profile

The five corrected/current normalized-candidate marginals remain:

```text
LOA            888
LWL            848
beam           891
draft          691
displacement   858
```

Normalized-field-count distribution over 1,770 canonical BoatModels:

```text
0 fields   787
1 field     28
2 fields    65
3 fields    53
4 fields   326
5 fields   511
```

Cumulative:

```text
>=3 fields  890
>=4 fields  837
all 5       511
```

The distribution sums exactly to 1,770.

## Predecessor and corrected precursor

The predecessor source-evidence precursor independently recomputes to:

```text
LOA + beam + (draft OR displacement)
607 / 1770 = 34.2938%
```

Under the corrected SLICE-0030 evidence path:

```text
817 / 1770 = 46.1582%
```

Delta:

```text
absolute                +210 BoatModels
percentage-point delta  +11.8644 pp
```

Overlap decomposition:

```text
draft only          55
displacement only  213
both                549
-----------------------
total               817
```

The corrected precursor is computed from joint per-BoatModel evidence and is not inferred from field marginals.

## Strong technical-evidence subsets

```text
LOA + beam + draft + displacement                 549
LOA + LWL + beam + (draft OR displacement)        753
all five fixed fields                             511
>=4/5 normalized with no disagreement diagnostic 831
```

These are source-evidence diagnostics only, not canonical production coverage definitions.

## Positive-control candidate pool

Final retained result:

```text
eligible candidate count       784
candidate pool limit             20
retained candidate pool size     20
pool result                     POSITIVE_CONTROL_POOL_AVAILABLE
```

The two already-researched SLICE-0029 Catalina negative controls remain excluded:

```text
Q5051252  Catalina 22
Q5051253  Catalina 30
```

The candidate pool remains evidence-selection only. It does not establish BoatDesign generation boundaries, applicability, source-right clearance or canonical technical promotion, and it does not authorize external research without a separately readied later slice.

## Fail-closed amendment

The post-merge adversarial review found that the first implementation allowed the retained document's own `candidate_pool_limit` to become verification input. Because the artifact builder also derived `pool_result` from the post-limit truncated list, a coherently tampered retained artifact could potentially set:

```text
candidate_pool_limit = 0
candidate_pool_size  = 0
candidates           = []
pool_result          = NO_POSITIVE_CONTROL_POOL
```

while real eligible candidates existed, and make the verifier rebuild against the attacker-controlled limit.

The accepted amendment fixes this invariant at four layers:

1. retained `candidate_pool_limit` is non-parameterizable and fixed to `20` by code;
2. the verifier independently rebuilds against the fixed `CANDIDATE_POOL_LIMIT`, never the retained artifact value, and explicitly rejects any non-20 retained limit;
3. the retained schema constrains `candidate_pool_limit` with `const: 20` and pool size to at most 20;
4. `pool_result` is derived from the full eligible set before truncation: eligible count greater than zero means `POSITIVE_CONTROL_POOL_AVAILABLE`; zero eligible means `NO_POSITIVE_CONTROL_POOL`.

Focused regressions cover zero/non-20 limit tampering, the coherent zero-limit/empty-list/result-flip attack, pool-result flips in both directions, direct schema rejection, normal fixed semantics, deterministic ranking and Catalina exclusion.

The amendment changed no measured evidence result. Regenerated SLICE-0031 artifacts differ only where required by generated timestamps, schema/verifier contract and corresponding digests.

## CAL-01 / launch-threshold boundary

The final implementation preserves the required interpretation boundary:

- corrected measurements may be calibration input;
- normalized research evidence is not relabeled canonical basic-searchable coverage;
- no CAL-01 D2/D2b threshold is declared met;
- no G4 pass is declared;
- no launch percentage threshold is invented or frozen;
- evidence precursor is not substituted for BoatDesign applicability plus FieldResolution/canonical promotion.

## Canonical mutation and network boundary

SLICE-0031 creates or mutates zero canonical BoatModel, BoatDesign or FieldResolution data and writes no canonical technical value.

The retained replay/verification path is offline and uses the already-accepted SLICE-0028/0030 retained inputs. No new boat discovery query or 1,770-entity reacquisition is part of the slice or amendment.

Accepted SLICE-0026/0027/0028/0029/0030 retained packages are untouched.

## Retained evidence package

`research/stage3/sl0031-corrected-tier1-evidence-profile/`

contains the profile, aggregate, candidate-pool documents and schemas, `REPORT.md`, and digest manifest. The offline verifier re-verifies accepted fixed inputs, independently re-derives the evidence state, validates schemas, checks self-consistency and checks retained artifact digests.

## Final validation evidence

Amendment-agent local validation reported:

- repository governance: PASS;
- Ruff format/lint: PASS;
- mypy: PASS (45 source files);
- full test run: **2,135 passed / 217 skipped**;
- total coverage: **90.82%** (>=90% gate);
- SLICE-0031 offline verifier: PASS.

Independent exact-head remote verification on final amendment head `1c988fc9dda421ac79951bd76ee231e7ae65c342` confirmed:

- CI run `33160513986`: SUCCESS;
  - dependency audit: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - PostgreSQL 18 db integration: SUCCESS, including SLICE-0031 offline verification;
- Manufacturer artifact reproducibility run `33160513847`: SUCCESS on Ubuntu and Windows.

## Retained audit trail

- controlling contract: `docs/slices/SLICE-0031-corrected-tier1-evidence-profile-positive-control-selection.md`;
- implementation PR #89;
- implementation head `c52360703b11d69fc9993d8fe9b8f7ce559fddc5`;
- implementation merge `7a20ed0759b89ded8ce845ea88dc9b32c55e5eff`;
- original independent review `5049491620`;
- post-implementation adversarial blocker recorded on superseded closure PR #90 review `5049571442`;
- amendment PR #91;
- amendment head `1c988fc9dda421ac79951bd76ee231e7ae65c342`;
- amendment merge `cfe953d45da4de255eb7d92b11ebb060105694f3`;
- final independent amendment review `5049949512`;
- final exact-head CI `33160513986`, SUCCESS;
- final exact-head Manufacturer reproducibility `33160513847`, SUCCESS;
- superseded closure PR #90: closed unmerged;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records final independent acceptance of SLICE-0031 after the bounded amendment. It does not itself mark the slice DONE and does not authorize SLICE-0032.

Any later external manufacturer/source research, BoatDesign/applicability pilot, canonical promotion or next slice remains separately gated.

Explicit Project Owner acceptance is required next. After owner acceptance, the normal `FINISH_SLICE` -> independent readiness -> `START_SLICE` workflow may continue.
