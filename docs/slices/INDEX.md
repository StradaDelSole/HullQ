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
| SLICE-0013 | IMPLEMENTATION | READY | PostgreSQL 18 migrations + lossless deterministic ResearchEvidenceBundle importer | SLICE-0012 accepted / DONE |

## Current execution rule

`SLICE-0013` is the **only READY implementation slice**.

It may start only through the normal isolated `START_SLICE.bat` workflow.

No later benchmark-execution slice, broad ingestion, query engine, API, frontend or marketplace work is authorized merely because SLICE-0013 is READY.

## SLICE-0012 acceptance closure

SLICE-0012 is explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `d2344cd359d296e2483ab074a14b773ae5668952`;
- GitHub Actions CI run #157: PASS on the exact accepted head;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- 1084 local tests passed, 2 skipped;
- branch coverage: 93.33%;
- Ruff/format: clean;
- strict mypy: clean;
- pip-audit: no known vulnerabilities;
- independent review: no remaining blocker;
- explicit project-owner acceptance on 2026-08-20;
- PR #24 merged on 2026-08-20;
- merge commit: `db68e53ddc9cfe4aa53caa3ba900dc6a3daa7324`.

The final closure record is `docs/slices/SLICE-0012-acceptance-closure.md`. The original SLICE-0012 implementation document retains its implementation-agent handoff history; the acceptance closure and this index are authoritative for final state.

Review corrections incorporated before acceptance included:

1. fail-closed applicability validation for every asserted string scope dimension;
2. removal of invented/incorrect benchmark fixture facts;
3. strict SailboatData outcome-only crosscheck handling;
4. synthetic fixture producer/source/job/observation metadata clearly separated from retained benchmark facts;
5. Catalina unresolved identity explicitly marked synthetic contract scaffolding.

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
PostgreSQL persistence + deterministic importer   READY — SLICE-0013
        ↓
run same benchmark through importer/DB            LATER / NOT READY
        ↓
measure automation/review/idempotency/cost        LATER
        ↓
1,000-design broad bootstrap                      NOT AUTHORIZED YET
```

## SLICE-0013 boundary

`docs/slices/SLICE-0013-postgresql-persistence-deterministic-importer.md` is the controlling READY contract.

It is deliberately limited to:

- PostgreSQL 18 migration baseline;
- persistence of accepted ResearchEvidenceBundle / ResearchObservation / applicability / unresolved findings / reference-crosscheck structures;
- optional already-promoted FieldEvidence v0.3 persistence;
- deterministic content fingerprinting;
- immutable/idempotent bundle and observation import semantics;
- transactional rollback/fail-closed collision behavior;
- minimal semantic round-trip/readback proof;
- real PostgreSQL 18 integration testing in CI.

It explicitly excludes:

- fuzzy/canonical identity resolution;
- automatic ResearchObservation → FieldEvidence promotion;
- automatic FieldResolution/canonical-value selection;
- broad BoatModel/BoatDesign persistence beyond what the accepted evidence snapshot requires;
- broad ingestion/crawling;
- the 50-design benchmark execution itself;
- query engine/API/frontend/auth;
- marketplace/listing ingestion;
- monitoring/price history;
- SailboatData field-value storage.

## Retained research rules

1. Research independently across the broad useful web.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, source identity, retrieval context and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData remains post-hoc reference crosscheck only; no SailboatData field value becomes HullQ evidence, fallback data or canonical input.
6. Benchmark outputs are research evidence/stress fixtures, not automatically production canonical data.

## Workflow note

`START_SLICE.bat` / `FINISH_SLICE.bat` govern Claude implementation worktrees.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned `slice/...` branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

The implementation agent must return SLICE-0013 in `REVIEW`, `BLOCKED` or `IN_PROGRESS` as appropriate and must not mark it `DONE`.
