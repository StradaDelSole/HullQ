# HullQ — Current Project State

**Updated:** 2026-08-21  
**Current stage:** Stage 3.2 — SLICE-0018 controlled Wikidata Tier-0 <=2,500-window expansion `READY`  
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

All slices 0001–0017 are `DONE` and owner-accepted.

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

## Current operational position — SLICE-0018 READY

`docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md` is the only READY primary slice contract.

SLICE-0018 is intentionally a baseline-preserving **expansion delta**, not a disposable rerun of 0017.

The binding state model is:

```text
A. accepted SLICE-0017 baseline
B. historical retained crosswalk
C. current SLICE-0018 first-<=2,500 discovery window
D. SLICE-0018 expansion delta = C minus all 1,000 baseline candidate QIDs
```

Only D receives new SLICE-0018 admission/review/non-admission decisions.

The accepted 965 baseline BoatModels must not be reclassified, demoted, deleted, renamed, re-aliased or reminted merely because a larger live discovery window exposes additional collisions or source churn.

A new delta candidate that collides with baseline search space is review-bound; the accepted baseline entity remains unchanged.

The one authorized live Wikidata acquisition for SLICE-0018 is bounded by:

- same accepted rights-gated direct-instance source;
- direct instances of `Q106179098` only;
- deterministic stable ordering;
- requested limit: **2,500**;
- hard safety ceiling: **3,000**;
- no recursive subclass expansion;
- no source switch;
- no padding from another source if fewer than 2,500 are returned.

If the direct-instance source returns fewer than 2,500 candidates, that observed source ceiling is a measured Stage-3 result rather than a reason to bypass the source boundary.

SLICE-0018 must retain a separate artifact from the accepted `research/bootstrap/wikidata/manifest.json` baseline and must prove the combined baseline-first/delta-second graph against isolated PostgreSQL 18 schemas with exact re-import and independent fresh-schema equality.

No later slice is pre-authorized by this readiness state.

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
SLICE-0018  baseline-preserving Wikidata <=2,500 expansion     READY
      ↓
measured 5,000/source/enrichment decision                      NOT AUTHORIZED YET
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

SLICE-0018 remains historical/bootstrap-universe work and does not implement the continuous new-model track.

## AI repository workflow — ACTIVE

Implementation/research slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It refuses slices whose own primary slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

After the SLICE-0017 closure / SLICE-0018 readiness PR is merged, the project owner may run `FINISH_SLICE.bat` for SLICE-0017 and then, when ready, `START_SLICE.bat` for SLICE-0018.

## Do not start yet

- 5,000 identity expansion before SLICE-0018 acceptance and measurement;
- another bootstrap source before SLICE-0018 measures whether Wikidata reaches the 2,500 window, unless SLICE-0018 is explicitly `BLOCKED` by the accepted source boundary;
- resolution campaign for SLICE-0017 review candidates;
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
