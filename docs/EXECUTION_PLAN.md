# HullQ — Step-by-Step Execution Plan

**Status:** ACTIVE master execution plan  
**Method:** docs-to-code  
**Repository:** single repository

This document is the execution order. `docs/ROADMAP.md` remains the strategic phase view; this plan defines the actual gates and deliverables.

## Operating rule for every step

Every implementation step follows:

```text
resolve blocker
→ update normative spec/requirements
→ define tests/fixtures
→ implement smallest coherent unit
→ pass quality gate
→ commit/version/change log where relevant
```

No downstream step may silently decide an upstream open question.

---

# Stage 0 — Repository governance and specification discipline

**Goal:** make the repository safe for AI-assisted docs-to-code development before meaningful code exists.

## 0.1 Establish authority and workflow — DONE

Artifacts:

- `docs/DOCS_TO_CODE_METHOD.md`
- `docs/governance/DOCUMENT_AUTHORITY.md`
- `docs/governance/OPEN_QUESTION_PROCESS.md`
- `docs/governance/TRACEABILITY.md`
- `specs/REQUIREMENTS.md`
- `specs/TEST_STRATEGY.md`
- ADR framework/templates

## 0.2 Lock repository decisions — DONE

Accepted:

- ADR-0001 single repository
- ADR-0002 docs-to-code
- ADR-0003 broad coverage + progressive verification depth

## 0.3 Tooling/repository bootstrap — IN PROGRESS

Under accepted OQ-010 / ADR-0009:

- initialize the real Git repository when moved to its hosted/local Git working tree;
- add `.editorconfig`, `.gitignore`, root tooling configuration;
- add CI skeleton;
- validate all JSON Schemas and fixtures in CI;
- enforce formatter/linter/type/test gates for implemented languages;
- use Conventional Commits;
- protect the default branch with required checks when hosted on GitHub or equivalent.

**Bootstrap status:** root configuration, package/test skeleton, CI and dependency-update policy are created. `uv.lock` generation + successful locked CI remain required before this step is DONE.

**Exit gate:** G0 governance baseline complete.

---

# Stage 1 — Resolve data-foundation blockers

**Goal:** prevent expensive broad ingestion against unstable identity/provenance semantics.

## 1.1 OQ-003 — Model / generation / variant identity — DONE

Produce:

- `specs/IDENTITY_MODEL.v0.1.md`
- examples covering simple model, named variant, major generation, keel/rig variants and builder changes;
- schema changes if necessary;
- test fixtures for ambiguous identities.

Decision questions include:

- What constitutes one `BoatDesign`?
- When is a production generation a separate design entity?
- When is a keel/rig option merely a variant?
- Can one listing resolve to a variant when source data only identifies the parent model?

**Blocking:** broad canonical ingestion.

## 1.2 OQ-007 — Source rights/licensing model — DONE

Produce:

- source-rights taxonomy;
- required Source fields for license/rights/access constraints;
- policy for CC0, CC-BY, CC-BY-SA, public-domain, permission-based, factual-primary-source and unknown-rights sources;
- explicit rule for what may seed identity vs production technical values.

Accepted decision package: `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`, `specs/SOURCE_RIGHTS_POLICY.v0.1.md`, `specs/SOURCE_SCHEMA.v0.2.json`, ADR-0005 and source-rights fixtures.

**Blocking:** open-data bootstrap at scale.

## 1.3 OQ-004 — Provenance persistence shape — COMPLETE

Accepted ADR-0006 and `specs/PROVENANCE_MODEL.v0.1.md`: separate immutable FieldEvidence, versioned FieldResolution and DerivationRecord lineage; RFC 6901 JSON Pointer field addressing; plain canonical searchable values.

## 1.4 OQ-001 — Derived ratios / metrics — DONE

Accepted methodology `hullq-derived-1.0.0` and its contracts define:

- formulas;
- canonical input units;
- multihull applicability/exclusions;
- rounding/display rules;
- missing-input behavior;
- reference examples;
- automated boundary/golden tests.

## 1.5 OQ-010 — Research/data toolchain — DONE

Accepted via ADR-0009: use the smallest modern stack for the data/research engine.

Evaluate at least:

- supported Python runtime;
- project/dependency manager;
- Ruff baseline;
- type checker;
- pytest;
- JSON Schema validator;
- persistence for benchmark/local development;
- job orchestration approach appropriate to a single-repo lean project.

Avoid selecting distributed infrastructure before throughput evidence requires it.

**Stage 1 exit:** all blocking data contracts are implementation-ready and G0 passes for pipeline code.

---

# Stage 2 — Build the research-pipeline benchmark implementation

**Goal:** prove that HullQ can research accurately and cheaply enough to scale.

## 2.1 Create repository code structure

Only after ADR/toolchain decisions. Suggested logical shape (exact names may be refined):

```text
apps/                  # user-facing applications when introduced
packages/              # shared first-party libraries/contracts if needed
services/              # deployable/background components if actually needed
src/ or packages/...   # research/domain implementation per chosen stack
specs/
research/
tests/
fixtures/
docs/
architecture/
```

Do not create separate repositories.

## 2.2 Implement schemas/contracts first

- Source
- BoatDesign/identity structure
- ResearchJob
- evidence/conflict structures
- taxonomy validation
- dataset/version metadata

Add positive and negative schema fixtures.

## 2.3 Implement deterministic normalization library

Functions/modules for:

- unit parsing/conversion;
- text normalization without identity loss;
- canonical manufacturer/model strings;
- taxonomy mappings;
- raw-value preservation;
- confidence/evidence attachment;
- validation rules.

Network/source discovery is NOT embedded in these pure domain functions.

## 2.4 Implement research job state machine

Explicit states and restart behavior. Requirements:

- idempotent/restart-safe where possible;
- each stage records evidence/errors;
- failures do not corrupt accepted output;
- review queue is explicit;
- raw artifacts remain immutable.

## 2.5 Build benchmark corpus

50–100 deliberately difficult designs across:

- mono/cat/tri;
- simple and ambiguous identities;
- production generations;
- keel/centerboard/lifting/bilge/daggerboard configurations;
- skeg/partial-skeg/spade/keel-hung/twin rudders;
- mixed source availability;
- conflicting specifications.

This corpus benchmarks the pipeline; it is not the product universe.

## 2.6 Measure benchmark

Mandatory metrics:

- identity-resolution success;
- source discovery success;
- automated acceptance rate;
- human-review rate;
- minutes per reviewed record;
- cost per design;
- conflict rate;
- variant ambiguity rate;
- HullQ-critical-field completeness;
- repeatability/idempotency;
- false normalization/classification errors.

## 2.7 Harden until Gate G3 passes

Do not scale because the happy path works. Fix taxonomy/schema/validation/review behavior based on benchmark evidence.

---

# Stage 3 — Build the broad Sailboat universe

**Goal:** reach breadth sufficient for unknown-model discovery.

## 3.1 Establish legal/open identity bootstrap sources

Use approved sources from OQ-007. Build a broad identity queue without importing technical values from the prohibited/reference scrape.

## 3.2 Create canonical identity universe

Target progression rather than a fake hard threshold:

- first 1,000 identities;
- 2,500;
- 5,000;
- continue toward SailboatData-like breadth (potentially 5,000–10,000+).

At each milestone measure duplicate/ambiguity rates.

## 3.3 Enrich basic searchable fields

Priority:

- identity/years;
- LOA/LWL/beam/draft;
- displacement;
- hull configuration;
- material;
- rig where available.

## 3.4 Enrich HullQ-critical differentiation

Priority:

- keel type/subtype;
- rudder type;
- skeg type;
- variants/generations;
- draft ranges/options;
- construction method where useful.

## 3.5 Calculate ratios

Only from canonical inputs and only under approved formula version.

## 3.6 Dataset snapshots and reproducibility

Introduce explicit dataset release/snapshot metadata so a search result can be reproduced against the same dataset + taxonomy + formula versions.

## 3.7 Market-driven enrichment loop

Unknown models observed in real market research later feed back into priority enrichment.

**Stage exit:** Gate G4 passes and coverage is broad enough that query-engine testing is meaningful.

---

# Parallel Track M — Market access and integration discovery

**Starts during Stage 1; does not wait for frontend work.**

## M1 Build market-source access register

For each target source record:

- official API?
- commercial API?
- broker/dealer feed?
- partner program?
- permitted deep links?
- query parameters?
- scraping/automation terms?
- storage/cache constraints?
- display/attribution constraints?
- pricing/access requirements?
- contact/status/date verified?

Initial targets:

- Boat24
- YachtWorld / Boats Group
- Scanboat
- TheYachtMarket
- Rightboat / other relevant regional sources

## M2 Rank integration paths

Prefer in order where commercially sensible:

1. documented permitted API/data partnership;
2. commercial/partner access;
3. broker/regional feeds;
4. stable permitted deep links;
5. automated retrieval only after legal/terms review.

## M3 Prove one source

Build no multi-source orchestration yet. One source must prove the canonical adapter contract and actual maintenance burden.

## M4 Measure maintenance

Track adapter break/fix frequency and human minutes. This is a first-class business KPI because HullQ targets low ongoing maintenance.

---

# Pre-Stage-4 public search/SEO gate — OQ-018

Before public frontend/search-surface implementation, define the canonical page taxonomy, URL grammar, faceted-navigation crawl/index policy, rendering strategy, canonicalization/sitemaps, internal-linking rules and structured-data mapping under ADR-0007. This does not block research-pipeline or broad-data work.

# Stage 4 — Technical Query Engine

**Goal:** implement the central HullQ differentiator over the broad database.

## 4.1 Resolve OQ-009 first

Freeze semantics for:

- confirmed match;
- confirmed non-match;
- insufficient data;
- inclusion/exclusion of unknown candidates;
- range filters;
- OR conditions such as rudder type sets;
- variant-aware matching.

## 4.2 Define machine-readable query contract

Create versioned query schema before implementation.

## 4.3 Implement pure deterministic query engine

Keep query semantics independent from UI and marketplace adapters.

## 4.4 Build query golden masters

Include realistic examples such as:

```text
34–40 ft
Draft <= 1.8 m
GRP
Skeg-hung OR keel-hung rudder
D/L >= threshold
```

Validate unknown-data behavior explicitly.

## 4.5 Compare engine

Side-by-side normalized comparison uses the same canonical dataset and displays missing/uncertain data honestly.

**Exit:** Gate G5.

---

# Stage 5 — Application/backend architecture and persistence

## 5.1 Resolve OQ-011/OQ-012

Decide:

- backend/application framework;
- whether Strapi remains useful or adds unnecessary abstraction;
- database technology;
- search/index strategy;
- deployment topology;
- migration tooling.

Choose based on measured dataset/query needs, not habit.

## 5.2 Persist canonical dataset and query API

Implement storage adapters behind domain interfaces. Domain/search rules stay independent from framework ORM semantics.

## 5.3 API contract

If HTTP boundary is introduced, specify it first with an official OpenAPI version selected at implementation time.

---

# Stage 6 — Web product MVP

**Goal:** smallest high-quality public product using the broad database.

## 6.1 Resolve OQ-008 frontend stack

Select modern framework/tooling based on:

- static/SEO needs;
- interactive filtering;
- accessibility;
- bundle/performance;
- maintainability;
- single-repo integration.

## 6.2 Build discovery UX

Primary path:

```text
technical query
→ matching unknown designs
→ transparent match/unknown state
→ compare
→ market availability action
```

Do not recreate the raw-field Tabulator prototype.

## 6.3 Add compare

Comparison is canonical-data based and version-aware.

## 6.4 Integrate first permitted market path

Use the best validated path from Track M: real adapter if cleanly available; otherwise a documented deep-link/partner fallback while maintaining the product boundary.

---

# Stage 7 — Accounts, saved technical queries and alerts

## 7.1 Security/privacy spec first

Resolve OQ-014 before account code.

## 7.2 Saved query is first-class

Store the versioned technical query itself, not just a list of model names.

## 7.3 Alert resolver

```text
saved technical query
→ matching design set
→ grouped market lookups
→ new physical listings
→ notification
```

## 7.4 Dedup before multi-market alerts

Resolve OQ-005 before claiming cross-platform new-listing uniqueness.

## 7.5 Cadence/freshness

Resolve OQ-006 based on source constraints and actual user value.

---

# Stage 8 — Public release, distribution and low-maintenance operations

## 8.1 SEO/discovery surfaces

Focus on unique query/category surfaces and high-quality design pages only where they provide real value; do not assume head-on model-name SEO is the only acquisition strategy.

## 8.2 Product analytics

Measure:

- technical searches;
- zero/low-result searches;
- insufficient-data rates;
- compare usage;
- market click-through;
- saved-query/alert intent;
- returning active-search users;
- unknown model requests.

## 8.3 Business KPIs

Primary operational economics:

- monthly profit;
- human maintenance hours/month;
- **profit per maintenance hour**;
- unplanned maintenance hours;
- source integration maintenance cost;
- research/enrichment cost per design.

## 8.4 Scaling decision

HullQ is not currently designed around venture-scale expectations. If real traction later shows materially larger opportunity, evaluate a deliberate scaling strategy in a new ADR/business decision rather than pre-optimizing architecture now.

---

# Immediate next actions

The next work session should continue **Stage 1**, in order:

1. research and freeze `OQ-001` ratio formulas;
2. decide `OQ-010` Python/research toolchain;
3. bootstrap repo/CI and then implement the research pipeline.

Already completed foundation blockers: OQ-003 identity, OQ-007 source rights, OQ-004 provenance. OQ-009 must close before query-engine code; OQ-018 must close before the public frontend/search surface.

In parallel, begin `OQ-013` market-access research, but do not let it distract from the design-data foundation.


## Product-commercial gate — OQ-016 subscription packaging

Before paid subscription launch, validate and freeze pricing/entitlement defaults. The architecture must already support configurable Free/Plus/Pro entitlements without coupling query semantics to billing. Current hypothesis is documented in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`.


## Deferred market-intelligence gate

Before implementing durable listing-price history or Pro price-intelligence features, resolve `OQ-017` to define source-specific retention permission, listing lifecycle semantics, asking-price vs sale-price rules, aggregation windows and tests.
