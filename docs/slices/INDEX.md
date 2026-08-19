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
| SLICE-0007 | IMPLEMENTATION | DONE | ResearchJob runtime + deterministic source-rights/use gate + cumulative extraction telemetry so automated acquisition fails closed | SLICE-0006 / ADR-0005 |
| SLICE-0008 | IMPLEMENTATION | REVIEW | First rights-gated real external acquisition adapter against Wikidata CC0 with bounded discovery/entity acquisition and provenance-aware extraction | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | Appendage/configuration normalization refined from actual acquired data: keel, board, rudder, skeg, count/state and option relationships | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` after canonical/configuration inputs are hardened | SLICE-0009 |

## Current execution rule

`SLICE-0007` is `DONE`. It was implemented on `slice/0007-research-job-source-rights-gate`, independently reviewed through multiple fail-closed amendment rounds, explicitly accepted by the project owner on 2026-08-19 and merged through PR #17.

Acceptance evidence:

- accepted implementation head: `8bf3347c7751be1bbf9b364f3d1f44635dd98eef`;
- GitHub Actions run #96: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- final independent review: no remaining blockers;
- implementation merge commit: `ca5ac38d5d402aa9e1b5d366d30d2ce0b2cdee53`.

The accepted boundary provides ResearchJob runtime parity, deterministic use-specific rights decisions, overall-assessment fail-closed behavior, independent automated-access checks, permission-conflict checks, machine-visible obligations, source-bound cumulative extraction telemetry with projected-usage limits, effective bulk-clearance evaluation, job routing and provenance impact integration.

`SLICE-0008` is in `REVIEW`. The Wikidata CC0 rights-gated adapter is implemented, all required local quality gates pass (567 tests, 90.13% branch coverage, ruff clean, strict mypy clean on new files, pip-audit clean), and the branch `slice/0008-wikidata-rights-gated-adapter` has been pushed to GitHub. Independent review and project-owner acceptance are required before `DONE`.

No implementation agent may begin SLICE-0009 automatically.

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
ResearchJob + source-rights gate      DONE
        ↓
FIRST RIGHTS-GATED REAL DATA — Wikidata CC0   REVIEW
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

The rolling wave therefore establishes only the minimum prerequisites first: identity, provenance/raw observations, and source-rights/research-job controls. HullQ now acquires one controlled rights-cleared source and uses actual data quality to refine deeper normalization.

This does not authorize broad ingestion. The first adapter remains controlled and the 50–100 difficult-design corpus remains the benchmark before production-scale ingestion.

## Workflow note

The current `START_SLICE` workflow prepares/synchronizes Git state, creates or reuses the isolated worktree, and copies the Claude prompt. It deliberately does **not** open, close, reload or switch VS Code windows. The project owner explicitly opens the prepared worktree in the desired VS Code window.

## Rolling-wave note

Exactly one implementation slice is `READY`. SLICE-0009–0010 remain directional backlog and may be refined by implementation and real-data evidence.
