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
9. pytest (`-n auto --dist loadgroup`, no coverage — coverage is measured once, in `db-integration`).

### `web-quality`

Astro/TypeScript check, web build, bounded web smoke tests. Runs independently of the Python jobs.

### `db-integration`

Runs on Linux against a `postgres:18` service container. Required steps:

1. checkout, uv/Python install, locked sync;
2. full backend suite (`pytest -n auto --dist loadgroup --cov=hullq --cov-branch`) — see
   "SLICE-0073 throughput topology" below for the parallel-shard/isolation design;
3. `coverage report` enforcing the repository-wide 90% branch-coverage floor against the
   combined coverage data from every xdist worker;
4. web build, then the retained per-slice real-HTTP vertical proofs (SLICE-0048 onward);
5. the persistence benchmark runner and its schema/recommendation validation.

### `historical-research-replay`

Runs on Linux against its own `postgres:18` service container, in parallel with
`db-integration`. Always executes (never workflow-level path-filtered, so it can never become a
permanently-pending required check), but its Wikidata bootstrap/replay steps
(SLICE-0017/0018/0021/0022/0026/0027/0028/0030/0031/0032) are individually gated by
`scripts/workflow/historical_replay_scope.py`'s relevance decision — see
`docs/engineering/CI_THROUGHPUT_EVIDENCE.md` for the routing rationale, the exact relevant-path
boundary and the fail-open behavior. Always relevant (steps always run) on `schedule`,
`workflow_dispatch`, and `push` to `main`.

### `dependency-audit`

Runs on Linux with the same locked environment and executes `pip-audit`.

## SLICE-0073 throughput topology

- `quality` and `db-integration` both invoke pytest with `-n auto --dist loadgroup`
  (pytest-xdist). `--dist loadgroup` keeps every test carrying an `xdist_group` mark on one
  worker while load-balancing every other test freely across all workers.
- `tests/persistence/conftest.py` applies that mark to the small, explicitly enumerated set of
  test modules that read/write the connection's *default* (unqualified search_path) PostgreSQL
  schema directly, rather than a throwaway per-test schema — see
  `_XDIST_SHARED_SCHEMA_MODULES` there. Every other persistence test already isolates itself in
  a uniquely named, created-and-dropped-per-test schema and is safe to run on any worker
  concurrently with any other test.
- `db-integration`'s coverage step uses `pytest-cov` (`--cov=hullq --cov-branch`), which combines
  every xdist worker's branch-coverage data automatically before the separate
  `coverage report` step enforces `fail_under = 90` against the combined result.
- The local/Claude final-validation path uses the same mechanism through the existing
  `scripts/workflow/claude_diag.py run-local-test-db-compact` helper — see
  `docs/engineering/AI_TOKEN_EFFICIENCY.md`.

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
