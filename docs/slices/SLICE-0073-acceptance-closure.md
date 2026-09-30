# SLICE-0073 — Acceptance Closure

**ID:** SLICE-0073  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #282  
**Accepted implementation HEAD:** `a21192985293b5985dbf540360a335e1b5f80c5e`  
**Implementation merge commit:** `1dceb6d23d935962846714348acc2bd1c98dd28a`  
**Independent exact-head ACCEPT review:** 2026-10-01  
**Owner acceptance:** explicitly recorded 2026-10-01

## Accepted capability

SLICE-0073 reduces HullQ validation wall-clock while preserving the accepted correctness, security, provenance and coverage bar.

Accepted operating model:

```text
LOCAL / CLAUDE
→ focused affected tests
→ relevant PostgreSQL/static/web checks
→ slice-owned proof where required

EXACT PUSHED HEAD / GITHUB ACTIONS
→ authoritative complete regression
→ PostgreSQL 18 integration
→ aggregate branch coverage
→ cross-platform verification
→ web/dependency/security gates
→ required retained proofs/replays
```

Routine local 38–45 minute complete-regression runs are no longer required merely because a candidate or amendment is ready for handoff.

## Accepted implementation behavior

- `pytest-xdist` and `pytest-cov` provide safe parallel backend execution and combined branch coverage;
- default-schema PostgreSQL tests that share mutable state are explicitly pinned to one `xdist_group`;
- unit tests that rewrite retained committed artifact directories in place are likewise serialized in one safe group;
- already-isolated persistence tests remain freely parallelizable;
- GitHub quality jobs and PostgreSQL coverage use `python -m pytest -n auto --dist loadgroup`;
- combined branch coverage remains enforced at the existing 90% floor;
- historical Wikidata/bootstrap replay is separated into its own PostgreSQL 18 job;
- historical replay is change-triggered on pull requests, fail-open when changed-file scope cannot be established, and always runs on schedule/workflow_dispatch/push-to-main;
- a nightly schedule preserves drift detection;
- timing evidence is retained;
- START_SLICE / CLAUDE / test-strategy guidance now makes focused-local / authoritative-remote validation the default;
- no production/domain/API marketplace behavior changed.

## Independent review and amendment history

Initial implementation final HEAD `48f06590d3b6c2bfb0eb5ddcbb04726194967df4` delivered the throughput optimization and passed complete remote CI.

During the active slice, the Project Owner directed and separately merged the focused-local / authoritative-remote validation rule to canonical `main`. That advanced `main` while PR #282 remained open, creating a merge conflict in the slice document.

The accepted merge-forward amendment used a normal merge of `origin/main` into the existing SLICE-0073 branch, without rebase or force-push, producing final accepted HEAD `a21192985293b5985dbf540360a335e1b5f80c5e`.

Only `docs/slices/SLICE-0073-test-ci-throughput-optimization.md` required manual conflict resolution. Both the 0073 implementation handoff/evidence and the newer validation-ownership policy were preserved in full.

No material implementation finding remains.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- focused-local / authoritative-remote validation ownership
- pytest-xdist parallel backend execution
- safe serialization of shared mutable PostgreSQL/default-schema tests
- safe serialization of retained-package in-place rewrite tests
- pytest-cov xdist aggregate branch coverage
- unchanged 90% branch coverage floor
- parallelized PostgreSQL full regression
- historical replay decomposition
- change-triggered + nightly historical replay
- retained before/after timing evidence
- exact-head remote regression authority

DECIDED_NOT_YET_IMPLEMENTED
- future test-topology improvements if later measurements justify them
- future product capability SLICE-0074 selection

EXPLICITLY_DEFERRED
- lowering coverage threshold
- deleting meaningful tests for speed
- unsafe shared-schema parallelism
- paid/distributed test infrastructure
- weakening security/provenance/reproducibility gates

GENUINELY_OPEN
- future shard/group refinements based on new measured bottlenecks

CONFLICT_OR_REGRESSION
- none remain on accepted exact head
```

## Exact-head verification

Remote verification on accepted HEAD `a21192985293b5985dbf540360a335e1b5f80c5e`:

```text
quality (ubuntu-latest): SUCCESS
quality (windows-latest): SUCCESS
web quality (Astro/Node): SUCCESS
dependency audit: SUCCESS
reproduce (ubuntu-latest): SUCCESS
reproduce (windows-latest): SUCCESS
db integration (PostgreSQL 18): SUCCESS
historical research/bootstrap replay (PostgreSQL 18): SUCCESS
```

Measured accepted result:

```text
baseline GitHub critical path: 7m21s–8m22s
accepted final critical path: 3m47s
target: <=5m
stretch target: <=4m
result: PASS

accepted db-integration full parallel run:
5908 passed / 3 skipped
combined branch coverage: 90.84%
coverage threshold: 90.00%
```

Representative local PostgreSQL subset improved from 636.6s serial to 317.8s parallel (~2.00×). A complete local full-suite timing was intentionally not required because the accepted operating model makes the exact pushed GitHub HEAD authoritative for complete regression.

## Validation-ownership result

The accepted rule for future ordinary implementation/amendment work is:

```text
focused affected validation locally
→ push exact candidate HEAD
→ authoritative complete regression remotely
```

A complete local backend suite is exceptional, not routine. Exceptions require a concrete reason such as direct modification of test/CI/coverage/migration/isolation machinery, broad reproduction of a remote failure, or a controlling local-only proof requirement.

## Trigger-gate state after acceptance

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

SLICE-0073 changes engineering validation only and introduces no production pilot, external marketplace data, payment activation or Search criterion.

## PROJECT_STATE freshness closure

```text
PROJECT_STATE_ACCEPTED_SLICE: 0073
PROJECT_STATE_QUEUE_SLICE:    0074
```

SLICE-0074 remains **UNSELECTED** until fresh post-SLICE-0073 reconciliation is completed.

## Closure decision

```text
SLICE-0073 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0073
PROJECT_STATE_QUEUE_SLICE = 0074
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. `FINISH_SLICE.bat` may run only after this closure PR passes independent exact-head closure review, required remote gates and merge.
