# HullQ — Standards Baseline

**Status:** ACTIVE  
**Last reviewed:** 2026-08-18

This file records the external standards/conventions HullQ deliberately follows. Re-check versions when a major implementation phase begins.

## Normative specification language

- IETF BCP 14: RFC 2119 + RFC 8174.
- Only uppercase `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, etc. carry normative meaning in HullQ specs.

## JSON data contracts

- JSON Schema Draft 2020-12 is the current HullQ contract dialect.
- Schemas MUST declare `$schema` and SHOULD use stable `$id` values.
- Schema examples/fixtures are validated automatically once CI exists.

## Provenance field addressing — accepted under OQ-004

- RFC 6901 JSON Pointer is the accepted standard syntax for field-level provenance addressing.
- W3C PROV-DM informs the conceptual separation of entities, activities and agents; HullQ does not adopt RDF/PROV-O persistence.
- The normative HullQ contracts are `specs/PROVENANCE_MODEL.v0.1.md`, FieldEvidence, FieldResolution and DerivationRecord under ADR-0006.

## Search / SEO architecture

- Search Architecture and SEO are first-class product architecture under ADR-0007.
- Google Search Central primary guidance on URL structure/faceted navigation, JavaScript SEO, canonicalization, sitemaps and structured data is registered as a current implementation-reference baseline.
- Core Web Vitals are a public-frontend performance baseline.
- Exact public URL/indexation/rendering mechanics are re-verified and accepted under OQ-018 before frontend implementation.

## Versioning

- Semantic Versioning 2.0.0 for stable released public contracts/components.
- Explicit `0.x` versions for unstable/pre-1.0 contracts.
- Released/persisted contract semantics are not silently rewritten.

## Commit history

- Conventional Commits 1.0.0 is the repository convention during active coding.
- Commit messages describe user/domain impact (`feat`, `fix`, `spec`, `test`, `chore`, etc.) rather than vague activity.

## Architecture decisions

- Lightweight ADR practice: one significant decision per record with context, decision and consequences.
- Accepted decisions are superseded by new ADRs instead of rewritten historically.

## Python project configuration

When Python implementation begins:

- `pyproject.toml` is the standardized configuration/packaging anchor per PyPA guidance;
- dependency/environment tooling is selected explicitly in `OQ-010`;
- avoid parallel overlapping formatter/linter stacks without a reason.

## HTTP APIs

When a stable HTTP boundary is introduced:

- define it contract-first using the then-current official OpenAPI specification;
- select exact OpenAPI version by ADR/spec at that time rather than freezing a version prematurely.

## Repository protection / CI

When hosted on GitHub or equivalent:

- protect the default branch;
- require relevant automated status checks before merge;
- keep required check names unambiguous;
- use PR/change review even for AI-generated work where practical.

## Review cadence

Re-check this baseline at least:

- before first production pipeline code;
- before first public HTTP API;
- before first public web release;
- when a selected tool reaches end-of-life or a major standard version changes.
