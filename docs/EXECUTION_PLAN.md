# HullQ — Step-by-Step Execution Plan

**Status:** ACTIVE master execution plan  
**Method:** docs-to-code + bounded implementation slices  
**Repository:** single repository  
**Operational queue:** `docs/slices/INDEX.md`

This document defines execution order and gates. `docs/ROADMAP.md` is the strategic phase view. `docs/slices/` decomposes the currently permitted work into small research/implementation contracts for coding agents.

## Operating rule for every step

```text
resolve blocker
→ update normative spec/requirements
→ define tests/fixtures
→ create/ready a bounded slice
→ implement/research smallest coherent unit
→ pass quality gate
→ review
→ merge/version/change log where relevant
```

No downstream step may silently decide an upstream open question. An assigned agent MUST NOT automatically begin the next slice.

---

# Stage 0 — Repository governance and specification discipline

**Goal:** make the repository safe for AI-assisted docs-to-code development before meaningful domain code exists.

## 0.1 Establish authority and workflow — DONE

Artifacts include:

- `docs/DOCS_TO_CODE_METHOD.md`
- `docs/governance/DOCUMENT_AUTHORITY.md`
- `docs/governance/OPEN_QUESTION_PROCESS.md`
- `docs/governance/TRACEABILITY.md`
- `specs/REQUIREMENTS.md`
- `specs/TEST_STRATEGY.md`
- ADR framework/templates

## 0.2 Lock foundational repository decisions — DONE

Accepted:

- ADR-0001 single repository
- ADR-0002 docs-to-code
- ADR-0003 broad coverage + progressive verification depth

## 0.3 Tooling/repository bootstrap — IN PROGRESS

Accepted OQ-010 / ADR-0009 baseline is implemented in repository configuration and CI.

Remaining gate is `SLICE-0001`:

- generate real `uv.lock` under accepted Python 3.14 + uv toolchain;
- synchronize locked environment;
- pass repository validator, Ruff, mypy, pytest/coverage and dependency audit;
- pass Linux + Windows GitHub Actions.

**Exit gate G0:** reproducible locked toolchain + green baseline CI.

---

# Stage 1 — Resolve data-foundation blockers

**Goal:** prevent implementation and broad ingestion against unstable identity, provenance, calculation or data-model semantics.

## 1.1 OQ-003 — Model / generation / variant identity — DONE

Accepted:

- `specs/IDENTITY_MODEL.v0.1.md`
- ADR-0004
- identity schemas/fixtures

## 1.2 OQ-007 — Source rights/licensing model — DONE

Accepted:

- source-rights taxonomy;
- Source rights/access/clearance metadata;
- production/bulk default-deny where rights remain unresolved;
- ADR-0005 + schemas/fixtures.

## 1.3 OQ-004 — Field-level provenance persistence — DONE

Accepted ADR-0006 and `specs/PROVENANCE_MODEL.v0.1.md` define separate immutable FieldEvidence, versioned FieldResolution and DerivationRecord lineage with RFC-6901 field addressing.

## 1.4 OQ-001 — Derived ratios / metrics — DONE

Accepted methodology `hullq-derived-1.0.0` defines formulas, canonical inputs, applicability, status behavior, rounding and golden tests.

## 1.5 OQ-010 — Research/data toolchain — DONE

Accepted via ADR-0009. Bootstrap closure remains Stage 0.3 operational work, not an open toolchain decision.

## 1.6 OQ-019 — Canonical logical data model — OPEN / PRE-CODE GATE

Before HullQ domain implementation, consolidate the accepted contracts into one persistence-neutral logical model.

Required output:

- complete entity/value-object inventory;
- relationships and cardinalities;
- stable identity/reference rules;
- lifecycle/mutability/versioning classification;
- explicit separation of canonical design universe, research/provenance, derived calculations, dataset releases, market observations and user-query/monitor domains;
- documented access patterns and order-of-magnitude scale assumptions for later persistence research;
- mapping back to accepted schemas/specs.

Executed by `SLICE-0002` after bootstrap closure.

**Important distinction:** OQ-019 defines **what HullQ data is and how it relates**. It MUST NOT choose production PostgreSQL/Elasticsearch/OpenSearch/document DB/ORM/etc. OQ-012 later chooses physical persistence/search technology based on this logical model plus benchmark evidence.

**Stage 1 exit:** G0 passes and OQ-019 is accepted.

---

# Stage 2 — Build the research-pipeline benchmark implementation

**Goal:** prove that HullQ can research accurately, reproducibly and cheaply enough to scale.

Stage-2 implementation is decomposed through `docs/slices/INDEX.md`. Current directional sequence is contract runtime → deterministic normalization → provenance/derived runtime → ResearchJob state machine.

## 2.1 Repository code structure — BOOTSTRAPPED

Current single-repo structure includes root Python project config, `src/hullq/`, tests, specs, fixtures, research, docs and architecture. Do not create separate repositories or distributed services without a later accepted decision.

## 2.2 Implement canonical contracts first

Only after OQ-019 acceptance.

Implement runtime handling for accepted contracts such as:

- Source;
- BoatModel / BoatDesign / ResolvedConfiguration;
- provenance/evidence/resolution/derivation records;
- ResearchJob when its contract is ready;
- dataset/version metadata.

Positive and negative schema fixtures remain first-class tests.

## 2.3 Implement deterministic normalization library

Pure functions/modules for:

- unit parsing/conversion;
- text normalization without identity loss;
- canonical manufacturer/model strings;
- taxonomy mappings;
- raw-value preservation;
- confidence/evidence attachment;
- validation rules.

Network/source discovery MUST NOT be embedded in pure normalization functions.

## 2.4 Implement research job state machine

Requirements:

- explicit states;
- restart/idempotency where feasible;
- evidence/error recording per stage;
- failures never corrupt accepted output;
- explicit review queue;
- immutable raw artifacts.

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

Mandatory metrics include:

- identity-resolution success;
- source-discovery success;
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

Do not scale because the happy path works. Fix taxonomy/schema/validation/review behavior from benchmark evidence.

---

# Stage 3 — Build the broad sailboat universe

**Goal:** reach breadth sufficient for unknown-model discovery.

## 3.1 Establish legal/open identity bootstrap sources

Use approved OQ-007 sources. The reference SailboatData scrape may inform taxonomy/edge-case research but MUST NOT become an invisible production-value source.

## 3.2 Create canonical identity universe

Target progression:

- first 1,000 identities;
- 2,500;
- 5,000;
- continue toward SailboatData-like breadth, potentially 5,000–10,000+.

Measure duplicate/ambiguity rates at milestones.

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

## 3.5 Calculate derived metrics

Only from canonical inputs and only under approved method version.

## 3.6 Dataset snapshots and reproducibility

Introduce explicit dataset release/snapshot metadata so search results can be reproduced against the same dataset + taxonomy + formula versions.

## 3.7 Market-driven enrichment loop

Unknown models observed in real market work later feed priority enrichment.

**Stage exit:** Gate G4 passes and coverage is broad enough that query-engine testing is meaningful.

---

# Parallel Track M — Market access and integration discovery

Starts during data work but does not block design-database construction.

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

Initial targets include Boat24, YachtWorld / Boats Group, Scanboat, TheYachtMarket, Rightboat and relevant regional sources.

## M2 Rank integration paths

Prefer where commercially sensible:

1. documented permitted API/data partnership;
2. commercial/partner access;
3. broker/regional feeds;
4. stable permitted deep links;
5. automated retrieval only after legal/terms review.

## M3 Prove one source

Do not build multi-source orchestration until one source proves the canonical adapter contract and actual maintenance burden.

## M4 Measure maintenance

Track break/fix frequency and human minutes. Maintenance burden is a first-class business KPI.

---

# Pre-Stage-4 search-semantics gate — OQ-009

Before technical query-engine implementation, freeze confirmed match/non-match/insufficient-data semantics, ranges, OR conditions and variant-aware matching.

# Pre-public search/SEO gate — OQ-018

Before public frontend/search-surface implementation, define canonical page taxonomy, URL grammar, faceted crawl/index policy, rendering strategy, canonicalization/sitemaps, internal linking and structured-data mapping under ADR-0007.

---

# Stage 4 — Technical Query Engine

1. resolve OQ-009;
2. define versioned machine-readable query contract;
3. implement pure deterministic query engine independent of UI/market adapters;
4. build query golden masters including unknown-data behavior;
5. build canonical-data compare engine.

**Exit:** Gate G5.

---

# Stage 5 — Application/backend architecture and persistence

## 5.1 Resolve OQ-011/OQ-012

Choose application/backend architecture and production database/search/index strategy based on:

- accepted OQ-019 logical model;
- measured Stage-2/3 access patterns and scale;
- technical-query behavior;
- operational maintenance economics.

Do not choose by framework habit.

## 5.2 Persist canonical dataset and query API

Storage adapters stay behind domain interfaces. Domain/search rules remain independent from ORM/framework semantics.

## 5.3 API contract

If an HTTP boundary is introduced, specify/version it before implementation under OQ-015.

---

# Stage 6 — Web product MVP

1. resolve OQ-008 frontend stack;
2. resolve OQ-018 search/SEO public surface;
3. build technical discovery UX;
4. add compare;
5. integrate first permitted market path from Track M.

Do not recreate the raw-field prototype as the product UX.

---

# Stage 7 — Accounts, saved technical queries and alerts

1. resolve security/privacy baseline OQ-014;
2. persist SavedQuery as first-class versioned technical query;
3. add Monitor and Alert as separate domain concepts;
4. resolve OQ-005 before claiming cross-market physical-listing uniqueness;
5. resolve OQ-006 cadence/freshness policy.

Subscription entitlements control capacity/frequency/features, not technical query semantics.

---

# Stage 8 — Public release, distribution and low-maintenance operations

Measure product and business KPIs including technical searches, unknown/insufficient-data rates, compare/monitor usage, market click-through, returning users, monthly profit, human maintenance hours, unplanned maintenance, source-integration burden, research cost per design, and profit per maintenance hour.

HullQ is not currently optimized for venture-scale expectations. Revisit scaling only if real traction justifies a deliberate new decision.

---

# Deferred commercial/intelligence gates

- OQ-016: subscription pricing and entitlement defaults before paid launch.
- OQ-017: source-specific longitudinal listing/asking-price retention and price-intelligence semantics before durable price-history storage or Pro price-intelligence launch.

---

# Immediate next actions

1. **SLICE-0001 — READY:** generate `uv.lock`, pass local quality gates and first green Linux + Windows CI.
2. **SLICE-0002 — then:** research and decide OQ-019 canonical logical data model.
3. Only after both are DONE: begin the first HullQ domain implementation slice (contract runtime).
4. Continue OQ-013 market-access research in parallel when useful, without distracting from the data foundation.
