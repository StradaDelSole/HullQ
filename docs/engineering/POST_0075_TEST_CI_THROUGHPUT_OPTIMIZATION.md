# HullQ — Post-SLICE-0075 Test / CI Throughput Optimization

**Date:** 2026-09-30  
**Status:** OWNER-ACCEPTED / DECIDED_NOT_YET_IMPLEMENTED  
**Trigger:** immediately after SLICE-0075 closure, before resuming normal feature-slice cadence unless an urgent correctness/security blocker takes precedence.

## Problem

HullQ's regression safety has grown substantially, but the feedback loop is now materially constraining delivery speed.

Observed current behavior includes:

- roughly 5,800+ Python tests;
- a full backend suite often taking about 40–45 minutes locally;
- full-suite reruns after security/dependency amendments even when the changed surface is narrow;
- a CI PostgreSQL job that serially combines the full suite, coverage, web build, many retained vertical proofs, benchmark/research replay and additional validation;
- repeated broad validation consuming both wall-clock time and Claude context/tokens.

This is now an engineering-productivity problem. The owner explicitly wants it addressed after SLICE-0075.

## Goal

Reduce ordinary implementation/amendment feedback time and total slice cycle time **without lowering the final correctness, security, provenance, reproducibility or acceptance bar**.

The optimization target is not "fewer tests". It is:

```text
faster focused feedback
+ parallel execution
+ better test classification
+ fewer redundant full-suite reruns
+ preserved final full confidence
```

## Hard constraints

The optimization MUST NOT:

- delete meaningful regression coverage merely to improve duration;
- weaken PostgreSQL-backed persistence/concurrency evidence;
- weaken auth/MFA/session/security validation;
- weaken retained vertical proofs required by accepted contracts;
- lower the accepted coverage floor solely to obtain speed;
- make CI depend on mutable live services;
- hide failures behind retries;
- convert required deterministic gates into optional best-effort checks;
- allow a slice to merge without the accepted final-candidate gate set.

## Required workstream

### 1. Establish a measured baseline

Before optimization, retain machine-readable timing evidence for:

- unit tests;
- contract tests;
- PostgreSQL/persistence tests;
- web tests/build/check;
- retained vertical proofs;
- research/benchmark replay;
- dependency audit;
- repository validation;
- total CI critical path.

Identify the slowest individual test files/tests and setup/fixture costs.

No optimization claim is accepted without before/after measurements.

### 2. Classify the test suite

Introduce explicit, mechanically selectable tiers/markers where useful, for example:

```text
fast/unit
contract
persistence/postgres
security/auth
web
vertical-proof
research-replay
full-regression
```

Exact marker names are implementation-local.

Tests must belong to the narrowest truthful tier. A marker must not be used to hide an expensive correctness test from the final gate.

### 3. Parallelize safely

Evaluate and implement safe parallelism where deterministic isolation permits it, including:

- pytest workers for genuinely isolated unit/contract suites;
- sharding large PostgreSQL-backed suites across independent schemas/jobs;
- separate CI jobs for independent vertical proofs;
- concurrent OS jobs already supported by the matrix;
- independent web/backend/static checks in parallel.

PostgreSQL tests that share mutable global state must first gain proper isolation rather than being blindly parallelized.

### 4. Split fast PR feedback from final acceptance gates

Normal development should receive a fast failure signal as early as possible.

Preferred structure:

```text
FAST PR GATES
  repo validation
  format/lint/type
  focused/unit/contract tests
  affected web tests
  dependency audit

PARALLEL INTEGRATION GATES
  PostgreSQL shards
  auth/security integration
  retained vertical proofs
  required benchmark/replay

FINAL CANDIDATE / MERGE GATE
  accepted complete regression confidence
  without redundant reruns of identical evidence
```

This is a scheduling/execution optimization, not permission to omit final evidence.

### 5. Change-aware focused validation

During implementation and intermediate amendments:

- run tests directly affected by changed modules/invariants first;
- use an explicit mapping or tooling between changed surfaces and required focused suites where practical;
- broad full-suite execution remains mandatory at the final candidate boundary defined by the governing slice.

For tiny docs-only or formatting-only deltas, do not rerun unrelated 40-minute suites unless governance/security/dependency state actually changed.

### 6. Avoid duplicate work across local and remote validation

Where exact-head local evidence already exists and CI reruns the same deterministic test, decide deliberately which layer owns which gate.

Do not remove remote verification merely because local verification exists. Instead eliminate accidental duplicate sequences inside the same CI workflow and avoid repeated local full-suite runs between immaterial amendments.

### 7. Isolate retained research/replay from ordinary feature critical path where safe

The long PostgreSQL CI job currently contains historical benchmark/bootstrap/research replay work.

Reconcile which retained replay checks are:

- required on every feature PR;
- required only when affected files/contracts change;
- required on scheduled/nightly/release verification;
- required specifically at final production/research gates.

Any move away from every-PR execution must be justified by dependency boundaries and retained reproducibility guarantees, not convenience.

### 8. Preserve security dependency gates

`pip-audit`, locked dependency verification and other security gates remain first-class.

When a dependency-only amendment occurs, the workflow should provide focused security/auth regression evidence quickly rather than automatically requiring repeated unrelated long-running validation at every intermediate attempt. The final merge candidate still receives the required full confidence gate.

### 9. Improve observability of test duration

CI should expose enough timing information to answer:

- which test group dominates the critical path;
- which files/tests regressed in duration;
- whether new slices increase wall-clock materially;
- whether parallelization actually shortens merge latency.

A lightweight retained timing artifact/report is preferred over manual intuition.

## Acceptance target

Exact numeric targets must be set after baseline measurement, but the optimization is expected to produce a material improvement, not a cosmetic one.

Initial engineering target direction:

- ordinary focused feedback: minutes, not tens of minutes;
- final full validation: materially below the present ~40–45 minute backend-only local runtime where hardware/CI isolation allows;
- CI critical path reduced through parallelism/sharding;
- no loss of accepted coverage/invariant/security evidence.

The post-0075 optimization package must report before/after wall-clock measurements.

## Relationship to slice throughput

This work exists specifically because the current validation cycle is contributing to a practical cadence of roughly two slices per day despite high implementation effort.

Slice count itself is **not** the quality metric. The goal is to remove avoidable waiting so product work is limited by reasoning/implementation risk rather than serialized test machinery.

## Workflow

This is not part of SLICE-0072, SLICE-0073, SLICE-0074 or SLICE-0075 implementation scope.

After SLICE-0075 closure:

1. perform a fresh repo/CI/test reconciliation;
2. measure current exact baseline;
3. prepare a bounded engineering optimization capability;
4. implement and independently review it;
5. prove before/after speed improvement;
6. preserve final-candidate acceptance gates;
7. then resume normal product-slice cadence.

Do not preassign the implementation slice number here; canonical post-0075 reassessment owns numbering.
