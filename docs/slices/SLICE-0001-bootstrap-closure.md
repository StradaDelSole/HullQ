# SLICE-0001 — Close Repository Bootstrap

**Type:** BOOTSTRAP  
**Status:** DONE  
**Stage:** 0.3  
**Depends on:** OQ-010 / ADR-0009  
**Blocks:** SLICE-0002 and all domain implementation

## Objective

Close the final repository-bootstrap gate by generating a real reproducible `uv.lock`, synchronizing the accepted Python 3.14 environment, passing every local quality gate, and obtaining the first green Linux + Windows CI run.

## Why this slice exists

The repository skeleton and CI configuration already exist, but the accepted toolchain requires a committed lockfile produced by a network-capable environment. Product/domain code must not begin while reproducibility is still incomplete.

## Controlling artifacts

- `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md`
- `architecture/decisions/ADR-0009-python-research-toolchain.md`
- `docs/engineering/QUALITY_GATES.md`
- `docs/engineering/CI_BASELINE.md`
- `pyproject.toml`
- `.python-version`
- `.github/workflows/ci.yml`
- `specs/REQUIREMENTS.md` — governance/toolchain requirements

## In scope

- install/use the accepted Python 3.14 runtime;
- install/use accepted uv version compatible with the repository baseline;
- generate `uv.lock` from `pyproject.toml`;
- synchronize all dependency groups from the lockfile;
- run repository validation, formatting, lint, typing, tests, branch coverage and dependency audit;
- make only bootstrap/tooling corrections required to satisfy already accepted OQ-010 semantics;
- commit `uv.lock`;
- confirm Linux and Windows GitHub Actions are green.

## Explicitly out of scope

- boat/domain implementation;
- data-model changes;
- selecting a production database;
- changing accepted derived-metric, provenance, identity, search, source-rights or product semantics;
- adding infrastructure not required by the accepted toolchain.

## Procedure

From repository root:

```bash
uv python install 3.14
uv lock
uv lock --check
uv sync --locked --all-groups

uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

If formatting itself is the only failure, apply the accepted formatter and rerun all affected checks:

```bash
uv run ruff format .
```

## Acceptance criteria

- [x] `uv.lock` exists and is committed.
- [x] `uv lock --check` passes.
- [x] `uv sync --locked --all-groups` passes from a clean environment.
- [x] repository contract validator passes. (11 schemas, 81 requirements, 81 acceptance criteria)
- [x] Ruff format check passes. (1 file reformatted per accepted formatter procedure, then check clean)
- [x] Ruff lint passes.
- [x] mypy strict gate passes for `src/`. (6 source files, 0 issues)
- [x] pytest passes. (18 passed)
- [x] configured branch-coverage threshold passes. (100% — exceeds 90% floor)
- [x] dependency audit passes or any upstream false-positive/exemption is explicitly documented and approved rather than silently ignored. (pip-audit: no known vulnerabilities; `hullq` itself not on PyPI is expected for a private package)
- [x] GitHub Actions `quality` passes on Ubuntu and Windows.
- [x] GitHub Actions dependency-audit passes.
- [x] no HullQ domain behavior was introduced.

## Expected touch points

- `uv.lock`
- bootstrap/tooling config only if required by an accepted-toolchain compatibility issue
- `docs/PROJECT_STATE.md`
- `docs/slices/INDEX.md`
- this slice status

## Stop conditions

Stop and report if:

- dependency resolution requires changing an accepted tool or major version policy;
- Python 3.14 incompatibility appears in an accepted dependency;
- CI requires relaxing a quality gate rather than correcting code/configuration;
- completing the slice would require product/domain semantics.

Do not solve any of those conditions silently.

## Required completion report

Report:

- generated lockfile status;
- files changed;
- exact commands run and results;
- GitHub Actions run/check status;
- any toolchain compatibility finding;
- confirmation that no domain implementation was added.

Do not automatically begin SLICE-0002.
