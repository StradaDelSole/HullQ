# HullQ — Instructions for Coding / Research Agents

Before changing the project, read in this order:

1. `README.md`
2. `PROJECT_CONTEXT.md`
3. `docs/PROJECT_STATE.md`
4. `docs/DOCS_TO_CODE_METHOD.md`
5. `specs/REQUIREMENTS.md`
6. `docs/governance/OPEN_QUESTIONS.md`
7. `docs/slices/INDEX.md`
8. the explicitly assigned slice under `docs/slices/`
9. relevant versioned specs / accepted ADRs / operational docs named by that slice

## Authority

1. normative `specs/`
2. accepted ADRs in `architecture/decisions/`
3. architecture contracts in `architecture/`
4. operational `research/` protocols
5. governance/engineering standards
6. `PROJECT_CONTEXT.md` / strategy docs
7. `reference/`

Slices are operational work contracts. They never override the authority order above.

Do not turn a **DRAFT**, **PROPOSED** or **BLOCKED** item into a production rule without an explicit project decision.

## Slice execution

HullQ uses bounded implementation/research slices defined under `docs/slices/`.

- Work only on the slice explicitly assigned by the user/operator.
- Do not automatically start the next slice after completion.
- Do not broaden scope because adjacent work appears convenient.
- A `DESIGN_RESEARCH` slice may produce research/spec/architecture artifacts but MUST NOT introduce domain implementation unless explicitly authorized.
- An `IMPLEMENTATION` slice may implement only already accepted semantics identified by its controlling artifacts.
- If the assigned slice depends on an unresolved OQ, stop and report it.
- If repository truth conflicts with the slice, repository truth wins and the slice must be corrected.
- Move an assigned slice to `IN_PROGRESS`, `BLOCKED`, or `REVIEW` only when justified by the actual state and evidence.
- Do not automatically begin another slice after reaching `REVIEW` or `BLOCKED`.

The canonical operational queue is `docs/slices/INDEX.md`.

## Slice status authority and completion reports

The implementation/research agent does **not** own final acceptance.

An agent MAY move its assigned slice among:

```text
READY → IN_PROGRESS → REVIEW
                 ↘ BLOCKED
```

An agent MUST NOT mark a slice `DONE`.

`DONE` is a project acceptance state. It may be set only after all of the following are true:

1. every required acceptance criterion has actually been verified;
2. required remote/external checks have actually been observed and passed, or are explicitly not applicable;
3. independent review is complete;
4. the user/project owner accepts the slice.

Never mark an acceptance checkbox as passed when its evidence was not actually observed. In particular, a locally green implementation is not evidence that remote GitHub CI passed. If an external check cannot be observed, record it as `NOT VERIFIED` and recommend `REVIEW`, not `DONE`.

At the end of every assigned slice, use the exact completion-report structure defined in `docs/slices/SLICE_TEMPLATE.md`. The report MUST distinguish local validation from remote/external verification and MUST include unresolved findings, scope deviations, and an explicit agent declaration.

Default successful agent handoff state is `REVIEW`. Default unsuccessful/incomplete handoff state is `BLOCKED`.

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

## Pre-code source-evidence rule

Before meaningful HullQ research-pipeline/domain implementation begins, execute the assigned design-data source-research slice and study **real sailboat data from independently usable sources**.

Do not build extraction or normalization behavior only from imagined source formats. The source-research slice must establish actual source availability, rights/clearance, field coverage, generation/option representation, conflicts, missing-data patterns and likely human-review needs using a representative real-boat evidence sample.

SailboatData may remain a reference/prototype aid under the accepted source-rights policy, but must not become an invisible production-value source.

The initial application/deployment stack is now accepted by ADR-0010, but this does not authorize premature persistence/API/frontend/deployment work outside an assigned slice.

## Accepted application architecture guardrail

Before any application/backend/persistence/frontend/deployment work, read:

- `architecture/decisions/ADR-0010-vps-first-application-stack.md`;
- `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md`;
- `architecture/SYSTEM_ARCHITECTURE.md`.

Accepted baseline:

- initial hosting provider: **Contabo VPS**, while targeting a portable commodity Linux VPS;
- public edge: Cloudflare DNS/proxy/CDN/TLS/basic WAF; R2 optional for backups/HullQ-owned artifacts;
- backend/application runtime: CPython 3.14 + **FastAPI** when OQ-015/API work is reached;
- production relational persistence: **PostgreSQL**;
- no dedicated search engine initially; add one only from measured need;
- web: **Astro + TypeScript**;
- React + TypeScript only as selective Astro islands where interaction/state complexity justifies it; do not turn HullQ into a client-only React SPA;
- Strapi, Next.js, Flutter Web, D1 as canonical production DB, and a second TypeScript business-logic backend are not the accepted baseline;
- responsive web/PWA first; **Flutter** is the preferred later Android/iOS client consuming the same accepted API boundary;
- simple VPS deployment is preferred; do not introduce Kubernetes, broker/distributed scheduler or paid managed-service dependencies without an accepted slice/decision.

Critical deferred boundaries:

- **OQ-014 remains unresolved**: do not choose JWT vs server sessions, auth library/provider, password/OAuth flow, email verification/reset or privacy/security mechanics before the dedicated account/auth decision;
- OQ-006 still controls alert cadence/freshness;
- OQ-015 still controls the stable public HTTP/API/versioning boundary;
- OQ-018 still controls exact public SEO URL/index/rendering/canonical/structured-data behavior.

SavedQuery, Monitor and Alert remain separate concepts. The application architecture must support them, but agents MUST NOT implement accounts/alerts merely because PostgreSQL/FastAPI are selected.

## Research behavior

Prefer primary/authoritative sources for deep verification in the order documented in `research/RESEARCH_WORKFLOW.md`. Appropriately licensed/open structured data may bootstrap identity/common facts when provenance is explicit. Use `null`, `unknown`, `needs_review` or `conflict` when evidence is insufficient. Read `docs/DATABASE_COVERAGE_STRATEGY.md` before changing ingestion or search semantics.

Research source accessibility, rights and HullQ clearance separately. A technically accessible page or API is not automatically cleared for bulk ingestion, persistence or redistribution.

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
- Do not make frontend assumptions from the existing Tabulator prototype; use the accepted Astro/TypeScript baseline only when a frontend slice authorizes frontend work.

## Open decisions

Consult canonical `docs/governance/OPEN_QUESTIONS.md` (`docs/DECISIONS_REQUIRED.md` is only a historical legacy-ID compatibility map). If a task depends on an unresolved question, work on or surface that decision rather than silently deciding it.
