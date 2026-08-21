# HullQ — Current Project State

**Updated:** 2026-08-21  
**Current stage:** Stage 3.0 — SLICE-0016 canonical identity persistence / bootstrap-admission boundary `READY`  
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

All slices 0001–0015 are `DONE` and owner-accepted.

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

SLICE-0013 established the first real physical persistence boundary:

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

Important Stage-3 boundary: the accepted SLICE-0013 schema is explicitly a **research/evidence persistence schema**. It does not provide canonical Brand / Organization / BoatModel / BoatDesign entity tables.

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

Exact-head CI #189 (`32468991110`) passed with:

- PostgreSQL 18 database integration PASS;
- benchmark runner PASS;
- benchmark result-schema validation PASS;
- benchmark artifact upload PASS;
- Ubuntu quality PASS;
- Windows quality PASS;
- dependency audit PASS.

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

Retained exact-head artifact:

- ID `9441784787`;
- digest `sha256:5f7048b86d2590509e764356283631c960c91988d2961d14e0d270e17b9ed588`.

Final closure record: `docs/slices/SLICE-0015-acceptance-closure.md`.

Stage 2 is now past G3. This authorizes controlled Stage-3 work through explicit slices; it is not blanket authorization for broad/unbounded ingestion.

## Why SLICE-0016 precedes the ~1,000-design canonical bootstrap

The next strategic milestone remains the controlled ~1,000-design identity bootstrap. Repository evidence shows one prerequisite is still missing:

- `src/hullq/domain/identity.py` explicitly contains pure identity value objects/search projections with **no persistence or network resolution**;
- the accepted PostgreSQL schema persists ResearchEvidenceBundle / ResearchObservation / FieldEvidence and explicitly does **not** require canonical entity tables.

Therefore inserting broad Wikidata/source candidates directly as canonical BoatModels/BoatDesigns would require the implementation agent to invent a canonical persistence/admission boundary during the bootstrap itself. HullQ's docs-to-code/single-authority rules forbid that silent decision.

SLICE-0016 closes only this prerequisite. It does not execute the broad bootstrap.

## Current operational position — SLICE-0016 READY

`docs/slices/SLICE-0016-canonical-identity-persistence-bootstrap-admission.md` is the only current READY slice.

Its purpose is to implement the first canonical Tier-0 identity persistence boundary on PostgreSQL for:

- Brand;
- Organization;
- BoatModel;
- BoatDesign;
- scoped aliases;
- Brand ↔ BoatModel relationships;
- Organization ↔ BoatDesign relationships;
- auditable supporting-observation/evidence links.

Binding constraints include:

- caller-supplied stable opaque HullQ IDs;
- no name/QID/source-based ID minting in the persistence layer;
- no fuzzy identity resolution or silent duplicate collapse;
- accepted schema validation before database mutation;
- atomic/idempotent/conflict-safe imports;
- PostgreSQL-native race safety;
- lossless semantic readback;
- existing research persistence preserved.

The actual controlled ~1,000-design bootstrap remains outside SLICE-0016.

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
SLICE-0016  canonical identity persistence/admission boundary  READY
      ↓
controlled ~1,000-design canonical bootstrap                   NOT AUTHORIZED YET
      ↓
progressive 2.5k / 5k design-universe enrichment               LATER
```

The benchmark corpus should not be expanded merely to increase its count. Additional stress cases are justified only if a materially new problem class is demonstrated.

## Continuous new-model intake — accepted future doctrine

Once broad design-universe ingestion is authorized, HullQ should treat historical/bootstrap coverage and ongoing new-model intake as separate tracks:

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

After the closure/readiness PR for SLICE-0015→0016 is merged, the project owner may start SLICE-0016 through the normal `START_SLICE.bat` workflow.

## Do not start yet

- the controlled ~1,000-design canonical bootstrap before SLICE-0016 acceptance;
- broad production ingestion;
- unbounded crawler work;
- automatic fuzzy/canonical identity resolution;
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