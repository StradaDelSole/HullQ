# HullQ — CI Baseline

**Status:** ACCEPTED bootstrap contract  
**Decision basis:** OQ-010 / ADR-0009  
**Workflow:** `.github/workflows/ci.yml`

## Purpose

CI is a product-engineering gate, not a reporting dashboard. A mergeable Python change must prove that the repository remains reproducible, contract-valid, formatted, lint-clean, type-safe under the accepted scope, tested and within the configured coverage floor.

## Required jobs

### `quality`

Runs on both:

- `ubuntu-latest`;
- `windows-latest`.

Required steps:

1. immutable-SHA checkout;
2. install pinned uv baseline and Python 3.14;
3. `uv lock --check`;
4. `uv sync --locked --all-groups`;
5. repository/schema validation;
6. Ruff format check;
7. Ruff lint;
8. mypy strict for `src/`;
9. pytest under branch coverage;
10. coverage threshold enforcement.

### `dependency-audit`

Runs on Linux with the same locked environment and executes `pip-audit`.

## Supply-chain rules

- Third-party GitHub Actions MUST be pinned to immutable commit SHAs, with the human-readable release in a trailing comment.
- uv is pinned by CI input and constrained by `[tool.uv].required-version`.
- `uv.lock` MUST be committed and CI MUST NOT silently refresh it.
- Dependabot tracks both the `uv` and `github-actions` ecosystems.
- Dependency updates MUST pass the same quality gates as feature changes.
- CI jobs MUST use finite job timeouts so hung external/tooling behavior cannot consume unbounded runner time.

## Required-check stability

A workflow that becomes a required repository check MUST NOT use path filtering that can leave the check permanently pending for otherwise valid pull requests.

## Change control

A material change to the CI gate set, supported OS matrix, accepted Python line, package manager or canonical type checker MUST update the governing toolchain/engineering docs and ADR when architectural.
