# HullQ AI Token-Efficiency Standard

**Status:** ACTIVE operational standard  
**Purpose:** reduce Claude Code context growth and weekly usage without weakening slice governance, validation, provenance or review quality.

## Core rule

> One Claude Code session should normally serve one HullQ slice only.

A fresh slice starts from a fresh Claude conversation/session. Do not carry an old slice conversation into the next slice merely for convenience.

## Operator rules

### Before a new slice

1. Finish/close the previous slice through the normal HullQ workflow.
2. Open the new `HullQ-slice-XXXX` worktree in VS Code.
3. Start a fresh Claude conversation. If reusing the same Claude Code UI/session, run `/clear` before pasting the new START_SLICE prompt.
4. Paste only the generated START_SLICE prompt.

Do not paste old completion reports, previous slice discussions, or project-wide summaries unless the new controlling slice explicitly requires them.

### During a slice

Use `/context` when context growth is uncertain.

Use `/compact` when the session has become large but the same slice is still in progress. Preserve only:

- controlling slice contract;
- controlling artifacts actually used;
- decisions made within the slice;
- changed files/current implementation state;
- validation/CI state;
- unresolved findings/blockers;
- exact final-head/review handoff requirements.

Do not `/clear` mid-slice unless deliberately restarting the task and supplying a sufficient compact handoff, because `/clear` removes conversational working state.

### Between tasks

Use `/clear` when switching to a different slice or materially different task.

## Agent reading policy

The assigned slice is the primary execution entry point.

Claude MUST read:

1. `CLAUDE.md` (normally loaded as repository instructions);
2. the assigned primary `docs/slices/SLICE-XXXX-*.md` contract;
3. only the controlling specs/ADRs/protocols/files explicitly named by that slice or required to resolve a concrete implementation question;
4. `docs/engineering/AI_SLICE_WORKFLOW.md` only when workflow/ownership behavior is relevant or unclear.

Claude SHOULD NOT preload the full project history, ROADMAP, PROJECT_STATE, OPEN_QUESTIONS, REQUIREMENTS, slice INDEX, or unrelated architecture documents merely for orientation when the assigned slice does not require them.

If the slice references a requirement ID, read the relevant section/range rather than loading unrelated requirements when practical.

If a local synchronized checkout already contains a file, do not repeatedly fetch the same file through GitHub/API tooling.

## Search/read discipline

Prefer targeted search and narrow reads over whole-file reads when a file is large and only one symbol/section is needed.

Avoid repeatedly reopening unchanged files already understood in the current compact context.

Do not inspect unrelated directories "just in case".

Do not perform broad repository archaeology unless a concrete blocker requires it.

## Implementation discipline

- Work in small coherent edits.
- Run focused tests while iterating; run the full required validation suite at the accepted handoff gate.
- Do not repeatedly run expensive full suites after every small edit unless the failure mode requires it.
- Do not restate the slice contract before implementing it.
- Do not narrate routine exploration unless a blocker or governance ambiguity must be surfaced.
- Reuse existing helpers/contracts instead of re-deriving accepted project semantics in conversation.

## Model discipline

Default normal HullQ slice implementation remains the project's accepted capable coding model.

Use a cheaper/smaller model only for genuinely mechanical work where the risk of extra review/amendment cycles is low. Do not trade a small per-token saving for a lower-quality patch that creates larger downstream context and review cost.

The primary optimization target is context size and unnecessary repeated reads, not indiscriminate model downgrading.

## Completion-report discipline

The required `SLICE_TEMPLATE.md` report remains mandatory, but it must be concise.

The agent MUST report:

- slice/state/scope;
- changed files;
- requirements/research addressed;
- tests/fixtures changed;
- local validation commands and summarized results;
- exact final branch HEAD;
- remote CI/external verification state;
- unresolved findings/ambiguities/scope deviations;
- recommended next action;
- agent declaration.

The agent SHOULD NOT include unless needed to explain a failure/blocker:

- full command logs;
- complete diffs;
- repeated acceptance-criteria prose;
- long explanations of code already visible in the PR;
- repository history recaps;
- speculative next-slice plans.

## Review/amendment discipline

When an independent review returns an amendment:

- continue in the same slice session if context remains modest;
- otherwise `/compact` before applying the amendment;
- preserve the exact reviewed HEAD, amendment requirements, affected files and required validation;
- do not reload unrelated project background.

After the slice reaches final handoff, stop. The next slice uses a fresh session.

## Context target

There is no absolute hard context threshold because task complexity varies. Operationally:

- avoid allowing sessions above roughly 150k context to become the normal state;
- compact earlier when a slice contains repeated research, logs or large file reads;
- prefer a fresh session at every slice boundary.

The goal is not minimum tokens at any cost. The goal is minimum **wasted** tokens while preserving correctness, reproducibility, safety and independent review.

## Project-master/operator responsibility

The project master should explicitly direct the operator when to:

- start a fresh Claude session or run `/clear`;
- run `/compact` before a large amendment/review continuation;
- avoid feeding duplicate context;
- stop a session after handoff.

Token efficiency is therefore part of normal HullQ orchestration, not something the operator must remember independently.
