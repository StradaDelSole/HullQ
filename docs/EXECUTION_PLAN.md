# HullQ — Step-by-Step Execution Plan

**Status:** ACTIVE master execution plan  
**Method:** docs-to-code + bounded implementation slices  
**Repository:** single repository  
**Operational queue:** `docs/slices/INDEX.md`

This document defines execution order and gates. `docs/ROADMAP.md` is the strategic phase view. `docs/slices/` decomposes the currently permitted work into small research/implementation contracts for coding agents.

## Operating rule for every step

```text
resolve blocker / gather real evidence
→ update normative spec/requirements where needed
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

# Stage 1 — Resolve data-foundation blockers and research real source data

**Goal:** prevent implementation and broad ingestion against hypothetical source conditions or unstable identity/provenance/calculation semantics.

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

## 1.6 Real design-data source research — REQUIRED BEFORE DOMAIN PIPELINE CODE

Executed by `SLICE-0002` after bootstrap closure.

HullQ must research the **actual independent sailboat-design data sources** from which its own canonical universe can be built rather than designing a pipeline around imagined inputs.

Required work includes:

- identify plausible broad identity/bootstrap sources usable under ADR-0005;
- build/extend the Source Register with rights/access/clearance information;
- map HullQ-critical technical fields to real source classes and observed availability;
- research official manufacturer/designer/class-association/archive sources for primary verification;
- manually research 20–30 representative difficult BoatDesign candidates;
- record real missing-data, conflict, generation, option and semantic-basis problems;
- distinguish likely automatable work from human-review work;
- derive extraction/normalization pipeline requirements from the observed source evidence.

The imported/reference SailboatData material may inform taxonomy, edge-case and candidate-model research but MUST NOT become an invisible production-value source.

The 20–30-design seed evidence sample is not the product database and not the final 50–100-design pipeline benchmark. Its purpose is to make later implementation evidence-driven.

**Stage 1 exit:** G0 passes and SLICE-0002 source/data research is complete enough to define the first pipeline implementation slices against real source conditions.

### Deferred logical-model note

OQ-019 is no longer a pre-code gate. Consolidating accepted contracts into a separate logical entity/relationship document may be revisited before production persistence under OQ-012 if implementation evidence shows that it is useful.

---

# Stage 2 — Build the research-pipeline benchmark implementation

**Goal:** implement against observed real source conditions, then prove that HullQ can research accurately, reproducibly and cheaply enough to scale.

Stage-2 implementation is decomposed through `docs/slices/INDEX.md`. Slice boundaries after SLICE-0002 must be refined from actual source evidence rather than treated as fixed in advance.

## 2.1 Repository code structure — BOOTSTRAPPED

Current single-repo structure includes root Python project config, `src/hullq/`, tests, specs, fixtures, research, docs and architecture. Do not create separate repositories or distributed services without a later accepted decision.

## 2.2 Implement canonical contract runtime first

Only after SLICE-0002 has documented the real source shapes and any resulting contract gaps have been resolved.

Implement runtime handling for accepted contracts such as:

- Source;
- BoatModel / BoatDesign / ResolvedConfiguration;
- provenance/evidence/resolution/derivation records;
- ResearchJob when its contract is ready;
- dataset/version metadata.

Positive and negative schema fixtures remain first-class tests.

## 2.3 Implement deterministic normalization library

Pure functions/modules for the source patterns proven necessary by SLICE-0002, including as applicable:

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

Use the source landscape and difficult cases discovered in SLICE-0002 to select the corpus. This corpus benchmarks the implemented pipeline; it is not the product universe.

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

## 3.1 Establish approved identity bootstrap sources

Promote the best cleared bootstrap path(s) identified during SLICE-0002 / later benchmark work. The reference SailboatData scrape may inform taxonomy/edge-case research but MUST NOT become an invisible production-value source.

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

- accepted domain/provenance contracts;
- real source and benchmark evidence;
- measured Stage-2/3 access patterns and scale;
- technical-query behavior;
- operational maintenance economics.

If a consolidated persistence-neutral logical model is useful at this stage, resolve/revive OQ-019 before choosing physical persistence. Do not choose by framework habit.

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
2. **SLICE-0002 — then:** research actual independent sailboat-design sources and complete the 20–30-design seed evidence sample.
3. Refine the implementation slices from those real findings.
4. Begin contract/runtime + deterministic-normalization implementation only after the source-research gate is sufficiently complete.
5. Continue OQ-013 market-access research in parallel when useful, without distracting from the design-data foundation.
