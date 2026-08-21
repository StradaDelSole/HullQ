# HullQ — Current Project State

**Updated:** 2026-08-21  
**Current stage:** Stage 3.1–3.2 — SLICE-0017 controlled Wikidata Tier-0 identity bootstrap `READY`  
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

All slices 0001–0016 are `DONE` and owner-accepted.

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

## Current operational position — SLICE-0017 READY

`docs/slices/SLICE-0017-controlled-wikidata-tier0-identity-bootstrap.md` is the only current READY slice.

Its purpose is to execute the first controlled broad Stage-3 identity run:

```text
rights-cleared Wikidata direct sailboat-class candidates
        ↓
first <=1,000 in deterministic bounded order
        ↓
source-backed Tier-0 identity observations
        ↓
safe BoatModel admission OR explicit review/non-admission
        ↓
versioned bootstrap manifest/review queue
        ↓
SLICE-0013 research persistence + SLICE-0016 canonical admission
        ↓
PostgreSQL 18 replay/idempotency/fresh-schema proof
```

Key binding constraints:

- process up to the first 1,000 direct-instance candidates, all if fewer are returned;
- retain a replayable CC0-safe bootstrap manifest;
- mint stable opaque HullQ IDs once and retain the QID→HullQ-ID crosswalk; IDs must not encode/derive from QID or display name;
- a direct Wikidata class item may safely seed a sparse BoatModel when the source-backed identity claim is unambiguous;
- manufacturer `P176` does not automatically prove Brand vs Organization;
- QID existence alone does not prove a distinct BoatDesign generation;
- same-name/search-projection ambiguity routes to review rather than forced merge/split;
- every admitted BoatModel has auditable supporting HullQ observation/evidence linkage;
- normal CI remains offline and replays the retained manifest against PostgreSQL 18;
- no post-hoc admission-rate threshold is invented after the run.

The measured result of SLICE-0017 will determine the next Stage-3 expansion/hardening/enrichment slice. No later slice is pre-authorized.

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
SLICE-0017  controlled Wikidata Tier-0 ~1,000 bootstrap        READY
      ↓
measured next Stage-3 expansion/enrichment                     NOT AUTHORIZED YET
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

## AI repository workflow — ACTIVE

Implementation/research slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It refuses slices whose own primary slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

After the closure/readiness PR for SLICE-0016→0017 is merged, the project owner may start SLICE-0017 through the normal `START_SLICE.bat` workflow.

## Do not start yet

- 2,500 / 5,000 identity expansion before SLICE-0017 acceptance and measurement;
- broad Tier-1/Tier-2 technical enrichment before the bootstrap result is reviewed;
- unbounded crawler work;
- automatic fuzzy/canonical identity resolution;
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