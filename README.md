# HullQ

**Tagline:** Find boats by what they are.

HullQ is a sailboat design search engine and market finder. Users describe a boat by technical characteristics, HullQ resolves matching designs, and market adapters look for current examples for sale.

## Repository map

- `PROJECT_CONTEXT.md` — concise canonical project overview.
- `docs/EXECUTION_PLAN.md` — canonical step-by-step execution order and phase gates.
- `docs/PROJECT_STATE.md` — current stage, active blocker and next canonical action for humans/agents.
- `docs/DOCS_TO_CODE_METHOD.md` — repository-wide docs-to-code development method.
- `specs/REQUIREMENTS.md` — stable requirement IDs and acceptance baseline.
- `specs/` — data contracts, taxonomies, provenance, validation and quality rules. `specs/IDENTITY_MODEL.v0.1.md` is the accepted identity model; `specs/SCHEMA_STATUS.md` records which JSON schemas are accepted, draft or historical.
- `research/` — independent-data research workflow and queue templates.
- `architecture/` — system boundaries, market-adapter contract and accepted ADRs under `architecture/decisions/`.
- `docs/` — execution plan, governance, engineering standards, product/data strategy, legal working position, roadmap and the external-LLM review pack.
- `docs/DATABASE_COVERAGE_STRATEGY.md` — canonical breadth-vs-depth strategy and sparse/unknown-data semantics.
- `docs/PRODUCT_RETENTION_AND_MONETIZATION.md` — owner-watcher retention thesis and accepted freemium/monitoring direction.
- `specs/PROVENANCE_MODEL.v0.1.md` — accepted OQ-004 field-provenance model with separate evidence, resolution and derivation lineage.
- `docs/governance/REPOSITORY_AUDIT_2026-08-18.md` — latest docs-to-code consistency audit.
- `reference/imported/` — the three uploaded source files, preserved unchanged.
- `pyproject.toml` + `.python-version` — accepted OQ-010 Python toolchain configuration.
- `.github/workflows/ci.yml` — cross-platform quality CI; `.github/dependabot.yml` — dependency/update visibility.
- `docs/engineering/REPOSITORY_BOOTSTRAP.md` — current bootstrap state and the remaining real-lockfile gate.

## Authority order

For implementation work in this repository, use the following precedence:

1. `specs/` — normative implementation-facing contracts and rules.
2. accepted ADRs under `architecture/decisions/`.
3. `architecture/` — component boundaries and interfaces.
4. `research/` — operational research process.
5. governance/engineering standards.
6. project context / strategy / roadmap.
7. `reference/` — historical/source material; never an invisible production-data fallback.

Where a newer file explicitly says **DRAFT** or **PROPOSED**, it is not yet a production rule. `docs/governance/OPEN_QUESTIONS.md` is the canonical open-decision register; `docs/DECISIONS_REQUIRED.md` is retained only as a legacy ID map.

**Current implementation gate:** OQ-010 is accepted. Repository bootstrap is in progress; Stage-2 pipeline code remains blocked until a real `uv.lock` is generated and the locked Linux/Windows CI baseline passes.

## Core chain

```text
technical requirements
→ matching BoatDesigns
→ live/on-request market lookup
→ normalize + deduplicate
→ current boats for sale
→ compare / save / alert
```

## Non-negotiable data rules

- Independent production data; the Sailboatdata scrape is reference/prototype only.
- No production value without provenance.
- Unknown is better than invented.
- Conflicting authoritative evidence is not silently resolved.
- Keel, rudder and skeg are separate dimensions.
- Monohulls, catamarans and trimarans are first-class from day one.
- Derived ratios are computed internally from base parameters with a versioned methodology.
- Aim for broad SailboatData-like identity coverage because unknown-model discovery requires a large universe; prioritize enrichment depth by real-market relevance rather than chasing record count for vanity.
- The 50–100 model set is a research benchmark corpus, not the product/launch database.
- Sparse records are valid; unknown fields are not negative facts.
- Identity is `BoatModel → BoatDesign generation → NamedVariant / orthogonal DesignOptions → ResolvedConfiguration`; independent option axes are not flattened into duplicated Cartesian variants.
- Prefer high-throughput automation with exception-based human review.

## Development method

HullQ is a **single-repository docs-to-code project**. Significant work follows:

```text
open question / evidence
→ decision / ADR
→ normative spec + requirement ID
→ tests / fixtures
→ implementation
→ automated verification
```

See `docs/DOCS_TO_CODE_METHOD.md`, `docs/governance/OPEN_QUESTIONS.md`, `docs/engineering/QUALITY_GATES.md` and `docs/EXECUTION_PLAN.md`.

## Current decision work

- OQ-003 identity model: accepted (`specs/IDENTITY_MODEL.v0.1.md`, ADR-0004).
- OQ-007 source rights/licensing: accepted (`specs/SOURCE_RIGHTS_POLICY.v0.1.md`, `specs/SOURCE_SCHEMA.v0.2.json`, ADR-0005).
- OQ-004 field-level provenance persistence: DECIDED; separate FieldEvidence / FieldResolution / DerivationRecord ledger + RFC 6901 field addressing is accepted.
- OQ-016 subscription pricing/entitlement defaults: deferred until pre-paid-launch validation; freemium architecture is already documented.

## Search/distribution architecture

Search Architecture and SEO are first-class product architecture. See `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` and accepted ADR-0007; OQ-018 gates the exact public search/SEO surface before frontend implementation.

## Development baseline

The accepted Stage-2 Python baseline is CPython 3.14 + uv. See `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md` and ADR-0009. The repository intentionally keeps normative JSON Schema contracts separate from Python implementation models.

Bootstrap with `uv python install 3.14`, `uv lock`, and `uv sync --locked --all-groups`. A committed `uv.lock` is required before Stage-2 code is mergeable.
