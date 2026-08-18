# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Research independent sailboat-design data sources and a 20–30-design seed evidence sample before domain pipeline code | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | DONE | Canonical JSON-Schema contract runtime and local `$id`/reference registry | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | DONE | Measurement observation + deterministic unit/basis normalization while preserving raw source semantics | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | READY | First-class Brand/Organization identity contracts, BoatModel/BoatDesign identity migration, entity-scoped aliases and deterministic search-label keys | SLICE-0004 / ADR-0011 |
| SLICE-0006 | IMPLEMENTATION | BACKLOG | Provenance/raw-observation boundary needed before real external values enter canonical identity/design records | SLICE-0005 |
| SLICE-0007 | IMPLEMENTATION | BACKLOG | ResearchJob state + source-clearance enforcement so automated acquisition fails closed by rights/use | SLICE-0006 |
| SLICE-0008 | IMPLEMENTATION | BACKLOG | First rights-gated real external acquisition adapter; preferred initial target Wikidata CC0 | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | Appendage/configuration normalization refined from actual acquired data: keel, board, rudder, skeg, count/state and option relationships | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` after canonical/configuration inputs are hardened | SLICE-0009 |

## Current execution rule

`SLICE-0004` is `DONE`: implementation was merged through PR #4 after green Ubuntu/Windows/dependency-audit CI, independent review, and explicit project-owner acceptance on 2026-08-18.

`SLICE-0005` is the **only READY slice**. It is fully defined in `docs/slices/SLICE-0005-identity-contracts-and-search-labels.md` and incorporates ADR-0011 Brand/Builder separation before any real external identity ingestion.

No implementation agent may begin SLICE-0006 or later work automatically after completing SLICE-0005.

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
Brand / Organization identity         READY (SLICE-0005)
        ↓
provenance/raw observation boundary
        ↓
ResearchJob + source-rights gate
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

The earlier directional queue placed appendage normalization and derived metrics before the first external adapter. SLICE-0002 already showed that appendage/configuration data is the hardest and most irregular part of the domain. Implementing its full normalization purely from imagined formats would create avoidable rework.

The revised rolling wave therefore establishes only the minimum prerequisites first: identity, provenance/raw observations, and source-rights/research-job controls. HullQ then ingests a controlled rights-cleared source and uses actual data quality to refine deeper normalization.

This does not authorize broad ingestion. The first adapter remains a controlled acquisition slice and the 50–100 difficult-design corpus remains the benchmark before production-scale ingestion.

## Rolling-wave note

Only SLICE-0005 is fully detailed and `READY`. SLICE-0006–0010 remain directional backlog and may be refined by implementation and real-data evidence. Do not create or start later slices automatically.
