# HullQ Implementation Slices

Implementation slices are HullQ's operational unit of AI-assisted work between the master execution plan and code changes.

A slice is **not** a free-form prompt. It is a small, versioned work contract that tells an implementation or research agent exactly what may be changed, which accepted artifacts control the work, how success is tested, and when the agent must stop instead of inventing a decision.

## Authority

Slices are operational documents. They do not override normative specifications, accepted ADRs, requirements, source-rights policy, or governance rules.

If a slice conflicts with a controlling artifact, the controlling artifact wins and the slice MUST be corrected before implementation proceeds.

## Allowed slice types

- `BOOTSTRAP` — tooling, CI, repository and reproducibility work; no product semantics.
- `DESIGN_RESEARCH` — research and architecture/specification work; no domain implementation unless explicitly authorized by a later slice.
- `IMPLEMENTATION` — code implementing already accepted requirements/specifications.
- `VALIDATION` — test, benchmark, migration or verification work with no new semantics.

## Statuses

Only these statuses are valid:

- `BACKLOG`
- `READY`
- `IN_PROGRESS`
- `BLOCKED`
- `REVIEW`
- `DONE`

A slice may become `READY` only when its upstream decisions are resolved, controlling requirements/specs are identified, acceptance criteria are explicit, and the validation method is known.

## Rolling-wave planning

HullQ deliberately does not specify dozens of implementation slices in detail up front.

Preferred horizon:

- 1 slice active or ready for immediate execution;
- 2–4 following slices outlined with enough detail to preserve direction;
- later work retained as backlog only.

This prevents stale micro-plans when implementation or research reveals a real upstream issue.

## Execution rule

For every assigned slice, the agent MUST:

1. read `CLAUDE.md`;
2. read `docs/slices/INDEX.md`;
3. read the assigned slice;
4. read every controlling artifact named by the slice;
5. stay inside explicit scope;
6. add or update tests/fixtures before or with behavior changes;
7. run the slice validation commands;
8. report changed files, requirements covered, tests added, commands run, and unresolved findings.

The agent MUST NOT automatically begin the next slice.

If a required product/domain/data/licensing/architecture decision is absent, contradictory, or blocked, the agent MUST stop and report the issue rather than resolve it silently in code.

## Git discipline

Preferred unit:

```text
one slice
→ one short-lived branch
→ one coherent implementation/research change
→ one reviewable PR
→ merge
```

A slice may span more than one commit when useful, but the PR MUST remain coherent and independently reviewable.

## Completion

`DONE` means more than "code exists". The slice acceptance criteria and repository quality gates must pass, required docs/state must be updated, and no unresolved scope item may be hidden in implementation.

Use `docs/slices/SLICE_TEMPLATE.md` for new slices.
