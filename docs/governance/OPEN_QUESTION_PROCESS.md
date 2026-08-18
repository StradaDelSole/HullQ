# HullQ — Open Question and Decision Process

**Status:** ACCEPTED

## Purpose

Open questions are treated as managed project objects, not loose notes. The goal is to prevent coding agents or future maintainers from silently making product, data or architecture decisions.

## Identifier

Use `OQ-NNN`.

## Required fields

Every material open question records:

- **ID**
- **Title**
- **Status**: `OPEN | RESEARCHING | READY_FOR_DECISION | DECIDED | DEFERRED | REJECTED`
- **Why it matters**
- **Decision deadline/gate**
- **Affected requirements/specs**
- **Known options**
- **Decision criteria**
- **Evidence required**
- **Risks of wrong choice**
- **Decision output**
- **Resulting ADR/spec changes**

## Workflow

```text
OPEN
  ↓
RESEARCHING
  ↓
READY_FOR_DECISION
  ↓
DECIDED
  ↓
ADR/spec/requirement update
  ↓
tests/implementation
```

A question MAY be `DEFERRED` only if the next execution gate does not depend on it.

## When an ADR is required

Create an ADR when the answer:

- significantly constrains architecture;
- is expensive to reverse;
- selects among meaningful alternatives;
- establishes a repository-wide engineering rule;
- changes a public or persisted contract;
- creates a deliberate dependency on an external platform or technology.

Small taxonomy values or formula details can be resolved directly in a versioned spec if no architectural decision is involved.

## Evidence standard

Decision evidence SHOULD prefer, in order:

1. primary/official documentation;
2. measured HullQ benchmark results;
3. controlled prototype results;
4. directly observed user/market evidence;
5. high-quality secondary research;
6. reasoned inference.

LLM opinion is input, not evidence by itself.

## Current register

The canonical register is `docs/governance/OPEN_QUESTIONS.md`. `docs/DECISIONS_REQUIRED.md` remains a compatibility summary until all existing `D-*` items are migrated.
