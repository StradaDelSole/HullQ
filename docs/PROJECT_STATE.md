# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 2.2 — SLICE-0003 canonical contract runtime in REVIEW  
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

ADR-0010 and `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md` define the target stack before application/persistence/frontend work begins:

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

Key guardrails:

- Contabo is the selected initial provider, but application code targets a portable commodity Linux VPS;
- Cloudflare remains edge infrastructure, not the canonical application runtime/database;
- PostgreSQL is the initial production relational store;
- no dedicated search engine initially; PostgreSQL indexes/projections come first after query semantics are accepted;
- Strapi, Next.js, Flutter Web and a full-site client-only React SPA are not the selected baseline;
- no CMS is required initially;
- no Kubernetes/broker/distributed scheduler/paid managed-service dependency is part of the initial baseline without measured need.

### Auth intentionally remains undecided

OQ-014 remains deliberately deferred until the dedicated account/auth slice. The stack must support users, SavedQuery, Monitor and Alert, but **no JWT/session/auth-provider/library/password/OAuth/email-verification/privacy implementation has been selected yet**.

OQ-006 still controls alert cadence/freshness. OQ-015 still controls the stable HTTP API/versioning boundary. OQ-018 still controls exact public SEO URL/index/rendering/canonicalization/structured-data behavior.

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

### SLICE-0003 — Canonical JSON-Schema Contract Runtime — REVIEW

Claude Code implemented the slice on branch `slice/0003-canonical-contract-runtime`, commit `7b8f4a9066031b2de6d4149ee31fc55f7be85b6c`.

Draft PR: **#3 — SLICE-0003: canonical JSON-Schema contract runtime**.

Reported local evidence:

- repository validator PASS;
- Ruff format/lint PASS;
- mypy strict PASS;
- pytest 39/39 PASS;
- coverage 98.18%;
- pip-audit PASS;
- no normalization/acquisition/persistence/query/frontend/domain-semantics expansion.

The actual GitHub commit/diff has been independently inspected and is consistent with the intended slice boundary. Remote PR CI was triggered after opening PR #3 and remains an external acceptance gate until observed green.

SLICE-0003 MUST NOT be moved to `DONE` or merged merely because local validation passed. Explicit project-owner acceptance remains required after remote CI + independent review.

SLICE-0004 remains `BACKLOG`.

## Evidence-derived implementation sequence

1. **SLICE-0003 — REVIEW:** canonical JSON-Schema contract runtime / local reference registry;
2. SLICE-0004 — measurement observation + unit/basis normalization preserving raw semantics;
3. SLICE-0005 — identity/model/generation text primitives;
4. SLICE-0006 — appendage/configuration normalization for independent keel/board/rudder/skeg/count/state relationships;
5. SLICE-0007 — provenance/conflict runtime;
6. SLICE-0008 — derived metrics;
7. SLICE-0009 — ResearchJob state machine;
8. SLICE-0010 — rights-gated first real acquisition adapter, preferred initial target Wikidata CC0.

SLICE-0004–0010 remain directional rolling-wave backlog until prior implementation evidence justifies detailing them.

## Downstream gates

- 50–100 difficult designs remain the real pipeline benchmark after the first implementation slices;
- broad ingestion toward 1,000 → 2,500 → 5,000 → 10,000+ designs follows benchmark hardening;
- OQ-009 is required before query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

The physical technology choices PostgreSQL/FastAPI/Astro/Contabo are accepted, but their implementation still waits for the relevant bounded slices.

## Retention / freemium direction

Accepted strategic direction remains in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`: core technical search stays open in the preferred freemium thesis; subscription value attaches primarily to monitoring capacity/frequency and advanced market intelligence. Exact pricing/limits remain OQ-016.

## Parallel work

OQ-013 market-source access research may continue in parallel when useful, but must not distract from the canonical design-data foundation.

## Do not start yet

- SLICE-0004 or later implementation before SLICE-0003 acceptance;
- production broad ingestion;
- PostgreSQL production schema/application persistence;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
