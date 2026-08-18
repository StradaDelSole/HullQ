# HullQ — Instructions for Coding / Research Agents

Before changing the project, read in this order:

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `docs/PROJECT_STATE.md`
4. `docs/DOCS_TO_CODE_METHOD.md`
5. `specs/REQUIREMENTS.md`
6. `docs/governance/OPEN_QUESTIONS.md`
7. relevant versioned specs / accepted ADRs / operational docs

## Authority

1. normative `specs/`
2. accepted ADRs in `architecture/decisions/`
3. architecture contracts in `architecture/`
4. operational `research/` protocols
5. governance/engineering standards
6. `PROJECT_CONTEXT.md` / strategy docs
7. `reference/`

Do not turn a **DRAFT**, **PROPOSED** or **BLOCKED** item into a production rule without an explicit project decision.

## Product guardrail

HullQ exists to strengthen:

```text
FIND DESIGN → FIND BOAT FOR SALE → COMPARE / SAVE → ALERT
```

Do not broaden it into a generic boating super-app.

## Data rules

- Never invent missing boat data.
- No production value without provenance.
- Preserve input identity separately from verified identity.
- Preserve raw source values when normalization occurs.
- Do not silently resolve conflicting authoritative sources.
- Keel, rudder and skeg are independent dimensions.
- Monohulls, catamarans and trimarans are first-class.
- Canonical physical storage uses SI where practical.
- Derived ratios require an approved versioned formula spec.
- The imported Sailboatdata scrape/context is never an invisible production-data fallback.
- Build for broad design-universe coverage from the outset; the 50–100 research set is only a benchmark corpus.
- Breadth and verification depth are independent. Partial/sparse production records are valid when provenance is retained and missing fields remain explicit.
- Missing/unknown data is never evidence that a characteristic is absent.
- Appropriately licensed/open sources may bootstrap common fields; do not re-research every ordinary fact from zero without reason.
- Optimize research for high-throughput automation and exception-based human review.

## Research behavior

Prefer primary/authoritative sources for deep verification in the order documented in `research/RESEARCH_WORKFLOW.md`. Appropriately licensed/open structured data may bootstrap identity/common facts when provenance is explicit. Use `null`, `unknown`, `needs_review` or `conflict` when evidence is insufficient. Read `docs/DATABASE_COVERAGE_STRATEGY.md` before changing ingestion or search semantics.

## Search / SEO architecture

Search Architecture and SEO are first-class product architecture (ADR-0007). Before changing public routing, filter URLs, canonical/indexable page types, rendering or metadata, read `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` and check OQ-018. Do not turn arbitrary faceted filter combinations into an uncontrolled indexable URL space. Do not make SEO semantics an implicit frontend implementation detail.

## Market integrations

Keep each marketplace in its own adapter. Before implementation, verify permitted API/feed/partner/access method and current terms. Return only the canonical market-listing contract to the rest of HullQ. Historical price/listing retention is not implied by live access; OQ-017 and source rights govern price-history persistence.

## Docs-to-code behavior

- Do not implement behavior that lacks an accepted requirement/specification when one is needed.
- Do not silently resolve an `OQ-*` blocker.
- Significant architectural decisions require an ADR.
- Behavioral requirements must be traceable to tests.
- Update spec + tests + code atomically when semantics change.
- Keep all first-party HullQ assets in this single repository.

## Engineering behavior

- Prefer small, testable changes.
- Add validation tests when adding or changing a rule.
- Keep raw imports immutable.
- Do not couple UI filters to raw source field names.
- Do not encode multiple technical concepts into a single legacy field.
- Do not make frontend-framework assumptions from the existing Tabulator prototype.

## Open decisions

Consult canonical `docs/governance/OPEN_QUESTIONS.md` (`docs/DECISIONS_REQUIRED.md` is only a historical legacy-ID compatibility map). If a task depends on an unresolved question, work on or surface that decision rather than silently deciding it.
