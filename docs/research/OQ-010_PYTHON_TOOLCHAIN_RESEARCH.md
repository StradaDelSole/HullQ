# OQ-010 — Python / Research Data-Pipeline Toolchain Research

**Status:** DECIDED / ACCEPTED  
**Date:** 2026-08-18  
**Decision target:** ADR-0009

## 1. Decision scope

OQ-010 selects the smallest modern, reproducible Python toolchain required to implement HullQ Stage 2 research/data-pipeline work. It does **not** decide the future public web frontend, production application backend, production database/search engine, or distributed job infrastructure.

## 2. Decision principles

The toolchain MUST optimize for:

1. deterministic/reproducible local and CI environments;
2. strict static analysis and automated tests;
3. low operational/tooling complexity for a solo-maintained project;
4. first-class Windows and Linux development/CI compatibility;
5. fast iteration for AI-assisted docs-to-code work;
6. explicit dependency locking and deliberate upgrades;
7. structured concurrency for network-bound research without premature distributed infrastructure;
8. compatibility with HullQ's JSON Schema Draft 2020-12 contracts;
9. easy replacement of local benchmark persistence when OQ-012 later selects production persistence.

## 3. Runtime

### Recommendation: CPython 3.14

Python 3.14 is the current stable major line and is supported by the proposed lint/test/coverage stack. HullQ should target exactly the tested 3.14 family initially rather than silently accepting a future 3.15 runtime before CI validation.

Proposed project constraint:

```toml
requires-python = ">=3.14,<3.15"
```

A `.python-version` file should contain `3.14` so uv can provision an appropriate stable patch release.

The upper bound is an operational compatibility gate, not a claim that HullQ cannot run on later Python. A deliberate toolchain update should widen it after CI validation.

## 4. Project/dependency manager

### Recommendation: uv

Use uv as the Python/project/dependency manager.

Reasons:

- native `pyproject.toml` project workflow;
- standardized dependency groups;
- committed `uv.lock` for reproducible environments;
- managed Python versions;
- fast local/CI synchronization;
- workspaces available later if multiple Python packages become justified inside the same repository.

HullQ SHOULD begin with **one Python package**, not a uv workspace created speculatively. A workspace can be introduced when a second independently packaged Python component actually exists.

CI and local commands SHOULD use the committed lockfile. CI MUST fail if `pyproject.toml` and `uv.lock` disagree (`uv lock --check` / locked execution semantics).

## 5. Build backend and layout

### Recommendation: `uv_build` + `src/` layout

Use the PEP-517-compatible `uv_build` backend for the initial pure-Python package and a `src/` layout:

```text
src/
  hullq/
    domain/
    research/
    sources/
    storage/
    cli/
tests/
```

The PyPA documents the `src/` layout as protection against accidentally importing the working-tree package rather than the installed package. This is valuable for CI/reproducibility.

Do not split these directories into separate packages/services until an accepted architectural need exists.

## 6. Formatting and linting

### Recommendation: Ruff

Use Ruff as the sole Python formatter/import sorter/linter baseline.

Proposed baseline:

- target Python: `py314`;
- line length: 100;
- formatter: Ruff formatter;
- lint families initially include core Pyflakes/pycodestyle errors, import sorting, Bugbear, pyupgrade, Ruff-specific correctness, pathlib/datetime/performance/simplification rules where applicable;
- preview rules MUST NOT be enabled globally without an explicit tooling update.

Do not add Black, isort, Flake8 or overlapping plugins unless a demonstrated gap requires them.

## 7. Static typing

### Recommendation: mypy strict as the CI authority

Use mypy in strict mode as the blocking static type checker for Stage 2.

Why mypy rather than Pyright as the canonical CI checker:

- mypy is mature/production-ready, supports Python 3.14, and is installed/locked as a normal Python development dependency;
- official Pyright CLI tooling is Node-based, which would add a second package ecosystem solely for the Python pipeline before HullQ otherwise needs Node;
- VS Code/Pylance may still provide excellent editor diagnostics, but CI should have one deterministic, repository-locked authority.

Why not adopt `ty` as the blocking checker yet:

- ty is technically attractive, very fast and current, but it is materially younger than mypy/Pyright;
- HullQ should prefer proven correctness tooling over novelty at the first pipeline implementation;
- re-evaluate ty after the benchmark pipeline or in a later toolchain ADR when its maturity/adoption warrants replacement.

Proposed mypy posture:

- `strict = true`;
- target Python 3.14;
- typed public/internal boundaries;
- `Any` escape hatches require narrow, documented suppressions;
- no blanket ignores for third-party typing problems.

## 8. Tests and property-based testing

### Recommendation: pytest + coverage.py + Hypothesis

Use:

- pytest as the test runner;
- coverage.py with branch coverage;
- Hypothesis selectively for normalization/parsing/unit-conversion/state-machine invariants.

Pytest should run with strict config and strict markers. Coverage percentage is a floor, not a proxy for correctness. Proposed initial global floor is 90% line/branch coverage for implemented Python package code, while critical domain logic (identity normalization, ratio calculations, state transitions, rights gates) requires explicit boundary/regression/property tests regardless of percentage.

Golden fixtures remain authoritative for exact deterministic domain cases.

## 9. JSON Schema validation

### Recommendation: `jsonschema`

Use the Python `jsonschema` library with schemas explicitly declaring Draft 2020-12. Code SHOULD select validators from each schema's `$schema` declaration rather than relying on an implicit latest draft.

The existing JSON Schemas remain normative. Runtime Python classes MUST NOT become an independent second source of schema truth.

## 10. Runtime modeling approach

### Recommendation: stdlib typed models first; no Pydantic dependency in baseline

Start with:

- dataclasses where value objects benefit from runtime structure;
- `TypedDict`, enums, protocols and normal typed classes where appropriate;
- JSON Schema validation at external/data-contract boundaries.

Do **not** introduce Pydantic merely to duplicate the already normative JSON Schemas. Add a runtime-model framework only if implementation evidence demonstrates a concrete reduction in complexity without schema drift.

## 11. Network client

### Recommendation: HTTPX

Use HTTPX for permitted HTTP source access because it provides sync/async APIs, connection pooling, explicit resource limits and timeouts.

Rules:

- use scoped `Client`/`AsyncClient`, not top-level request calls in hot loops;
- explicit finite connect/read/write/pool timeouts;
- bounded concurrency per source;
- source-specific User-Agent/access policy;
- automated access MUST pass Source Rights clearance before execution;
- response persistence MUST honor the Source Rights Policy.

Retries are HullQ policy, not an implicit infinite client behavior. Retry only transient failures, with bounded attempts/backoff and idempotency awareness.

## 12. Concurrency and orchestration

### Recommendation: stdlib `asyncio.TaskGroup` + explicit job state machine

For Stage 2 network-bound research:

- use `asyncio.TaskGroup` for structured concurrency;
- use bounded semaphores/source limits;
- propagate cancellation correctly;
- persist ResearchJob state transitions;
- make stages restart-safe/idempotent where practical.

Do not introduce Celery, Airflow, Temporal, Redis queues, Kubernetes, or another distributed orchestrator before benchmark evidence shows one process / one machine is insufficient.

CPU-heavy work, if it appears, should be isolated behind explicit executors/processes rather than blocking the event loop.

## 13. Benchmark/local persistence

### Recommendation: stdlib SQLite, explicitly non-production

Use SQLite through Python's `sqlite3` module as the Stage 2 durable local job/control store.

Reasons:

- no server process;
- transactional durable state;
- appropriate for a benchmark/research tool;
- easy to inspect/back up;
- does not pre-decide OQ-012 production persistence.

Rules:

- explicit transaction handling (`autocommit` behavior MUST be set, not inherited from a future-changing default);
- parameterized SQL only;
- foreign keys enabled;
- versioned SQL migrations;
- do not build an ORM abstraction until evidence justifies it;
- canonical exported domain records remain contract-valid JSON/NDJSON rather than SQLite becoming the semantic source of truth.

SQLite WAL mode/concurrency tuning should be benchmark-driven rather than assumed.

## 14. Raw artifacts and reproducibility

Network/source raw artifacts are operational inputs, not Git content by default.

Recommended local shape:

```text
var/
  raw/
  work/
  state/
```

`var/` MUST be gitignored. Raw artifacts that may legally be retained SHOULD be immutable/content-addressed or otherwise hash-identified. Provenance records retain the relevant source/evidence identifiers and hashes. Source Rights clearance controls whether content may be stored at all.

Small legal/test fixtures required for deterministic tests remain under `fixtures/`.

## 15. Configuration and secrets

- committed non-secret configuration lives in `pyproject.toml` or versioned application config;
- secrets MUST come from environment/secret-management mechanisms and MUST NOT enter Git;
- no production credentials in `.env` files committed to the repo;
- locale/timezone/encoding-dependent parsing must be explicit and testable.

## 16. Dependency/security discipline

- commit `uv.lock`;
- dependency upgrades are explicit changes, not automatic at runtime;
- use stable releases by default;
- use `pip-audit` as a CI/release dependency-vulnerability signal;
- vulnerability reports are investigated, not blindly auto-fixed;
- minimize dependencies and remove unused ones.

## 17. Proposed quality commands

After OQ-010 acceptance and repository bootstrap, the canonical Python gates should be equivalent to:

```text
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report --fail-under=90
```

Schema/fixture validation gets its own first-party test/CLI entry and MUST run in CI.

Dependency auditing is a separate network-dependent CI/release check.

## 18. CI platform baseline

At bootstrap:

- Python tests SHOULD run on Linux and Windows because development occurs on Windows while deployment/CI is likely Linux-oriented;
- lint/type/schema checks may run once on Linux;
- all blocking jobs use Python 3.14 and the committed lockfile;
- later Python-version expansion requires a deliberate runtime-support decision.

## 19. Rejected alternatives

### Poetry/Pipenv as project manager

Rejected for Stage 2 because uv already covers environment, dependency, lock and Python management with lower tooling overlap.

### Conda

Rejected because HullQ's initial pure-Python/data workload does not require a separate binary/scientific environment distribution layer.

### Pyright as CI authority

Not rejected as a checker; rejected as the initial canonical CI authority because the official CLI brings Node into the pipeline toolchain solely for typing. Pylance/Pyright remains acceptable as editor assistance.

### ty as CI authority

Deferred, not rejected. Revisit after Stage 2 or when a toolchain refresh is justified.

### Pydantic as normative model layer

Rejected because JSON Schema is already the normative contract and duplicate schema-generation authority creates drift risk.

### PostgreSQL / Redis / distributed queues in Stage 2

Rejected as premature. OQ-012 remains the production persistence decision.

## 20. Decision closure and bootstrap exit criteria

OQ-010 is **closed by decision acceptance**: ADR-0009 and the toolchain baseline are accepted. The repository bootstrap is a separate execution gate and remains incomplete until the locked environment is materialized.

Bootstrap exit criteria are:

1. root `pyproject.toml` and `.python-version` exist;
2. a committed `uv.lock` is generated by the accepted uv line against real package metadata;
3. the initial `src/` + `tests/` skeleton exists;
4. locked Linux + Windows CI runs repository/schema validation, format, lint, strict typing and tests;
5. dependency auditing runs against the locked environment;
6. no production research behavior is merged before those gates are green.

A missing lockfile blocks Stage-2 implementation readiness but does **not** reopen the accepted OQ-010 decision.

## 21. Post-decision bootstrap verification — 2026-08-18

The accepted toolchain has been translated into the repository bootstrap. Current official documentation was re-checked before pinning the initial bootstrap:

- uv uses a committed cross-platform `uv.lock`; locked CI must reject manifest/lock drift;
- the repository uses a root `pyproject.toml` and `src/` package layout;
- GitHub Actions installs uv through the official `astral-sh/setup-uv` action with immutable action SHAs;
- Dependabot configuration covers both the uv dependency ecosystem and GitHub Actions;
- CI quality jobs target both Linux and Windows.

The artifact-generation environment used to prepare this repository snapshot has no usable package-index/network access and does not provide the accepted Python 3.14 environment. Therefore `uv.lock` MUST NOT be fabricated. It remains the final external bootstrap artifact to generate and commit in a networked development environment before Stage 2 implementation begins.
