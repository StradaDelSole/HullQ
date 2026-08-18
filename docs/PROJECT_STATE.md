# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 2.3 — SLICE-0004 measurement normalization READY  
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
- initial application/deployment stack accepted (OQ-008/OQ-011/OQ-012 / ADR-0010);
- requirements/test/governance baseline established;
- bounded implementation-slice workflow established under `docs/slices/`.

## Accepted initial application/deployment architecture

ADR-0010 and `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md` define the target stack:

```text
Cloudflare edge
      |
      v
Contabo Linux VPS
      |
      +-- Astro + TypeScript web
      |     \-- React islands only where state complexity justifies them
      +-- FastAPI / CPython 3.14
      +-- PostgreSQL
      +-- background/scheduled Python worker when needed
      \-- simple VPS deployment / Caddy baseline

Off-VPS backup/artifact direction: Cloudflare R2 when introduced
Later native mobile: Flutter Android/iOS via the same accepted API boundary
```

Guardrails:

- Contabo is the selected initial provider, while application code targets a portable commodity Linux VPS;
- Cloudflare remains edge infrastructure, not the canonical application runtime/database;
- PostgreSQL is the initial production relational store;
- no dedicated search engine initially; PostgreSQL indexes/projections come first after query semantics are accepted;
- Strapi, Next.js, Flutter Web and a full-site client-only React SPA are not the selected baseline;
- no CMS is required initially;
- no Kubernetes/broker/distributed scheduler/paid managed-service dependency is part of the initial baseline without measured need.

### Auth intentionally remains undecided

OQ-014 remains deliberately deferred until the dedicated account/auth slice. The stack must support users, SavedQuery, Monitor and Alert, but **no JWT/session/auth-provider/library/password/OAuth/email-verification/privacy implementation has been selected yet**.

OQ-006 still controls alert cadence/freshness. OQ-015 still controls the stable HTTP API/versioning boundary. OQ-018 still controls exact public SEO URL/index/rendering/canonicalization/structured-data behavior.

## Completed evidence gate — SLICE-0002

SLICE-0002 is `DONE`. Main findings retained for implementation:

1. Wikidata CC0 is the strongest current broad bootstrap candidate; exact live count belongs to the future adapter rather than a hard-coded planning number.
2. No single SailboatData replacement exists; HullQ needs broad open bootstrap plus progressive manufacturer/designer/class/archive enrichment.
3. In the deliberately difficult 21-case evidence set, useful common specs were directly available in 18/21, keel/board architecture in 17/21, rudder/support architecture in 13/21 and explicit skeg/skegless state in 7/21.
4. 8/21 cases have option/variant changes to core technical values.
5. 11/21 cases expose a non-generic displacement/mass basis; source basis must survive normalization.
6. Primary sources can conflict internally or with other strong evidence; resolution remains field-specific.
7. ORC remains blocked for systematic commercial ingestion under reviewed terms absent separate permission/licence.
8. Rudder/skeg classification will drive disproportionate review cost.

Evidence package:

- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`
- `research/evidence/SOURCE_REGISTER.md`
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`
- `research/benchmark/SEED_RESEARCH_NOTES.md`
- `research/benchmark/SEED_RESEARCH_SUPPLEMENT.md`

## Completed implementation — SLICE-0003

### Canonical JSON-Schema Contract Runtime — DONE

SLICE-0003 was implemented by Claude Code, independently reviewed, explicitly accepted by the project owner, and merged through PR #3 on 2026-08-18.

Final merge commit: `b927a6b17e204de43773c8682e36a29db037ab8a`.

Acceptance evidence:

- local implementation report: repository validator PASS, Ruff PASS, mypy strict PASS, pytest 39/39 PASS, coverage 98.18%, pip-audit PASS;
- PR-head CI run #45: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- independent code/spec review: ACCEPT, no blocking findings;
- explicit project-owner acceptance received on 2026-08-18.

The merged runtime provides repository-local Draft 2020-12 schema loading/validation and local `$id`/`$ref` resolution without network retrieval. No normalization/acquisition/persistence/query/frontend semantics were introduced.

## Current operational step — SLICE-0004

### Measurement Observation and Deterministic Unit/Basis Normalization — READY

See `docs/slices/SLICE-0004-measurement-normalization.md`.

The slice is intentionally narrow:

- deterministic conversion of explicit length/mass/area values to SI;
- explicit supported units only;
- exact conversion relationships covered by tests;
- raw source text and semantic labels preserved unchanged;
- accepted displacement/sail-area basis values remain explicit and machine-visible;
- `unknown` remains distinct from `source_unspecified`;
- **no free-text source-label inference** such as automatically mapping `half-load`, `EEC light`, `unladen` or `working sails` into accepted semantic basis values;
- no source acquisition, identity, appendage, provenance, persistence, API or frontend behavior.

This boundary follows directly from SLICE-0002 evidence: unit conversion is highly automatable, while source-semantic interpretation often requires explicit rules/evidence/review.

## Evidence-derived implementation sequence

1. ~~SLICE-0003~~ — **DONE**: canonical JSON-Schema contract runtime;
2. **SLICE-0004 — READY:** measurement observation + deterministic unit/basis normalization preserving raw semantics;
3. SLICE-0005 — identity/model/generation text primitives;
4. SLICE-0006 — appendage/configuration normalization for independent keel/board/rudder/skeg/count/state relationships;
5. SLICE-0007 — provenance/conflict runtime;
6. SLICE-0008 — derived metrics;
7. SLICE-0009 — ResearchJob state machine;
8. SLICE-0010 — rights-gated first real acquisition adapter, preferred initial target Wikidata CC0.

Only SLICE-0004 is currently `READY`. SLICE-0005–0010 remain rolling-wave backlog and MUST NOT be started automatically.

## Downstream gates

- 50–100 difficult designs remain the real pipeline benchmark after the first implementation slices;
- broad ingestion toward 1,000 → 2,500 → 5,000 → 10,000+ designs follows benchmark hardening;
- OQ-009 is required before query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

The physical technology choices PostgreSQL/FastAPI/Astro/Contabo are accepted, but their implementation still waits for the relevant bounded slices.

## Agent/repository working convention

Coding agents should read repository files from the **local checkout** for normal implementation work. GitHub is the canonical shared state for pushed branches, PRs, CI, review and accepted `main`, but agents should not repeatedly fetch ordinary repository files through remote tooling when the synchronized local checkout already contains them.

Before starting a new slice locally, synchronize `main` explicitly and avoid merging `main` into an old feature branch by accident:

```bash
git switch main
git pull --ff-only origin main
```

Then create/use the assigned slice branch. Branch work must be pushed to GitHub for review; final `DONE` remains owned by the acceptance workflow, not the implementation agent.

## Retention / freemium direction

Accepted strategic direction remains in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`: core technical search stays open in the preferred freemium thesis; subscription value attaches primarily to monitoring capacity/frequency and advanced market intelligence. Exact pricing/limits remain OQ-016.

## Parallel work

OQ-013 market-source access research may continue in parallel when useful, but must not distract from the canonical design-data foundation.

## Do not start yet

- SLICE-0005 or later implementation;
- production broad ingestion;
- PostgreSQL production schema/application persistence;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
