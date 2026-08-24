# HullQ Slice Index

**Status:** ACTIVE execution board  
**Updated:** 2026-08-24 (SLICE-0020 owner-accepted / DONE)

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, ADRs or accepted slice contracts.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Repository bootstrap, locked toolchain and cross-platform CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Independent sailboat-design source research and seed evidence | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | DONE | Canonical JSON-Schema contract runtime | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | DONE | Measurement observation + deterministic normalization | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | DONE | Brand/Organization + BoatModel/BoatDesign identity contracts and search labels | SLICE-0004 / ADR-0011 |
| SLICE-0006 | IMPLEMENTATION | DONE | FieldEvidence/FieldResolution provenance boundary | SLICE-0005 / ADR-0006 |
| SLICE-0007 | IMPLEMENTATION | DONE | ResearchJob + source-rights/use gate + extraction telemetry | SLICE-0006 / ADR-0005 |
| SLICE-0008 | IMPLEMENTATION | DONE | First rights-gated real adapter: Wikidata CC0 | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | DONE | Appendage/configuration normalization | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | DONE | `hullq-derived-1.0.0` derived metrics | SLICE-0009 / ADR-0008 |
| SLICE-0011 | DESIGN_RESEARCH | DONE | Controlled 50-design real-web stress benchmark | SLICE-0010 |
| SLICE-0012 | IMPLEMENTATION | DONE | Pre-canonical ResearchObservation, claim/applicability semantics, explicit promotion and ResearchEvidenceBundle | SLICE-0011 |
| SLICE-0013 | IMPLEMENTATION | DONE | PostgreSQL 18 migrations + lossless deterministic ResearchEvidenceBundle importer | SLICE-0012 accepted / DONE |
| SLICE-0014 | DESIGN_RESEARCH | DONE | Run the accepted 50-design benchmark through the real PostgreSQL persistence path and measure determinism/review/throughput | SLICE-0013 accepted / DONE |
| SLICE-0015 | IMPLEMENTATION | DONE | Harden benchmark failure paths and make the Stage-2 Gate G3 decision using the fixed pre-committed scorecard | SLICE-0014 accepted / DONE |
| SLICE-0016 | IMPLEMENTATION | DONE | Canonical Brand/Organization/BoatModel/BoatDesign PostgreSQL persistence + explicit bootstrap-admission boundary | SLICE-0015 accepted / DONE / G3 PASS |
| SLICE-0017 | IMPLEMENTATION | DONE | Controlled Wikidata Tier-0 identity bootstrap across the first 1,000 direct sailboat-class candidates | SLICE-0016 accepted / DONE |
| SLICE-0018 | IMPLEMENTATION | DONE | Baseline-preserving Wikidata Tier-0 expansion to the first <=2,500 direct sailboat-class discovery window | SLICE-0017 accepted / DONE |
| SLICE-0019 | DESIGN_RESEARCH | DONE | Global active+historical series-sailboat manufacturer/yard universe + source-yield study | SLICE-0018 accepted / DONE |
| SLICE-0020 | DESIGN_RESEARCH | DONE | Manufacturer archive source-clearance assessment + bounded (<=20/source) identity-yield pilot over a fixed 10-source sample | SLICE-0019 accepted / DONE |

## Current execution rule

**SLICE-0001 through SLICE-0020 are accepted / `DONE`.** SLICE-0020's contract is `docs/slices/SLICE-0020-manufacturer-archive-source-clearance-identity-expansion-pilot.md`; its closure record is `docs/slices/SLICE-0020-acceptance-closure.md`.

SLICE-0020 is a bounded DESIGN_RESEARCH slice. It assessed use-specific rights/access clearance for a fixed, precommitted sample of ten manufacturer/heritage archive surfaces and ran a strictly bounded (<=20 model identities per source, <=200 total), research-only identity-yield pilot against those same surfaces. It did not authorize, build or stage a production adapter, did not perform automated/bulk acquisition, and did not create or modify any canonical Brand/Organization/BoatModel/BoatDesign row. The measured result is a truthful zero `ADAPTER_READY` sources (9 `RESEARCH_ONLY`/`REVIEW_REQUIRED`, 1 `BLOCKED` — Bénéteau); this was not padded or rounded up. See `research/manufacturers/archive_clearance/ARCHIVE_SOURCE_CLEARANCE_REPORT.md`.

SLICE-0020's acceptance does not authorize SLICE-0021. **No later slice is currently `READY`.**

SLICE-0019 was a DESIGN_RESEARCH slice. It did not ingest a new production dataset. It built an evidence-backed global active+historical manufacturer/yard research registry and measured which source surfaces can credibly extend HullQ beyond the accepted direct-instance Wikidata ceiling.

The accepted SLICE-0018 measurement remains the input boundary: **1,829** unique direct-instance Wikidata sailboat-class QIDs, **829** expansion-delta candidates and **1,770** accepted combined sparse canonical BoatModels.

No 5,000 rerun, new production-source ingestion, broad technical enrichment, review-queue campaign, query engine, API, frontend, marketplace or monitoring work is authorized merely by SLICE-0019's closure.

## SLICE-0020 acceptance closure

SLICE-0020 is explicitly accepted and `DONE`.

Acceptance evidence:

- independent-review verdict: **ACCEPT**;
- original implementation/research PR #47, initial head `1ca06c3`;
- independent review returned **AMEND**; amendment `44ed42c` corrected Elan/Hallberg-Rassy provenance, removed the unsupported Elan E3 and Bénéteau First 32/38 hazards, and tightened the exact-match whitespace semantics; a second docs-only amendment `ced1880` corrected the report's own characterization of that implementation correction;
- final reviewed / accepted head: `ced18800c20a6a2c328794d3af5cb0686d59c20d`;
- implementation/research merge commit: `5c2a9cc40a05fbaebe2a4db2bcfff7d3498a58d9` (PR #47);
- exact-head CI run #250 (`32727915597`): SUCCESS — quality (ubuntu-latest), quality (windows-latest), db integration (PostgreSQL 18), dependency audit all SUCCESS;
- fixed sources assessed: **10**; source-clearance result: **0** `ADAPTER_READY` / **9** `RESEARCH_ONLY`/`REVIEW_REQUIRED` / **1** `BLOCKED` (Bénéteau);
- bounded identity pilot: **100** total identities (10 per source); exact-overlap result: **9** `exact_overlap` / **91** `no_exact_overlap_signal` / **0** `unresolved_possible_overlap`;
- no canonical Brand/Organization/BoatModel/BoatDesign rows created or modified;
- no SailboatData value used as HullQ production evidence;
- research ownership: ChatGPT performed the external research/orchestration pass; Claude performed repository integration/deterministic computation/validation only;
- explicit project-owner acceptance on 2026-08-24.

Final closure record: `docs/slices/SLICE-0020-acceptance-closure.md`.

## SLICE-0019 acceptance closure

SLICE-0019 is explicitly accepted and `DONE`.

Acceptance evidence:

- independent-review verdict: **ACCEPT** — all 16 SLICE-0019 acceptance criteria PASS;
- original research PR #42, merged as `dd4caebb4859ef3404afbc8e8d107cfcccd22969`;
- independent-review amendment PR #43, final reviewed head `98a8916b7634250cf6540ea21abe497b2d664234`;
- amendment merge commit: `0f8b94609c6d0886b72caa521f6ee9d5258f0d0f`;
- post-merge CI run ID `32653479069`: SUCCESS;
- retained registry: **136** total records, **129** verified, **1** needs_review, **6** excluded;
- strict verified manufacturer/yard floor: **121** (>=120 floor: PASS);
- countries: **25** (>=20 floor: PASS); macro-regions: **8** (>=5 floor: PASS);
- historical/defunct/acquired/renamed strict-floor records: **61** (>=40 floor: PASS);
- recognized heritage/archive surfaces under the corrected strict definition: **61** (>=25 floor: PASS);
- 20-entity source-yield sample: complete;
- overlap probe: **57** model identities / **8** exact overlap / **0** unresolved possible overlap / **49** clearly new;
- no canonical Brand/Organization/BoatModel/BoatDesign rows created or modified;
- no SailboatData value used as HullQ production evidence;
- explicit project-owner acceptance on 2026-08-23.

Final closure record: `docs/slices/SLICE-0019-acceptance-closure.md`.

## SLICE-0018 acceptance closure

SLICE-0018 is explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `cbc93582c7ed93aa7a4253ac58868f7e79e266cc`;
- implementation PR: #37;
- implementation merge commit: `213ec3b13769708b1d996b3266a9e9c19fabbb45`;
- GitHub Actions CI run #208 (`32540170666`): PASS on the accepted PR head;
- PostgreSQL **18.6** integration: PASS;
- persistence suite: **205 passed**;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- retained Stage-2 benchmark: exact `G3_PASS`;
- requested discovery limit / safety ceiling: **2,500 / 3,000**;
- live discovery: **1,829** unique QIDs, target not reached, no source padding;
- accepted-baseline overlap / absent: **1,000 / 0**;
- expansion delta: **829**;
- delta decisions: **805 AUTO_ADMIT / 16 REVIEW_REQUIRED / 8 NOT_ADMITTED**;
- delta↔baseline collision records: **6**;
- delta↔delta collision clusters: **6**;
- retained historical QID→HullQ-ID mappings: **1,772**;
- expected combined sparse canonical BoatModels: **1,770**;
- first combined replay: **1,806/1,806** ResearchEvidenceBundles and **1,770/1,770** canonical admissions imported;
- accepted baseline verified exact before delta and unchanged after delta;
- combined semantic readback mismatches: **0**;
- unexpected canonical rows for non-admitted candidates: **0**;
- Brand/Organization/BoatDesign rows inferred: **0 / 0 / 0**;
- exact re-import: **3,576 ALREADY_IMPORTED**, 0 conflicts/errors;
- independent fresh-schema replay: **1,806** bundles + **1,770** admissions, 0 semantic mismatches, exact ID set, 0 stray Brand/Organization/BoatDesign rows;
- `all_zero_tolerance_conditions_clear = true`;
- SLICE-0018 CI artifact ID: `9466761747`;
- artifact digest: `sha256:2037d92cd56296878f8e8290102dd473376a20ccee755f893454ad9bc81a12d4`;
- benchmark artifact ID: `9466747867`;
- benchmark artifact digest: `sha256:fd924b8f600c43b2ec2b623d0ad69ed53ca2fcd80722319db1079c56dd1709f2`;
- implementation-agent final local report: **1,656 passed, 2 skipped**;
- reported local coverage: **94.88%**;
- remote non-DB quality coverage: **94.49%**;
- repository validator / Ruff / strict mypy / pip-audit: PASS/CLEAN;
- independent review: five identified blockers corrected; final re-review found no remaining blocker;
- correction round used retained artifacts offline and performed no second live Wikidata acquisition;
- explicit project-owner acceptance on 2026-08-22.

Final closure record: `docs/slices/SLICE-0018-acceptance-closure.md`.

Accepted Stage-3 bootstrap semantics now additionally include:

- accepted SLICE-0017 baseline protected by exact pinned raw-byte SHA256 before SLICE-0018 work/replay;
- current discovery window, expansion delta and historical crosswalk structurally separate;
- historical mappings survive omission and reuse the byte-identical HullQ ID on reappearance;
- exact entity-acquisition completeness before classification/manifest replacement;
- exact candidate-set equality to discovery-minus-baseline enforced again inside manifest construction;
- 2,500 slice-level window bound enforced before adapter/network use while preserving the shared 3,000 hard ceiling;
- baseline QIDs and duplicate QIDs rejected if accidentally supplied as delta input;
- overlap measured directly from QID-set intersection;
- baseline-first/delta-second PostgreSQL replay with exact baseline re-verification after delta;
- no automatic Brand/Organization/BoatDesign invention;
- normal CI remains fully offline with respect to Wikidata.

## SLICE-0017 acceptance closure

SLICE-0017 is explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `34c2de8fc99ab6babad054a4186cee168cc3a2da`;
- GitHub Actions CI run #200 (`32499124689`): PASS on the exact accepted head;
- PostgreSQL **18.6** integration: PASS;
- persistence suite: PASS with **203** PostgreSQL tests;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- retained Stage-2 benchmark: exact `G3_PASS`;
- final retained bootstrap: **1,000 candidates / 965 AUTO_ADMIT / 20 REVIEW_REQUIRED / 15 NOT_ADMITTED**;
- deterministic collision clusters: **10**;
- retained historical QID→HullQ-ID mappings: **967**;
- first production replay: **985/985** ResearchEvidenceBundles and **965/965** canonical admissions imported;
- first-pass conflicts/errors/unexpected statuses: **0**;
- deep semantic readback mismatches: **0**;
- unexpected canonical rows for non-admitted candidates: **0**;
- Brand/Organization/BoatDesign rows inferred: **0 / 0 / 0**;
- exact re-import: **1,950 ALREADY_IMPORTED**, 0 conflicts/errors;
- independent fresh-schema replay: **985** bundles + **965** admissions, 0 semantic mismatches, exact ID set, 0 stray Brand/Organization/BoatDesign rows;
- `all_zero_tolerance_conditions_clear = true`;
- bootstrap artifact ID: `9452810477`;
- bootstrap artifact digest: `sha256:3161e6f43572dcbcafbd6512becc2aea7be44b2f8d1ae56234e49ef37a5eb034`;
- benchmark artifact ID: `9452803532`;
- benchmark artifact digest: `sha256:6cb1414ac7b9c90393ba1545c4fd89adb67fbe298d367d42a29c51775c09684c`;
- implementation-agent final local report: **1,407 passed, 205 skipped**;
- reported coverage: **94.29%**;
- repository validator / Ruff / strict mypy / pip-audit: PASS/CLEAN;
- independent review: all identified blockers corrected; final review found no remaining blocker;
- explicit project-owner acceptance on 2026-08-21;
- PR #35 merged on 2026-08-21;
- merge commit: `e2001d3a926c08706558b6cb97962f235c843379`.

Final closure record: `docs/slices/SLICE-0017-acceptance-closure.md`.

Accepted Stage-3 bootstrap semantics now include:

- rights-gated deterministic direct-instance discovery;
- safe sparse Tier-0 BoatModel admission only;
- accepted HullQ search-key semantics for collision detection;
- stable content-derived alias IDs;
- stable opaque HullQ IDs not derived from QID/name;
- historical retained QID→HullQ-ID mapping structurally separate from current candidate rows;
- fail-closed crosswalk conflict detection in both directions before live network use;
- preserved acquisition timestamp distinct from later recompute time;
- isolated PostgreSQL replay from migrations zero;
- exact first-pass, re-import and independent fresh-schema proof;
- deep alias/provenance semantic readback;
- no automatic Brand/Organization/BoatDesign invention;
- no SailboatData value contamination;
- retained Stage-2 exact-`G3_PASS` regression gate.

## SLICE-0016 acceptance closure

SLICE-0016 is explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `61b500c2de061abb09dd7ddc36a0bfaa724ceece`;
- GitHub Actions CI run #195 (`32478124648`): PASS on the exact accepted head;
- PostgreSQL **18.6** integration: PASS;
- persistence suite: **199 passed**;
- benchmark runner: PASS;
- benchmark result-schema validation: PASS;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- retained benchmark artifact ID: `9445058966`;
- artifact digest: `sha256:03a190278d9591879d3e3dfd8e7ec6b3c1d51b0c40bfaee843f3ce0eef7ebdc6`;
- retained Stage-2 benchmark remained 50/50 materialized, 50/50 first-pass imported, 50/50 exact re-import `ALREADY_IMPORTED`, 50/50 fresh-schema imported, 0 persistence conflicts/errors, 0 semantic mismatches and `G3_PASS`;
- implementation-agent final local report: **1354 passed, 201 skipped**;
- reported coverage: **94.31%**;
- repository validator / Ruff / strict mypy: PASS/CLEAN;
- independent review: initial three blockers corrected; final review found no remaining blocker;
- explicit project-owner acceptance on 2026-08-21;
- PR #33 merged on 2026-08-21;
- merge commit: `ae34363f5db8111a75d108b9b936084f76b56cef`.

Final closure record: `docs/slices/SLICE-0016-acceptance-closure.md`.

Accepted Stage-3 persistence semantics now include:

- canonical Brand/Organization/BoatModel/BoatDesign PostgreSQL persistence;
- stable caller-supplied opaque HullQ IDs;
- no persistence-layer name/QID/source-based identity minting;
- entity-scoped aliases;
- Brand↔BoatModel and Organization↔BoatDesign relationship separation;
- schema validation before mutation;
- fail-closed canonical reference/provenance linkage;
- order-independent BoatModel `boat_design_ids` consistency against the persisted design graph;
- atomic/idempotent/conflict-safe imports;
- PostgreSQL-native race safety;
- lossless semantic readback;
- preservation of accepted research persistence.

## SLICE-0015 acceptance closure

SLICE-0015 is explicitly accepted and `DONE`. Stage-2 Gate G3 is passed.

Acceptance evidence:

- final accepted implementation head: `022bec43318025bdeb92608bb2fb0445650f081d`;
- GitHub Actions CI run #189 (`32468991110`): PASS on the exact accepted head;
- PostgreSQL 18 integration: PASS;
- benchmark runner: PASS;
- benchmark result-schema validation: PASS;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- retained benchmark artifact ID: `9441784787`;
- artifact digest: `sha256:5f7048b86d2590509e764356283631c960c91988d2961d14e0d270e17b9ed588`;
- final measured result: 50/50 materialized, 50/50 first-pass imported, 50/50 exact re-import `ALREADY_IMPORTED`, 50/50 fresh-schema imported, 0 persistence errors/conflicts, 0 semantic mismatches/errors;
- technical recommendation: `G3_PASS`;
- fixed thresholds remained `>=65%` materialization, `<=10%` cannot-materialize-without-invention and `<=35%` review-required;
- implementation-agent final local report: **1277 passed, 164 skipped**;
- reported coverage: **93.66%**;
- repository validator / Ruff / strict touched-code mypy: PASS/CLEAN;
- independent review: no remaining blocker;
- explicit project-owner acceptance on 2026-08-21;
- PR #31 merged on 2026-08-21;
- merge commit: `d87490c6103676935768ba57ed41e665225731b8`.

Final closure record: `docs/slices/SLICE-0015-acceptance-closure.md`.

Accepted failure-class semantics:

- `CONTRACT_GAP` → `BLOCKED`;
- `VALIDATION_FAILURE` → `HARDEN_FIRST` regardless of percentage;
- `INSUFFICIENT_RETAINED_FACT` → rate-based and may remain G3-positive within the `<=10%` cannot-materialize threshold.

## SLICE-0014 acceptance closure

SLICE-0014 remains explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `98d2e38e42254bba17279945551d53c17b869f5e`;
- GitHub Actions CI run #178 (`32457026920`): PASS on the exact accepted head;
- PostgreSQL 18.6 integration: PASS;
- PostgreSQL persistence tests: **162 passed**;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- benchmark runner: PASS;
- benchmark result-schema validation: PASS;
- retained benchmark artifact ID: `9437591681`;
- artifact digest: `sha256:de4e6ec1e2b020b3758e5066441d3d068676bf298c0b1707c86b6b7098308f79`;
- final measured result: 50/50 materialized, 50/50 imported, 50/50 exact re-import `ALREADY_IMPORTED`, 50/50 fresh-schema imported, 0 persistence errors/conflicts, 0 semantic mismatches;
- implementation-agent local unit report: **987 passed**;
- reported overall coverage: **93.59%**;
- independent review: no remaining blocker;
- explicit project-owner acceptance on 2026-08-21;
- PR #29 merged on 2026-08-21;
- merge commit: `71100b50052ed7c2910b096e36b8a5402f757191`;
- benchmark recommendation: `G3_CANDIDATE`.

Final closure record: `docs/slices/SLICE-0014-acceptance-closure.md`.

## SLICE-0013 acceptance closure

SLICE-0013 remains explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `2da1ad19717707f3ec48c0ebfd6925d5e2fee043`;
- GitHub Actions CI run #166: PASS on the exact accepted head;
- PostgreSQL 18 integration: PASS;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- technical head `5cd9f9283dd927013925c0b2f66a756cfc27d52e`: 37/37 PostgreSQL 18.6 persistence integration tests PASS under CI #165;
- 949 local unit tests passed;
- overall coverage: 93.55%;
- persistence-module coverage: 95.73%;
- Ruff/format: clean;
- strict mypy: clean;
- repository validator: PASS;
- pip-audit: no known vulnerabilities;
- independent review: no remaining blocker;
- explicit project-owner acceptance on 2026-08-20;
- PR #27 merged on 2026-08-20;
- merge commit: `2b8417beeb848507ba0f97c49bbd0f37d647c438`.

Final closure record: `docs/slices/SLICE-0013-acceptance-closure.md`.

## SLICE-0012 acceptance closure

SLICE-0012 remains explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `d2344cd359d296e2483ab074a14b773ae5668952`;
- GitHub Actions CI run #157: PASS on the exact accepted head;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- 1084 local tests passed, 2 skipped;
- branch coverage: 93.33%;
- independent review: no remaining blocker;
- explicit project-owner acceptance on 2026-08-20;
- PR #24 merge commit: `db68e53ddc9cfe4aa53caa3ba900dc6a3daa7324`.

Final closure record: `docs/slices/SLICE-0012-acceptance-closure.md`.

## Evidence-first sequence

```text
reproducible toolchain                            DONE
        ↓
seed design-data source research                  DONE
        ↓
canonical contracts / measurements / identity     DONE
        ↓
provenance + source-rights + first adapter         DONE
        ↓
appendage/configuration + derived metrics          DONE
        ↓
controlled 50-design real-web benchmark           DONE — SLICE-0011
        ↓
pre-canonical observation + applicability/bundle  DONE — SLICE-0012
        ↓
research PostgreSQL persistence                   DONE — SLICE-0013
        ↓
run same benchmark through importer/DB            DONE — SLICE-0014 / G3_CANDIDATE
        ↓
harden negative paths + Stage-2 Gate G3           DONE — SLICE-0015 / G3 PASS
        ↓
canonical identity persistence/admission boundary DONE — SLICE-0016
        ↓
controlled Wikidata Tier-0 1,000 bootstrap        DONE — SLICE-0017
        ↓
baseline-preserving Wikidata <=2,500 expansion    DONE — SLICE-0018
        ↓
global manufacturer/yard universe + source yield  DONE — SLICE-0019
        ↓
archive source clearance + identity pilot         DONE — SLICE-0020
        ↓
next measured Stage-3 implementation decision      LATER / NOT AUTHORIZED
```

## SLICE-0018 accepted boundary

SLICE-0018 measured and accepted the current direct-instance Wikidata boundary rather than treating 2,500 as a quota that had to be filled.

The accepted result is:

- accepted SLICE-0017 retained manifest and 965 canonical BoatModels remain immutable baseline input;
- direct-instance discovery returned **1,829** current QIDs under the same rights-gated deterministic source path;
- all **1,000** accepted baseline QIDs remained present;
- only the **829** expansion-delta QIDs received SLICE-0018 decisions;
- **805** delta candidates were safely admitted as sparse Tier-0 BoatModels;
- **16** were review-bound and **8** were not admitted;
- the historical retained crosswalk contains **1,772** QID→HullQ-ID mappings;
- combined replay contains **1,770** canonical BoatModels;
- accepted baseline drift/deletion/demotion/remint count is zero;
- no Brand/Organization/BoatDesign rows were inferred;
- the source was not padded or silently changed when fewer than 2,500 direct instances were returned.

A later slice must use this measured result as evidence. It must not turn the 2,500 request into an invented 5,000 continuation without a new discovery/source rationale.

## SLICE-0019 boundary

`docs/slices/SLICE-0019-global-series-sailboat-manufacturer-universe-research.md` is the controlling contract. It is accepted and `DONE`; see `docs/slices/SLICE-0019-acceptance-closure.md` for the closure record.

The slice was deliberately limited to research/source mapping:

- build a broad global research registry of series-sailboat manufacturers/yards;
- include active and historical/defunct/acquired/renamed entities;
- preserve manufacturer/yard/brand/legal-organization/designer distinctions;
- retain source provenance and rights/access assessment;
- measure a 20-entity source-yield sample;
- estimate where additional model identities and Tier-1/Tier-2 facts can be obtained;
- compare to accepted HullQ state only where overlap is exact/unambiguous;
- recommend the next bounded slice without starting it.

It created and modified no canonical HullQ entities and did not authorize systematic ingestion from any newly researched source.

## Retained research rules

1. Research independently across the broad useful web only when an assigned research/acquisition slice explicitly authorizes it.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, source identity, retrieval context and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData remains post-hoc reference crosscheck only; no SailboatData field value becomes HullQ evidence, fallback data or canonical input.
6. Benchmark outputs are research evidence/stress fixtures, not automatically production canonical data.
7. Stage-2 G3 passage authorizes controlled Stage-3 work only through explicit bounded slice contracts; it is not a blanket ingestion authorization.
8. Accepted bootstrap artifacts are immutable baselines for later expansion unless a separate owner-accepted correction/migration slice explicitly changes that policy.

## Workflow note

`START_SLICE.bat` / `FINISH_SLICE.bat` govern Claude implementation/research worktrees.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

SLICE-0019 is closed and accepted `DONE` (see `docs/slices/SLICE-0019-acceptance-closure.md`). SLICE-0020 is closed and accepted `DONE` (see `docs/slices/SLICE-0020-acceptance-closure.md` and `research/manufacturers/archive_clearance/ARCHIVE_SOURCE_CLEARANCE_REPORT.md`). No slice beyond SLICE-0020 has been created or started, and no later slice is currently `READY`.
