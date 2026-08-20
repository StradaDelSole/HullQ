# HullQ — Current Project State

**Updated:** 2026-08-20  
**Current stage:** Stage 2.14 — SLICE-0014 controlled benchmark-through-PostgreSQL `READY`  
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
| SLICE-0013 | PostgreSQL 18 persistence + deterministic transactional importer |

All slices 0001–0013 are `DONE` and owner-accepted.

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

Final acceptance evidence:

- accepted PR head: `2da1ad19717707f3ec48c0ebfd6925d5e2fee043`;
- PR #27 merge commit: `2b8417beeb848507ba0f97c49bbd0f37d647c438`;
- GitHub Actions CI #166: PASS on exact accepted head;
- PostgreSQL 18 integration: PASS;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- technical head `5cd9f9283dd927013925c0b2f66a756cfc27d52e`: 37/37 PostgreSQL 18.6 persistence integration tests PASS under CI #165;
- 949 local unit tests passed;
- 93.55% overall coverage;
- 95.73% persistence-module coverage;
- Ruff/format, strict mypy, repository validator and pip-audit clean;
- independent review: no remaining blocker;
- explicit project-owner acceptance: 2026-08-20.

Final closure record: `docs/slices/SLICE-0013-acceptance-closure.md`.

The review process specifically hardened global evidence identity, concurrency behavior, bundle fingerprint semantics and the unreleased migration baseline before acceptance.

## Current operational position — SLICE-0014 READY

`docs/slices/SLICE-0014-controlled-benchmark-through-postgresql.md` is the only current READY slice.

Its purpose is to run the **same accepted 50-design stress corpus** through the real ResearchEvidenceBundle/PostgreSQL path and measure actual behavior before any broad design-universe ingestion is considered.

Target flow:

```text
retained SLICE-0011 benchmark evidence
        ↓
mechanical benchmark-only bundle materialization
        ↓
accepted SLICE-0012 validation semantics
        ↓
accepted SLICE-0013 PostgreSQL importer
        ↓
readback + exact re-import + fresh-DB rerun
        ↓
measured automation/review/idempotency/throughput evidence
```

In scope:

- exact 50 retained benchmark cases, unchanged;
- deterministic benchmark manifest;
- mechanical materialization from already retained HullQ research artifacts only;
- honest review-required/insufficient-retained-fact classification instead of invention;
- real PostgreSQL 18 execution;
- exact re-import idempotency measurement;
- fresh-database reproducibility measurement;
- readback fidelity checks on hard cases;
- measurement of materialization/review burden and execution throughput;
- observable cost only; unavailable cost must be `NOT_MEASURED`;
- evidence-based recommendation: HARDEN FIRST / G3 CANDIDATE / BLOCKED.

Explicitly not in SLICE-0014:

- new broad web research or source acquisition;
- SailboatData field-value use;
- fuzzy/canonical BoatDesign resolver;
- automatic promotion or FieldResolution;
- broad production ingestion;
- the 1,000-design bootstrap;
- query engine/API/frontend/auth;
- marketplace/listings;
- monitoring/price history;
- SEO/public pages;
- distributed infrastructure.

SLICE-0014 does not authorize Stage-2 Gate G3 by itself. The agent may recommend a G3 candidate state, but owner acceptance and a later bounded hardening/gate decision remain required.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis          DONE
      ↓
SLICE-0012  ResearchObservation + applicability/bundle         DONE
      ↓
SLICE-0013  PostgreSQL persistence + deterministic importer    DONE
      ↓
SLICE-0014  same 50 cases through importer/database            READY
      ↓
SLICE-0015  harden benchmark / Stage-2 G3 decision             LATER / NOT READY
      ↓
first 1,000-design broad bootstrap                             NOT AUTHORIZED YET
```

The benchmark corpus should not be expanded merely to increase its count. Additional stress designs are justified only if importer/database execution exposes a materially missing problem class.

## AI repository workflow — ACTIVE

Implementation/research slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It must refuse slices whose own primary slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

## Do not start yet

- SLICE-0015 before SLICE-0014 acceptance;
- broad production ingestion;
- 1,000-design bootstrap;
- unbounded crawler work;
- query-engine implementation;
- public FastAPI API;
- Astro frontend;
- account/auth;
- marketplace adapters;
- alerts/monitoring execution;
- multi-source listing deduplication;
- price-history pipeline;
- Powerboat expansion.
