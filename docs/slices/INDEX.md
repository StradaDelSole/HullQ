# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | READY | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | BACKLOG | Resolve OQ-019: canonical persistence-neutral logical data model and data-access requirements before domain implementation | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | BACKLOG | Canonical contract runtime and schema-loading/validation layer | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | BACKLOG | Deterministic unit-normalization primitives | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | BACKLOG | Text and identity-normalization primitives without fuzzy identity invention | SLICE-0004 |
| SLICE-0006 | IMPLEMENTATION | BACKLOG | Taxonomy normalization for hull/keel/rudder/skeg/rig concepts | SLICE-0005 |
| SLICE-0007 | IMPLEMENTATION | BACKLOG | Provenance runtime: FieldEvidence, FieldResolution and DerivationRecord behavior | SLICE-0006 |
| SLICE-0008 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | ResearchJob state machine, restartability and explicit review/error states | SLICE-0008 |

## Current execution rule

Only `SLICE-0001` is currently `READY`.

No HullQ domain implementation may begin before:

1. `SLICE-0001` is `DONE`; and
2. `SLICE-0002` has resolved OQ-019 and is `DONE`.

This deliberately separates:

```text
logical data model now
        ↓
research/contract implementation
        ↓
benchmark evidence
        ↓
physical production database/search technology later under OQ-012
```

Do not select PostgreSQL, Elasticsearch/OpenSearch, a document database, ORM strategy, or production indexing topology merely to complete SLICE-0002.

## Rolling-wave note

Slices 0003–0009 are directional backlog. Their exact boundaries MAY be refined after SLICE-0002 or earlier implementation evidence, provided scope changes are recorded here and do not silently alter accepted requirements/specs.
