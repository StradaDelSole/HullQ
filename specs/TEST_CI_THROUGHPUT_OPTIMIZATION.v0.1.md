# Test / CI Throughput Optimization Contract v0.1

**Status:** ACCEPTED FOR SLICE-0073 READINESS  
**Scope:** engineering workflow / test execution / CI scheduling only

## 1. Objective

Reduce HullQ validation wall-clock and repeated Claude/operator waiting while preserving exactly the accepted correctness, security, provenance and reproducibility bar.

## 2. Baseline

The implementation must retain a before/after machine-readable timing comparison.

Current reference baseline:

- GitHub db-integration critical job: 7m21s–8m22s;
- complete PostgreSQL coverage step: 4m35s–5m14s;
- local complete backend suite with PostgreSQL: approximately 38–45 minutes;
- Python tests at SLICE-0072 acceptance: 5900 passed, 3 skipped.

## 3. Invariants

The slice MUST preserve:

1. branch coverage `fail_under = 90`;
2. PostgreSQL 18 persistence/integration coverage;
3. all meaningful regression tests;
4. Auth/session/MFA/security test coverage;
5. locked dependency verification and `pip-audit`;
6. deterministic retained vertical proofs required by accepted contracts;
7. reproducibility checks;
8. final-candidate broad confidence before merge;
9. cross-platform Python validation on Ubuntu and Windows;
10. normal CI independence from mutable live external sources.

## 4. Prohibited optimizations

The implementation MUST NOT:

- lower `fail_under`;
- mark meaningful tests skipped/xfail solely for speed;
- exclude production modules from coverage solely for speed;
- run persistence workers concurrently against shared mutable tables without isolation;
- weaken or remove dependency audit;
- make required checks conditional in a way that can leave GitHub required checks missing/pending;
- replace deterministic evidence with timing assumptions.

## 5. Required implementation surfaces

### 5.1 Timing observability

Provide retained timing data sufficient to identify:

- suite/shard wall-clock;
- CI job critical path;
- slowest relevant test groups/files where practical;
- before/after comparison.

### 5.2 Safe test partitioning

Partition the backend suite into mechanically explicit groups. Exact grouping is implementation-local, but must distinguish PostgreSQL-dependent work from ordinary unit/contract work.

### 5.3 PostgreSQL isolation

Any parallel PostgreSQL shard must own isolated mutable state.

Accepted approaches include independent CI service containers, isolated databases, or isolated schemas/search paths when all participating code honors the isolation boundary.

Legacy shared-state fixtures prohibit blind `pytest-xdist -n auto` against one common schema.

### 5.4 Coverage preservation

Parallel/sharded execution must produce deterministic combined branch coverage over the same production source set and enforce the existing 90% threshold.

A shard passing independently is not a substitute for combined coverage enforcement.

### 5.5 CI critical-path decomposition

Independent work should execute concurrently rather than serially when safe.

At minimum reconcile these categories:

- static/repository quality;
- cross-platform non-DB tests;
- PostgreSQL product regression;
- web validation;
- dependency audit;
- retained application vertical proofs;
- retained historical research/bootstrap replay.

### 5.6 Historical research/replay routing

The implementation must explicitly classify retained historical research/bootstrap checks into:

- every-PR product-critical;
- change-triggered;
- scheduled/nightly;
- release/production-gate;

or retain them every-PR if dependency evidence does not justify moving them.

No historical replay may be removed from the verification system merely for speed.

### 5.7 Local developer/Claude path

Provide a supported local command or orchestration path that allows:

- fast focused iteration;
- safe final-candidate broad validation;
- compact output suitable for Claude;
- PostgreSQL isolation if local parallel shards are used.

## 6. Acceptance performance target

The slice is not accepted for a cosmetic improvement.

Target:

- reduce GitHub PR critical path from the measured 7m21s–8m22s baseline to **<= 5 minutes** on a representative clean run, with a stretch target of <=4 minutes;
- materially reduce local full-validation wall-clock on the owner's environment, with a target of **at least 2× faster** than the observed 38–45 minute baseline where local PostgreSQL/hardware permits;
- focused iteration remains minutes rather than tens of minutes.

If infrastructure variance prevents a numeric target on one run, median/repeated evidence may be used, but the implementation must still demonstrate a material improvement.

## 7. Required retained proof

The final candidate must demonstrate:

1. all original required test categories still execute;
2. combined branch coverage >=90%;
3. PostgreSQL shard isolation prevents cross-shard state interference;
4. intentionally failing test in a shard fails the aggregate gate (mechanical proof or test of orchestration);
5. coverage from each required shard participates in final combine;
6. cross-platform quality remains green;
7. dependency audit remains green;
8. retained application proofs remain green;
9. historical replay remains reachable by its newly documented gate/routing;
10. before/after timings are recorded.

## 8. Scope exclusions

No marketplace/domain/API behavior change is authorized.

No Search criterion, identity rule, publication rule, broker workflow, buyer workflow or production data rule changes in SLICE-0073.
