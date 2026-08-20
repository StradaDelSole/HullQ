# HullQ Slice Index

**Status:** ACTIVE execution board  
**Updated:** 2026-08-20

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
| SLICE-0014 | DESIGN_RESEARCH | READY | Run the accepted 50-design benchmark through the real PostgreSQL persistence path and measure determinism/review/throughput | SLICE-0013 accepted / DONE |

## Current execution rule

`SLICE-0014` is the **only READY slice**.

It may start only through the normal isolated `START_SLICE.bat` workflow after the closure/readiness PR containing its contract is merged to `main`.

No later hardening/G3 slice, broad ingestion, query engine, API, frontend or marketplace work is authorized merely because SLICE-0014 is READY.

## SLICE-0013 acceptance closure

SLICE-0013 is explicitly accepted and `DONE`.

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

The final closure record is `docs/slices/SLICE-0013-acceptance-closure.md`. The original SLICE-0013 implementation document retains its implementation-agent handoff history; the acceptance closure and this index are authoritative for final state.

Review corrections incorporated before acceptance included:

1. globally stable immutable `FieldEvidence.evidence_id` with separate bundle membership;
2. PostgreSQL-native race-safe import semantics with fail-closed hash verification;
3. order-insensitive bundle semantic fingerprinting;
4. final migration baseline folded into a single unreleased `001_initial_schema.sql`;
5. real two-connection concurrency tests for identical imports, shared observation/evidence identities and conflicting immutable content.

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
run same benchmark through importer/DB            READY — SLICE-0014
        ↓
measure + harden toward Stage-2 Gate G3           LATER / NOT READY
        ↓
1,000-design broad bootstrap                      NOT AUTHORIZED YET
```

## SLICE-0014 boundary

`docs/slices/SLICE-0014-controlled-benchmark-through-postgresql.md` is the controlling READY contract.

It is deliberately limited to:

- the exact accepted 50-design benchmark population;
- mechanical materialization from already retained HullQ benchmark artifacts;
- accepted `ResearchEvidenceBundle` validation;
- execution through the accepted PostgreSQL 18 migration/import/readback path;
- deterministic exact re-import and fresh-database rerun;
- measurement of materialization/review burden, import outcomes, readback fidelity and throughput;
- honest `NOT_MEASURED` handling where timing/cost cannot be observed reliably;
- an evidence-based recommendation for hardening/G3, without declaring G3 passed.

It explicitly excludes:

- new broad web research/acquisition;
- SailboatData extraction or field-value persistence;
- fuzzy/canonical identity resolution;
- automatic promotion/FieldResolution;
- broad production ingestion;
- the 1,000-design bootstrap;
- query engine/API/frontend/auth;
- marketplace/listing ingestion;
- monitoring/price history;
- SEO/public pages;
- distributed infrastructure.

## Retained research rules

1. Research independently across the broad useful web when a future research slice explicitly authorizes acquisition.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, source identity, retrieval context and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData remains post-hoc reference crosscheck only; no SailboatData field value becomes HullQ evidence, fallback data or canonical input.
6. Benchmark outputs are research evidence/stress fixtures, not automatically production canonical data.
7. SLICE-0014 may only reuse retained benchmark evidence; inability to materialize a case without invention is itself a measured result.

## Workflow note

`START_SLICE.bat` / `FINISH_SLICE.bat` govern Claude implementation/research worktrees.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned `slice/...` branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

The SLICE-0014 agent must return the slice in `REVIEW`, `BLOCKED` or `IN_PROGRESS` as appropriate and must not mark it `DONE`.
