# HullQ — Document Authority and Consistency Rules

**Status:** ACCEPTED

## Authority order

1. **Normative specifications** — `specs/`
2. **Accepted architecture decisions** — `architecture/decisions/`
3. **Architecture contracts and boundaries** — `architecture/`
4. **Operational research/process protocols** — `research/`
5. **Governance and engineering standards** — `docs/governance/`, `docs/engineering/`
6. **Project context / strategy / roadmap** — `PROJECT_CONTEXT.md`, `docs/`
7. **Historical/reference material** — `reference/`

## Consistency rule

The repository SHOULD NOT contain a knowingly inconsistent accepted state.

If an accepted ADR changes a normative behavior, the same change MUST update the affected specification. Therefore the normal authority order remains stable instead of relying on document timestamps.

## Status labels

Documents that are not yet authoritative MUST clearly use one of:

- `DRAFT`
- `PROPOSED`
- `BLOCKED`
- `HISTORICAL`

Accepted normative documents should use `ACCEPTED`, `ACTIVE`, or an explicit stable version.

## Versioned contracts

Schemas, taxonomies, formula methodologies and external API contracts MUST be versioned when consumers or persisted data can depend on them.

Published versions MUST NOT be silently rewritten. Corrections that change semantics require a new version.

## Conflict handling

If two documents appear to conflict:

1. stop implementation of the disputed behavior;
2. identify the controlling requirement/specification;
3. open or update an `OQ-*` item if the rule is genuinely unresolved;
4. create an ADR if the resolution is architecturally significant;
5. update all affected documents in one logical change;
6. add tests that prevent regression to the conflicting behavior.

## Evidence and external-review material

- `research/evidence/SOURCE_REGISTER.md` records evidence metadata and canonical locators. It is evidentiary, not itself a production-data license or normative implementation rule.
- `reference/external_reviews/` contains preserved third-party/LLM opinions. These are **NON-NORMATIVE** and cannot override accepted requirements, specs or ADRs.
- `reference/imported/` remains historical source/reference material and is not an invisible fallback for production values.
- A project decision discovered in chat or an external review becomes implementation-authoritative only after promotion through the docs-to-code decision process.

