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

## 8. Remote CI observation

<!-- Filled from a real `gh run view` observation of this branch's/PR's actual GitHub Actions
run after push. Per CLAUDE.md, local evidence is never substituted for this — if the remote run
could not be observed at handoff time, this section says so explicitly (NOT VERIFIED) rather than
inferring remote timing from local numbers. -->
