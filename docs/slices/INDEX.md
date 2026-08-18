# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | IN_PROGRESS | Research actual independent sailboat-design data sources and a 20–30-design seed evidence sample before domain pipeline code | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | BACKLOG | Canonical contract runtime and schema-loading/validation layer, refined from SLICE-0002 evidence | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | BACKLOG | Deterministic unit-normalization primitives based on observed source inputs | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | BACKLOG | Text and identity-normalization primitives without fuzzy identity invention | SLICE-0004 |
| SLICE-0006 | IMPLEMENTATION | BACKLOG | Taxonomy normalization for hull/keel/rudder/skeg/rig concepts | SLICE-0005 |
| SLICE-0007 | IMPLEMENTATION | BACKLOG | Provenance runtime: FieldEvidence, FieldResolution and DerivationRecord behavior | SLICE-0006 |
| SLICE-0008 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | ResearchJob state machine, restartability and explicit review/error states | SLICE-0008 |

## Current execution rule

Only `SLICE-0002` is currently `IN_PROGRESS`. `SLICE-0001` is `DONE`.

No HullQ domain implementation should begin before:

1. `SLICE-0001` is `DONE`; and
2. `SLICE-0002` has researched real data sources and completed its seed evidence sample.

This deliberately uses evidence-first pipeline design:

```text
reproducible toolchain
        ↓
real design-data source research
        ↓
manual 20–30-design evidence sample
        ↓
actual observed extraction / normalization requirements
        ↓
bounded pipeline implementation
        ↓
50–100-design benchmark
        ↓
broad ingestion into thousands of designs
```

The purpose of SLICE-0002 is **not** to finish the product database manually. It is to prevent HullQ from building a research pipeline against imaginary source conditions.

The production persistence/search technology remains a later OQ-012 decision. A persistence-neutral logical-model review may be performed when implementation evidence makes it useful, but it is no longer a pre-code gate.

## Rolling-wave note

Slices 0003–0009 are directional backlog. Their exact boundaries MUST be refined from SLICE-0002 source evidence and later implementation findings. Do not detail future slices merely to create a long plan.
