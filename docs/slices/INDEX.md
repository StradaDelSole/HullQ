# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Research independent sailboat-design data sources and a 20–30-design seed evidence sample before domain pipeline code | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | DONE | Canonical JSON-Schema contract runtime and local `$id`/reference registry | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | DONE | Measurement observation + deterministic unit/basis normalization while preserving raw source semantics | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | DONE | First-class Brand/Organization identity contracts, BoatModel/BoatDesign identity migration, entity-scoped aliases and deterministic search-label keys | SLICE-0004 / ADR-0011 |
| SLICE-0006 | IMPLEMENTATION | DONE | Provenance/raw-observation runtime: successor FieldEvidence/FieldResolution contracts, stable provenance subjects, conflict/supersession/current-resolution validation and source-impact lookup | SLICE-0005 / ADR-0006 |
| SLICE-0007 | IMPLEMENTATION | READY | ResearchJob runtime + deterministic source-rights/use gate + cumulative extraction telemetry so automated acquisition fails closed | SLICE-0006 / ADR-0005 |
| SLICE-0008 | IMPLEMENTATION | BACKLOG | First rights-gated real external acquisition adapter; preferred initial target Wikidata CC0 | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | Appendage/configuration normalization refined from actual acquired data: keel, board, rudder, skeg, count/state and option relationships | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` after canonical/configuration inputs are hardened | SLICE-0009 |

## Current execution rule

`SLICE-0006` is `DONE`. It was implemented on `slice/0006-provenance-raw-observation-boundary`, independently reviewed through multiple amendment rounds, explicitly accepted by the project owner on 2026-08-19 and merged through PR #14.

Acceptance evidence:

- accepted implementation head: `c934dc615d306ef8d8ad11a5024925e650933c27`;
- GitHub Actions run #86: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- final independent review: no remaining blockers;
- implementation merge commit: `c0163795df3c4efb27102163770da0f7ff8cedbb`.

The accepted boundary provides shared provenance subjects, immutable raw-vs-normalized evidence snapshots, versioned field resolutions, strict RFC 6901 lookup, conflict/supersession/current-resolution validation, canonical consistency checking and Source → FieldEvidence → FieldResolution reverse-impact lookup.

`SLICE-0007` is now the only `READY` implementation slice. It is defined in `docs/slices/SLICE-0007-research-job-source-rights-gate.md` and must run only on its isolated `slice/0007-research-job-source-rights-gate` worktree/branch.

No implementation agent may begin SLICE-0008 or later work automatically after completing SLICE-0007.

## Evidence-first sequence

```text
reproducible toolchain
        ↓
real design-data source research
        ↓
canonical contract runtime            DONE
        ↓
measurement normalization             DONE
        ↓
Brand / Organization identity         DONE
        ↓
provenance/raw observation boundary   DONE
        ↓
ResearchJob + source-rights gate      READY
        ↓
FIRST RIGHTS-GATED REAL DATA — Wikidata CC0
        ↓
inspect actual data quality
        ↓
appendage/configuration hardening
        ↓
derived metrics
        ↓
controlled benchmark → broad ingestion
```

## Why real data moved earlier

SLICE-0002 showed that appendage/configuration data is the hardest and most irregular part of the domain. Implementing its full normalization purely from imagined formats would create avoidable rework.

The rolling wave therefore establishes only the minimum prerequisites first: identity, provenance/raw observations, and source-rights/research-job controls. HullQ then ingests one controlled rights-cleared source and uses actual data quality to refine deeper normalization.

This does not authorize broad ingestion. The first adapter remains controlled and the 50–100 difficult-design corpus remains the benchmark before production-scale ingestion.

## Workflow note

The current `START_SLICE` workflow prepares/synchronizes Git state, creates or reuses the isolated worktree, and copies the Claude prompt. It deliberately does **not** open, close, reload or switch VS Code windows. The project owner explicitly opens the prepared worktree in the desired VS Code window.

## Rolling-wave note

Exactly one implementation slice is `READY`. SLICE-0008–0010 remain directional backlog and may be refined by implementation and real-data evidence.
