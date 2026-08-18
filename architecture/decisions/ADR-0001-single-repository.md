# ADR-0001 — Use a Single Repository

**Status:** ACCEPTED  
**Date:** 2026-08-18

## Context

HullQ will contain project specifications, research/data tooling, application code, market adapters, tests and deployment/infrastructure configuration. The project is developed primarily as a lean product with AI-assisted coding and a strong docs-to-code workflow.

Splitting components across repositories would increase coordination, version drift and context overhead without a current independent-team or release-boundary need.

## Decision

HullQ MUST use one repository for all first-party project assets:

- normative specs and schemas;
- documentation and ADRs;
- research/data pipeline code;
- backend/application code;
- frontend code;
- market adapters;
- migrations;
- tests and fixtures;
- infrastructure-as-code and CI configuration.

This is a repository boundary, not a requirement to deploy everything as one process.

## Consequences

### Positive

- atomic spec + code + migration changes;
- one source of truth for coding agents;
- simpler traceability and CI;
- lower operational overhead;
- easier cross-component refactoring.

### Negative

- repository tooling must handle multiple components cleanly;
- CI should become path-aware as the project grows;
- ownership boundaries must be expressed by directories/contracts rather than repositories.

## Revisit when

Only reconsider if independent teams, security isolation, release cadence or repository scale creates measurable problems that a split demonstrably solves.
