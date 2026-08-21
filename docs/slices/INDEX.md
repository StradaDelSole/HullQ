# HullQ Slice Index

**Status:** ACTIVE execution board  
**Updated:** 2026-08-21

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
| SLICE-0017 | IMPLEMENTATION | REVIEW | Controlled Wikidata Tier-0 identity bootstrap across the first ~1,000 direct sailboat-class candidates | SLICE-0016 accepted / DONE |

## Current execution rule

`SLICE-0017` is the **only READY slice**.

It may start only through the normal isolated `START_SLICE.bat` workflow after this closure/readiness PR containing its contract is merged to `main`.

SLICE-0017 is the first controlled broad Stage-3 bootstrap. It may process up to the first 1,000 deterministic rights-cleared Wikidata direct-instance candidates and persist only safe Tier-0 canonical BoatModel identities through the accepted SLICE-0016 admission boundary.

No 2,500/5,000 expansion, broad technical enrichment, query engine, API, frontend, marketplace or monitoring work is authorized by this readiness transition.

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
controlled Wikidata Tier-0 ~1,000 bootstrap       READY — SLICE-0017
        ↓
measured next Stage-3 expansion/enrichment        LATER / NOT AUTHORIZED
```

## SLICE-0017 boundary

`docs/slices/SLICE-0017-controlled-wikidata-tier0-identity-bootstrap.md` is the controlling READY contract.

The slice is deliberately limited to the first controlled broad identity run:

- rights-gated direct Wikidata sailboat-class discovery;
- up to the first 1,000 candidates in deterministic bounded order;
- versioned replayable bootstrap manifest + review queue;
- stable opaque retained HullQ IDs for admitted BoatModels;
- source-backed ResearchObservation/provenance linkage;
- safe sparse Tier-0 BoatModel admission through SLICE-0016;
- real PostgreSQL 18 offline manifest replay, exact re-replay and fresh-schema equality;
- measured auto-admission/review/non-admission distribution.

It explicitly forbids treating a Wikidata QID as automatic proof of:

- Brand identity;
- Organization identity;
- Brand↔BoatModel relationship from manufacturer label alone;
- a distinct BoatDesign generation;
- a NamedVariant/DesignOption;
- technical-field completeness.

Ambiguity remains visible and review-bound. No post-hoc admission-rate threshold may be invented after seeing the run.

## Retained research rules

1. Research independently across the broad useful web only when an assigned research/acquisition slice explicitly authorizes it.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, source identity, retrieval context and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData remains post-hoc reference crosscheck only; no SailboatData field value becomes HullQ evidence, fallback data or canonical input.
6. Benchmark outputs are research evidence/stress fixtures, not automatically production canonical data.
7. Stage-2 G3 passage authorizes controlled Stage-3 work only through explicit bounded slice contracts; it is not a blanket ingestion authorization.

## Workflow note

`START_SLICE.bat` / `FINISH_SLICE.bat` govern Claude implementation/research worktrees.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

After this closure/readiness PR is merged, the project owner may run `START_SLICE.bat` for SLICE-0017. The script synchronizes `main`, creates the isolated worktree/branch, and copies Claude's assignment to the clipboard.

The SLICE-0017 agent must return the slice in `REVIEW`, `BLOCKED` or `IN_PROGRESS` as appropriate and must not mark it `DONE` or begin 2,500/5,000 expansion or technical enrichment automatically.