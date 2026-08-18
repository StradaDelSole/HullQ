# HullQ

**Find boats by what they are.**

HullQ is a technical-first sailboat discovery and market-finding project. It lets users describe the boat they want by actual design characteristics, resolves those requirements to matching sailboat designs, and ultimately connects those designs to current boats for sale.

This repository is developed **docs-to-code**: accepted specifications, requirements, architecture decisions, evidence, fixtures and tests define what implementation is allowed to do.

## Current state

HullQ is at the repository-bootstrap / Stage-2 boundary. Core data-foundation decisions covering identity, source rights, field-level provenance, derived metrics and the Python research toolchain are accepted. The next bootstrap gate is generating and committing a real `uv.lock` with the accepted Python 3.14 + uv toolchain and establishing the first green Linux/Windows CI run.

See:

- `PROJECT_CONTEXT.md`
- `CLAUDE.md`
- `docs/PROJECT_STATE.md`
- `docs/EXECUTION_PLAN.md`
- `docs/DOCS_TO_CODE_METHOD.md`
- `specs/REQUIREMENTS.md`
- `docs/governance/OPEN_QUESTIONS.md`
- `architecture/decisions/`

## Product principle

```text
TECHNICAL REQUIREMENTS
        ↓
HULLQ DESIGN UNIVERSE
        ↓
MATCHING DESIGNS
        ↓
MARKET AVAILABILITY
        ↓
COMPARE / SAVE / MONITOR / ALERT
```

HullQ is not intended to become a generic boating super-app or a two-sided listing marketplace. The current business objective is a lean, highly automated, low-maintenance niche product; larger-scale expansion may be reconsidered if actual traction justifies it.

## Data strategy

HullQ targets broad SailboatData-like design coverage early, with progressive verification depth. A 50–100-design corpus is a benchmark for the research pipeline, not the intended product database. Unknown data is never interpreted as a negative fact.

## Engineering baseline

- single repository
- docs-to-code
- CPython 3.14
- uv
- Ruff
- mypy strict
- pytest + coverage + Hypothesis
- JSON Schema Draft 2020-12
- Linux + Windows CI
- explicit requirements → tests → implementation traceability

See `docs/engineering/` for the normative engineering baseline.
