# Contributing to HullQ

HullQ uses a docs-to-code workflow even when changes are made by a single maintainer or AI coding agents.

## Before changing behavior

1. Read `CLAUDE.md` and `PROJECT_CONTEXT.md`.
2. Read `docs/DOCS_TO_CODE_METHOD.md`.
3. Identify the controlling requirement(s) in `specs/REQUIREMENTS.md`.
4. Check `docs/governance/OPEN_QUESTIONS.md` for blockers.
5. Read relevant specs/ADRs.

## Change sequence

```text
spec/decision → tests → implementation → verification
```

Behavioral changes should not be implemented only in code.

## Commits

Use Conventional Commits once the repository is under active Git development.

## Pull/merge quality

A change should pass the applicable gates in `docs/engineering/QUALITY_GATES.md` before merging to the default branch.

## Scope

Do not expand HullQ outside the product guardrail without an explicit project decision.

## Python bootstrap commands

After installing uv 0.12.5+:

```bash
uv python install 3.14
uv lock
uv sync --locked --all-groups
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

`uv.lock` MUST be committed. CI uses locked sync and does not silently refresh it.
