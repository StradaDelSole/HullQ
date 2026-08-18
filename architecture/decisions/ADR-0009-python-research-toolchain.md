# ADR-0009 — Python Research/Data-Pipeline Toolchain

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Decision:** OQ-010

## Context

HullQ is ready to move from domain/data specifications into Stage 2 research-pipeline implementation. The project requires a reproducible, strict, low-maintenance Python environment that supports network-bound research, deterministic normalization, JSON Schema validation, provenance, fixtures and benchmark measurement without prematurely selecting production backend/database/distributed infrastructure.

## Decision

Adopt `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md` as the initial Python implementation baseline:

1. CPython 3.14, constrained to the tested 3.14 major line;
2. uv for Python provisioning, dependencies, environments and locking;
3. `uv_build` and a PyPA-style `src/` package layout;
4. Ruff as the only formatter/linter/import-sorter baseline;
5. mypy strict as the canonical blocking type checker;
6. pytest + coverage.py + Hypothesis for deterministic, branch and property-based tests;
7. `jsonschema` for normative Draft-2020-12 contract validation;
8. HTTPX for permitted network access;
9. `asyncio.TaskGroup` for bounded structured concurrency;
10. stdlib SQLite as an explicitly non-production Stage-2 job/control store;
11. no ORM/distributed scheduler/message broker in Stage 2 without new evidence/decision;
12. committed `uv.lock` and dependency-vulnerability auditing as part of engineering discipline.

## Rationale

The chosen stack minimizes overlapping tools and external services while preserving strong static/contract/test guarantees. It keeps Stage 2 runnable on a single developer machine, fits Windows development and Linux CI, and leaves OQ-011/OQ-012 free to choose later application/backend/persistence architecture based on actual requirements.

Mypy is preferred over Pyright for the canonical CI gate because it is a mature Python dependency that can be locked with the same uv environment; official Pyright CLI use would introduce Node solely for type checking at this stage. `ty` remains a deliberate future re-evaluation candidate rather than being adopted as a blocking gate while younger.

## Consequences

### Positive

- one locked Python toolchain;
- fast formatting/linting;
- strict static typing;
- deterministic contract/golden tests;
- no service dependencies required for benchmark development;
- straightforward local/CI reproducibility;
- low operational burden.

### Costs

- Python 3.15 support will require an explicit compatibility update rather than being automatic;
- SQLite is deliberately temporary for production concerns;
- mypy and VS Code/Pylance may occasionally report different editor diagnostics; CI remains authoritative;
- if benchmark throughput outgrows a single process/machine, orchestration/storage must be revisited explicitly.

## Alternatives considered

- Poetry/Pipenv/Conda: additional or overlapping environment-management complexity without current need.
- Pyright as CI authority: excellent checker, but official CLI adds a Node toolchain before otherwise needed.
- ty as CI authority: promising and modern, but deferred in favor of more mature blocking tooling.
- Pydantic-first models: duplicates normative JSON Schema authority.
- PostgreSQL/Redis/Celery/Temporal/Airflow: premature before benchmark evidence.

## Acceptance evidence required

Acceptance evidence satisfied:

- project owner explicitly accepted OQ-010 on 2026-08-18;
- current official documentation supports the selected Python/tool versions/capabilities;
- draft `pyproject.toml` configuration is internally coherent;
- repository bootstrap plan includes cross-platform CI and lockfile validation;
- no unresolved Stage-2 requirement depends on a rejected tool capability.
