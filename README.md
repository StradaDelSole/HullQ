# HullQ

**Find boats by what they are.**

HullQ is a technical-first sailboat discovery and market-finding project. It lets users describe the boat they want by actual design characteristics, resolves those requirements to matching sailboat designs, and ultimately connects those designs to current boats for sale.

This repository is developed **docs-to-code**: accepted specifications, requirements, architecture decisions, evidence, fixtures and tests define what implementation is allowed to do.

## Current state

HullQ is at the repository-bootstrap / pre-domain-implementation boundary. Core data-foundation decisions covering identity, source rights, field-level provenance, derived metrics and the Python research toolchain are accepted.

Before HullQ domain implementation begins, two gates remain:

1. close repository bootstrap with a real committed `uv.lock` and first green Linux/Windows CI (`SLICE-0001`);
2. consolidate the accepted distributed contracts into one persistence-neutral canonical logical data model (`OQ-019` / `SLICE-0002`).

The production database/search technology remains intentionally open under OQ-012 until the logical model, access patterns and benchmark evidence exist.

See:

- `PROJECT_CONTEXT.md`
- `CLAUDE.md`
- `docs/PROJECT_STATE.md`
- `docs/EXECUTION_PLAN.md`
- `docs/slices/INDEX.md`
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

The current data-architecture rule is:

```text
accepted logical/domain model first
        ↓
research + benchmark implementation
        ↓
measured access patterns / scale
        ↓
production database + search/index choice under OQ-012
```

## AI-assisted development

HullQ uses bounded implementation/research slices under `docs/slices/`.

An implementation agent should receive a small instruction such as:

```text
Implement SLICE-0001.
Read CLAUDE.md first and follow the assigned slice exactly.
Do not begin the next slice automatically.
```

The slice itself points to controlling requirements/specs/ADRs and defines scope, acceptance criteria, stop conditions and validation.

## Engineering baseline

- single repository
- docs-to-code
- bounded implementation slices
- CPython 3.14
- uv
- Ruff
- mypy strict
- pytest + coverage + Hypothesis
- JSON Schema Draft 2020-12
- Linux + Windows CI
- explicit requirements → tests → implementation traceability

See `docs/engineering/` for the engineering baseline.
