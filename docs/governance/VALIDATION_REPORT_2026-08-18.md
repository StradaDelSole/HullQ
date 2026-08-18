# HullQ — Validation Report — 2026-08-18

**Scope:** post-OQ-010 acceptance and Stage-0.3 repository bootstrap snapshot.

## Decision state

- OQ-001: DECIDED; ADR-0008 ACCEPTED.
- OQ-003: DECIDED; ADR-0004 ACCEPTED.
- OQ-004: DECIDED; ADR-0006 ACCEPTED.
- OQ-007: DECIDED; ADR-0005 ACCEPTED.
- OQ-010: DECIDED; ADR-0009 ACCEPTED.
- Search/SEO first-class architecture: ADR-0007 ACCEPTED.

## Repository bootstrap state

Created and validated offline:

- root `pyproject.toml`;
- `.python-version` targeting Python 3.14;
- `src/hullq/` single-package skeleton;
- unit/contract/integration test topology;
- repository/schema/governance validation script;
- Linux + Windows GitHub Actions quality CI;
- dependency-audit job;
- Dependabot config for uv and GitHub Actions;
- docs-to-code pull-request template;
- finite CI job timeouts;
- bootstrap/CI/GitHub-settings documentation.

## Offline executable validation

The artifact runtime does not provide the accepted Python 3.14 + uv 0.12.x environment and cannot access package indexes. Within the available runtime, all checks that do not require resolving the accepted environment were executed:

```text
active JSON Schemas                         11  PASS
Requirements                               81  PASS
Acceptance Criteria                        81  PASS
Requirement IDs unique                         PASS
active DRAFT/PROPOSED spec files                none
repository/schema/governance validator          PASS
unit + contract regression tests           18  PASS
Python compileall                               PASS
pyproject TOML parse                            PASS
JSON parse                                      PASS
GitHub workflow/Dependabot YAML parse           PASS
```

Contract regression includes current identity contracts, source-rights fixtures, positive/negative provenance fixtures, and accepted derived-metric fixtures through the first-party contract test suite.

## Reproducibility gate intentionally still open

`uv.lock` is **not present**. This is intentional. A dependency lockfile MUST be produced by the accepted uv line against real package metadata; it MUST NOT be fabricated or hand-authored in an offline artifact environment.

Stage 0.3 becomes DONE only after a networked development/CI environment performs:

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

and the locked CI baseline passes on Linux and Windows.

## Integrity

The original three user-supplied HullQ input files remain preserved under `reference/imported/`; repository manifest hashing is regenerated for each integrated snapshot.

## Conclusion

OQ-010 is formally closed. The repository structure and executable contract baseline are ready. The **single remaining Stage-0.3 blocker is a real committed `uv.lock` plus the first green locked CI run**. Production Stage-2 research-pipeline behavior must not be merged before that gate is satisfied.
