# Post-SLICE-0072 Test / CI Throughput Reassessment — 2026-09-30

**Status:** OWNER-DIRECTED / READY FOR SLICE DEFINITION  
**Canonical base:** `2f903df9f9e48b016b473fbdb7dd2bf2c049619a`

## Trigger

The Project Owner explicitly directed that test/CI throughput be optimized at the earliest safe opportunity after SLICE-0072, before the next normal feature slice.

SLICE-0072 is now fully owner-accepted, merged, closed and locally finished. The trigger is therefore due now.

## Measured baseline

Recent exact-head GitHub Actions provide a concrete baseline:

| Run | DB integration | Full PostgreSQL coverage step | Ubuntu quality | Windows quality | Web | Audit |
|---|---:|---:|---:|---:|---:|---:|
| 36768339164 | 8m22s | 5m14s | 1m08s | 1m37s | 22s | 17s |
| 36773261259 | 7m21s | 4m35s | 1m04s | 1m46s | 25s | 16s |

The db-integration job is the CI critical path. Its largest single step is the complete Python suite with PostgreSQL + branch coverage.

The same full backend run was repeatedly observed locally during SLICE-0072 at roughly 38–45 minutes for approximately 5,900 tests.

The db-integration job additionally serializes:

- web install/build;
- retained HTTP vertical proofs;
- Stage-2 benchmark replay;
- retained research/bootstrap validation and PostgreSQL replay from older slices.

## Root causes

### RC-1 — duplicate broad execution

The normal quality jobs execute the non-PostgreSQL suite on both Ubuntu and Windows. The db-integration job then executes the entire Python suite again with PostgreSQL enabled rather than only the additional PostgreSQL-dependent coverage surface.

### RC-2 — one serialized PostgreSQL lane

All PostgreSQL-dependent tests and retained replay/proof work share one job/service container and therefore one critical path.

### RC-3 — historical retained research replay sits on every feature PR critical path

Deterministic research/bootstrap evidence remains valuable, but much of it is logically independent from ordinary marketplace/application changes. It is currently serialized after the product regression suite on every PR.

### RC-4 — local final validation has no safe parallel orchestrator

Persistence tests include legacy fixtures such as `clean_conn` that truncate shared tables. Blind pytest worker parallelism against one shared test database would be unsafe.

## Reconciliation

```text
DECIDED_AND_IMPLEMENTED
- branch coverage threshold = 90%
- PostgreSQL 18 integration required
- deterministic retained proofs required where governed
- immutable/pinned CI/toolchain baseline
- full final-candidate regression confidence required
- focused validation permitted during iteration/amendments
- no live mutable network dependencies in normal CI

DECIDED_NOT_YET_IMPLEMENTED
- measured test-duration reporting
- safe PostgreSQL test sharding
- combined coverage from isolated shards
- fast/focused local final-validation runner
- CI separation of product regression from historical retained research replay
- explicit change-aware validation routing

EXPLICITLY_DEFERRED
- lowering coverage threshold
- deleting meaningful tests for speed
- weakening security/audit gates
- unsafe shared-database xdist
- hiding deterministic failures behind retries

GENUINELY_OPEN
- exact shard count after measurement
- exact path-based routing rules for historical research replay, provided required-check stability is preserved
- whether local orchestration uses schemas or databases, subject to least-privilege compatibility

CONFLICT_OR_REGRESSION
- none
```

## Selection

The next capability is selected as:

```text
SLICE-0073 — Test / CI Throughput Optimization
```

This is an engineering-productivity slice, not a marketplace product-domain change.

It takes priority before the next normal feature capability because every subsequent slice benefits from the reduced validation cycle.

## Safety conclusion

The optimization must preserve the final acceptance bar. In particular:

- no lower coverage floor;
- no skipped PostgreSQL invariants;
- no reduced auth/security coverage;
- no removal of retained proof obligations without an explicit dependency-based routing decision;
- no unsafe concurrent use of shared mutable PostgreSQL state.

The preferred implementation direction is isolated PostgreSQL shards/jobs with deterministic coverage combine, plus separation of historical research replay from the application critical path where dependency boundaries prove it safe.
