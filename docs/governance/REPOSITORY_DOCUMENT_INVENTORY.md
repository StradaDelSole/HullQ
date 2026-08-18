# HullQ — Repository Document Inventory

**Status:** ACTIVE  
**Last verified:** 2026-08-18  
**Purpose:** Human-readable completeness map for the docs-to-code repository. `MANIFEST.json` remains the machine-readable file inventory/hash list.

## Completeness rule

A decision or rule that is required to implement HullQ MUST NOT exist only in chat history. Before code depends on it, it must be represented in the repository as one or more of:

- accepted requirement/specification;
- accepted ADR;
- architecture contract;
- governance rule;
- research/evidence record;
- test/fixture contract;
- explicit open question blocking implementation.

External source documents do not need to be copied into the repo when redistribution is inappropriate; their evidence metadata and canonical locator must be recorded in `research/evidence/SOURCE_REGISTER.md`.

## Current document sets

### Root / orientation — PRESENT
- `README.md`
- `PROJECT_CONTEXT.md`
- `CLAUDE.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `TREE.txt`
- `MANIFEST.json`

### Execution / product / strategy — PRESENT
- `docs/EXECUTION_PLAN.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/DATA_STRATEGY.md`
- `docs/DATABASE_COVERAGE_STRATEGY.md`
- `docs/LEGAL_WORKING_POSITION.md`
- `docs/DOCS_TO_CODE_METHOD.md`

### Governance / traceability — PRESENT
- `docs/governance/DOCUMENT_AUTHORITY.md`
- `docs/governance/OPEN_QUESTIONS.md`
- `docs/governance/OPEN_QUESTION_PROCESS.md`
- `docs/governance/TRACEABILITY.md`
- `docs/governance/REPOSITORY_DOCUMENT_INVENTORY.md`
- `docs/DECISIONS_REQUIRED.md` (historical compatibility ID map only; open-question register is canonical)
- `docs/governance/REPOSITORY_AUDIT_2026-08-18.md`

### Engineering standards / quality — PRESENT
- `docs/engineering/ENGINEERING_STANDARD.md`
- `docs/engineering/QUALITY_GATES.md`
- `docs/engineering/STANDARDS_BASELINE.md`
- `docs/engineering/VERSIONING_AND_CHANGE_CONTROL.md`
- `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md` — accepted OQ-010 Python/data-pipeline baseline.
- `pyproject.toml` — active root Python project/tool configuration.
- `reference/history/tooling/PYPROJECT_OQ010_DRAFT.toml` — archived pre-acceptance proposal.
- `docs/engineering/REPOSITORY_BOOTSTRAP.md` — bootstrap status and exit gate.
- `docs/research/OQ-010_PYTHON_TOOLCHAIN_RESEARCH.md` — OQ-010 decision research.
- `architecture/decisions/ADR-0009-python-research-toolchain.md` — PROPOSED.

### Architecture — PRESENT
- `architecture/SYSTEM_ARCHITECTURE.md`
- `architecture/MARKET_ADAPTER_CONTRACT.md`
- `architecture/decisions/README.md`
- ADR-0001 through ADR-0007 accepted; OQ-004 closed

### Normative specs / contracts — PRESENT
- `specs/REQUIREMENTS.md`
- `specs/TEST_STRATEGY.md`
- `specs/SCHEMA_STATUS.md`
- `specs/IDENTITY_MODEL.v0.1.md`
- `specs/BOAT_MODEL_SCHEMA.v0.1.json`
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json`
- `reference/history/RESOLVED_CONFIGURATION_SCHEMA.v0.1-DRAFT.json` — historical pre-OQ-001 draft.
- `specs/SOURCE_SCHEMA.v0.2.json`
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- `specs/RESEARCH_JOB_SCHEMA.v0.1.json`
- `specs/MARKET_LISTING_SCHEMA.v0.1.json`
- `specs/TAXONOMY.v0.1.md`
- `specs/PROVENANCE_AND_QUALITY.md`
- `specs/PROVENANCE_MODEL.v0.1.md`
- `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json`
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json`
- `specs/DERIVED_METRICS_SPEC.v1.0.md`
- `docs/research/OQ-001_DERIVED_METRICS_RESEARCH.md` — accepted OQ-001 decision research.
- `architecture/decisions/ADR-0008-derived-metric-methodology.md` — ACCEPTED.
- `specs/RATIO_INPUT_BASIS_SCHEMA.v0.1.json` — OQ-001 accepted contract.
- `specs/DERIVED_METRICS_SCHEMA.v1.0.json` — OQ-001 accepted contract.
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json` — OQ-001 accepted migration contract.
- `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json` — OQ-001 accepted migration contract.
- `fixtures/ratios/` — OQ-001 golden/status/schema fixtures.
- `specs/VALIDATION_RULES.v0.2.md`

### Research / data operations — PRESENT
- `research/RESEARCH_WORKFLOW.md`
- `research/RESEARCH_PILOT.md`
- `research/RESEARCH_QUEUE_INPUT_TEMPLATE.csv`
- `research/MARKET_ACCESS_REGISTER.md`
- `research/evidence/SOURCE_REGISTER.md`
- `docs/research/OQ-003_IDENTITY_RESEARCH.md`
- `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`
- `docs/research/OQ-004_FIELD_PROVENANCE_RESEARCH.md`

### Contract fixtures — PRESENT
- `fixtures/identity/README.md`
- `fixtures/identity/oq003_cases.v0.1.json`
- `fixtures/identity/identity_contract_examples.v0.2.json`
- `fixtures/sources/README.md`
- `fixtures/sources/source_rights_cases.v0.1.json`
- `fixtures/provenance/README.md` + positive/negative provenance contract fixtures

### External-review package — PRESENT
- `docs/EXTERNAL_LLM_REVIEW_BRIEF.md`
- `docs/EXTERNAL_LLM_REVIEW_PROMPT.md`
- raw Gemini/Grok/Claude reviews under `reference/external_reviews/`

### Original user-supplied project inputs — PRESENT AND PRESERVED
- `reference/imported/HullQ_PROJECT_CONTEXT.md`
- `reference/imported/HullQ_BOAT_SCHEMA.v0.1.json`
- `reference/imported/HullQ_RESEARCH_QUEUE_TEMPLATE.csv`
- `reference/IMPORT_NOTES.md`

### Templates — PRESENT
- `templates/ADR_TEMPLATE.md`
- `templates/OPEN_QUESTION_TEMPLATE.md`
- `templates/REQUIREMENT_TEMPLATE.md`


### Repository bootstrap / CI — PRESENT, LOCKFILE GATE PENDING
- `pyproject.toml` — accepted OQ-010 toolchain realized at repository root.
- `.python-version` — Python 3.14 family selector.
- `.github/workflows/ci.yml` — Linux + Windows locked quality pipeline.
- `.github/dependabot.yml` — uv + GitHub Actions update baseline.
- `.github/pull_request_template.md` — docs-to-code/verification review checklist.
- `scripts/validate_repository.py` — first-party governance/contract validator.
- `src/hullq/` — initial single-package source layout.
- `tests/unit/`, `tests/contract/`, `tests/integration/` — initial test topology.
- `docs/engineering/REPOSITORY_BOOTSTRAP.md`
- `docs/engineering/CI_BASELINE.md`
- `docs/engineering/GITHUB_REPOSITORY_SETTINGS.md`
- `uv.lock` — REQUIRED BUT PENDING; must be generated in a networked Python 3.14 environment and committed before Stage-2 code is mergeable.

## Intentionally not yet present

The following are **not missing files**; they are future artifacts gated by unresolved project decisions or later execution stages:

- production database migrations/models — after relevant schemas are accepted;
- search-engine implementation/API contracts — after data-foundation blockers;
- alert implementation contracts — later execution stage.

These items MUST be created before their corresponding code is considered implementation-ready.

## Verification conclusion — 2026-08-18

All project-authored documents and user-supplied project inputs currently required to reproduce the **present planning/decision state** are present in the repository.

The external LLM reviews are now preserved as raw reference material. External manufacturer/standards webpages and PDFs are represented by source metadata/locators rather than copied wholesale into the repo; this is intentional and avoids treating third-party copyrighted material as vendored project content.

## OQ-007 decision package

Present and ACCEPTED:

- `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`
- `docs/research/OQ-004_FIELD_PROVENANCE_RESEARCH.md`
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- `specs/SOURCE_SCHEMA.v0.2.json`
- `architecture/decisions/ADR-0005-source-rights-clearance.md`
- `fixtures/sources/source_rights_cases.v0.1.json`
- `fixtures/provenance/README.md` + positive/negative provenance contract fixtures

These OQ-007 artifacts are now accepted; see ADR-0005 and Project State.

- `docs/PRODUCT_RETENTION_AND_MONETIZATION.md` — active retention/freemium product strategy; exact pricing/limits remain OQ-016.

## Latest audit additions

- `docs/governance/REPOSITORY_AUDIT_2026-08-18.md` — completed consistency audit.
- `docs/research/OQ-004_FIELD_PROVENANCE_RESEARCH.md` — OQ-004 decision research.
- `specs/PROVENANCE_MODEL.v0.1.md` — accepted normative provenance model.
- `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json` — accepted evidence contract.
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json` — accepted field-decision contract.
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json` — accepted derived-lineage contract.
- `fixtures/provenance/` — positive/negative contract fixtures.

Historical superseded schemas/drafts are stored under `reference/history/`, not active `specs/`.

## Accepted delta — 2026-08-18

- OQ-004 is closed; accepted provenance artifacts are `specs/PROVENANCE_MODEL.v0.1.md`, `FIELD_EVIDENCE_SCHEMA.v0.1.json`, `FIELD_RESOLUTION_SCHEMA.v0.1.json`, `DERIVATION_RECORD_SCHEMA.v0.1.json`, ADR-0006 and provenance fixtures.
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json` is accepted; its prior draft is retained under `reference/history/`.
- ADR-0007 and `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` establish Search Architecture + SEO as first-class product architecture.
- OQ-018 records the still-open implementation details for the public indexable/search surface.

## Explicitly pending bootstrap artifact

- `uv.lock` — required by accepted OQ-010 but not hand-authored in this snapshot; must be generated by uv 0.12.5+ in a networked environment and committed before Stage-2 code is mergeable.
