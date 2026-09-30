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

Use `/context` early rather than after the session is already near its limit.

For substantial implementation slices, use this phase policy:

- after initial reconnaissance/planning: continue normally;
- after the main implementation is materially complete and **before the final broad validation phase**, request one `/compact` checkpoint when the slice touched many files, involved debugging/rework, or accumulated substantial tool output;
- if reported context is around **80k+ tokens**, compact at the next safe phase boundary;
- if reported context is around **100k+ tokens**, do not begin another broad read/test/debug cycle before compacting;
- treat **120k active context as an exception**, not a normal target.

The point is to reduce repeated re-sending of old tool/file output before expensive final validation and amendment cycles.

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

### Default controlling-file budget

For an ordinary implementation slice, begin with a small controlling set rather than broad context loading:

1. `CLAUDE.md` (normally preloaded);
2. the assigned primary slice document;
3. its normative spec(s);
4. `docs/engineering/IMPLEMENTATION_CONTEXT_INDEX.md` only when a stable cross-cutting boundary needs a compact reminder;
5. the concrete production modules/tests required by the task.

A typical start should need roughly 3–7 controlling documents/files before code work begins. This is a routing target, not permission to skip a file the slice explicitly requires.

Broader documents are demand-loaded only when a concrete question, conflict, trigger, or stop condition requires them.


The assigned slice is the primary execution entry point.

Claude MUST read:

1. `CLAUDE.md` (normally loaded as repository instructions);
2. the assigned primary `docs/slices/SLICE-XXXX-*.md` contract;
3. only the controlling specs/ADRs/protocols/files explicitly named by that slice or required to resolve a concrete implementation question;
4. `docs/engineering/AI_SLICE_WORKFLOW.md` only when workflow/ownership behavior is relevant or unclear.

Claude SHOULD NOT preload the full project history, ROADMAP, PROJECT_STATE, OPEN_QUESTIONS, REQUIREMENTS, slice INDEX, or unrelated architecture documents merely for orientation when the assigned slice does not require them.

If the slice references a requirement ID, read the relevant section/range rather than loading unrelated requirements when practical.

If a local synchronized checkout already contains a file, do not repeatedly fetch the same file through GitHub/API tooling.

## Research cold-context policy

The entire `research/` tree is demand-load only by default.

- Do not enumerate/read research artifacts merely because they exist.
- If research becomes necessary, read `research/CONTEXT_INDEX.md` first.
- Start with the relevant human-readable report/summary.
- Treat large JSON/manifests/raw observations as deep-cold generated evidence: query narrowly or replay mechanically; never preload them into context.
- An implementation slice that does not touch research-derived semantics/source/provenance should normally read **zero** research files.
- A slice naming one research artifact does not authorize loading neighboring research directories.

## Search/read discipline

### Read-once / narrow-reread rule

Once a large file has been read and remains unchanged in the same session, do not reopen it in full. Use Grep plus a bounded Read range for the exact symbol/section needed.

Before any broad file read, ask whether a path/symbol search can identify the relevant range first.

Prefer targeted search and narrow reads over whole-file reads when a file is large and only one symbol/section is needed.

### Diff discipline

Never dump a large whole-branch diff into context merely to inspect what changed.

Use this order:

1. `git diff --stat` / changed-file list;
2. path-scoped diff for the file currently under review;
3. hunk/symbol-level inspection where possible.

Do not print generated lockfiles, large fixtures, manifests, or unchanged-context diff hunks unless a concrete finding requires them.

### Tool-output discipline

Tool output is context.

- prefer quiet/summary modes when they preserve pass/fail evidence;
- do not print full successful test logs;
- do not paste successful build/install logs into the final report;
- on failure, inspect the bounded failure summary first and expand only the relevant failing section;
- avoid commands whose only purpose is to print data already available from a prior tool result;
- keep exact full logs on disk when useful for diagnosis rather than keeping them in model context.

For PostgreSQL-backed Python validation through `claude_diag.py`, prefer:

```text
uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/run_pytest_local.py ...
```

The compact mode executes the same test command and retains the complete combined log in a temporary file, but emits only a bounded tail to model context. If a failure needs deeper inspection, open only the relevant full-log region.

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

## Validation cadence

Use a two-level validation cadence unless the slice contract requires something stricter.

### Iteration / intermediate amendment

Prefer:

- focused unit/persistence/web tests for changed behavior;
- repository validator when governance/docs changed;
- ruff/mypy/typecheck/build only when the changed surface warrants them;
- retained proof directly owned by the changed invariant.

Do **not** rerun the entire PostgreSQL/web/full-repository suite after every small amendment merely to reproduce the same evidence.

### Final candidate handoff

The default final-candidate ownership is split:

- **locally:** run focused/affected unit, persistence, web, static and slice-owned proof validation needed to establish that the candidate is sensible to push;
- **remotely on the exact pushed HEAD:** GitHub Actions owns the complete regression, PostgreSQL integration, aggregate coverage, cross-platform, web, dependency/security and required retained-gate confirmation.

Do **not** run the complete local backend suite merely because a candidate or amendment is ready for handoff. The remote exact-head full regression is the authoritative broad final gate.

A local complete regression is exceptional and requires a concrete reason: the task changes the test/CI/collection/coverage/migration/isolation machinery itself, a remote failure needs broad local reproduction, or an explicit local-only acceptance proof cannot be provided by CI.

For amendments, the default is focused local validation → push → authoritative remote regression. Multiple amendments do not justify repeated 38–45 minute local full-suite runs.

If an amendment materially touches identity, authorization, transactionality, migration state, Search semantics, or public eligibility, expand the focused local set appropriately; that still does not automatically require all ~5,900 tests locally.

This changes execution ownership, not the final acceptance bar.

## Completion-report discipline

The required `SLICE_TEMPLATE.md` report remains mandatory, but it must be concise.

The normal completion-report target is one screen/page. It may exceed that only when needed to explain a blocker, ambiguity, scope deviation, or unverified acceptance condition.

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

## Review discipline

Independent implementation review is **delta-first by default**.

Review order:

1. readiness base / previous reviewed HEAD → exact candidate HEAD;
2. changed-file list and diff;
3. affected invariants using the review matrix in `IMPLEMENTATION_CONTEXT_INDEX.md`;
4. unchanged surrounding implementation only where needed to validate the delta;
5. broad repository/history only when a material conflict, regression, or missing accepted obligation is plausible.

Do not re-read large unchanged files merely because they were important in the original readiness phase.

A full-state reread remains appropriate when the candidate changes a foundational identity/auth/data/architecture boundary, when the base is uncertain, or when review evidence indicates drift.

## Review/amendment discipline

When an independent review returns an amendment:

- continue in the same slice session if context remains modest;
- otherwise `/compact` before applying the amendment;
- preserve the exact reviewed HEAD, amendment requirements, affected files and required validation;
- compare previous reviewed HEAD → new HEAD first;
- inspect only the amendment delta plus directly affected invariants unless the delta crosses a new material boundary;
- use focused validation during intermediate amendment rounds and require the contract's complete validation on the final candidate HEAD;
- do not reload unrelated project background.

After the slice reaches final handoff, stop. The next slice uses a fresh session.

## Context target

There is no absolute hard context threshold because task complexity varies. Operationally:

- **target active context:** below roughly 80–100k for normal continuing work;
- at ~80k+, plan compaction at the next safe phase boundary;
- at ~100k+, compact before another broad implementation/debug/validation cycle;
- ~120k+ should be exceptional and justified by work that cannot safely be compacted yet;
- do not allow 150k+ to become normal;
- always consider a compact checkpoint before final full-suite validation on a large vertical slice;
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

## SLICE-0073 throughput optimization

Post-SLICE-0072, the owner-directed earliest-safe optimization is selected as SLICE-0073. Its controlling contract is `specs/TEST_CI_THROUGHPUT_OPTIMIZATION.v0.1.md`. The implementation must reduce wall-clock and repeated validation/token cost through measured grouping, safe PostgreSQL isolation/parallelism and removal of redundant execution without weakening the final acceptance bar.
