# SLICE-0073 — Test / CI Throughput Optimization

**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Engineering productivity / validation throughput  
**Depends on:** SLICE-0072 owner-accepted / DONE  
**Normative contract:** `specs/TEST_CI_THROUGHPUT_OPTIMIZATION.v0.1.md`

## Capability

Deliver one coherent engineering outcome:

```text
current broad validation topology
→ measured partitioning
→ isolated PostgreSQL shards
→ deterministic aggregate coverage
→ parallel CI decomposition
→ faster local/final validation
→ unchanged acceptance bar
```

No marketplace/domain behavior is introduced.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One engineering capability: reduce validation wall-clock without weakening correctness/security/provenance.

**VISIBLE-RESULT CHECK:** PASS  
The implementation must produce retained before/after timing evidence showing materially shorter CI/local validation.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The owner explicitly prioritized this work immediately after SLICE-0072 so all later product slices inherit the faster validation path.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current CI, test strategy, PostgreSQL fixtures, coverage configuration, AI token-efficiency rules and recent exact-head Actions timings were checked before selecting the slice.

**TRIGGER GATES CHECK:** PASS  
This slice changes engineering/test execution only; it adds no production pilot, external data, payment activation or technical Search criterion.

## Decision / implementation reconciliation

**Accepted records checked:** docs/PROJECT_STATE.md; docs/slices/SLICE-0072-acceptance-closure.md; docs/engineering/CI_BASELINE.md; docs/engineering/AI_TOKEN_EFFICIENCY.md; specs/TEST_STRATEGY.md; .github/workflows/ci.yml; pyproject.toml; scripts/validate_repository.py; tests/persistence/conftest.py; recent GitHub Actions timing evidence from runs 36768339164 and 36773261259.  
**Production implementation checked:** current quality Ubuntu/Windows jobs; current db-integration PostgreSQL 18 job; branch coverage configuration; local pytest wrapper; PostgreSQL persistence fixtures; retained vertical/research replay steps.  
**Already implemented / not re-decided:** 90% branch coverage floor; PostgreSQL 18 integration requirement; cross-platform quality; locked dependencies; pip-audit; deterministic retained proofs; no live mutable network dependency; broad final-candidate confidence.  
**Exact remaining gap:** broad validation is materially slower than necessary because PostgreSQL/full-suite work and historical retained replay are serialized and local final validation has no supported safe isolated parallel orchestration.  
**Accepted-but-unimplemented obligations:** timing observability; safe isolated PostgreSQL sharding; deterministic aggregate coverage combine; CI critical-path decomposition; supported faster local/Claude final-validation route; explicit routing for historical research replay.  
**Material classifications:** DECIDED_AND_IMPLEMENTED existing correctness/security gates; DECIDED_NOT_YET_IMPLEMENTED 0073 throughput work; EXPLICITLY_DEFERRED unsafe same-schema xdist and any gate weakening; GENUINELY_OPEN exact shard count/topology after measurement; CONFLICT_OR_REGRESSION none.

### DECIDED_AND_IMPLEMENTED foundations

- coverage `fail_under = 90`;
- PostgreSQL 18 integration;
- Ubuntu/Windows cross-platform quality;
- web quality;
- locked dependency audit;
- deterministic retained application proofs;
- deterministic retained research/bootstrap evidence;
- focused iteration + broad final candidate validation discipline.

### DECIDED_NOT_YET_IMPLEMENTED — owned by 0073

- machine-readable timing observability;
- explicit backend test grouping;
- isolated PostgreSQL parallel/sharded execution;
- deterministic combined branch coverage across required shards;
- independent CI lanes for product regression / retained proofs / historical replay where safe;
- supported faster local/Claude final-validation route;
- before/after performance evidence.

### EXPLICITLY DEFERRED

- lowering the coverage threshold;
- deleting meaningful tests for speed;
- unsafe shared-schema parallel persistence execution;
- paid/distributed external test infrastructure;
- weakening security, provenance or reproducibility gates;
- marketplace/domain/API product changes.

### GENUINELY_OPEN

Exact shard count, grouping algorithm, schema-vs-database isolation choice, timing-report format and historical-replay routing details remain implementation-local provided the normative safety/acceptance contract is satisfied.

### CONFLICT_OR_REGRESSION

None found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Goal

Remove the current validation-throughput bottleneck before additional feature slices while preserving HullQ's final acceptance bar.

## Measured baseline

At SLICE-0072 closure:

- GitHub db-integration critical path: 7m21s–8m22s;
- complete PostgreSQL branch-coverage step: 4m35s–5m14s;
- local complete PostgreSQL-backed backend validation: repeatedly roughly 38–45 minutes;
- accepted backend count: 5900 passed / 3 skipped.

## Required implementation

1. instrument/retain baseline and resulting test-group timings;
2. introduce explicit backend test grouping suitable for deterministic execution;
3. safely parallelize PostgreSQL-dependent work using isolated mutable state;
4. combine branch coverage deterministically and enforce the existing 90% threshold;
5. remove unnecessary duplicate broad execution while retaining cross-platform confidence;
6. separate independent CI work into parallel jobs;
7. reconcile historical research/bootstrap replay out of the ordinary product critical path where a documented dependency boundary permits;
8. make focused/affected local validation the default for implementation and amendments, with full exact-head regression authoritative in GitHub Actions;
9. prohibit routine duplicate local full-suite reruns before a GitHub final-candidate run;
10. provide a supported fast local/Claude validation route and update CI/test engineering documentation to match the resulting system.

## Mandatory constraints

- no production/domain behavior changes;
- no coverage-floor reduction;
- no meaningful test deletion;
- no unsafe same-schema PostgreSQL concurrency;
- no weakening of dependency/security gates;
- no mutable live-network dependency;
- no required-check path-filter trap;
- no final-candidate merge without broad aggregate evidence.

## Acceptance performance target

- representative GitHub PR critical path <=5 minutes, stretch <=4 minutes;
- ordinary local implementation/amendment validation completes through focused affected gates rather than routine 38–45 minute full-suite runs;
- GitHub exact-head complete regression is authoritative for final candidate acceptance;
- aggregate branch coverage remains >=90%;
- all required test/proof/security categories remain reachable and enforced.

## Validation

The final implementation report must include exact before/after CI timings, local timing where reproducible, shard/group definitions, PostgreSQL-isolation proof, aggregate test counts, aggregate coverage, retained proof/research-replay routing, remote required-check results and exact implementation HEAD.

## Stop conditions

Stop for reassessment rather than weakening safety if:

- a persistence test cannot be safely isolated;
- combined coverage cannot be made mechanically trustworthy;
- required-check semantics become ambiguous;
- moving retained replay off every PR cannot be justified by dependency boundaries.

## Non-goals

SLICE-0073 adds no HullQ marketplace capability. After closure, normal product capability selection resumes through fresh reconciliation.

Initial implementation prompt must come only from `START_SLICE.bat` after readiness review, remote gates and readiness merge.

## Validation ownership — owner directive

Effective with SLICE-0073 and intended as the default for later slices:

```text
during implementation/amendment:
  local focused affected validation

final candidate:
  push exact HEAD
  GitHub Actions runs authoritative complete regression

remote failure:
  reproduce only the failing/affected surface locally
  fix
  focused local validation
  push again
```

Claude MUST NOT run the complete local backend suite merely because an implementation or amendment is ready for handoff. A local full-suite run requires a concrete exception: the slice changes the test/CI system itself, remote failure reproduction requires it, or an explicit local-only acceptance proof demands it.

This specifically prevents the historical pattern where two amendments can consume roughly 80–90 minutes of duplicated local full-suite execution before GitHub reruns the same regression.

## Implementation handoff

**Status set by this handoff:** `REVIEW`

Summary evidence is retained in `docs/engineering/CI_THROUGHPUT_EVIDENCE.md` and the conversational
completion report delivered at handoff. Local full-suite PostgreSQL-backed before/after timing could
not be completed within the implementation session on the owner's local hardware (see that document,
section 5); a bounded representative subset, the non-DB suite, coverage-combine mechanics and
orchestration failure-propagation were all verified directly. Remote GitHub Actions timing (the
authoritative acceptance evidence) was directly observed on PR #282 — critical path 3m23s against the
5min/4min targets and the 7m21s-8m22s baseline — and is detailed in section 8 of the evidence doc, so
this metric is `VERIFIED`, not `NOT VERIFIED`, at handoff. Two defects were found and fixed only via
that real run (see evidence doc section 7a); the final green HEAD before this merge-forward amendment
was `a569b9f`. This amendment merges the owner-directed focused-local/authoritative-remote validation
policy (PR #283, `origin/main` `8388a7b`) into this branch per explicit instruction, preserving both
the SLICE-0073 implementation/evidence and the newer policy above; see the amendment completion report
delivered at this handoff for the resulting exact HEAD and remote verification, never inferred from
local numbers.
