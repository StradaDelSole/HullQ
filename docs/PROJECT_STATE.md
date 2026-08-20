# HullQ — Current Project State

**Updated:** 2026-08-20  
**Current stage:** Stage 2.13 — SLICE-0013 PostgreSQL persistence + deterministic importer `READY`  
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

All slices 0001–0012 are `DONE` and owner-accepted.

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

Final acceptance evidence:

- accepted PR head: `d2344cd359d296e2483ab074a14b773ae5668952`;
- GitHub Actions CI run #157: PASS on exact head;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- 1084 local tests passed, 2 skipped;
- branch coverage: 93.33%;
- Ruff/format, strict mypy and pip-audit clean;
- independent review: no remaining blocker;
- explicit project-owner acceptance: 2026-08-20;
- PR #24 merge commit: `db68e53ddc9cfe4aa53caa3ba900dc6a3daa7324`.

Final closure record: `docs/slices/SLICE-0012-acceptance-closure.md`.

The review process additionally established a strict fixture-integrity rule: retained benchmark facts and synthetic contract scaffolding must be explicitly distinguishable; fixture metadata must not fabricate historical producer/source/retrieval provenance.

## Current operational position — SLICE-0013 READY

`docs/slices/SLICE-0013-postgresql-persistence-deterministic-importer.md` is the only current READY implementation slice.

Its objective is the first real persistence boundary:

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

In scope:

- PostgreSQL 18 migration baseline;
- environment-driven connection configuration with no committed secrets;
- persistence of versioned ResearchEvidenceBundle snapshots;
- stable ResearchObservation persistence;
- structured applicability persistence;
- unresolved finding persistence;
- separate reference-crosscheck persistence;
- optional already-promoted FieldEvidence v0.3 persistence;
- deterministic immutable identity/content fingerprints;
- atomic/idempotent importer;
- explicit conflict/fail-closed behavior;
- minimal semantic round-trip readback;
- a real PostgreSQL 18 integration job in CI.

Explicitly not in SLICE-0013:

- fuzzy/canonical BoatModel/BoatDesign identity resolution;
- automatic ResearchObservation → FieldEvidence promotion;
- automatic FieldResolution/canonical-value selection;
- broad ingestion/crawling;
- running/importing the full 50-design benchmark as the next measurement exercise;
- query engine/API/frontend/auth;
- marketplace/listings;
- monitoring/price history;
- SEO/public pages;
- SailboatData value storage.

The project owner's local PostgreSQL baseline is PostgreSQL 18.6 on Windows. Repository code must not depend on local passwords/database names; local/CI connection settings remain external configuration.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis          DONE
      ↓
SLICE-0012  ResearchObservation + applicability/bundle         DONE
      ↓
SLICE-0013  PostgreSQL persistence + deterministic importer    READY
      ↓
next slice   same benchmark through importer/database          LATER / NOT READY
      ↓
measure      automation/review/idempotency/throughput/cost     LATER
      ↓
1,000-design broad bootstrap                                   NOT AUTHORIZED YET
```

The benchmark corpus should not be expanded merely to increase its count. Additional stress designs are justified only if importer/database execution exposes a materially missing problem class.

## AI repository workflow — ACTIVE

Implementation slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It must refuse slices whose own slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned implementation branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

## Do not start yet

- any post-0013 benchmark execution until SLICE-0013 is accepted;
- broad production ingestion;
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
