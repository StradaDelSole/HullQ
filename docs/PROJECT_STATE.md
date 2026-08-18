# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 0.3 complete — SLICE-0001 done; next: SLICE-0002 real design-data source research  
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

## Current operational step

### SLICE-0002 — Design Data Source Research & Seed Corpus — READY

SLICE-0001 is complete: `uv.lock` committed, all local gates green, Linux + Windows CI green.

See `docs/slices/SLICE-0002-source-data-research.md`.

## Completed bootstrap

### SLICE-0001 — Close repository bootstrap — DONE

`uv.lock` generated and committed; all local quality gates pass (Ruff format/lint, mypy strict, pytest 18/18, coverage 100%, pip-audit clean); first green Linux + Windows GitHub Actions CI run confirmed.

See `docs/slices/SLICE-0001-bootstrap-closure.md`.

## Immediate pre-domain research step

### SLICE-0002 — Design Data Source Research & Seed Corpus — READY

Before HullQ writes meaningful research-pipeline/domain code, research the **actual independent sailboat-design data sources** from which HullQ can build its own canonical universe.

This means researching real boat data, not choosing a database product.

SLICE-0002 must:

- identify plausible broad identity/bootstrap sources that are usable under the accepted source-rights model;
- map HullQ-critical fields to real sources and observed availability;
- research manufacturer/designer/class-association/archive sources for primary verification;
- manually research 20–30 representative difficult BoatDesign candidates;
- record missing data, source conflicts, generations/options and semantic ambiguity;
- distinguish what can likely be automated from what requires human review;
- derive actual extraction/normalization pipeline requirements from the source evidence.

SailboatData remains reference/prototype material only and MUST NOT become an invisible production-value source.

The 20–30-design seed sample is not the final benchmark. After implementation begins, HullQ still builds and measures the deliberately difficult 50–100-design research benchmark before broad ingestion.

## Current source-research direction

Initial candidate classes include:

- open structured data such as Wikidata for broad identity/common-field bootstrap where source clearance permits;
- official manufacturer heritage/current model pages, brochures, manuals and parts/heritage systems for primary factual verification;
- official designer/builder/class-association technical material;
- explicitly licensed secondary datasets where obligations are compatible with the accepted source-rights policy;
- commercial/community databases only as permitted research leads/reference where production clearance is absent.

Every source remains subject to ADR-0005: technical accessibility is not equivalent to rights or HullQ clearance.

## Following steps

1. ~~execute `SLICE-0001`~~ **DONE**: `uv.lock` committed, all gates green, Linux + Windows CI green;
2. execute `SLICE-0002`: perform real source/data research and the 20–30-design seed evidence sample;
3. use those findings to refine `SLICE-0003+` rather than coding against hypothetical input shapes;
4. implement contracts and deterministic normalization in bounded slices;
5. implement provenance/derived runtime and ResearchJob state machine;
6. build and measure the 50–100-design benchmark;
7. harden the pipeline before broad ingestion toward thousands of designs.

OQ-009 remains required before query-engine implementation and OQ-018 before the public search/SEO surface.

## Database / persistence note

The concrete production database/search/index choice remains OQ-012 and is **not** the immediate task. A separate logical-model consolidation may be revisited when implementation/persistence work requires it; it is not a substitute for researching the actual sailboat data sources first.

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
