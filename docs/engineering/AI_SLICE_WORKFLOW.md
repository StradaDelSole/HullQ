# HullQ AI Slice Workflow

## User workflow

For normal slice work the project owner should not need to manage Git branches manually.

### Start a slice

1. Double-click `START_SLICE.bat` in the normal HullQ folder.
2. Enter the slice number, for example `0005`.
3. The script synchronizes local `main` with `origin/main`, creates/reuses an isolated Git worktree and slice branch, opens that worktree in VS Code, and copies the Claude Code instruction to the clipboard.
4. Paste the copied instruction into Claude Code.

The normal HullQ folder stays on `main`. Claude works in a sibling folder such as `HullQ-slice-0005`.

### Finish a slice

Only after the slice PR has been merged:

1. Double-click `FINISH_SLICE.bat`.
2. Enter the slice number.

The script synchronizes local `main`. If GitHub CLI can confirm that the slice PR was merged and the worktree is clean, it also removes the old worktree and local slice branch. If merge status cannot be confirmed, nothing is deleted.

## Single-writer rules

- `origin/main` is canonical truth.
- Claude writes only the currently assigned `slice/...` branch/worktree.
- The master/architect does not write Claude's branch.
- While Claude is implementing an active slice, `main` is treated as frozen except for a deliberate blocker-resolution workflow.
- All implementation reaches `main` through review/CI/project-owner acceptance.
- Never use `git pull origin main` from a feature branch merely to update local `main`.

## Safety

The helper scripts are intentionally fail-safe:

- they refuse to start from a dirty main checkout;
- they use `git pull --ff-only` for local main;
- they never push or merge to `main`;
- the finish script does not delete a worktree with uncommitted changes;
- cleanup is skipped unless a merged PR can be confirmed through GitHub CLI.
