# SLICE-0073 — Test/CI Throughput Optimization: Retained Evidence

**Status:** IMPLEMENTATION EVIDENCE — see `docs/slices/SLICE-0073-test-ci-throughput-optimization.md`
for the controlling slice and `specs/TEST_CI_THROUGHPUT_OPTIMIZATION.v0.1.md` for the contract.

## 1. Baseline (SLICE-0072 acceptance, pre-0073)

Measured at SLICE-0072 closure (GitHub Actions runs 36768339164 and 36773261259):

| Metric | Baseline |
| --- | --- |
| `db-integration` critical job (GitHub Actions) | 7m21s–8m22s |
| Complete PostgreSQL branch-coverage step alone | 4m35s–5m14s |
| Local complete PostgreSQL-backed backend suite | ~38–45 minutes |
| Accepted backend test count | 5900 passed / 3 skipped |

## 2. Shard / grouping design

The backend suite is not manually partitioned into fixed shard files. Instead it runs under a
single `pytest -n auto --dist loadgroup` invocation with two effective groups:

- **Shared-default-schema group** (`xdist_group` mark `hullq-persistence-shared-default-schema`,
  applied in `tests/persistence/conftest.py`): the 10 test modules that mutate the PostgreSQL
  connection's *default* schema directly (`clean_conn`/`migrated_conn`/`benchmark_conn`
  fixtures, or an inline `TRUNCATE TABLE` against a bare `psycopg.connect(db_url)`). All tests
  in this group run on one worker, preserving the existing truncate-between-tests isolation
  exactly as before parallelization.
- **Everything else**: every other test (all `tests/unit`, `tests/contract`, and the remaining
  ~46 `tests/persistence` modules) is freely load-balanced across every other `pytest-xdist`
  worker. The ~46 persistence modules were already self-isolating — each creates and drops its
  own uniquely named PostgreSQL schema per test (the pre-existing `_create_schema`/
  `_with_search_path` pattern, e.g. `tests/persistence/test_broker_workspace_access_api.py`) —
  so distributing them across workers introduces no new PostgreSQL state hazard.

The exact module list and the mechanical scan that produced it (every `tests/persistence/
test_*.py` file, classified by presence/absence of the per-test schema-isolation pattern) are
recorded in `tests/persistence/conftest.py`'s `_XDIST_SHARED_SCHEMA_MODULES` docstring/comment.

## 3. PostgreSQL isolation proof

Two isolation guarantees, both mechanical:

1. **Cross-worker**: only one `xdist_group` (the shared-default-schema group) ever touches the
   database's default schema; pytest-xdist's `loadgroup` scheduler guarantees every test in that
   group executes on a single worker, so no two tests in that group ever run concurrently against
   each other. Every other test operates inside its own throwaway, uniquely-named schema created
   and dropped within the test itself, so it can never collide with another worker's schema.
2. **Repeatability**: the sharded run was executed locally against the real local PostgreSQL 18
   instance and produced the same aggregate pass/skip count as the pre-0073 serial baseline (see
   section 5) — no flaky failures attributable to cross-worker interference were observed.

## 4. Coverage combine

`db-integration`'s coverage step now runs `pytest --cov=hullq --cov-branch --cov-report= -n auto
--dist loadgroup` instead of wrapping the whole suite in a single-process `coverage run`.
`pytest-cov` detects the active `pytest-xdist` workers and combines each worker's branch-coverage
data into one combined `.coverage` file automatically at session end (standard `pytest-cov`
xdist-combine behavior); the separate `coverage report` step then enforces the unchanged
`fail_under = 90` threshold from `pyproject.toml` against that combined result. A shard/worker
passing independently is never treated as a substitute for this combined enforcement — the gate
is always the one combined `coverage report` step.

## 5. Local before/after timing

The owner's local machine has only 4 logical CPUs and (observed empirically) a PostgreSQL
instance whose per-statement commit latency makes the full ~5900-test backend suite take on the
order of the pre-existing ~38–45 minute baseline; a full serial-vs-parallel comparison of the
entire suite was impractical to complete within one implementation session on this hardware. A
bounded, representative 8-file / 210-test persistence subset (`test_broker_identity_persistence.py`,
`test_broker_inventory_editing_api.py`, `test_broker_inventory_lifecycle_api.py`,
`test_broker_inventory_read_api.py`, `test_buyer_lead_api.py`, `test_buyer_lead_persistence.py`,
`test_native_listing_persistence.py`, `test_media_gallery_persistence.py` — all from the
already-self-isolating, freely-parallelizable group) was instead timed both ways using the new
`scripts/workflow/timed_pytest.py` wrapper through the existing
`scripts/workflow/claude_diag.py run-local-test-db-compact` helper:

| Run | Command | Result |
| --- | --- | --- |
| Serial (pre-0073 equivalent) | `... timed_pytest.py <8 files> -q` | 210 passed, **636.6s** |
| Parallel (`-n 4 --dist loadgroup`) | `... timed_pytest.py <8 files> -n 4 --dist loadgroup -q` | 210 passed, **317.8s** |

**Speedup: 2.00×**, identical pass count both ways (no lost, duplicated, or flaky tests from
cross-worker interference) — meeting the spec's local "at least 2× faster... where local
hardware/PostgreSQL permits" target on this representative, bounded sample. The full-suite local
number is `NOT VERIFIED` within this session; the GitHub Actions numbers in section 8 are the
authoritative acceptance-target evidence (the spec's primary, non-conditional target is the
GitHub PR critical path, not the local number).

## 6. Orchestration failure-propagation proof

Verified directly (temporary, not committed): a deliberately failing test
(`assert False`) was added under `tests/unit/`, then run alongside two real passing unit test
modules with `pytest -n 2 --dist loadgroup --cov=hullq --cov-branch --cov-report=`. The failing
test landed on worker `gw1`; the overall pytest invocation still exited non-zero
(`1 failed, 126 passed`, exit code 1) even though every other worker's tests passed, and the
coverage-enforcement path was still reached and still evaluated (reporting the expected
below-threshold failure for this tiny, non-representative subset). This mechanically confirms
the slice's required retained proof #4: a failure in any one shard/worker fails the aggregate
gate — `pytest -n auto --dist loadgroup` does not let a failure in one worker get masked by
other workers' successes. The scratch failing test was deleted immediately after the
verification; it is not part of the committed test suite.

## 7. Historical research/bootstrap replay routing

Classification per `specs/TEST_CI_THROUGHPUT_OPTIMIZATION.v0.1.md` section 5.6:

- **change-triggered** (default): SLICE-0017/0018/0021/0022/0026/0027/0028/0030/0031/0032
  Wikidata bootstrap/replay steps, now isolated in the `historical-research-replay` job. Every
  step is individually gated on `scripts/workflow/historical_replay_scope.py`'s relevance
  decision, computed from the actual PR diff against a documented path allowlist (the retained
  research/bootstrap trees, the bootstrap/identity-import production code, the migrations/SQL
  schema, the replay tests themselves, and the locked dependency files).
- **always relevant** (no gating, replay always executes): `schedule` (nightly drift backstop,
  `17 3 * * *`), `workflow_dispatch`, and `push` to `main` (the last accepted-state gate before
  `main` moves).
- **fail-open**: if the changed-file set cannot be determined for any reason (missing/zero base
  SHA, `git diff` failure), the decision defaults to relevant — the replay always runs rather
  than being silently skipped on ambiguity.
- **dependency-boundary justification**: these steps reproduce already-closed, frozen research
  evidence (fixed manifests tied to specific accepted SLICEs) against PostgreSQL through the
  bootstrap/identity-import code path. An ordinary product PR that never touches
  `research/bootstrap/**`, `scripts/bootstrap/**`, `src/hullq/bootstrap/**`, the identity-import/
  readback/migration modules, the replay tests, or the locked dependency files cannot change that
  reproduction's outcome, so re-running it on every such PR buys no incremental verification.
  The nightly schedule and the `push`-to-`main` run exist specifically to catch any drift this
  path-based reasoning might miss (e.g. a transitive dependency behavior change not reflected in
  `uv.lock`'s own diff, or an unanticipated code path).
- The job itself is never workflow-level path-filtered (per `docs/engineering/CI_BASELINE.md`'s
  required-check-stability rule) — it always executes and reports a real conclusion (fast
  success when no step runs, full replay result otherwise), so it can never leave a required
  check permanently pending.

## 7a. Real-CI-only findings and fixes (PR #282)

Two defects surfaced only on the real GitHub Actions run, not in local validation, and were
fixed on the same branch before acceptance:

1. **`db-integration`'s coverage step used bare `uv run pytest` instead of
   `uv run python -m pytest`.** Bare `pytest` does not add the repository root to `sys.path` the
   way `python -m pytest` does, so every test module that imports the `scripts.*` package
   (`test_claude_diag.py`, `test_historical_replay_scope.py`,
   `test_repository_governance.py`, several `tests/unit` search-demo modules, etc.) failed
   collection with `ModuleNotFoundError`. Local validation never hit this because
   `scripts/workflow/timed_pytest.py` and `scripts/run_pytest_local.py` both insert the repo root
   onto `sys.path` themselves. Fixed by invoking `python -m pytest` consistently in both
   pytest-xdist CI steps.
2. **A pre-existing "regenerate committed artifacts in place and diff" reproducibility-test
   family raced under parallel execution.** Several `tests/unit/test_*` modules
   (SLICE-0019 `research/manufacturers/`, SLICE-0020 `research/manufacturers/archive_clearance/`,
   SLICE-0024 `research/bootstrap/wikimedia/sl0024-independent-verification/`, SLICE-0025
   `research/stage3/sl0025-breadth-enrichment-entry/`) contain one test per package that calls a
   generator/`run_assemble()`-style entry point which rewrites the real, git-committed retained
   files in place (not `tmp_path`) to prove the regeneration is byte-stable, while sibling tests
   in the same or a different file read those same files. Under single-process serial execution
   (the pre-0073 topology) this was always safe because nothing ever ran concurrently; under
   `pytest-xdist` a reader on one worker could observe the writer's file mid-rewrite on another
   worker — observed directly as a digest recomputed to the SHA-256 of an empty file. Fixed by
   adding `tests/unit/conftest.py`, which pins every test in all of these modules to one shared
   `xdist_group` (`hullq-unit-shared-real-package-dirs`) so none of them can ever execute
   concurrently with any other, while every other unit test remains fully parallel. Verified
   clean across 6 repeated full non-DB-suite local runs after the fix (0 failures), versus a
   single flake observed with a narrower per-directory grouping before consolidating to one
   shared group.

Both fixes are orchestration-only: no production `src/hullq` behavior changed, and no test
assertion was weakened to make it pass.

## 8. Remote CI observation

Observed directly via `gh pr checks` / `gh run view --json jobs` on PR #282
(`https://github.com/StradaDelSole/HullQ/pull/282`), final green run
`https://github.com/StradaDelSole/HullQ/actions/runs/36789457988` (HEAD `a569b9f`):

| Job | Duration | Conclusion |
| --- | --- | --- |
| `db integration (PostgreSQL 18)` | **3m22s** | pass |
| `quality (windows-latest)` | 1m47s | pass |
| `historical research/bootstrap replay (PostgreSQL 18)` | 2m21s | pass |
| `quality (ubuntu-latest)` | 1m2s | pass |
| `web quality (Astro/Node)` | 36s | pass |
| `dependency audit` | 11s | pass |

**Critical path (workflow start → last required job complete): 3m23s** (23:08:02Z → 23:11:25Z),
against the 7m21s–8m22s baseline — a **~2.2×–2.4× reduction**, comfortably inside both the ≤5min
target and the ≤4min stretch target.

Inside `db-integration`, the sharded `pytest -n auto --dist loadgroup --cov=hullq --cov-branch`
step itself (the direct replacement for the old single-process `coverage run -m pytest`, whose
equivalent baseline step alone was 4m35s–5m14s) completed in **117.95s** on GitHub's 4-vCPU
Linux runner: **5908 passed, 3 skipped**, combined branch coverage **90.84%** (≥90% enforced by
the following `coverage report` step, which read the pytest-cov-combined data from all 4
xdist workers). The test count is 8 higher than the SLICE-0072 baseline's 5900 because this
slice adds `tests/contract/test_historical_replay_scope.py`; the skip count (3) is unchanged.

`historical-research-replay` correctly computed `relevant=true` and ran every replay step on
this PR (it modifies `pyproject.toml`, `uv.lock`, and `tests/persistence/conftest.py`, all in
its relevant-path allowlist) — a real end-to-end confirmation of the change-triggered routing
logic, not just the fail-open/always-relevant-event paths exercised by the local unit tests in
`tests/contract/test_historical_replay_scope.py`.

Two defects were found and fixed only via this real run — see section 7a for the exact symptoms,
root causes and fixes (a `python -m pytest` invocation fix, and an xdist serialization fix for a
pre-existing "regenerate committed artifacts in place" test family). The final green run above is
the fully-fixed state.
