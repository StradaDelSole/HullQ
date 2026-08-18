# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 0.3 / Stage 2 boundary — repository bootstrap  
**Execution plan:** `docs/EXECUTION_PLAN.md`

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
- engineering quality gates established.

## Newly completed decisions

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

BoatDesign v0.4 and ResolvedConfiguration v0.2 are now the accepted canonical contracts after OQ-001; BoatDesign v0.3 is retained only as historical accepted reference.

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

## Newly completed toolchain decision

### OQ-010 — Python/data-pipeline runtime and tooling baseline — DECIDED

Accepted artifacts:

- `docs/research/OQ-010_PYTHON_TOOLCHAIN_RESEARCH.md`;
- `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md`;
- `architecture/decisions/ADR-0009-python-research-toolchain.md`.

Accepted baseline: CPython 3.14 + uv + uv_build + Ruff + mypy strict + pytest/coverage/Hypothesis + jsonschema + HTTPX + asyncio TaskGroup + Stage-2 SQLite.

## Active implementation step

**Repository tooling + CI bootstrap under Stage 0.3.**

Created root Python project configuration, package/test skeleton, cross-platform GitHub Actions CI and dependency-update configuration. A valid committed `uv.lock` remains the final bootstrap gate and MUST be generated with uv 0.12.5+ in a networked development environment before Stage-2 implementation is mergeable.

## Following steps

1. generate and commit `uv.lock`;
2. pass the full Linux + Windows CI baseline;
3. begin Stage 2.2 contract implementation/tests;
4. continue to deterministic normalization and research job-state implementation.

OQ-009 remains required before query-engine implementation and OQ-018 before the public search/SEO surface.

## Retention / freemium direction

Accepted strategic direction is documented in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`: HullQ serves active buyers plus long-lived owner-watchers/opportunity hunters; core search remains open in the preferred freemium model; subscription value attaches to monitoring capacity/frequency and advanced market-watch features. Exact pricing/limits remain OQ-016.

## Parallel work

OQ-013 — market-source access matrix can be researched in parallel but MUST NOT distract from the design-data foundation.

## Do not start yet

- production broad ingestion;
- frontend implementation;
- application/backend implementation;
- production marketplace adapters;
- accounts/alerts;
- multi-source listing deduplication.

These remain downstream of explicit gates in `docs/EXECUTION_PLAN.md`.

## Repository audit

A pre-OQ-004 consistency audit is recorded in `docs/governance/REPOSITORY_AUDIT_2026-08-18.md`. It resolved stale draft placement, legacy decision-ID drift, missing identity requirements, architecture wording drift and the missing price-intelligence decision gate.
