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

### Start a slice

1. Double-click `START_SLICE.bat` in the normal HullQ folder.
2. Enter the slice number, for example `0005`.
3. The script synchronizes local `main` with `origin/main`, creates/reuses an isolated Git worktree and slice branch, and copies the Claude Code instruction to the clipboard.
4. The script deliberately does **not** open, close, reload, or switch any VS Code window.
5. When ready, explicitly open the sibling worktree (for example `HullQ-slice-0005`) in the VS Code window that should host Claude Code, then paste the copied instruction.

The normal HullQ folder stays on `main`. Claude works in a sibling folder such as `HullQ-slice-0005`.

Why VS Code opening is manual: Claude Code UI/session state can be tied to the current VS Code workspace. Automatically reusing a window can replace the current workspace and interrupt an existing Claude session; automatically opening a second window may also be unwanted. The workflow therefore prepares Git state only and leaves the UI decision to the project owner.

### Finish a slice

Only after the slice PR has been merged:

1. Double-click `FINISH_SLICE.bat`.
2. Enter the slice number.

The script synchronizes local `main`. If GitHub CLI can confirm that the slice PR was merged and the worktree is clean, it also removes the old worktree and local slice branch. If merge status cannot be confirmed, nothing is deleted.

## Single-writer rules

- `origin/main` is canonical truth.
- Claude writes only the currently assigned `slice/...` branch/worktree.
- The master/architect does not write Claude's branch.
- Claude does not write `main`, `master/...`, `review/...`, or another agent's branch.
- While Claude is implementing an active slice, `main` is treated as frozen except for a deliberate blocker-resolution workflow.
- Future architecture/spec work may be prepared on a separate `master/...` branch but is not merged while the implementation slice is active.
- Review findings go back to Claude; Claude fixes them on the same slice branch.
- All implementation reaches `main` through PR, required CI, independent review, and project-owner acceptance.
- Never use `git pull origin main` from a feature branch merely to update local `main`.
- Never use an old slice worktree as the base for the next slice.

## Safety

The helper scripts are intentionally fail-safe:

- they refuse to start from a dirty main checkout;
- they use `git pull --ff-only` for local main;
- they never push or merge to `main`;
- `START_SLICE.bat` never manipulates VS Code windows;
- the finish script does not delete a worktree with uncommitted changes;
- cleanup is skipped unless a merged PR can be confirmed through GitHub CLI;
- the setup script verifies the canonical repository before changing GitHub rules;
- the setup script creates/updates one named ruleset and does not touch source files or branches.
