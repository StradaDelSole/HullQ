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
| SLICE-0015 | IMPLEMENTATION | READY | Harden benchmark failure paths and make the Stage-2 Gate G3 decision using the fixed pre-committed scorecard | SLICE-0014 accepted / DONE |

## Current execution rule

`SLICE-0015` is the **only READY slice**.

It may start only through the normal isolated `START_SLICE.bat` workflow after the closure/readiness PR containing its contract is merged to `main`.

No 1,000-design bootstrap, broad ingestion, query engine, API, frontend or marketplace work is authorized merely because SLICE-0015 is READY.

## SLICE-0014 acceptance closure

SLICE-0014 is explicitly accepted and `DONE`.

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

`G3_CANDIDATE` does not mean G3 has passed. Stage-2 G3 remains the bounded decision of SLICE-0015.

Review corrections incorporated before acceptance included:

1. field-/claim-level retained benchmark materialization instead of summary TEXT_FRAGMENT flattening;
2. true fresh-schema migration/import rerun;
3. real PostgreSQL-18 benchmark runner in CI with retained artifacts;
4. fail-closed ClaimSemantics and EvidenceType behavior;
5. derived materialization/review metrics;
6. one corpus-wide full semantic comparator for observations/findings/crosschecks;
7. lossless retained field identity;
8. prevention of generic evidence-type overclaiming;
9. schema-consistent failure/cost reporting;
10. explicit true BoatDesign-v0.4 `intended_field_pointer` allowlist with ambiguous fields left unset.

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
PostgreSQL persistence + deterministic importer   DONE — SLICE-0013
        ↓
run same benchmark through importer/DB            DONE — SLICE-0014 / G3_CANDIDATE
        ↓
harden negative paths + Stage-2 Gate G3           READY — SLICE-0015
        ↓
controlled 1,000-design identity bootstrap        NOT AUTHORIZED YET
```

## SLICE-0015 boundary

`docs/slices/SLICE-0015-benchmark-hardening-stage-2-g3.md` is the controlling READY contract.

It is deliberately limited to:

- the accepted SLICE-0014 benchmark path and exact 50-design corpus;
- the pre-committed, fixed G3 scorecard;
- deterministic failure classification;
- negative-path proof for review-required, insufficient-retained-fact, validation/materialization failure, true representational contract gap, semantic mismatch and idempotency/conflict behavior;
- correcting the latent rule that `CANNOT_MATERIALIZE` must not automatically imply architecture `BLOCKED`;
- re-running the exact 50-case benchmark through real PostgreSQL 18;
- an explicit `G3_PASS`, `HARDEN_FIRST` or `BLOCKED` recommendation;
- independent review and project-owner acceptance before DONE/G3 passage.

It explicitly excludes:

- the 1,000-design bootstrap;
- new broad web acquisition;
- crawlers/bulk ingestion;
- SailboatData extraction/value persistence;
- fuzzy/canonical identity resolution;
- automatic FieldResolution;
- query engine/API/frontend/auth;
- marketplace/listing ingestion;
- monitoring/price history;
- SEO/public pages;
- distributed infrastructure;
- HullQ Design Watch implementation.

## Retained research rules

1. Research independently across the broad useful web when a future research slice explicitly authorizes acquisition.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, source identity, retrieval context and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData remains post-hoc reference crosscheck only; no SailboatData field value becomes HullQ evidence, fallback data or canonical input.
6. Benchmark outputs are research evidence/stress fixtures, not automatically production canonical data.
7. SLICE-0015 is a hardening/gate slice; it must not reinterpret `50/50 materialized` as a production research-automation rate.

## Workflow note

`START_SLICE.bat` / `FINISH_SLICE.bat` govern Claude implementation/research worktrees.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned `slice/...` branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

The SLICE-0015 agent must return the slice in `REVIEW`, `BLOCKED` or `IN_PROGRESS` as appropriate and must not mark it `DONE`.
