# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 2.2 — SLICE-0003 canonical contract runtime READY  
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
- source-rights/clearance model accepted (OQ-007 / ADR-0005);
- field-level provenance accepted (OQ-004 / ADR-0006);
- search/SEO as first-class product architecture accepted (ADR-0007);
- derived metrics methodology accepted (OQ-001 / ADR-0008);
- Python research toolchain accepted (OQ-010 / ADR-0009);
- requirements/test/governance baseline established;
- bounded implementation-slice workflow established under `docs/slices/`.

## Completed bootstrap

### SLICE-0001 — Close repository bootstrap — DONE

`uv.lock` is committed and the accepted local quality gates passed. See `docs/slices/SLICE-0001-bootstrap-closure.md` for the recorded bootstrap evidence.

## Completed evidence gate

### SLICE-0002 — Design Data Source Research & Seed Corpus — DONE

SLICE-0002 completed its independent review and was explicitly accepted by the project owner on 2026-08-18. The final research-agent handoff was `REVIEW`; the slice was moved to `DONE` only after review and project-owner acceptance under the status-authority rule in `CLAUDE.md`.

Evidence package:

- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`
- `research/evidence/SOURCE_REGISTER.md`
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`
- `research/benchmark/SEED_RESEARCH_NOTES.md`
- `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md`

Main findings retained for implementation:

1. **Wikidata CC0 is the strongest current broad bootstrap candidate.** Current planning evidence supports a four-digit open identity/common-field seed; the later adapter must record an exact reproducible live count rather than hard-code a volatile number.
2. **No single SailboatData replacement was found.** HullQ needs broad open bootstrap plus progressive manufacturer/designer/class/archive enrichment.
3. **Common specifications are much easier than HullQ differentiators.** In the deliberately difficult 21-case evidence set, useful common specs were directly available in 18/21 cases, keel/board architecture in 17/21, rudder/support architecture in 13/21, and explicit skeg/skegless state in only 7/21.
4. **Configuration awareness is mandatory.** 8/21 cases have option/variant changes to core technical values.
5. **Measurement basis must survive normalization.** 11/21 cases expose a non-generic mass/displacement basis.
6. **Primary sources are not globally authoritative.** Real manufacturer/archival source conflicts were observed; evidence resolution remains field-specific.
7. **ORC is technically attractive but is not a permitted HullQ systematic commercial bootstrap under the reviewed terms absent separate permission/licence.**
8. **Rudder/skeg research will drive disproportionate review.** These facts often live in prose, manuals, parts catalogues, class documents or drawings rather than structured model tables.

See `docs/slices/SLICE-0002-design-data-source-research.md` for final acceptance evidence and completion report.

## Current operational step

### SLICE-0003 — Canonical JSON-Schema Contract Runtime — READY

This is the first implementation slice after the evidence gate.

Objective: create one small reusable Python runtime for repository-local JSON Schema loading/validation and local `$id`/`$ref` resolution, replacing duplicated ad-hoc registry logic without introducing new HullQ boat semantics.

Key scope boundaries:

- local explicitly supplied schema directory only;
- Draft 2020-12 meta-schema validation;
- deterministic filename / `$id` registry;
- local reference resolution without network retrieval;
- reuse by contract tests and repository validator;
- no normalization, acquisition, persistence, Wikidata, source-rights runtime, derived formulas, query engine, frontend or market behavior.

See `docs/slices/SLICE-0003-canonical-contract-runtime.md`.

## Evidence-derived implementation sequence

1. **SLICE-0003 — READY:** canonical JSON-Schema contract runtime / local reference registry;
2. SLICE-0004 — measurement observation + unit/basis normalization preserving raw semantics;
3. SLICE-0005 — identity/model/generation text primitives;
4. SLICE-0006 — appendage/configuration normalization for independent keel/board/rudder/skeg/count/state relationships;
5. SLICE-0007 — provenance/conflict runtime;
6. SLICE-0008 — derived metrics;
7. SLICE-0009 — ResearchJob state machine;
8. SLICE-0010 — rights-gated first real acquisition adapter, preferred initial target Wikidata CC0.

Only SLICE-0003 is detailed/READY. SLICE-0004–0010 remain directional rolling-wave backlog until prior implementation evidence justifies detailing them.

## Handoff rule for SLICE-0003

Claude Code / the implementation agent should:

1. read `CLAUDE.md`;
2. execute only `docs/slices/SLICE-0003-canonical-contract-runtime.md`;
3. run the required local quality gates;
4. hand the slice off as `REVIEW` or `BLOCKED` using the standard completion report;
5. not mark it `DONE`;
6. not start SLICE-0004 automatically.

Independent review + explicit project-owner acceptance remain required for `REVIEW → DONE`.

## Downstream gates unchanged

- 50–100 difficult designs remain the real pipeline benchmark after the first implementation slices;
- broad ingestion toward 1,000 → 2,500 → 5,000 → 10,000+ designs follows benchmark hardening;
- OQ-009 is required before query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-012 remains the later physical production database/search/index decision.

## Retention / freemium direction

Accepted strategic direction remains in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`: core technical search stays open in the preferred freemium thesis; subscription value attaches primarily to monitoring capacity/frequency and advanced market intelligence. Exact pricing/limits remain OQ-016.

## Parallel work

OQ-013 market-source access research may continue in parallel when useful, but must not distract from the canonical design-data foundation.

## Do not start yet

- SLICE-0004 or later implementation;
- production broad ingestion;
- frontend/application backend;
- physical production database/search technology selection;
- production marketplace adapters;
- accounts/alerts;
- multi-source listing deduplication.
