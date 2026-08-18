# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 0.3 / Stage 1.6 boundary — bootstrap closure, then canonical logical data-model gate  
**Execution plan:** `docs/EXECUTION_PLAN.md`  
**Operational work queue:** `docs/slices/INDEX.md`

## Completed foundation

- canonical project context established;
- broad-coverage / progressive-depth data strategy accepted;
- 50–100 design corpus defined as research benchmark only;
- single-repository rule accepted (ADR-0001);
- docs-to-code method accepted (ADR-0002);
- broad-coverage strategy captured as ADR-0003;
- model/design-generation/option identity accepted (OQ-003 / ADR-0004 / `IDENTITY_MODEL.v0.1.md`);
- identity contract fixtures created;
- requirements baseline and test strategy created;
- open-question/decision process established;
- engineering quality gates established;
- implementation-slice workflow established under `docs/slices/`.

## Completed decisions

### OQ-007 — Source rights / licensing metadata — DECIDED

Accepted artifacts:

- `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- `specs/SOURCE_SCHEMA.v0.2.json`;
- `architecture/decisions/ADR-0005-source-rights-clearance.md`;
- `fixtures/sources/source_rights_cases.v0.1.json`.

### OQ-004 — Field-level provenance persistence — DECIDED

Accepted artifacts:

- `docs/research/OQ-004_FIELD_PROVENANCE_RESEARCH.md`;
- `specs/PROVENANCE_MODEL.v0.1.md`;
- `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json`;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`;
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json`;
- `architecture/decisions/ADR-0006-field-provenance-ledger.md`;
- `fixtures/provenance/`.

BoatDesign v0.4 and ResolvedConfiguration v0.2 are the accepted canonical contracts after OQ-001; BoatDesign v0.3 is retained only as historical accepted reference.

### Search Architecture + SEO — ACCEPTED ARCHITECTURAL PRINCIPLE

ADR-0007 establishes that Search Architecture and SEO are part of product architecture, not a post-launch marketing layer. `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` defines the baseline; OQ-018 gates the exact public URL/indexation/rendering surface before frontend implementation.

### OQ-001 — Derived-ratio / metric methodology — DECIDED

Accepted artifacts:

- `docs/research/OQ-001_DERIVED_METRICS_RESEARCH.md`;
- `specs/DERIVED_METRICS_SPEC.v1.0.md`;
- `specs/RATIO_INPUT_BASIS_SCHEMA.v0.1.json`;
- `specs/DERIVED_METRICS_SCHEMA.v1.0.json`;
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json`;
- `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json`;
- `architecture/decisions/ADR-0008-derived-metric-methodology.md`;
- `fixtures/ratios/`.

The accepted methodology is `hullq-derived-1.0.0`.

### OQ-010 — Python/data-pipeline runtime and tooling baseline — DECIDED

Accepted artifacts:

- `docs/research/OQ-010_PYTHON_TOOLCHAIN_RESEARCH.md`;
- `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md`;
- `architecture/decisions/ADR-0009-python-research-toolchain.md`.

Accepted baseline: CPython 3.14 + uv + uv_build + Ruff + mypy strict + pytest/coverage/Hypothesis + jsonschema + HTTPX + asyncio TaskGroup + Stage-2 SQLite for local benchmark/job state only.

## Current operational step

### SLICE-0001 — Close repository bootstrap — READY

Root Python project configuration, package/test skeleton, cross-platform GitHub Actions CI and dependency-update policy are present. A valid committed `uv.lock` remains the final bootstrap gate and MUST be generated in a networked development environment before HullQ domain implementation begins.

See `docs/slices/SLICE-0001-bootstrap-closure.md`.

## New pre-code data-model gate

### OQ-019 — Canonical logical data model — OPEN

Before HullQ domain implementation, the distributed accepted contracts must be consolidated into one persistence-neutral logical model covering entity inventory, relationships/cardinalities, lifecycle/mutability, domain boundaries and required access patterns.

This is **not** the production database-technology decision.

- OQ-019 answers: what data exists, how it relates, what is immutable/versioned/derived, and what access patterns must be supported.
- OQ-012 later answers: which production persistence/search technology and indexing strategy best implements that model after benchmark evidence exists.

OQ-019 is executed through `SLICE-0002` after bootstrap closure.

## Following steps

1. execute `SLICE-0001`: generate and commit `uv.lock`, pass full local gates and first green Linux + Windows CI;
2. execute `SLICE-0002`: research and explicitly accept OQ-019 canonical logical data model;
3. begin Stage-2 contract runtime slice;
4. continue to deterministic normalization, provenance/derived runtime and ResearchJob state machine;
5. build the 50–100-design benchmark only after those foundations are implementation-ready.

No HullQ domain code should be introduced before steps 1 and 2 are complete.

OQ-009 remains required before query-engine implementation and OQ-018 before the public search/SEO surface.

## Retention / freemium direction

Accepted strategic direction is documented in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`: HullQ serves active buyers plus long-lived owner-watchers/opportunity hunters; core search remains open in the preferred freemium model; subscription value attaches to monitoring capacity/frequency and advanced market-watch features. Exact pricing/limits remain OQ-016.

## Parallel work

OQ-013 — market-source access matrix can be researched in parallel but MUST NOT distract from the design-data foundation.

## Do not start yet

- production broad ingestion;
- frontend implementation;
- application/backend implementation;
- physical production database/search technology selection under OQ-012;
- production marketplace adapters;
- accounts/alerts;
- multi-source listing deduplication.

These remain downstream of explicit gates in `docs/EXECUTION_PLAN.md`.

## Repository audit

A pre-OQ-004 consistency audit is recorded in `docs/governance/REPOSITORY_AUDIT_2026-08-18.md`. It resolved stale draft placement, legacy decision-ID drift, missing identity requirements, architecture wording drift and the missing price-intelligence decision gate.
