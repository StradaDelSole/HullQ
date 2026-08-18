
## 2026-08-18 — OQ-010 accepted + repository bootstrap

- formally closed OQ-010 and accepted ADR-0009 / Python Toolchain Baseline v0.1;
- created root `pyproject.toml`, `.python-version`, single-package `src/hullq/` skeleton and unit/contract/integration test topology;
- created Linux + Windows GitHub Actions quality CI with immutable action SHAs, locked-environment checks, finite job timeouts and dependency audit;
- added Dependabot configuration for uv dependencies and GitHub Actions plus a docs-to-code pull-request template;
- added first-party repository/schema/governance validation and executable contract-regression tests;
- added REQ-GOV-005..007 for reproducibility, automated quality gates and supply-chain visibility;
- intentionally left `uv.lock` absent because the artifact sandbox cannot resolve the accepted uv/Python environment; a real generated and committed lockfile remains the sole external Stage-0.3 bootstrap gate before Stage-2 implementation.


## 2026-08-18 — OQ-010 accepted and repository bootstrap started

- Accepted ADR-0009 and Python Toolchain Baseline v0.1.
- Added root `pyproject.toml`, `.python-version`, editor/Git hygiene files and `src/hullq` package skeleton.
- Added Linux/Windows GitHub Actions quality pipeline with immutable action SHAs.
- Added Dependabot support for uv and GitHub Actions ecosystems.
- Added executable repository/contract regression tests.
- Added REQ-GOV-005..007 for reproducibility, CI quality gates and supply-chain auditing.
- `uv.lock` generation remains an explicit bootstrap gate because the artifact-generation runtime has no package-index network access.

## 2026-08-18 — OQ-010 toolchain decision package

- Completed current-primary-source review of the Stage-2 Python research/data-pipeline toolchain.
- Proposed CPython 3.14 + uv/uv_build + Ruff + mypy strict + pytest/coverage/Hypothesis + jsonschema + HTTPX + asyncio TaskGroup + non-production SQLite.
- Chose mypy as the proposed blocking CI type checker to avoid introducing a Node toolchain solely for Pyright; Pylance/Pyright remains suitable editor assistance and `ty` is explicitly deferred for later re-evaluation.
- Added a non-active draft `pyproject.toml`; root toolchain/lock/CI/code remain blocked until explicit OQ-010 acceptance.
- Migrated the active OQ-003 identity regression fixture to BoatDesign v0.4 / ResolvedConfiguration v0.2.
- Full regression validation remained green at the OQ-010 decision point.

## 2026-08-18 — OQ-001 accepted

- Formally closed OQ-001 and accepted ADR-0008.
- Accepted derived-metric methodology `hullq-derived-1.0.0`.
- Promoted `DERIVED_METRICS_SPEC.v1.0.md`, ratio-input basis schema and derived-metrics schema.
- Promoted BoatDesign v0.4 and ResolvedConfiguration v0.2; archived BoatDesign v0.3 as historical accepted.
- Unblocked derived-metric semantics while keeping implementation gated by OQ-010/repository bootstrap.

# Changelog

## 2026-08-18 — OQ-001 derived-metric decision package

- Researched official/primary formula references for D/L, SA/D, Ballast/Displacement, Brewer Comfort Ratio, CSF and legacy Hull Speed.
- Identified displacement load-state and sail-area basis as required calculation semantics rather than optional metadata.
- Added proposed `hullq-derived-1.0.0` methodology, ADR-0008 and explicit result-status semantics.
- Added draft RatioInputBasis and DerivedMetrics schemas.
- Added BoatDesign v0.4 and ResolvedConfiguration v0.2 migration drafts; renamed draft `derived_ratios` projection to `derived_metrics`.
- Added numeric golden fixtures, external compatibility check and status fixtures.
- Added REQ-RATIO-003..008 and VAL-RATIO-001..007.
- Moved OQ-001 to READY_FOR_DECISION; implementation remains blocked pending explicit acceptance.

## 2026-08-18 — OQ-004 accepted + Search/SEO architecture principle

- Accepted ADR-0006 and closed OQ-004 as DECIDED.
- Promoted `PROVENANCE_MODEL.v0.1`, FieldEvidence v0.1, FieldResolution v0.1 and DerivationRecord v0.1 to accepted contracts.
- Promoted BoatDesign schema v0.3 after reconciliation with the separate provenance ledger.
- Added REQ-PROV-001..008 and updated provenance fixtures to stable contract version 0.1.
- Accepted ADR-0007: Search Architecture and SEO are first-class product architecture, not a post-launch marketing retrofit.
- Added `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, REQ-SEO-001..007 and OQ-018 for detailed public URL/indexation/faceted-navigation/rendering policy before frontend implementation.
- Added SEO/search guidance authorities to the evidence register and strengthened public-release quality gates.
- Next canonical decision is OQ-001 derived-ratio methodology.


## 2026-08-18 — repository audit + OQ-004 provenance decision package

- Completed a pre-implementation repository consistency audit.
- Retired `docs/DECISIONS_REQUIRED.md` as a canonical register and fixed the D-009/OQ-009 collision; `OPEN_QUESTIONS.md` is the sole active decision register.
- Moved superseded drafts out of active `specs/` into `reference/history/`.
- Restored accepted identity requirements REQ-ID-004..008 and REQ-SEARCH-006 that were referenced by the changelog but missing from the requirements baseline.
- Upgraded the requirements baseline so every normative requirement has an explicit acceptance condition.
- Updated system architecture to remove premature Strapi/cache commitments and align Search/SavedQuery/Monitor/Alert/SubscriptionEntitlement concepts.
- Added OQ-017 for historical market observations / price intelligence and asking-price-vs-sale-price semantics.
- Added OQ-004 research, proposed provenance model and ADR-0006.
- Proposed separate immutable `FieldEvidence`, versioned `FieldResolution`, and `DerivationRecord` contracts using RFC 6901 JSON Pointer field addressing.
- Added positive and negative provenance contract fixtures and reconciled BoatDesign v0.3 draft so provenance is not redundantly embedded as canonical `source_ids`.

## 2026-08-18 — OQ-007 accepted + persistent market-watch/freemium direction

- Accepted ADR-0005 and closed OQ-007 as DECIDED.
- Promoted `specs/SOURCE_RIGHTS_POLICY.v0.1.md` and `specs/SOURCE_SCHEMA.v0.2.json` to accepted contracts.
- Unblocked REQ-RESEARCH-005..009 and moved the next canonical decision to OQ-004 provenance persistence.
- Added `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`.
- Added the owner-watcher / opportunity-hunter retention hypothesis: purchase frequency is not treated as a direct proxy for HullQ retention.
- Accepted the freemium product direction: core search remains open; persistence/monitoring is the primary subscription lever.
- Recorded the initial packaging hypothesis: Free = search everything/save 5/monitor 2; Plus = monitor 10 across supported markets; Pro = advanced monitoring/faster alerts/price tracking/larger limits.
- Added OQ-016 for final pricing and entitlement defaults before paid launch.
- Added requirements separating Search, SavedQuery, Monitor, Alert and SubscriptionEntitlement and requiring configurable entitlements.
- Updated roadmap, project context, project state and external-review materials accordingly.

## 2026-08-18 — OQ-003 accepted: canonical identity model

- Accepted ADR-0004 and closed OQ-003 as DECIDED.
- Promoted `specs/IDENTITY_MODEL.v0.1.md` to the normative identity specification.
- Established `BoatModel → BoatDesign generation → NamedVariant / orthogonal DesignOptions → derived ResolvedConfiguration`.
- Added `specs/BOAT_MODEL_SCHEMA.v0.1.json` as the accepted BoatModel identity envelope.
- Added identity-aware `specs/BOAT_DESIGN_SCHEMA.v0.3-DRAFT.json`; final provenance persistence remains blocked by OQ-004.
- Added `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.1-DRAFT.json` so option-sensitive technical values/ratios are modeled as a deterministic derived projection rather than assumed to equal the BoatDesign baseline.
- Added `specs/SCHEMA_STATUS.md` to prevent draft/historical schemas from being mistaken for released contracts.
- Unblocked REQ-ID-003 and added explicit identity requirements REQ-ID-004..008 plus REQ-SEARCH-006.
- Updated research workflow, execution plan, traceability and project state; OQ-007 is now the next canonical decision.

## 2026-08-18 — OQ-003 identity decision draft

- Researched real manufacturer cases for sequential design generations, concurrent keel/rig choices and named versions.
- Added `docs/research/OQ-003_IDENTITY_RESEARCH.md`.
- Added proposed normative `reference/history/IDENTITY_MODEL.v0.1-DRAFT.md`.
- Added proposed ADR-0004 for `BoatModel → BoatDesign generation → NamedVariant / DesignOption → ResolvedConfiguration`.
- Added identity decision fixtures under `fixtures/identity/oq003_cases.v0.1.json`.
- Moved OQ-003 to `READY_FOR_DECISION`; broad ingestion remains blocked until acceptance and schema migration.

## 2026-08-18 — Docs-to-code execution framework

- Established single-repository docs-to-code method and document authority rules.
- Added canonical requirements baseline and test strategy.
- Added managed open-question register/process and requirements traceability rules.
- Added engineering standards, quality gates, standards baseline and version/change-control policy.
- Added ADR framework plus accepted ADRs for single repository, docs-to-code and broad-coverage/progressive-depth strategy.
- Added canonical step-by-step execution plan with Stage/Gate sequencing and parallel market-access track.
- Updated agent instructions and repository index accordingly.


## 2026-08-18 — Integration pack

- Preserved the three uploaded HullQ source files unchanged under `reference/imported/`.
- Split the large project context into product, data, legal, roadmap and architecture files.
- Promoted the uploaded BoatDesign type sketch to archived v0.1 reference.
- Added a formal draft JSON Schema for BoatDesign v0.2 with field-addressable evidence and conflict records.
- Added draft Source, ResearchJob and canonical MarketListing schemas.
- Centralized the starting taxonomy and validation rules.
- Separated minimal research-target input from workflow metadata.
- Added research workflow and pilot plan.
- Added system architecture and market-adapter contract.
- Added `CLAUDE.md` implementation/research guardrails.
- Added an explicit unresolved-decisions register; no ratio formula was silently chosen.
- Updated the external-LLM review brief and prompt to evaluate HullQ primarily as a low-maintenance niche-income product; venture-scale growth is optional upside rather than a success requirement.
- Reframed the 50–100 design research set as a benchmark corpus only; it is no longer presented as the HullQ launch/MVP database.
- Added `docs/DATABASE_COVERAGE_STRATEGY.md`: broad SailboatData-like identity coverage from the outset, progressive verification depth, sparse-data semantics, open-data bootstrap rules and exception-based human review.
- Updated roadmap/research/agent/review documents to target thousands of canonical identities after the benchmark rather than scaling through 500 → 2,000 as a product sequence.
- Added the rule that unknown/missing technical fields are insufficient evidence, never negative facts, to avoid false negatives in characteristic-first search.

## 2026-08-18 — OQ-007 source-rights decision package

- corrected OQ-003/ADR-0004 repository status to reflect the user's explicit acceptance;
- completed source-rights/licensing research for OQ-007;
- added structured Source schema v0.2 draft;
- added source-rights policy draft and proposed ADR-0005;
- added seven source-rights contract fixtures;
- added access-vs-reuse, fail-closed, share-alike quarantine and cumulative-extraction requirements;
- registered legal/licensing/open-data authorities in the evidence register.
