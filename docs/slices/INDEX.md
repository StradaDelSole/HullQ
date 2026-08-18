# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Research independent sailboat-design data sources and a 20–30-design seed evidence sample before domain pipeline code | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | DONE | Canonical JSON-Schema contract runtime and local `$id`/reference registry | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | DONE | Measurement observation + deterministic unit/basis normalization while preserving raw source semantics | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | BACKLOG | Identity/model/generation text primitives without fuzzy resolution or silent generation inference | SLICE-0004 |
| SLICE-0006 | IMPLEMENTATION | BACKLOG | Appendage/configuration normalization: independent keel, board, rudder, skeg, count/state and option relationships | SLICE-0005 |
| SLICE-0007 | IMPLEMENTATION | BACKLOG | Provenance/conflict runtime: FieldEvidence, FieldResolution and DerivationRecord behavior | SLICE-0006 |
| SLICE-0008 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | BACKLOG | ResearchJob state machine, restartability and explicit review/error states | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | BACKLOG | Source-clearance guard plus first real external acquisition adapter, preferred initial target: Wikidata CC0 | SLICE-0009 |

## Current execution rule

`SLICE-0004` is `DONE`: implementation was merged through PR #4 after green Ubuntu/Windows/dependency-audit CI, independent review, and explicit project-owner acceptance on 2026-08-18.

No later implementation slice is `READY` yet. The next slice must be prepared from the accepted current identity model and the post-SLICE-0004 rolling-wave backlog before Claude starts new implementation work.

Evidence-first sequence:

```text
reproducible toolchain
        ↓
real design-data source research
        ↓
20-design core seed + targeted supplement
        ↓
canonical contract runtime            DONE
        ↓
measurement normalization             DONE
        ↓
identity / provenance / research-boundary implementation
        ↓
first rights-gated real source adapter
        ↓
controlled real-data pilot
        ↓
broad ingestion into thousands of designs
```

## Why SLICE-0004 was deliberately narrow

SLICE-0002 proved that measurement semantics are broader than unit conversion: source labels such as lightship, half-load, measurement trim and EEC-light must survive normalization. At the same time, arbitrary free-text interpretation would silently invent source semantics.

Therefore SLICE-0004 implements deterministic conversion only for **explicit numeric values + explicit units + explicit accepted basis values**. It preserves raw text/semantic labels but does not infer accepted basis values from manufacturer prose. Source-semantic classification remains a later evidence/review boundary.

The initial application/deployment/persistence target remains accepted under ADR-0010: Contabo VPS + Cloudflare edge, Astro/TypeScript with selective React islands, FastAPI/CPython 3.14 and PostgreSQL. That decision does not authorize application/frontend/persistence work before its future slices.

## Rolling-wave note

SLICE-0004 is closed. SLICE-0005 and later backlog remain directional until explicitly refined and moved to `READY`; no implementation agent may start them automatically.
