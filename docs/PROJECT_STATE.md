# HullQ — Current Project State

**Updated:** 2026-08-23
**Current stage:** Stage 3.2–3.3 — SLICE-0019 manufacturer/yard universe research `DONE` (owner-accepted 2026-08-23). No slice is currently `READY`.
**Execution plan:** `docs/EXECUTION_PLAN.md`  
**Operational work queue:** `docs/slices/INDEX.md`

## Canonical project direction

HullQ is building an independent, provenance-aware sailboat design universe suitable for technical search/discovery, later market integration and reproducible derived metrics.

Accepted strategic principles remain:

- broad coverage with progressive verification depth;
- search architecture and SEO are product architecture, not later marketing;
- Search stays broadly available while persistence/monitoring are monetization candidates;
- source data, normalized candidates, canonical resolutions and HullQ-derived values remain distinct;
- unknown/conflict is preferable to fabricated completeness;
- one model string is not a reliable technical identity boundary;
- option/variant/state-sensitive values must not be flattened into one scalar baseline;
- source breadth is intentionally broad while canonical confidence remains strict;
- SailboatData is outcome-only post-hoc reference QA, never HullQ evidence/fallback data;
- GitHub `main` is canonical truth; bounded slice/PR review remains mandatory.

## Accepted application/deployment architecture

Target baseline remains:

```text
Cloudflare edge
      |
      v
Contabo Linux VPS
      |
      +-- Astro + TypeScript web
      |     \-- React islands only where state complexity justifies them
      +-- FastAPI / CPython 3.14
      +-- PostgreSQL
      +-- background/scheduled Python worker when needed
      \-- simple VPS deployment / Caddy baseline

Off-VPS backup/artifact direction: Cloudflare R2 when introduced
Later native mobile: Flutter Android/iOS via the same accepted API boundary
```

Auth remains deferred under OQ-014. OQ-006 controls alert cadence/freshness; OQ-015 controls the stable HTTP API/versioning boundary; OQ-018 controls the public SEO/search surface; OQ-009 must be resolved before technical query-engine semantics are frozen.

## Accepted foundation

| Slice | Result |
|---|---|
| SLICE-0001 | repository bootstrap, locked toolchain, Linux/Windows CI |
| SLICE-0002 | independent source research + seed evidence |
| SLICE-0003 | canonical JSON-Schema contract runtime |
| SLICE-0004 | measurement observation + exact normalization |
| SLICE-0005 | Brand/Organization + BoatModel/BoatDesign identity contracts |
| SLICE-0006 | FieldEvidence/FieldResolution provenance boundary |
| SLICE-0007 | ResearchJob + deterministic source-rights gate |
| SLICE-0008 | rights-gated Wikidata CC0 adapter |
| SLICE-0009 | appendage/configuration normalization |
| SLICE-0010 | `hullq-derived-1.0.0` derived metrics |
| SLICE-0011 | controlled 50-design real-web benchmark |
| SLICE-0012 | pre-canonical observations, claim/applicability semantics, research bundle + explicit promotion |
| SLICE-0013 | PostgreSQL 18 research persistence + deterministic transactional importer |
| SLICE-0014 | exact 50-design retained benchmark through PostgreSQL; full semantic roundtrip; G3_CANDIDATE |
| SLICE-0015 | negative-path hardening + fixed Stage-2 G3 scorecard; G3_PASS |
| SLICE-0016 | canonical Tier-0 identity PostgreSQL persistence/admission boundary |
| SLICE-0017 | controlled Wikidata Tier-0 1,000-candidate identity bootstrap; accepted broad Stage-3 baseline |
| SLICE-0018 | baseline-preserving Wikidata first-<=2,500 discovery expansion; measured direct-instance ceiling at 1,829 QIDs; accepted combined Tier-0 universe |

All slices 0001–0018 are `DONE` and owner-accepted.

## SLICE-0011 — benchmark result retained

The controlled benchmark covered 50 deliberately difficult designs across six waves.

Measured non-exclusive stress-corpus incidences:

- authoritative/original-document path found: **44/50 (88%)**;
- appendage/configuration complexity: **42/50 (84%)**;
- temporal/production applicability mattered: **32/50 (64%)**;
- identity/generation/lineage semantics mattered: **30/50 (60%)**;
- option/variant/operating-state semantics mattered: **30/50 (60%)**;
- secondary/community/broker evidence materially needed: **30/50 (60%)**;
- post-hoc reference anomaly/incompleteness/definition issue: **28/50 (56%)**;
- measurement/definition-basis semantics mattered: **22/50 (44%)**;
- material explicit conflict or unresolved question: **20/50 (40%)**.

These are stress-corpus incidences, not population prevalence estimates.

Research policy remains:

```text
broad independent web research
→ source-linked raw observation/context
→ corroboration/conflict detection
→ post-hoc reference comparison
→ benchmark classification/measurement
→ persistence requirements derived from evidence
```

SailboatData remains outcome-only post-hoc QA/reference comparison. No SailboatData field value becomes HullQ ResearchObservation, FieldEvidence, fallback value or canonical resolution input.

## SLICE-0012 — DONE / accepted

SLICE-0012 closed the benchmark-proven pre-persistence data gaps:

- `ResearchObservation` can exist before canonical identity resolution;
- source/document `EvidenceType` is distinct from claim semantics;
- applicability preserves year/hull/market/variant/option/state/individual-hull scope;
- FieldEvidence v0.3 adds claim/applicability without mutating v0.2;
- promotion requires an explicit caller-supplied stable `ProvenanceSubject`;
- ResearchEvidenceBundle supports partial/unresolved identity research;
- reference crosschecks remain structurally outside evidence/provenance.

Final closure record: `docs/slices/SLICE-0012-acceptance-closure.md`.

## SLICE-0013 — DONE / accepted

SLICE-0013 established the first real physical research-persistence boundary:

```text
validated ResearchEvidenceBundle
        ↓
deterministic semantic fingerprint
        ↓
transactional PostgreSQL 18 import
        ↓
immutable persisted research/evidence records
        ↓
round-trip/readback verification
```

Accepted persistence semantics include:

- reproducible PostgreSQL 18 schema creation from empty database;
- external environment-driven connection configuration;
- immutable `(bundle_id, bundle_version)` identity;
- globally stable immutable `ResearchObservation.observation_id`;
- globally stable immutable `FieldEvidence.evidence_id`;
- separate bundle membership for global observations/evidence;
- lossless raw/normalized/claim/applicability snapshots;
- crosschecks structurally outside evidence;
- deterministic order-insensitive bundle fingerprinting;
- atomic/idempotent/fail-closed imports;
- PostgreSQL-native race-safe concurrent imports;
- no fuzzy identity resolution, automatic canonical subject creation, automatic promotion or FieldResolution.

Final closure record: `docs/slices/SLICE-0013-acceptance-closure.md`.

## SLICE-0014 — DONE / accepted / G3_CANDIDATE

SLICE-0014 ran the exact retained 50-design stress corpus through the accepted ResearchEvidenceBundle/PostgreSQL boundary and hardened the benchmark until the result was semantically meaningful rather than merely green.

Accepted final head:

`98d2e38e42254bba17279945551d53c17b869f5e`

Implementation PR #29 merge commit:

`71100b50052ed7c2910b096e36b8a5402f757191`

Exact-head CI #178 (`32457026920`) passed with PostgreSQL 18.6, 162 persistence tests, Ubuntu/Windows quality, dependency audit, benchmark runner/schema validation and artifact upload all green.

Final measured benchmark outcome:

```text
50/50 materialized
50/50 first-pass imported
50/50 exact re-import ALREADY_IMPORTED
50/50 fresh-schema imported
0 persistence errors
0 conflicts
0 semantic readback mismatches
0 fresh-schema semantic mismatches
recommendation: G3_CANDIDATE
```

Retained artifact:

- ID `9437591681`;
- digest `sha256:de4e6ec1e2b020b3758e5066441d3d068676bf298c0b1707c86b6b7098308f79`.

Final closure record: `docs/slices/SLICE-0014-acceptance-closure.md`.

Important interpretation limit: `50/50 materialized` is not a production research automation-rate estimate because the benchmark begins with pre-curated retained HullQ evidence.

## SLICE-0015 — DONE / accepted / Stage-2 G3 PASS

SLICE-0015 hardened the benchmark's negative paths and applied the fixed pre-committed G3 scorecard without moving the thresholds after seeing the result.

Accepted final head:

`022bec43318025bdeb92608bb2fb0445650f081d`

Implementation PR #31 merge commit:

`d87490c6103676935768ba57ed41e665225731b8`

Exact-head CI #189 (`32468991110`) passed with PostgreSQL 18 integration, benchmark runner/schema validation, Ubuntu/Windows quality and dependency audit green.

Final measured benchmark outcome remained:

```text
50/50 materialized
50/50 first-pass imported
50/50 exact re-import ALREADY_IMPORTED
50/50 fresh-schema imported
0 persistence errors/conflicts
0 semantic readback mismatches
0 fresh-schema semantic mismatches/errors
recommendation: G3_PASS
```

Binding thresholds remain:

- mechanical materialization `>=65%`;
- cannot-materialize-without-invention `<=10%`;
- review-required `<=35%`.

Accepted failure-class semantics:

- `CONTRACT_GAP` → `BLOCKED`;
- `VALIDATION_FAILURE` → `HARDEN_FIRST` regardless of percentage;
- `INSUFFICIENT_RETAINED_FACT` → rate-based and may remain G3-positive within the `<=10%` threshold.

Final closure record: `docs/slices/SLICE-0015-acceptance-closure.md`.

Stage 2 is past G3. This authorizes controlled Stage-3 work through explicit slices; it is not blanket authorization for broad/unbounded ingestion.

## SLICE-0016 — DONE / accepted

SLICE-0016 closed the missing canonical Tier-0 identity persistence/admission prerequisite.

Accepted final head:

`61b500c2de061abb09dd7ddc36a0bfaa724ceece`

Implementation PR #33 merge commit:

`ae34363f5db8111a75d108b9b936084f76b56cef`

Exact-head CI #195 (`32478124648`) passed with:

- PostgreSQL **18.6** integration PASS;
- **199 persistence tests passed**;
- benchmark runner PASS;
- benchmark schema validation PASS;
- Ubuntu quality PASS;
- Windows quality PASS;
- dependency audit PASS.

The retained benchmark still returned `G3_PASS` with 50/50 materialization/import/reimport/fresh-schema behavior and zero semantic mismatches/conflicts/errors.

Accepted canonical persistence semantics now include:

- Brand / Organization / BoatModel / BoatDesign canonical tables;
- entity-scoped aliases;
- Brand↔BoatModel and Organization↔BoatDesign relationship separation;
- caller-supplied stable opaque HullQ IDs;
- accepted schema validation before mutation;
- auditable links to retained HullQ observations/evidence;
- fail-closed exact-kind target validation for provenance links;
- `BoatModel.boat_design_ids` consistency against the normalized BoatDesign graph;
- immutable semantic content fingerprints;
- atomic/idempotent/conflict-safe imports;
- PostgreSQL-native race-safe concurrency;
- lossless semantic readback;
- no fuzzy source-candidate resolution or persistence-layer ID minting.

Final closure record: `docs/slices/SLICE-0016-acceptance-closure.md`.

## SLICE-0017 — DONE / accepted

SLICE-0017 executed HullQ's first controlled broad Stage-3 identity bootstrap against the first 1,000 deterministic rights-cleared direct Wikidata sailboat-class candidates.

Accepted final head:

`34c2de8fc99ab6babad054a4186cee168cc3a2da`

Implementation PR #35 merge commit:

`e2001d3a926c08706558b6cb97962f235c843379`

Exact-head CI #200 (`32499124689`) passed with PostgreSQL 18.6, Ubuntu/Windows quality, dependency audit, retained Stage-2 exact `G3_PASS`, production bootstrap replay and every zero-tolerance assertion green.

Final retained live measurement:

```text
requested candidates                         1,000
unique candidates processed                  1,000
AUTO_ADMIT                                     965
REVIEW_REQUIRED                                 20
NOT_ADMITTED                                    15
collision clusters                              10
retained historical QID -> HullQ-ID mappings   967
ResearchEvidenceBundles on replay              985
canonical BoatModel admissions                 965
acquisition failures                             0
live retrievals                                 21
```

Final deterministic reason counts:

- `ok`: **965**;
- `name_collision`: **20**;
- `missing_label`: **15**.

Production PostgreSQL 18.6 replay proved:

```text
first isolated schema:
  985/985 bundles imported
  965/965 admissions imported
  0 conflicts/errors/unexpected statuses
  0 semantic readback mismatches
  exact canonical BoatModel ID set
  0 unexpected canonical rows for non-admitted candidates
  0 Brand / Organization / BoatDesign rows

exact re-import:
  1,950 ALREADY_IMPORTED
  0 conflicts
  0 errors

independent fresh schema:
  985 bundles imported
  965 admissions imported
  0 semantic mismatches
  exact canonical BoatModel ID set
  0 Brand / Organization / BoatDesign rows

all_zero_tolerance_conditions_clear = true
```

Accepted bootstrap semantics now include:

- accepted HullQ search-key semantics for collision detection;
- stable content-derived alias IDs;
- opaque once-minted HullQ IDs independent of QID/name;
- historical retained crosswalk structurally separate from the current candidate set;
- fail-closed crosswalk validation in both conflict directions before live network use;
- stable mappings across discovery-window omission/reappearance;
- original acquisition time preserved separately from later recompute time;
- current candidate rows describe only the current bounded acquisition;
- isolated PostgreSQL replay from migrations zero;
- exact first-pass/importer-status/readback/reimport/fresh-schema proof;
- no Brand/Organization/BoatDesign inference;
- normal CI remains fully offline with respect to Wikidata.

Final closure record: `docs/slices/SLICE-0017-acceptance-closure.md`.

## SLICE-0018 — DONE / accepted

SLICE-0018 extended the accepted Stage-3 Tier-0 identity universe without reinterpreting the accepted SLICE-0017 baseline.

Accepted final head:

`cbc93582c7ed93aa7a4253ac58868f7e79e266cc`

Implementation PR #37 merge commit:

`213ec3b13769708b1d996b3266a9e9c19fabbb45`

Exact-head CI #208 (`32540170666`) passed with PostgreSQL 18.6, Ubuntu/Windows quality, dependency audit, retained Stage-2 exact `G3_PASS`, accepted SLICE-0017 replay and the combined SLICE-0018 baseline-first/delta-second replay all green.

Final retained live measurement:

```text
requested discovery limit                    2,500
hard safety ceiling                          3,000
unique discovery QIDs returned               1,829
target reached                               false
accepted-baseline overlap                    1,000
accepted-baseline absent                         0
expansion delta                                829
AUTO_ADMIT                                     805
REVIEW_REQUIRED                                 16
NOT_ADMITTED                                     8
baseline collision records                       6
delta-delta collision clusters                   6
retained historical QID -> HullQ-ID mappings 1,772
combined canonical BoatModels                 1,770
acquisition failures                              0
```

Final deterministic delta reason counts:

- `ok`: **805**;
- `name_collision`: **16**;
- `missing_label`: **8**.

The direct-instance Wikidata query therefore established a measured current source ceiling of **1,829** under this discovery definition. The result was retained as fact; it was not padded from another source and was not converted into an artificial 2,500-candidate quota.

Accepted SLICE-0018 semantics include:

- exact raw-byte fingerprint protection for the accepted SLICE-0017 baseline before SLICE-0018 work;
- immutable accepted SLICE-0017 baseline decisions/IDs/payload semantics;
- separate current discovery window, expansion delta and historical retained crosswalk;
- stable historical mapping survival across omission/reappearance;
- fail-closed crosswalk conflict detection in both directions;
- exact fetched-entity completeness for every expected delta QID;
- exact manifest candidate-set equality to discovery-minus-baseline;
- slice-level <=2,500 network boundary enforced before adapter construction while shared safety ceiling remains 3,000;
- baseline-QID and duplicate-delta rejection before classification;
- accepted HullQ search-key collision semantics for delta↔baseline and delta↔delta review routing;
- baseline-first/delta-second PostgreSQL 18 replay from migrations zero;
- exact baseline verification before delta and zero drift after delta;
- exact first-pass/importer-status/readback/reimport/fresh-schema proof;
- no Brand/Organization/BoatDesign inference;
- no second live acquisition during the correction round;
- normal CI fully offline with respect to Wikidata.

Remote PostgreSQL 18.6 replay proved:

```text
baseline before delta:
  985 bundles
  965 admissions
  exact canonical ID set
  0 readback mismatches

combined first schema:
  1,806 bundles imported
  1,770 admissions imported
  0 conflicts/errors/unexpected statuses
  0 semantic readback mismatches
  0 post-delta baseline drift mismatches
  exact combined canonical ID set
  0 unexpected canonical rows for non-admitted candidates
  0 Brand / Organization / BoatDesign rows

exact re-import:
  3,576 ALREADY_IMPORTED
  0 conflicts
  0 errors

independent fresh schema:
  1,806 bundles imported
  1,770 admissions imported
  0 semantic mismatches
  0 post-delta baseline drift mismatches
  exact combined canonical ID set
  0 Brand / Organization / BoatDesign rows

all_zero_tolerance_conditions_clear = true
```

Final closure record: `docs/slices/SLICE-0018-acceptance-closure.md`.

## Current operational position — SLICE-0019 DONE

`docs/slices/SLICE-0019-global-series-sailboat-manufacturer-universe-research.md` is the controlling primary slice contract. It is **explicitly owner-accepted and closed `DONE`** on 2026-08-23; see `docs/slices/SLICE-0019-acceptance-closure.md` for the full closure record. **No later slice (including SLICE-0020) is made `READY` by this closure** — no slice is currently `READY`.

SLICE-0019 was a bounded DESIGN_RESEARCH step, not a production-ingestion step. Its purpose was to map the next breadth/enrichment source layer after the direct-instance Wikidata ceiling measured by SLICE-0018.

The bounded first wave targeted approximately **120–160 verified eligible series-sailboat manufacturer/yard research records** and landed at **121** verified eligible manufacturer/yard records, with active and historical entities, global geographic coverage (25 countries, 8 macro-regions), explicit source provenance and a completed **20-entity source-yield study**.

The research preserved manufacturer/yard/brand/legal-organization/designer distinctions and assessed later systematic-use rights/access separately from public readability.

It created no canonical HullQ entities and did not authorize a new production source. Its decision output was a ranked evidence-based recommendation for the next bounded Stage-3 slice, which remains not authorized/TBD pending a separate readiness decision.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis          DONE
      ↓
SLICE-0012  ResearchObservation + applicability/bundle         DONE
      ↓
SLICE-0013  research PostgreSQL persistence                    DONE
      ↓
SLICE-0014  same 50 cases through importer/database            DONE / G3_CANDIDATE
      ↓
SLICE-0015  harden negative paths + Stage-2 G3 decision        DONE / G3 PASS
      ↓
SLICE-0016  canonical identity persistence/admission boundary  DONE
      ↓
SLICE-0017  controlled Wikidata Tier-0 1,000 bootstrap         DONE
      ↓
SLICE-0018  baseline-preserving Wikidata <=2,500 expansion     DONE / source ceiling 1,829
      ↓
SLICE-0019  global manufacturer/yard universe source research  DONE / source-yield floor 121
      ↓
next bounded Stage-3 implementation decision                   NOT AUTHORIZED YET
```

The benchmark corpus should not be expanded merely to increase its count. Additional stress cases are justified only if a materially new problem class is demonstrated.

## Continuous new-model intake — accepted future doctrine

Once broad design-universe ingestion is accepted, HullQ should treat historical/bootstrap coverage and ongoing new-model intake as separate tracks:

```text
historical / bootstrap universe
        +
continuous new-model intake
```

The future continuous track should progressively handle discovery → identity triage → technical intake → validation/persistence → deep enrichment, with explicit maturity such as announced/preliminary/production-confirmed/verified rather than pretending announcement data is final production specification.

SLICE-0019 (now `DONE`) remains historical/bootstrap/source-strategy research and does not implement the continuous new-model track.

## AI repository workflow — ACTIVE

Implementation/research slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It refuses slices whose own primary slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

SLICE-0001 through SLICE-0019 are accepted / `DONE`. SLICE-0019's closure does not itself make SLICE-0020 (or any later slice) `READY`. SLICE-0020 has not been created or started; it requires its own bounded contract, explicit acceptance criteria and readiness decision before `START_SLICE.bat` may be used for it.

## Do not start yet

- 5,000 identity rerun merely by increasing the accepted SLICE-0018 limit;
- another production bootstrap source or different Wikidata production discovery strategy before a separate bounded source/discovery implementation slice is accepted and READY;
- resolution campaign for SLICE-0017/SLICE-0018 review candidates;
- broad Tier-1/Tier-2 technical enrichment;
- unbounded crawler work;
- automatic fuzzy/canonical identity resolution;
- destructive canonical correction/retraction framework;
- automatic Brand/Organization role inference from manufacturer labels;
- automatic BoatDesign generation invention from Wikidata QIDs;
- query-engine implementation;
- public FastAPI API;
- Astro frontend;
- account/auth;
- marketplace adapters;
- alerts/monitoring execution;
- multi-source listing deduplication;
- price-history pipeline;
- SEO/public-page implementation;
- HullQ Design Watch implementation;
- Powerboat expansion.
