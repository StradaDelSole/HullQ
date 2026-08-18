# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 0.3 complete; SLICE-0002 design-data evidence research in REVIEW  
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

## Current operational step

### SLICE-0002 — Design Data Source Research & Seed Corpus — REVIEW

The evidence-first source research is complete enough for independent review and project-owner acceptance. The research agent has **not** marked the slice `DONE`.

See `docs/slices/SLICE-0002-design-data-source-research.md`.

### Evidence package

- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`
- `research/evidence/SOURCE_REGISTER.md`
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`
- `research/benchmark/SEED_RESEARCH_NOTES.md`
- `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md`

### Main findings

1. **Wikidata CC0 is the strongest current broad bootstrap candidate.** The official sailing data model and query surface support a four-digit open identity/common-field seed. Current planning range is approximately 1,000–1,500 useful sailboat-class identity candidates before additional-source expansion/deduplication; the future adapter must record an exact reproducible live count.
2. **No single SailboatData replacement was found.** HullQ needs broad open bootstrap plus progressive manufacturer/designer/class/archive enrichment.
3. **Common specifications are much easier than HullQ differentiators.** In the deliberately difficult 21-case evidence set, useful common specs were directly available in 18/21 cases, keel/board architecture in 17/21, rudder/support architecture in 13/21, and explicit skeg/skegless state in only 7/21.
4. **Configuration awareness is mandatory.** 8/21 cases have option/variant changes to core technical values; real examples include shallow/deep/lifting/twin keels, single/twin rudders, rig variants, folding multihull geometry and board-up/down states.
5. **Measurement basis must survive normalization.** 11/21 cases expose a non-generic mass/displacement basis such as lightship, half-load, measurement trim, unladen or EEC-light.
6. **Primary sources are not globally authoritative.** Najad's own multilingual N34 PDF conflicts internally on number built; Westerly archival evidence contains another count discrepancy. Evidence resolution must remain field-specific.
7. **ORC is technically attractive but not a permitted HullQ bootstrap under the terms reviewed.** Public access does not equal commercial/systematic database reuse clearance.
8. **Rudder/skeg research will drive disproportionate human review.** These facts often live in prose, parts catalogues, manuals, class documents or drawings rather than structured model tables.

## Evidence-derived implementation sequence

The backlog was refined from the observed source shapes:

1. SLICE-0003 — canonical JSON-Schema contract runtime / local reference registry;
2. SLICE-0004 — measurement observation + unit/basis normalization preserving raw semantics;
3. SLICE-0005 — identity/model/generation text primitives;
4. SLICE-0006 — appendage/configuration normalization for independent keel/board/rudder/skeg/count/state relationships;
5. SLICE-0007 — provenance/conflict runtime;
6. SLICE-0008 — derived metrics;
7. SLICE-0009 — ResearchJob state machine;
8. SLICE-0010 — rights-gated first real acquisition adapter, preferred initial target Wikidata CC0.

Only SLICE-0003 should be detailed/made READY after SLICE-0002 is accepted. Later slices remain directional rolling-wave backlog.

## Following gate

SLICE-0002 requires:

1. independent review of the research package;
2. explicit user/project-owner acceptance;
3. only then status `DONE` and preparation of SLICE-0003.

No domain implementation slice is READY while SLICE-0002 remains in REVIEW.

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

- SLICE-0003 implementation before SLICE-0002 acceptance;
- production broad ingestion;
- frontend/application backend;
- physical production database/search technology selection;
- production marketplace adapters;
- accounts/alerts;
- multi-source listing deduplication.
