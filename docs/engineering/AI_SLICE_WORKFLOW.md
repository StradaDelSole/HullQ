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

### Pre-decision reconciliation invariant

Before a new product/domain/data/architecture question is put to the Project Owner, before a new slice capability is selected, or before an accepted behavior is challenged, the project master/reviewer MUST perform the repository reconciliation defined in:

```text
docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md
```

The check is against canonical `origin/main`, not conversation memory alone, and it must cover both:

- accepted decision records/specs/ADRs/governance/slice closures; and
- relevant existing production code/tests/migrations.

The result must classify the material point as already decided+implemented, decided+not-yet-implemented, explicitly deferred, genuinely open, or conflict/regression.

Hard:

```text
already decided + implemented
→ must not be presented as a new owner decision

already decided + not yet implemented
→ implementation gap, not re-decision
```

From `SLICE-0051` onward this is mechanically surfaced in the slice contract through:

```text
**REPOSITORY RECONCILIATION CHECK:** PASS
## Decision / implementation reconciliation
```

Both `START_SLICE` and repository validation reject a queued 0051+ slice that lacks these markers.

### Post-SLICE-0051 trigger-gate invariant

From SLICE-0052 onward every capability-selection/readiness pass must also read:

```text
docs/governance/POST_0051_TRIGGER_GATES.md
docs/governance/PRODUCTION_READINESS_GATE.md
```

and every primary queued slice must contain:

```text
**TRIGGER GATES CHECK:** PASS
## Trigger gates
```

The trigger section must carry the exact machine-checked evidence fields defined by `docs/slices/SLICE_TEMPLATE.md`.

The four controlling triggers are:

1. architecture/current-state reconciliation must remain PASS before SLICE-0052+ readiness;
2. Production Readiness must be PASS before real external broker data is stored/relied upon as HullQ production data, before the first real external production pilot, or before public production launch, whichever comes first;
3. technical native Search criterion #2 must explicitly compare its bridge/path to SLICE-0051, and criterion #3+ may not create a third structural copy without the abstraction guard PASS;
4. the post-SLICE-0056 workflow reassessment must remain `PASS`; the accepted result is recorded in `docs/POST_SLICE_0056_WORKFLOW_REASSESSMENT_2026-09-18.md`.

The repository validator enforces deterministic marker/state relationships. Independent readiness review must still verify that the claimed comparison, generalization/distinction and readiness evidence are substantively true.

The older accepted database HA minimum remains separately hard: before real external broker inventory is exposed to real external buyers, production PostgreSQL must have automatic failover with at least one standby.

`START_SLICE` runs repository governance validation for SLICE-0052+ before creating/reusing a slice worktree, and separately verifies the required trigger marker/section. A triggered gate therefore cannot be bypassed merely by writing `READY` into a slice document.

The trigger gates constrain execution; they do not select the next capability and do not authorize speculative foundation work.

### Readiness handoff invariant

A readiness document merged to `main` for the current queue must already be directly consumable by `START_SLICE`.

The primary queued slice document therefore MUST use the canonical `SLICE_TEMPLATE.md` header vocabulary, in particular:

```text
**Type:** BOOTSTRAP | DESIGN_RESEARCH | IMPLEMENTATION | VALIDATION
**Status:** READY
```

Do not merge a queued implementation document with transitional readiness header values such as `IMPLEMENTATION READINESS` or `READY_FOR_REVIEW`. Review state belongs to the readiness PR/review process; the artifact merged to `main` is the final authorized `READY` implementation contract.

Once `START_SLICE` has created the actual slice branch and the implementation agent reaches a handoff, that same primary document may legitimately move from `READY` to `REVIEW` or `BLOCKED` while `PROJECT_STATE_QUEUE_SLICE` still points at the active slice. In that case the document MUST contain the matching explicit execution-handoff line:

```text
**Status set by this handoff:** `REVIEW`
```

or:

```text
**Status set by this handoff:** `BLOCKED`
```

This line distinguishes a real implementation handoff from a malformed readiness artifact. A queued `REVIEW`/`BLOCKED` document without the matching handoff line fails repository validation. `READY_FOR_REVIEW` remains invalid everywhere.

`scripts/validate_repository.py` mechanically validates this for the current `PROJECT_STATE_QUEUE_SLICE` whenever a queue document exists. Before execution it mirrors the `START_SLICE` primary-document header rules and post-SLICE-0038 product checks; from SLICE-0051 onward it also requires the repository-reconciliation PASS marker/section, and from SLICE-0052 onward it requires the trigger-gates PASS marker/section and validates the canonical trigger state. After an explicit implementation handoff it permits only the tightly marked `REVIEW`/`BLOCKED` states above. This ensures an unstartable readiness artifact fails CI before merge without blocking the normal implementation-review lifecycle.

### Post-SLICE-0079 mechanical-invariant readiness rule

From SLICE-0080 onward, every primary readiness contract must contain the `MECHANICAL INVARIANTS / FAILURE MODES CHECK` and `## Mechanical invariants / failure modes` section defined by `docs/slices/SLICE_TEMPLATE.md`.

This rule exists because SLICE-0079 showed that high-level acceptance phrases such as “immutable images”, “controlled rollback”, “replaceable host” or “fail closed” are not precise enough by themselves. Readiness must translate those goals into mechanical invariants before implementation starts.

For `HIGH_RISK` work, readiness must explicitly answer all of the following:

- what state/identity must never silently change once established;
- which source is authoritative and which state must survive loss of a process, cache, local file or replaceable host;
- what retries, reruns, replays, duplicate requests, partial successes, rollbacks and concurrent attempts are allowed to do;
- how confirmed absence is distinguished from network/auth/timeout/parse/provider failure before any mutation is authorized;
- which failures must fail closed;
- which negative cases require executable proof rather than static review or documentation;
- whether the proposed slice is still one coherent capability or actually multiple independently testable failure domains.

A shared umbrella such as “production readiness”, “security hardening” or “launch gate” does not itself satisfy the one-capability rule. If deploy/rollback, backup/restore, observability/alerting, identity/durability and another independently useful subsystem can each be implemented and accepted separately, readiness should split them unless separation would make the observable outcome unusable or unsafe.

Repository validation and `START_SLICE` enforce the presence and basic shape of this section for SLICE-0080+, but independent readiness review remains responsible for judging whether the invariants are actually complete and whether `ORDINARY` / `NOT_APPLICABLE` is honest.

Before a `HIGH_RISK` implementation is handed to independent review, the implementation agent must perform one adversarial self-review against the readiness failure model. At minimum, re-check applicable retry/rerun/replay, partial-failure, stale/concurrent-state, dependency-unavailable/auth/timeout, confirmed-absence-vs-error, replaceable-host/cache-loss and rollback/recovery paths. Evidence claims must state what was actually executed; intended configuration, vendor documentation or an unrun harness is not execution proof.

Independent exact-head review should then re-run that same failure model rather than merely checking that the happy path and acceptance checklist are present.

### Production go-live staging invariant

The Project Owner accepted the staged operator procedure in `docs/operations/PRODUCTION_LAUNCH_PACK.md` on 2026-10-08.

HullQ production go-live is not a big-bang cutover. The required phase order is:

```text
1. Accounts & Ownership
2. Secrets & Connections
3. Closed Production Infrastructure
4. Closed HullQ Production Deploy
5. Internal Real Operation
6. Bounded External Broker Pilot
7. Public Production Launch
```

Any readiness/reassessment or operator action that would advance HullQ into a later production phase MUST reconcile against that launch pack and the canonical Production Readiness Gate first. A successful deploy, provider account creation, DNS change, database creation or pilot does not implicitly authorize the next phase.

Production setup should be executed one provider/dependency at a time with an explicit done-when test and `PASS` / `BLOCKED` outcome. Secret values never belong in the launch pack or repository documentation; only secret names, purpose and destination secret store may be recorded.

`docs/PROJECT_STATE.md` carries the canonical machine-readable `PRODUCTION_LAUNCH_PACK_PHASE`. A production-phase slice from SLICE-0080 onward must declare that exact current value as its `Launch-pack phase before this slice`; repository validation rejects a stale/fabricated before-phase, backwards movement or a skip of more than one phase. If an accepted slice advances the phase, its acceptance closure must update the canonical marker atomically to the slice contract's `phase after` value. Pure provider-console execution outside a slice may advance the marker only through a separately reviewed repository maintenance change after the phase's defined done-when evidence is complete.

If launch execution uncovers a new product/domain/data/architecture decision, stop and route it back through the normal HullQ reconciliation/readiness/slice lifecycle. Pure provider-console provisioning of already-accepted configuration may remain an operator-checklist action, but evidence required by the controlling gate/runbook must still be retained.

### Start a slice

1. Double-click `START_SLICE.bat` in the normal HullQ folder.
2. Enter the slice number, for example `0005`.
3. The script synchronizes local `main` with `origin/main`, validates the applicable governance/readiness gates, creates/reuses an isolated Git worktree and slice branch, and copies the Claude Code instruction to the clipboard.
4. The script deliberately does **not** open, close, reload, or switch any VS Code window.
5. Explicitly open the sibling worktree (for example `HullQ-slice-0005`) in the VS Code window that should host Claude Code.
6. Start a **fresh Claude conversation**. If reusing the current Claude Code session/UI, run `/clear` first.
7. Paste only the copied START_SLICE instruction. Do not paste the previous slice report/history unless the new slice explicitly requires it.

The normal HullQ folder stays on `main`. Claude works in a sibling folder such as `HullQ-slice-0005`.

Why VS Code opening is manual: Claude Code UI/session state can be tied to the current VS Code workspace. Automatically reusing a window can replace the current workspace and interrupt an existing Claude session; automatically opening a second window may also be unwanted. The workflow therefore prepares Git state only and leaves the UI decision to the project owner.

### Approval-autonomy guard

Routine Claude Code work must not require the Project Owner to watch the session for avoidable permission popups.

HullQ therefore uses a project-level mechanical approval guard in addition to prompt guidance:

```text
.claude/settings.json
→ PreToolUse(Bash|PowerShell)
→ scripts/workflow/claude_command_guard.py
→ malformed routine shell composition is denied before permission UI
→ Claude receives a rewrite reason and retries with standalone calls

PermissionRequest(Bash|PowerShell)
→ the same guard
→ bounded routine command families are auto-allowed
→ destructive / privileged / explicitly operator-gated commands remain on normal permission flow
```

The PreToolUse guard rejects routine commands containing shell composition that commonly defeats static permission analysis, including shell/environment-variable expansion, command substitution, loops/control flow, pipes, redirects, subshells and compound separators. This is not a product/security-policy decision and must not be bypassed by spelling the same routine diagnostic differently. Claude should split the operation into separate tool calls, use `Read`/`Grep`/`Glob` for file inspection, `uv run python ...` for Python and standalone npm commands such as `npm ci --prefix web`.

Recurring local diagnostics have a repository-owned helper, `scripts/workflow/claude_diag.py`, so agents do not rebuild environment-prefix commands or PowerShell pipelines. It provides secret-safe environment status, TCP reachability, newest-temp-directory lookup, local PostgreSQL test-script execution, and a bounded local API smoke launcher. Fixed local test credentials/signing values are injected only into child processes and are never printed.

The PermissionRequest hook auto-allows only bounded routine families already intended for autonomous HullQ development. It does not auto-allow destructive Git recovery, force-push/main-push, branch deletion, Alembic downgrade, destructive Docker-volume teardown or other deliberately operator-gated actions.

`scripts/validate_repository.py` validates the hook wiring and required shared permission rules. Since `START_SLICE` runs repository validation for current post-0051 slices, future slice start is blocked if this approval-autonomy mechanism is missing or regresses.

This guard complements rather than replaces the shared `allow` / `ask` / `deny` policy. The goal is:

```text
routine implementation / inspection / tests
→ autonomous

destructive / privileged / policy-sensitive action
→ explicit operator approval
```

### Token/context discipline during a slice

HullQ uses one Claude session per slice by default.

- Use `/context` when it is useful to see what is consuming context.
- If the same slice becomes large, use `/compact` before continuing rather than carrying excessive exploratory history/logs through every subsequent turn.
- A useful compact instruction preserves the controlling slice, decisions already made, changed files/current implementation state, validation/CI state, unresolved blockers and exact handoff requirements.
- Do **not** `/clear` casually mid-slice; it is primarily a slice/task-boundary command.
- Do not ask Claude to reread full project history merely for reassurance. The controlling slice identifies the required dependencies and records the readiness reconciliation/trigger-gate state.

Detailed rules: `docs/engineering/AI_TOKEN_EFFICIENCY.md`. Stable cross-cutting engineering boundaries are indexed compactly in `docs/engineering/IMPLEMENTATION_CONTEXT_INDEX.md`; it is a routing aid, not a normative substitute for the assigned slice/spec.

### Review and amendments

Independent review happens after Claude's pushed handoff.

If an amendment is required:

- continue in the same slice branch;
- if the Claude context is already large, run `/compact` before pasting the amendment;
- do not reload previous project background that is unrelated to the finding;
- compare the previous reviewed HEAD to the amended HEAD first;
- Claude applies only the requested amendment plus necessary tests/validation and reports a new exact HEAD using the compact amendment report from `SLICE_TEMPLATE.md`;
- use focused validation during intermediate amendment rounds; require the slice's complete validation on the final candidate HEAD unless the contract or risk boundary requires it earlier.

Independent review must compare implementation not only with the immediate slice text but with the accepted semantics named by the reconciliation and trigger-gate records. A regression from previously accepted/implemented behavior is a review defect, not a new design choice. For SLICE-0080+ `HIGH_RISK` work, review must also explicitly traverse the readiness contract's mechanical invariants/failure modes and look for second-order failures caused by retry, partial completion, host/cache loss, external dependency errors and ambiguous absence detection.

#### Post-SLICE-0056 risk-focused review depth

The evidence-based workflow reassessment in `docs/POST_SLICE_0056_WORKFLOW_REASSESSMENT_2026-09-18.md` found material independent-review defects in every accepted SLICE-0051 through SLICE-0056 implementation slice. Therefore no generic lighter primary `IMPLEMENTATION` lifecycle is authorized.

Review depth is focused by the invariant touched rather than by file extension:

- persistence/migrations/concurrency, auth/session/MFA/CSRF/authorization, identity/ownership/trust/publication, Search semantics/evidence/canonicalization/ranking, payments and production-data/operations are critical boundaries and require cross-boundary review plus appropriate retained proof;
- browser/API projection, public validation/error behavior, canonical/indexability behavior and buyer/seller copy that assigns truth/lifecycle semantics remain exact-head review territory, but review should stay focused on the changed vertical plus the accepted invariant being projected;
- pure non-runtime documentation/mechanical maintenance may receive a targeted exact-head review when it genuinely changes no product/runtime/security/CI semantics. Workflow hooks, CI behavior, permission/security policy and required-check topology are not low-risk merely because they live in docs/config/scripts.

For a bounded same-slice amendment, re-review is **delta-first**:

1. compare the previous reviewed exact HEAD with the amended exact HEAD;
2. inspect every amendment change;
3. re-check every invariant materially affected by those changes;
4. verify no unrelated scope entered the branch;
5. require the final exact-head remote gates.

Do not restart an unrelated whole-repository review unless the amendment broadens scope or touches a new material boundary.

Primary implementation review is also delta-first by default: inspect readiness-base → candidate diff, map the changed surfaces to scope/auth/identity/persistence/concurrency/failure/privacy/API-UI/public-Search/governance invariants, and open unchanged surrounding files only where the delta depends on them. Broad repository rereads are reserved for uncertain bases, foundational boundary changes, or evidence of drift.

### Reviewer continuation to owner-acceptance boundary

After an independent implementation review finds the exact slice HEAD materially acceptable, the reviewer/project master MUST continue the workflow autonomously through the remaining non-owner gates rather than handing routine monitoring back to the Project Owner.

Normal continuation is:

1. create or verify the implementation pull request for the exact reviewed HEAD;
2. observe all required remote/external checks on that exact HEAD;
3. if a check fails, investigate it and either return a targeted same-slice amendment/blocker or re-run only when the failure is demonstrably transient;
4. re-verify that the PR head SHA remains the reviewed SHA and that the PR remains mergeable/up-to-date as required;
5. only then hand control to the Project Owner when explicit owner acceptance is the next mandatory action.

Do not interrupt the Project Owner merely because CI is queued/in progress or because another routine reviewer-controlled step remains. Stop earlier only for a genuine blocker, a material new review finding, an authorization/access boundary, or an action that explicitly requires Project Owner approval.

The intended handoff label is:

```text
OWNER ACCEPTANCE READY
```

At that point report the exact accepted implementation HEAD, implementation PR, independent review result and exact-head external-gate result, then request the Project Owner's explicit acceptance. Do not merge merely because the implementation is technically ready; owner acceptance remains a separate mandatory gate.

### Post-Owner-Acceptance continuation — ChatGPT project master owns closure

**Binding Owner decision (2026-10-28, SLICE-0094 onward):** As soon as the Project Owner explicitly accepts an independently reviewed implementation/research slice, **ChatGPT in the project master/reviewer role owns the entire remaining remote workflow**. The Owner MUST NOT have to ask anew in each chat or relay a separate closure-review request to Claude. The project master must continue until the **only remaining next action is the Owner's local `FINISH_SLICE.bat`**.

The sequence is mandatory:

1. Reconfirm that the Owner accepted the **exact** reviewed implementation HEAD and verify the required exact-HEAD external gates; merge the implementation PR via the usual protected PR route (never direct-push `main`). If a head changes or a check fails, resolve/review the new exact HEAD before merging.
2. Create the separate **docs-only Owner acceptance-closure branch/PR**. Reconcile the accepted implementation, immutable review trail, formal closure, `docs/PROJECT_STATE.md`, technical-criteria/gate markers and compact `docs/slices/INDEX.md` in the same PR. Do not secretly activate production or select the next slice.
3. **ChatGPT project master/reviewer itself reviews the closure PR** against the actual accepted merge, normative specs and governance, inspects the complete exact-HEAD diff, corrects inaccuracies on the docs-only branch and re-reviews any changed HEAD. Do **not** delegate this closure review or closure paperwork to Claude. A reviewer who also authored the docs must describe the check as a source-based self-review, not falsely claim a second independent human/agent reviewed it. This does **not** weaken the pre-acceptance independent review of Claude's implementation, which remains mandatory.
4. Monitor the closure PR's **own exact-HEAD six-job CI, manufacturer reproducibility and applicable Deploy checks**. If checks fail, diagnose/remediate and rerun on the new exact HEAD where needed. **Do not merge before all required gates are successful.** If a genuine blocker or missing authorization prevents progress, report that specific blocker rather than declaring closure complete.
5. Squash-merge the docs-only closure PR when its review and remote gates pass; verify the actual resulting `origin/main` merge SHA and canonical accepted/queue markers. Record the result.
6. **Only then hand back to the Owner** with the single next task: run the unchanged local `FINISH_SLICE.bat` and enter that slice's number; ask for the actual command output. The Owner alone performs this Windows/local worktree operation. No new slice is selected/started and no local FINISH success is claimed before the Owner's output.

**Division of responsibilities:** Claude Code = assigned slice implementation and targeted amendments only. ChatGPT project master/reviewer = independent implementation review through Owner acceptance; **after explicit Owner acceptance, merge, documentation, closure review, monitoring, closure PR merge and final FINISH handoff**. Project Owner = explicit implementation acceptance and local `START_SLICE.bat`/`FINISH_SLICE.bat` operations. These are separate boundaries. Do not stop halfway to give the Owner a Claude closure-review prompt or ask the Owner to track routine CI.

The durable reference for new ChatGPT conversations is this section, plus `CLAUDE.md`, `docs/PROJECT_STATE.md` and `docs/slices/INDEX.md`. Treat this Owner assignment as continuing by default unless a later explicit Owner direction changes it.

### Acceptance closure and PROJECT_STATE freshness

The acceptance closure is not complete until `docs/PROJECT_STATE.md` reflects the newly accepted slice.

Every closure that creates a new highest `SLICE-XXXX-acceptance-closure.md` MUST, in the same closure change:

1. update the `PROJECT_STATE_ACCEPTED_SLICE` marker to that exact slice number;
2. update the human-readable latest accepted/current queue text;
3. keep the file compact by replacing stale current-state prose rather than appending another historical report;
4. update the near-term product-execution path when the accepted slice changes the route to the first visible listing;
5. update `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` in `POST_0051_TRIGGER_GATES.md` if and only if the accepted slice actually added another hard technical native-inventory Search criterion;
6. if the accepted slice makes the workflow reassessment due, ensure the canonical workflow-reassessment state is no longer invalidly `NOT_DUE`.
7. if the accepted slice's `PRODUCTION LAUNCH PACK CHECK` is `PASS` and its declared `phase after` differs from the canonical `PRODUCTION_LAUNCH_PACK_PHASE`, update that marker atomically to the accepted `phase after` only after the phase's done-when evidence is satisfied.

`scripts/validate_repository.py` mechanically compares the `PROJECT_STATE_ACCEPTED_SLICE` marker with the highest acceptance-closure filename. A stale or ahead-of-history state document fails repository validation and therefore CI.

At every post-slice reassessment, explicitly record the estimated remaining slice distance to the first externally visible listing. Any proposed foundation-only slice must explain why it cannot safely be deferred until after that visible vertical slice.

The same reassessment must apply `DECISION_IMPLEMENTATION_RECONCILIATION.md` and the post-0051 trigger gates: accepted implementation obligations discovered during the check must be identified as implemented, concretely owned by queued/active work, or explicitly deferred, and any due trigger must be satisfied before readiness. They may not silently disappear from planning.

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
- from SLICE-0051 onward `START_SLICE` refuses to start a slice without the repository-reconciliation PASS marker and reconciliation section;
- from SLICE-0052 onward `START_SLICE` also runs repository trigger validation and refuses to start without the trigger-gates PASS marker/section;
- real external broker production data cannot become ACTIVE while the production-readiness gate is not PASS;
- production-pilot/public-launch state cannot be ACTIVE while the production-readiness gate or mandatory pre-pilot workflow reassessment is not PASS;
- after accepted SLICE-0056 the workflow reassessment cannot remain `NOT_DUE`; the accepted post-0056 result is `PASS` and remains a readiness invariant;
- the finish script does not delete a worktree with substantive uncommitted changes;
- cleanup is skipped unless a merged PR can be confirmed through GitHub CLI;
- the setup script verifies the canonical repository before changing GitHub rules;
- the setup script creates/updates one named ruleset and does not touch source files or branches.
