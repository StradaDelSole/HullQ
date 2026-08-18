# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Research independent sailboat-design data sources and a 20–30-design seed evidence sample before domain pipeline code | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | READY | Canonical JSON-Schema contract runtime and local `$id`/reference registry; no acquisition/network semantics | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | BACKLOG | Measurement observation + deterministic unit/basis normalization while preserving raw source semantics | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | BACKLOG | Identity/model/generation text primitives without fuzzy resolution or silent generation inference | SLICE-0004 |
| SLICE-0006 | IMPLEMENTATION | BACKLOG | Appendage/configuration normalization: independent keel, board, rudder, skeg, count/state and option relationships | SLICE-0005 |
| SLICE-0007 | IMPLEMENTATION | BACKLOG | Provenance/conflict runtime: FieldEvidence, FieldResolution and DerivationRecord behavior | SLICE-0006 |
| SLICE-0008 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | ResearchJob state machine, restartability and explicit review/error states | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | BACKLOG | Source-clearance guard plus first real external acquisition adapter, preferred initial target: Wikidata CC0 | SLICE-0009 |

## Current execution rule

`SLICE-0002` has completed independent review and was explicitly accepted by the project owner on 2026-08-18. `SLICE-0003` is the only implementation slice currently `READY`.

No implementation agent may begin SLICE-0004 or later work automatically after completing SLICE-0003.

Evidence-first sequence:

```text
reproducible toolchain
        ↓
real design-data source research
        ↓
20-design core seed + targeted supplement
        ↓
observed extraction / measurement / appendage / conflict requirements
        ↓
canonical contract runtime            ← current
        ↓
bounded measurement / identity / appendage / provenance implementation
        ↓
first rights-gated real source adapter
        ↓
50–100-design benchmark
        ↓
broad ingestion into thousands of designs
```

## Why the implementation backlog changed after SLICE-0002

The source sample proved several concerns deserve separate boundaries:

- **measurement semantics** are broader than unit conversion: raw labels such as lightship, half-load, measurement trim and EEC-light must survive normalization;
- **appendage/configuration normalization** needs its own slice because keel, board, rudder, skeg, rudder count and protection/support relationships vary independently in real boats;
- **source acquisition** should come only after the pure contracts/normalization/provenance/job-state foundations exist, and the first adapter must enforce source clearance before network use;
- one generic `taxonomy normalization` slice would hide too much domain complexity and encourage accidental source-string mapping.

The production persistence/search technology remains a later OQ-012 decision.

## Rolling-wave note

SLICE-0003 is fully detailed in `docs/slices/SLICE-0003-canonical-contract-runtime.md`. SLICE-0004–0010 remain directional backlog and may be refined by implementation evidence. Do not create a long speculative plan merely to fill the queue.
