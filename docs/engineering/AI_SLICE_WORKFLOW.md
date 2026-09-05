# HullQ AI Slice Workflow

## User workflow

For normal slice work the project owner should not need to manage Git branches manually.

### One-time setup

After this workflow is first merged to `main`:

1. synchronize the normal HullQ folder once;
2. double-click `SETUP_WORKFLOW.bat`;
3. if GitHub CLI asks for setup/authentication, complete that once and run the BAT again.

The setup is idempotent: running it again updates the same `HullQ main protection` ruleset rather than creating a new workflow.

The GitHub ruleset protects `main` by requiring a pull request, the existing Ubuntu/Windows/dependency-audit checks, an up-to-date branch, linear history, and by blocking force-push/deletion. It deliberately requires zero formal GitHub approvals because project-owner acceptance and independent AI review are tracked by the HullQ slice workflow rather than a second GitHub account.

### Readiness handoff invariant

A readiness document merged to `main` for the current queue must already be directly consumable by `START_SLICE`.

The primary queued slice document therefore MUST use the canonical `SLICE_TEMPLATE.md` header vocabulary, in particular:

```text
**Type:** BOOTSTRAP | DESIGN_RESEARCH | IMPLEMENTATION | VALIDATION
**Status:** READY
```

Do not merge a queued implementation document with transitional header values such as `IMPLEMENTATION READINESS` or `READY_FOR_REVIEW`. Review state belongs to the readiness PR/review process; the artifact merged to `main` is the final authorized `READY` implementation contract.

`scripts/validate_repository.py` mechanically validates this for the current `PROJECT_STATE_QUEUE_SLICE` whenever a queue document exists. It mirrors the `START_SLICE` primary-document header rules and post-SLICE-0038 product checks, so an unstartable readiness artifact must fail CI before merge rather than fail later on the project owner's machine.

### Start a slice

1. Double-click `START_SLICE.bat` in the normal HullQ folder.
2. Enter the slice number, for example `0005`.
3. The script synchronizes local `main` with `origin/main`, creates/reuses an isolated Git worktree and slice branch, and copies the Claude Code instruction to the clipboard.
4. The script deliberately does **not** open, close, reload, or switch any VS Code window.
5. Explicitly open the sibling worktree (for example `HullQ-slice-0005`) in the VS Code window that should host Claude Code.
6. Start a **fresh Claude conversation**. If reusing the current Claude Code session/UI, run `/clear` first.
7. Paste only the copied START_SLICE instruction. Do not paste the previous slice report/history unless the new slice explicitly requires it.

The normal HullQ folder stays on `main`. Claude works in a sibling folder such as `HullQ-slice-0005`.

Why VS Code opening is manual: Claude Code UI/session state can be tied to the current VS Code workspace. Automatically reusing a window can replace the current workspace and interrupt an existing Claude session; automatically opening a second window may also be unwanted. The workflow therefore prepares Git state only and leaves the UI decision to the project owner.

### Token/context discipline during a slice

HullQ uses one Claude session per slice by default.

- Use `/context` when it is useful to see what is consuming context.
- If the same slice becomes large, use `/compact` before continuing rather than carrying excessive exploratory history/logs through every subsequent turn.
- A useful compact instruction preserves the controlling slice, decisions already made, changed files/current implementation state, validation/CI state, unresolved blockers and exact handoff requirements.
- Do **not** `/clear` casually mid-slice; it is primarily a slice/task-boundary command.
- Do not ask Claude to reread full project history merely for reassurance. The controlling slice identifies the required dependencies.

Detailed rules: `docs/engineering/AI_TOKEN_EFFICIENCY.md`.

### Review and amendments

Independent review happens after Claude's pushed handoff.

If an amendment is required:

- continue in the same slice branch;
- if the Claude context is already large, run `/compact` before pasting the amendment;
- do not reload previous project background that is unrelated to the finding;
- Claude applies only the requested amendment plus necessary tests/validation and reports a new exact HEAD.

### Acceptance closure and PROJECT_STATE freshness

The acceptance closure is not complete until `docs/PROJECT_STATE.md` reflects the newly accepted slice.

Every closure that creates a new highest `SLICE-XXXX-acceptance-closure.md` MUST, in the same closure change:

1. update the `PROJECT_STATE_ACCEPTED_SLICE` marker to that exact slice number;
2. update the human-readable latest accepted/current queue text;
3. keep the file compact by replacing stale current-state prose rather than appending another historical report;
4. update the near-term product-execution path when the accepted slice changes the route to the first visible listing.

`scripts/validate_repository.py` mechanically compares the `PROJECT_STATE_ACCEPTED_SLICE` marker with the highest acceptance-closure filename. A stale or ahead-of-history state document fails repository validation and therefore CI.

At every post-slice reassessment, explicitly record the estimated remaining slice distance to the first externally visible listing. Any proposed foundation-only slice must explain why it cannot safely be deferred until after that visible vertical slice.

### Finish a slice

Only after the slice PR has been merged, explicit owner acceptance has been recorded, and the separate closure is complete:

1. Double-click `FINISH_SLICE.bat`.
2. Enter the slice number.

The script synchronizes local `main`. If GitHub CLI can confirm that the slice PR was merged and the worktree is clean, it also removes the old worktree and local slice branch. If merge status cannot be confirmed, nothing is deleted.

After finishing, the next slice starts with a fresh Claude conversation; do not carry the completed slice chat forward.

## Single-writer rules

- `origin/main` is canonical truth.
- Claude writes only the currently assigned `slice/...` branch/worktree.
- The master/architect does not write Claude's branch.
- Claude does not write `main`, `master/...`, `review/...`, or another agent's branch.
- While Claude is implementing an active slice, `main` is treated as frozen except for a deliberate blocker-resolution workflow.
- Future architecture/spec work may be prepared on a separate `master/...` or docs/maintenance branch but is not merged while the implementation slice is active.
- Review findings go back to Claude; Claude fixes them on the same slice branch.
- All implementation reaches `main` through PR, required CI, independent review, explicit project-owner acceptance, and closure.
- Never use `git pull origin main` from a feature branch merely to update local `main`.
- Never use an old slice worktree as the base for the next slice.

## Safety

The helper scripts are intentionally fail-safe:

- they refuse to start from a dirty main checkout;
- they use `git pull --ff-only` for local main;
- they never push or merge to `main`;
- `START_SLICE.bat` never manipulates VS Code windows;
- the finish script does not delete a worktree with substantive uncommitted changes;
- cleanup is skipped unless a merged PR can be confirmed through GitHub CLI;
- the setup script verifies the canonical repository before changing GitHub rules;
- the setup script creates/updates one named ruleset and does not touch source files or branches.
