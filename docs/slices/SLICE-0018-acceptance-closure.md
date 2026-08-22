# SLICE-0018 — Acceptance Closure

**ID:** SLICE-0018  
**Final status:** DONE  
**Accepted:** 2026-08-22  
**Implementation PR:** #37  
**Accepted implementation head:** `cbc93582c7ed93aa7a4253ac58868f7e79e266cc`  
**Merge commit:** `213ec3b13769708b1d996b3266a9e9c19fabbb45`

## Acceptance result

SLICE-0018 is explicitly accepted by the project owner and closed as `DONE`.

The slice extended HullQ's accepted Wikidata Tier-0 identity universe from the immutable SLICE-0017 1,000-candidate baseline to the deterministic first-<=2,500 direct sailboat-class discovery window. The live source returned **1,829** unique QIDs rather than 2,500; per the controlling contract this measured source ceiling was retained as fact and was not padded from another source.

SLICE-0018 preserved four separate states throughout: the accepted SLICE-0017 baseline, the historical retained QID→HullQ-ID crosswalk, the current SLICE-0018 discovery window, and the SLICE-0018 expansion delta. Only the expansion delta received new decisions.

It did not reinterpret or mutate the accepted SLICE-0017 baseline, infer Brand/Organization/BoatDesign entities, resolve the prior review queue, perform Tier-1/Tier-2 technical enrichment, switch bootstrap source, or authorize a later 5,000-window expansion.

## Final accepted production measurement

The one authorized live Wikidata acquisition retained:

- requested discovery limit: **2,500**;
- shared hard safety ceiling: **3,000**;
- unique discovery QIDs returned: **1,829**;
- target reached: **false**;
- overlap with accepted SLICE-0017 baseline: **1,000**;
- accepted baseline QIDs absent from current discovery: **0**;
- expansion delta: **829**;
- delta `AUTO_ADMIT`: **805**;
- delta `REVIEW_REQUIRED`: **16**;
- delta `NOT_ADMITTED`: **8**;
- delta↔baseline collision records: **6**;
- delta↔delta collision clusters: **6**;
- delta entities fetched/processed: **829 / 829**;
- acquisition failures/throttle/malformed omissions: **0**;
- retained historical QID→HullQ-ID mappings after expansion: **1,772**;
- delta ResearchObservations / replayable bundles: **821**;
- delta canonical evidence links / admissions: **805**;
- expected combined canonical BoatModels: **1,770**.

Final deterministic delta reason counts were:

- `ok`: **805**;
- `name_collision`: **16**;
- `missing_label`: **8**.

The original live acquisition timestamp remained `2026-08-21T20:31:34.113774+00:00`. Later corrections used retained data offline only; no second live Wikidata acquisition was authorized or observed.

## Final accepted evidence

Exact accepted implementation head:

`cbc93582c7ed93aa7a4253ac58868f7e79e266cc`

GitHub Actions CI run **#208** (`32540170666`) passed on the accepted PR head.

Verified CI jobs:

- quality / Ubuntu: PASS;
- quality / Windows: PASS;
- dependency audit: PASS;
- db integration / PostgreSQL 18: PASS;
- retained Stage-2 benchmark: PASS with exact recommendation `G3_PASS`;
- SLICE-0017 baseline manifest validation/replay: PASS;
- SLICE-0018 manifest schema validation: PASS;
- SLICE-0018 baseline-first/delta-second replay: PASS;
- SLICE-0018 zero-tolerance verification: PASS.

The remote PostgreSQL job ran against PostgreSQL **18.6** and independently verified the accepted SLICE-0017 manifest fingerprint `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845` before applying the delta.

### First isolated schema

- accepted baseline bundles / admissions: **985 / 965**;
- baseline verified before delta: exact counts, exact canonical ID set, **0** readback mismatches;
- combined expected bundles / admissions: **1,806 / 1,770**;
- combined imported bundles / admissions: **1,806 / 1,770**;
- first-pass already-present/conflict/error/unexpected statuses: **0**;
- combined semantic readback mismatches: **0**;
- post-delta accepted-baseline drift mismatches: **0**;
- unexpected canonical rows for review/non-admitted candidates: **0**;
- exact combined canonical BoatModel ID set equality: PASS;
- stray canonical Brand rows: **0**;
- stray canonical Organization rows: **0**;
- stray canonical BoatDesign rows: **0**.

### Exact re-import

- `ALREADY_IMPORTED`: **3,576** total bundle+admission operations;
- conflicts: **0**;
- errors: **0**.

### Independent fresh schema

- combined bundles imported: **1,806**;
- combined admissions imported: **1,770**;
- accepted baseline verified before delta: exact;
- semantic mismatches: **0**;
- post-delta baseline drift mismatches: **0**;
- exact combined canonical BoatModel ID set equality: PASS;
- stray Brand/Organization/BoatDesign rows: **0 / 0 / 0**;
- expected import counts: PASS.

Final replay result:

`all_zero_tolerance_conditions_clear = true`

## Retained CI artifacts

SLICE-0018 expansion artifact from CI #208:

- artifact ID: `9466761747`;
- digest: `sha256:2037d92cd56296878f8e8290102dd473376a20ccee755f893454ad9bc81a12d4`.

The artifact contains the retained SLICE-0018 manifest/report plus the exact CI replay result/report.

Retained Stage-2 benchmark artifact from the same CI run:

- artifact ID: `9466747867`;
- digest: `sha256:fd924b8f600c43b2ec2b623d0ad69ed53ca2fcd80722319db1079c56dd1709f2`;
- recommendation: exact `G3_PASS`.

## Final implementation-agent local report

After the independent-review correction round the implementation agent reported:

- **1,656 passed, 2 skipped** locally;
- coverage: **94.88%** overall;
- repository validator: PASS (88/88);
- Ruff lint/format: CLEAN;
- strict mypy: PASS;
- `pip-audit`: no known vulnerabilities;
- PostgreSQL 18.6 replay: zero-tolerance clear;
- no live network request during the correction round.

Remote quality CI independently reported **1,451 passed, 207 skipped** in the non-DB job with **94.49%** coverage; the database integration job separately ran **205 persistence tests**, all passing.

## Independent-review hardening retained

The accepted implementation includes the following review-driven protections:

1. historical SLICE-0018 QID→HullQ-ID mappings survive later discovery-window omission and are reused byte-for-byte on reappearance;
2. current candidate rows remain current-delta-only and are not used as an identity-history registry;
3. historical crosswalk merges fail closed on same-QID/different-ID and same-ID/different-QID conflicts;
4. entity acquisition must cover the expected delta QIDs exactly; missing, unexpected or duplicate QIDs fail closed before manifest replacement;
5. the manifest builder independently verifies that candidate QIDs equal the exact current expansion delta;
6. overlap is computed directly from discovery∩baseline QID sets;
7. SLICE-0018 rejects a discovery limit above 2,500 before adapter/network use while retaining the shared 3,000 hard ceiling;
8. the accepted SLICE-0017 manifest is protected by an exact pinned raw-byte SHA256 in addition to aggregate checks;
9. duplicate accepted-baseline candidate QIDs fail closed explicitly;
10. accidental baseline QIDs or duplicate QIDs passed as delta input fail closed before classification;
11. accepted baseline replay occurs before delta replay and is rechecked after delta application for exact zero drift;
12. the checked-in report distinguishes original live acquisition, offline recomputation, local PostgreSQL evidence and remote exact-head CI evidence.

## Accepted boundary carried forward

The accepted combined Stage-3 Tier-0 identity state now consists of:

- immutable accepted SLICE-0017 baseline artifact: **1,000** candidate decisions, **965** accepted canonical BoatModels and **967** retained baseline mappings;
- separate accepted SLICE-0018 expansion artifact: **1,829** discovery QIDs and an **829**-candidate expansion delta;
- **805** additional accepted sparse canonical BoatModels from the delta;
- **16** new review-bound delta candidates;
- **8** new non-admitted delta candidates;
- **1,772** retained historical QID→HullQ-ID mappings in the expanded registry;
- **1,770** accepted combined sparse canonical BoatModels after baseline+delta replay.

The accepted source result is also a planning fact: the direct-instance Wikidata query used for this bootstrap family returned **1,829**, not 2,500. A future slice must therefore make an explicit evidence/source decision rather than pretending that simply increasing the limit will create additional direct-instance candidates.

## Next boundary

No SLICE-0019 or other later slice is made `READY` by this closure.

Any next Stage-3 step — for example another bootstrap source, a deliberately different Wikidata discovery strategy, manufacturer-universe research, review-resolution work, technical enrichment, or another coverage mechanism — requires its own bounded contract, source-rights analysis where applicable, explicit acceptance criteria and normal `START_SLICE.bat` workflow.

In particular, this closure does **not** authorize a 5,000-window rerun, source padding, broad enrichment, query/API/frontend work, marketplace work, monitoring, or price-history implementation.