# HullQ — Current Project State

**Updated:** 2026-08-21  
**Current stage:** Stage 2.15 — SLICE-0015 benchmark hardening / Stage-2 G3 `READY`  
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
| SLICE-0014 | exact 50-design retained benchmark through PostgreSQL; full semantic roundtrip; G3_CANDIDATE |

All slices 0001–0014 are `DONE` and owner-accepted.

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

Final closure record: `docs/slices/SLICE-0013-acceptance-closure.md`.

## SLICE-0014 — DONE / accepted / G3_CANDIDATE

SLICE-0014 ran the exact retained 50-design stress corpus through the accepted ResearchEvidenceBundle/PostgreSQL boundary and hardened the benchmark until the result was semantically meaningful rather than merely green.

Accepted final head:

`98d2e38e42254bba17279945551d53c17b869f5e`

Implementation PR #29 merge commit:

`71100b50052ed7c2910b096e36b8a5402f757191`

Exact-head CI #178 (`32457026920`) passed with:

- PostgreSQL 18.6;
- 162 persistence tests PASS;
- Ubuntu quality PASS;
- Windows quality PASS;
- dependency audit PASS;
- benchmark runner PASS;
- benchmark schema validation PASS;
- benchmark artifact upload PASS.

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

The accepted path now preserves/compares complete persisted observation semantics plus unresolved findings and reference crosschecks, preserves retained field identity, fails closed on ambiguous claim/evidence semantics, and only emits canonical field pointers through an explicit BoatDesign-v0.4 one-to-one allowlist.

Retained artifact:

- ID `9437591681`;
- digest `sha256:de4e6ec1e2b020b3758e5066441d3d068676bf298c0b1707c86b6b7098308f79`.

Final closure record: `docs/slices/SLICE-0014-acceptance-closure.md`.

Important interpretation limit:

`50/50 materialized` is **not** a production research automation-rate estimate. The benchmark starts from pre-curated retained HullQ evidence. It proves the research-contract/materialization/persistence boundary for that corpus, not unknown-design source discovery and acquisition economics.

## Current operational position — SLICE-0015 READY

`docs/slices/SLICE-0015-benchmark-hardening-stage-2-g3.md` is the only current READY slice.

Its purpose is to harden the remaining failure paths and make the Stage-2 Gate G3 decision using the fixed scorecard agreed **before** the final benchmark result.

Binding correctness gates remain zero-tolerance:

```text
readback mismatches                  0
nondeterministic semantic output     0
unexpected persistence errors        0
duplicate/membership anomalies       0
exact re-import idempotency           100%
fresh-DB semantic equality            100%
invented / force-resolved values      0
SailboatData value contamination      0
```

Binding scale/review interpretation:

- mechanically materializable >=65% required for G3-positive outcome;
- cannot-materialize-without-invention <=10%;
- review-required cases <=35%;
- reviewer timing only where genuinely measurable;
- no arbitrary PostgreSQL throughput threshold.

The main known hardening item carried from SLICE-0014 is narrow:

`CANNOT_MATERIALIZE` must be classified before recommendation. An ordinary validation/materialization exception must not automatically become architecture `BLOCKED`; `BLOCKED` is reserved for a true recurring representational/contract insufficiency.

SLICE-0015 also requires explicit negative-path proof so the benchmark is proven to fail honestly when semantics, validation, idempotency or representability fail.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis          DONE
      ↓
SLICE-0012  ResearchObservation + applicability/bundle         DONE
      ↓
SLICE-0013  PostgreSQL persistence + deterministic importer    DONE
      ↓
SLICE-0014  same 50 cases through importer/database            DONE / G3_CANDIDATE
      ↓
SLICE-0015  harden negative paths + Stage-2 G3 decision        READY
      ↓
controlled ~1,000-design identity bootstrap                    NOT AUTHORIZED YET
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

This is a future ingestion/maintenance concern and is not implementation scope for SLICE-0015.

## AI repository workflow — ACTIVE

Implementation/research slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It must refuse slices whose own primary slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

## Do not start yet

- the 1,000-design bootstrap before SLICE-0015 acceptance / Stage-2 G3 decision;
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
- SEO/public-page implementation;
- HullQ Design Watch implementation;
- Powerboat expansion.
