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

The application technology target is accepted early under ADR-0010 so domain work does not drift into incompatible runtime/persistence/frontend assumptions. **This does not authorize early application implementation outside its later slices.**

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

## 0.3 Tooling/repository bootstrap — DONE

Accepted OQ-010 / ADR-0009 baseline is implemented with a committed `uv.lock`, locked synchronization, repository validation, Ruff, mypy, pytest/coverage, dependency audit and cross-platform CI.

**Exit gate G0:** passed.

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

Accepted via ADR-0009.

## 1.6 Real design-data source research — DONE

SLICE-0002 researched the **actual independent sailboat-design data sources** from which HullQ's own canonical universe can be built rather than designing a pipeline around imagined inputs.

Completed work includes:

- plausible broad identity/bootstrap sources under ADR-0005;
- Source Register rights/access/clearance evidence;
- HullQ-critical field/source coverage matrix;
- official manufacturer/designer/class-association/archive research;
- 20-design core sample + targeted edge-case supplement;
- observed missing-data, conflict, generation, option and semantic-basis problems;
- automation vs human-review findings;
- evidence-derived extraction/normalization pipeline needs.

The imported/reference SailboatData material remains research/reference only and MUST NOT become an invisible production-value source.

**Stage 1 exit:** passed after project-owner acceptance of SLICE-0002.

### Deferred logical-model note

OQ-019 is not a pre-code gate. Consolidating accepted contracts into a separate persistence-neutral logical entity/relationship document may be revisited before physical PostgreSQL schema work if implementation evidence shows that it is useful.

---

# Cross-stage application architecture decision — ACCEPTED EARLY

OQ-008, OQ-011 and OQ-012 were deliberately resolved before frontend/backend/persistence implementation to prevent incompatible stack assumptions while the Python/domain foundation is built.

Accepted via ADR-0010 / `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md`:

- initial host: **Contabo commodity Linux VPS**;
- edge: Cloudflare DNS/proxy/CDN/TLS/basic WAF; R2 optional for off-VPS backups/HullQ-owned artifacts;
- backend: **CPython 3.14 + FastAPI** when the API slice is reached;
- production persistence: **PostgreSQL**;
- no dedicated search engine initially; PostgreSQL indexes/projections first after accepted query semantics;
- web: **Astro + TypeScript**;
- React + TypeScript only as selective Astro islands for sufficiently stateful UI; no full-site client-only React SPA;
- no Strapi/Next.js/Flutter Web baseline;
- no CMS initially;
- responsive web/PWA first; **Flutter** preferred later for Android/iOS via the same API boundary;
- simple VPS deployment; no Kubernetes/broker/distributed scheduler without measured need.

This architecture choice does **not** resolve or bypass:

- OQ-006 alert cadence/freshness;
- OQ-009 unknown-data query semantics;
- OQ-014 exact authentication/account/privacy architecture;
- OQ-015 stable HTTP API/versioning;
- OQ-017 market-history retention;
- OQ-018 exact public SEO/search surface.

In particular, OQ-014 remains intentionally deferred. Accounts/SavedQuery/Monitor/Alert are architecturally supported, but no JWT/session/auth library/provider/password/OAuth/email-verification implementation is accepted yet.

---

# Stage 2 — Build the research-pipeline benchmark implementation

**Goal:** implement against observed real source conditions, then prove that HullQ can research accurately, reproducibly and cheaply enough to scale.

Stage-2 implementation is decomposed through `docs/slices/INDEX.md`. Slice boundaries after SLICE-0002 are refined from actual source evidence rather than treated as fixed in advance.

## 2.1 Repository code structure — BOOTSTRAPPED

Current single-repo structure includes root Python project config, `src/hullq/`, tests, specs, fixtures, research, docs and architecture. Do not create separate repositories or distributed services without a later accepted decision.

## 2.2 Canonical contract runtime — REVIEW

SLICE-0003 implements one reusable repository-local Draft-2020-12 JSON-Schema registry/validation boundary without network retrieval or new boat semantics.

Implementation branch: `slice/0003-canonical-contract-runtime`; PR #3 is the independent-review/CI path. SLICE-0004 remains blocked until SLICE-0003 is accepted/DONE.

## 2.3 Deterministic measurement normalization

After SLICE-0003 acceptance, implement the smallest evidence-derived slice for source observations and deterministic unit/basis normalization while preserving raw source semantics.

Expected later pure functions/modules include as justified by the source sample:

- unit parsing/conversion;
- raw label/basis preservation;
- ranges and option-sensitive observations;
- explicit invalid/unknown behavior;
- no network/source discovery in pure normalization functions.

## 2.4 Identity text primitives

Normalize/manipulate manufacturer/model/generation text only within accepted identity semantics. Do not introduce fuzzy forced identity resolution or silent generation invention.

## 2.5 Appendage/configuration normalization

Treat keel, board, rudder, skeg, rudder count/state and support/protection relationships as independent dimensions. Real SLICE-0002 evidence proved this requires a dedicated boundary rather than one flat taxonomy mapping.

## 2.6 Provenance/conflict runtime

Implement accepted FieldEvidence / FieldResolution / DerivationRecord behavior and explicit conflict handling.

## 2.7 Derived metrics

Implement `hullq-derived-1.0.0` only after the required canonical/provenance/configuration foundations exist.

## 2.8 Research job state machine

Requirements include:

- explicit states;
- restart/idempotency where feasible;
- evidence/error recording per stage;
- failures never corrupt accepted output;
- explicit review queue;
- immutable raw artifacts.

## 2.9 First real rights-gated source adapter

Preferred initial target: Wikidata CC0. Source clearance must be enforced before acquisition/bulk use; exact current identity/field-completeness metrics must be reproducibly recorded rather than hard-coded from research estimates.

## 2.10 Build benchmark corpus

50–100 deliberately difficult designs across:

- mono/cat/tri;
- simple and ambiguous identities;
- production generations;
- keel/centerboard/lifting/bilge/daggerboard configurations;
- skeg/partial-skeg/spade/keel-hung/twin rudders;
- mixed source availability;
- conflicting specifications.

Use the source landscape and difficult cases discovered in SLICE-0002 to select the corpus. This corpus benchmarks the implemented pipeline; it is not the product universe.

## 2.11 Measure benchmark

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

## 2.12 Harden until Gate G3 passes

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

Before public frontend/search-surface implementation, define canonical page taxonomy, URL grammar, faceted crawl/index policy, rendering strategy, canonicalization/sitemaps, internal linking and structured-data mapping under ADR-0007. Astro is already selected by ADR-0010, but framework selection does not replace this gate.

---

# Stage 4 — Technical Query Engine

1. resolve OQ-009;
2. define versioned machine-readable query contract;
3. implement pure deterministic query engine independent of UI/market adapters/PostgreSQL;
4. build query golden masters including unknown-data behavior;
5. build canonical-data compare engine.

**Exit:** Gate G5.

---

# Stage 5 — Production persistence and application API

The technology target is already accepted by ADR-0010; this stage implements it only after domain/query requirements are sufficiently stable.

## 5.1 Re-evaluate logical-model need

If implementation evidence shows a separate persistence-neutral relationship model is useful, resolve/revive OQ-019 here. Do not create one merely because PostgreSQL was selected.

## 5.2 PostgreSQL persistence

Design and implement physical PostgreSQL persistence behind domain/repository adapters. Persistence must not redefine accepted identity/provenance/query semantics.

Before relying on production data, introduce tested off-VPS backup/restore behavior. Preferred low-cost direction is encrypted/compressed PostgreSQL backups to R2 or another independent target.

## 5.3 API contract and FastAPI boundary

Resolve OQ-015 before exposing a stable public HTTP boundary. Then implement the accepted API using FastAPI/CPython 3.14 and reuse the existing HullQ core.

Do not reimplement canonical business rules in TypeScript/frontend handlers.

---

# Stage 6 — Web product MVP

The frontend technology is already accepted by ADR-0010:

- Astro;
- TypeScript;
- React islands only for sufficiently complex stateful UI;
- static/server-rendered HTML first for public/SEO content.

Before public search implementation:

1. resolve OQ-018;
2. build technical discovery UX;
3. add compare;
4. integrate the first permitted market path from Track M.

Do not recreate the raw-field prototype as the product UX and do not default to a client-only React SPA.

---

# Stage 7 — Accounts, saved technical queries and alerts

1. **resolve OQ-014 in detail before auth code** — session/token architecture, credential/OAuth/provider choice, verification/reset, privacy/security and web/later-Flutter consequences;
2. persist SavedQuery as first-class versioned technical query;
3. add Monitor and Alert as separate domain concepts;
4. resolve OQ-005 before claiming cross-market physical-listing uniqueness;
5. resolve OQ-006 cadence/freshness policy;
6. introduce email/web/native-push delivery only through explicit notification slices.

The accepted PostgreSQL/FastAPI architecture must accommodate these features, but ADR-0010 intentionally did not pre-select the auth implementation.

Subscription entitlements control capacity/frequency/features, not technical query semantics.

---

# Stage 8 — Native mobile when justified

Responsive web/PWA is the initial mobile path. When recurring monitor/alert usage justifies native apps:

1. define the mobile/API/product slice;
2. implement Flutter for Android/iOS;
3. consume the same stable HTTP API;
4. do not duplicate domain/query semantics in Dart.

Native app-store costs/operations should not be incurred before product usage justifies them.

---

# Stage 9 — Public release, distribution and low-maintenance operations

Measure product and business KPIs including technical searches, unknown/insufficient-data rates, compare/monitor usage, market click-through, returning users, monthly profit, human maintenance hours, unplanned maintenance, source-integration burden, research cost per design, and profit per maintenance hour.

HullQ is not currently optimized for venture-scale expectations. Scale VPS/services only if real traction justifies a deliberate new decision.

---

# Deferred commercial/intelligence gates

- OQ-016: subscription pricing and entitlement defaults before paid launch.
- OQ-017: source-specific longitudinal listing/asking-price retention and price-intelligence semantics before durable price-history storage or Pro price-intelligence launch.

---

# Immediate next actions

1. **SLICE-0003 — REVIEW:** complete remote PR CI + independent review + project-owner acceptance; do not merge/mark DONE before all three.
2. If accepted, move SLICE-0003 to DONE and detail only SLICE-0004.
3. Continue evidence-derived Stage-2 slices in bounded order; do not start PostgreSQL/FastAPI/Astro merely because the stack is selected.
4. Continue OQ-013 market-access research in parallel when useful, without distracting from the design-data foundation.
