# HullQ — Test Strategy

**Status:** ACCEPTED baseline

## Principle

Tests verify normative HullQ behavior; they do not invent it.

## Test ID format

Use requirement-linked identifiers:

```text
TEST-REQ-DATA-004-A
TEST-REQ-SEARCH-003-B
```

## Required categories

### Contract tests

Every JSON Schema MUST have:

- valid positive fixtures;
- invalid negative fixtures for important constraints;
- automated schema validation in CI.

### Domain unit tests

Required for:

- unit normalization;
- taxonomy mapping;
- identity resolution rules;
- formula calculations;
- completeness/quality state derivation;
- search predicate semantics;
- listing deduplication rules when defined.

### Boundary tests

Required where numerical thresholds or nullable/unknown states affect behavior.

### Golden-master corpus

Maintain a small, curated set of representative designs and searches whose expected normalized outputs/results are reviewed and version-controlled.

The 50–100 research benchmark corpus is broader than the golden-master set; not every benchmark record needs to become a permanent unit-test fixture.

### Property/invariant tests

Use where useful for rules such as:

- normalized values remain within physical domains;
- conversion round trips stay within tolerance;
- unknown never becomes false solely because data is absent;
- deterministic inputs produce deterministic normalized output.

### Integration tests

Persistence and adapter boundaries require integration tests. Network sources should be represented by recorded/controlled fixtures in normal CI; live probes belong to operations/source health.

### Regression tests

Every corrected domain/data bug SHOULD gain a regression test linked to the relevant requirement/validation rule.

## Determinism

Normal CI MUST NOT depend on mutable live marketplace pages or live research sources. Live checks are operational probes, not unit-test dependencies.
