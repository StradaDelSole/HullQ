# HullQ — Engineering Standard

**Status:** ACCEPTED baseline; stack-specific details require ADRs.

## 1. Repository model

HullQ uses one repository for all project code and documentation. Multiple deployable components MAY exist later, but they remain in the same repository unless explicitly superseded by ADR.

## 2. Default engineering posture

- Prefer simple architecture with explicit module boundaries over premature distributed systems.
- Prefer deterministic, reproducible batch/data workflows.
- Prefer typed contracts at boundaries.
- Prefer immutable raw inputs and explicit derived outputs.
- Prefer migrations over destructive in-place schema changes.
- Prefer automation over recurring manual process, especially for research and source health.
- Optimize for low maintenance as a first-class business constraint.

## 3. Standards baseline

- JSON contracts: JSON Schema Draft 2020-12.
- Normative keywords: BCP 14 (RFC 2119 + RFC 8174).
- Versioning: Semantic Versioning 2.0.0 for stable released public contracts; pre-1.0 versions may change rapidly but MUST still be explicit.
- Commit messages: Conventional Commits 1.0.0 once the Git repository enters active coding, unless superseded by ADR.
- HTTP APIs: define machine-readable OpenAPI contracts before/with implementation once an HTTP API becomes a stable boundary; exact OpenAPI version is selected at that time from the current official specification.
- Python projects: use `pyproject.toml` as the configuration/packaging anchor; exact environment/dependency tool requires `OQ-010`/ADR.

## 4. Code quality

Stack-specific quality gates MUST be automated in CI. For Python, the intended modern baseline is:

- formatter + linter (Ruff is the default candidate, subject to toolchain ADR);
- static typing at meaningful boundaries;
- pytest for domain/data tests;
- dependency lock/reproducibility mechanism selected by ADR;
- no network-dependent unit tests;
- explicit integration-test marker/suite for network/source interactions.

Equivalent strict tooling must be selected for frontend/backend languages.

## 5. Testing pyramid for HullQ

### Unit/domain tests

Fast and deterministic. Cover formulas, normalization, taxonomy mapping, identity rules, search semantics and dedup heuristics.

### Contract/schema tests

Validate examples/fixtures against JSON Schema and later API contracts.

### Golden-master tests

Use curated known boat records/search cases to prevent accidental semantic drift in research normalization and query behavior.

### Boundary/property tests

Use for numerical formulas, units, null/unknown semantics and physical plausibility rules.

### Integration tests

Exercise persistence and adapters using controlled fixtures or sandbox/test endpoints where available.

### Live source probes

Operational health checks are separate from deterministic CI and MUST NOT be required for every code change.

## 6. Data migrations

Any persisted schema change MUST include:

- compatibility impact;
- migration strategy;
- rollback/recovery strategy where realistic;
- fixture/schema validation updates;
- version bump when contract semantics changed.

## 7. Observability

Every recurring automated pipeline/adaptor MUST eventually expose at minimum:

- last successful run;
- duration/latency;
- processed/result count;
- error category;
- schema/parser failure signal;
- human-review queue size where applicable.

Observability should be exception-oriented; the owner should not need to watch dashboards daily.

## 8. Security and privacy

Security requirements are specified before user accounts or public write APIs are implemented. Secrets MUST never be committed. External data/source credentials MUST be isolated from test fixtures and logs.

## 9. Dependency discipline

Add dependencies only for clear value. Avoid framework duplication and overlapping tools. Pin/lock dependencies using the selected ecosystem mechanism and automate update review when the codebase is active.

## 10. Definition of quality

"Highest quality" for HullQ means correctness, traceability, reproducibility, maintainability and explicit uncertainty — not maximum architectural complexity.

## CI and hosted-repository baseline

The implementation baseline is governed by `docs/engineering/CI_BASELINE.md`. When hosted on GitHub, repository rules/settings MUST follow `docs/engineering/GITHUB_REPOSITORY_SETTINGS.md` unless superseded by an accepted decision.
